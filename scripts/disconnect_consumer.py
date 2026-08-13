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
    commit_consumer_changes, get_shared_config, print_diagnose_inline,
    TC_IN_USE_HEADING, WORKFLOW_HEADING, DISCONNECTED_HEADING,
    DISCONNECT_NOTES_FILENAME as NOTES_FILENAME,
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


def write_disconnect_notes(target_path, date, mode, host_id, n_imports, removed_hooks,
                            had_read_rule, removed_skills, sections_replaced, log):
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
    if not removed_lines:
        removed_lines.append("- (nothing local was present to remove - this host's connection "
                              "existed only in the registry.)")

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
    else:
        cross_ref = (f"`CLAUDE.md` does **not** carry a pointer to this file - its "
                      f"`{TC_IN_USE_HEADING}`/`{WORKFLOW_HEADING}` sections weren't found in "
                      f"their standard scaffolded shape (likely hand-edited), so they were left "
                      f"untouched rather than guessed at. This file is therefore the only place "
                      f"this disconnect is recorded at a glance - check `CLAUDE.md` by hand too.")

    text = (
        f"# Tower Crane — Disconnect Notes\n\n"
        f"Generated automatically by `disconnect_consumer.py` on {date} (mode: {mode}, host: "
        f"`{host_id}`). This file is meant to be the complete index of every trace Tower Crane "
        f"left behind in this project after disconnecting — read this file alone and you "
        f"have the full picture; nothing else needs following to find more.\n\n"
        f"## Removed by this disconnect\n\n"
        + "\n".join(removed_lines) + "\n\n"
        f"## Left behind deliberately (not touched by this command)\n\n"
        + "\n".join(left_lines) + "\n\n"
        f"## Cross-reference\n\n"
        f"{cross_ref}\n\n"
        f"## If you want a clean break\n\n"
        f"None of the above is deleted automatically. To fully purge Tower Crane from this "
        f"project:\n"
        f"- Delete this file and the `{DISCONNECTED_HEADING}` section in `CLAUDE.md` (if "
        f"present).\n"
        f"- Remove `shared_resources/` / `COMPLIANCE_GUIDANCE.md` if present and no longer "
        f"wanted.\n"
        f"- Rewriting git history to remove old Tower Crane commits is a manual, destructive git "
        f"operation - not something this command does. Ask Claude Code in this project directly "
        f"if you want help with that.\n\n"
        f"Reconnecting later: run `\"connect project\"` again from the Tower Crane hub.\n"
    )
    notes_path = target_path / NOTES_FILENAME
    notes_path.write_text(text, encoding='utf-8', newline='\n')
    log(f"  wrote  {notes_path}")


def strip_local_references(target_path, consumer, config, mode, log):
    """Undo what new_consumer.py wrote at target_path for THIS hub connection: strip @import
    lines and replace the now-inaccurate 'Tower Crane In Use'/'Shared Workflow Protocol' prose
    with a short honest pointer, strip hook/permission entries and scaffolded skill dirs, write
    TOWER_CRANE_DISCONNECT_NOTES.md as the single complete breadcrumb index, then commit
    everything in the consumer's own repo (commit_consumer_changes()) so nothing is left
    uncommitted/unexplained - the gap a live 2026-08-12 test found (design\\connect_disconnect.md).
    Never touches project_progress.md or FIRST_RUN.md - those are the consumer's own content."""
    target_path = Path(target_path)
    if not target_path.exists():
        log(f"  note   {target_path} no longer exists on disk - nothing local to clean up.")
        return

    date = datetime.date.today().isoformat()
    import_base = str(config['import_base'])

    # CLAUDE.md: strip every @{import_base}/... line, then replace the prose sections.
    claude_md_path = target_path / 'CLAUDE.md'
    n_imports = 0
    sections_replaced = False
    if claude_md_path.exists():
        text = claude_md_path.read_text(encoding='utf-8')
        escaped_base = re.escape(import_base)
        text, n_imports = re.subn(rf'(?m)^@{escaped_base}/\S+\.md\s*\r?\n?', '', text)
        text, sections_replaced = replace_prose_sections(text, date, mode)
        if n_imports or sections_replaced:
            claude_md_path.write_text(text, encoding='utf-8', newline='\n')
            log(f"  wrote  {claude_md_path} (removed {n_imports} @import line(s)"
                f"{', replaced Tower Crane prose sections' if sections_replaced else ''})")
        if not sections_replaced:
            log(f"  note   {claude_md_path} doesn't contain the standard '{TC_IN_USE_HEADING}' "
                f"section (hand-edited?) - prose left untouched, clean up manually if desired.")

    # settings.json: strip this hub's hook entries + the Read(import_base/**) permission rule.
    settings_path = target_path / '.claude' / 'settings.json'
    removed_hooks = 0
    had_read_rule = False
    if settings_path.exists():
        settings = json.loads(settings_path.read_text(encoding='utf-8'))
        tools = [o['name'] for o in consumer['opted_in']] + [o['name'] for o in consumer['private_opted_in']]
        for evt, groups in list(settings.get('hooks', {}).items()):
            new_groups = []
            for grp in groups:
                kept = [h for h in grp.get('hooks', [])
                        if not any(re.search(r'hooks[\\/]' + re.escape(t) + r'\.(ps1|py)', h.get('command', ''))
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

    # .claude\skills\<name>\ - every skill this hub scaffolded.
    skills_dir = target_path / '.claude' / 'skills'
    removed_skills = []
    for name in sorted(local_skill_names(consumer)):
        skill_dir = skills_dir / name
        if skill_dir.exists():
            shutil.rmtree(skill_dir)
            removed_skills.append(name)
            log(f"  removed {skill_dir}")

    write_disconnect_notes(target_path, date, mode, config['host_id'], n_imports, removed_hooks,
                            had_read_rule, removed_skills, sections_replaced, log)

    commit_msg = f"Tower Crane: disconnected via 'disconnect project' (mode: {mode})"
    result = commit_consumer_changes(target_path, commit_msg, log=log)
    commit_labels = {
        'not-a-repo': "  note   not a git repo - changes left uncommitted on disk.",
        'noop': None,
        'committed-pushed': "  [git] committed and pushed in this consumer's own repo.",
        'committed-no-remote': "  [git] committed in this consumer's own repo (no origin remote to push to).",
        'commit-failed': None,  # commit_consumer_changes() already logged the warn line itself
        'push-failed': None,
    }
    label = commit_labels.get(result)
    if label:
        log(label)


def disconnect_host(slug, host_id, config, mode, log, do_local_cleanup=True):
    """Core primitive: remove ONE host from ONE consumer's registry entry, optionally cleaning up
    that host's own local files (only possible/meaningful when host_id is THIS machine's own
    config['host_id']). `mode` is recorded in the local-cleanup commit message / notes file, not
    used for any registry logic. Returns True if the host was actually present and removed."""
    registry_path = CONSUMERS_DIR / f"{slug}.md"
    if not registry_path.exists():
        log(f"  skip   no registry entry for '{slug}' - nothing to disconnect.")
        return False
    consumer = registry_lib.parse_registry(registry_path)
    if consumer is None:
        log(f"  skip   {registry_path} isn't parseable - fix it by hand first.")
        return False
    if host_id not in consumer['hosts']:
        log(f"  skip   '{slug}' has no hosts.{host_id} entry - already disconnected there.")
        return False

    if do_local_cleanup:
        strip_local_references(consumer['hosts'][host_id]['path'], consumer, config, mode, log)
    else:
        log(f"  note   registry-only: this machine can't reach '{host_id}''s files at "
            f"{consumer['hosts'][host_id]['path']} - clean up its @import lines/settings.json/"
            f".claude\\skills\\ there directly (or run this same command from that machine).")

    raw = registry_path.read_text(encoding='utf-8')
    new_raw, was_present, host_count_after = registry_lib.remove_host_from_text(raw, host_id)
    if not was_present:
        return False
    if host_count_after == 0:
        registry_path.unlink()
        log(f"  removed {registry_path} (last host disconnected - git history is the record)")
    else:
        registry_path.write_text(new_raw, encoding='utf-8', newline='\n')
        floor_note = ", scope -> local (below 2-host floor)" if host_count_after < 2 else ""
        log(f"  wrote  {registry_path} (removed hosts.{host_id}, {host_count_after} host(s) left{floor_note})")
    return True


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

    print(f"Disconnecting '{args.slug}' (mode: {args.mode}) - target host(s): {', '.join(targets)}")
    for host_id in targets:
        disconnect_host(args.slug, host_id, config, args.mode, print, do_local_cleanup=(host_id == this_host))


if __name__ == '__main__':
    main()
