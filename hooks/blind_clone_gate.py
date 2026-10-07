#!/usr/bin/env python3
"""
blind_clone_gate.py - PreToolUse hook (matcher: Bash) for Tower Crane architects.

Reads the PreToolUse JSON on stdin. When the Bash command runs checkpoint_git.py, runs
scripts\\check_blind_clone.py first and blocks the command (exit 2, report on stderr) if that check
fails. Any other command passes through (exit 0).
"""

import json
import re
import subprocess
import sys
from pathlib import Path

CHECK = Path(__file__).resolve().parent.parent / 'scripts' / 'check_blind_clone.py'

# One shell segment that starts with a Python launcher, optional flags, then checkpoint_git.py as
# the script path.
CHECKPOINT_RE = re.compile(
    r'^\s*["\']?(?:\S*[\\/])?(?:python[\d.]*|py)(?:\.exe)?["\']?'
    r'(?:\s+-\S+)*\s+(?:"[^"]*checkpoint_git\.py"|\'[^\']*checkpoint_git\.py\'|\S*checkpoint_git\.py)(?:\s|$)',
    re.IGNORECASE)
SEGMENT_SPLIT_RE = re.compile(r'&&|\|\||[;|\n]')


def is_checkpoint(command):
    return any(CHECKPOINT_RE.match(seg) for seg in SEGMENT_SPLIT_RE.split(command))


def main():
    try:
        command = json.loads(sys.stdin.read()).get('tool_input', {}).get('command', '')
    except ValueError:
        sys.exit(0)
    if not is_checkpoint(command):
        sys.exit(0)
    proc = subprocess.run([sys.executable, str(CHECK)], capture_output=True, text=True, encoding='utf-8')
    if proc.returncode != 0:
        sys.stderr.write("[blind_clone_gate] checkpoint blocked - blind clone check failed:\n")
        sys.stderr.write(proc.stdout + proc.stderr)
        sys.exit(2)
    sys.exit(0)


if __name__ == '__main__':
    main()
