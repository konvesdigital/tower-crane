#!/usr/bin/env python3
"""
consumer_resume_check.py - the consumer-side `resume`'s already-scripted, notify-only checks,
chained into one call: a connected project's own `resume` asks "has the hub toolkit\\ I import
from fallen behind its own upstream" and "is this project ready on this machine," not the hub's own
host-perspective checks (this machine's own hook activation, the consumers\\ registry, other
consumers' stale paths - none of which a consumer session can meaningfully run against another
project's registry entry).

Runs, in order:
  1. update_toolkit.py --notify --consumer   (toolkit\\ dirty / incoming / outgoing state - never
                                               merges; --consumer rephrases every message as
                                               informational-only, since none of --notify's hub-only
                                               fix verbs are reachable from here)
  2. check_tower_crane.py --write-guidance --consumer <slug>
                                             (this project only - its registry slug on this host;
                                               skipped if unregistered, which step 3 reports)
  3. readiness.py --project-root <root>      (what this project still needs on this machine)

All are guaranteed side-effect-free from this project's own perspective (none pulls/merges/
pushes toolkit\\ - that's the gated `update` action, run only in a session opened directly in the
hub) and always exit 0, so this script does no pass/fail interpretation of its own; it just runs
each in turn and prints its output verbatim under a numbered header.

Usage: python consumer_resume_check.py [--project-root <path>]   (defaults to the current directory)
Run from anywhere; resolves the hub's toolkit\\ folder relative to this script's own location, not
the caller's cwd.
"""

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config_lib import get_shared_config
from readiness import registry_slug_for

SHARED_ROOT = Path(__file__).resolve().parent.parent  # toolkit\


def _run(python_launcher, script_name, extra_args=None):
    script = SHARED_ROOT / 'scripts' / script_name
    proc = subprocess.run(
        [python_launcher, str(script)] + (extra_args or []),
        capture_output=True, text=True,
    )
    output = (proc.stdout + proc.stderr).strip()
    return output if output else '(nothing to report)'


def main():
    parser = argparse.ArgumentParser(description="Consumer-side resume checks, chained.")
    parser.add_argument('--project-root', default=str(Path.cwd()),
                         help="This project's root. Defaults to the current directory.")
    args = parser.parse_args()

    cfg = get_shared_config(SHARED_ROOT)
    launcher = cfg['python_launcher']
    slug = registry_slug_for(args.project_root)

    checks = [
        ('update_toolkit.py --notify --consumer', 'update_toolkit.py', ['--notify', '--consumer']),
        (f'check_tower_crane.py --write-guidance --consumer {slug or "(unregistered)"}',
         'check_tower_crane.py',
         ['--write-guidance', '--consumer', slug] if slug else None),
        ('readiness.py', 'readiness.py', ['--project-root', args.project_root]),
    ]

    print("=== consumer_resume_check.py - consolidated consumer resume checks ===")
    for i, (label, script_name, extra_args) in enumerate(checks, 1):
        print(f"\n--- {i}/{len(checks)}: {label} ---")
        if extra_args is None:
            print("(skipped - this project isn't registered on this host; see readiness below)")
            continue
        print(_run(launcher, script_name, extra_args))
    print("\n=== end resume checks ===")


if __name__ == '__main__':
    main()
