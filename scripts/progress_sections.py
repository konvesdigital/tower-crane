#!/usr/bin/env python3
"""
progress_sections.py - prints exactly the four pieces of project_progress.md that AGENTS.md's
"resume" (step 4) and "quick resume" (step 2) both need: Current Status, Next Up, the Decisions
table, and only the MOST RECENT Work Log entry. Replaces a by-hand grep-for-headings-then-Read-with-
offset dance repeated at the start of every session with one deterministic call - same motivation
as resume_check.py (B1) consolidating the four notify-only sync checks, and ticket_scan.py replacing
hand-derived ticket categorization.

Section boundaries are fixed by project_progress.md's own documented structure (its own header
comment / agents_continuity.md's "checkpoint" step 1): four top-level '## ' headings, always in
this order - Current Status, Next Up, Decisions, Work Log - each running to the next '## ' heading
or end of file. The Work Log heading itself carries extra trailing text (an inline instruction),
matched by prefix rather than an exact string so a future rewording doesn't silently break this.

Work Log entries are newest-first, each starting at a line beginning with '**YYYY-MM-DD' (bold
dated header - project_progress.md's own convention, confirmed 2026-09-14). Recognized with the
same tolerant pattern ticket_scan.py already uses for round-trip logs (also accepting a plain
'- ' dash-bullet start) rather than assuming the bold form only, after that exact single-form
assumption already caused ticket_scan.py to silently miss real entries once (see
project_progress.md's own Decisions table, "ticket_scan.py's round-trip-log parser").
"""

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PROGRESS_PATH = PROJECT_ROOT / 'project_progress.md'

HEADING_RE = re.compile(r'^## (Current Status|Next Up|Decisions|Work Log)\b.*$', re.MULTILINE)
ENTRY_START_RE = re.compile(r'^(?:- |\*\*\d{4}-\d{2}-\d{2}\b)')


def extract_sections(text):
    """Returns {heading_name: body_text} for the four fixed sections, each sliced from just after
    its own heading line to the start of the next matched heading (or end of file)."""
    matches = list(HEADING_RE.finditer(text))
    sections = {}
    for i, m in enumerate(matches):
        name = m.group(1)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections[name] = text[start:end].strip('\n')
    return sections


def most_recent_entry(work_log_body):
    """First entry in the (newest-first) Work Log body - same entry-boundary tolerance as
    ticket_scan.py's _log_entries(), scoped here to just the leading entry since that's all any
    caller needs."""
    lines = work_log_body.splitlines()
    start = None
    for i, line in enumerate(lines):
        if ENTRY_START_RE.match(line):
            start = i
            break
    if start is None:
        return work_log_body.strip()
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if ENTRY_START_RE.match(lines[i]):
            end = i
            break
    return '\n'.join(lines[start:end]).strip('\n')


def main():
    # project_progress.md's Decisions table uses non-cp1252 characters (e.g. the pointer arrow
    # '→') that crash a plain print() on Windows' default console codepage.
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

    if not PROGRESS_PATH.exists():
        print(f"[ERROR] {PROGRESS_PATH} not found.", file=sys.stderr)
        sys.exit(1)

    text = PROGRESS_PATH.read_text(encoding='utf-8')
    sections = extract_sections(text)

    missing = [name for name in ('Current Status', 'Next Up', 'Decisions', 'Work Log') if name not in sections]
    if missing:
        print(f"[ERROR] project_progress.md is missing expected heading(s): {', '.join(missing)}. "
              "Read the file directly this time.", file=sys.stderr)
        sys.exit(1)

    print("=== Current Status ===")
    print(sections['Current Status'])
    print()
    print("=== Next Up ===")
    print(sections['Next Up'])
    print()
    print("=== Decisions ===")
    print(sections['Decisions'])
    print()
    print("=== Most Recent Work Log Entry ===")
    print(most_recent_entry(sections['Work Log']))


if __name__ == '__main__':
    main()
