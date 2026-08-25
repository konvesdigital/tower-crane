#!/usr/bin/env python3
"""
checkpoint_consumer.py - the consumer-side "checkpoint" skill's git mechanics
(design\\command_procedure_audit.md's B2 consumer port, scoped 2026-08-24): ports
scripts\\checkpoint_git.py's untracked-file-safety mechanic from the hub's own two-repo checkpoint
to a single connected project's own repo.

Ported deliberately narrower than the hub original - see command_procedure_audit.md's "Hub/
consumer command parity" section for why:
  - Untracked-file safety carries over unchanged: `git add -u` stages tracked modifications
    automatically (always safe, no prompt); a genuinely untracked file blocks with an
    `[UNTRACKED]` report until resolved via --include/--include-all/--skip-untracked, exactly
    like the hub script - the same "a stray temp file looks identical to a real new file, from
    git's point of view" problem applies equally to a consumer project's own repo.
  - No leak-scan gate and no Standing-Constraints guardrail port over - both are hub-specific
    (scrubbing outgoing content against toolkit\\'s own public remote; AGENTS.md's own governance
    section). Neither has a consumer-side analogue to guard.
  - No-remote handling is SOFT here, unlike the hub script's hard `[ABORT]`:
    `config_lib.py`'s own `_commit_scoped()` already treats a consumer project's missing 'origin'
    as a normal, everyday 'committed-no-remote' outcome (commit locally, skip the push, no error)
    - a local-only consumer project is common, not an anomaly, unlike the hub's own two repos,
    which are always expected to have one. Copying the hub script's abort-on-no-remote behavior
    here would regress every local-only consumer project from "commits fine today" to "refuses to
    save work."
  - No `.last_reviewed_sha` self-heal - that mechanic is specific to the hub's own `toolkit\\` push
    advancing its own trust anchor; a consumer project has no such file.
  - No internal verify-clean loop: same "re-running is always safe" idempotence the hub script
    settled on when B2 replaced its own former prose verify-clean loop - if a further edit lands
    dirty after this script runs (e.g. correcting the same Work Log entry once more), just run it
    again rather than looping internally.

Usage:
  python checkpoint_consumer.py --project-root "<this project's absolute root>"
      --message "<summary>" [--include PATH [PATH ...]] [--include-all] [--skip-untracked]

Exit codes: 0 = committed+pushed, committed-with-no-remote-configured, or nothing to do;
1 = a commit/push failure occurred, or the project root has no `.git\\` at all; 2 = untracked
files need resolving first - nothing was touched, safe to just re-run with the right flag once
decided.

Run from anywhere; operates on --project-root, not this script's own location (unlike
checkpoint_git.py, which always targets its own two fixed hub repos - this script targets whatever
connected project's session invokes it, so the target repo must be told, not assumed).
"""

import argparse
import subprocess
import sys
from pathlib import Path


def _git(root, args):
    return subprocess.run(['git', '-C', str(root)] + args, capture_output=True, encoding='utf-8')


def is_repo(root):
    return (Path(root) / '.git').exists()


def has_origin(root):
    return 'origin' in _git(root, ['remote']).stdout.split()


def tracked_dirty(root):
    """`git status --porcelain`, TRACKED changes only - a leftover untracked file is often the
    deliberate, correct outcome of --skip-untracked/a partial --include, not a problem to warn
    about; only a lingering tracked-file change is."""
    return _git(root, ['status', '--porcelain', '--untracked-files=no']).stdout.strip()


def porcelain_status(root):
    """(tracked, untracked): both lists of repo-relative paths from `git status --porcelain -z`.
    -z gives NUL-delimited, unquoted paths - the plain LF form wraps a path in literal "..."
    (with backslash-escapes) whenever it contains characters like a space+parens combo, a quote, a
    backslash, or non-ASCII bytes, and a naive line[3:] slice then captures those quote characters
    as part of the path, breaking any later `git add --` on it. A rename emits two consecutive
    NUL-terminated fields (new path, then old path); only the new path is kept, matching the LF
    form's old ' -> '-split behavior."""
    proc = _git(root, ['status', '--porcelain', '-z'])
    fields = proc.stdout.split('\0')
    tracked, untracked = [], []
    i = 0
    while i < len(fields):
        entry = fields[i]
        i += 1
        if not entry:
            continue
        code, path = entry[:2], entry[3:]
        if 'R' in code or 'C' in code:
            i += 1  # skip the old-path field a rename/copy carries alongside the new path
        (untracked if code == '??' else tracked).append(path)
    return tracked, untracked


def resolve_untracked(untracked, include, include_all, skip_untracked):
    """Splits `untracked` into (to_stage, unresolved) given this invocation's flags. Nothing here
    guesses - a path only becomes to_stage if it was explicitly named or --include-all/
    --skip-untracked was passed; everything else is unresolved and blocks the run."""
    to_stage, unresolved = [], []
    for path in untracked:
        if include_all or path in include:
            to_stage.append(path)
        elif skip_untracked:
            pass  # explicitly, consciously left alone this round
        else:
            unresolved.append(path)
    return to_stage, unresolved


def describe_push_failure(stderr_text):
    low = stderr_text.lower()
    if 'non-fast-forward' in low or 'fetch first' in low or '[rejected]' in low:
        return ("remote has commit(s) this clone doesn't have (non-fast-forward rejection) - pull, "
                "then re-run checkpoint to retry the push.")
    if ('could not read from remote' in low or 'permission denied' in low
            or 'authentication failed' in low or 'could not resolve host' in low):
        return "no remote access (auth/network/permissions) - check credentials and `git remote -v`."
    if not stderr_text.strip():
        return "push failed with no stderr output - inspect manually (`git -C <repo> push`)."
    return f"push failed: {stderr_text.strip()}"


def main():
    parser = argparse.ArgumentParser(
        description="checkpoint's git mechanics for a connected project's own repo: "
                     "untracked-file-safe, soft no-remote handling."
    )
    parser.add_argument('--project-root', required=True, help="This project's absolute root.")
    parser.add_argument('--message', required=True, help="One-line checkpoint summary.")
    parser.add_argument('--include', nargs='*', default=[],
                         help="Untracked paths (exact, as printed in an [UNTRACKED] report) to "
                              "stage and commit this round.")
    parser.add_argument('--include-all', action='store_true',
                         help="Stage every currently-untracked file.")
    parser.add_argument('--skip-untracked', action='store_true',
                         help="Leave every untracked file not named by --include alone this "
                              "round (commit only tracked changes).")
    args = parser.parse_args()

    root = Path(args.project_root).resolve()

    if not is_repo(root):
        print(f"[ABORT] {root} has no .git - stop and ask the user whether to set one up now; "
              "never skip this silently.")
        sys.exit(1)

    tracked, untracked = porcelain_status(root)
    to_stage, unresolved = resolve_untracked(
        untracked, args.include, args.include_all, args.skip_untracked)

    if unresolved:
        print("[UNTRACKED] untracked file(s) found - nothing has been touched. Decide, per file, "
              "whether each belongs in this checkpoint (a real new file this session wrote) or "
              "should be left alone (a scratch/temp file). Re-run with --include <path...> to "
              "stage specific ones and/or --skip-untracked to leave everything else untouched, or "
              "--include-all to stage everything listed below.")
        for p in unresolved:
            print(f"    {p}")
        sys.exit(2)

    _git(root, ['add', '-u'])
    for path in to_stage:
        _git(root, ['add', '--', path])

    if not tracked and not to_stage:
        print("[CLEAN] nothing to commit this round.")
        sys.exit(0)

    commit = _git(root, ['commit', '-m', f'Checkpoint: {args.message}'])
    if commit.returncode != 0:
        print(f"[FAIL] commit failed: {(commit.stderr + commit.stdout).strip()}")
        sys.exit(1)
    print(f"[COMMITTED] {commit.stdout.strip()}")

    if not has_origin(root):
        print("[COMMITTED-NO-REMOTE] no 'origin' remote configured - committed locally, push "
              "skipped. A local-only project is a normal, everyday state, not an error.")
        dirty = tracked_dirty(root)
        print("[CLEAN] working tree (tracked files)." if not dirty else
              f"[WARNING] still uncommitted TRACKED changes:\n{dirty}")
        sys.exit(0 if not dirty else 1)

    push = _git(root, ['push'])
    if push.returncode != 0:
        print(f"[BLOCKED] push failed - {describe_push_failure(push.stderr)}")
        dirty = tracked_dirty(root)
        print("[CLEAN] working tree (tracked files)." if not dirty else
              f"[WARNING] still uncommitted TRACKED changes:\n{dirty}")
        sys.exit(1)
    print("[PUSHED].")

    dirty = tracked_dirty(root)
    print("[CLEAN] working tree (tracked files)." if not dirty else
          f"[WARNING] still uncommitted TRACKED changes:\n{dirty}")
    sys.exit(0 if not dirty else 1)


if __name__ == '__main__':
    main()
