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
procedure (toolkit\\CLAUDE.md's "update" section, alongside checkpoint/resume), since it is
judgment work with no deterministic algorithm.

Two-call protocol, because the review gate needs a human/Claude in the loop between the mechanical
check and the mechanical merge:
  --check     (default) fetch + diff last_reviewed_sha vs origin/main.
                Empty diff -> fast-forwards silently, advances last_reviewed_sha, done.
                Non-empty diff -> runs the golden suite against the fetched content in a throwaway
                git worktree (never touches this clone's real working tree). FAIL hard-blocks
                (Locked 2026-07-25, no override) - nothing merges. PASS prints the literal diff
                text and leaves a pending-review marker for --approve/--reject.
  --approve   Only valid after a --check left a pending PASS. Re-fetches to confirm origin/main
              hasn't moved since the diff was shown, merges (fast-forward), advances
              last_reviewed_sha to the new HEAD.
  --reject    Clears the pending marker. Nothing was ever merged during --check (the golden suite
              ran against a worktree, not this clone), so rejecting is just "forget the pending
              review" - the old trusted baseline was never actually left.

last_reviewed_sha lives at toolkit\\.last_reviewed_sha (gitignored - design\\update_trust_review.md's
resolved storage-location decision: a property of this specific clone, not the toolkit content).
First run (file absent): trust-on-first-use - the clone's current local HEAD becomes the initial
baseline (same bootstrap assumption as an SSH known_hosts first connection or a fresh lockfile
install; nothing to review yet since nothing has been pulled through this gate before).

Update is always the user's choice, never assumed or forced (Locked 2026-07-26) - this script never
runs itself; nothing schedules --check automatically. See "Check for update" (separate, not-yet-built
proactive notice) for the low-lift heads-up half of that story.
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


def run_golden_suite_against(target_sha, cfg):
    """Checks out target_sha into a throwaway worktree and runs ITS OWN check_tower_crane.py
    golden suite only (--skip-reference: consumers\\/config.local.json live outside the inner
    repo's tree post-split, so pass B has nothing valid to scan from an ephemeral worktree
    location). Returns (passed: bool, output: str)."""
    worktree_dir = Path(tempfile.gettempdir()) / f"tower_crane_update_review_{os.getpid()}"
    if worktree_dir.exists():
        shutil.rmtree(worktree_dir, ignore_errors=True)

    _git(['worktree', 'add', '--detach', str(worktree_dir), target_sha])
    try:
        # get_shared_config needs a config.local.json to exist; reuse this clone's own (per-machine
        # values are valid regardless of the temporary path - shared_root self-corrects harmlessly).
        shutil.copy2(CONFIG_PATH, worktree_dir / 'config.local.json')
        proc = subprocess.run(
            [cfg['python_launcher'], str(worktree_dir / 'scripts' / 'check_tower_crane.py'), '--skip-reference'],
            capture_output=True, text=True,
        )
        return proc.returncode == 0, proc.stdout + proc.stderr
    finally:
        _git(['worktree', 'remove', '--force', str(worktree_dir)], check=False)
        _git(['worktree', 'prune'], check=False)


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
          "golden-suite gate before any review is shown.")
    passed, suite_output = run_golden_suite_against(target, cfg)
    print(suite_output)
    if not passed:
        print("[BLOCKED] Golden suite FAILED against the incoming content - update refused, no "
              "override (Locked 2026-07-25). The old trusted baseline is untouched. Investigate, "
              "or file a fork+PR fix upstream.")
        clear_pending()
        sys.exit(1)

    diff_text = _git(['diff', base, target]).stdout
    save_pending({'base': base, 'target': target})
    print("[PASS] Golden suite passed against the incoming content.")
    print()
    print("=== BEGIN DIFF (last_reviewed_sha..origin/main, literal, unabridged) ===")
    print(diff_text)
    print("=== END DIFF ===")
    print()
    print("Review the diff above with the user, alongside a plain-language assessment of what it "
          "does and why - never the diff alone, never a verdict alone. Then:")
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

    _git(['merge', '--ff-only', pending['target']])
    write_last_reviewed(pending['target'])
    clear_pending()
    print(f"Approved. Trusted baseline advanced to {pending['target'][:8]}. toolkit\\ is up to date.")


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
    args = parser.parse_args()

    cfg = get_shared_config(SHARED_ROOT)

    if args.approve:
        cmd_approve(cfg)
    elif args.reject:
        cmd_reject()
    else:
        cmd_check(cfg)


if __name__ == '__main__':
    main()
