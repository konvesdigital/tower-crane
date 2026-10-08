#!/usr/bin/env python3
"""
work_log_entry_check.py - checks the NEWEST Work Log entry in project_progress.md against the
entry template `checkpoint` step 1 defines. Read-only; prints [OK] or one [OVER-CAP]/[BAD-HEADER]
line per problem. Always exits 0 - a warning to fix before committing, never a block.

The template (what checkpoint step 1 tells the author to write):
  Header line:  **YYYY-MM-DD - <host or author> session (<topic>):** <first sentence of body>
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
HEADER_RE = re.compile(r'^\*\*\d{4}-\d{2}-\d{2}\s*[—–-]\s*.+?:\*\*')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--project-root', required=True)
    root = Path(ap.parse_args().project_root)
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    try:
        lines = (root / 'project_progress.md').read_text(encoding='utf-8').splitlines()
    except OSError:
        print('[ABSENT] project_progress.md not readable - no entry to check.')
        return 0
    sec = next(((s, e) for text, s, e in split_sections(lines)
                if text.lower().startswith('work log')), None)
    entries = split_entries(lines[sec[0]:sec[1]], sec[0]) if sec else []
    if not entries:
        print('[ABSENT] no Work Log entries found - nothing to check.')
        return 0
    start, body = entries[0]
    while body and not body[-1].strip():
        body = body[:-1]
    problems = []
    if not HEADER_RE.match(body[0]):
        problems.append('[BAD-HEADER] line %d should start `**YYYY-MM-DD — <who> session '
                        '(<topic>):**`.' % start)
    if len(body) > MAX_LINES:
        problems.append('[OVER-CAP] newest entry (line %d) is %d lines; cap is %d. Cut it to '
                        'what changed / what was not run / Next:.' % (start, len(body), MAX_LINES))
    print('\n'.join(problems) if problems else
          '[OK] newest Work Log entry fits the template (%d lines).' % len(body))
    return 0


if __name__ == '__main__':
    sys.exit(main())
