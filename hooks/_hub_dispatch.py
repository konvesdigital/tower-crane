#!/usr/bin/env python3
# _hub_dispatch.py - host-invariant wrapper invoked from a consumer's .claude\settings.json hook
# commands. Copied verbatim into every consumer at .claude\hooks\_hub_dispatch.py.
#
# Reads this project's .claude\hub_pointer.md (gitignored, regenerated per host by "connect
# project" / scripts\relocate.py) for shared_root, then execs {shared_root}/hooks/<tool>.py with
# the same stdin/argv passthrough.
#
# Usage (from settings.json): python "$CLAUDE_PROJECT_DIR/.claude/hooks/_hub_dispatch.py" <tool> [args...]
# <tool> selects the target script: {shared_root}/hooks/<tool>.py

import re
import subprocess
import sys
from pathlib import Path

HUB_POINTER = Path(__file__).resolve().parent.parent / 'hub_pointer.md'


def read_shared_root():
    if not HUB_POINTER.exists():
        sys.exit(
            f"_hub_dispatch.py: {HUB_POINTER} not found - this host has never run "
            "\"connect project\" for this project. Run it once from the Tower Crane hub."
        )
    text = HUB_POINTER.read_text(encoding='utf-8')
    m = re.search(r'(?m)^shared_root:\s*(.+?)\s*$', text)
    if not m:
        sys.exit(
            f"_hub_dispatch.py: {HUB_POINTER} has no 'shared_root:' value - regenerate it "
            "(re-run \"connect project\", or scripts\\relocate.py, from the hub)."
        )
    return m.group(1)


def main():
    if len(sys.argv) < 2:
        sys.exit("_hub_dispatch.py: no tool name given (usage: _hub_dispatch.py <tool> [args...])")
    tool, extra_args = sys.argv[1], sys.argv[2:]
    shared_root = read_shared_root()
    target = Path(shared_root) / 'hooks' / f'{tool}.py'
    if not target.exists():
        sys.exit(f"_hub_dispatch.py: no such hub tool script: {target}")
    proc = subprocess.run([sys.executable, str(target)] + extra_args)
    sys.exit(proc.returncode)


if __name__ == '__main__':
    main()
