#!/usr/bin/env python3
"""
archive_candidates.py - the deterministic first pass of `"archive"`: lists every Work Log entry
with a verdict, and classifies every Current Status / Next Up item into the three buckets
`agents_continuity.md` defines. Read-only; never edits or moves anything (the move is the
procedure's step 4-5 / 9, done after the user sees this).

Work Log verdicts (first rule that matches wins):
  [KEEP]    - the newest entry (`resume` reads it), or its title text is cited in Current Status,
              Next Up or Decisions, or it names a change_requests\\ ticket whose Status is not DONE.
  [ASK]     - not cited by title, but its date is cited on a Current Status / Next Up line that also says 'Work Log', or
              its body holds an open-work phrase (OPEN_PHRASES below). Ask about that entry
              specifically; never "where's the cutoff".
  [ARCHIVE] - none of the above: complete and nothing depends on it.

Current Status / Next Up buckets (first rule that matches wins - the order IS the precedence):
  [IN-PROGRESS] - the item holds an open-caveat word (OPEN_WORDS), or has no completion verb,
                  acceptance phrase or date to place it elsewhere.
  [STANDING]    - the item holds an acceptance phrase (ACCEPT_PHRASES).
  [CALCIFIED]   - the item holds a completion verb (DONE_WORDS) AND a YYYY-MM-DD date.
A mixed item is classified whole; trimming it to its residue first (procedure step 7) can still
move it, so treat this table as the starting classification, not the final one.

Usage: python archive_candidates.py --project-root "<absolute project root>"
Always exits 0 for a readable project_progress.md.
"""

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from resume_digest import split_sections  # noqa: E402

ENTRY_STYLES = [
    re.compile(r'^(?:\*\*|### )\d{4}-\d{2}-\d{2}'),   # **2026-10-07 - title:** / ### 2026-10-07
    re.compile(r'^- '),                                # bullet-per-entry projects
]
DATE_RE = re.compile(r'\d{4}-\d{2}-\d{2}')
TICKET_RE = re.compile(r'\b(\d{4}-\d{2}-\d{2}_[\w.-]+\.md)\b')
ITEM_RE = re.compile(r'^(?:- |\* |\d+[.)] |\[[ xX]\] )')

OPEN_PHRASES = ['not started', 'not yet', 'still open', 'unexercised', 'pending', 'awaiting',
                'not run', 'was not run', 'todo']
OPEN_WORDS = ['not yet', 'still', 'unconfirmed', 'unproven', 'not started', 'unexercised',
              "hasn't", 'has not', 'no design', 'not decided', 'not scoped', 'pending', 'todo',
              'open', 'unfixed', 'no plan', 'unknown']
ACCEPT_PHRASES = ['deliberately', 'not a bug', 'accepted', 'either way', 'by design',
                  'intentionally', 'left as is']
DONE_WORDS = ['built', 'fixed', 'verified', 'confirmed', 'found', 'resolved', 'done',
              'live-tested', 'audited']


def has(text, needles):
    low = text.lower()
    return [n for n in needles if re.search(r'(?<![\w])' + re.escape(n) + r'(?![\w])', low)]


def entry_title(first_line):
    m = re.match(r'^(?:\*\*|### |- )(.*?)(?::\*\*|$)', first_line)
    t = (m.group(1) if m else first_line).strip(' *')
    return t[:110]


def title_key(title):
    """The distinctive part of an entry header: the parenthetical if there is one, else the whole
    text after the date. Used to decide whether another section cites this exact entry."""
    m = re.search(r'\(([^)]{6,})\)', title)
    if m:
        return m.group(1).strip().lower()
    return re.sub(r'^\d{4}-\d{2}-\d{2}\s*[—–-]*\s*', '', title).strip().lower()


def split_entries(body, offset):
    for style in ENTRY_STYLES:
        starts = [i for i, l in enumerate(body) if style.match(l)]
        if starts:
            break
    else:
        return []
    entries = []
    for n, s in enumerate(starts):
        e = starts[n + 1] if n + 1 < len(starts) else len(body)
        entries.append((offset + s + 1, body[s:e]))   # (1-based file line, lines)
    return entries


def open_tickets(root):
    d = root / 'change_requests'
    out = {}
    if d.is_dir():
        for f in d.glob('*.md'):
            try:
                head = f.read_text(encoding='utf-8').splitlines()[:3]
            except OSError:
                continue
            status = next((l.split(':', 1)[1].strip() for l in head if l.startswith('Status:')), '')
            out[f.name] = status
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--project-root', required=True)
    root = Path(ap.parse_args().project_root)
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    prog = root / 'project_progress.md'
    try:
        lines = prog.read_text(encoding='utf-8').splitlines()
    except OSError:
        print(f'[ABSENT] {prog} not readable - nothing to archive.')
        return 0

    secs = {}
    for text, s, e in split_sections(lines):
        low = text.lower()
        for key in ('current status', 'current focus', 'next up', 'decisions', 'work log'):
            if low.startswith(key) and key not in secs:
                secs[key] = (s, e)

    def body(key):
        s, e = secs[key]
        return lines[s + 1:e]

    live_text = {k: '\n'.join(body(k)).lower() for k in
                 ('current status', 'current focus', 'next up', 'decisions') if k in secs}
    all_live = '\n'.join(live_text.values())
    dated_text = '\n'.join(live_text.get(k, '') for k in ('current status', 'current focus', 'next up'))
    tickets = open_tickets(root)

    print('=== WORK LOG ===')
    counts = {'ARCHIVE': 0, 'KEEP': 0, 'ASK': 0}
    if 'work log' not in secs:
        print('(no Work Log section)')
    else:
        entries = split_entries(body('work log'), secs['work log'][0] + 1)
        for idx, (lineno, elines) in enumerate(entries):
            title = entry_title(elines[0])
            text = '\n'.join(elines)
            date = (DATE_RE.search(title) or DATE_RE.search(text) or [''])
            date = date.group(0) if hasattr(date, 'group') else ''
            key = title_key(title)
            reasons, verdict = [], 'ARCHIVE'
            open_tix = [t for t in TICKET_RE.findall(text) if t in tickets and tickets[t].lower() != 'done']
            if idx == 0:
                verdict, reasons = 'KEEP', ['newest entry - resume reads it']
            elif len(key) >= 6 and key in all_live:
                verdict, reasons = 'KEEP', ['title cited in Current Status/Next Up/Decisions']
            elif open_tix:
                verdict, reasons = 'KEEP', [f'names non-DONE ticket {open_tix[0]}']
            else:
                if date and any(date in l and 'work log' in l for l in dated_text.splitlines()):
                    verdict = 'ASK'
                    reasons.append(f'date {date} cited in a live section')
                hits = has(text, OPEN_PHRASES)
                if hits:
                    verdict = 'ASK'
                    reasons.append('open-work phrase: ' + ', '.join(hits))
            counts[verdict] += 1
            why = f' ({"; ".join(reasons)})' if reasons else ''
            print(f'[{verdict}] line {lineno} - {title}{why}')

    print('\n=== CURRENT STATUS / NEXT UP ===')
    buckets = {'CALCIFIED': 0, 'STANDING': 0, 'IN-PROGRESS': 0}
    for key in ('current status', 'current focus', 'next up'):
        if key not in secs:
            continue
        sbody, base = body(key), secs[key][0] + 2
        starts = [i for i, l in enumerate(sbody) if ITEM_RE.match(l)]
        for n, s in enumerate(starts):
            e = starts[n + 1] if n + 1 < len(starts) else len(sbody)
            item = ' '.join(l.strip() for l in sbody[s:e]).strip()
            open_w, accept, done = has(item, OPEN_WORDS), has(item, ACCEPT_PHRASES), has(item, DONE_WORDS)
            dated = bool(DATE_RE.search(item))
            if open_w:
                b, sig = 'IN-PROGRESS', 'open: ' + ', '.join(open_w[:3])
            elif accept:
                b, sig = 'STANDING', 'accepted: ' + ', '.join(accept[:3])
            elif done and dated:
                b, sig = 'CALCIFIED', 'done: ' + ', '.join(done[:3]) + ' + date'
            else:
                b, sig = 'IN-PROGRESS', 'no completion+date signal'
            buckets[b] += 1
            print(f'[{b}] {key.title()} line {base + s} - {item[:90]} ({sig})')

    print('\n=== SUMMARY ===')
    print('Work Log: ' + ', '.join(f'{v} {k}' for k, v in counts.items()) +
          ' | Items: ' + ', '.join(f'{v} {k}' for k, v in buckets.items()))
    return 0


if __name__ == '__main__':
    sys.exit(main())
