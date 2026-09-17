#!/usr/bin/env python3
"""
check_shared_resource_hosts.py - hub-session, catalog-wide scan of every shared_resources\\
entry's per-host registration status for THIS machine.

Reuses check_shared_resource_refs.py's parse_hosts_block()/read_this_host_id() helpers.

Walks shared_resources\\CATALOG.md, skipping `Status: Archived` rows and `Kind: insight` rows.
Buckets every remaining reference/tool row:
  [OK]              - Hosts: block exists, this host is a key.
  [UNREGISTERED]     - Hosts: block exists, this host is not a key.
  [NO-HOSTS-BLOCK]   - no Hosts: block at all.

Notify-only - never mutates, exit code always 0. The write/negotiate half is the "register host"
procedure in agents_continuity.md, not this script.

Usage: python scripts\\check_shared_resource_hosts.py (run from inside toolkit\\, or anywhere - the
hub root is computed from this file's own location, not the current working directory).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_shared_resource_refs import parse_hosts_block, read_this_host_id

SHARED_ROOT = Path(__file__).resolve().parent.parent
# shared_resources\ lives one level above SHARED_ROOT, at the outer repo root.
PROJECT_ROOT = SHARED_ROOT.parent
CATALOG_PATH = PROJECT_ROOT / 'shared_resources' / 'CATALOG.md'


def parse_catalog(catalog_text):
    """Parse shared_resources\\CATALOG.md's table (Name | Kind | File | Category | Tier |
    Description | Added | Status). Returns a list of dicts; skips the header and separator rows.
    Malformed rows (fewer than 8 cells) are silently skipped."""
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
