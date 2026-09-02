#!/usr/bin/env python3
"""
check_shared_resource_catalog.py - internal-consistency checks for shared_resources\\CATALOG.md
and shared_resources\\resource_relationships.yaml (design\\shared_resources_relationship_graph.md).
These two hand-maintained files only work if they agree with each other; nothing previously
checked that they do. Flagged as a gap in that design doc's "What this doc does not decide" (the
edge-validity check) and found alongside it while scoping this script (the File-column and
Tier-name checks) - all three are the same "hand-edited data trusted without a check" shape as
design\\shared_resources_pipeline_reliability.md's Family B.

Three checks, all notify-only (never blocks anything - nothing currently runs this automatically):

1. File column - every CATALOG.md row's `File` cell must resolve to a real file in
   shared_resources\\, active or archived (an archived entry is still fully readable by design -
   "never deleted", templates\\shared_resources.md - so archived status is not exempted from this
   check, only from the two below where relevant).
2. Tier-name consistency - a row's `Tier` cell (when set and not `Primary`) must match a tier
   `name:` actually defined under its `Category` in resource_relationships.yaml's `tiers:` block.
   Tier names are expected to get renamed/split over time (the design doc: "Tier names/definitions
   stay revisable going forward"), and nothing enforces the two files staying in sync when that
   happens.
3. Edge validity - every edge's `from`/`to` or `a`/`b` in resource_relationships.yaml must resolve
   to some CATALOG.md row, by filename stem (the design doc's node-naming convention). An edge to
   an *archived* entry PASSes deliberately (decided 2026-09-02): the archived file still exists and
   is still fully readable, and the retrieval procedure doesn't filter graph neighbors by Status -
   only a stem matching no row at all (a typo, or a genuine deletion without edge cleanup) is a
   real failure.

Message format (decided 2026-09-02, deliberately different from this script family's usual
technical-first phrasing): lead with the practical effect on what Claude will or won't do,
because a shared_resources\\ entry is saved for a reason and these breakages are exactly what
stops that reason from ever reaching a session - the technical cause is secondary, included only
so it can be fixed.

Reuses check_shared_resource_hosts.py's parse_catalog() (fixed 2026-09-02: it was unpacking
`cells[:6]` against the current 8-column Name/Kind/File/Category/Tier/Description/Added/Status
schema, silently mis-assigning every cell from Category onward and breaking the archived-row
filter downstream - caught live while scoping this script).

resource_relationships.yaml is hand-parsed (regex/line-based, same style as registry_lib.py's own
yaml handling) rather than via a `yaml` import - this hub has no external Python dependency today
(design\\portability.md's multi-machine stance), and the file's shape is simple and always
machine-written by templates\\shared_resources.md's Saving procedure, so a small dedicated parser
is more portable than a new hard dependency for one script.

Wired into `resume` (not `quick resume`) via resume_check.py - decided 2026-09-02.

Usage: python scripts\\check_shared_resource_catalog.py (run from inside toolkit\\, or anywhere -
computed from this file's own location, not the caller's cwd). Quiet when clean (matching
check_multi_machine.py/check_stale_paths.py's "(nothing to report)" convention, not this script
family's usual per-row [OK] line) - prints one `[!] <message>` line per actual problem found, then
a one-line summary either way. Always exits 0 (notify-only - nothing here blocks resume).
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_shared_resource_hosts import parse_catalog

SHARED_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = SHARED_ROOT.parent
CATALOG_PATH = PROJECT_ROOT / 'shared_resources' / 'CATALOG.md'
RELATIONSHIPS_PATH = PROJECT_ROOT / 'shared_resources' / 'resource_relationships.yaml'

CATEGORY_KEY_RE = re.compile(r'^  (\S+):\s*$')
TIER_NAME_RE = re.compile(r'^    - name:\s*(.+?)\s*$')
EDGE_START_RE = re.compile(r'^  - type:\s*(\S+)\s*$')
EDGE_FIELD_RE = re.compile(r'^    (from|to|a|b):\s*(\S+)\s*$')


def parse_relationships(text):
    """Hand-rolled parser for resource_relationships.yaml's two top-level keys. Returns
    (tiers_by_category: dict[str, list[str]], edges: list[dict]). Relies on the file's always-
    consistent machine-written indentation (2-space top-level keys/list items, 4-space nested
    fields) - see module docstring for why this isn't a real yaml parse."""
    lines = text.splitlines()
    tiers_idx = next((i for i, l in enumerate(lines) if l.strip() == 'tiers:'), None)
    edges_idx = next((i for i, l in enumerate(lines) if l.strip() == 'edges:'), None)

    tiers_by_category = {}
    if tiers_idx is not None:
        end = edges_idx if edges_idx is not None else len(lines)
        current_category = None
        for line in lines[tiers_idx + 1:end]:
            cat_m = CATEGORY_KEY_RE.match(line)
            if cat_m:
                current_category = cat_m.group(1)
                tiers_by_category[current_category] = []
                continue
            name_m = TIER_NAME_RE.match(line)
            if name_m and current_category:
                tiers_by_category[current_category].append(name_m.group(1))

    edges = []
    if edges_idx is not None:
        current = None
        for line in lines[edges_idx + 1:]:
            start_m = EDGE_START_RE.match(line)
            if start_m:
                current = {'type': start_m.group(1), 'from': None, 'to': None, 'a': None, 'b': None}
                edges.append(current)
                continue
            field_m = EDGE_FIELD_RE.match(line)
            if field_m and current is not None:
                current[field_m.group(1)] = field_m.group(2)

    return tiers_by_category, edges


def check_file_column(rows):
    """Every row's File cell resolves to a real file - regardless of Kind or Status, since an
    archived entry is still supposed to be fully readable by design."""
    results = []
    for row in rows:
        entry_path = CATALOG_PATH.parent / row['file']
        if entry_path.exists():
            results.append(('OK', row['name'], f"'{row['file']}' resolves."))
        else:
            results.append(('FAIL', row['name'],
                f'Claude will not read "{row["name"]}" in context as a shared resource because '
                'the file has been removed or renamed. Fix: repoint the file cell to a valid '
                'filename, or restore the missing file.'))
    return results


def check_tier_consistency(rows, tiers_by_category):
    """Every row with a non-blank, non-Primary Tier must match a real tier name: defined under
    its own Category in resource_relationships.yaml."""
    results = []
    for row in rows:
        category, tier = row['category'], row['tier']
        if not category or not tier or tier == 'Primary':
            continue
        valid = tiers_by_category.get(category, [])
        if tier in valid:
            results.append(('OK', row['name'], f"tier '{tier}' matches Category '{category}'."))
        else:
            results.append(('MISMATCH', row['name'],
                f'Claude will not reliably surface "{row["name"]}" for "{tier}" because "{tier}" '
                f'has been renamed or removed. Fix: update {row["name"]}\'s tier to match what '
                f'"{tier}" has been renamed to, or add "{tier}" back as a tier.'))
    return results


def check_edges(edges, rows):
    """Every edge's from/to (directional) or a/b (undirected) resolves to some CATALOG.md row by
    filename stem - active or archived both count (archived entries stay fully readable and
    retrieval doesn't filter graph neighbors by Status), only a name matching no row at all is a
    real failure."""
    stem_to_name = {Path(row['file']).stem: row['name'] for row in rows}
    results = []
    for edge in edges:
        if edge['from'] is not None or edge['to'] is not None:
            pairs = [('from', edge['from'], edge['to']), ('to', edge['to'], edge['from'])]
        else:
            pairs = [('a', edge['a'], edge['b']), ('b', edge['b'], edge['a'])]

        for field, stem, other_stem in pairs:
            if stem is None:
                continue
            if stem in stem_to_name:
                continue
            label = stem_to_name.get(other_stem, other_stem)
            broken_label = stem
            if field in ('from', 'to'):
                to_side = stem_to_name.get(edge['to'], edge['to']) if field == 'from' else broken_label
                from_side = broken_label if field == 'from' else stem_to_name.get(edge['from'], edge['from'])
                results.append(('FAIL', f"{edge['from']}->{edge['to']}",
                    f'Claude will not surface "{to_side}" alongside "{from_side}" because '
                    f'"{broken_label}" no longer matches any catalog entry. Fix: correct the '
                    f'edge\'s "{field}" target to a valid entry, or remove the edge if the entry '
                    'is gone.'))
            else:
                results.append(('FAIL', f"{edge['a']}<->{edge['b']}",
                    f'Claude will not surface "{label}" and "{broken_label}" together because '
                    f'"{broken_label}" no longer matches any catalog entry. Fix: correct the '
                    'edge\'s target to a valid entry, or remove the edge if the entry is gone.'))
    return results


def main():
    print("=== check_shared_resource_catalog.py ===")

    if not CATALOG_PATH.exists():
        print("[N/A] no shared_resources\\CATALOG.md found - nothing to check.")
        sys.exit(0)

    rows = parse_catalog(CATALOG_PATH.read_text(encoding='utf-8'))
    tiers_by_category, edges = ({}, [])
    if RELATIONSHIPS_PATH.exists():
        tiers_by_category, edges = parse_relationships(RELATIONSHIPS_PATH.read_text(encoding='utf-8'))

    # Quiet when clean, matching this hub's other resume-time checks (check_multi_machine.py/
    # check_stale_paths.py print "(nothing to report)" rather than one OK line per item) - a
    # CATALOG.md row count that only grows shouldn't mean a resume that only gets noisier.
    file_fails = [r for r in check_file_column(rows) if r[0] == 'FAIL']
    tier_mismatches = [r for r in check_tier_consistency(rows, tiers_by_category) if r[0] == 'MISMATCH']
    edge_fails = check_edges(edges, rows)  # already FAIL-only, see its own docstring/return shape

    for _, _, message in file_fails + tier_mismatches + edge_fails:
        print(f"[!] {message}")

    total = len(file_fails) + len(tier_mismatches) + len(edge_fails)
    print()
    if total:
        print(f"=== {total} issue(s) found across {len(rows)} catalog row(s)/{len(edges)} edge(s): "
              f"{len(file_fails)} broken file reference(s), {len(tier_mismatches)} tier "
              f"mismatch(es), {len(edge_fails)} broken edge(s) (notify only, not a failure) ===")
    else:
        print(f"=== no catalog/graph inconsistencies found across {len(rows)} catalog row(s)/"
              f"{len(edges)} edge(s) ===")
    sys.exit(0)


if __name__ == '__main__':
    main()
