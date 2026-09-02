#!/usr/bin/env python3
"""
resume_check.py - `resume`'s Shape-B fix (design\\command_procedure_audit.md, finding B1): chains
the already-scripted, notify-only `resume` checks into one call instead of separately
prose-sequenced Bash invocations every session.

Runs, in order, each exactly as `resume` already documents invoking it standalone:
  1. update_toolkit.py --notify           (toolkit\\ dirty / incoming / outgoing state)
  2. check_hook_activation.py             (--project-root <outer repo root>)
  3. check_multi_machine.py               (no args)
  4. check_stale_paths.py                 (no args)
  5. check_shared_resource_catalog.py     (no args - added 2026-09-02, resume-only per user
                                            request, deliberately not run at `quick resume`: it
                                            checks shared_resources\\CATALOG.md/
                                            resource_relationships.yaml internal consistency,
                                            hub-root content that doesn't change within a single
                                            mid-session `checkpoint`-then-reopen gap)

All five are guaranteed side-effect-free and always exit 0 (each is a notify-only heads-up, never a
gate - see their own docstrings), so this script does no pass/fail interpretation of its own; it
just runs each in turn and prints its output verbatim under a numbered header, silent sub-sections
included, so the reader (or the agent following `resume`) still applies the exact same per-tag
reporting rules `resume`'s own steps already state: dirty/incoming/outgoing lines from step 1,
[UNWIRED]/[BROKEN] from step 2, [NUDGE] from step 3, [STALE-PATH] from step 4, [FAIL]/[MISMATCH]
from step 5. Consolidating the CALL, not the interpretation - each check's own semantics are
untouched.

Usage: python scripts\\resume_check.py [--project-root <path>]
--project-root defaults to this toolkit\\ checkout's own parent (the outer repo root) - the same
value check_multi_machine.py/check_stale_paths.py already compute for themselves via SHARED_ROOT,
so this script works correctly regardless of the caller's own cwd.
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
        description="Chains resume's four notify-only checks (update_toolkit.py --notify, "
                     "check_hook_activation.py, check_multi_machine.py, check_stale_paths.py) into "
                     "one consolidated report."
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
    ]

    print("=== resume_check.py - consolidated resume checks ===")
    for i, (label, script_name, extra_args) in enumerate(checks, 1):
        print(f"\n--- {i}/{len(checks)}: {label} ---")
        print(_run(launcher, script_name, extra_args))
    print("\n=== end resume checks ===")


if __name__ == '__main__':
    main()
