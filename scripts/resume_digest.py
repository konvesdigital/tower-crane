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
  STATUS: line - the first list item in Current Status (200 chars max)
  NEXT: line - the first unchecked checkbox item in Next Up, else the first list item (200 max)

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


def next_item(body):
    """First unchecked-checkbox list item, else first list item that isn't a checked checkbox."""
    items = []
    for line in body:
        m = LIST_ITEM_RE.match(line)
        if m:
            items.append(m.group(1).strip())
    for text in items:
        m = CHECKBOX_OPEN_RE.match(text)
        if m:
            return m.group(1).strip()
    for text in items:
        if not CHECKBOX_DONE_RE.match(text):
            return text
    return None


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
        item = None
        for _text, start, end in found[key]:
            body = lines[start + 1:end]
            item = next_item(body)
            if not item and key == 'status':
                # prose-form Current Status: first non-blank line that isn't a '(...)' instruction note
                item = next((l.strip() for l in body if l.strip() and not l.strip().startswith('(')), None)
            if item:
                break
        missing = '(section absent)' if not found[key] else '(none found - the section has no text)'
        print(f"{key.upper()}: {item[:200] if item else missing}")


if __name__ == '__main__':
    main()
