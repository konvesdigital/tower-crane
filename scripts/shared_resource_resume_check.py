#!/usr/bin/env python3
"""
shared_resource_resume_check.py - chains templates\\shared_resources_resume_check.md's "At
resume" notify-only checks into one call.

Runs, in order:
  1. check_shared_resource_refs.py    ([FAIL]/[HOST-GAP] - a broken adopted reference/pointer, or
                                        a Hosts: block missing this machine)
  2. check_shared_resource_drift.py   ([DRIFT]/[N/A] - an adopted stub's content hash vs. the
                                        source entry's current content)

Both take --project-root and always exit 0 (notify-only). This script does no pass/fail
interpretation of its own - it runs each in turn and prints its output verbatim under a numbered
header. Only relevant if this project has adopted a reference/tool entry (or an insight with a
live Track-1 destination); this script doesn't check that gate itself.

Usage: python shared_resource_resume_check.py --project-root "<this project's absolute root>"
Run from anywhere; resolves the hub's toolkit\\ folder relative to this script's own location, not
the caller's cwd.
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
        description="Chains shared_resources_resume_check.md's notify-only checks into one "
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
