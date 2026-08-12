#!/usr/bin/env python3
"""
disconnect_consumer.py - reverse of new_consumer.py's host-connect: removes a host's connection to
a registered consumer (design\\disconnect.md).

Three modes (--mode):
  this-only     - remove only the current machine's connection to this consumer.
  all-but-this  - remove every OTHER host's connection, leaving only this machine.
  all           - remove every host's connection (full disconnect).

For each host being removed:
  - If it's THIS machine (config['host_id']), the consumer's own local files at its registered
    path are cleaned up too: this hub's @import lines are stripped from CLAUDE.md, this hub's
    hook entries and the Read(import_base/**) permission rule are stripped from
    .claude\\settings.json, and every .claude\\skills\\<name>\\ directory this hub scaffolded is
    removed. project_progress.md and FIRST_RUN.md are never touched - they're the consumer's own
    content, not Tower Crane's.
  - If it's a DIFFERENT host, only the registry side can be touched from here - this machine has
    no filesystem access to another machine's files. Printed plainly, not silently skipped.

Registry side: each removed host's hosts.<host_id> entry is deleted. If 0 hosts remain, the whole
consumers\\<slug>.md file is hard-deleted (git history is the record - no archive/marker, matching
the project's existing "no version tags/changelog" precedent, Reverts decision). If exactly 1 host
remains, scope auto-reverts to `local` (registry_lib.remove_host_from_text's floor-in-reverse).

Deliberately NOT touched by this first build (flagged in the output, not silently dropped): any
adopted shared_resources\\ stub (its hub-rel: marker just goes stale) and COMPLIANCE_GUIDANCE.md's
broadcast section - a real scope decision left for a later pass if it turns out to matter in
practice.

Reused by remove_hub.py (this-only, looped across every consumer connected on this machine) - see
that script for the "reverse setup_machine.md entirely" case.
"""

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config_lib import get_shared_config
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


def strip_local_references(target_path, consumer, config, log):
    """Undo what new_consumer.py wrote at target_path for THIS hub connection. Never touches
    project_progress.md or FIRST_RUN.md - those are the consumer's own content."""
    target_path = Path(target_path)
    if not target_path.exists():
        log(f"  note   {target_path} no longer exists on disk - nothing local to clean up.")
        return

    import_base = str(config['import_base'])

    # CLAUDE.md: strip every @{import_base}/... line (protocol-piece imports this hub added).
    claude_md_path = target_path / 'CLAUDE.md'
    if claude_md_path.exists():
        text = claude_md_path.read_text(encoding='utf-8')
        escaped_base = re.escape(import_base)
        new_text, n = re.subn(rf'(?m)^@{escaped_base}/\S+\.md\s*\r?\n?', '', text)
        if n:
            claude_md_path.write_text(new_text, encoding='utf-8', newline='\n')
            log(f"  wrote  {claude_md_path} (removed {n} @import line(s))")

    # settings.json: strip this hub's hook entries + the Read(import_base/**) permission rule.
    settings_path = target_path / '.claude' / 'settings.json'
    if settings_path.exists():
        settings = json.loads(settings_path.read_text(encoding='utf-8'))
        tools = [o['name'] for o in consumer['opted_in']] + [o['name'] for o in consumer['private_opted_in']]
        removed_hooks = 0
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
    for name in sorted(local_skill_names(consumer)):
        skill_dir = skills_dir / name
        if skill_dir.exists():
            shutil.rmtree(skill_dir)
            log(f"  removed {skill_dir}")

    log("  note   left untouched (not this hub's to delete): project_progress.md, FIRST_RUN.md, "
        "any shared_resources\\ adopted stub (hub-rel: marker will just go stale), and any "
        "COMPLIANCE_GUIDANCE.md broadcast section.")


def disconnect_host(slug, host_id, config, log, do_local_cleanup=True):
    """Core primitive: remove ONE host from ONE consumer's registry entry, optionally cleaning up
    that host's own local files (only possible/meaningful when host_id is THIS machine's own
    config['host_id']). Returns True if the host was actually present and removed."""
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
        strip_local_references(consumer['hosts'][host_id]['path'], consumer, config, log)
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
    parser = argparse.ArgumentParser(description="Disconnect a consumer from Tower Crane (design\\disconnect.md).")
    parser.add_argument('--slug', required=True, help="Registry slug (consumers\\<slug>.md).")
    parser.add_argument('--mode', required=True, choices=['this-only', 'all-but-this', 'all'],
                         help="this-only: disconnect just this machine. all-but-this: disconnect every "
                              "OTHER machine, keep this one. all: disconnect everywhere.")
    args = parser.parse_args()

    config = get_shared_config(SHARED_ROOT)
    this_host = config['host_id']

    registry_path = CONSUMERS_DIR / f"{args.slug}.md"
    if not registry_path.exists():
        raise SystemExit(f"No registry entry for '{args.slug}' at {registry_path}.")
    consumer = registry_lib.parse_registry(registry_path)
    if consumer is None:
        raise SystemExit(f"{registry_path} isn't parseable.")

    if args.mode in ('this-only', 'all-but-this') and this_host not in consumer['hosts']:
        raise SystemExit(f"'{args.slug}' has no hosts.{this_host} entry on this machine - "
                          f"'{args.mode}' requires this machine to be connected. Known hosts: "
                          f"{', '.join(consumer['hosts']) or '(none)'}")

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
        disconnect_host(args.slug, host_id, config, print, do_local_cleanup=(host_id == this_host))


if __name__ == '__main__':
    main()
