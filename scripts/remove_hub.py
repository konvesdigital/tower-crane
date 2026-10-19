#!/usr/bin/env python3
"""
remove_hub.py - reverses setup_machine.md for this machine. Disconnects every consumer connected
on this machine (this-only mode; any other machine's connection to the same consumer is left
alone), clears this machine's own gitignored per-machine hub state, and removes the 'origin' remote
from both the outer hub repo and toolkit\\.

Never touches tracked file content or history in either repo, or .claude\\hooks\\ - apart from
removing this host from each disconnected consumer's registry file (consumers\\<slug>.md), which it
commits and pushes - only the 'origin' remote entry, which is local-only and reversible
(`git remote add origin <url>` reattaches, but the URLs are not recorded anywhere, so a reinstall
needs the user to supply both remotes again). Never touches GitHub or any other machine's own clone. Does not delete the hub folder
tree itself. Never rm -rf's its own running directory.

Ordering: the registry edit(s) disconnect_host() makes are committed and pushed (while 'origin' is
still attached) BEFORE anything irreversible, so the push has the best chance of landing. The script
never inspects either repo for unsaved work and never pauses: the agent running it states, before
launching, that anything not committed and pushed will exist only on this disk, and the user chooses "proceed" or
"checkpoint" first (agents_consumers.md, "Removing this machine"). If the registry push itself fails,
that's the same kind of leftover drift any other gone machine can leave behind - recoverable by hand
later from a surviving hub using registry data already there. TOWER_CRANE_UNINSTALLED.md is written
(local-only, gitignored) recording what was removed.
"""

import datetime
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config_lib import get_shared_config, commit_hub_changes
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


_SKIP_REASON_LABELS = {
    'no-registry': "no registry entry", 'not-parseable': "registry entry not parseable",
    'not-connected': "already had no hosts.<host> entry",
}


def _print_consumer_summary(slug, host_result):
    """Prints one consumer's close-out block, sourced entirely from host_result (disconnect_host()'s
    return dict)."""
    if not host_result['removed']:
        reason = _SKIP_REASON_LABELS.get(host_result['skip_reason'], host_result['skip_reason'] or "unknown")
        print(f"{slug}: not removed ({reason})")
        return
    hosts_left_note = f", {host_result['hosts_left']} host(s) left in the registry" if host_result['hosts_left'] is not None else ""
    print(f"{slug}: removed from the registry{hosts_left_note}")
    local = host_result['local']
    if local is None:
        return  # local is only None when do_local_cleanup=False, never the case here
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


def _remove_origin(repo_path):
    """Removes the 'origin' remote from repo_path if present - local-only, fully reversible
    (`git remote add origin <url>` reattaches), never touches GitHub or any other clone.
    Returns True if a remote was actually removed."""
    repo_path = Path(repo_path)
    if not (repo_path / '.git').is_dir():
        return False
    remotes = subprocess.run(['git', '-C', str(repo_path), 'remote'],
                              capture_output=True, text=True).stdout.split()
    if 'origin' not in remotes:
        return False
    subprocess.run(['git', '-C', str(repo_path), 'remote', 'remove', 'origin'], capture_output=True)
    return True


def _build_uninstall_note(this_host, host_results, per_machine_removed, outer_origin_removed,
                           toolkit_origin_removed):
    """Builds TOWER_CRANE_UNINSTALLED.md's content from the same facts already computed for the
    console output above, reformatted for a file meant to be read later. Gitignored (see
    .gitignore)."""
    lines = [
        f"# Tower Crane — uninstalled from this machine ({this_host})",
        "",
        f"Generated by \"remove\"/\"uninstall\" on {datetime.date.today().isoformat()}. Describes "
        "only this one machine's own clone — has no bearing on any other machine, which is "
        "unaffected regardless of what this file says. "
        "Gitignored, never pushed anywhere.",
        "",
        "## A. What was removed",
        "",
        "### Consumers disconnected here",
    ]
    if not host_results:
        lines.append("None were connected on this machine.")
    else:
        for slug, host_result in host_results:
            if host_result['removed']:
                hosts_left = host_result['hosts_left']
                note = f", {hosts_left} host(s) left in the registry" if hosts_left is not None else ""
                lines.append(f"- {slug}: removed from the registry{note}")
            else:
                reason = _SKIP_REASON_LABELS.get(host_result['skip_reason'], host_result['skip_reason'] or "unknown")
                lines.append(f"- {slug}: not removed ({reason})")

    lines += ["", "### Per-machine state cleared"]
    if per_machine_removed:
        lines += [f"- {r}" for r in per_machine_removed]
    else:
        lines.append("None found (already clean).")

    lines += ["", "### Git remotes"]
    for label, origin_removed in (("outer hub repo", outer_origin_removed),
                                   ("toolkit\\", toolkit_origin_removed)):
        if origin_removed:
            lines.append(f"- {label}: 'origin' remote removed (the URL is not recorded here - "
                          "reinstalling means supplying it again)")
        else:
            lines.append(f"- {label}: had no 'origin' remote to remove")

    lines += ["", "## B. What's left", ""]
    lines.append(
        "This machine is disconnected from Tower Crane and the remote: no consumers connected "
        "here, no per-machine state left, both repos' 'origin' remote removed. Nothing of yours "
        "was deleted. Anything that wasn't committed and pushed beforehand exists only on this "
        "disk. When you're ready, delete the hub's folders (the outer hub and toolkit\\) "
        "yourself; any connected consumer projects are separate folders and stay where they are. "
        "Reinstalling later means running setup_machine.md again and supplying both remote URLs "
        "again. (Deleting the actual GitHub repos, if you ever want that too, is a separate "
        "decision - not something \"uninstall\" touches.)"
    )

    lines += ["", "---", "This file is local-only — delete it along with everything else whenever "
              "you're done reading it. A later `setup_machine.md` run also deletes it automatically "
              "once this machine is reconnected (`--clear-uninstall-note`)."]
    return "\n".join(lines) + "\n"


def print_close_out_summary(this_host, host_results, per_machine_removed):
    """Prints the close-out block at the end of the run: one section per consumer disconnected on
    this machine, plus the per-machine state cleared."""
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

    # Mirrors disconnect_consumer.py's own main(): disconnect_host() only edits consumers/<slug>.md
    # in memory/on disk - committing (and pushing, while 'origin' is still attached) that edit into
    # the outer repo is this call's job. Runs before any irreversible step past this point so the
    # push has the best chance of succeeding; if it fails anyway the commit-result label printed
    # below says so - same recoverable-by-hand pattern as any other leftover drift from a gone
    # machine.
    removed_slugs = [slug for slug, r in host_results if r['removed']]
    if removed_slugs:
        registry_commit_msg = (
            f"Registry: uninstall this machine ({this_host}) - disconnect {', '.join(removed_slugs)}")
        registry_commit_result = commit_hub_changes(
            PROJECT_ROOT, [f"consumers/{slug}.md" for slug in removed_slugs], registry_commit_msg,
            log=print)
        label = _COMMIT_RESULT_LABELS.get(registry_commit_result, registry_commit_result)
        print(f"  [git] registry change(s): {label}")

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

    print()
    if removed:
        print("Cleared this machine's own per-machine state:")
        for r in removed:
            print(f"  removed {r}")
    else:
        print("No per-machine state found to clear (already clean).")

    outer_origin_removed = _remove_origin(PROJECT_ROOT)
    toolkit_origin_removed = _remove_origin(SHARED_ROOT)

    print()
    print("Git remotes:")
    for label, origin_removed in (("outer hub repo", outer_origin_removed),
                                   ("toolkit\\", toolkit_origin_removed)):
        if origin_removed:
            print(f"  {label}: 'origin' remote removed (the URL is not recorded - reinstalling "
                  "means supplying it again)")
        else:
            print(f"  {label}: had no 'origin' remote to remove")

    print()
    print("This machine is disconnected from Tower Crane and the remote: no consumers connected "
          "here, no per-machine state left, and both repos' 'origin' remote removed. Nothing of "
          "yours was deleted. Anything that wasn't committed and pushed beforehand exists only on "
          "this disk. When you're ready, delete the hub's folders (the outer hub and toolkit\\) "
          "yourself - this command never deletes them. Connected consumer projects are separate "
          "folders and stay where they are. (.claude\\hooks\\ - tracked, personal content, not "
          "Tower Crane's to begin with - is included in that, same as everything else here. "
          "Reinstalling later means running setup_machine.md again and supplying both remote URLs "
          "again. Deleting the actual GitHub repos, if you ever want that too, is a separate "
          "decision this command has no part in.)")

    note_text = _build_uninstall_note(this_host, host_results, removed, outer_origin_removed,
                                       toolkit_origin_removed)
    note_path = PROJECT_ROOT / 'TOWER_CRANE_UNINSTALLED.md'
    note_path.write_text(note_text, encoding='utf-8', newline='\n')
    print()
    print(f"Wrote {note_path} (local-only, gitignored) - the above, saved for later reading.")

    print_close_out_summary(this_host, host_results, removed)


if __name__ == '__main__':
    main()
