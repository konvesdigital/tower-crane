#!/usr/bin/env python3
"""
check_multi_machine.py - resume-time nudge: surfaces any `scope: multi_machine` consumer with no
`hosts.<this_host_id>` entry yet. Notify-only, never mutates. The connect action is the "connect
project" flow (new_consumer.py's slug-collision merge routing).

Effective scope is computed live via registry_lib.effective_scope (2+ hosts: entries always
counts as multi_machine, regardless of the declared `scope:` line) rather than trusting the
declared value.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config_lib import get_shared_config
from registry_lib import parse_registry, effective_scope

SHARED_ROOT = Path(__file__).resolve().parent.parent
# consumers\ lives one level above SHARED_ROOT, at the outer repo root.
PROJECT_ROOT = SHARED_ROOT.parent
CONSUMERS_DIR = PROJECT_ROOT / 'consumers'


def main():
    config = get_shared_config(SHARED_ROOT)
    this_host = str(config.get('host_id', ''))

    if not CONSUMERS_DIR.is_dir():
        return

    for f in sorted(CONSUMERS_DIR.glob('*.md')):
        c = parse_registry(f)
        if c is None:
            continue
        if effective_scope(c) == 'multi_machine' and this_host not in c['hosts']:
            print(f"[NUDGE] '{c['name']}' is multi_machine but not connected here ('{this_host}') "
                  f"- want to connect it? (say \"connect project\")")


if __name__ == '__main__':
    main()
