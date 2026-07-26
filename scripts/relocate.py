#!/usr/bin/env python3
"""
relocate.py - regenerate every registered consumer's hook command(s) from config.local.json,
the "config -> regenerate" action of the portability foundation (design\\portability.md).

Reads config.local.json, walks the consumer registry (consumers/*.md), and for each consumer
that lives on THIS machine rewrites the hook command in its .claude/settings.json to the concrete
command computed from config (python launcher + shared_root path + hooks/<tool>.py). shared_root
itself is always the live, current location (config_lib.py never trusts a stale stored value), so
this is the one-run fix that brings every consumer's ALREADY-BAKED hook command/@import lines back
in sync after this repo moved or was renamed - config_lib.py notices that automatically and points
here; this script is what actually pushes the fix out to consumers. Also the path that migrates a
consumer from the old PowerShell hook (hooks/<tool>.ps1) to the pure-Python hook (hooks/<tool>.py).

It rewrites ONLY the command string of hooks that reference an opted-in tool's hook file
(hooks/<tool>.ps1 or .py). It never adds, removes, or reorders unrelated settings/hooks. On the
current machine with an already-current settings.json it is a no-op.

Cross-repo note: this writes into each consumer's OWN repo working tree (it does not commit). The
consumer's next session verifies the hook still fires and commits - the change-request round-trip
(a behavior-changing edit to a live consumer). Run --dry-run first to preview.

OS-reach Tier 2 port of relocate.ps1 (design\\portability.md, "OS-reach Tier 2: full
cross-platform design"). Logic is a direct translation - see that doc's Build order for the
parity-check approach used to verify this against the original.
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config_lib import get_shared_config, get_expanded_optin

SHARED_ROOT = Path(__file__).resolve().parent.parent
OPTINS_DIR = SHARED_ROOT / 'templates' / 'optins'
CONSUMERS_DIR = SHARED_ROOT / 'consumers'

COUNTS = {'changed': 0, 'noop': 0, 'skipped': 0, 'warn': 0}


def write_utf8(path, content):
    # Python's utf-8 encoding never writes a BOM (unlike PS 5.1's -Encoding utf8); newline='\n'
    # keeps embedded '\n' as LF instead of Windows-translating it to CRLF on write.
    path.write_text(content, encoding='utf-8', newline='\n')


# Minimal registry reader - just the fields relocate needs (name, path, host, opted-in tools).
def read_registry_entry(path):
    raw = path.read_text(encoding='utf-8')
    m = re.search(r'```yaml\s*\r?\n(.*?)\r?\n```', raw, re.DOTALL)
    if not m:
        return None
    obj = {'name': None, 'path': None, 'host': None, 'tools': []}
    section = None
    for line in re.split(r'\r?\n', m.group(1)):
        m1 = re.match(r'^name:\s*(.+?)\s*$', line)
        if m1:
            obj['name'] = m1.group(1)
            section = None
            continue
        m1 = re.match(r'^path:\s*(.+?)\s*$', line)
        if m1:
            obj['path'] = m1.group(1)
            section = None
            continue
        m1 = re.match(r'^host:\s*(.+?)\s*$', line)
        if m1:
            obj['host'] = m1.group(1)
            section = None
            continue
        if re.match(r'^opted_in:\s*\[\s*\]\s*$', line):
            section = None
            continue
        if re.match(r'^opted_in:\s*$', line):
            section = 'opted_in'
            continue
        if re.match(r'^(imported|registered|owner):', line):
            section = None
            continue
        if section == 'opted_in':
            m1 = re.match(r'^\s*-\s*tool:\s*(.+?)\s*$', line)
            if m1:
                obj['tools'].append(m1.group(1))
                continue
    return obj


def main():
    parser = argparse.ArgumentParser(
        description="Regenerate every registered consumer's hook command(s) from config.local.json."
    )
    parser.add_argument('--consumer', default=None, help="Slug of a single consumer to scope to (e.g. geo_rank_tracker). Default: all.")
    parser.add_argument('--dry-run', action='store_true', help="Show what would change without writing anything.")
    args = parser.parse_args()

    config = get_shared_config(SHARED_ROOT)
    this_host = str(config.get('host_id', ''))

    print("=== relocate.py ===")
    print(f"shared_root : {config['shared_root']}")
    print(f"launcher    : {config['python_launcher']}")
    print(f"this host   : {this_host}")
    if args.dry_run:
        print("MODE        : DRY RUN (no files written)")

    files = sorted(CONSUMERS_DIR.glob('*.md')) if CONSUMERS_DIR.is_dir() else []
    if args.consumer:
        files = [f for f in files if f.stem == args.consumer]
    if not files:
        if args.consumer:
            raise SystemExit(f"No registry entry for consumer '{args.consumer}' (consumers/{args.consumer}.md).")
        print("No consumer registry entries found.")
        return

    for f in files:
        c = read_registry_entry(f)
        if c is None:
            print(f"  [warn] {f.name}: no parseable yaml block - skipping.")
            COUNTS['warn'] += 1
            continue

        print()
        print(f"Consumer: {c['name']} ({f.stem})")

        # Federate (#1): only regenerate consumers that live on this machine.
        if c['host'] and c['host'] != this_host:
            print(f"  [skip] registered on host '{c['host']}', not this machine ('{this_host}').")
            COUNTS['skipped'] += 1
            continue
        if not c['path'] or not Path(c['path']).exists():
            print(f"  [warn] path not found on disk: {c['path']}")
            COUNTS['warn'] += 1
            continue
        if not c['tools']:
            print("  [no-op] no opted-in tools (prose-only consumer).")
            COUNTS['noop'] += 1
            continue

        settings_path = Path(c['path']) / '.claude' / 'settings.json'
        if not settings_path.exists():
            print("  [warn] no .claude/settings.json but registry lists opted-in tool(s).")
            COUNTS['warn'] += 1
            continue

        try:
            settings = json.loads(settings_path.read_text(encoding='utf-8'))
        except json.JSONDecodeError:
            print("  [warn] settings.json is not valid JSON - skipping.")
            COUNTS['warn'] += 1
            continue

        # Build tool -> new concrete command map from the canonical opt-ins.
        new_cmd = {}
        for t in c['tools']:
            optin_path = OPTINS_DIR / f"{t}.json"
            if not optin_path.exists():
                print(f"  [warn] no canonical opt-in for '{t}' - skipping that tool.")
                COUNTS['warn'] += 1
                continue
            optin = get_expanded_optin(optin_path, config)
            for evt, groups in optin.get('hooks', {}).items():
                for grp in groups:
                    for h in grp.get('hooks', []):
                        if 'command' in h:
                            new_cmd[t] = h['command']

        # Walk the consumer's hooks; rewrite any command that references an opted-in tool's hook
        # file (hooks/<tool>.ps1 or .py) to that tool's new command. This handles both path
        # relocation and the .ps1 -> .py migration in one motion.
        changed_here = False
        for evt, groups in settings.get('hooks', {}).items():
            for grp in groups:
                for h in grp.get('hooks', []):
                    if 'command' not in h:
                        continue
                    for t in c['tools']:
                        if t not in new_cmd:
                            continue
                        pattern = r'hooks[\\/]' + re.escape(t) + r'\.(ps1|py)'
                        if re.search(pattern, h['command']) and h['command'] != new_cmd[t]:
                            verb = 'would change' if args.dry_run else 'change'
                            print(f"  [{verb}] {t}")
                            print(f"      from: {h['command']}")
                            print(f"      to:   {new_cmd[t]}")
                            h['command'] = new_cmd[t]
                            changed_here = True

        if changed_here:
            if args.dry_run:
                print("  (dry run - not written)")
            else:
                write_utf8(settings_path, json.dumps(settings, indent=2))
                print(f"  wrote {settings_path}")
            COUNTS['changed'] += 1
        else:
            print("  [no-op] settings already current.")
            COUNTS['noop'] += 1

    print()
    print(f"=== Summary: {COUNTS['changed']} changed, {COUNTS['noop']} no-op, {COUNTS['skipped']} off-host, {COUNTS['warn']} warning(s) ===")


if __name__ == '__main__':
    main()
