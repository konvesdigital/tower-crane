#!/usr/bin/env python3
"""
consumer_resume_check.py - the consumer-side `resume`'s Shape-B fix
(design\\command_procedure_audit.md's B1 audit re-run on consumer `resume`, scoped 2026-08-24):
chains templates\\continuity_resume_check.md's `resume` step 3's two already-scripted, notify-only
hub-staleness checks into one call instead of two separately prose-sequenced Bash invocations
every session - the consumer-side analogue of the hub's own resume_check.py (B1), deliberately
smaller: a connected project's own `resume` only ever needs to ask "has the hub toolkit\\ I import
from fallen behind its own upstream," not the hub's own four host-perspective checks (this
machine's own hook activation, the consumers\\ registry, other consumers' stale paths - none of
which a consumer session can meaningfully run against another project's registry entry).

Runs, in order, each exactly as `resume` step 3 already documents invoking it standalone:
  1. update_toolkit.py --notify        (toolkit\\ dirty / incoming / outgoing state - never merges)
  2. check_tower_crane.py --write-guidance   (no --consumer flag - the hub's per-machine `host:`
                                               scoping already limits it to what's reachable here)

Both are guaranteed side-effect-free from this project's own perspective (neither pulls/merges/
pushes toolkit\\ - that's the gated `update` action, run only in a session opened directly in the
hub) and always exit 0, so this script does no pass/fail interpretation of its own; it just runs
each in turn and prints its output verbatim under a numbered header, same "consolidate the CALL,
not the interpretation" split resume_check.py already established for the hub side.

Usage: python consumer_resume_check.py
Run from anywhere; resolves the hub's toolkit\\ folder relative to this script's own location, not
the caller's cwd - same self-locating pattern every other consumer-invoked script in this toolkit
uses (e.g. scan_consumer_update.py).
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config_lib import get_shared_config

SHARED_ROOT = Path(__file__).resolve().parent.parent  # toolkit\


def _run(python_launcher, script_name, extra_args=None):
    script = SHARED_ROOT / 'scripts' / script_name
    proc = subprocess.run(
        [python_launcher, str(script)] + (extra_args or []),
        capture_output=True, text=True,
    )
    output = (proc.stdout + proc.stderr).strip()
    return output if output else '(nothing to report)'


def main():
    cfg = get_shared_config(SHARED_ROOT)
    launcher = cfg['python_launcher']

    checks = [
        ('update_toolkit.py --notify', 'update_toolkit.py', ['--notify']),
        ('check_tower_crane.py --write-guidance', 'check_tower_crane.py', ['--write-guidance']),
    ]

    print("=== consumer_resume_check.py - consolidated consumer resume checks ===")
    for i, (label, script_name, extra_args) in enumerate(checks, 1):
        print(f"\n--- {i}/{len(checks)}: {label} ---")
        print(_run(launcher, script_name, extra_args))
    print("\n=== end resume checks ===")


if __name__ == '__main__':
    main()
