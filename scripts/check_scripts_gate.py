#!/usr/bin/env python3
"""
check_scripts_gate.py - runs hooks\\consistency_check.py (static analysis - undefined names, arity
mismatches, string-key drift) against every new/changed .py file under hooks\\/scripts\\/agents\\
between two refs. The PR-facing sibling of update_toolkit.py's own consistency sweep (used during
`update`'s pre-merge worktree check): that one needs a throwaway worktree because it runs against
content that was only ever fetched, never checked out. This one is meant to run inside a GitHub
Actions checkout of a PR's head, where the files are already on disk at their real paths - no
worktree trick needed, just read what's there.

Exit 0 if every changed script passes consistency_check.py (or there's nothing to check); exit 1
if any of them FAILs. Hard gate, no soft-flag mode - a static-analysis FAIL (undefined name, arity
mismatch) is never a matter of reviewer taste.

Usage: python scripts\\check_scripts_gate.py --base-sha <sha> --head-sha <sha>
Run from anywhere; always resolves paths against this toolkit\\ repo, not the caller's cwd.
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SHARED_ROOT = Path(__file__).resolve().parent.parent
ALLOWED_DIR_PREFIXES = ('hooks/', 'scripts/', 'agents/')


def git(args):
    return subprocess.run(['git', '-C', str(SHARED_ROOT)] + args, capture_output=True, text=True)


def changed_python_files(base_sha, head_sha):
    proc = git(['diff', '--name-status', '-M', '-C', f'{base_sha}..{head_sha}'])
    out = []
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split('\t')
        status = parts[0]
        if status.startswith('D'):
            continue
        path = parts[2] if status.startswith(('R', 'C')) and len(parts) >= 3 else parts[-1]
        norm = path.replace('\\', '/')
        if norm.endswith('.py') and norm.startswith(ALLOWED_DIR_PREFIXES):
            out.append(norm)
    return out


def main():
    parser = argparse.ArgumentParser(
        description="Runs consistency_check.py over every changed script under hooks\\/scripts\\/agents\\."
    )
    parser.add_argument('--base-sha', required=True)
    parser.add_argument('--head-sha', default='HEAD')
    args = parser.parse_args()

    print("=== check_scripts_gate.py ===")
    print(f"comparing {args.base_sha}..{args.head_sha}")

    hook_script = SHARED_ROOT / 'hooks' / 'consistency_check.py'
    files = changed_python_files(args.base_sha, args.head_sha)
    if not files:
        print("[N/A] no changed .py files under hooks\\/scripts\\/agents\\ - nothing to check.")
        sys.exit(0)
    if not hook_script.exists():
        print("[N/A] no hooks\\consistency_check.py in this checkout - nothing to run.")
        sys.exit(0)

    sandbox = Path(tempfile.gettempdir()) / f"check_scripts_gate_sandbox_{os.getpid()}"
    sandbox.mkdir(parents=True, exist_ok=True)
    saved = os.environ.get('CLAUDE_PROJECT_DIR')
    os.environ['CLAUDE_PROJECT_DIR'] = str(sandbox)

    ok = True
    try:
        for rel in files:
            full = SHARED_ROOT / rel
            proc = subprocess.run([sys.executable, str(hook_script), str(full)],
                                   capture_output=True, text=True)
            if proc.returncode == 2:
                ok = False
                print(f"[FAIL] {rel}")
                print(proc.stdout + proc.stderr)
            else:
                print(f"[PASS] {rel}")
    finally:
        if saved is None:
            os.environ.pop('CLAUDE_PROJECT_DIR', None)
        else:
            os.environ['CLAUDE_PROJECT_DIR'] = saved
        shutil.rmtree(sandbox, ignore_errors=True)

    print()
    print(f"=== Summary: {'PASS' if ok else 'FAIL'} ===")
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
