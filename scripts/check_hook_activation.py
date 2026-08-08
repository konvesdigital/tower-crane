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

This script answers two mechanical questions - nothing broader:
  1. Does every tracked hook script have a line somewhere in settings.local.json referencing it?
  2. Does that reference actually RESOLVE to this file on disk right now?

Question 2 was added 2026-08-08 after a real incident: a folder rename left a hook command's
baked absolute path pointing at nothing, and the original filename-substring-only check reported
[WIRED] the entire time - the string was still present, it just no longer resolved to a real file,
so every Bash/PowerShell call was silently failing the hook before this script ever got a chance
to say anything. Command strings may use Claude Code's own $CLAUDE_PROJECT_DIR env var (this
script's own project_root) or a literal ~/-relative or absolute path; all three are resolved
before the existence check.

Usage: python scripts\\check_hook_activation.py [--project-root <path>]
Defaults --project-root to the current working directory (the outer repo root, matching how
`resume` invokes this). Prints [WIRED]/[BROKEN]/[UNWIRED]/[N/A] lines. Always exits 0 - this is a
heads-up, not a hard gate; either failure mode is a one-time fix (add a hook block / fix a path),
not a broken state that blocks work.
"""

import argparse
import json
import re
import sys
from pathlib import Path

_QUOTED_PATH_RE = re.compile(r'"([^"]*\.py)"')


def _resolve(raw_path, project_root):
    """Expand $CLAUDE_PROJECT_DIR / ~ / a bare relative or absolute path the same way the shell
    actually would when Claude Code runs the hook command, then return the resulting Path."""
    expanded = raw_path.replace('$CLAUDE_PROJECT_DIR', str(project_root))
    if expanded.startswith('~'):
        expanded = str(Path.home()) + expanded[1:]
    p = Path(expanded)
    if not p.is_absolute():
        p = project_root / p
    return p


def _commands_referencing(settings, hook_name):
    """Walk settings['hooks'][event][group]['hooks'][*]['command'] and yield every command string
    whose quoted path ends in this hook file's own name - i.e. every place that claims to wire it."""
    hooks = settings.get('hooks') if isinstance(settings, dict) else None
    if not isinstance(hooks, dict):
        return
    for groups in hooks.values():
        if not isinstance(groups, list):
            continue
        for grp in groups:
            for h in grp.get('hooks', []) if isinstance(grp, dict) else []:
                cmd = h.get('command') if isinstance(h, dict) else None
                if isinstance(cmd, str) and hook_name in cmd:
                    yield cmd


def main():
    parser = argparse.ArgumentParser(
        description="Notify-only check: is every tracked .claude\\hooks\\ script referenced in "
                     "this machine's .claude\\settings.local.json, AND does that reference "
                     "actually resolve to a real file?"
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

    settings = {}
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text(encoding='utf-8'))
        except json.JSONDecodeError as e:
            print(f"[N/A] .claude\\settings.local.json is not valid JSON ({e}) - can't check "
                  "activation.")
            sys.exit(0)
    else:
        print("[N/A] no .claude\\settings.local.json on this machine yet - every hook below is "
              "necessarily unwired.")

    unwired_count = 0
    broken_count = 0
    for hook_file in hook_files:
        commands = list(_commands_referencing(settings, hook_file.name))
        if not commands:
            unwired_count += 1
            print(f"[UNWIRED] '{hook_file.name}' exists under .claude\\hooks\\ but isn't "
                  "referenced anywhere in settings.local.json on this machine - add a hook block "
                  "for it if you want it active here.")
            continue
        resolved_ok = False
        last_target = None
        for cmd in commands:
            m = _QUOTED_PATH_RE.search(cmd)
            raw_path = m.group(1) if m else cmd
            target = _resolve(raw_path, project_root)
            last_target = target
            if target.exists():
                resolved_ok = True
                break
        if resolved_ok:
            print(f"[WIRED] '{hook_file.name}' is referenced in settings.local.json and resolves "
                  "to a real file.")
        else:
            broken_count += 1
            print(f"[BROKEN] '{hook_file.name}' is referenced in settings.local.json, but its "
                  f"command resolves to '{last_target}', which does not exist on disk (a stale "
                  "path - e.g. left over from a folder rename/move). The hook is silently not "
                  "running.")

    print()
    if unwired_count or broken_count:
        print(f"=== {unwired_count} hook(s) not wired in, {broken_count} hook(s) wired but "
              "broken on this machine (notify only, not a failure) ===")
    else:
        print("=== every tracked hook is wired in and resolves correctly on this machine ===")
    sys.exit(0)


if __name__ == '__main__':
    main()
