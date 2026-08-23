#!/usr/bin/env python3
"""
disconnect_consumer.py - reverse of new_consumer.py's host-connect: removes a host's connection to
a registered consumer (design\\connect_disconnect.md).

Three modes (--mode):
  this-only     - remove only the current machine's connection to this consumer.
  all-but-this  - remove every OTHER host's connection, leaving only this machine.
  all           - remove every host's connection (full disconnect).

For each host being removed:
  - If it's THIS machine (config['host_id']), the consumer's own local files at its registered
    path are cleaned up too: this hub's @import lines are stripped from CLAUDE.md, its
    'Tower Crane In Use'/'Shared Workflow Protocol' sections are replaced with a short honest
    pointer (never just left behind reading as if the connection were still live), this hub's
    hook entries and the Read(import_base/**) permission rule are stripped from
    .claude\\settings.json, and every .claude\\skills\\<name>\\ directory this hub scaffolded is
    removed. A generated TOWER_CRANE_DISCONNECT_NOTES.md is written as the single complete
    breadcrumb index (what was removed, what was deliberately left behind, where the rest of the
    history lives), and everything touched is committed (and pushed, if a remote exists) in the
    consumer's OWN repo so nothing sits uncommitted/unexplained. project_progress.md and
    FIRST_RUN.md are never touched - they're the consumer's own content, not Tower Crane's.
  - If it's a DIFFERENT host, only the registry side can be touched from here - this machine has
    no filesystem access to another machine's files. Printed plainly, not silently skipped.

Registry side: each removed host's hosts.<host_id> entry is deleted. If 0 hosts remain, the whole
consumers\\<slug>.md file is hard-deleted (git history is the record - no archive/marker, matching
the project's existing "no version tags/changelog" precedent, Reverts decision). If exactly 1 host
remains, scope auto-reverts to `local` (registry_lib.remove_host_from_text's floor-in-reverse).

Deliberately NOT touched by this first build (flagged in the notes file, not silently dropped):
any adopted shared_resources\\ stub (its hub-rel: marker just goes stale) and
COMPLIANCE_GUIDANCE.md's broadcast section - a real scope decision left for a later pass if it
turns out to matter in practice.

Reused by remove_hub.py (this-only, looped across every consumer connected on this machine) - see
that script for the "reverse setup_machine.md entirely" case.
"""

import argparse
import datetime
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config_lib import (
    commit_consumer_changes, commit_hub_changes, get_shared_config, print_diagnose_inline,
    sync_consumer_repo,
    TC_IN_USE_HEADING, WORKFLOW_HEADING, DISCONNECTED_HEADING,
    DISCONNECT_NOTES_FILENAME as NOTES_FILENAME,
    HUB_POINTER_IMPORT_LINE, HUB_POINTER_RELPATH, HUB_DISPATCH_RELPATH,
    CONSUMER_OWNED_PATHS, scoped_status_paths,
)
import registry_lib
from new_consumer import SKILL_PIECES, STANDALONE_SKILLS

SHARED_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = SHARED_ROOT.parent
CONSUMERS_DIR = PROJECT_ROOT / 'consumers'


def local_skill_names(consumer):
    """Every .claude\\skills\\<name>\\ this hub would have scaffolded for this consumer: the
    SKILL_PIECES piece->skills expansion for each imported companion, every STANDALONE_SKILLS
    entry (always scaffolded), and every private_opted_in name (private tools aren't tagged
    hook-vs-skill in the registry, so removal is attempted unconditionally - a no-op for a name
    that was actually a private hook, since there's no matching directory to remove)."""
    names = set()
    for imp in consumer['imported']:
        for piece_info in SKILL_PIECES.values():
            if piece_info['companion'] == imp['name']:
                names.update(piece_info['skills'])
    names.update(STANDALONE_SKILLS)
    names.update(o['name'] for o in consumer['private_opted_in'])
    return names


def replace_prose_sections(text, date, mode):
    """Replace the '## Tower Crane In Use' / '## Shared Workflow Protocol' sections (each
    heading through the end of its content) with a short, honest pointer to NOTES_FILENAME -
    fixes the gap found live 2026-08-12 (design\\connect_disconnect.md): leaving that prose in place made
    a disconnected project's CLAUDE.md still read as if the connection were live, which is what
    sent a fresh session in that project looking for an explanation. Returns (new_text, replaced)
    - replaced is False if the standard heading isn't found (e.g. hand-edited CLAUDE.md), in
    which case text is returned unchanged and the caller flags it for manual cleanup instead of
    guessing at unfamiliar structure."""
    idx_start = text.find(TC_IN_USE_HEADING)
    if idx_start == -1:
        return text, False
    search_from = text.find(WORKFLOW_HEADING, idx_start)
    if search_from == -1:
        search_from = idx_start
    idx_end = len(text)
    for m in re.finditer(r'(?m)^## .+$', text):
        if m.start() > search_from:
            idx_end = m.start()
            break
    pointer = (
        f"{DISCONNECTED_HEADING}\n\n"
        f"This project was disconnected from the Tower Crane shared-tooling hub on {date} "
        f"(mode: {mode}). See `{NOTES_FILENAME}` for exactly what was removed, what was "
        f"deliberately left behind, and where the remaining history lives.\n\n"
    )
    return text[:idx_start] + pointer + text[idx_end:], True


def _detect_shared_content(target_path, consumer, config):
    """Read-only detection of every trace of SHARED, git-tracked Tower Crane content in this
    consumer's local files - the same signals strip_local_references()'s apply path removes on the
    last host, computed here without mutating anything. Used only when another host is still
    connected, to render an exhaustive, code-derived checklist for a manual full purge
    (design\\host_scoped_disconnect_state.md Decision 2) - never a hand-written enumeration that
    could drift from what a real last-host removal would actually do."""
    import_base = str(config['import_base'])
    claude_md_path = target_path / 'CLAUDE.md'
    n_imports = 0
    sections_present = False
    if claude_md_path.exists():
        text = claude_md_path.read_text(encoding='utf-8')
        escaped_base = re.escape(import_base)
        n_imports = (len(re.findall(rf'(?m)^@{escaped_base}/\S+\.md\s*\r?\n?', text)) +
                     len(re.findall(rf'(?m)^{re.escape(HUB_POINTER_IMPORT_LINE)}\s*\r?\n?', text)))
        sections_present = TC_IN_USE_HEADING in text

    settings_path = target_path / '.claude' / 'settings.json'
    hook_count = 0
    if settings_path.exists():
        settings = json.loads(settings_path.read_text(encoding='utf-8'))
        tools = [o['name'] for o in consumer['opted_in']] + [o['name'] for o in consumer['private_opted_in']]
        for groups in settings.get('hooks', {}).values():
            for grp in groups:
                hook_count += sum(
                    1 for h in grp.get('hooks', [])
                    if any(
                        re.search(r'hooks[\\/]' + re.escape(t) + r'\.(ps1|py)', h.get('command', '')) or
                        re.search(r'_hub_dispatch\.py"?\s+' + re.escape(t) + r'\b', h.get('command', ''))
                        for t in tools))

    dispatch_present = (target_path / HUB_DISPATCH_RELPATH).exists()

    skills_dir = target_path / '.claude' / 'skills'
    skills_present = sorted(
        name for name in local_skill_names(consumer) if (skills_dir / name).exists())

    return {
        'n_imports': n_imports, 'sections_present': sections_present,
        'removed_hooks': hook_count, 'dispatch_present': dispatch_present,
        'skills_present': skills_present,
    }


def write_disconnect_notes(target_path, date, mode, host_id, n_imports, removed_hooks,
                            had_read_rule, removed_skills, sections_replaced, log,
                            original_registered=None, is_last_host=True,
                            hub_pointer_removed=False, dispatch_removed=False, detected=None):
    """Write TOWER_CRANE_DISCONNECT_NOTES.md - designed so reading THIS FILE ALONE gives a 100%
    complete list of every trace Tower Crane leaves behind in a consumer project after a
    this-machine disconnect, including a cross-reference back to CLAUDE.md's own short pointer
    (which itself points back here) so neither file alone is a dead end."""
    removed_lines = []
    if n_imports:
        removed_lines.append(f"- {n_imports} `@import` line(s) removed from `CLAUDE.md`")
    if removed_hooks or had_read_rule:
        detail = []
        if removed_hooks:
            detail.append(f"{removed_hooks} hook entry/entries")
        if had_read_rule:
            detail.append("the `Read(...)` permission rule granting access to the hub's "
                           "templates folder")
        removed_lines.append(f"- {' and '.join(detail)} removed from `.claude/settings.json`")
    if removed_skills:
        plural = "y" if len(removed_skills) == 1 else "ies"
        removed_lines.append(
            f"- Skill director{plural} removed from `.claude/skills/`: " +
            ", ".join(f"`{n}`" for n in sorted(removed_skills)))
    if sections_replaced:
        removed_lines.append(
            f"- `{TC_IN_USE_HEADING}` / `{WORKFLOW_HEADING}` in `CLAUDE.md` replaced with a "
            f"short pointer under `{DISCONNECTED_HEADING}` - that pointer links back to this "
            f"file.")
    if hub_pointer_removed:
        removed_lines.append(
            f"- `{HUB_POINTER_RELPATH}` deleted (gitignored, per-host only - had zero effect on "
            f"any other host's own connection).")
    if dispatch_removed:
        removed_lines.append(f"- `{HUB_DISPATCH_RELPATH}` deleted (last host disconnecting).")
    if not removed_lines:
        removed_lines.append("- (nothing local was present to remove - this host's connection "
                              "existed only in the registry.)")
    checklist = []
    if not is_last_host:
        if detected['n_imports']:
            checklist.append(f"- {detected['n_imports']} `@import`/pointer line(s) in `CLAUDE.md`")
        if detected['sections_present']:
            checklist.append(f"- the `{TC_IN_USE_HEADING}` / `{WORKFLOW_HEADING}` sections in `CLAUDE.md`")
        if detected['removed_hooks']:
            checklist.append(f"- {detected['removed_hooks']} hook entry/entries in `.claude/settings.json`")
        if detected['dispatch_present']:
            checklist.append(f"- `{HUB_DISPATCH_RELPATH}`")
        if detected['skills_present']:
            plural = "y" if len(detected['skills_present']) == 1 else "ies"
            checklist.append(
                f"- skill director{plural} in `.claude/skills/`: " +
                ", ".join(f"`{n}`" for n in detected['skills_present']))
        if checklist:
            removed_lines.append(
                "- **Left in place on purpose:** shared, git-tracked Tower Crane content was NOT "
                "touched here - another host is still connected to this consumer and depends on it "
                "(design\\consumer_reference_indirection.md's host-count-aware split). Only this "
                "host's own per-host state (above) was cleaned up. See \"Your options from here\" "
                "below.")
        else:
            removed_lines.append(
                "- **Left in place on purpose:** shared, git-tracked Tower Crane content was "
                "checked for and none was found present here to begin with - nothing left to purge "
                "even by hand.")

    options_section = ""
    if not is_last_host and checklist:
        options_section = (
            "## Your options from here (another host is still connected)\n\n"
            "Another host is still connected to this consumer and depends on the shared, "
            "git-tracked content listed below - none of it was touched by this disconnect, and "
            "none of it should be hand-edited (doing so would break that other host's live "
            "connection the next time it pulls). Four real options, and since one of them is "
            "\"do nothing,\" none of the others is time-pressured - exercise any of them whenever "
            "it suits you.\n\n"
            "**1A. Manually strip this clone too, while leaving the other host(s) connected "
            "elsewhere.**\n"
            "1. Sever this clone from the shared history first - `git remote remove origin` (or "
            "repoint it to a private fork). Nothing removed after this point can ever reach the "
            "surviving host via a push, which is what makes step 2 safe to do at all.\n"
            "2. Then remove every trace below by hand (the exact same content the last host to "
            "disconnect would have had removed automatically):\n"
            + "\n".join(f"   {line}" for line in checklist) + "\n\n"
            "**1B. Let the other host(s) do it, then just `git pull` here.** Run `\"disconnect "
            "project\"` (or `\"uninstall tower crane\"`, which runs it for every consumer that "
            "machine has) on every OTHER machine still connected to this consumer. The LAST one to "
            "disconnect is the one whose own run triggers the real full strip there (shared "
            "content removed, commit pushed to `origin`) - this clone then only needs an ordinary "
            "`git pull` to receive that same fully-stripped state. No manual edits here at all, "
            "and it works even though this host already left the registry.\n\n"
            "**2. Reconnect instead.** If Tower Crane isn't already set up on this machine, set it "
            "up, then run `\"connect project\"` for this consumer - this regenerates "
            f"`{HUB_POINTER_RELPATH}` and this host's own `Read(...)` permission entry, restoring "
            "full functionality alongside the still-live shared content. **Not yet verified for a "
            "clone left in exactly this shape** (a this-only disconnect while another host stays "
            "connected) - test this path before relying on it without checking.\n\n"
            "**3. Do nothing.** Leave this file in place - it's a reference for exercising 1A "
            "later, and a record of exactly which files here are shared/tracked and must not be "
            "hand-edited. This file itself is not required to be kept; deleting it loses nothing "
            "but that record.\n\n"
        )

    left_lines = [
        "- `project_progress.md` - this project's own continuity file; any historical Work Log "
        "entries mentioning Tower Crane (checkpoint/archive commits, resume notes, etc.) remain "
        "exactly as written.",
        "- Git history - every commit this project ever made via a Tower Crane skill (e.g. "
        "\"Checkpoint: ...\", \"Archive: ...\" commit messages), plus the commit that performed "
        "this disconnect itself, remain in `git log`. Nothing has been rewritten or squashed.",
    ]
    shared_resources_path = target_path / 'shared_resources'
    if shared_resources_path.exists():
        left_lines.append(
            f"- `shared_resources/` - present at `{shared_resources_path}`; any adopted stub's "
            f"`hub-rel:` marker will just go stale, the files themselves are untouched.")
    compliance_path = target_path / 'COMPLIANCE_GUIDANCE.md'
    if compliance_path.exists():
        left_lines.append(
            f"- `COMPLIANCE_GUIDANCE.md` - present at `{compliance_path}`; its Tower Crane "
            f"broadcast section is untouched.")

    if sections_replaced:
        cross_ref = (f"`CLAUDE.md` carries a short pointer back to this file, under the heading "
                      f"`{DISCONNECTED_HEADING}`. That pointer plus this file are the only two "
                      f"places Tower Crane content still surfaces at a glance in this project; "
                      f"everything else is history, listed above.")
    elif not is_last_host and detected['sections_present']:
        cross_ref = (f"`CLAUDE.md` does **not** carry a pointer to this file - its "
                      f"`{TC_IN_USE_HEADING}`/`{WORKFLOW_HEADING}` sections were deliberately left "
                      f"untouched (another host is still connected and depends on that shared, "
                      f"tracked content), not because they're missing or hand-edited. This file is "
                      f"therefore the only place this disconnect is recorded at a glance for this "
                      f"host - check `CLAUDE.md` by hand too if you want the full manual-purge "
                      f"checklist under \"Your options from here\" below.")
    else:
        cross_ref = (f"`CLAUDE.md` does **not** carry a pointer to this file - its "
                      f"`{TC_IN_USE_HEADING}`/`{WORKFLOW_HEADING}` sections weren't found in "
                      f"their standard scaffolded shape (likely hand-edited), so they were left "
                      f"untouched rather than guessed at. This file is therefore the only place "
                      f"this disconnect is recorded at a glance - check `CLAUDE.md` by hand too.")

    registered_note = f" Originally registered with Tower Crane: **{original_registered}**." \
        if original_registered else ""
    host_scope_note = (
        f" This file describes **`{host_id}`**'s own clone specifically (mode: `{mode}`) - if "
        f"you're reading it on a different machine (e.g. after pulling it via `git pull` "
        f"following another host's own disconnect), it has no bearing on that machine's own Tower "
        f"Crane connection, which is unaffected.")

    tail_section = ""
    if is_last_host:
        tail_section = (
            f"## If you want a clean break\n\n"
            f"None of the above is deleted automatically. To fully purge Tower Crane from this "
            f"project:\n"
            f"- Delete this file and the `{DISCONNECTED_HEADING}` section in `CLAUDE.md` (if "
            f"present).\n"
            f"- Remove `shared_resources/` / `COMPLIANCE_GUIDANCE.md` if present and no longer "
            f"wanted.\n"
            f"- Rewriting git history to remove old Tower Crane commits is a manual, destructive "
            f"git operation - not something this command does. Ask Claude Code in this project "
            f"directly if you want help with that.\n\n"
            f"Reconnecting later: run `\"connect project\"` again from the Tower Crane hub.\n")

    text = (
        f"# Tower Crane — Disconnect Notes\n\n"
        f"Generated automatically by `disconnect_consumer.py` on {date} (mode: {mode}, host: "
        f"`{host_id}`). This file is meant to be the complete index of every trace Tower Crane "
        f"left behind in this project after disconnecting — read this file alone and you "
        f"have the full picture; nothing else needs following to find "
        f"more.{registered_note}{host_scope_note}\n\n"
        f"## Removed by this disconnect\n\n"
        + "\n".join(removed_lines) + "\n\n"
        + options_section +
        f"## Left behind deliberately (not touched by this command)\n\n"
        + "\n".join(left_lines) + "\n\n"
        f"## Cross-reference\n\n"
        f"{cross_ref}\n\n"
        + tail_section
    )
    notes_path = target_path / NOTES_FILENAME
    notes_path.write_text(text, encoding='utf-8', newline='\n')
    log(f"  wrote  {notes_path}")


def strip_local_references(target_path, consumer, config, mode, log, is_last_host=True):
    """Undo what new_consumer.py wrote at target_path for THIS hub connection. Host-count-aware
    split (design\\consumer_reference_indirection.md, fixing a confirmed pre-existing bug this
    design's own per-host/shared distinction made newly obvious): ALWAYS strips this host's own
    per-host state (hub_pointer.md, this host's own Read(...) permission entry) regardless of how
    many other hosts remain connected; only strips SHARED, git-tracked content (@import/pointer
    line, hook entries, _hub_dispatch.py, skill-stub dirs) when is_last_host - doing so with
    another host still connected would break that host's live connection, since those are the same
    tracked file synced to every host. Replaces the now-inaccurate 'Tower Crane In Use'/'Shared
    Workflow Protocol' prose with a short honest pointer (last-host only, for the same reason),
    writes TOWER_CRANE_DISCONNECT_NOTES.md as the single complete breadcrumb index, then commits
    everything in the consumer's own repo (commit_consumer_changes()) so nothing is left
    uncommitted/unexplained - the gap a live 2026-08-12 test found (design\\connect_disconnect.md).
    Never touches project_progress.md or FIRST_RUN.md - those are the consumer's own content.

    Returns a result dict (design\\script_action_reporting.md) - the same classification variables
    this function already computes to drive its own behavior and write_disconnect_notes(), threaded
    back out instead of discarded, so a caller's own close-out summary can relay them directly
    rather than re-deriving them from this function's printed log. Every key is always present with
    a safe default, even on the early target-missing return, so a caller never needs a presence
    check before reading one."""
    target_path = Path(target_path)
    result = {
        'target_path': str(target_path), 'target_missing': False,
        'hub_pointer_removed': False, 'n_imports': 0, 'sections_replaced': False,
        'claude_prose_status': None, 'removed_hooks': 0, 'had_read_rule': False,
        'dispatch_removed': False, 'removed_skills': [], 'notes_path': None,
        'commit_result': None, 'left_uncommitted': [],
    }
    if not target_path.exists():
        log(f"  note   {target_path} no longer exists on disk - nothing local to clean up.")
        result['target_missing'] = True
        return result

    # Pull this consumer's own repo current BEFORE reading/editing CLAUDE.md/settings.json below,
    # so the disconnect commit is never built on a stale snapshot (config_lib.py's
    # sync_consumer_repo() - a real 2026-08-22 push conflict this closes (see that function's own
    # docstring, and project_progress.md's Work Log, for the full incident).
    sync_consumer_repo(target_path, log=log)

    date = datetime.date.today().isoformat()
    import_base = str(config['import_base'])

    # .claude\hub_pointer.md: ALWAYS safe to delete - gitignored, genuinely per-host, zero effect
    # on any other host's own (separately-regenerated) copy.
    pointer_path = target_path / HUB_POINTER_RELPATH
    hub_pointer_removed = pointer_path.exists()
    if hub_pointer_removed:
        pointer_path.unlink()
        log(f"  removed {pointer_path}")

    # CLAUDE.md: strip @import lines / the pointer line, then replace the prose sections - SHARED,
    # tracked content, so only on the last host disconnecting.
    claude_md_path = target_path / 'CLAUDE.md'
    n_imports = 0
    sections_replaced = False
    if is_last_host and claude_md_path.exists():
        text = claude_md_path.read_text(encoding='utf-8')
        escaped_base = re.escape(import_base)
        text, n_direct = re.subn(rf'(?m)^@{escaped_base}/\S+\.md\s*\r?\n?', '', text)
        text, n_pointer = re.subn(rf'(?m)^{re.escape(HUB_POINTER_IMPORT_LINE)}\s*\r?\n?', '', text)
        n_imports = n_direct + n_pointer
        text, sections_replaced = replace_prose_sections(text, date, mode)
        if n_imports or sections_replaced:
            claude_md_path.write_text(text, encoding='utf-8', newline='\n')
            log(f"  wrote  {claude_md_path} (removed {n_imports} @import line(s)"
                f"{', replaced Tower Crane prose sections' if sections_replaced else ''})")
        if not sections_replaced:
            log(f"  note   {claude_md_path} doesn't contain the standard '{TC_IN_USE_HEADING}' "
                f"section (hand-edited?) - prose left untouched, clean up manually if desired.")

    # settings.json: hook entries are SHARED tracked content (last host only); this host's own
    # Read(...) permission entry is per-host-distinct (each host appends its own import_base-keyed
    # entry - design\consumer_reference_indirection.md's decision 4) so it's always removed.
    settings_path = target_path / '.claude' / 'settings.json'
    removed_hooks = 0
    had_read_rule = False
    if settings_path.exists():
        settings = json.loads(settings_path.read_text(encoding='utf-8'))
        if is_last_host:
            tools = [o['name'] for o in consumer['opted_in']] + [o['name'] for o in consumer['private_opted_in']]
            for evt, groups in list(settings.get('hooks', {}).items()):
                new_groups = []
                for grp in groups:
                    kept = [h for h in grp.get('hooks', [])
                            if not any(
                                re.search(r'hooks[\\/]' + re.escape(t) + r'\.(ps1|py)', h.get('command', '')) or
                                re.search(r'_hub_dispatch\.py"?\s+' + re.escape(t) + r'\b', h.get('command', ''))
                                for t in tools)]
                    removed_hooks += len(grp.get('hooks', [])) - len(kept)
                    if kept:
                        new_grp = dict(grp)
                        new_grp['hooks'] = kept
                        new_groups.append(new_grp)
                if new_groups:
                    settings['hooks'][evt] = new_groups
                else:
                    del settings['hooks'][evt]

        allow = settings.setdefault('permissions', {}).setdefault('allow', [])
        read_rule = f"Read({import_base}/**)"
        had_read_rule = read_rule in allow
        if had_read_rule:
            allow.remove(read_rule)

        if removed_hooks or had_read_rule:
            settings_path.write_text(json.dumps(settings, indent=2), encoding='utf-8', newline='\n')
            log(f"  wrote  {settings_path} (removed {removed_hooks} hook entry/entries"
                f"{', removed Read permission rule' if had_read_rule else ''})")

    # .claude\hooks\_hub_dispatch.py - tracked, shared, host-invariant content (last host only).
    dispatch_removed = False
    if is_last_host:
        dispatch_path = target_path / HUB_DISPATCH_RELPATH
        if dispatch_path.exists():
            dispatch_path.unlink()
            dispatch_removed = True
            log(f"  removed {dispatch_path}")

    # .claude\skills\<name>\ - every skill this hub scaffolded (SHARED tracked content - last host only).
    removed_skills = []
    if is_last_host:
        skills_dir = target_path / '.claude' / 'skills'
        for name in sorted(local_skill_names(consumer)):
            skill_dir = skills_dir / name
            if skill_dir.exists():
                shutil.rmtree(skill_dir)
                removed_skills.append(name)
                log(f"  removed {skill_dir}")

    # Read-only detection of shared content, for the not-last-host manual-purge checklist only
    # (design\host_scoped_disconnect_state.md Decision 2) - nothing above this line was mutated by
    # it, and it's never used to decide what the apply steps above actually did.
    detected = None if is_last_host else _detect_shared_content(target_path, consumer, config)

    write_disconnect_notes(target_path, date, mode, config['host_id'], n_imports, removed_hooks,
                            had_read_rule, removed_skills, sections_replaced, log,
                            original_registered=consumer.get('registered'), is_last_host=is_last_host,
                            hub_pointer_removed=hub_pointer_removed, dispatch_removed=dispatch_removed,
                            detected=detected)

    # claude_prose_status (design\script_action_reporting.md): derived, not separately tracked -
    # 'left-shared' when another host still depends on the tracked prose (deliberately untouched,
    # not an anomaly), 'missing' when there was no CLAUDE.md to touch at all, 'replaced' on the
    # normal success path, 'unrecognized' when is_last_host and CLAUDE.md exists but the standard
    # heading wasn't found (the hand-edited case the existing log note above already flags).
    claude_prose_status = ('left-shared' if not is_last_host else
                            'missing' if not claude_md_path.exists() else
                            'replaced' if sections_replaced else 'unrecognized')

    commit_msg = f"Tower Crane: disconnected via 'disconnect project' (mode: {mode})"
    commit_result = commit_consumer_changes(
        target_path, commit_msg, log=log, config=config,
        imports=[i['name'] for i in consumer['imported']], shared_root=SHARED_ROOT)
    commit_labels = {
        'not-a-repo': "  note   not a git repo - changes left uncommitted on disk.",
        'noop': None,
        'committed-pushed': "  [git] committed and pushed in this consumer's own repo.",
        'committed-no-remote': "  [git] committed in this consumer's own repo (no origin remote to push to).",
        'commit-failed': None,  # commit_consumer_changes() already logged the warn line itself
        'push-failed': None,
        # design\grt_connectivity_audit.md item (ii): a real divergence was auto-resolved by
        # resetting and regenerating this host's own Tower-Crane-owned values.
        'reconciled-pushed': "  [git] push conflict auto-reconciled (reset + regenerated), committed and pushed.",
    }
    label = commit_labels.get(commit_result)
    if label:
        log(label)

    result.update({
        'hub_pointer_removed': hub_pointer_removed, 'n_imports': n_imports,
        'sections_replaced': sections_replaced, 'claude_prose_status': claude_prose_status,
        'removed_hooks': removed_hooks, 'had_read_rule': had_read_rule,
        'dispatch_removed': dispatch_removed, 'removed_skills': removed_skills,
        'notes_path': str(target_path / NOTES_FILENAME), 'commit_result': commit_result,
        # Evidence over intent (design\script_action_reporting.md): re-checked fresh via git rather
        # than assumed clean from commit_result alone, since a 'noop'/'not-a-repo'/'commit-failed'
        # result can each legitimately still leave real content dirty on disk.
        'left_uncommitted': scoped_status_paths(target_path, CONSUMER_OWNED_PATHS),
    })
    return result


def disconnect_host(slug, host_id, config, mode, log, do_local_cleanup=True):
    """Core primitive: remove ONE host from ONE consumer's registry entry, optionally cleaning up
    that host's own local files (only possible/meaningful when host_id is THIS machine's own
    config['host_id']). `mode` is recorded in the local-cleanup commit message / notes file, not
    used for any registry logic.

    Returns a result dict (design\\script_action_reporting.md), not just True/False as before -
    'removed' carries the old boolean meaning (present and actually removed from the registry) for
    any caller still checking only that key; 'local' carries strip_local_references()'s own result
    dict when do_local_cleanup ran, else None; 'skip_reason' names why nothing happened when
    'removed' is False. A caller that only inspects `result['removed']` (or ignores the return value
    entirely, as remove_hub.py's loop does today) keeps working unchanged - this is purely additive
    over the boolean the old return value carried."""
    base = {'slug': slug, 'host_id': host_id, 'removed': False, 'local': None,
            'do_local_cleanup': do_local_cleanup, 'skip_reason': None, 'hosts_left': None}
    registry_path = CONSUMERS_DIR / f"{slug}.md"
    if not registry_path.exists():
        log(f"  skip   no registry entry for '{slug}' - nothing to disconnect.")
        base['skip_reason'] = 'no-registry'
        return base
    consumer = registry_lib.parse_registry(registry_path)
    if consumer is None:
        log(f"  skip   {registry_path} isn't parseable - fix it by hand first.")
        base['skip_reason'] = 'not-parseable'
        return base
    if host_id not in consumer['hosts']:
        log(f"  skip   '{slug}' has no hosts.{host_id} entry - already disconnected there.")
        base['skip_reason'] = 'not-connected'
        return base

    # design\consumer_reference_indirection.md's host-count-aware split: computed BEFORE removal
    # (host_id is confirmed present above) since strip_local_references() needs to know, for a
    # multi_machine consumer, whether any OTHER host will still depend on the shared tracked
    # content it's deciding whether to strip.
    is_last_host = len(consumer['hosts']) == 1

    if do_local_cleanup:
        base['local'] = strip_local_references(consumer['hosts'][host_id]['path'], consumer, config,
                                                 mode, log, is_last_host=is_last_host)
    else:
        log(f"  note   registry-only: this machine can't reach '{host_id}''s files at "
            f"{consumer['hosts'][host_id]['path']} - clean up its @import lines/settings.json/"
            f".claude\\skills\\ there directly (or run this same command from that machine).")
        base['skip_reason'] = 'remote-registry-only'

    raw = registry_path.read_text(encoding='utf-8')
    new_raw, was_present, host_count_after = registry_lib.remove_host_from_text(raw, host_id)
    if not was_present:
        return base
    base['removed'] = True
    base['hosts_left'] = host_count_after
    if host_count_after == 0:
        registry_path.unlink()
        log(f"  removed {registry_path} (last host disconnected - git history is the record)")
    else:
        registry_path.write_text(new_raw, encoding='utf-8', newline='\n')
        floor_note = ", scope -> local (below 2-host floor)" if host_count_after < 2 else ""
        log(f"  wrote  {registry_path} (removed hosts.{host_id}, {host_count_after} host(s) left{floor_note})")
    return base


_COMMIT_RESULT_LABELS = {
    'not-a-repo': "not a git repo",
    'noop': "nothing to commit",
    'committed-pushed': "committed and pushed",
    'committed-no-remote': "committed (no origin remote to push to)",
    'commit-failed': "commit FAILED - see warning above",
    'push-failed': "committed locally, push FAILED - see warning above",
    'reconciled-pushed': "push conflict auto-reconciled, committed and pushed",
}


def _print_host_summary(host_result):
    """One host's block within the close-out summary (design\\script_action_reporting.md) -
    entirely sourced from disconnect_host()'s/strip_local_references()'s own already-computed
    result dicts, nothing re-derived."""
    host_id = host_result['host_id']
    if not host_result['removed']:
        reason = {
            'no-registry': "no registry entry", 'not-parseable': "registry entry not parseable",
            'not-connected': "already had no hosts.<host> entry",
            'remote-registry-only': "registry-only (not this machine - local files untouched here)",
        }.get(host_result['skip_reason'], host_result['skip_reason'] or "unknown")
        print(f"{host_id}: not removed ({reason})")
        return
    hosts_left_note = f", {host_result['hosts_left']} host(s) left in the registry" if host_result['hosts_left'] is not None else ""
    print(f"{host_id}: removed from the registry{hosts_left_note}")
    local = host_result['local']
    if local is None:
        return  # remote-registry-only - nothing local to report
    if local['target_missing']:
        print(f"  local path no longer exists on disk ({local['target_path']}) - nothing local to clean up")
        return
    prose_labels = {
        'replaced': "CLAUDE.md prose replaced with disconnected-pointer",
        'left-shared': "CLAUDE.md prose left in place (another host still depends on it)",
        'missing': "no CLAUDE.md present to touch",
        'unrecognized': "CLAUDE.md prose NOT replaced - standard heading not found (hand-edited?)",
    }
    parts = [f"{local['n_imports']} @import line(s) removed", prose_labels[local['claude_prose_status']]]
    if local['hub_pointer_removed']:
        parts.append("hub_pointer.md removed")
    if local['removed_hooks'] or local['had_read_rule']:
        detail = []
        if local['removed_hooks']:
            detail.append(f"{local['removed_hooks']} hook entry/entries")
        if local['had_read_rule']:
            detail.append("Read permission rule")
        parts.append(f"{' and '.join(detail)} removed from settings.json")
    if local['dispatch_removed']:
        parts.append("_hub_dispatch.py removed")
    if local['removed_skills']:
        parts.append(f"skills removed: {', '.join(sorted(local['removed_skills']))}")
    print(f"  local cleanup: {'; '.join(parts)}")
    print(f"  notes file: {local['notes_path']}")
    commit_label = _COMMIT_RESULT_LABELS.get(local['commit_result'], local['commit_result'])
    print(f"  committed to this consumer's own repo: {commit_label}")
    if local['left_uncommitted']:
        print(f"  left uncommitted: {', '.join(local['left_uncommitted'])}")


def print_close_out_summary(slug, mode, host_results, registry_commit_result):
    """Close-out block, printed once at the very end of the run (design\\
    script_action_reporting.md) - entirely built from the result dicts disconnect_host()/
    strip_local_references() already computed and returned, never a second re-derivation of what
    happened. Extends the same shape new_consumer.py's own close-out summary uses, adapted for the
    one real structural difference here: a single run can touch several hosts at once, each landing
    in a genuinely different outcome, so this reports one block per host instead of one block total."""
    print()
    print(f"=== {slug}: disconnect project summary ===")
    print(f"Mode: {mode} (target host(s): {', '.join(r['host_id'] for r in host_results)})")
    for host_result in host_results:
        _print_host_summary(host_result)
    if registry_commit_result is not None:
        label = _COMMIT_RESULT_LABELS.get(registry_commit_result, registry_commit_result)
        print(f"Registered in the hub's own registry: {label}.")


def main():
    parser = argparse.ArgumentParser(description="Disconnect a consumer from Tower Crane (design\\connect_disconnect.md).")
    parser.add_argument('--slug', required=True, help="Registry slug (consumers\\<slug>.md).")
    parser.add_argument('--mode', required=True, choices=['this-only', 'all-but-this', 'all'],
                         help="this-only: disconnect just this machine. all-but-this: disconnect every "
                              "OTHER machine, keep this one. all: disconnect everywhere.")
    args = parser.parse_args()

    config = get_shared_config(SHARED_ROOT)
    this_host = config['host_id']

    registry_path = CONSUMERS_DIR / f"{args.slug}.md"
    if not registry_path.exists():
        print_diagnose_inline(config, slug=args.slug)
        raise SystemExit(f"No registry entry for '{args.slug}' at {registry_path}. See "
                          "toolkit\\troubleshoot_project_connection.md if the project's CLAUDE.md "
                          "still looks like it's connected.")
    consumer = registry_lib.parse_registry(registry_path)
    if consumer is None:
        print_diagnose_inline(config, slug=args.slug)
        raise SystemExit(f"{registry_path} isn't parseable. See "
                          "toolkit\\troubleshoot_project_connection.md.")

    if args.mode in ('this-only', 'all-but-this') and this_host not in consumer['hosts']:
        print_diagnose_inline(config, slug=args.slug)
        raise SystemExit(f"'{args.slug}' has no hosts.{this_host} entry on this machine - "
                          f"'{args.mode}' requires this machine to be connected. Known hosts: "
                          f"{', '.join(consumer['hosts']) or '(none)'}. See "
                          "toolkit\\troubleshoot_project_connection.md if that looks wrong.")

    if args.mode == 'this-only':
        targets = [this_host]
    elif args.mode == 'all-but-this':
        targets = [h for h in consumer['hosts'] if h != this_host]
    else:
        targets = list(consumer['hosts'])

    if not targets:
        print(f"Nothing to do for '{args.slug}' under mode '{args.mode}'.")
        return

    # design\consumer_reference_indirection.md: disconnect_host() computes its own
    # is_last_host from the registry's LIVE state at call time (never from this loop's
    # precomputed target set), so this-host's own removal must run LAST under mode 'all' -
    # otherwise it would see other still-present hosts.<host> entries and wrongly conclude shared
    # tracked content should be left in place, even though every host is being removed this run.
    if args.mode == 'all' and this_host in targets:
        targets = [h for h in targets if h != this_host] + [this_host]

    print(f"Disconnecting '{args.slug}' (mode: {args.mode}) - target host(s): {', '.join(targets)}")
    any_removed = False
    host_results = []
    for host_id in targets:
        host_result = disconnect_host(args.slug, host_id, config, args.mode, print,
                                       do_local_cleanup=(host_id == this_host))
        host_results.append(host_result)
        if host_result['removed']:
            any_removed = True

    # design\grt_connectivity_audit.md item (i): commit the registry change into the outer hub
    # repo itself, now, not left for a later optional `checkpoint` - the registry is
    # functionality-critical state (every host's own resume / check_tower_crane.py reads it for a
    # correct answer), not user work-in-progress. `git add` on a since-hard-deleted registry file
    # (0 hosts left) stages the deletion correctly, so this covers that case too.
    registry_commit_result = None
    if any_removed:
        registry_commit_msg = (
            f"Registry: disconnect '{args.slug}' (mode: {args.mode}, host(s): {', '.join(targets)})")
        registry_commit_result = commit_hub_changes(
            PROJECT_ROOT, [f"consumers/{args.slug}.md"], registry_commit_msg, log=print)
        registry_commit_labels = {
            'committed-pushed': f"  [git] consumers/{args.slug}.md committed and pushed in tower_crane's own outer repo.",
            'committed-no-remote': f"  [git] consumers/{args.slug}.md committed in tower_crane's own outer repo (no origin remote to push to).",
        }
        label = registry_commit_labels.get(registry_commit_result)
        if label:
            print(label)

    print_close_out_summary(args.slug, args.mode, host_results, registry_commit_result)


if __name__ == '__main__':
    main()
