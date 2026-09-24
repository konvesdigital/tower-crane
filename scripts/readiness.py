#!/usr/bin/env python3
"""
readiness.py - read-only report of what a connected project still needs on this machine.

  python readiness.py --project-root <path> [--all]
  python readiness.py --hub [--all]

Statuses: OK, TODO, NOTE, UNKNOWN, HUB-MISMATCH. Without --all, only non-OK lines print.
Never writes, never touches the network.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config_lib import (get_shared_config, parse_hub_pointer, scoped_status_paths,
                        CONSUMER_OWNED_PATHS, FIRST_RUN_FILENAME)
from registry_lib import parse_registry

SHARED_ROOT = Path(__file__).resolve().parent.parent
PLACEHOLDER_MARKER = '<!-- FIRST_RUN:'
CLAUDE_STATE_PATH = Path(os.path.expanduser('~')) / '.claude.json'


def _norm(p):
    return os.path.normcase(os.path.normpath(os.path.expanduser(str(p))))


def _claude_project_state(project_root):
    try:
        data = json.loads(CLAUDE_STATE_PATH.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    target = _norm(project_root)
    for key, val in (data.get('projects') or {}).items():
        if _norm(key) == target and isinstance(val, dict):
            return val
    return None


def _registry_entry_for(consumers_dir, host_id, project_root):
    target = _norm(project_root)
    for f in sorted(Path(consumers_dir).glob('*.md')):
        c = parse_registry(f)
        if not c:
            continue
        h = c['hosts'].get(host_id)
        if h and h.get('path') and _norm(h['path']) == target:
            return c
    return None


def registry_slug_for(project_root):
    """consumers/<slug>.md stem registering project_root on this host, or None."""
    host_id = get_shared_config(SHARED_ROOT).get('host_id')
    entry = _registry_entry_for(SHARED_ROOT.parent / 'consumers', host_id, project_root)
    return Path(entry['file']).stem if entry else None


def check(project_root):
    """List of (status, item, detail) for one project on this machine."""
    root = Path(project_root)
    out = []

    pointer = parse_hub_pointer(root / '.claude' / 'hub_pointer.md')
    if pointer is None:
        out.append(('TODO', 'hub pointer',
                    "no .claude/hub_pointer.md - Tower Crane isn't active for this project on this "
                    "machine; run `connect project` from the hub"))
        return out
    shared_root = Path(os.path.expanduser(pointer['shared_root'] or ''))
    if not (shared_root / 'config.local.json').exists():
        out.append(('TODO', 'hub pointer',
                    f"shared_root '{pointer['shared_root']}' has no config.local.json - hub moved "
                    "or not set up; run `connect project` from the hub"))
        return out
    out.append(('OK', 'hub pointer', str(shared_root)))

    host_id = get_shared_config(shared_root).get('host_id')
    entry = _registry_entry_for(shared_root.parent / 'consumers', host_id, root)
    if entry is None:
        out.append(('HUB-MISMATCH', 'registry',
                    f"no consumers/ entry lists host '{host_id}' at this path - run `connect "
                    "project` from the hub"))
    else:
        out.append(('OK', 'registry', f"{entry['name']} on {host_id}"))

    if not (root / '.git').exists():
        out.append(('TODO', 'git', "no .git - `git init` (or finish cloning), then commit"))
    else:
        out.append(('OK', 'git', 'repo present'))
        r = subprocess.run(['git', '-C', str(root), 'remote', 'get-url', 'origin'],
                           capture_output=True, text=True)
        if r.returncode != 0 or not r.stdout.strip():
            out.append(('NOTE', 'git remote', "no origin remote - optional, for off-machine backup"))
        else:
            out.append(('OK', 'git remote', r.stdout.strip()))
        dirty = scoped_status_paths(root, list(CONSUMER_OWNED_PATHS))
        if dirty:
            out.append(('TODO', 'setup committed',
                        f"uncommitted Tower Crane setup files: {', '.join(dirty)} - commit them "
                        "(`checkpoint`)"))
        else:
            out.append(('OK', 'setup committed', 'clean'))

    state = _claude_project_state(root)
    if state is None:
        out.append(('UNKNOWN', 'Claude Code approvals',
                    "no record of this folder in ~/.claude.json - on first launch, accept the "
                    "folder-trust prompt and the CLAUDE.md import-approval dialog"))
    else:
        trust = state.get('hasTrustDialogAccepted')
        if trust is True:
            out.append(('OK', 'folder trust', 'accepted'))
        elif trust is False:
            out.append(('TODO', 'folder trust', "not accepted - accept the trust prompt on next launch"))
        else:
            out.append(('UNKNOWN', 'folder trust', "no hasTrustDialogAccepted key - accept if prompted"))
        approved = state.get('hasClaudeMdExternalIncludesApproved')
        shown = state.get('hasClaudeMdExternalIncludesWarningShown')
        if approved is True:
            out.append(('OK', 'import approval', 'approved'))
        elif approved is False and shown is True:
            out.append(('TODO', 'import approval',
                        "CLAUDE.md external imports were declined - the shared protocol won't "
                        "load until they're approved"))
        elif approved is False:
            out.append(('TODO', 'import approval',
                        "not yet approved - accept the CLAUDE.md import-approval dialog on next launch"))
        else:
            out.append(('UNKNOWN', 'import approval',
                        "no hasClaudeMdExternalIncludesApproved key - accept the dialog if prompted"))

    unfilled = [n for n in ('CLAUDE.md', 'README.md')
                if (root / n).exists()
                and PLACEHOLDER_MARKER in (root / n).read_text(encoding='utf-8', errors='replace')]
    if unfilled:
        out.append(('TODO', 'overview',
                    f"placeholder not yet filled in: {', '.join(unfilled)} (the `<!-- FIRST_RUN:` "
                    "block)"))
    else:
        out.append(('OK', 'overview', 'filled in'))

    if (root / FIRST_RUN_FILENAME).exists():
        out.append(('TODO', 'legacy FIRST_RUN.md',
                    "superseded by this check - delete it once the items above are resolved"))

    return out


def hub_check():
    """{project_name: [(status, item, detail), ...]} for every consumer registered on this host."""
    cfg = get_shared_config(SHARED_ROOT)
    host_id = cfg.get('host_id')
    results = {}
    for f in sorted((SHARED_ROOT.parent / 'consumers').glob('*.md')):
        c = parse_registry(f)
        if not c or host_id not in c['hosts']:
            continue
        path = c['hosts'][host_id].get('path')
        if not path or not Path(path).exists():
            results[c['name']] = [('HUB-MISMATCH', 'registry',
                                   f"registered on '{host_id}' at '{path}', which doesn't exist - "
                                   "`connect project` (moved) or `disconnect project` (gone)")]
            continue
        results[c['name']] = check(path)
    return results


def format_lines(lines, show_all=False, indent=''):
    return [f"{indent}[{s}] {item}: {detail}" for s, item, detail in lines
            if show_all or s != 'OK']


def main():
    parser = argparse.ArgumentParser(description="Read-only readiness report for connected projects.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--project-root', help="One project's root folder.")
    group.add_argument('--hub', action='store_true',
                       help="Every project registered on this machine.")
    parser.add_argument('--all', action='store_true', help="Also print OK lines.")
    args = parser.parse_args()

    if args.project_root:
        for line in format_lines(check(args.project_root), args.all):
            print(line)
        return
    for name, lines in hub_check().items():
        shown = format_lines(lines, args.all, '  ')
        if shown:
            print(f"{name}:")
            for line in shown:
                print(line)


if __name__ == '__main__':
    main()
