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
  --approve   Only valid after a --check left a pending PASS. Re-fetches to confirm origin/main
              hasn't moved since the diff was shown, merges (fast-forward), then runs a FOURTH
              gate: the full check_tower_crane.py (both passes, including Pass B's cross-consumer
              drift scan) against the now-live merged content and the real consumers\\ registry -
              something only possible post-merge, since Pass B needs consumers\\ (outer repo) and a
              real toolkit\\ location, neither reachable from the pre-merge worktree. A FAIL here
              automatically rolls the merge back (fast-forward makes this a clean `git reset
              --hard`) rather than leaving a broken state landed. Only on a clean pass does
              last_reviewed_sha actually advance.
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
              write, never mutates state. Prints one line. Safe on any cadence (resume, cron) -
              never triggers the full review gate; that stays --check, user-initiated only.
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

    diff_text = _git(['diff', base, target]).stdout
    save_pending({'base': base, 'target': target})
    print("[PASS] All mechanical gates passed against the incoming content.")
    print()
    print("=== BEGIN DIFF (last_reviewed_sha..origin/main, literal, unabridged) ===")
    print(diff_text)
    print("=== END DIFF ===")
    print()
    print("Quote the diff above VERBATIM in your own chat-visible response (fenced code block), "
          "together with your own plain-language assessment - never the diff alone, never a "
          "verdict alone, and never relying on this tool output alone to convey it, since tool "
          "call results are not guaranteed visible to the user. Then:")
    print("  python scripts\\update_toolkit.py --approve   (on the user's yes)")
    print("  python scripts\\update_toolkit.py --reject    (on the user's no)")


def cmd_approve(cfg):
    print("=== update_toolkit.py --approve ===")
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

    pre_merge_sha = _git(['rev-parse', 'HEAD']).stdout.strip()
    _git(['merge', '--ff-only', pending['target']])

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

    write_last_reviewed(pending['target'])
    clear_pending()
    print(f"Approved. Trusted baseline advanced to {pending['target'][:8]}. toolkit\\ is up to date.")


def cmd_notify():
    """The 'check for update' proactive notice (design\\local_first_reframe.md): a plain fetch +
    comparison against last_reviewed_sha, no LLM, no golden suite, no pending-file write - never
    mutates anything, safe to run on any cadence (resume, cron). Surfaces a single line; never
    triggers the full review gate (that stays --check, user-initiated only)."""
    fetch = _git(['fetch', 'origin'], check=False)
    if fetch.returncode != 0:
        print("[update check] couldn't fetch origin (offline?) - skipping.")
        return

    target = origin_main_sha()
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
    args = parser.parse_args()

    if args.notify:
        cmd_notify()
        return

    cfg = get_shared_config(SHARED_ROOT)

    if args.approve:
        cmd_approve(cfg)
    elif args.reject:
        cmd_reject()
    else:
        cmd_check(cfg)


if __name__ == '__main__':
    main()
