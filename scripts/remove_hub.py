#!/usr/bin/env python3
"""
remove_hub.py - reverses setup_machine.md for THIS machine (design\\connect_disconnect.md). Disconnects
every consumer connected on this machine (this-only mode, so any OTHER machine's connection to the
same consumer is left alone), then clears this machine's own gitignored per-machine hub state, so
a later setup_machine.md run here starts genuinely clean - no consumer thinks this machine is
still connected, and nothing here remembers this machine was ever configured.

Deliberately does NOT touch anything git-tracked: the outer/toolkit repos themselves, or
.claude\\hooks\\ (Rung 2's tracked-across-this-operator's-own-machines personal hook content,
design\\resource_sharing_model.md's three-rung ladder - not this hub's to delete). Physically
deleting the hub folder tree afterward, if wanted, is left to the user - this script only clears
state and connections, it never rm -rf's its own running directory.
"""

import shutil
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

    print()
    print("Done. This machine no longer appears connected to any consumer, and has no local "
          "config.local.json / self-use state left. .claude\\hooks\\ (tracked, personal content) "
          "was left alone - it isn't Tower Crane's to delete. If you also want the hub folder "
          "itself gone, delete it now (both outer and toolkit\\ - config.local.json won't come "
          "back on a fresh clone; setup_machine.md will treat this exactly like a new machine).")

    print_close_out_summary(this_host, host_results, removed)


if __name__ == '__main__':
    main()
