#!/usr/bin/env python3
# shared_resources_trigger_match.py
# SHARED TOOL - lives in tower_crane\hooks\, referenced by any project that opts in.
#
# design\shared_resources_mechanical_trigger.md - a deterministic, script-only recognition layer
# under shared_resources\'s existing skill-gate mechanism. Today, a Category-level fallback / Tier-
# scoped skill (templates\shared_resources.md's Saving step 7) only fires when the agent's own
# judgment classifies the live task as matching that skill's trigger description - a real, repeated
# failure mode (2026-08-31_toolkit_private_seo-skill-index-not-read-in-full.md, and the incident
# that produced this design doc) when the task's phrasing doesn't happen to match. This hook adds a
# second, judgment-free recognition path: cheap case-insensitive substring matching against
# hand-authored trigger phrases in shared_resources\trigger_index.yaml. A hit does not bypass the
# existing Retrieval procedure - it only surfaces a candidate for the agent to read live, the same
# way any other retrieval candidate would be.
#
# Triggered by Claude Code's UserPromptSubmit hook, once per submitted message. Reads the prompt
# from stdin JSON's "user_input" field (see Claude Code's hooks reference), matches it against
# every resource's trigger list, and on a hit, emits hookSpecificOutput.additionalContext naming the
# candidate(s) - never blocks or alters the prompt itself.
#
# Non-goals (design doc's own): no embedding model, no LLM call, no network round-trip - this stays
# a local, sub-second string match so it can run on every single message without perceptible
# latency. A missed match degrades to today's behavior (no worse than the status quo); a false
# positive costs the agent a moment's consideration of an irrelevant candidate.
#
# HARD CONTRACT, deliberately different from consistency_check.py's guardrail contract: this hook
# must NEVER exit 2. Exit 2 on UserPromptSubmit blocks and erases the user's own message - the wrong
# failure mode for a retrieval nicety. Any error (missing file, malformed YAML, bad stdin JSON)
# fails open: print nothing, exit 0. A match prints hookSpecificOutput JSON and exits 0; no match
# exits 0 with no output.
#
# To use in a project: add a UserPromptSubmit hook in that project's .claude\settings.json pointing
# at this file (see MENU.md / templates\optins\shared_resources_trigger_match.json for the canonical
# snippet), then list it in that project's CLAUDE.md under "Tower Crane In Use".
#
# Invocation:
#   <python_launcher> shared_resources_trigger_match.py            # hook mode: reads stdin JSON
#   <python_launcher> shared_resources_trigger_match.py "<text>"   # direct/test mode: argv[1]
#
# Exit codes: always 0.

import io
import json
import re
import sys
from pathlib import Path

# Force UTF-8 stdout - Windows console defaults to cp1252 which breaks non-ASCII.
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SHARED_ROOT = Path(__file__).resolve().parent.parent
# shared_resources\ is private hub state, not shipped toolkit content - it lives at the outer root
# (design\local_first_reframe.md's outer/inner split), one level above SHARED_ROOT (toolkit\), same
# convention check_shared_resource_catalog.py / check_shared_resource_hosts.py already use.
PROJECT_ROOT = SHARED_ROOT.parent
TRIGGER_INDEX_PATH = PROJECT_ROOT / 'shared_resources' / 'trigger_index.yaml'
CATALOG_PATH = PROJECT_ROOT / 'shared_resources' / 'CATALOG.md'

RESOURCE_RE = re.compile(r'^  - resource:\s*(\S+)\s*$')
TRIGGER_RE = re.compile(r'^\s*-\s*"(.+)"\s*$')


def parse_trigger_index(text):
    """Hand-rolled parser for trigger_index.yaml's one top-level `entries:` list - same style as
    check_shared_resource_catalog.py's parse_relationships() (no external YAML dependency;
    design\\portability.md's multi-machine stance). Returns {resource_stem: [trigger phrase, ...]}.
    Tolerant of anything it doesn't recognize - an unfamiliar line is just skipped, never a crash."""
    entries = {}
    current = None
    for line in text.splitlines():
        m = RESOURCE_RE.match(line)
        if m:
            current = m.group(1)
            entries[current] = []
            continue
        if current is not None:
            t = TRIGGER_RE.match(line)
            if t:
                entries[current].append(t.group(1))
    return entries


def parse_catalog_row(catalog_text, resource_stem):
    """Find the CATALOG.md row whose File cell stem matches resource_stem. Returns a dict with
    name/category/tier/description, or None if no matching row is found (catalog missing/renamed -
    the hit still surfaces by resource id/path, just without the extra detail)."""
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


def find_matches(prompt_text, trigger_index, catalog_text):
    """Case-insensitive substring match prompt_text against every resource's trigger phrases.
    Returns a list of (resource_stem, matched_phrase, catalog_row_or_None), one per resource that
    matched at least one phrase (first matching phrase only, per resource)."""
    haystack = prompt_text.lower()
    hits = []
    for resource_stem, phrases in trigger_index.items():
        for phrase in phrases:
            if phrase.lower() in haystack:
                row = parse_catalog_row(catalog_text, resource_stem) if catalog_text else None
                hits.append((resource_stem, phrase, row))
                break
    return hits


def format_context(hits):
    lines = [
        "[shared_resources mechanical trigger] The submitted message matched authored trigger "
        "phrase(s) for the following shared_resources\\ entries (design\\"
        "shared_resources_mechanical_trigger.md). This is a candidate surfaced by string match, not "
        "a judgment call already made - read the entry live per templates\\shared_resources.md's "
        "Retrieval procedure before relying on it, rather than trusting this description or any "
        "memory of the file's past content:",
    ]
    for resource_stem, phrase, row in hits:
        path = f"shared_resources/{resource_stem}.md"
        if row:
            tag = f"{row['category']}/{row['tier']}" if row['category'] else ""
            tag = f" ({tag})" if tag else ""
            lines.append(f'- "{row["name"]}"{tag} - {path} - matched "{phrase}"')
            if row['description']:
                lines.append(f"  {row['description']}")
        else:
            lines.append(f'- {path} - matched "{phrase}" (no CATALOG.md row found for detail)')
    return "\n".join(lines)


def read_prompt_text():
    if len(sys.argv) > 1:
        return sys.argv[1]
    raw = sys.stdin.read()
    if not raw.strip():
        return ""
    data = json.loads(raw)
    return data.get('user_input', '') or ''


def main():
    try:
        prompt_text = read_prompt_text()
        if not prompt_text or not TRIGGER_INDEX_PATH.exists():
            sys.exit(0)

        trigger_index = parse_trigger_index(TRIGGER_INDEX_PATH.read_text(encoding='utf-8'))
        if not trigger_index:
            sys.exit(0)

        catalog_text = CATALOG_PATH.read_text(encoding='utf-8') if CATALOG_PATH.exists() else ""
        hits = find_matches(prompt_text, trigger_index, catalog_text)
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
