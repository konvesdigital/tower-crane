#!/usr/bin/env python3
"""
checkpoint_git.py - the `checkpoint` action's git mechanics (design\\command_procedure_audit.md's
B2, the largest Shape-B gap that audit found): mechanizes the two-repo commit/guardrail/leak-scan/
push sequence that used to be 100% re-decided from prose (toolkit\\agents_continuity.md's
"checkpoint" step 2) every single invocation. The doc-editing half of checkpoint (step 1 -
updating project_progress.md's Current Status / Next Up / Decisions / Work Log) stays a Claude
Code judgment call, same split as update_toolkit.py keeps the diff-review-and-assessment step out
of its own mechanical --check/--approve.

Two repos live in this folder (design\\local_first_reframe.md's outer/inner split) and this script
handles both in one call:
  - the OUTER project repo (this folder's own root - project_progress.md, consumers\\,
    change_requests\\, config.local.json)
  - the INNER toolkit\\ repo (this file's own SHARED_ROOT) - only touched if it exists and has
    pending changes.

Untracked-file safety (the reason this script exists as more than a thin wrapper around `git add
-A && git commit && git push`): a session sometimes drops a temporary file - a scratch report, a
draft, an experiment - directly in either repo's root. Usually there's nothing unaccounted for,
but that can never be assumed. `git add -u` (stage modifications/deletions to files git ALREADY
tracks) is always safe and runs automatically - no prompt, no friction, in the common case where
nothing new needs a decision. A genuinely NEW (untracked) file is different: it looks identical to
"a legitimate new design doc this session wrote" and "a stray temp file that should never be
committed" from git's point of view, so nothing here even tries to guess which - every untracked
file in either repo is surfaced and must be explicitly resolved (staged via --include/
--include-all, or explicitly left alone via --skip-untracked) before ANYTHING is committed. Same
"never a blind git add -A, scope explicitly" discipline config_lib.py's _commit_scoped() already
applies to routine hub/consumer writes via a fixed candidate-path tuple - checkpoint can't use a
fixed tuple (a session's own edits legitimately land in any tracked file), so it uses a
tracked/untracked split instead: automatic for tracked, always a conscious decision for untracked.

Leak-scan-first ordering (Locked in command_procedure_audit.md, "Leak-scan ordering"): the old
prose order ran check_file_surface.py's outgoing-leak gate only right before the push, after the
inner repo's own commit had already happened - catching a leak at the last possible moment, after
the work of committing to it was already done. This script runs that gate FIRST, before either
repo's commit step: toolkit\\'s pending changes (tracked + whichever untracked files get resolved
into this round) are staged, then scanned against origin/main via check_file_surface.py's new
`--head-sha worktree` mode, before anything is committed anywhere. A FAIL unstages toolkit\\ and
skips its commit/push for this run, but does not block the outer repo, which is unrelated.

last_reviewed_sha self-heal (the "B2 addendum" found live 2026-08-23): a checkpoint
push to toolkit\\'s origin advances origin/main directly (this clone's admin-bypass write access),
but nothing previously touched update_toolkit.py's own trust anchor (.last_reviewed_sha) when that
happened - the next `update_toolkit.py --check`/`--notify` would see a gap and report a false "N
commit(s) available" nag about this same clone's own, already-reviewed-by-writing content. After a
successful toolkit\\ push here, this script advances last_reviewed_sha to the new HEAD directly
(trust-on-first-use already applies - this clone authored the content).

Usage:
  python scripts\\checkpoint_git.py --message "<summary>"
      [--include PATH [PATH ...]] [--include-all] [--skip-untracked]
      [--standing-constraints-note "<one-line reason>"]

Exit codes: 0 = fully succeeded (or nothing to do); 1 = a failure occurred partway through
(leak-scan FAIL, unresolved Standing-Constraints disclosure, a commit/push failure) - read the
printed report for what still needs attention; 2 = untracked files need resolving first - nothing
was touched, safe to just re-run with the right flag once decided.

Run from anywhere; resolves both repo roots relative to this script's own location, not the
caller's cwd.
"""

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config_lib import get_shared_config
import update_toolkit as ut

TOOLKIT_ROOT = Path(__file__).resolve().parent.parent
OUTER_ROOT = TOOLKIT_ROOT.parent


def _git(root, args, check=False):
    return subprocess.run(['git', '-C', str(root)] + args, capture_output=True, text=True, check=check)


def is_repo(root):
    return (Path(root) / '.git').exists()


def has_origin(root):
    return 'origin' in _git(root, ['remote']).stdout.split()


def has_staged_changes(root):
    """True if the index has anything staged right now. `git status --porcelain` has no
    '--cached' flag (an easy mistake - git silently errors on it, which reads as 'nothing staged'
    if the caller only checks stdout); `git diff --cached --quiet` is the correct check: exit 0 =
    nothing staged, exit 1 = something is."""
    return _git(root, ['diff', '--cached', '--quiet']).returncode != 0


def tracked_dirty(root):
    """`git status --porcelain` output, TRACKED changes only (untracked files excluded). Used for
    the end-of-run clean check: a leftover untracked file is often the deliberate, correct outcome
    of --skip-untracked/a partial --include, not a problem to warn about - only a lingering
    tracked-file change (something that should have been committed but wasn't) is."""
    return _git(root, ['status', '--porcelain', '--untracked-files=no']).stdout.strip()


def porcelain_status(root):
    """(tracked_changed, untracked): both are lists of repo-relative paths from `git status
    --porcelain`. A rename's reported path is the NEW path (the part after '-> ')."""
    proc = _git(root, ['status', '--porcelain'])
    tracked, untracked = [], []
    for line in proc.stdout.splitlines():
        if not line:
            continue
        code, path = line[:2], line[3:]
        if ' -> ' in path:
            path = path.split(' -> ', 1)[1]
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
        return ("remote has commit(s) this clone doesn't have (non-fast-forward rejection) - run "
                "`update`, then re-run `checkpoint` to retry the push.")
    if ('could not read from remote' in low or 'permission denied' in low
            or 'authentication failed' in low or 'could not resolve host' in low):
        return "no remote access (auth/network/permissions) - check credentials and `git remote -v`."
    if not stderr_text.strip():
        return "push failed with no stderr output - inspect manually (`git -C <repo> push`)."
    return f"push failed: {stderr_text.strip()}"


def run_leak_scan(cfg):
    """Fetches origin, then runs check_file_surface.py against origin/main..worktree (staged +
    unstaged content already in toolkit\\'s index/working tree - the caller must have already
    staged anything untracked it wants covered, since a truly untracked file is invisible to `git
    diff` regardless of options). Returns (passed: bool, output: str)."""
    _git(TOOLKIT_ROOT, ['fetch', 'origin'])
    proc = subprocess.run(
        [cfg['python_launcher'], str(TOOLKIT_ROOT / 'scripts' / 'check_file_surface.py'),
         '--base-sha', 'origin/main', '--head-sha', 'worktree'],
        capture_output=True, text=True,
    )
    return proc.returncode == 0, proc.stdout + proc.stderr


def run_standing_constraints_check(cfg):
    """AGENTS.md's Standing Constraints section, HEAD vs the current worktree (uncommitted
    changes included). Returns (changed: bool, output: str)."""
    proc = subprocess.run(
        [cfg['python_launcher'], str(TOOLKIT_ROOT / 'scripts' / 'check_standing_constraints.py'),
         '--base', 'HEAD', '--head', 'worktree'],
        capture_output=True, text=True,
    )
    out = proc.stdout + proc.stderr
    return out.lstrip().startswith('[CHANGED]'), out


def toolkit_stage_and_leak_scan(cfg, to_stage):
    """Phase 1 of the toolkit\\ side: stage (tracked + resolved-untracked) and run the leak-scan
    gate - and nothing else. Split out from the commit/push phase below so this can run, and
    complete, BEFORE either repo's commit step (Locked ordering, design\\
    command_procedure_audit.md's "Leak-scan ordering") - the outer repo's own commit happens in
    between this and toolkit_commit_push() in main(). Returns a dict: {'status': 'n/a'|'clean'|
    'no-origin'|'leak-blocked'|'ready', 'changed_this_round': set()} (changed_this_round only set
    when status is 'ready')."""
    if not TOOLKIT_ROOT.exists() or not is_repo(TOOLKIT_ROOT):
        return {'status': 'n/a'}
    tracked, _untracked = porcelain_status(TOOLKIT_ROOT)
    if not tracked and not to_stage:
        return {'status': 'clean'}
    if not has_origin(TOOLKIT_ROOT):
        return {'status': 'no-origin'}

    _git(TOOLKIT_ROOT, ['add', '-u'])
    for path in to_stage:
        _git(TOOLKIT_ROOT, ['add', '--', path])

    print("Running the leak-scan gate BEFORE any commit, in either repo (Locked ordering, "
          "design\\command_procedure_audit.md)...")
    leak_ok, leak_output = run_leak_scan(cfg)
    print(leak_output)
    if not leak_ok:
        _git(TOOLKIT_ROOT, ['reset'])
        return {'status': 'leak-blocked'}

    return {'status': 'ready', 'changed_this_round': set(tracked) | set(to_stage)}


def toolkit_commit_push(cfg, message, changed_this_round, standing_constraints_note):
    """Phase 2 of the toolkit\\ side: the Standing-Constraints disclosure guardrail (only if
    AGENTS.md is among this round's changes), commit, push, and the last_reviewed_sha self-heal.
    Only called when toolkit_stage_and_leak_scan() returned status 'ready' - staging and the
    leak-scan gate have already happened by the time this runs."""
    print("=== toolkit\\ repo: commit/push ===")
    if 'AGENTS.md' in changed_this_round:
        sc_changed, sc_output = run_standing_constraints_check(cfg)
        print(sc_output)
        if sc_changed and not standing_constraints_note:
            _git(TOOLKIT_ROOT, ['reset'])
            print("[BLOCKED] AGENTS.md's Standing Constraints section changed and no "
                  "--standing-constraints-note was given - toolkit\\ unstaged, nothing committed. "
                  "Surface the before/after text above to the user, then re-run with "
                  "--standing-constraints-note \"<one-line reason>\".")
            return False
        commit_msg = f'Checkpoint: {message}'
        if sc_changed:
            commit_msg += f'\n\nStanding-Constraints-changed: {standing_constraints_note}'
    else:
        commit_msg = f'Checkpoint: {message}'

    commit = _git(TOOLKIT_ROOT, ['commit', '-m', commit_msg])
    if commit.returncode != 0:
        print(f"[FAIL] toolkit\\ commit failed: {(commit.stderr + commit.stdout).strip()}")
        return False
    print(f"[COMMITTED] toolkit\\: {commit.stdout.strip()}")

    push = _git(TOOLKIT_ROOT, ['push'])
    push_ok = push.returncode == 0
    if not push_ok:
        print(f"[BLOCKED] toolkit\\ push failed - {describe_push_failure(push.stderr)}")
        print("The outer repo's checkpoint already landed (if it succeeded) - correct its "
              "project_progress.md text to say 'committed locally only, blocked on: <reason>' "
              "(with the SHA) rather than claiming this toolkit\\ change is built/pushed, then "
              "amend with a second small outer-repo commit once fixed. Never leave a stale "
              "'built' claim standing.")
    else:
        print("[PUSHED] toolkit\\.")
        new_head = _git(TOOLKIT_ROOT, ['rev-parse', 'HEAD']).stdout.strip()
        ut.write_last_reviewed(new_head)
        print(f"[last_reviewed_sha] advanced to {new_head[:8]} (self-authored, trust-on-write - "
              "avoids a false 'N commit(s) available' nag about this same push next `update`).")

    dirty = tracked_dirty(TOOLKIT_ROOT)
    print("[CLEAN] toolkit\\ (tracked files)." if not dirty else
          f"[WARNING] toolkit\\ still has uncommitted TRACKED changes:\n{dirty}")
    return push_ok and not dirty


def do_outer(message, to_stage):
    print("=== outer repo ===")
    if not is_repo(OUTER_ROOT):
        print(f"[ABORT] {OUTER_ROOT} has no .git - stop and ask the user whether to set one up "
              "now; never skip this silently.")
        return False
    if not has_origin(OUTER_ROOT):
        print(f"[ABORT] {OUTER_ROOT} has no 'origin' remote configured - stop and ask the user "
              "whether to set one up now; never skip this silently.")
        return False

    _git(OUTER_ROOT, ['add', '-u'])
    for path in to_stage:
        _git(OUTER_ROOT, ['add', '--', path])

    push_ok = True
    if not has_staged_changes(OUTER_ROOT):
        print("[SKIPPED] nothing staged - outer repo has nothing to commit this round.")
    else:
        commit = _git(OUTER_ROOT, ['commit', '-m', f'Checkpoint: {message}'])
        if commit.returncode != 0:
            print(f"[FAIL] outer commit failed: {(commit.stderr + commit.stdout).strip()}")
            return False
        print(f"[COMMITTED] outer repo: {commit.stdout.strip()}")

        push = _git(OUTER_ROOT, ['push'])
        push_ok = push.returncode == 0
        if not push_ok:
            print(f"[BLOCKED] outer push failed - {describe_push_failure(push.stderr)}")
        else:
            print("[PUSHED] outer repo.")

    dirty = tracked_dirty(OUTER_ROOT)
    print("[CLEAN] outer repo (tracked files)." if not dirty else
          f"[WARNING] outer repo still has uncommitted TRACKED changes:\n{dirty}")
    return push_ok and not dirty


def main():
    parser = argparse.ArgumentParser(
        description="checkpoint's git mechanics: both repos, leak-scan-first, untracked-file-safe."
    )
    parser.add_argument('--message', required=True, help="One-line checkpoint summary.")
    parser.add_argument('--include', nargs='*', default=[],
                         help="Untracked paths (exact, as printed in an [UNTRACKED] report) to "
                              "stage and commit this round.")
    parser.add_argument('--include-all', action='store_true',
                         help="Stage every currently-untracked file in both repos.")
    parser.add_argument('--skip-untracked', action='store_true',
                         help="Leave every untracked file not named by --include alone this "
                              "round (commit only tracked changes).")
    parser.add_argument('--standing-constraints-note', default=None,
                         help="Required only if AGENTS.md's Standing Constraints section shows "
                              "[CHANGED] - one-line reason, lands as a commit trailer.")
    args = parser.parse_args()

    _outer_tracked, outer_untracked = porcelain_status(OUTER_ROOT) if is_repo(OUTER_ROOT) else ([], [])
    _toolkit_tracked, toolkit_untracked = (
        porcelain_status(TOOLKIT_ROOT) if TOOLKIT_ROOT.exists() and is_repo(TOOLKIT_ROOT) else ([], []))

    outer_stage, outer_unresolved = resolve_untracked(
        outer_untracked, args.include, args.include_all, args.skip_untracked)
    toolkit_stage, toolkit_unresolved = resolve_untracked(
        toolkit_untracked, args.include, args.include_all, args.skip_untracked)

    if outer_unresolved or toolkit_unresolved:
        print("[UNTRACKED] untracked file(s) found - nothing has been touched. Decide, per file, "
              "whether each belongs in this checkpoint (a new design doc / script this session "
              "wrote for real) or should be left alone (a scratch/temp file). Re-run with "
              "--include <path...> to stage specific ones and/or --skip-untracked to leave "
              "everything else untouched, or --include-all to stage everything listed below.")
        if outer_unresolved:
            print(f"  outer repo ({OUTER_ROOT}):")
            for p in outer_unresolved:
                print(f"    {p}")
        if toolkit_unresolved:
            print(f"  toolkit\\ ({TOOLKIT_ROOT}):")
            for p in toolkit_unresolved:
                print(f"    {p}")
        sys.exit(2)

    cfg = get_shared_config(TOOLKIT_ROOT)

    # Leak-scan-first (Locked ordering, design\command_procedure_audit.md): toolkit\'s staging and
    # leak-scan gate run to completion here, BEFORE either repo's commit step - the outer repo's
    # own commit (do_outer, below) and toolkit\'s own commit (toolkit_commit_push, further below)
    # both happen only after this resolves.
    print("=== toolkit\\ repo: staging + leak-scan ===")
    tk = toolkit_stage_and_leak_scan(cfg, toolkit_stage)
    if tk['status'] == 'n/a':
        print("[N/A] toolkit\\ doesn't exist here - nothing to do.")
    elif tk['status'] == 'clean':
        print("[CLEAN] toolkit\\ has nothing to commit this round.")
    elif tk['status'] == 'no-origin':
        print("[ABORT] toolkit\\ has no 'origin' remote configured - stop and ask the user "
              "whether to set one up now; never skip this silently.")
    elif tk['status'] == 'leak-blocked':
        print("[BLOCKED] leak-scan gate FAILED - toolkit\\ unstaged, nothing committed. Fix the "
              "flagged content, then re-run checkpoint. (The outer repo is unaffected and still "
              "gets committed/pushed normally, below.)")
    print()

    outer_ok = do_outer(args.message, outer_stage)
    print()

    if tk['status'] == 'ready':
        toolkit_ok = toolkit_commit_push(cfg, args.message, tk['changed_this_round'],
                                          args.standing_constraints_note)
    else:
        toolkit_ok = tk['status'] in ('n/a', 'clean')

    sys.exit(0 if (outer_ok and toolkit_ok) else 1)


if __name__ == '__main__':
    main()
