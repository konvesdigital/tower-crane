#!/usr/bin/env python3
"""
ticket_scan.py - pure-Python, zero-AI mechanical scan of change_requests\\*.md, the token-free
gate `scripts\\run_automation.py` (Piece 3, design\\sync_automation.md) checks before ever paying
for a headless Claude Code invocation.

Two responsibilities, both importable (no `claude` subprocess calls live here):

  scan() / parse_ticket() - categorize every OPEN ticket using the exact rule CLAUDE.md's
    "Scanning at session start" already documents for a human session, plus two states this piece
    introduces (a PR already open awaiting review; that PR closed without merging).

  apply_mechanical_actions() - perform the categories that need no judgment at all: flip a
    consumer-verified ticket to DONE, and react to a previously-opened automation PR's outcome
    (merged -> append a "PR merged" round-trip line; closed unmerged -> append a "closed without
    merging" line so the ticket becomes fix-worthy again next scan). Every write here touches only
    change_requests\\<file>.md - `git add change_requests`, never `-A` - so the "auto-merge never
    for hooks\\/scripts\\/templates\\/agents\\" boundary stays unambiguous even though this
    ticket-inbox bookkeeping itself goes straight to main (Piece 1's already-locked precedent: a
    filed ticket / its own metadata is inert until acted on, so it stays ungated).

  Attempt-tracking (load_state/record_attempt/is_backed_off) is separate from categorization so a
    ticket whose fix keeps failing check_tower_crane.py backs off after max_attempts instead of
    starving every other candidate behind it forever (run_automation.py always picks the oldest
    fix-worthy ticket first).

No golden-suite fixtures - matches the established convention for scripts\\*.py maintainer tooling
(relocate.py, publish_release.py, broadcast_guidance.py, self_hooks.py all have none either;
check_tower_crane.py's golden discovery is hardcoded to hooks\\<tool>.py, not scripts\\). Verified
via manual/live testing against real ticket files instead - see project_progress.md.
"""

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

SHARED_ROOT = Path(__file__).resolve().parent.parent
# change_requests\ and .claude\ are private/per-machine hub state, not shipped toolkit content -
# both live at the outer root (design\local_first_reframe.md's outer/inner split), one level
# above SHARED_ROOT (toolkit\).
PROJECT_ROOT = SHARED_ROOT.parent
CHANGE_REQUESTS_DIR = PROJECT_ROOT / 'change_requests'
STATE_PATH = PROJECT_ROOT / '.claude' / 'automation_state.json'


class Category:
    NO_ACTIVITY = 'no_activity'
    AWAITING_CONSUMER = 'awaiting_consumer'
    VERIFIED_PASS = 'verified_pass'
    STILL_FAILS = 'still_fails'
    AWAITING_PR_REVIEW = 'awaiting_pr_review'   # last line: an automation "PR opened" line
    PR_REJECTED = 'pr_rejected'                 # that PR was closed without merging
    UNKNOWN_STATE = 'unknown_state'              # non-empty log, none of the above - log, don't guess
    REGISTRATION = 'registration'                # Type: registration - excluded from all automation


# Categories a candidate ticket must be in for run_automation.py to consider spending an AI
# invocation on it.
FIX_WORTHY = (Category.NO_ACTIVITY, Category.STILL_FAILS, Category.PR_REJECTED)

STATUS_RE = re.compile(r'^Status:\s*(OPEN|DONE)\s*$', re.MULTILINE)
TYPE_REGISTRATION_RE = re.compile(r'^Type:\s*registration\s*$', re.MULTILINE | re.IGNORECASE)
SECTION_HEADING_RE = re.compile(r'^##\s*(Round-trip log|Processing log)\s*$', re.MULTILINE)
NEXT_HEADING_RE = re.compile(r'^##\s', re.MULTILINE)

RE_VERIFIED_PASS = re.compile(r'verified PASS', re.IGNORECASE)
RE_STILL_FAILS = re.compile(r'still fails', re.IGNORECASE)
RE_PR_CLOSED = re.compile(r'PR #(\d+) closed without merging', re.IGNORECASE)
RE_PR_OPENED = re.compile(r'PR #(\d+) opened', re.IGNORECASE)
RE_PR_MERGED = re.compile(r'PR #(\d+) merged', re.IGNORECASE)
RE_AWAITING = re.compile(r'\bawaiting\b.+?\bverify\b', re.IGNORECASE)
RE_AFFECTS = re.compile(r'affects:\s*([^;]+?)(?:[;.]|$)', re.IGNORECASE)


@dataclass
class Ticket:
    path: Path
    slug: str               # path.stem - used verbatim as the auto/<slug> branch suffix
    status: str              # 'OPEN' or 'DONE' (None if unparseable)
    is_registration: bool
    last_entry: str           # full text of the last '## Round-trip log' / '## Processing log' bullet
    category: str
    pr_number: int = None


def _log_entries(section_body):
    """Split a log section's body into bullet entries. An entry starts at a line beginning with
    '- ' (no leading whitespace); any following non-'- '-prefixed lines are that entry's
    continuation (matches every real ticket's wrapped-paragraph style, e.g.
    change_requests\\2026-07-20_consistency_check_ps1-to-python.md's multi-line bullets)."""
    entries = []
    current = []
    for line in section_body.splitlines():
        if line.startswith('- '):
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
        return Category.REGISTRATION, None
    if not last_entry:
        return Category.NO_ACTIVITY, None
    if RE_VERIFIED_PASS.search(last_entry):
        return Category.VERIFIED_PASS, None
    if RE_STILL_FAILS.search(last_entry):
        return Category.STILL_FAILS, None
    m = RE_PR_CLOSED.search(last_entry)
    if m:
        return Category.PR_REJECTED, int(m.group(1))
    m = RE_PR_OPENED.search(last_entry)
    if m:
        return Category.AWAITING_PR_REVIEW, int(m.group(1))
    if RE_AWAITING.search(last_entry):
        return Category.AWAITING_CONSUMER, None
    return Category.UNKNOWN_STATE, None


def parse_ticket(path):
    text = path.read_text(encoding='utf-8')
    m = STATUS_RE.search(text)
    status = m.group(1) if m else None
    is_registration = bool(TYPE_REGISTRATION_RE.search(text))
    last_entry = _last_log_entry(text)
    category, pr_number = _categorize(status, is_registration, last_entry)
    return Ticket(path=path, slug=path.stem, status=status, is_registration=is_registration,
                  last_entry=last_entry, category=category, pr_number=pr_number)


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
    both apply_mechanical_actions() here and run_automation.py's own "fix proposed" line, so every
    automation-authored append goes through one code path."""
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


# --- mechanical actions: no judgment required, safe to perform without an AI invocation -----------
def _run_git(args, cwd=SHARED_ROOT):
    return subprocess.run(['git', '-C', str(cwd)] + args, capture_output=True, text=True, check=True)


def _run_gh_pr_view(pr_number, cwd=SHARED_ROOT):
    proc = subprocess.run(
        ['gh', 'pr', 'view', str(pr_number), '--json', 'state,mergeCommit'],
        cwd=str(cwd), capture_output=True, text=True,
    )
    if proc.returncode != 0:
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None


def apply_mechanical_actions(tickets, dry_run=False):
    """Handle VERIFIED_PASS (flip DONE) and AWAITING_PR_REVIEW (check gh for merge/close outcome).
    Mutates each affected Ticket's .category/.status in place so a status change (e.g. a PR that
    just got rejected) is visible to needs_fix_candidates() in the SAME tick, not next hour's scan.
    Returns a summary dict. One commit+push covering everything changed, not one per ticket."""
    today = date.today().isoformat()
    touched_files = []
    summary = {'done_flipped': [], 'pr_merged': [], 'pr_closed': [], 'errors': []}

    for t in tickets:
        if t.category == Category.VERIFIED_PASS:
            if not dry_run:
                append_log_line(t.path, f"- {today} — automation: Status flipped to DONE (consumer verified PASS).")
                flip_status_done(t.path)
            t.status = 'DONE'
            touched_files.append(t.path)
            summary['done_flipped'].append(t.slug)

        elif t.category == Category.AWAITING_PR_REVIEW and t.pr_number:
            info = _run_gh_pr_view(t.pr_number)
            if info is None:
                summary['errors'].append(f"{t.slug}: could not read PR #{t.pr_number} state")
                continue
            state_ = info.get('state')
            if state_ == 'MERGED':
                affects_m = RE_AFFECTS.search(t.last_entry or '')
                affects = affects_m.group(1).strip() if affects_m else 'unspecified'
                sha = (info.get('mergeCommit') or {}).get('oid', 'unknown')[:9]
                if not dry_run:
                    append_log_line(
                        t.path,
                        f"- {today} — automation: PR #{t.pr_number} merged (commit `{sha}`), "
                        f"affects: {affects}; awaiting {affects} verify.",
                    )
                t.category = Category.AWAITING_CONSUMER
                touched_files.append(t.path)
                summary['pr_merged'].append(t.slug)
            elif state_ == 'CLOSED':
                if not dry_run:
                    append_log_line(
                        t.path,
                        f"- {today} — automation: PR #{t.pr_number} closed without merging; "
                        "returning to shared side for re-fix.",
                    )
                t.category = Category.PR_REJECTED
                touched_files.append(t.path)
                summary['pr_closed'].append(t.slug)
            # state_ == 'OPEN' -> still pending, nothing to do.

    if touched_files and not dry_run:
        rel = [str(p.relative_to(SHARED_ROOT)) for p in touched_files]
        try:
            _run_git(['add'] + rel)
            _run_git(['commit', '-m', f"automation: ticket bookkeeping ({len(rel)} file(s))"])
            _run_git(['push', 'origin', 'main'])
        except subprocess.CalledProcessError as e:
            summary['errors'].append(f"git commit/push of ticket bookkeeping failed: {e.stderr}")

    return summary


def _cli_report(tickets):
    for t in tickets:
        pr = f" (PR #{t.pr_number})" if t.pr_number else ''
        print(f"  [{t.category}]{pr} {t.path.name}")


def main():
    parser = argparse.ArgumentParser(description="Mechanical, zero-AI scan/bookkeeping of change_requests\\*.md.")
    parser.add_argument('--apply', action='store_true', help="Perform mechanical bookkeeping (DONE flips, PR merge/close bookkeeping). Without this flag, dry-run report only.")
    parser.add_argument('--json', action='store_true', help="Emit the categorized report as JSON instead of text.")
    args = parser.parse_args()

    tickets = scan()
    if args.apply:
        summary = apply_mechanical_actions(tickets)
        if args.json:
            print(json.dumps(summary, indent=2))
        else:
            print("=== ticket_scan.py --apply ===")
            for k, v in summary.items():
                print(f"  {k}: {v}")
        return

    if args.json:
        print(json.dumps([
            {'slug': t.slug, 'category': t.category, 'pr_number': t.pr_number} for t in tickets
        ], indent=2))
    else:
        print("=== ticket_scan.py (dry-run report) ===")
        _cli_report(tickets)


if __name__ == '__main__':
    main()
