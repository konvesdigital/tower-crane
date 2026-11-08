#!/usr/bin/env python3
"""
check_shared_resource_catalog.py - internal-consistency checks for shared_resources\\CATALOG.md
and shared_resources\\resource_relationships.yaml.

Six checks, all notify-only:

1. File column - every CATALOG.md row's `File` cell must resolve to a real file in
   shared_resources\\, active or archived.
2. Tier-name consistency - a row's `Tier` cell (when set and not `Primary`) must match a tier
   `name:` defined under its `Category` in resource_relationships.yaml's `tiers:` block.
3. identity_eligible declared - every (non-archived) Category on any CATALOG.md row must have a
   corresponding entry in resource_relationships.yaml's `identity_eligible:` block.
4. Edge validity - every edge's `from`/`to` or `a`/`b` in resource_relationships.yaml must resolve
   to some CATALOG.md row, by filename stem. An edge to an archived entry PASSes; only a stem
   matching no row at all is a failure.

5. No absolute paths in an entry - no shared_resources\\ entry file may contain an absolute path
   anywhere except inside its own `**Hosts:**` block (the one place a machine-local path
   belongs). An absolute path pointing back into the hub is a mis-recorded hub reference (breaks
   on any machine whose hub lives elsewhere); one pointing outside the hub is a machine-local
   resource that belongs in the Hosts block. There is no exemption or escape marker: a URL
   (scheme://, other than file://) is not a path and is skipped; everything else is flagged.

6. Host tag - an active reference/tool row whose entry has a `Hosts:` block must start its
   Description with the matching tag (`[<host_a> only]`, or `[<host_a>, <host_b>]` for several hosts), and a
   row whose entry has none (hub-resident `any`, insight) must carry no leading `[..]` tag. The SEO
   stubs read CATALOG.md directly, so the tag is how they learn which machines have an entry.

Message format leads with the practical effect on what Claude will or won't do; the technical
cause is included secondarily.

resource_relationships.yaml is hand-parsed (regex/line-based), not via a `yaml` import.

Wired into `resume` (not `quick resume`) via resume_check.py.

Usage: python scripts\\check_shared_resource_catalog.py (run from inside toolkit\\, or anywhere).
Quiet when clean - prints one `[!] <message>` line per problem found, then a one-line summary.
Always exits 0.

Single-file mode, used by `save` before it propagates a write:
  python scripts\\check_shared_resource_catalog.py --entry <file> [<file> ...]
Runs only check 5 on the named file(s); prints one `[!]` line per absolute path found and exits 1
if any were found (0 if clean), so `save` can require a clean result before committing.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_shared_resource_hosts import parse_catalog
from check_shared_resource_refs import parse_hosts_block

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


# --- Check 5: no absolute paths outside an entry's own Hosts: block -----------------------------

# A URL (scheme://...) is not a filesystem path - except file://, which IS one and must be scanned.
URL_RE = re.compile(r'\b(?!file:)[A-Za-z][A-Za-z0-9+.\-]*://\S*')
_BOUNDARY = r'(?:^|[\s`"\'(\[=])'
ABS_PATH_PATTERNS = [
    re.compile(r'(?<![A-Za-z0-9])[A-Za-z]:[\\/]'),                 # C:\ or C:/
    re.compile(_BOUNDARY + r'~[\\/]'),                              # ~/ or ~\
    re.compile(_BOUNDARY + r'\\\\[A-Za-z0-9_.$-]+\\'),              # \\server\share
    re.compile(_BOUNDARY + r'/(?:Users|home|mnt|opt|var|etc|usr|tmp|root)/'),  # POSIX roots
    re.compile(r'%[A-Za-z_]+%[\\/]|\$\{?HOME\}?[\\/]'),             # %APPDATA%\ or $HOME/
    re.compile(r'\bfile:/{2,3}'),                                    # file:// URLs
]
PATH_END_RE = re.compile(r'[\s`"\')>\]]')
HUB_SEGMENT_RE = re.compile(r'[\\/]shared_resources(?:[\\/]|$)', re.IGNORECASE)


def _hosts_block_indexes(lines):
    """Line indexes inside the entry's `**Hosts:**` block: the header line plus every following
    blank or indented line (the block ends at the first unindented, non-blank line)."""
    inside = set()
    for i, line in enumerate(lines):
        if line.strip() != '**Hosts:**':
            continue
        inside.add(i)
        j = i + 1
        while j < len(lines) and (not lines[j].strip() or lines[j][0] in ' \t'):
            inside.add(j)
            j += 1
    return inside


def find_absolute_paths(text):
    """Return [(line_number, path_token, points_into_hub)] for every absolute path in `text`
    outside the Hosts: block. No exemptions beyond that block and plain URLs."""
    lines = text.splitlines()
    skip = _hosts_block_indexes(lines)
    found = []
    for idx, line in enumerate(lines):
        if idx in skip:
            continue
        scan = URL_RE.sub(lambda m: ' ' * len(m.group(0)), line)
        starts = set()
        for pattern in ABS_PATH_PATTERNS:
            for m in pattern.finditer(scan):
                start = m.start()
                while start < m.end() and scan[start] in ' \t`"\'([=':
                    start += 1
                starts.add(start)
        covered_to = 0  # a later hit inside an earlier hit's token (file:///C:/...) is the same path
        for start in sorted(starts):
            if start < covered_to:
                continue
            end_m = PATH_END_RE.search(scan, start)
            end = end_m.start() if end_m else len(scan)
            token = scan[start:end].rstrip('.,;:')
            covered_to = end
            found.append((idx + 1, token, bool(HUB_SEGMENT_RE.search(token))))
    return found


def absolute_path_message(name, line_no, token, into_hub):
    if into_hub:
        return (f'"{name}" (line {line_no}) names the hub file "{token}" by absolute path, so the '
                'reference breaks on any machine whose hub lives somewhere else. Fix: replace it '
                'with the shared_resources file name alone.')
    return (f'"{name}" (line {line_no}) writes the absolute path "{token}" in its body, which makes '
            'the resource local to one machine while looking available everywhere. Fix: move the '
            'path into the entry\'s Hosts: block under the machine that has it, and refer to it in '
            'the body by name only.')


def check_absolute_paths(rows):
    """Scan every catalog row's entry file (active or archived) for absolute paths outside its
    Hosts: block. A missing file is check 1's finding, not this one's."""
    results = []
    for row in rows:
        entry_path = CATALOG_PATH.parent / row['file']
        if not entry_path.exists():
            continue
        text = entry_path.read_text(encoding='utf-8')
        for line_no, token, into_hub in find_absolute_paths(text):
            results.append(('ABSOLUTE-PATH', row['name'],
                            absolute_path_message(row['name'], line_no, token, into_hub)))
    return results


# --- Check 6: the catalog row's host tag matches the entry's Hosts: block ------------------------

LEADING_TAG_RE = re.compile(r'^\[[^\]]*\]')


def expected_host_tag(hosts):
    """The tag a catalog row's Description must start with for an entry with this Hosts: block:
    `[<host_a> only]` for one host, `[<host_a>, <host_b>]` (sorted) for several."""
    names = sorted(hosts)
    return f"[{names[0]} only]" if len(names) == 1 else "[" + ", ".join(names) + "]"


def check_host_tags(rows):
    """Every active reference/tool row with a Hosts: block starts its Description with the matching
    tag; every other row (hub-resident, `any`, insight) carries no leading [..] tag. The SEO stubs
    read CATALOG.md directly, so the tag is how they see which machines have an entry."""
    results = []
    for row in rows:
        if row['status'].lower().startswith('archived'):
            continue
        entry_path = CATALOG_PATH.parent / row['file']
        if not entry_path.exists():
            continue
        hosts = parse_hosts_block(entry_path.read_text(encoding='utf-8')) if row['kind'] != 'insight' else {}
        m = LEADING_TAG_RE.match(row['description'])
        have = m.group(0) if m else None
        want = expected_host_tag(hosts) if hosts else None
        if have == want:
            continue
        if want:
            current = f'"{have}"' if have else 'untagged'
            listed = ", ".join(sorted(hosts))
            results.append(('HOST-TAG', row['name'],
                f'Claude reading the catalog will not see which machines have "{row["name"]}". '
                f'Fix: start its Description with "{want} " (its Hosts: block lists '
                f'{listed}); currently {current}.'))
        else:
            results.append(('HOST-TAG', row['name'],
                f'"{row["name"]}" has no Hosts: block but its Description starts with "{have}", '
                'which reads as a machine restriction. Fix: remove the tag, or give the entry a Hosts: block.'))
    return results


def run_entry_mode(file_args):
    """--entry <file>...: check 5 alone on the named file(s). Exit 1 if any path found."""
    total = 0
    for arg in file_args:
        path = Path(arg)
        if not path.exists():
            print(f"[!] {arg} does not exist - nothing to check.")
            total += 1
            continue
        for line_no, token, into_hub in find_absolute_paths(path.read_text(encoding='utf-8')):
            print(f"[!] {absolute_path_message(path.name, line_no, token, into_hub)}")
            total += 1
    print(f"=== {total} absolute-path problem(s) in {len(file_args)} file(s) ===" if total
          else f"=== no absolute paths found in {len(file_args)} file(s) ===")
    sys.exit(1 if total else 0)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--entry':
        if len(sys.argv) < 3:
            print("usage: check_shared_resource_catalog.py --entry <file> [<file> ...]")
            sys.exit(1)
        run_entry_mode(sys.argv[2:])

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
    path_fails = check_absolute_paths(rows)
    tag_fails = check_host_tags(rows)

    for _, _, message in (file_fails + tier_mismatches + undeclared_identity + edge_fails
                          + path_fails + tag_fails):
        print(f"[!] {message}")

    total = (len(file_fails) + len(tier_mismatches) + len(undeclared_identity) + len(edge_fails)
             + len(path_fails) + len(tag_fails))
    print()
    if total:
        print(f"=== {total} issue(s) found across {len(rows)} catalog row(s)/{len(edges)} edge(s): "
              f"{len(file_fails)} broken file reference(s), {len(tier_mismatches)} tier "
              f"mismatch(es), {len(undeclared_identity)} undeclared identity_eligible categor"
              f"y(ies), {len(edge_fails)} broken edge(s), {len(path_fails)} absolute path(s), "
              f"{len(tag_fails)} host tag mismatch(es) (notify only, not a failure) ===")
    else:
        print(f"=== no catalog/graph inconsistencies found across {len(rows)} catalog row(s)/"
              f"{len(edges)} edge(s) ===")
    sys.exit(0)


if __name__ == '__main__':
    main()
