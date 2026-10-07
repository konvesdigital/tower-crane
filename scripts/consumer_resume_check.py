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
  4. ticket_scan.py --project <name> <slug>  (open hub tickets mentioning this project; name and
                                               slug come from the registry - skipped if unregistered)
  5. shared_resource_resume_check.py --project-root <root>
                                             (adopted shared-resource references: broken/drifted)
  6. resume_digest.py --project-root <root>  (project_progress.md's live-state sections, capped,
                                               absent sections stated, plus the NEXT: line)

Starts with a Host line (host_id from this hub's config.local.json), prints each step's output
verbatim under a numbered header, and ends with a RESUME SUMMARY block: one line per area, each
either "clean" or what needs the operator, naming the section number to read for detail. The
summary also reports whether COMPLIANCE_GUIDANCE.md exists in the project - checked here, after
step 2 may have just written it.

All are guaranteed side-effect-free from this project's own perspective (none pulls/merges/
pushes toolkit\\ - that's the gated `update` action, run only in a session opened directly in the
hub) and always exit 0. Run this AFTER `git pull`, as its own call: step 2 audits project files and
step 6 reads project_progress.md, both of which a pull can change.

Usage: python consumer_resume_check.py [--project-root <path>]   (defaults to the current directory)
Run from anywhere; resolves the hub's toolkit\\ folder relative to this script's own location, not
the caller's cwd.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config_lib import get_shared_config
from readiness import registry_slug_for, registry_entry_for

SHARED_ROOT = Path(__file__).resolve().parent.parent  # toolkit\


def _run(python_launcher, script_name, extra_args=None):
    script = SHARED_ROOT / 'scripts' / script_name
    proc = subprocess.run(
        [python_launcher, str(script)] + (extra_args or []),
        capture_output=True, text=True,
    )
    output = (proc.stdout + proc.stderr).strip()
    return output if output else '(nothing to report)'


def _host_id():
    try:
        cfg = json.loads((SHARED_ROOT / 'config.local.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    return cfg.get('host_id')


def _summary_lines(outputs, project_root, slug):
    """One line per area from the numbered step outputs (list of str, steps 1-6, '' if skipped)."""
    out = []
    upd, comp, ready, tick, shared = outputs[0], outputs[1], outputs[2], outputs[3], outputs[4]

    out.append("hub toolkit: " + ("current (nothing to review)" if 'up to date' in upd
                                  else "NEEDS A LOOK - read section 1"))

    m = re.search(r'Summary: (\d+) passed, (\d+) warning\(s\), (\d+) failure\(s\)', comp)
    if not slug:
        out.append("compliance: SKIPPED (project unregistered on this host)")
    elif m:
        passed, warn, fail = (int(x) for x in m.groups())
        out.append("compliance: " + ("clean" if not (warn or fail) else
                                     f"{fail} failure(s), {warn} warning(s) - read section 2"))
    else:
        out.append("compliance: NO VERDICT - read section 2")
    guidance = Path(project_root) / 'COMPLIANCE_GUIDANCE.md'
    out.append("compliance guidance file: " + (f"PRESENT at {guidance} - read it per the compliance "
                                              "protocol" if guidance.exists() else "absent"))

    flags = [l for l in ready.splitlines() if l.startswith(('[TODO]', '[UNKNOWN]', '[HUB-MISMATCH]'))]
    out.append("readiness: " + ("clean" if not flags else f"{len(flags)} line(s) need the operator - read section 3"))

    m = re.search(r"needs this project's attention \((\d+)\)", tick)
    if m is None:
        out.append("tickets: " + ("SKIPPED (project unregistered on this host)" if not slug
                                  else "NO VERDICT - read section 4"))
    else:
        hits = re.findall(r'^\s+\[(awaiting_consumer|unknown_state|verify_request)\] .*\n.*\n'
                          r'\s+names this project: (yes|NO)', tick, re.MULTILINE)
        mine = [label for label, names in hits if names == 'yes']
        out.append(f"tickets: {len(mine)} awaiting this project"
                   + (f" ({', '.join(mine)}) - detail in section 4" if mine else "")
                   + (f"; {len(hits) - len(mine)} other flagged ticket(s) do not name it" if len(hits) > len(mine) else ""))

    sflags = [l for l in shared.splitlines() if l.startswith(('[FAIL]', '[HOST-GAP]', '[DRIFT]'))]
    out.append("shared resources: " + ("clean" if not sflags else f"{len(sflags)} flagged line(s) - read section 5"))
    return out


def main():
    parser = argparse.ArgumentParser(description="Consumer-side resume checks, chained.")
    parser.add_argument('--project-root', default=str(Path.cwd()),
                         help="This project's root. Defaults to the current directory.")
    args = parser.parse_args()
    # Resolve once, before any use or forwarding to sub-scripts: a relative value ("." / "..\Foo")
    # would otherwise read as "unregistered" instead of resolving.
    args.project_root = str(Path(args.project_root).expanduser().resolve())

    cfg = get_shared_config(SHARED_ROOT)
    launcher = cfg['python_launcher']
    slug = registry_slug_for(args.project_root)
    entry = registry_entry_for(args.project_root)
    # Both forms a ticket's text uses (display name + slug), taken from the registry - never guessed.
    ticket_args = ['--project', entry['name'], slug] if entry and entry.get('name') else None

    checks = [
        ('update_toolkit.py --notify --consumer', 'update_toolkit.py', ['--notify', '--consumer']),
        (f'check_tower_crane.py --write-guidance --consumer {slug or "(unregistered)"}',
         'check_tower_crane.py',
         ['--write-guidance', '--consumer', slug] if slug else None),
        ('readiness.py', 'readiness.py', ['--project-root', args.project_root]),
        (f'ticket_scan.py --project {slug or "(unregistered)"}', 'ticket_scan.py', ticket_args),
        ('shared_resource_resume_check.py', 'shared_resource_resume_check.py',
         ['--project-root', args.project_root]),
        ('resume_digest.py', 'resume_digest.py', ['--project-root', args.project_root]),
    ]

    print("=== consumer_resume_check.py - consolidated consumer resume checks ===")
    print(f"Host: {_host_id() or '(unknown - toolkit/config.local.json missing or has no host_id)'}")
    if not slug:
        print(f"[UNREGISTERED] no consumers\\ entry lists this host at {args.project_root} - "
              "steps that need the registry are skipped (check the path, or run `connect project`).")
    outputs = []
    for i, (label, script_name, extra_args) in enumerate(checks, 1):
        print(f"\n--- {i}/{len(checks)}: {label} ---")
        if extra_args is None:
            print("(skipped - this project isn't registered on this host; see readiness below)")
            outputs.append('')
            continue
        text = _run(launcher, script_name, extra_args)
        outputs.append(text)
        print(text)
    print("\n=== RESUME SUMMARY ===")
    for line in _summary_lines(outputs, args.project_root, slug):
        print(line)
    print("\n=== end resume checks ===")


if __name__ == '__main__':
    main()
