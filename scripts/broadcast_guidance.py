#!/usr/bin/env python3
"""
broadcast_guidance.py - push one hand-authored guidance file to every registered consumer (or a
single one via --consumer), and report delivery status. The reusable maintainer-side primitive
scoped in design\\broadcast_guidance.md (locked 2026-07-23): fills the gap between silent
minor-change propagation (import-by-reference content - no delivery step needed) and Replicate
publish (public downloaders, outside the registry entirely) - content that's deliberately NOT
imported (a one-off directive, a heads-up) but still needs to reach every registered project.

Shares COMPLIANCE_GUIDANCE.md with check_tower_crane.py's checker writer via guidance_lib.py's
namespaced sections ('## Broadcast' here, '## Checker deviations' there) - each writer replaces
only its own section and preserves the other's, so a routine checker run never wipes a pending
broadcast, and a broadcast never wipes pending checker deviations (design\\broadcast_guidance.md,
"Collision fix").

Usage:
  python broadcast_guidance.py --broadcast <file.md> [--consumer <slug>]
  python broadcast_guidance.py --status [--consumer <slug>]

Status model (design\\broadcast_guidance.md, "Status model"): live re-scan, no persisted ack.
--status recomputes from the registry every run - a consumer's '## Broadcast' section still
present means pending/declined; gone means applied (the consumer's own agent resolved it and
removed that section per templates\\compliance.md).

Targeting (design\\broadcast_guidance.md, "Targeting"): whole registry by default, optional
--consumer filter. No owner:/host: subset filtering - not needed at current single-user,
single-machine scale.
"""

import argparse
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config_lib import get_shared_config
from guidance_lib import read_sections, write_section, SECTION_BROADCAST, SECTION_CHECKER

SHARED_ROOT = Path(__file__).resolve().parent.parent
# consumers\ is private hub state, not shipped toolkit content - it lives at the outer root
# (design\local_first_reframe.md's outer/inner split), one level above SHARED_ROOT (toolkit\).
PROJECT_ROOT = SHARED_ROOT.parent
CONSUMERS_DIR = PROJECT_ROOT / 'consumers'


def parse_registry_minimal(path):
    """Minimal registry read - name + hosts: map only, enough to target a broadcast. Deliberately
    duplicated rather than imported from check_tower_crane.py: each maintainer script reads the
    registry independently (same pattern relocate.py/new_consumer.py already use) - only the
    guidance-file section logic is shared, per design\\broadcast_guidance.md's Primitive-shape
    decision. Schema per design\\multi_machine_hub.md (2026-08-10 migration): hosts: is a map of
    host_id -> {path, registered}, replacing the old flat path:/host: pair.
    """
    raw = path.read_text(encoding='utf-8')
    m = re.search(r'```yaml\s*\r?\n(.*?)\r?\n```', raw, re.DOTALL)
    if not m:
        return None
    obj = {'name': None, 'hosts': {}}
    section = None
    current_host = None
    for line in re.split(r'\r?\n', m.group(1)):
        m1 = re.match(r'^name:\s*(.+?)\s*$', line)
        if m1:
            obj['name'] = m1.group(1)
            section = None
            continue
        if re.match(r'^hosts:\s*$', line):
            section = 'hosts'
            current_host = None
            continue
        if re.match(r'^(scope|owner|registered|opted_in|imported|private_opted_in):', line):
            section = None
            continue
        if section == 'hosts':
            m1 = re.match(r'^  (\S+):\s*$', line)
            if m1:
                current_host = m1.group(1)
                obj['hosts'][current_host] = {'path': None}
                continue
            m1 = re.match(r'^    path:\s*(.+?)\s*$', line)
            if m1 and current_host:
                obj['hosts'][current_host]['path'] = m1.group(1)
                continue
    return obj


def load_targets(consumer_filter):
    if not CONSUMERS_DIR.is_dir():
        print("[WARN] No consumers/ folder - nothing to target.")
        return []
    files = sorted(CONSUMERS_DIR.glob('*.md'))
    if consumer_filter:
        files = [f for f in files if f.stem == consumer_filter]
        if not files:
            print(f"[FAIL] No registry entry for consumer '{consumer_filter}' (consumers/{consumer_filter}.md).")
            sys.exit(1)
    targets = []
    for f in files:
        c = parse_registry_minimal(f)
        if c is None or not c['name'] or not c['hosts']:
            print(f"[WARN] {f.name} : no parseable registry block - skipped.")
            continue
        targets.append(c)
    return targets


def get_head_sha():
    try:
        result = subprocess.run(
            ['git', '-C', str(SHARED_ROOT), 'rev-parse', '--short', 'HEAD'],
            capture_output=True, text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except OSError:
        pass
    return 'unknown'


def reachable(c, this_host):
    """Federate (#1) parity with check_tower_crane.py: skip silently when a consumer has no
    hosts.<this_host> entry - its path can't be validated/written from here. Returns this host's
    path on success, None otherwise."""
    this_path = c['hosts'].get(this_host, {}).get('path')
    if not this_path:
        print(f"[skip] {c['name']} : not connected on this machine ('{this_host}').")
        return None
    cpath = Path(this_path)
    if not cpath.exists():
        print(f"[WARN] {c['name']} : path not found on disk ({this_path}) - skipped.")
        return None
    return this_path


def do_broadcast(guidance_file, consumer_filter, this_host):
    src = Path(guidance_file)
    if not src.exists():
        print(f"[FAIL] Guidance file not found: {src}")
        sys.exit(1)
    content = src.read_text(encoding='utf-8').strip('\n')
    today = date.today().isoformat()
    head_sha = get_head_sha()
    body_lines = [
        f"Broadcast by tower_crane `broadcast_guidance.py` on {today} from tower_crane HEAD `{head_sha}`.",
        '',
        content,
    ]

    targets = load_targets(consumer_filter)
    sent, skipped = 0, 0
    for c in targets:
        this_path = reachable(c, this_host)
        if not this_path:
            skipped += 1
            continue
        write_section(this_path, c['name'], SECTION_BROADCAST, body_lines)
        print(f"[sent] {c['name']} : wrote Broadcast section to {Path(this_path) / 'COMPLIANCE_GUIDANCE.md'}")
        sent += 1
    print()
    print(f"=== Broadcast complete: {sent} sent, {skipped} skipped ===")


def do_status(consumer_filter, this_host):
    targets = load_targets(consumer_filter)
    for c in targets:
        this_path = reachable(c, this_host)
        if not this_path:
            continue
        sections = read_sections(this_path)
        if SECTION_BROADCAST in sections:
            note = " (+ checker deviations also pending)" if SECTION_CHECKER in sections else ''
            print(f"[pending] {c['name']}{note}")
        else:
            print(f"[applied/none] {c['name']}")


def main():
    parser = argparse.ArgumentParser(description="Push hand-authored guidance to registered consumers.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--broadcast', metavar='FILE',
                        help="Markdown file whose content is written into each target's Broadcast section.")
    group.add_argument('--status', action='store_true',
                        help="Live re-scan of Broadcast section presence across targets.")
    parser.add_argument('--consumer', default=None,
                         help="Slug of a single consumer to target. Default: all registered consumers.")
    args = parser.parse_args()

    config = get_shared_config(SHARED_ROOT)
    this_host = str(config.get('host_id', ''))

    print("=== broadcast_guidance.py ===")
    if args.consumer:
        print(f"scope: consumer '{args.consumer}'")

    if args.broadcast:
        do_broadcast(args.broadcast, args.consumer, this_host)
    else:
        do_status(args.consumer, this_host)


if __name__ == '__main__':
    main()
