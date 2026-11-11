#!/usr/bin/env python3
"""
resume_check.py - chains resume's notify-only checks into one call.

Starts with a `Cell:` line (`Cell: <host_id> / <repo>`). With --quick (`quick resume`) it prints
that line and then the same project_progress.md digest progress_sections.py prints, and runs none
of the checks below.

Runs, in order:
  1. update_toolkit.py --notify           (toolkit\\ dirty / incoming / outgoing state)
  2. check_hook_activation.py             (--project-root <outer repo root>)
  3. check_multi_machine.py               (no args)
  4. check_stale_paths.py                 (no args)
  5. check_shared_resource_catalog.py     (no args - resume-only, not run at `quick resume`)
  6. readiness.py --hub                   (every consumer registered on this host)
  7. self_hooks.py --check-defaults       (default hub self-use tools off on this machine)
  8. ticket_scan.py                       (read-only categorization of change_requests\\ tickets)
  9. check_hub_identity_import.py         (outer CLAUDE.md imports templates\\identity.md)

All nine are side-effect-free and always exit 0. This script does no pass/fail interpretation of
its own - it runs each in turn and prints its output verbatim under a numbered header, silent
sub-sections included. Reporting tags per step: dirty/incoming/outgoing lines (step 1),
[UNWIRED]/[BROKEN] (step 2), [NUDGE] (step 3), [STALE-PATH] (step 4), [FAIL]/[MISMATCH] (step 5),
[TODO]/[NOTE]/[UNKNOWN]/[HUB-MISMATCH] (step 6),
[SELF-USE-OFF] (step 7), [NO-IDENTITY-IMPORT] (step 9).

Usage: python scripts\\resume_check.py [--project-root <path>] [--quick]
--project-root defaults to this toolkit\\ checkout's own parent (the outer repo root).
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config_lib import get_shared_config, cell_line
import resume_digest

SHARED_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = SHARED_ROOT.parent


def _run(python_launcher, script_name, extra_args=None):
    script = SHARED_ROOT / 'scripts' / script_name
    proc = subprocess.run(
        [python_launcher, str(script)] + (extra_args or []),
        capture_output=True, text=True, encoding='utf-8', errors='replace',
        env={**os.environ, 'PYTHONIOENCODING': 'utf-8'},
    )
    output = (proc.stdout + proc.stderr).strip()
    if proc.returncode != 0 and 'Traceback' in proc.stderr:
        output = f"[CRASHED: {script_name} exited {proc.returncode}]" + chr(10) + output
    return output if output else '(nothing to report)'


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    parser = argparse.ArgumentParser(
        description="Chains resume's notify-only checks into one consolidated report."
    )
    parser.add_argument('--project-root', default=str(PROJECT_ROOT),
                         help="Outer repo root, passed through to check_hook_activation.py. "
                              "Defaults to this toolkit\\ checkout's own parent.")
    parser.add_argument('--quick', action='store_true',
                         help="`quick resume`: print the Cell line and the project_progress.md "
                              "digest, and run none of the checks.")
    args = parser.parse_args()

    if args.quick:
        print(cell_line(args.project_root))
        sys.argv = [sys.argv[0], '--project-root', args.project_root]
        resume_digest.main()
        return

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
        ('ticket_scan.py', 'ticket_scan.py', []),
        ('check_hub_identity_import.py', 'check_hub_identity_import.py', []),
    ]

    print("=== resume_check.py - consolidated resume checks ===")
    print(cell_line(args.project_root))
    for i, (label, script_name, extra_args) in enumerate(checks, 1):
        print(f"\n--- {i}/{len(checks)}: {label} ---")
        print(_run(launcher, script_name, extra_args))
    print("\n=== end resume checks ===")


if __name__ == '__main__':
    main()
