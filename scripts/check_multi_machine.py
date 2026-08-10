#!/usr/bin/env python3
"""
check_multi_machine.py - resume-time nudge for design\\multi_machine_hub.md's Problem 2: a
`scope: multi_machine` consumer with no `hosts.<this_host_id>` entry yet is surfaced proactively
instead of staying silent ("`multi_machine` is a standing invitation, not teleportation" - the
design doc's own framing). Notify-only, never mutates - same shape as check_hook_activation.py's
Rung-2 check. The actual connect action stays the "connect project" flow (new_consumer.py's
slug-collision merge routing).

Effective scope is computed live (2+ hosts: entries always counts as multi_machine, regardless of
the declared `scope:` line - see registry_lib.effective_scope) rather than trusting the declared
value, so this nudge never depends on check_tower_crane.py/relocate.py having already run their
own floor write-back first.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config_lib import get_shared_config
from registry_lib import parse_registry, effective_scope

SHARED_ROOT = Path(__file__).resolve().parent.parent
# consumers\ is private hub state, not shipped toolkit content - it lives at the outer root
# (design\local_first_reframe.md's outer/inner split), one level above SHARED_ROOT (toolkit\).
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
