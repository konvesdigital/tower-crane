#!/usr/bin/env python3
"""
work_log_entry_check.py - checks the NEWEST Work Log entry in project_progress.md against the
entry template `checkpoint` step 1 defines, and flags DONE/REMOVED/BUILT/DROPPED in Current
Status and Next Up. Also scans the WHOLE file for stray control characters (TAB, BEL, a lone
carriage return, any other non-text byte; a CRLF line ending is fine). Read-only; prints [OK] or
one [OVER-CAP]/[BAD-HEADER]/[STALE-MARKER]/[CONTROL-CHAR] line per problem. Always exits 0 - a
warning to fix before committing, never a block.

The template (what checkpoint step 1 tells the author to write):
  Header line:  **YYYY-MM-DD - <host> / <repo> session (<topic>):** <first sentence of body>
  Body:         what changed, then what was NOT run or verified, then `Next:` - in that order.
  Cap:          MAX_LINES lines in total (header included), wrapped at 100 columns.

Usage: python work_log_entry_check.py --project-root "<absolute project root>"
"""

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from resume_digest import split_sections  # noqa: E402
from archive_candidates import split_entries  # noqa: E402

MAX_LINES = 10
LIVE_SECTIONS = ('current status', 'next up')
MARKER_RE = re.compile(r'\b(DONE|REMOVED|BUILT|DROPPED)\b')
HEADER_RE = re.compile(r'^\*\*\d{4}-\d{2}-\d{2}\s*[—–-]\s*.+?:\*\*')
# Every control character except the line feed; a carriage return is checked separately in
# control_char_problems() because only a CRLF pair is legitimate.
CONTROL_RE = re.compile(r'[\x00-\x09\x0b-\x1f\x7f]')
CONTROL_NAMES = {'\t': 'TAB', '\x07': 'BEL', '\r': 'lone carriage return'}
MAX_SHOWN = 5


def control_char_problems(text):
    """One [CONTROL-CHAR] line per kind of stray character, with up to MAX_SHOWN line numbers.
    A carriage return directly before a line feed (CRLF) is normal and not reported."""
    found = {}
    for m in CONTROL_RE.finditer(text):
        char = m.group()
        if char == '\r' and text[m.end():m.end() + 1] == '\n':
            continue
        found.setdefault(char, []).append(text.count('\n', 0, m.start()) + 1)
    out = []
    for char, where in found.items():
        shown = ', '.join(str(n) for n in where[:MAX_SHOWN])
        more = ' (+%d more)' % (len(where) - MAX_SHOWN) if len(where) > MAX_SHOWN else ''
        out.append('[CONTROL-CHAR] %s x%d at line %s%s - delete it; it is not text.'
                   % (CONTROL_NAMES.get(char, 'U+%04X' % ord(char)), len(where), shown, more))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--project-root', required=True)
    root = Path(ap.parse_args().project_root)
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    try:
        # Raw bytes, not read_text(): universal-newline reading would turn a lone carriage
        # return into a line break and hide it from the control-character scan below.
        text = (root / 'project_progress.md').read_bytes().decode('utf-8', errors='replace')
    except OSError:
        print('[ABSENT] project_progress.md not readable - no entry to check.')
        return 0
    lines = text.splitlines()
    problems = control_char_problems(text)
    for text, s, e in split_sections(lines):
        name = next((n for n in LIVE_SECTIONS if text.lower().startswith(n)), None)
        if not name:
            continue
        for i in range(s, e):
            m = MARKER_RE.search(lines[i])
            if m:
                problems.append('[STALE-MARKER] line %d (%s): `%s` - delete the finished item or '
                                'rewrite it to what remains.' % (i + 1, name, m.group(1)))
    sec = next(((s, e) for text, s, e in split_sections(lines)
                if text.lower().startswith('work log')), None)
    entries = split_entries(lines[sec[0]:sec[1]], sec[0]) if sec else []
    if not entries:
        print('\n'.join(problems) if problems else
              '[ABSENT] no Work Log entries found - nothing to check.')
        return 0
    start, body = entries[0]
    while body and not body[-1].strip():
        body = body[:-1]
    if not HEADER_RE.match(body[0]):
        problems.append('[BAD-HEADER] line %d should start `**YYYY-MM-DD — <host> / <repo> '
                        'session (<topic>):**`.' % start)
    if len(body) > MAX_LINES:
        problems.append('[OVER-CAP] newest entry (line %d) is %d lines; cap is %d. Cut it to '
                        'what changed / what was not run / Next:.' % (start, len(body), MAX_LINES))
    print('\n'.join(problems) if problems else
          '[OK] newest Work Log entry fits the template (%d lines).' % len(body))
    return 0


if __name__ == '__main__':
    sys.exit(main())
