#!/usr/bin/env python3
"""
ticket_scan.py - pure-Python, zero-AI mechanical scan of change_requests\\*.md.

Two responsibilities, both importable (no `claude` subprocess calls live here):

  scan() / parse_ticket() - categorize every OPEN ticket using the same rule a human session's
    "Scanning at session start" check applies. No PR-outcome states exist here (local ticket fixes
    commit directly, no PR is ever opened for a ticket) - just VERIFIED_PASS, on top of the
    ordinary categories.

  filter_by_project() - narrows a scan() result to tickets that plausibly mention a given consumer
    project (case-insensitive substring over each ticket's raw text), reached via `--project` on
    the CLI.

  mark_done() - flip consumer-verified / operator-overridden tickets to DONE. Local edits to
    change_requests\\<file>.md only - never runs git. Returns the touched paths in its summary.
    The CLI's default report lists these as ready to flip; `--mark-done` performs the flip and
    prints the remaining OPEN tickets' categorization afterward.

  Attempt-tracking (load_state/record_attempt/is_backed_off) is separate from categorization so a
    ticket whose fix keeps failing check_tower_crane.py backs off after max_attempts instead of
    starving every other candidate behind it forever (run_automation.py always picks the oldest
    fix-worthy ticket first).
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

SHARED_ROOT = Path(__file__).resolve().parent.parent
# change_requests\ and .claude\ are private/per-machine hub state, not shipped toolkit content -
# both live at the outer root (the outer/inner repo split), one level
# above SHARED_ROOT (toolkit\).
PROJECT_ROOT = SHARED_ROOT.parent
CHANGE_REQUESTS_DIR = PROJECT_ROOT / 'change_requests'
STATE_PATH = PROJECT_ROOT / '.claude' / 'automation_state.json'


class Category:
    NO_ACTIVITY = 'no_activity'
    AWAITING_CONSUMER = 'awaiting_consumer'
    VERIFIED_PASS = 'verified_pass'
    STILL_FAILS = 'still_fails'
    OPERATOR_OVERRIDE = 'operator_override'      # operator directly instructed a DONE flip
    UNKNOWN_STATE = 'unknown_state'              # non-empty log, none of the above - log, don't guess
    REGISTRATION = 'registration'                # Type: registration - excluded from all automation


# Categories a candidate ticket must be in for run_automation.py to consider spending an AI
# invocation on it.
FIX_WORTHY = (Category.NO_ACTIVITY, Category.STILL_FAILS)
DONE_READY = (Category.VERIFIED_PASS, Category.OPERATOR_OVERRIDE)

STATUS_RE = re.compile(r'^Status:\s*(OPEN|DONE)\s*$', re.MULTILINE)
TYPE_REGISTRATION_RE = re.compile(r'^Type:\s*registration\s*$', re.MULTILINE | re.IGNORECASE)
SECTION_HEADING_RE = re.compile(r'^##\s*(Round-trip log|Processing log)\s*$', re.MULTILINE)
NEXT_HEADING_RE = re.compile(r'^##\s', re.MULTILINE)

RE_OPERATOR_OVERRIDE = re.compile(r'\boperator override\b', re.IGNORECASE)
RE_VERIFIED_PASS = re.compile(r'verified\s+PASS', re.IGNORECASE)
RE_STILL_FAILS = re.compile(r'still\s+fails', re.IGNORECASE)
RE_AWAITING = re.compile(r'\bawaiting\b.+?\bverify\b', re.IGNORECASE | re.DOTALL)


@dataclass
class Ticket:
    path: Path
    slug: str               # path.stem - used verbatim as the auto/<slug> branch suffix (fix commits)
    status: str              # 'OPEN' or 'DONE' (None if unparseable)
    is_registration: bool
    last_entry: str           # full text of the last '## Round-trip log' / '## Processing log' bullet
    category: str
    text: str                # full raw ticket text - used by --project's substring filter below


ENTRY_START_RE = re.compile(r'^(?:- |\*\*\d{4}-\d{2}-\d{2}\b)')


def _log_entries(section_body):
    """Split a log section's body into bullet entries. An entry starts at a line beginning with
    '- ' (no leading whitespace) OR at a line beginning with a bold dated header, e.g.
    '**2026-09-01 — ...**'. Any following line matching neither start pattern is that entry's
    continuation."""
    entries = []
    current = []
    for line in section_body.splitlines():
        if ENTRY_START_RE.match(line):
            if current:
                entries.append('\n'.join(current))
            current = [line]
        elif current:
            current.append(line)
    if current:
        entries.append('\n'.join(current))
    return entries


def _last_log_entry(text):
    m = SECTION_HEADING_RE.search(text)
    if not m:
        return None
    body = text[m.end():]
    nm = NEXT_HEADING_RE.search(body)
    if nm:
        body = body[:nm.start()]
    entries = _log_entries(body)
    return entries[-1] if entries else None


def _categorize(status, is_registration, last_entry):
    if is_registration:
        return Category.REGISTRATION
    if not last_entry:
        return Category.NO_ACTIVITY
    if RE_OPERATOR_OVERRIDE.search(last_entry):
        return Category.OPERATOR_OVERRIDE
    if RE_VERIFIED_PASS.search(last_entry):
        return Category.VERIFIED_PASS
    if RE_STILL_FAILS.search(last_entry):
        return Category.STILL_FAILS
    if RE_AWAITING.search(last_entry):
        return Category.AWAITING_CONSUMER
    return Category.UNKNOWN_STATE


def parse_ticket(path):
    text = path.read_text(encoding='utf-8')
    m = STATUS_RE.search(text)
    status = m.group(1) if m else None
    is_registration = bool(TYPE_REGISTRATION_RE.search(text))
    last_entry = _last_log_entry(text)
    category = _categorize(status, is_registration, last_entry)
    return Ticket(path=path, slug=path.stem, status=status, is_registration=is_registration,
                  last_entry=last_entry, category=category, text=text)


def scan(change_requests_dir=CHANGE_REQUESTS_DIR):
    """Every OPEN ticket, filename order (chronological - the YYYY-MM-DD prefix sorts naturally)."""
    if not change_requests_dir.is_dir():
        return []
    tickets = []
    for f in sorted(change_requests_dir.glob('*.md')):
        t = parse_ticket(f)
        if t.status == 'OPEN':
            tickets.append(t)
    return tickets


# --- append a dated round-trip/processing log line -----------------------------------------------
def append_log_line(ticket_path, line):
    """Append one line (caller includes the leading '- ') to the ticket's log section. Used by
    both mark_done() here and run_automation.py's own "fix proposed" line."""
    text = ticket_path.read_text(encoding='utf-8')
    if not text.endswith('\n'):
        text += '\n'
    text += line.rstrip('\n') + '\n'
    ticket_path.write_text(text, encoding='utf-8', newline='\n')


def flip_status_done(ticket_path):
    text = ticket_path.read_text(encoding='utf-8')
    new_text = STATUS_RE.sub('Status: DONE', text, count=1)
    ticket_path.write_text(new_text, encoding='utf-8', newline='\n')


# --- attempt-tracking state (.claude\automation_state.json, gitignored, per-machine) --------------
def load_state():
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding='utf-8'))
        except json.JSONDecodeError:
            pass
    return {'tickets': {}}


def save_state(state):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding='utf-8', newline='\n')


def record_attempt(state, slug, result):
    entry = state.setdefault('tickets', {}).setdefault(slug, {'attempts': 0})
    entry['attempts'] += 1
    entry['last_result'] = result
    entry['last_attempt'] = date.today().isoformat()
    return state


def clear_attempts(state, slug):
    state.setdefault('tickets', {}).pop(slug, None)
    return state


def is_backed_off(state, slug, max_attempts=3):
    entry = state.get('tickets', {}).get(slug)
    return bool(entry and entry.get('attempts', 0) >= max_attempts)


def needs_fix_candidates(tickets, state, max_attempts=3):
    return [t for t in tickets
            if t.category in FIX_WORTHY and not is_backed_off(state, t.slug, max_attempts)]


# --- mechanical actions: local file edits only, never git ------------------------------------------
def mark_done(tickets, dry_run=False):
    """Flip VERIFIED_PASS and OPERATOR_OVERRIDE tickets to DONE in the local ticket files.
    Mutates each affected Ticket's .status in place. Returns
    {'done_flipped': [slug, ...], 'touched': [Path, ...]}."""
    today = date.today().isoformat()
    touched_files = []
    summary = {'done_flipped': [], 'touched': touched_files}

    for t in tickets:
        if t.category == Category.VERIFIED_PASS:
            if not dry_run:
                append_log_line(t.path, f"- {today} — automation: Status flipped to DONE (consumer verified PASS).")
                flip_status_done(t.path)
            t.status = 'DONE'
            touched_files.append(t.path)
            summary['done_flipped'].append(t.slug)
        elif t.category == Category.OPERATOR_OVERRIDE:
            if not dry_run:
                append_log_line(t.path, f"- {today} — automation: Status flipped to DONE (operator override already logged).")
                flip_status_done(t.path)
            t.status = 'DONE'
            touched_files.append(t.path)
            summary['done_flipped'].append(t.slug)

    return summary


def filter_by_project(tickets, names):
    """Case-insensitive substring match against each ticket's full raw text, for any of `names`.
    Takes multiple names because a project may be named inconsistently across ticket text (a
    slug, a full title, an ad-hoc abbreviation) - pass every form this project is known by.

    A hit only means one of `names` appears somewhere in the ticket's text, not that this project
    is necessarily who's being awaited right now - a ticket can legitimately affect more than one
    consumer. For an AWAITING_CONSUMER hit specifically, the caller must still confirm the
    ticket's own last round-trip line actually names this project."""
    needles = [n.lower() for n in names]
    return [t for t in tickets if any(n in t.text.lower() for n in needles)]


def _cli_report(tickets):
    for t in tickets:
        print(f"  [{t.category}] {t.path.name}")


def main():
    parser = argparse.ArgumentParser(description="Mechanical, zero-AI local scan/bookkeeping of change_requests\\*.md. Never runs git.")
    parser.add_argument('--mark-done', action='store_true',
                         help="Flip verified/overridden tickets to DONE in the local ticket files (no git). "
                              "Without this flag, read-only report listing which tickets are ready to flip.")
    parser.add_argument('--json', action='store_true', help="Emit the categorized report as JSON instead of text.")
    parser.add_argument('--project', nargs='+', default=None,
                         help="Filter to tickets whose text mentions ANY of these project "
                              "names/slug/abbreviations (case-insensitive substring). Pass every "
                              "form this project is known by (slug, full name, common "
                              "abbreviation).")
    args = parser.parse_args()

    tickets = scan()
    if args.project:
        tickets = filter_by_project(tickets, args.project)
    if args.mark_done:
        flipped = mark_done(tickets)['done_flipped']
        remaining = [t for t in tickets if t.status == 'OPEN']
        if args.json:
            print(json.dumps({
                'done_flipped': flipped,
                'remaining': [{'slug': t.slug, 'category': t.category} for t in remaining],
            }, indent=2))
        else:
            print("=== ticket_scan.py --mark-done ===")
            print(f"  done_flipped (local, uncommitted): {flipped}")
            print("--- remaining OPEN tickets (categorized) ---")
            _cli_report(remaining)
        return

    if args.json:
        print(json.dumps([
            {'slug': t.slug, 'category': t.category} for t in tickets
        ], indent=2))
    else:
        ready = [t for t in tickets if t.category in DONE_READY]
        rest = [t for t in tickets if t.category not in DONE_READY]
        print("=== ticket_scan.py (categorize report, read-only) ===")
        if ready:
            print(f"--- ready to flip to DONE ({len(ready)}) - run: python toolkit/scripts/ticket_scan.py --mark-done ---")
            _cli_report(ready)
        print(f"--- other OPEN tickets ({len(rest)}) ---")
        _cli_report(rest)


if __name__ == '__main__':
    main()
