#!/usr/bin/env python3
# shared_resources_trigger_match.py
# SHARED TOOL - lives in tower_crane\hooks\, referenced by any project that opts in.
#
# design\shared_resources_mechanical_trigger.md Part 3 - a deterministic, script-only recognition
# layer under shared_resources\'s existing skill-gate mechanism. Today, a Category-level fallback /
# Tier-scoped skill (templates\shared_resources.md's Saving step 7) only fires when the agent's own
# judgment classifies the live task as matching that skill's trigger description - a real, repeated
# failure mode when the task's phrasing doesn't happen to match. This hook adds a second,
# judgment-free recognition path: cheap case-insensitive substring matching against hand-authored
# concept slots in shared_resources\trigger_index.yaml. A hit does not bypass the existing Retrieval
# procedure - it only surfaces a candidate for the agent to read live, the same way any other
# retrieval candidate would be.
#
# Matching model (Part 3, superseding Part 2's flat one-phrase-per-entry list):
#   - Each resource has one or more scenario GROUPS (OR across groups - a resource with two groups
#     fires if either is satisfied).
#   - Each group holds 2-3 concept SLOTS, each slot a short list of 1-2 word alternate phrasings for
#     one concept (AND across slots within a group, OR within a slot).
#   - A Category's own slot-set (trigger_index.yaml's top-level `categories:` block) is applied as
#     an implicit extra slot appended to EVERY group of every resource tagged with that Category in
#     CATALOG.md - evaluated in this same deterministic string-match pass, never gated behind
#     whether the Skill tool fired.
#   - EDGE-ASSIST: a `process-material` edge in resource_relationships.yaml, from this resource to
#     another one, relaxes or waives this resource's own bar when the edge's `to` node is "in play"
#     this session (tracked by the companion `shared_resources_read_tracker.py` PostToolUse hook,
#     read from its per-session state file). Default strength relaxes a group's AND-across-slots to
#     any-one-slot; `strength: required` waives the check entirely - the resource surfaces
#     unconditionally, since a `required` edge means the target's own content literally cites this
#     resource's filename (a checkable fact, not an inferred association).
#
# Triggered by Claude Code's UserPromptSubmit hook, once per submitted message. Reads the prompt
# from stdin JSON's "user_input" field, matches it, and on a hit, emits
# hookSpecificOutput.additionalContext naming the candidate(s) - never blocks or alters the prompt.
#
# Non-goals (design doc's own): no embedding model, no LLM call, no network round-trip - this stays
# a local, sub-second string match so it can run on every single message without perceptible
# latency (design doc's "Speed vs. precision" - a governing principle, not just this file's own
# constraint). A missed match degrades to today's behavior; a false positive costs the agent a
# moment's consideration of an irrelevant candidate.
#
# HARD CONTRACT, deliberately different from consistency_check.py's guardrail contract: this hook
# must NEVER exit 2. Exit 2 on UserPromptSubmit blocks and erases the user's own message - the wrong
# failure mode for a retrieval nicety. Any error (missing file, malformed data, bad stdin JSON,
# missing/unreadable session-state file) fails open: print nothing, exit 0, with edge-assist simply
# unavailable rather than the whole match failing. A match prints hookSpecificOutput JSON and exits
# 0; no match exits 0 with no output.
#
# To use in a project: add a UserPromptSubmit hook in that project's .claude\settings.json pointing
# at this file (see MENU.md / templates\optins\shared_resources_trigger_match.json for the canonical
# snippet), then list it in that project's CLAUDE.md under "Tower Crane In Use". Edge-assist also
# needs shared_resources_read_tracker.py wired as a companion PostToolUse hook - see MENU.md's
# shared_resources_read_tracker row; this matcher works fine without it, just with no assist.
#
# Invocation:
#   <python_launcher> shared_resources_trigger_match.py            # hook mode: reads stdin JSON
#   <python_launcher> shared_resources_trigger_match.py "<text>"   # direct/test mode: argv[1]
#
# Exit codes: always 0.

import ast
import io
import json
import os
import re
import sys
from pathlib import Path

# Force UTF-8 stdout - Windows console defaults to cp1252 which breaks non-ASCII.
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SHARED_ROOT = Path(__file__).resolve().parent.parent
# shared_resources\ is private hub state, not shipped toolkit content - it lives at the outer root
# (design\local_first_reframe.md's outer/inner split), one level above SHARED_ROOT (toolkit\), same
# convention check_shared_resource_catalog.py / check_shared_resource_hosts.py already use.
HUB_ROOT = SHARED_ROOT.parent
TRIGGER_INDEX_PATH = HUB_ROOT / 'shared_resources' / 'trigger_index.yaml'
CATALOG_PATH = HUB_ROOT / 'shared_resources' / 'CATALOG.md'
RELATIONSHIPS_PATH = HUB_ROOT / 'shared_resources' / 'resource_relationships.yaml'

CATEGORY_KEY_RE = re.compile(r'^  (\S+):\s*$')
CATEGORY_SLOT_RE = re.compile(r'^    - (\[.*\])\s*$')
ENTRY_RESOURCE_RE = re.compile(r'^  - resource:\s*(\S+)\s*$')
GROUP_START_RE = re.compile(r'^      - slots:\s*$')
SLOT_RE = re.compile(r'^          - (\[.*\])\s*$')

EDGE_START_RE = re.compile(r'^  - type:\s*(\S+)\s*$')
EDGE_FIELD_RE = re.compile(r'^    (from|to|strength):\s*(\S+)\s*$')


def _parse_slot_literal(text):
    """Parse a `["a", "b"]`-shaped line as a Python list literal (ast.literal_eval - no external
    YAML dependency, design\\portability.md's multi-machine stance). Returns [] on anything
    malformed rather than raising - one bad hand-edited line should degrade that one slot, not take
    the whole matcher down."""
    try:
        val = ast.literal_eval(text)
        if isinstance(val, list) and all(isinstance(v, str) for v in val):
            return val
    except Exception:
        pass
    return []


def parse_trigger_index(text):
    """Hand-rolled parser for trigger_index.yaml's two top-level keys (Part 3 schema: `categories:`
    and `entries:`), same style as check_shared_resource_catalog.py's parse_relationships() - no
    external YAML dependency, relies on the file's always-consistent machine-written indentation.
    Tolerant of anything it doesn't recognize - an unfamiliar line is just skipped, never a crash.

    Returns (categories: {name: [slot, ...]}, entries: {resource_stem: [group, ...]}) where each
    group is a list of slots and each slot is a list of alternate term strings."""
    categories = {}
    entries = {}

    section = None
    current_category = None
    current_entry = None

    for line in text.splitlines():
        stripped = line.strip()
        if stripped == 'categories:':
            section = 'categories'
            current_category = None
            continue
        if stripped == 'entries:':
            section = 'entries'
            current_entry = None
            continue

        if section == 'categories':
            m = CATEGORY_KEY_RE.match(line)
            if m:
                current_category = m.group(1)
                categories[current_category] = []
                continue
            m = CATEGORY_SLOT_RE.match(line)
            if m and current_category is not None:
                categories[current_category].append(_parse_slot_literal(m.group(1)))
                continue

        if section == 'entries':
            m = ENTRY_RESOURCE_RE.match(line)
            if m:
                current_entry = m.group(1)
                entries[current_entry] = []
                continue
            if GROUP_START_RE.match(line) and current_entry is not None:
                entries[current_entry].append([])
                continue
            m = SLOT_RE.match(line)
            if m and current_entry is not None and entries[current_entry]:
                entries[current_entry][-1].append(_parse_slot_literal(m.group(1)))
                continue

    return categories, entries


def parse_process_material_edges(text):
    """Extract only `process-material` edges (from/to/strength) - the only edge type this matcher
    consumes (design doc's edge-assist section: prerequisite/lifecycle-sibling/related stay
    Retrieval-procedure-only, not read here at all)."""
    edges = []
    current = None
    in_edges = False
    for line in text.splitlines():
        if line.strip() == 'edges:':
            in_edges = True
            continue
        if not in_edges:
            continue
        m = EDGE_START_RE.match(line)
        if m:
            current = {'type': m.group(1), 'from': None, 'to': None, 'strength': None}
            if current['type'] == 'process-material':
                edges.append(current)
            else:
                current = None  # not a type this matcher tracks - ignore its fields too
            continue
        if current is not None:
            m = EDGE_FIELD_RE.match(line)
            if m:
                current[m.group(1)] = m.group(2)
    return edges


def parse_catalog_row(catalog_text, resource_stem):
    """Find the CATALOG.md row whose File cell stem matches resource_stem. Returns a dict with
    name/category/tier/description, or None if no matching row is found (catalog missing/renamed -
    the hit still surfaces by resource id/path, just without the extra detail or category slots)."""
    for line in catalog_text.splitlines():
        line = line.strip()
        if not line.startswith('|') or line.startswith('|---'):
            continue
        cells = [c.strip() for c in line.strip('|').split('|')]
        if len(cells) < 8:
            continue
        name, kind, file_cell, category, tier, description = cells[0:6]
        if name.lower() in ('name', ''):
            continue
        file_stem = Path(file_cell.strip('`')).stem
        if file_stem == resource_stem:
            return {'name': name, 'category': category, 'tier': tier, 'description': description}
    return None


def read_in_play_resources():
    """Read this session's read-tracking state file (written by the companion PostToolUse hook,
    shared_resources_read_tracker.py). Returns an empty set on anything missing/unreadable - edge-
    assist simply doesn't apply, the plain slot matching below still runs regardless."""
    try:
        project_root = os.environ.get('CLAUDE_PROJECT_DIR')
        session_id = _CURRENT_SESSION_ID
        if not project_root or not session_id:
            return set()
        state_path = Path(project_root) / 'logs' / 'shared_resources_session_state' / f'{session_id}.txt'
        if not state_path.exists():
            return set()
        return {line.strip() for line in state_path.read_text(encoding='utf-8').splitlines() if line.strip()}
    except Exception:
        return set()


def slot_satisfied(slot_terms, haystack):
    return any(term.lower() in haystack for term in slot_terms if term)


def group_satisfied(slots, haystack, relax_to_one):
    """AND-across-slots normally; relaxed to OR-across-slots (any one slot present) when a
    default-strength edge-assist applies this turn (design doc's 'relax to one slot')."""
    if not slots:
        return False, []
    hit_flags = [slot_satisfied(slot, haystack) for slot in slots]
    satisfied = any(hit_flags) if relax_to_one else all(hit_flags)
    matched_terms = []
    if satisfied:
        for slot, hit in zip(slots, hit_flags):
            if hit:
                matched_terms.append(next((t for t in slot if t.lower() in haystack), slot[0]))
    return satisfied, matched_terms


def find_matches(prompt_text, categories, entries, edges, catalog_text, in_play):
    """Evaluate every resource's groups (plus its Category's implicit slot, plus edge-assist)
    against the prompt. Returns a list of (resource_stem, detail_dict) for every resource that
    fires, where detail_dict carries enough to render a useful message (matched terms, or the
    required/default edge-assist reason when that's what fired it)."""
    haystack = prompt_text.lower()
    hits = []

    edges_by_from = {}
    for edge in edges:
        edges_by_from.setdefault(edge['from'], []).append(edge)

    for resource_stem, groups in entries.items():
        row = parse_catalog_row(catalog_text, resource_stem) if catalog_text else None
        category_slots = categories.get(row['category'], []) if row and row.get('category') else []

        # Edge-assist: does any process-material edge from this resource have its `to` in play?
        required_hit = None
        relax = False
        for edge in edges_by_from.get(resource_stem, []):
            if edge['to'] in in_play:
                if edge.get('strength') == 'required':
                    required_hit = edge['to']
                    break
                relax = True

        if required_hit:
            hits.append((resource_stem, {'row': row, 'assist': f'required edge - "{required_hit}" in play'}))
            continue

        for group in groups:
            combined = list(group) + list(category_slots)
            satisfied, matched_terms = group_satisfied(combined, haystack, relax_to_one=relax)
            if satisfied:
                detail = {'row': row, 'matched_terms': matched_terms}
                if relax:
                    detail['assist'] = 'default edge-assist relaxed this group to any one slot'
                hits.append((resource_stem, detail))
                break

    return hits


def format_context(hits):
    lines = [
        "[shared_resources mechanical trigger] The submitted message matched authored concept "
        "slot(s) for the following shared_resources\\ entries (design\\"
        "shared_resources_mechanical_trigger.md Part 3). This is a candidate surfaced by string "
        "match, not a judgment call already made - read the entry live per "
        "templates\\shared_resources.md's Retrieval procedure before relying on it, rather than "
        "trusting this description or any memory of the file's past content:",
    ]
    for resource_stem, detail in hits:
        row = detail.get('row')
        path = f"shared_resources/{resource_stem}.md"
        if row:
            tag = f"{row['category']}/{row['tier']}" if row['category'] else ""
            tag = f" ({tag})" if tag else ""
            lines.append(f'- "{row["name"]}"{tag} - {path}')
            if row['description']:
                lines.append(f"  {row['description']}")
        else:
            lines.append(f'- {path} (no CATALOG.md row found for detail)')
        if detail.get('matched_terms'):
            lines.append(f"  matched: {', '.join(detail['matched_terms'])}")
        if detail.get('assist'):
            lines.append(f"  ({detail['assist']})")
    lines.append(
        "If you act on one of these (or deliberately dismiss it as irrelevant), say so briefly to "
        "the user when it's worth mentioning - a mis-fire is otherwise invisible to them. A real "
        "critical correction or an unneeded-but-fired candidate is exactly what feeds a concrete, "
        "one-step-approvable trigger fix later (\"shared resources - adjust triggers for <entry>\"; "
        "templates\\shared_resources.md's \"Adjusting triggers\")."
    )
    return "\n".join(lines)


_CURRENT_SESSION_ID = None


def read_prompt_text(stdin_data):
    if len(sys.argv) > 1:
        return sys.argv[1]
    return stdin_data.get('user_input', '') or ''


def main():
    global _CURRENT_SESSION_ID
    try:
        stdin_data = {}
        if len(sys.argv) <= 1:
            raw = sys.stdin.read().lstrip(chr(0xFEFF))  # tolerate a UTF-8 BOM some Windows pipes prepend
            if raw.strip():
                stdin_data = json.loads(raw)
        _CURRENT_SESSION_ID = stdin_data.get('session_id')

        prompt_text = read_prompt_text(stdin_data)
        if not prompt_text or not TRIGGER_INDEX_PATH.exists():
            sys.exit(0)

        categories, entries = parse_trigger_index(TRIGGER_INDEX_PATH.read_text(encoding='utf-8'))
        if not entries:
            sys.exit(0)

        catalog_text = CATALOG_PATH.read_text(encoding='utf-8') if CATALOG_PATH.exists() else ""
        edges = parse_process_material_edges(
            RELATIONSHIPS_PATH.read_text(encoding='utf-8')) if RELATIONSHIPS_PATH.exists() else []
        in_play = read_in_play_resources()

        hits = find_matches(prompt_text, categories, entries, edges, catalog_text, in_play)
        if not hits:
            sys.exit(0)

        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": format_context(hits),
            }
        }))
        sys.exit(0)
    except Exception:
        # Fail open, always - a retrieval nicety must never block or degrade the user's own prompt.
        sys.exit(0)


if __name__ == '__main__':
    main()
