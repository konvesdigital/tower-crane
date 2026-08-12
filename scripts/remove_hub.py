#!/usr/bin/env python3
"""
remove_hub.py - reverses setup_machine.md for THIS machine (design\\disconnect.md). Disconnects
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

    if connected_here:
        print(f"Disconnecting {len(connected_here)} consumer(s) connected on this machine: "
              f"{', '.join(connected_here)}")
        for slug in connected_here:
            print(f"- {slug}")
            disconnect_host(slug, this_host, config, lambda m: print(f"  {m}"), do_local_cleanup=True)
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


if __name__ == '__main__':
    main()
