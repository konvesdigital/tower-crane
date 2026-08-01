#!/usr/bin/env python3
"""
check_hook_activation.py - narrow notify-only check for the rung-2 half of
design\\resource_sharing_model.md's three-rung settings ladder (machine-only /
private-ecosystem / public-default).

Rung 2 (private ecosystem: synced across the operator's own machines, never public) is built as
Option D: `.claude\\hooks\\` is tracked in the outer private repo (no longer gitignored), so a hook
script written on one machine reaches every other machine the operator owns via the ordinary
`git pull` `resume` already does. That solves syncing the ARTIFACT. It does not solve ACTIVATION -
`.claude\\settings.local.json` (Claude Code's own personal/local-settings file) stays gitignored by
design, so a hook file arriving via git pull is not automatically wired into a `PreToolUse`/
`PostToolUse` block on the machine that just received it.

This script answers exactly that one mechanical question - "does every tracked hook script have a
line somewhere in settings.local.json referencing it" - nothing broader. A deliberately considered
and rejected alternative was asking an agent "what's implemented here vs. everywhere" as a general
audit; that's a fuzzier, more expensive question with no fixed shape, and this check exists
specifically so that broader question never has to be asked routinely. Scope stays narrow by
design - see that doc's "Open extension, 2026-07-31" section.

Usage: python scripts\\check_hook_activation.py [--project-root <path>]
Defaults --project-root to the current working directory (the outer repo root, matching how
`resume` invokes this). Prints [WIRED]/[UNWIRED]/[N/A] lines. Always exits 0 - this is a heads-up,
not a hard gate; a missing wiring line is an easy one-time fix, not a broken state.
"""

import argparse
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Notify-only check: is every tracked .claude\\hooks\\ script referenced "
                     "somewhere in this machine's .claude\\settings.local.json?"
    )
    parser.add_argument('--project-root', default='.', help="Defaults to the current directory.")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    hooks_dir = project_root / '.claude' / 'hooks'
    settings_path = project_root / '.claude' / 'settings.local.json'
    print("=== check_hook_activation.py ===")

    if not hooks_dir.is_dir():
        print("[N/A] no .claude\\hooks\\ directory - nothing to check.")
        sys.exit(0)

    hook_files = sorted(p for p in hooks_dir.glob('*.py') if p.is_file())
    if not hook_files:
        print("[N/A] no hook scripts under .claude\\hooks\\ - nothing to check.")
        sys.exit(0)

    settings_text = ''
    if settings_path.exists():
        settings_text = settings_path.read_text(encoding='utf-8')
    else:
        print("[N/A] no .claude\\settings.local.json on this machine yet - every hook below is "
              "necessarily unwired.")

    unwired_count = 0
    for hook_file in hook_files:
        if hook_file.name in settings_text:
            print(f"[WIRED] '{hook_file.name}' is referenced in settings.local.json.")
        else:
            unwired_count += 1
            print(f"[UNWIRED] '{hook_file.name}' exists under .claude\\hooks\\ but isn't "
                  "referenced anywhere in settings.local.json on this machine - add a hook block "
                  "for it if you want it active here.")

    print()
    if unwired_count:
        print(f"=== {unwired_count} hook(s) present but not wired in on this machine (notify "
              "only, not a failure) ===")
    else:
        print("=== every tracked hook is wired in on this machine ===")
    sys.exit(0)


if __name__ == '__main__':
    main()
