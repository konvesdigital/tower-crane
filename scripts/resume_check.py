#!/usr/bin/env python3
"""
resume_check.py - chains resume's notify-only checks into one call.

Runs, in order:
  1. update_toolkit.py --notify           (toolkit\\ dirty / incoming / outgoing state)
  2. check_hook_activation.py             (--project-root <outer repo root>)
  3. check_multi_machine.py               (no args)
  4. check_stale_paths.py                 (no args)
  5. check_shared_resource_catalog.py     (no args - resume-only, not run at `quick resume`)
  6. readiness.py --hub                   (every consumer registered on this host)
  7. self_hooks.py --check-defaults       (default hub self-use tools off on this machine)

All seven are side-effect-free and always exit 0. This script does no pass/fail interpretation of
its own - it runs each in turn and prints its output verbatim under a numbered header, silent
sub-sections included. Reporting tags per step: dirty/incoming/outgoing lines (step 1),
[UNWIRED]/[BROKEN] (step 2), [NUDGE] (step 3), [STALE-PATH] (step 4), [FAIL]/[MISMATCH] (step 5),
[TODO]/[NOTE]/[UNKNOWN]/[HUB-MISMATCH] (step 6),
[SELF-USE-OFF] (step 7).

Usage: python scripts\\resume_check.py [--project-root <path>]
--project-root defaults to this toolkit\\ checkout's own parent (the outer repo root).
"""

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config_lib import get_shared_config

SHARED_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = SHARED_ROOT.parent


def _run(python_launcher, script_name, extra_args=None):
    script = SHARED_ROOT / 'scripts' / script_name
    proc = subprocess.run(
        [python_launcher, str(script)] + (extra_args or []),
        capture_output=True, text=True,
    )
    output = (proc.stdout + proc.stderr).strip()
    return output if output else '(nothing to report)'


def main():
    parser = argparse.ArgumentParser(
        description="Chains resume's notify-only checks into one consolidated report."
    )
    parser.add_argument('--project-root', default=str(PROJECT_ROOT),
                         help="Outer repo root, passed through to check_hook_activation.py. "
                              "Defaults to this toolkit\\ checkout's own parent.")
    args = parser.parse_args()

    cfg = get_shared_config(SHARED_ROOT)
    launcher = cfg['python_launcher']

    checks = [
        ('update_toolkit.py --notify', 'update_toolkit.py', ['--notify']),
        ('check_hook_activation.py', 'check_hook_activation.py', ['--project-root', args.project_root]),
        ('check_multi_machine.py', 'check_multi_machine.py', []),
        ('check_stale_paths.py', 'check_stale_paths.py', []),
        ('check_shared_resource_catalog.py', 'check_shared_resource_catalog.py', []),
        ('readiness.py --hub', 'readiness.py', ['--hub']),
        ('self_hooks.py --check-defaults', 'self_hooks.py', ['--check-defaults']),
    ]

    print("=== resume_check.py - consolidated resume checks ===")
    for i, (label, script_name, extra_args) in enumerate(checks, 1):
        print(f"\n--- {i}/{len(checks)}: {label} ---")
        print(_run(launcher, script_name, extra_args))
    print("\n=== end resume checks ===")


if __name__ == '__main__':
    main()
