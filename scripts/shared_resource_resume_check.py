#!/usr/bin/env python3
"""
shared_resource_resume_check.py - templates\\shared_resources_resume_check.md's "At resume"
Shape-B fix (design\\command_procedure_audit.md's consumer-side sweep, finding B4, 2026-08-24):
chains its two already-scripted, notify-only checks into one call instead of two separately
prose-sequenced Bash invocations every resume this project has adopted a shared_resources entry -
a smaller-scale instance of the exact same disease B1 found and fixed for `resume` step 3.

Runs, in order, each exactly as "At resume" already documents invoking it standalone:
  1. check_shared_resource_refs.py    ([FAIL]/[HOST-GAP] - a broken adopted reference/pointer, or
                                        a Hosts: block missing this machine)
  2. check_shared_resource_drift.py   ([DRIFT]/[N/A] - an adopted stub's content hash vs. the
                                        source entry's current content)

Both take --project-root and always exit 0 (notify-only), so this script does no pass/fail
interpretation of its own - it just runs each in turn and prints its output verbatim under a
numbered header, same "consolidate the CALL, not the interpretation" split resume_check.py/
consumer_resume_check.py already established. Only relevant if this project has adopted a
reference/tool entry (or an insight with a live Track-1 destination) - templates\\
shared_resources_resume_check.md already gates the whole section on that; this script doesn't
duplicate that check.

Usage: python shared_resource_resume_check.py --project-root "<this project's absolute root>"
Run from anywhere; resolves the hub's toolkit\\ folder relative to this script's own location, not
the caller's cwd - same self-locating pattern every other consumer-invoked script in this toolkit
uses (e.g. scan_consumer_update.py, consumer_resume_check.py).
"""

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config_lib import get_shared_config

SHARED_ROOT = Path(__file__).resolve().parent.parent  # toolkit\


def _run(python_launcher, script_name, project_root):
    script = SHARED_ROOT / 'scripts' / script_name
    proc = subprocess.run(
        [python_launcher, str(script), '--project-root', str(project_root)],
        capture_output=True, text=True,
    )
    output = (proc.stdout + proc.stderr).strip()
    return output if output else '(nothing to report)'


def main():
    parser = argparse.ArgumentParser(
        description="Chains shared_resources_resume_check.md's two notify-only checks "
                     "(check_shared_resource_refs.py, check_shared_resource_drift.py) into one "
                     "consolidated report."
    )
    parser.add_argument('--project-root', required=True, help="This project's absolute root.")
    args = parser.parse_args()

    cfg = get_shared_config(SHARED_ROOT)
    launcher = cfg['python_launcher']

    checks = ['check_shared_resource_refs.py', 'check_shared_resource_drift.py']

    print("=== shared_resource_resume_check.py - consolidated shared_resources checks ===")
    for i, script_name in enumerate(checks, 1):
        print(f"\n--- {i}/{len(checks)}: {script_name} ---")
        print(_run(launcher, script_name, args.project_root))
    print("\n=== end shared_resources checks ===")


if __name__ == '__main__':
    main()
