#!/usr/bin/env python3
"""
resume_digest.py - the deterministic replacement for "read only the live-state sections of
project_progress.md" in a connected project's `resume` / `quick resume`. Prints, in a fixed order
with fixed headers, exactly the pieces the procedure names, states plainly which were absent, and
caps each section so one oversized section can never silently cut off the ones after it.

Output order (always):
  Host line (host_id from this hub's config.local.json)
  Sections found / absent
  Current Status, Current Focus, Next Up, Decisions (every '## Decisions...' heading, in file
  order - covers the single-table form and the Locked/Open split), Phases, and ONLY the newest
  Work Log entry
  STATUS: line - the first list item (or first paragraph) in Current Status, or in Current Focus
  when there is no Current Status (wrapped lines joined; 400 chars max,
  cut at a sentence/word boundary with a `…[truncated, full item at ... line N]` marker)
  NEXT: line - the first unchecked checkbox item in Next Up, else the first list item (same rules)
  NEXT LIST block - only when Next Up has 2+ open top-level items: the open top-level items, tiered
  by Next Up's `### ` sub-headings (up to 5 above the first heading, 3 from the first group, later
  groups as a name and count); a flat list is its first 5 items. Each tier ends `+N more` when cut.

Section boundaries: a section is a '## ' heading whose text starts with the names above
(case-insensitive); it runs to the next '## ' heading or end of file. A Work Log entry starts at a
line beginning '- ', '**YYYY-MM-DD' or '### ' and runs to the next such line.

Size cap: each section prints at most --max-lines lines (default 60) and --max-chars characters
(default 5000), whichever hits first, then `[truncated: N more line(s) omitted from <section> -
Read project_progress.md offset=<A> limit=<B> for the rest]`. Nothing is ever cut without that
marker.

Usage: python resume_digest.py --project-root "<absolute project root>" [--max-lines N] [--max-chars N]
Always exits 0 for a readable project_progress.md (a missing one prints a plain [ABSENT] line).
"""

import argparse
import json
import re
import sys
from pathlib import Path

SHARED_ROOT = Path(__file__).resolve().parent.parent  # toolkit\

HEADING_RE = re.compile(r'^## (.*)$')
ENTRY_START_RE = re.compile(r'^(?:- |\*\*\d{4}-\d{2}-\d{2}\b|### )')
LIST_ITEM_RE = re.compile(r'^\s{0,3}(?:[-*]|\d+[.)])\s+(.*)$')
CHECKBOX_OPEN_RE = re.compile(r'^\[ \]\s*(.*)$')
CHECKBOX_DONE_RE = re.compile(r'^\[[xX]\]')

# NEXT LIST sizes: items listed above Next Up's first `### ` heading (or in a flat list), items
# listed from its first `### ` group, and the per-item character budget.
LISTED_UNGROUPED = 5
LISTED_FIRST_GROUP = 3
ITEM_BUDGET = 110

# (key, display name, heading-prefix or None = the lowercased display name, required-in-every-tier)
SECTIONS = [
    ('status', 'Current Status', 'current status', True),
    ('focus', 'Current Focus', 'current focus', False),
    ('next', 'Next Up', 'next up', True),
    ('decs', 'Decisions', None, True),
    ('phs', 'Phases', 'phase', False),
    ('worklog', 'Work Log', 'work log', True),
]


def host_line():
    cfg = SHARED_ROOT / 'config.local.json'
    try:
        host = json.loads(cfg.read_text(encoding='utf-8')).get('host_id')
    except (OSError, ValueError):
        host = None
    return host or '(unknown - toolkit/config.local.json missing or has no host_id)'


def split_sections(lines):
    """[(heading_text, start_idx, end_idx_exclusive)] for every '## ' heading; body is
    lines[start+1:end]."""
    heads = [(i, m.group(1).strip()) for i, line in enumerate(lines)
             if (m := HEADING_RE.match(line))]
    out = []
    for n, (i, text) in enumerate(heads):
        end = heads[n + 1][0] if n + 1 < len(heads) else len(lines)
        out.append((text, i, end))
    return out


def newest_entry_bounds(body):
    """(start, end) indices within body of the first Work Log entry, or None."""
    start = next((i for i, l in enumerate(body) if ENTRY_START_RE.match(l)), None)
    if start is None:
        return None
    end = next((i for i in range(start + 1, len(body)) if ENTRY_START_RE.match(body[i])), len(body))
    return start, end


def emit_capped(label, body, first_line_no, max_lines, max_chars):
    """Print body (trimmed of blank edges) capped at max_lines with an explicit marker."""
    while body and not body[0].strip():
        body = body[1:]
        first_line_no += 1
    while body and not body[-1].strip():
        body = body[:-1]
    print(f"=== {label} ===")
    if not body:
        print("(empty)")
        print()
        return
    shown, used = 0, 0
    for line in body[:max_lines]:
        if shown and used + len(line) > max_chars:
            break
        print(line)
        shown += 1
        used += len(line) + 1
    omitted = len(body) - shown
    if omitted > 0:
        print(f"[truncated: {omitted} more line(s) omitted from {label} - Read project_progress.md "
              f"offset={first_line_no + shown} limit={omitted} for the rest]")
    print()


def list_items(body):
    """[(text joined with its wrapped continuation lines, index of its first line in body, indent)]"""
    items = []
    for i, line in enumerate(body):
        m = LIST_ITEM_RE.match(line)
        if m:
            parts = [m.group(1).strip()]
            marker_indent = len(line) - len(line.lstrip())
            for nxt in body[i + 1:]:
                if (not nxt.strip() or LIST_ITEM_RE.match(nxt)
                        or len(nxt) - len(nxt.lstrip()) <= marker_indent):
                    break
                parts.append(nxt.strip())
            items.append((' '.join(parts), i, marker_indent))
    return items


def next_item(body):
    """First unchecked-checkbox list item, else first list item that isn't a checked checkbox."""
    items = [(text, i) for text, i, _indent in list_items(body)]
    for text, i in items:
        m = CHECKBOX_OPEN_RE.match(text)
        if m:
            return m.group(1).strip(), i
    for text, i in items:
        if not CHECKBOX_DONE_RE.match(text):
            return text, i
    return None


def trim_item(text, budget, line_no, short=False):
    """Whole text if it fits; else cut at a sentence end (past 40% of budget) or the last word
    boundary within budget, and say where the full item lives (short=True: just `(line N)`)."""
    if len(text) <= budget:
        return text
    head = text[:budget]
    ends = [m.end() for m in re.finditer(r'[.!?](?=\s)', head)]
    if ends and ends[-1] >= budget * 0.4:
        head = head[:ends[-1]]
    else:
        head = head.rsplit(' ', 1)[0] if ' ' in head else head
    if short:
        return f"{head.rstrip()} …(line {line_no})"
    return f"{head.rstrip()} …[truncated, full item at project_progress.md line {line_no}]"


def next_list(body, first_line_no):
    """The NEXT LIST block for `resume`: the open top-level items of Next Up, tiered by its `### `
    sub-headings (items above the first heading, then the first group, then later groups as a count).
    A flat list is just the first LISTED_UNGROUPED items plus a `+N more`. Items are numbered
    continuously; `first_line_no` is the file line number of body[0]."""
    heads = [i for i, l in enumerate(body) if l.startswith('### ')]
    bounds = [(None, 0, heads[0] if heads else len(body))]
    for n, i in enumerate(heads):
        bounds.append((body[i][4:].strip(), i + 1, heads[n + 1] if n + 1 < len(heads) else len(body)))

    tiers = []  # (heading or None, [(text, file line number)])
    for name, start, end in bounds:
        seg = body[start:end]
        open_items = [(CHECKBOX_OPEN_RE.sub(r'\1', t) if CHECKBOX_OPEN_RE.match(t) else t,
                       first_line_no + start + i)
                      for t, i, indent in list_items(seg)
                      if indent == 0 and not CHECKBOX_DONE_RE.match(t)]
        if open_items:
            tiers.append((name, open_items))
    if not tiers:
        return []

    out, n, seen_group = [], 0, False
    for name, items in tiers:
        if name is None:
            cap = LISTED_UNGROUPED
        elif not seen_group:
            cap, seen_group = LISTED_FIRST_GROUP, True
            out.append(f"  {name}, {min(cap, len(items))} of {len(items)}:")
        else:
            out.append(f"  {name}: {len(items)} more, not listed")
            continue
        for text, line_no in items[:cap]:
            n += 1
            out.append(f"  {n}. {trim_item(text, ITEM_BUDGET, line_no, short=True)}")
        if len(items) > cap:
            out.append(f"     +{len(items) - cap} more")
    return out


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description="Deterministic project_progress.md digest for resume.")
    parser.add_argument('--project-root', required=True, help="This project's absolute root.")
    parser.add_argument('--max-lines', type=int, default=60,
                        help="Per-section line cap (default 60).")
    parser.add_argument('--max-chars', type=int, default=5000,
                        help="Per-section character cap (default 5000); whichever cap hits first.")
    args = parser.parse_args()

    root = Path(args.project_root).expanduser().resolve()
    path = root / 'project_progress.md'
    print("=== resume_digest.py ===")
    print(f"Host: {host_line()}")
    if not path.exists():
        print(f"[ABSENT] {path} does not exist - no progress doc to digest.")
        return
    lines = path.read_text(encoding='utf-8').splitlines()
    sections = split_sections(lines)

    found = {key: [] for key, *_ in SECTIONS}
    for text, start, end in sections:
        low = text.lower()
        for key, name, prefix, _req in SECTIONS:
            if low.startswith(prefix or name.lower()):
                found[key].append((text, start, end))
                break

    present = [name for key, name, _p, _r in SECTIONS if found[key]]
    absent_req = [name for key, name, _p, req in SECTIONS if req and not found[key]]
    absent_opt = [name for key, name, _p, req in SECTIONS if not req and not found[key]]
    print(f"Sections found: {', '.join(present) if present else '(none)'}")
    print(f"Required sections ABSENT: {', '.join(absent_req) if absent_req else 'none'}")
    print(f"Optional sections not used by this project: {', '.join(absent_opt) if absent_opt else 'none'}")
    print()

    for key, name, _p, _r in SECTIONS:
        for text, start, end in found[key]:
            body = lines[start + 1:end]
            first_line_no = start + 2  # 1-indexed line number of body[0]
            if key == 'worklog':
                b = newest_entry_bounds(body)
                if b is None:
                    emit_capped("Most recent Work Log entry", [], first_line_no,
                                args.max_lines, args.max_chars)
                else:
                    s, e = b
                    emit_capped("Most recent Work Log entry", body[s:e], first_line_no + s,
                                args.max_lines, args.max_chars)
            else:
                emit_capped(text, body, first_line_no, args.max_lines, args.max_chars)

    for key in ('status', 'next'):
        item, item_line = None, 0
        sections = found[key] or (found['focus'] if key == 'status' else [])
        for _text, start, end in sections:
            body = lines[start + 1:end]
            hit = None if sections is found['focus'] else next_item(body)  # Current Focus is prose-led
            if hit:
                item, item_line = hit[0], start + 2 + hit[1]
            else:
                # prose-form Current Status: first non-blank line that isn't a '(...)' instruction note
                idx = next((j for j, l in enumerate(body)
                            if l.strip() and not l.strip().startswith('(')), None)
                if idx is not None:
                    para = []
                    for l in body[idx:]:
                        if not l.strip():
                            break
                        para.append(l.strip())
                    item, item_line = ' '.join(para), start + 2 + idx
            if item:
                break
        missing = '(section absent)' if not sections else '(none found - the section has no text)'
        print(f"{key.upper()}: {trim_item(item, 400, item_line) if item else missing}")

    for _text, start, end in found['next'][:1]:
        block = next_list(lines[start + 1:end], start + 2)
        if len(block) > 1:
            print("NEXT LIST (resume's Next; quick resume uses the NEXT: line above):")
            print('\n'.join(block))


if __name__ == '__main__':
    main()
