#!/usr/bin/env python3
"""
remove_hub.py - reverses setup_machine.md for THIS machine (design\\connect_disconnect.md,
design\\hub_uninstall_end_state.md). Disconnects every consumer connected on this machine (this-only
mode, so any OTHER machine's connection to the same consumer is left alone), clears this machine's
own gitignored per-machine hub state, and removes the 'origin' remote from both the outer hub repo
and toolkit\\ - so a later setup_machine.md run here starts genuinely clean - no consumer thinks
this machine is still connected, nothing here remembers this machine was ever configured, and this
clone can no longer push/pull at all.

Never touches tracked FILE CONTENT or history in either repo, or .claude\\hooks\\ (Rung 2's tracked-
across-this-operator's-own-machines personal hook content, design\\resource_sharing_model.md's
three-rung ladder - not this hub's to delete) - only the 'origin' remote entry, which is local-only
and fully reversible (`git remote add origin <url>` reattaches). Never touches GitHub or any other
machine's own clone. Physically deleting the hub folder tree afterward, if wanted, is left to the
user - this script only clears state/connections and reports whether that's actually safe yet
(design\\hub_uninstall_end_state.md's dirty/unpushed check); it never rm -rf's its own running
directory.
"""

import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config_lib import get_shared_config
import registry_lib
from disconnect_consumer import disconnect_host

SHARED_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = SHARED_ROOT.parent
CONSUMERS_DIR = PROJECT_ROOT / 'consumers'


_COMMIT_RESULT_LABELS = {
    'not-a-repo': "not a git repo",
    'noop': "nothing to commit",
    'committed-pushed': "committed and pushed",
    'committed-no-remote': "committed (no origin remote to push to)",
    'commit-failed': "commit FAILED - see warning above",
    'push-failed': "committed locally, push FAILED - see warning above",
    'reconciled-pushed': "push conflict auto-reconciled, committed and pushed",
}


def _print_consumer_summary(slug, host_result):
    """One consumer's block within the close-out summary (design\\script_action_reporting.md) -
    entirely sourced from disconnect_host()'s/strip_local_references()'s own already-computed
    result dict, nothing re-derived. Keyed by slug rather than host_id (disconnect_consumer.py's
    own _print_host_summary()'s label) since every call in this script's loop shares the same
    host_id (this_host) - what varies here is which consumer, not which host."""
    if not host_result['removed']:
        reason = {
            'no-registry': "no registry entry", 'not-parseable': "registry entry not parseable",
            'not-connected': "already had no hosts.<host> entry",
        }.get(host_result['skip_reason'], host_result['skip_reason'] or "unknown")
        print(f"{slug}: not removed ({reason})")
        return
    hosts_left_note = f", {host_result['hosts_left']} host(s) left in the registry" if host_result['hosts_left'] is not None else ""
    print(f"{slug}: removed from the registry{hosts_left_note}")
    local = host_result['local']
    if local is None:
        return  # do_local_cleanup is always True in this script's call site - defensive only
    if local['target_missing']:
        print(f"  local path no longer exists on disk ({local['target_path']}) - nothing local to clean up")
        return
    prose_labels = {
        'replaced': "CLAUDE.md prose replaced with disconnected-pointer",
        'left-shared': "CLAUDE.md prose left in place (another host still depends on it)",
        'missing': "no CLAUDE.md present to touch",
        'unrecognized': "CLAUDE.md prose NOT replaced - standard heading not found (hand-edited?)",
    }
    parts = [f"{local['n_imports']} @import line(s) removed", prose_labels[local['claude_prose_status']]]
    if local['hub_pointer_removed']:
        parts.append("hub_pointer.md removed")
    if local['removed_hooks'] or local['had_read_rule']:
        detail = []
        if local['removed_hooks']:
            detail.append(f"{local['removed_hooks']} hook entry/entries")
        if local['had_read_rule']:
            detail.append("Read permission rule")
        parts.append(f"{' and '.join(detail)} removed from settings.json")
    if local['dispatch_removed']:
        parts.append("_hub_dispatch.py removed")
    if local['removed_skills']:
        parts.append(f"skills removed: {', '.join(sorted(local['removed_skills']))}")
    print(f"  local cleanup: {'; '.join(parts)}")
    print(f"  notes file: {local['notes_path']}")
    commit_label = _COMMIT_RESULT_LABELS.get(local['commit_result'], local['commit_result'])
    print(f"  committed to this consumer's own repo: {commit_label}")
    if local['left_uncommitted']:
        print(f"  left uncommitted: {', '.join(local['left_uncommitted'])}")


def _repo_status(repo_path):
    """Advisory-only snapshot of a repo's dirty/unpushed state, used to decide whether declaring
    this folder "safe to delete" is honest (design\\hub_uninstall_end_state.md). Never blocks or
    mutates anything by itself - same spirit as update_toolkit.py's cmd_notify(). Fetches origin
    (if present) so the ahead-count is accurate; call this BEFORE _remove_origin() removes it.

    Returns {'is_repo': bool, 'dirty': bool, 'had_origin': bool, 'ahead': str|None} - 'ahead' is a
    digit-string commit count, or None if unknown/unverifiable (no origin, unresolvable branch, or
    the fetch itself failed - e.g. offline). An unknown ahead-count is treated as a blocker by the
    caller, same as a nonzero one - can't claim "safe" without being able to check."""
    repo_path = Path(repo_path)
    result = {'is_repo': False, 'dirty': False, 'had_origin': False, 'ahead': None}
    if not (repo_path / '.git').is_dir():
        return result
    result['is_repo'] = True

    def _git(args):
        return subprocess.run(['git', '-C', str(repo_path)] + args, capture_output=True, text=True)

    result['dirty'] = bool(_git(['status', '--porcelain', '--untracked-files=no']).stdout.strip())
    result['had_origin'] = 'origin' in _git(['remote']).stdout.split()
    if not result['had_origin']:
        return result

    branch = _git(['rev-parse', '--abbrev-ref', 'HEAD']).stdout.strip()
    if not branch or branch == 'HEAD':
        return result
    if _git(['fetch', 'origin']).returncode != 0:
        return result  # offline/unreachable - ahead stays None (unverifiable)
    counts = _git(['rev-list', f'origin/{branch}..HEAD', '--count']).stdout.strip()
    result['ahead'] = counts if counts.isdigit() else None
    return result


def _remove_origin(repo_path):
    """Removes the 'origin' remote from repo_path if present - local-only, fully reversible
    (`git remote add origin <url>` reattaches), never touches GitHub or any other clone
    (design\\hub_uninstall_end_state.md). Returns True if a remote was actually removed."""
    repo_path = Path(repo_path)
    if not (repo_path / '.git').is_dir():
        return False
    remotes = subprocess.run(['git', '-C', str(repo_path), 'remote'],
                              capture_output=True, text=True).stdout.split()
    if 'origin' not in remotes:
        return False
    subprocess.run(['git', '-C', str(repo_path), 'remote', 'remove', 'origin'], capture_output=True)
    return True


def print_close_out_summary(this_host, host_results, per_machine_removed):
    """Close-out block, printed once at the very end of the run (design\\
    script_action_reporting.md) - extends the same shape new_consumer.py's/disconnect_consumer.py's
    own close-out summaries use, adapted for remove_hub.py's own structure: one block per consumer
    disconnected on this machine, plus the per-machine state this script alone clears (a second
    concern neither of the other two scripts has)."""
    print()
    print(f"=== remove_hub: this-machine ({this_host}) teardown summary ===")
    if not host_results:
        print("Consumers: none were connected on this machine.")
    else:
        for slug, host_result in host_results:
            _print_consumer_summary(slug, host_result)
    if per_machine_removed:
        print("Per-machine state cleared:")
        for r in per_machine_removed:
            print(f"  removed {r}")
    else:
        print("Per-machine state: none found to clear (already clean).")


def main():
    config = get_shared_config(SHARED_ROOT)
    this_host = config['host_id']

    print(f"Removing Tower Crane from this machine (host_id: {this_host}).")
    print()

    registry_files = sorted(CONSUMERS_DIR.glob('*.md')) if CONSUMERS_DIR.exists() else []
    connected_here = []
    for rp in registry_files:
        consumer = registry_lib.parse_registry(rp)
        if consumer and this_host in consumer['hosts']:
            connected_here.append(rp.stem)

    host_results = []
    if connected_here:
        print(f"Disconnecting {len(connected_here)} consumer(s) connected on this machine: "
              f"{', '.join(connected_here)}")
        for slug in connected_here:
            print(f"- {slug}")
            result = disconnect_host(slug, this_host, config, 'this-only', lambda m: print(f"  {m}"), do_local_cleanup=True)
            host_results.append((slug, result))
    else:
        print("No consumers are connected on this machine.")
    print()

    removed = []
    config_local = SHARED_ROOT / 'config.local.json'
    if config_local.exists():
        config_local.unlink()
        removed.append(str(config_local))

    claude_dir = PROJECT_ROOT / '.claude'
    for name in ('settings.local.json', 'self_hooks_status.md', 'automation_state.json'):
        p = claude_dir / name
        if p.exists():
            p.unlink()
            removed.append(str(p))

    skills_dir = claude_dir / 'skills'
    if skills_dir.exists():
        shutil.rmtree(skills_dir)
        removed.append(str(skills_dir))

    if removed:
        print("Cleared this machine's own per-machine state:")
        for r in removed:
            print(f"  removed {r}")
    else:
        print("No per-machine state found to clear (already clean).")

    # Repo status must be captured BEFORE removing origin, so the ahead-count still has a remote
    # to compare against (design\hub_uninstall_end_state.md).
    outer_status = _repo_status(PROJECT_ROOT)
    toolkit_status = _repo_status(SHARED_ROOT)
    outer_origin_removed = _remove_origin(PROJECT_ROOT)
    toolkit_origin_removed = _remove_origin(SHARED_ROOT)

    print()
    print("Git remotes:")
    for label, status, origin_removed in (
        ("outer hub repo", outer_status, outer_origin_removed),
        ("toolkit\\", toolkit_status, toolkit_origin_removed),
    ):
        if not status['is_repo']:
            print(f"  {label}: not a git repo - nothing to disconnect")
        elif origin_removed:
            print(f"  {label}: 'origin' remote removed (reversible - `git remote add origin "
                  "<url>` reattaches)")
        elif not status['had_origin']:
            print(f"  {label}: already had no 'origin' remote")

    blockers = []
    for label, status in (("outer hub repo", outer_status), ("toolkit\\", toolkit_status)):
        if not status['is_repo']:
            continue
        if status['dirty']:
            blockers.append(f"{label} has uncommitted changes")
        if status['had_origin'] and status['ahead'] not in (None, '0'):
            blockers.append(f"{label} has {status['ahead']} commit(s) that were never pushed")
        elif status['had_origin'] and status['ahead'] is None:
            blockers.append(f"{label}'s unpushed-commit status could not be verified (offline?)")

    print()
    if blockers:
        print("NOT safe to delete this folder yet:")
        for b in blockers:
            print(f"  - {b}")
        print("Run `checkpoint` (which commits and pushes) to clear these, then re-run "
              "\"uninstall\" to confirm, before deleting anything.")
    else:
        print("This machine is now fully disconnected from Tower Crane: no consumers connected "
              "here, no per-machine state left, and both repos' 'origin' remote removed. Nothing "
              "here depends on GitHub or any other machine anymore - these files are safe to "
              "delete whenever you want. That's a manual step you do yourself; this command "
              "never deletes anything on its own. (.claude\\hooks\\ - tracked, personal content, "
              "not Tower Crane's to begin with - is included in that, same as everything else "
              "here. Deleting the actual GitHub repos, if you ever want that too, is a separate "
              "decision this command has no part in.)")

    print_close_out_summary(this_host, host_results, removed)


if __name__ == '__main__':
    main()
