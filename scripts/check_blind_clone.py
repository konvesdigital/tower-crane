#!/usr/bin/env python3
"""
check_blind_clone.py - Tower Crane architecture tool: for people modifying Tower Crane itself;
ordinary users have no use for it. Runs the toolkit exactly as another operator's hub would first meet it:
the toolkit\\ folder alone, with no outer repo around it (no design\\, tickets, or progress doc).

Steps:
  1. Copy this toolkit into <temp>\\hub\\toolkit - default: tracked + untracked-not-ignored files at
     their current on-disk content; --committed: HEAD only (git archive).
  2. Copy this machine's config.local.json into the copy so the scripts can start.
  3. Run each script that reads an outer-repo file and require its output to contain
     [MISSING-TEMPLATE-FILE] and no Traceback.
  4. Run check_file_surface.py check 9 (outer-repo citations) over the whole copy.

Prints [PASS]/[FAIL] per step; exit 1 on any FAIL.

Usage: python scripts\\check_blind_clone.py [--committed]
"""

import argparse
import io
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config_lib import get_shared_config

SHARED_ROOT = Path(__file__).resolve().parent.parent
MARKER = '[MISSING-TEMPLATE-FILE]'

# (script, args) pairs that each read an outer-repo file or folder.
OUTER_READERS = [
    ('ticket_scan.py', []),
    ('progress_sections.py', []),
    ('check_multi_machine.py', []),
    ('check_stale_paths.py', []),
    ('readiness.py', ['--hub']),
]


def _git(args):
    return subprocess.run(['git', '-C', str(SHARED_ROOT)] + args, capture_output=True)


def copy_toolkit(dest, committed):
    if committed:
        proc = _git(['archive', '--format=tar', 'HEAD'])
        with tarfile.open(fileobj=io.BytesIO(proc.stdout)) as tar:
            tar.extractall(dest)
        return
    names = _git(['ls-files', '-z', '--cached', '--others', '--exclude-standard']).stdout
    for rel in filter(None, names.decode('utf-8').split('\0')):
        src = SHARED_ROOT / rel
        if src.is_file():
            (dest / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest / rel)


def run(launcher, script, args, cwd):
    proc = subprocess.run([launcher, str(script)] + args, capture_output=True, text=True,
                          encoding='utf-8', cwd=cwd)
    return proc.stdout + proc.stderr


def main():
    parser = argparse.ArgumentParser(description="Run the toolkit with no outer repo around it.")
    parser.add_argument('--committed', action='store_true',
                        help="Use HEAD only (git archive) instead of the current on-disk content.")
    args = parser.parse_args()

    failures = 0
    launcher = get_shared_config(SHARED_ROOT)['python_launcher']
    with tempfile.TemporaryDirectory() as tmp:
        hub = Path(tmp) / 'hub'
        toolkit = hub / 'toolkit'
        toolkit.mkdir(parents=True)
        copy_toolkit(toolkit, args.committed)
        shutil.copy2(SHARED_ROOT / 'config.local.json', toolkit / 'config.local.json')

        for script, script_args in OUTER_READERS:
            out = run(launcher, toolkit / 'scripts' / script, script_args, hub)
            label = ' '.join([script] + script_args)
            if MARKER in out and 'Traceback' not in out:
                print(f"[PASS] {label}: reports the missing outer-repo file")
            else:
                failures += 1
                print(f"[FAIL] {label}: expected a {MARKER} line and no Traceback; got:")
                print(re.sub(r'(?m)^', '    ', out.strip()))

        subprocess.run(['git', 'init', '-q'], cwd=toolkit, capture_output=True)
        subprocess.run(['git', 'add', '-A'], cwd=toolkit, capture_output=True)
        subprocess.run(['git', '-c', 'user.name=blind', '-c', 'user.email=blind@example.invalid',
                        'commit', '-q', '-m', 'blind clone'], cwd=toolkit, capture_output=True)
        empty_tree = '4b825dc642cb6eb9a060e54bf8d69288fbd8dd8e'
        out = run(launcher, toolkit / 'scripts' / 'check_file_surface.py',
                  ['--base-sha', empty_tree, '--head-sha', 'HEAD'], toolkit)
        citation_fails = [ln for ln in out.splitlines() if ln.startswith('[FAIL]') and 'citation' in ln]
        if citation_fails:
            failures += 1
            print("[FAIL] check 9 over the whole toolkit:")
            for ln in citation_fails:
                print(f"    {ln}")
        else:
            print("[PASS] check 9: no outer-repo design/ticket citation anywhere in the toolkit")

    print(f"\n=== blind clone: {'FAIL' if failures else 'PASS'} ({failures} failure(s)) ===")
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    main()
