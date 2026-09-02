#!/usr/bin/env python3
"""
check_shared_resource_hosts.py - Part 1 of design\\shared_resources_bulk_host_registration.md: a
hub-session, catalog-wide scan of every shared_resources\\ entry's per-host registration status for
THIS machine - the proactive counterpart to check_shared_resource_refs.py's existing [HOST-GAP]
check, which only fires per already-adopted entry in an already-connected consumer project (so a
freshly connected machine, or an entry no currently-connected project has adopted yet, gets zero
visibility from that check alone).

Reuses check_shared_resource_refs.py's parse_hosts_block()/read_this_host_id() helpers unmodified -
a hub-session caller already knows its own hub_root without needing that script's
resolve_hub_root() upward-walk from a resolved consumer-side path.

Walks shared_resources\\CATALOG.md, skipping `Status: Archived` rows and `Kind: insight` rows
(insights never carry Hosts: blocks by construction - "Insights are different",
templates\\shared_resources.md). Buckets every remaining reference/tool row:
  [OK]              - Hosts: block exists, this host is a key. Nothing to do.
  [UNREGISTERED]     - Hosts: block exists, this host is not a key. Candidate for registration.
  [NO-HOSTS-BLOCK]   - no Hosts: block at all. Ambiguous by construction - could be a genuinely
                        self-contained entry, or an unmigrated pointer entry that needs migrating
                        to Hosts: block form before it can be registered. Human/model judgment call.

Notify-only, same shape as check_multi_machine.py/check_stale_paths.py - never mutates, exit code
always 0. The write/negotiate half (Part 2) is the "register host" procedure in
agents_continuity.md, not this script.

Usage: python scripts\\check_shared_resource_hosts.py (run from inside toolkit\\, or anywhere - the
hub root is computed from this file's own location, not the current working directory).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_shared_resource_refs import parse_hosts_block, read_this_host_id

SHARED_ROOT = Path(__file__).resolve().parent.parent
# shared_resources\ is private hub state, not shipped toolkit content - it lives at the outer
# root (design\local_first_reframe.md's outer/inner split), one level above SHARED_ROOT (toolkit\).
PROJECT_ROOT = SHARED_ROOT.parent
CATALOG_PATH = PROJECT_ROOT / 'shared_resources' / 'CATALOG.md'


def parse_catalog(catalog_text):
    """Parse shared_resources\\CATALOG.md's table (Name | Kind | File | Category | Tier |
    Description | Added | Status - design\\shared_resources_relationship_graph.md's Category/Tier
    columns, inserted after File). Returns a list of dicts; skips the header and separator rows.
    Malformed rows (fewer than 8 cells) are silently skipped - out of scope for this scan, not a
    failure.

    Column-index fix (2026-09-02): this used to unpack `cells[:6]` assuming the pre-Category/Tier
    six-column shape (Name/Kind/File/Description/Added/Status), which silently mis-assigned every
    cell from Category onward once those two columns were inserted - `status` ended up holding the
    Description text instead of the real Status column, so the archived-row filter below
    (`row['status'].lower().startswith('archived')`) stopped matching real 'Archived ...' values
    and started including archived rows (the three retired seo_*_index.md rows) as if active.
    Caught by hand-tracing this exact bug live, not by a test."""
    rows = []
    lines = [l for l in catalog_text.splitlines() if l.strip().startswith('|')]
    for line in lines[2:]:  # [0] header, [1] '---' separator
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells) < 8:
            continue
        name, kind, file_cell, category, tier, _description, _added, status = cells[:8]
        rows.append({'name': name, 'kind': kind, 'file': file_cell.strip('`'),
                     'category': category, 'tier': tier, 'status': status})
    return rows


def main():
    print("=== check_shared_resource_hosts.py ===")

    if not CATALOG_PATH.exists():
        print("[N/A] no shared_resources\\CATALOG.md found - nothing to scan.")
        sys.exit(0)

    this_host = read_this_host_id(PROJECT_ROOT)
    if this_host is None:
        print("[N/A] couldn't determine this host's own host_id (toolkit\\config.local.json not "
              "reachable or host_id not filled in) - skipping the per-host scan.")
        sys.exit(0)

    rows = parse_catalog(CATALOG_PATH.read_text(encoding='utf-8'))
    ok = unregistered = no_hosts_block = 0
    for row in rows:
        if row['kind'] == 'insight':
            continue
        if row['status'].lower().startswith('archived'):
            continue

        entry_path = CATALOG_PATH.parent / row['file']
        if not entry_path.exists():
            print(f"[N/A] '{row['name']}' ({row['file']}) - catalog row doesn't resolve to a "
                  "real file. Unrelated catalog drift, not this scan's concern.")
            continue

        hosts = parse_hosts_block(entry_path.read_text(encoding='utf-8'))
        if not hosts:
            no_hosts_block += 1
            print(f"[NO-HOSTS-BLOCK] '{row['name']}' ({row['file']}) - no Hosts: block at all. "
                  "Ambiguous: genuinely self-contained (nothing to ever register), or an "
                  "unmigrated pointer entry that needs migrating to Hosts: block form first. See "
                  "templates\\shared_resources.md's \"Per-host availability for pointer entries.\"")
        elif this_host in hosts:
            ok += 1
            print(f"[OK] '{row['name']}' ({row['file']}) - registered for this host "
                  f"('{this_host}').")
        else:
            unregistered += 1
            known = ', '.join(sorted(hosts)) or '(none)'
            print(f"[UNREGISTERED] '{row['name']}' ({row['file']}) - this host ('{this_host}') "
                  f"not in its Hosts: block. Currently registered on: {known}.")

    print()
    print(f"=== {ok} OK, {unregistered} unregistered, {no_hosts_block} no-hosts-block "
          "(notify only, not a failure) ===")
    sys.exit(0)


if __name__ == '__main__':
    main()
