#!/usr/bin/env python3
"""
update_toolkit.py - the `update` action (design\\local_first_reframe.md's "`update` action
mechanics", design\\update_trust_review.md's Fix 1): pulls this inner toolkit repo's own `origin`
remote (the public tower_crane repo, or whichever upstream this clone points at) under a
diff-review trust gate, instead of a blind `git pull`.

Mechanical-gate-then-agent split (Locked 2026-07-26, mirrors run_automation.py's Piece 3 shape):
this script owns every deterministic step - fetch, diff-against-last-reviewed decision, golden
suite, and the post-approval merge. The diff-review-and-assessment step itself (reading the
literal diff, writing a plain-language read of what it does) is NOT here - it stays a Claude Code
procedure (toolkit\\AGENTS.md's "update" section, alongside checkpoint/resume), since it is
judgment work with no deterministic algorithm.

Two-call protocol, because the review gate needs a human/Claude in the loop between the mechanical
check and the mechanical merge:
  --check     (default) fetch + diff last_reviewed_sha vs origin/main.
                Empty diff -> fast-forwards silently, advances last_reviewed_sha, done.
                Non-empty diff -> runs three mechanical gates against the fetched content, all in a
                throwaway git worktree or via direct ref comparison (never touches this clone's
                real working tree): check_tower_crane.py's golden suite (Pass A only - Pass B needs
                the live consumers\\ registry, see below); a consistency_check.py static-analysis
                sweep over every .py file in hooks\\/scripts\\/agents\\ (closes the gap the golden
                suite leaves for a brand-new script with no tests\\<tool>\\ fixtures yet); and
                check_file_surface.py's file-surface classifier (assumes an adversary, not just
                carelessness - catches a non-Python script, a script outside its expected home, a
                second AI-directive file, or a binary blob). Any FAIL hard-blocks (Locked
                2026-07-25 for the golden suite, extended 2026-07-27 to the other two gates - no
                override). PASS prints the literal diff text and leaves a pending-review marker for
                --approve/--reject.
  --approve [--through <n-or-sha>]
              Only valid after a --check left a pending PASS. Re-fetches to confirm origin/main
              hasn't moved since the diff was shown, merges (fast-forward), then runs a FOURTH
              gate: the full check_tower_crane.py (both passes, including Pass B's cross-consumer
              drift scan) against the now-live merged content and the real consumers\\ registry -
              something only possible post-merge, since Pass B needs consumers\\ (outer repo) and a
              real toolkit\\ location, neither reachable from the pre-merge worktree. A FAIL here
              automatically rolls the merge back (fast-forward makes this a clean `git reset
              --hard`) rather than leaving a broken state landed. Only on a clean pass does
              last_reviewed_sha actually advance.
                Without --through: approves every pending commit shown by --check (all the way to
              origin/main). With --through <n-or-sha>: partial approval, added 2026-07-27 (security
              stress-test pass, design\\security_stress_test.md) - fast-forwards only to the given
              commit (a 1-based index into the pending-commit list --check printed, or one of those
              commits' own SHAs), leaving the remaining, newer pending commits queued. Lets a large
              batch of upstream commits be reviewed a few at a time across multiple `update` calls
              instead of forcing one all-or-nothing read of a potentially large diff in one sitting
              (a real residual risk this project's own diff-size gate only partially covers - see
              the design doc). The mechanical gates below still always run against the FULL pending
              range regardless of --through, so nothing merges - partial or otherwise - until
              everything currently fetched has passed every gate; --through only controls how much
              of what already passed gets merged and trusted in this round.
  --reject    Clears the pending marker. Nothing was ever merged during --check (the golden suite
              ran against a worktree, not this clone), so rejecting is just "forget the pending
              review" - the old trusted baseline was never actually left.

last_reviewed_sha lives at toolkit\\.last_reviewed_sha (gitignored - design\\update_trust_review.md's
resolved storage-location decision: a property of this specific clone, not the toolkit content).
First run (file absent): trust-on-first-use - the clone's current local HEAD becomes the initial
baseline (same bootstrap assumption as an SSH known_hosts first connection or a fresh lockfile
install; nothing to review yet since nothing has been pulled through this gate before).

Update is always the user's choice, never assumed or forced (Locked 2026-07-26) - this script never
runs itself; nothing schedules --check automatically.

  --notify    The "check for update" proactive notice (design\\local_first_reframe.md): plain
              fetch + comparison against last_reviewed_sha, no golden suite, no pending-file
              write, never mutates state. Prints one line per direction. Safe on any cadence
              (resume, cron) - never triggers the full review gate; that stays --check,
              user-initiated only. Also checks the outgoing direction
              (design\\cross_machine_toolkit_sync.md): local HEAD ahead of origin/main means an
              earlier checkpoint's push was rejected or never completed - surfaced independently of
              the incoming last_reviewed_sha comparison, so a stranded local commit is never
              silently forgotten by a later session on any machine.

Remote-identity check (added 2026-07-27, security stress-test pass, design\\security_stress_test.md):
every subcommand that talks to `origin` first confirms `git remote get-url origin` still matches
the expected canonical URL recorded in config.local.json (`publish.public_repo_remote`). Nothing
before this defended against `origin` silently being repointed (local tampering, a bad clone-URL
paste, a typosquatted fork) - the diff-review gate would have faithfully reviewed and let a user
approve content from an entirely different repo with no structural signal anything was wrong.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config_lib import get_shared_config

SHARED_ROOT = Path(__file__).resolve().parent.parent
LAST_REVIEWED_PATH = SHARED_ROOT / '.last_reviewed_sha'
PENDING_PATH = SHARED_ROOT / '.update_pending.json'
CONFIG_PATH = SHARED_ROOT / 'config.local.json'
EMPTY_TREE_SHA = '4b825dc642cb6eb9a060e54bf8d69288fbee4904'  # git's canonical empty-tree object


def _normalize_remote_url(url):
    """Loose-compare git remote URLs: strip a trailing '.git', trailing slash, and case-fold the
    host - 'https://github.com/x/y.git' and 'https://github.com/x/y' are the same remote."""
    u = url.strip().rstrip('/')
    if u.lower().endswith('.git'):
        u = u[:-4]
    return u.lower()


def _origin_remote_mismatch(cfg):
    """Returns None if `origin` matches config.local.json's publish.public_repo_remote (or
    nothing's configured to check against), else (expected, actual) strings describing the
    mismatch."""
    expected = cfg.get('publish', {}).get('public_repo_remote')
    if not expected:
        return None
    actual = _git(['remote', 'get-url', 'origin'], check=False)
    if actual.returncode != 0:
        return (expected, '(no origin remote configured)')
    if _normalize_remote_url(actual.stdout) != _normalize_remote_url(expected):
        return (expected, actual.stdout.strip())
    return None


def check_origin_remote(cfg):
    """Hard-abort version of the remote-identity check, used by --check/--approve: prevents a
    silently repointed origin (local tampering, a bad clone-URL paste, a typosquatted fork) from
    having its content diff-reviewed and approved as if it were the real upstream, with no signal
    anything was wrong."""
    mismatch = _origin_remote_mismatch(cfg)
    if mismatch is None:
        return
    expected, actual = mismatch
    print(f"[ABORT] 'origin' does not match the expected upstream. Configured (trusted): "
          f"{expected!r}. Actual, this clone: {actual!r}. This could mean origin was silently "
          "repointed (local tampering, a bad clone-URL paste, a typosquatted fork) - refusing to "
          "review or merge anything until this is confirmed deliberate. If you intentionally "
          "changed upstream, update config.local.json's publish.public_repo_remote to match.")
    sys.exit(1)


def write_utf8(path, content):
    path.write_text(content, encoding='utf-8', newline='\n')


def _git(args, check=True):
    return subprocess.run(['git', '-C', str(SHARED_ROOT)] + args,
                           capture_output=True, text=True, check=check)


def _is_dirty():
    return bool(_git(['status', '--porcelain']).stdout.strip())


def _sha_exists(sha):
    return subprocess.run(
        ['git', '-C', str(SHARED_ROOT), 'cat-file', '-e', f'{sha}^{{commit}}'],
        capture_output=True, text=True,
    ).returncode == 0


def read_last_reviewed():
    if not LAST_REVIEWED_PATH.exists():
        return None
    sha = LAST_REVIEWED_PATH.read_text(encoding='utf-8').strip()
    return sha or None


def write_last_reviewed(sha):
    write_utf8(LAST_REVIEWED_PATH, sha + '\n')


def load_pending():
    if not PENDING_PATH.exists():
        return None
    try:
        return json.loads(PENDING_PATH.read_text(encoding='utf-8'))
    except json.JSONDecodeError:
        return None


def save_pending(data):
    write_utf8(PENDING_PATH, json.dumps(data, indent=2))


def clear_pending():
    PENDING_PATH.unlink(missing_ok=True)


def origin_main_sha():
    return _git(['rev-parse', 'origin/main']).stdout.strip()


def list_pending_commits(base, target):
    """Oldest-first list of commit SHAs strictly between base (exclusive) and target (inclusive).
    The natural atomic unit for partial review/approval: a fast-forward merge can only ever land a
    contiguous prefix of this list, never an arbitrary subset, so commits (not files) are what
    --approve --through addresses."""
    proc = _git(['log', '--reverse', '--format=%H', f'{base}..{target}'])
    return [sha for sha in proc.stdout.splitlines() if sha.strip()]


def commit_subject_and_files(sha):
    subject = _git(['log', '-1', '--format=%s', sha]).stdout.strip()
    files = [f for f in _git(['diff-tree', '--no-commit-id', '--name-only', '-r', sha]).stdout.splitlines() if f.strip()]
    return subject, files


def resolve_through(value, commits):
    """value is either a 1-based index into `commits` (oldest-first, matching what --check prints)
    or a SHA/unambiguous-prefix of one of those commits. Returns the resolved full SHA, or None if
    value doesn't identify any commit in the pending list."""
    if value.isdigit():
        idx = int(value)
        if 1 <= idx <= len(commits):
            return commits[idx - 1]
        return None
    proc = _git(['rev-parse', '--verify', value], check=False)
    if proc.returncode != 0:
        return None
    resolved = proc.stdout.strip()
    return resolved if resolved in commits else None


def create_review_worktree(target_sha):
    worktree_dir = Path(tempfile.gettempdir()) / f"tower_crane_update_review_{os.getpid()}"
    if worktree_dir.exists():
        shutil.rmtree(worktree_dir, ignore_errors=True)
    _git(['worktree', 'add', '--detach', str(worktree_dir), target_sha])
    return worktree_dir


def remove_review_worktree(worktree_dir):
    _git(['worktree', 'remove', '--force', str(worktree_dir)], check=False)
    _git(['worktree', 'prune'], check=False)


def run_golden_suite_against(worktree_dir, cfg):
    """Runs check_tower_crane.py's golden suite only (--skip-reference: consumers\\/
    config.local.json live outside the inner repo's tree post-split, so pass B has nothing valid to
    scan from an ephemeral worktree location - that gap is covered separately, post-merge, by
    run_post_merge_check()). Returns (passed: bool, output: str)."""
    # get_shared_config needs a config.local.json to exist; reuse this clone's own (per-machine
    # values are valid regardless of the temporary path - shared_root self-corrects harmlessly).
    shutil.copy2(CONFIG_PATH, worktree_dir / 'config.local.json')
    proc = subprocess.run(
        [cfg['python_launcher'], str(worktree_dir / 'scripts' / 'check_tower_crane.py'), '--skip-reference'],
        capture_output=True, text=True,
    )
    return proc.returncode == 0, proc.stdout + proc.stderr


def run_consistency_sweep(worktree_dir, cfg):
    """Runs hooks\\consistency_check.py (static analysis - undefined names, arity mismatches,
    string-key drift) against every .py file under hooks\\/scripts\\/agents\\ in the incoming
    worktree. Closes the gap the golden suite leaves: Pass A only exercises tools that already have
    tests\\<tool>\\ fixtures, so a brand-new script gets zero automatic scrutiny otherwise. Returns
    (passed: bool, output: str)."""
    hook_script = worktree_dir / 'hooks' / 'consistency_check.py'
    if not hook_script.exists():
        return True, "--- consistency_check.py sweep ---\n  (no hooks\\consistency_check.py in incoming content - skipping)"

    targets = []
    for sub in ('hooks', 'scripts', 'agents'):
        d = worktree_dir / sub
        if d.is_dir():
            targets.extend(sorted(d.glob('*.py')))

    # sandbox project dir, same convention as check_tower_crane.py's own invoke_golden_suite() -
    # the hook needs CLAUDE_PROJECT_DIR and writes logs there; without it, it silently skips.
    sandbox = Path(tempfile.gettempdir()) / f"update_toolkit_consistency_sandbox_{os.getpid()}"
    sandbox.mkdir(parents=True, exist_ok=True)
    saved_proj_dir = os.environ.get('CLAUDE_PROJECT_DIR')
    os.environ['CLAUDE_PROJECT_DIR'] = str(sandbox)

    lines = ["--- consistency_check.py sweep (every script in the incoming content) ---"]
    ok = True
    try:
        for f in targets:
            proc = subprocess.run(
                [cfg['python_launcher'], str(hook_script), str(f)],
                capture_output=True, text=True,
            )
            rel = f.relative_to(worktree_dir)
            if proc.returncode == 2:
                ok = False
                lines.append(f"  [FAIL] {rel}")
                for line in (proc.stdout + proc.stderr).splitlines():
                    lines.append(f"    {line}")
            else:
                lines.append(f"  [PASS] {rel}")
    finally:
        if saved_proj_dir is None:
            os.environ.pop('CLAUDE_PROJECT_DIR', None)
        else:
            os.environ['CLAUDE_PROJECT_DIR'] = saved_proj_dir
        shutil.rmtree(sandbox, ignore_errors=True)

    return ok, '\n'.join(lines)


def run_file_surface_check(base_sha, target_sha, cfg):
    """Runs check_file_surface.py directly against this clone's own git history (base_sha and
    target_sha are both already fetched/reachable here - no worktree checkout needed, since the
    script reads blobs via `git show`/`git diff`, never the working tree). Returns (passed, output)."""
    script = SHARED_ROOT / 'scripts' / 'check_file_surface.py'
    proc = subprocess.run(
        [cfg['python_launcher'], str(script), '--base-sha', base_sha, '--head-sha', target_sha],
        capture_output=True, text=True,
    )
    return proc.returncode == 0, proc.stdout + proc.stderr


def run_post_merge_check(cfg):
    """Runs the FULL check_tower_crane.py (both passes) against the now-live merged toolkit\\ and
    the real consumers\\ registry - only possible post-merge, since Pass B needs the outer repo's
    consumers\\ folder and a real (not ephemeral-worktree) toolkit\\ location. Returns (passed,
    output)."""
    proc = subprocess.run(
        [cfg['python_launcher'], str(SHARED_ROOT / 'scripts' / 'check_tower_crane.py')],
        capture_output=True, text=True, cwd=str(SHARED_ROOT),
    )
    return proc.returncode == 0, proc.stdout + proc.stderr


def cmd_check(cfg):
    print("=== update_toolkit.py --check ===")
    check_origin_remote(cfg)
    if _is_dirty():
        print("[ABORT] toolkit\\ working tree has uncommitted changes - commit or stash them first.")
        sys.exit(1)

    _git(['fetch', 'origin'])
    target = origin_main_sha()

    base = read_last_reviewed()
    if base is None:
        base = _git(['rev-parse', 'HEAD']).stdout.strip()
        write_last_reviewed(base)
        print(f"[FIRST RUN] No trust anchor yet - initialized last_reviewed_sha to this clone's "
              f"current HEAD ({base[:8]}), trust-on-first-use.")
    elif not _sha_exists(base):
        print(f"[WARNING] Recorded last_reviewed_sha ({base[:8]}) no longer exists in this clone's "
              "history (rewritten/force-pushed?) - falling back to a full review against an empty "
              "tree so nothing upstream goes unreviewed.")
        base = EMPTY_TREE_SHA

    if not _git(['diff', '--quiet', base, target], check=False).returncode:
        _git(['merge', '--ff-only', target], check=False)
        if base != target:
            write_last_reviewed(target)
        print(f"Already up to date - no content differs between the last-reviewed baseline and "
              f"origin/main ({target[:8]}). Nothing to review.")
        return

    print(f"Non-empty diff: last-reviewed {base[:8]} .. origin/main {target[:8]}. Running the "
          "mechanical gates before any review is shown.")

    worktree_dir = create_review_worktree(target)
    try:
        golden_ok, golden_output = run_golden_suite_against(worktree_dir, cfg)
        print(golden_output)
        consistency_ok, consistency_output = run_consistency_sweep(worktree_dir, cfg)
        print(consistency_output)
    finally:
        remove_review_worktree(worktree_dir)

    surface_ok, surface_output = run_file_surface_check(base, target, cfg)
    print(surface_output)

    if not (golden_ok and consistency_ok and surface_ok):
        print("[BLOCKED] One or more mechanical gates FAILED against the incoming content - update "
              "refused, no override (Locked 2026-07-25, extended 2026-07-27 to the consistency "
              "sweep and file-surface classifier). The old trusted baseline is untouched. "
              "Investigate, or file a fork+PR fix upstream.")
        clear_pending()
        sys.exit(1)

    save_pending({'base': base, 'target': target})
    print("[PASS] All mechanical gates passed against the incoming content.")
    print()

    commits = list_pending_commits(base, target)
    print(f"=== PENDING COMMITS ({len(commits)}, oldest first) ===")
    for i, sha in enumerate(commits, 1):
        subject, files = commit_subject_and_files(sha)
        print(f"  [{i}] {sha[:8]}  {subject}")
        for f in files:
            print(f"        {f}")
    print("=== END PENDING COMMITS ===")
    print()

    print("=== BEGIN DIFF (one section per pending commit, literal, unabridged) ===")
    for i, sha in enumerate(commits, 1):
        subject, _files = commit_subject_and_files(sha)
        show = _git(['show', sha]).stdout
        print(f"--- COMMIT [{i}/{len(commits)}] {sha[:8]}: {subject} ---")
        print(show)
        print(f"--- END COMMIT [{i}] ---")
    print("=== END DIFF ===")
    print()
    print("Present the pending-commit list above to the user FIRST, as a short line-item index. "
          "Ask how many of the leading (oldest) items they want to review right now - a large batch "
          "doesn't have to be read in one sitting (design\\security_stress_test.md). For whichever "
          "commits they choose to decide on this round, quote that commit's own diff section above "
          "VERBATIM in your own chat-visible response (fenced code block), together with your own "
          "plain-language assessment - never the diff alone, never a verdict alone, and never "
          "relying on this tool output alone to convey it, since tool call results are not "
          "guaranteed visible to the user. Then:")
    print("  python scripts\\update_toolkit.py --approve                    (approve ALL pending commits)")
    print("  python scripts\\update_toolkit.py --approve --through <n>      (approve only through "
          "item <n> in the list above - the rest stay queued; running `update` again later reviews "
          "just the remainder)")
    print("  python scripts\\update_toolkit.py --reject                     (discard this round; "
          "nothing was merged)")


def cmd_approve(cfg, through=None):
    print("=== update_toolkit.py --approve ===")
    check_origin_remote(cfg)
    if _is_dirty():
        print("[ABORT] toolkit\\ working tree has uncommitted changes - commit or stash them first.")
        sys.exit(1)

    pending = load_pending()
    if pending is None:
        print("[ABORT] No pending review - run --check first.")
        sys.exit(1)

    _git(['fetch', 'origin'])
    current_target = origin_main_sha()
    if current_target != pending['target']:
        print(f"[ABORT] origin/main moved since the reviewed diff was shown (was "
              f"{pending['target'][:8]}, now {current_target[:8]}) - re-run --check to review the "
              "new state before approving.")
        sys.exit(1)

    commits = list_pending_commits(pending['base'], pending['target'])
    if through is None:
        merge_target = pending['target']
    else:
        merge_target = resolve_through(through, commits)
        if merge_target is None:
            print(f"[ABORT] '{through}' isn't one of the pending commits the last --check showed "
                  f"(expected a 1-based index from 1..{len(commits)}, or one of their SHAs).")
            sys.exit(1)

    pre_merge_sha = _git(['rev-parse', 'HEAD']).stdout.strip()
    _git(['merge', '--ff-only', merge_target])

    print("Merged. Running the post-merge gate: full check_tower_crane.py (both passes) against "
          "the now-live content and the real consumers\\ registry...")
    post_ok, post_output = run_post_merge_check(cfg)
    print(post_output)
    if not post_ok:
        _git(['reset', '--hard', pre_merge_sha])
        print("[ROLLED BACK] Post-merge check_tower_crane.py found a FAILURE - most likely "
              "cross-consumer breakage that only the real, live consumers\\ registry could reveal "
              "(the pre-merge gate can't see it from an ephemeral worktree). The merge has been "
              "reverted; the old trusted baseline is untouched. Hard block, no override (Locked "
              "2026-07-27, same discipline as the pre-merge golden-suite gate).")
        clear_pending()
        sys.exit(1)

    write_last_reviewed(merge_target)
    clear_pending()
    remaining = len(list_pending_commits(merge_target, pending['target']))
    if remaining:
        approved_count = len(commits) - remaining
        print(f"Approved through {merge_target[:8]} ({approved_count}/{len(commits)} pending "
              f"commits merged). {remaining} commit(s) remain queued - run `update` again to "
              "review the rest.")
    else:
        print(f"Approved. Trusted baseline advanced to {merge_target[:8]}. toolkit\\ is up to date.")


def cmd_notify(cfg):
    """The 'check for update' proactive notice (design\\local_first_reframe.md): a plain fetch +
    comparison against last_reviewed_sha, no LLM, no golden suite, no pending-file write - never
    mutates anything, safe to run on any cadence (resume, cron). Surfaces a single line; never
    triggers the full review gate (that stays --check, user-initiated only). The remote-identity
    check here is a WARN, not an abort - --notify's whole point is a safe, side-effect-free
    heads-up, so it still reports a mismatched origin without blocking `resume`."""
    mismatch = _origin_remote_mismatch(cfg)
    if mismatch is not None:
        expected, actual = mismatch
        print(f"[update check] [WARN] 'origin' does not match the expected upstream (configured: "
              f"{expected!r}, actual: {actual!r}) - run `update` for the full check, which will "
              "abort until this is resolved.")

    fetch = _git(['fetch', 'origin'], check=False)
    if fetch.returncode != 0:
        print("[update check] couldn't fetch origin (offline?) - skipping.")
        return

    target = origin_main_sha()

    # Outgoing check (design\\cross_machine_toolkit_sync.md): local HEAD ahead of origin/main means
    # an earlier checkpoint's push was rejected or never ran - independent of the incoming
    # last_reviewed_sha comparison below, and checked even before a baseline exists.
    head = _git(['rev-parse', 'HEAD']).stdout.strip()
    if head != target:
        ahead = _git(['rev-list', f'{target}..{head}', '--count']).stdout.strip()
        if ahead != '0':
            print(f"[update check] toolkit\\ has {ahead} local commit(s) not yet pushed to origin "
                  "- run `checkpoint` to retry the push, or `update` first if origin has moved "
                  "ahead too.")

    base = read_last_reviewed()
    if base is None or not _sha_exists(base):
        print("[update check] no reviewed baseline yet - run `update` to establish one.")
        return

    if not _git(['diff', '--quiet', base, target], check=False).returncode:
        print("[update check] toolkit\\ is up to date - nothing to review.")
        return

    count = _git(['rev-list', f'{base}..{target}', '--count']).stdout.strip()
    print(f"[update check] a tower_crane update is available ({count} commit(s) since last "
          "review) - run `update` to review and pull it in.")


def cmd_reject():
    print("=== update_toolkit.py --reject ===")
    pending = load_pending()
    if pending is None:
        print("Nothing pending to reject.")
        return
    print(f"Rejected. Trusted baseline stays at {pending['base'][:8]}; nothing was merged (the "
          "golden suite ran against a throwaway worktree during --check, never this clone's real "
          "working tree). Tools go stale but stay safe - a fully supported, indefinite state.")
    clear_pending()


def main():
    parser = argparse.ArgumentParser(
        description="The `update` action: diff-reviewed pull of toolkit\\'s origin remote."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--check', action='store_true',
                        help="Fetch and run the review gate (default if no flag given).")
    group.add_argument('--approve', action='store_true', help="Finalize a pending --check PASS.")
    group.add_argument('--reject', action='store_true', help="Discard a pending --check PASS.")
    group.add_argument('--notify', action='store_true',
                        help="Lightweight one-line heads-up, no golden suite, no state mutation.")
    parser.add_argument('--through', default=None,
                         help="With --approve: partial approval, only through this pending commit "
                              "(1-based index from the last --check's list, or one of those "
                              "commits' own SHAs). Ignored by every other flag.")
    args = parser.parse_args()

    cfg = get_shared_config(SHARED_ROOT)

    if args.notify:
        cmd_notify(cfg)
        return

    if args.approve:
        cmd_approve(cfg, through=args.through)
    elif args.reject:
        cmd_reject()
    else:
        cmd_check(cfg)


if __name__ == '__main__':
    main()
