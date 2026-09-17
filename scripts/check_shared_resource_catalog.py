#!/usr/bin/env python3
"""
check_shared_resource_catalog.py - internal-consistency checks for shared_resources\\CATALOG.md
and shared_resources\\resource_relationships.yaml.

Four checks, all notify-only:

1. File column - every CATALOG.md row's `File` cell must resolve to a real file in
   shared_resources\\, active or archived.
2. Tier-name consistency - a row's `Tier` cell (when set and not `Primary`) must match a tier
   `name:` defined under its `Category` in resource_relationships.yaml's `tiers:` block.
3. identity_eligible declared - every (non-archived) Category on any CATALOG.md row must have a
   corresponding entry in resource_relationships.yaml's `identity_eligible:` block.
4. Edge validity - every edge's `from`/`to` or `a`/`b` in resource_relationships.yaml must resolve
   to some CATALOG.md row, by filename stem. An edge to an archived entry PASSes; only a stem
   matching no row at all is a failure.

Message format leads with the practical effect on what Claude will or won't do; the technical
cause is included secondarily.

resource_relationships.yaml is hand-parsed (regex/line-based), not via a `yaml` import.

Wired into `resume` (not `quick resume`) via resume_check.py.

Usage: python scripts\\check_shared_resource_catalog.py (run from inside toolkit\\, or anywhere).
Quiet when clean - prints one `[!] <message>` line per problem found, then a one-line summary.
Always exits 0.
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
IDENTITY_ELIGIBLE_ITEM_RE = re.compile(r'^  (\S+):\s*(true|false)\s*$')
EDGE_START_RE = re.compile(r'^  - type:\s*(\S+)\s*$')
EDGE_FIELD_RE = re.compile(r'^    (from|to|a|b):\s*(\S+)\s*$')


def parse_relationships(text):
    """Hand-rolled parser for resource_relationships.yaml's three top-level keys. Returns
    (tiers_by_category: dict[str, list[str]], identity_eligible: dict[str, bool], edges:
    list[dict]). Relies on the file's always-consistent indentation (2-space top-level
    keys/list items, 4-space nested fields)."""
    lines = text.splitlines()
    tiers_idx = next((i for i, l in enumerate(lines) if l.strip() == 'tiers:'), None)
    identity_idx = next((i for i, l in enumerate(lines) if l.strip() == 'identity_eligible:'), None)
    edges_idx = next((i for i, l in enumerate(lines) if l.strip() == 'edges:'), None)

    # Each section's own end is whichever of the other two top-level keys comes next in the file
    # (identity_eligible/edges can appear in either order relative to each other, tiers is always
    # first) - never assume a fixed key order beyond "tiers: first, edges: last" (true today).
    def section_end(start_idx, *other_idxs):
        later = [i for i in other_idxs if i is not None and i > start_idx]
        return min(later) if later else len(lines)

    tiers_by_category = {}
    if tiers_idx is not None:
        end = section_end(tiers_idx, identity_idx, edges_idx)
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

    identity_eligible = {}
    if identity_idx is not None:
        end = section_end(identity_idx, tiers_idx, edges_idx)
        for line in lines[identity_idx + 1:end]:
            item_m = IDENTITY_ELIGIBLE_ITEM_RE.match(line)
            if item_m:
                identity_eligible[item_m.group(1)] = item_m.group(2) == 'true'

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

    return tiers_by_category, identity_eligible, edges


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


def check_identity_eligible_declared(rows, identity_eligible):
    """Every Category that appears on any active CATALOG.md row must have a corresponding
    identity_eligible: entry in resource_relationships.yaml. Archived rows are excluded."""
    results = []
    seen = set()
    for row in rows:
        category = row['category']
        if not category or row['status'].lower().startswith('archived') or category in seen:
            continue
        seen.add(category)
        if category in identity_eligible:
            results.append(('OK', category, f"Category '{category}' has a declared identity_eligible value."))
        else:
            results.append(('UNDECLARED', category,
                f'Claude has no answer for whether "{category}" can ever define a project\'s '
                f'identity (the "Adopted Shared Resources" tiered directive can\'t apply Tier 1 to '
                f'it either way until this is set). Fix: add "{category}" to '
                'resource_relationships.yaml\'s identity_eligible: block (true or false).'))
    return results


def check_edges(edges, rows):
    """Every edge's from/to (directional) or a/b (undirected) resolves to some CATALOG.md row by
    filename stem - active or archived both count; only a name matching no row at all is a
    failure."""
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
    tiers_by_category, identity_eligible, edges = ({}, {}, [])
    if RELATIONSHIPS_PATH.exists():
        tiers_by_category, identity_eligible, edges = parse_relationships(
            RELATIONSHIPS_PATH.read_text(encoding='utf-8'))

    file_fails = [r for r in check_file_column(rows) if r[0] == 'FAIL']
    tier_mismatches = [r for r in check_tier_consistency(rows, tiers_by_category) if r[0] == 'MISMATCH']
    undeclared_identity = [r for r in check_identity_eligible_declared(rows, identity_eligible)
                            if r[0] == 'UNDECLARED']
    edge_fails = check_edges(edges, rows)  # already FAIL-only, see its own docstring/return shape

    for _, _, message in file_fails + tier_mismatches + undeclared_identity + edge_fails:
        print(f"[!] {message}")

    total = len(file_fails) + len(tier_mismatches) + len(undeclared_identity) + len(edge_fails)
    print()
    if total:
        print(f"=== {total} issue(s) found across {len(rows)} catalog row(s)/{len(edges)} edge(s): "
              f"{len(file_fails)} broken file reference(s), {len(tier_mismatches)} tier "
              f"mismatch(es), {len(undeclared_identity)} undeclared identity_eligible categor"
              f"y(ies), {len(edge_fails)} broken edge(s) (notify only, not a failure) ===")
    else:
        print(f"=== no catalog/graph inconsistencies found across {len(rows)} catalog row(s)/"
              f"{len(edges)} edge(s) ===")
    sys.exit(0)


if __name__ == '__main__':
    main()
