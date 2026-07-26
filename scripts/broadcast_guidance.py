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
    """Minimal registry read - name/path/host only, enough to target a broadcast. Deliberately
    duplicated rather than imported from check_tower_crane.py: each maintainer script reads the
    registry independently (same pattern relocate.py/new_consumer.py already use) - only the
    guidance-file section logic is shared, per design\\broadcast_guidance.md's Primitive-shape
    decision.
    """
    raw = path.read_text(encoding='utf-8')
    m = re.search(r'```yaml\s*\r?\n(.*?)\r?\n```', raw, re.DOTALL)
    if not m:
        return None
    obj = {'name': None, 'path': None, 'host': None}
    for line in re.split(r'\r?\n', m.group(1)):
        m1 = re.match(r'^name:\s*(.+?)\s*$', line)
        if m1:
            obj['name'] = m1.group(1)
            continue
        m1 = re.match(r'^path:\s*(.+?)\s*$', line)
        if m1:
            obj['path'] = m1.group(1)
            continue
        m1 = re.match(r'^host:\s*(.+?)\s*$', line)
        if m1:
            obj['host'] = m1.group(1)
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
        if c is None or not c['name'] or not c['path']:
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
    """Federate (#1) parity with check_tower_crane.py: skip silently when a consumer is
    registered on another machine's clone - its path can't be validated/written from here.
    """
    if c['host'] and this_host and c['host'] != this_host:
        print(f"[skip] {c['name']} : registered on host '{c['host']}', not this machine ('{this_host}').")
        return False
    cpath = Path(c['path'])
    if not cpath.exists():
        print(f"[WARN] {c['name']} : path not found on disk ({c['path']}) - skipped.")
        return False
    return True


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
        if not reachable(c, this_host):
            skipped += 1
            continue
        write_section(c['path'], c['name'], SECTION_BROADCAST, body_lines)
        print(f"[sent] {c['name']} : wrote Broadcast section to {Path(c['path']) / 'COMPLIANCE_GUIDANCE.md'}")
        sent += 1
    print()
    print(f"=== Broadcast complete: {sent} sent, {skipped} skipped ===")


def do_status(consumer_filter, this_host):
    targets = load_targets(consumer_filter)
    for c in targets:
        if c['host'] and this_host and c['host'] != this_host:
            print(f"[skip] {c['name']} : registered on host '{c['host']}', not this machine ('{this_host}').")
            continue
        cpath = Path(c['path'])
        if not cpath.exists():
            print(f"[WARN] {c['name']} : path not found on disk ({c['path']}).")
            continue
        sections = read_sections(cpath)
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
