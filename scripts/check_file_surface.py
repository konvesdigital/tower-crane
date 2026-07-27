#!/usr/bin/env python3
"""
check_file_surface.py - a "what kind of file is this, and does it belong here" gate, independent
of what any individual file's content means. Built alongside Fix 3 Phase 3
(design\\update_trust_review.md) after a live discussion found that the other new gates
(check_agents_pr_gate.py's AGENTS.md-content checks, consistency_check.py's Python static
analysis) only defend against careless mistakes in the surface they already know to look at - a
deliberate adversary doesn't need to write a mismatched variable name, they can write the payload
in a language no checker here reads, or hide it in a file extension nobody scans. This script
assumes an adversary, not just carelessness (design\\update_trust_review.md's own threat model).

Runs over a whole-repo diff between two refs (matches the Locked "diff scope for the review gate
= the whole inner repo, no path filter" decision) - never scoped to one file, since the whole point
is catching a script or directive file showing up somewhere unexpected.

Four checks, three hard-fail, one soft-flag:
  1. Known AI-directive filename        HARD  - a new/renamed file matching a real, converged
                                                  AI-directive filename convention (CLAUDE.md,
                                                  .cursorrules, a second AGENTS.md, etc.) anywhere
                                                  other than the one canonical AGENTS.md.
  2. Non-Python script language          HARD  - this project's Locked "Language policy" decision
                                                  (project_progress.md Decisions) is Python-only for
                                                  every runtime script, no exceptions remaining now
                                                  that the legacy PowerShell tools are fully retired
                                                  to _archive\\. A new script in any other language is
                                                  either going to be a compatibility problem or an
                                                  attempt to dodge the Python-only checkers - both
                                                  are reasons to stop and ask, not silently allow.
                                                  Detected two ways: file extension, AND (to catch
                                                  the "rename it to .txt" evasion) a non-Python
                                                  shebang line, regardless of extension.
  3. Python file outside its home        HARD  - a .py file added anywhere other than hooks\\,
                                                  scripts\\, agents\\, or a tests\\<tool>\\ fixture.
  4. Binary file                         HARD  - this is a text-based tooling repo; it should never
                                                  need to ship a binary blob. The single clearest
                                                  "something is very wrong" signal for an obfuscated
                                                  payload.
  5. Disguised-code heuristic            SOFT  - content (eval/exec/base64/curl-pipe-shell/etc.) in
                                                  a file not already classified as code. Heuristic,
                                                  so it can't safely hard-block (a design doc
                                                  legitimately quotes shell commands in prose) - see
                                                  capability-vs-content in check_agents_pr_gate.py
                                                  for the same reasoning.

Usage: python scripts\\check_file_surface.py --base-sha <sha> --head-sha <sha>
Run from anywhere; always resolves paths against this toolkit\\ repo, not the caller's cwd.
"""

import argparse
import subprocess
import sys
from pathlib import PurePosixPath

SHARED_ROOT = None  # set in main() after argparse, so this file can be imported without side effects


def _resolve_shared_root():
    from pathlib import Path
    return Path(__file__).resolve().parent.parent


COUNTS = {'PASS': 0, 'WARN': 0, 'FAIL': 0}

# Other real, converged AI-directive filename conventions. AGENTS.md itself is deliberately NOT in
# this set - a second copy of it elsewhere is checked separately below, against the canonical
# constant directly, so there's only one spelling of that particular filename in this file.
KNOWN_DIRECTIVE_BASENAMES = {
    'claude.md', '.cursorrules', '.windsurfrules', '.clinerules', 'gemini.md',
    'copilot-instructions.md', 'system_prompt.md', 'system_prompt.txt',
}
CANONICAL_AGENTS_MD = 'AGENTS.md'  # the one sanctioned location, repo root

NONPY_SCRIPT_EXTENSIONS = {
    '.sh', '.bash', '.zsh', '.ps1', '.psm1', '.psd1', '.bat', '.cmd', '.js', '.mjs', '.cjs',
    '.ts', '.rb', '.pl', '.php', '.go', '.rs', '.c', '.cpp', '.cc', '.h', '.java', '.class',
    '.jar', '.exe', '.dll', '.so', '.dylib', '.wasm', '.lua', '.groovy', '.scala', '.swift',
    '.kt', '.vbs',
}
PY_EXT = '.py'
ALLOWED_PY_DIR_PREFIXES = ('hooks/', 'scripts/', 'agents/')
FIXTURE_DIR_PREFIX = 'tests/'
WORKFLOW_DIR_PREFIX = '.github/workflows/'  # legitimately embeds shell in `run:` blocks

DISGUISED_CODE_TOKENS = [
    'eval(', 'exec(', 'base64', '| sh', '| bash', 'invoke-expression', 'iex(',
    'os.system(', 'subprocess.', 'curl ', 'wget ',
]


def report(level, message):
    COUNTS[level] += 1
    print(f"[{level}] {message}")


def git(shared_root, args):
    return subprocess.run(['git', '-C', str(shared_root)] + args, capture_output=True, text=True)


def changed_files(shared_root, base_sha, head_sha):
    """Returns a list of (status, path) for every added/modified/renamed/copied file, path is the
    file's path AT HEAD (the new path, for renames/copies). Deletions are excluded - nothing to
    classify about a file that's gone."""
    proc = git(shared_root, ['diff', '--name-status', '-M', '-C', f'{base_sha}..{head_sha}'])
    out = []
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split('\t')
        status = parts[0]
        if status.startswith('D'):
            continue
        if status.startswith(('R', 'C')) and len(parts) >= 3:
            out.append((status, parts[2]))
        elif len(parts) >= 2:
            out.append((status, parts[1]))
    return out


def binary_paths(shared_root, base_sha, head_sha):
    proc = git(shared_root, ['diff', '--numstat', f'{base_sha}..{head_sha}'])
    out = set()
    for line in proc.stdout.splitlines():
        parts = line.split('\t')
        if len(parts) >= 3 and parts[0] == '-' and parts[1] == '-':
            out.add(parts[2])
    return out


def read_file_at(shared_root, ref, path):
    proc = git(shared_root, ['show', f'{ref}:{path}'])
    return proc.stdout if proc.returncode == 0 else None


def check_known_directive_filenames(files):
    hits = []
    for status, path in files:
        norm = path.replace('\\', '/')
        if norm == CANONICAL_AGENTS_MD:
            continue
        basename = PurePosixPath(norm).name.lower()
        if basename in KNOWN_DIRECTIVE_BASENAMES or basename == CANONICAL_AGENTS_MD.lower():
            hits.append(norm)
    if not hits:
        report('PASS', "no new/renamed file matches a known AI-directive filename convention.")
        return
    for h in hits:
        report('FAIL', f"'{h}' matches a known AI-directive filename convention (CLAUDE.md, "
                       ".cursorrules, a second AGENTS.md, etc.) outside the one canonical "
                       f"{CANONICAL_AGENTS_MD} - this repo's convention is a single file; a new one "
                       "needs a deliberate design decision, not a silent addition.")


def check_language_and_location(shared_root, files, head_sha):
    flagged = False
    for status, path in files:
        norm = path.replace('\\', '/')
        ext = PurePosixPath(norm).suffix.lower()
        under_allowed_dir = norm.startswith(ALLOWED_PY_DIR_PREFIXES)
        under_fixtures = norm.startswith(FIXTURE_DIR_PREFIX)

        if ext in NONPY_SCRIPT_EXTENSIONS:
            report('FAIL', f"'{norm}' is a non-Python script (extension {ext!r}) - this project's "
                           "Locked language policy is Python-only for every runtime script, no "
                           "exceptions remain now that legacy PowerShell tooling is fully retired. "
                           "A different language is either a compatibility risk or a way to dodge "
                           "the Python-only checkers - needs a deliberate decision either way.")
            flagged = True
            continue

        if ext == PY_EXT and not under_allowed_dir and not under_fixtures:
            report('FAIL', f"'{norm}' is a Python file outside hooks\\/scripts\\/agents\\ (or a "
                           "tests\\ fixture) - code doesn't belong in this location.")
            flagged = True
            continue

    # shebang scan, independent of extension - catches "rename my shell script to .txt"
    for status, path in files:
        norm = path.replace('\\', '/')
        ext = PurePosixPath(norm).suffix.lower()
        if ext in NONPY_SCRIPT_EXTENSIONS:
            continue  # already reported above, don't double-count
        text = read_file_at(shared_root, head_sha, path)
        if text is None:
            continue
        first_line = text.splitlines()[0] if text.splitlines() else ''
        if first_line.startswith('#!') and 'python' not in first_line.lower():
            report('FAIL', f"'{norm}' carries a non-Python shebang ({first_line.strip()!r}) - "
                           "flagged regardless of its extension, since renaming a script doesn't "
                           "change what it is.")
            flagged = True

    if not flagged:
        report('PASS', "every script-like file is Python, in an expected location.")


def check_binary_files(shared_root, base_sha, head_sha):
    paths = binary_paths(shared_root, base_sha, head_sha)
    if not paths:
        report('PASS', "no binary files added or modified.")
        return
    for p in sorted(paths):
        report('FAIL', f"'{p}' is a binary file - this is a text-based tooling repo; a binary blob "
                       "has no legitimate reason to ship here and is the clearest signal of an "
                       "obfuscated payload.")


def check_disguised_code(shared_root, files, base_sha, head_sha):
    hits = []
    for status, path in files:
        norm = path.replace('\\', '/')
        ext = PurePosixPath(norm).suffix.lower()
        if ext == PY_EXT and (norm.startswith(ALLOWED_PY_DIR_PREFIXES) or norm.startswith(FIXTURE_DIR_PREFIX)):
            continue  # already-recognized code, not "disguised"
        if norm.startswith(WORKFLOW_DIR_PREFIX):
            continue  # legitimately embeds shell in `run:` blocks
        proc = git(shared_root, ['diff', f'{base_sha}..{head_sha}', '--', path])
        added_lines = [l[1:] for l in proc.stdout.splitlines()
                       if l.startswith('+') and not l.startswith('+++')]
        for line in added_lines:
            lower = line.lower()
            for token in DISGUISED_CODE_TOKENS:
                if token in lower:
                    hits.append((norm, token, line.strip()))
    if not hits:
        report('PASS', "no code-like content found hiding in a file not already classified as code.")
        return
    report('WARN', "content resembling executable code appears in file(s) not classified as code - "
                   "heuristic, so this is a nudge for reviewer attention, not a block:")
    for norm, token, line in hits[:10]:
        print(f"  {norm} matched {token!r}: {line}")


def main():
    parser = argparse.ArgumentParser(
        description="File-surface classifier: language, location, and disguise checks over a "
                     "whole-repo diff. Assumes an adversary, not just carelessness."
    )
    parser.add_argument('--base-sha', required=True)
    parser.add_argument('--head-sha', default='HEAD')
    args = parser.parse_args()

    shared_root = _resolve_shared_root()

    print("=== check_file_surface.py ===")
    print(f"comparing {args.base_sha}..{args.head_sha}")

    files = changed_files(shared_root, args.base_sha, args.head_sha)
    if not files:
        print("[N/A] no added/modified/renamed files in this diff - nothing to classify.")
        sys.exit(0)

    check_known_directive_filenames(files)
    check_language_and_location(shared_root, files, args.head_sha)
    check_binary_files(shared_root, args.base_sha, args.head_sha)
    check_disguised_code(shared_root, files, args.base_sha, args.head_sha)

    print()
    print(f"=== Summary: {COUNTS['PASS']} passed, {COUNTS['WARN']} warning(s), {COUNTS['FAIL']} failure(s) ===")
    sys.exit(1 if COUNTS['FAIL'] > 0 else 0)


if __name__ == '__main__':
    main()
