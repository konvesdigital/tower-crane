#!/usr/bin/env python3
"""
run_automation.py - wrapper an OS-level scheduled task invokes hourly to apply at most one
fix-worthy change_requests\\ ticket per tick.

No-op (exit 0) unless config.local.json's automation.enabled is true.

Two separate repos, two separate git targets: a ticket's tool fix physically lives in `toolkit\\`
(SHARED_ROOT) and commits there, LOCAL ONLY - never pushed. The ticket's own round-trip log
line/bookkeeping (including `ticket_scan.mark_done()`'s DONE flips) commits and pushes to the
outer (private) repo (PROJECT_ROOT).

Never runs `toolkit\\`'s own update/merge gate (`scripts\\update_toolkit.py --check`/`--approve`) -
only `--notify`, a plain surfacing check with no state mutation.

The headless `claude -p` invocation this script makes gets no git/gh/Bash access - it edits the
target shared-tool file(s) and nothing else. Every git call and the check_tower_crane.py pass/fail
gate live here, in deterministic Python. A before/after snapshot of the outer repo's own git status
runs around the agent invocation to catch a write outside `toolkit\\`.

`scripts\\automation_settings.json` must list Bash (and WebFetch/WebSearch/Agent/NotebookEdit)
under `permissions.deny`, not merely omit them from `permissions.allow` - an allow-only list does
not block `claude -p --permission-mode dontAsk` from running Bash.

Never flips a ticket's Status directly (only ticket_scan.py's mechanical DONE-flip for an
already-consumer-verified ticket does that).
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config_lib import get_shared_config
import ticket_scan

SHARED_ROOT = Path(__file__).resolve().parent.parent
# The outer (private) repo - change_requests\/project_progress.md live here.
PROJECT_ROOT = SHARED_ROOT.parent
CHECK_SCRIPT = SHARED_ROOT / 'scripts' / 'check_tower_crane.py'
UPDATE_SCRIPT = SHARED_ROOT / 'scripts' / 'update_toolkit.py'
AUTOMATION_SETTINGS = SHARED_ROOT / 'scripts' / 'automation_settings.json'
CLAUDE_TIMEOUT_SECONDS = 20 * 60


# --- small git helpers ---------------------------------------------------------------------
def _git(args, cwd=SHARED_ROOT, check=True):
    return subprocess.run(['git', '-C', str(cwd)] + args,
                           capture_output=True, text=True, check=check)


def _changed_paths():
    """Both modified-tracked and new-untracked files inside toolkit\\."""
    proc = _git(['status', '--porcelain'])
    paths = []
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        # porcelain format: XY <path>  (renames: XY old -> new - take the new path)
        p = line[3:].strip()
        if ' -> ' in p:
            p = p.split(' -> ', 1)[1]
        paths.append(p.replace('\\', '/'))
    return paths


def _discard_working_tree_changes():
    # Discards uncommitted working-tree changes in toolkit\.
    _git(['checkout', '--', '.'], check=False)
    _git(['clean', '-fd'], check=False)


def _project_status_dirty():
    """The outer (private) repo's own working-tree status."""
    return bool(_git(['status', '--porcelain'], cwd=PROJECT_ROOT).stdout.strip())


# --- headless Claude Code invocation --------------------------------------------------------------
def build_prompt(ticket):
    return f"""You are processing a single tower_crane change-request ticket as part of an
UNATTENDED automation run. Follow these steps exactly - there is no human watching this session.

Ticket file: {ticket.path}

1. Read the ticket file. It has Symptom/repro, Root cause, and Proposed fix sections. The
   Proposed fix is a SUGGESTION, not a mandate - decide the best actual fix yourself.
2. Read every file under consumers\\*.md (the registry - source of truth for who's opted into
   what) and reason about how your fix affects each one, not just the ticket's filer.
3. Apply the smallest correct fix to the shared tool file(s) it concerns, under hooks\\, scripts\\,
   templates\\, or agents\\ as appropriate. Do not refactor unrelated code.
4. You have Read/Edit/Write/Glob/Grep tools only - no Bash, no git, no gh. Do not attempt to run
   any command; you cannot and should not.
5. Do NOT touch anything under change_requests\\ or project_progress.md. A separate deterministic
   step - not you - handles this ticket's round-trip log line and any progress notes after this
   session ends.
6. End your final response with exactly one line formatted as:
   AFFECTS: <comma-separated affected consumer names, or "none apparent" if the fix is generic>
"""


def invoke_claude(prompt):
    try:
        proc = subprocess.run(
            ['claude', '-p', prompt, '--permission-mode', 'dontAsk',
             '--settings', str(AUTOMATION_SETTINGS), '--output-format', 'json'],
            cwd=str(SHARED_ROOT), capture_output=True, text=True,
            timeout=CLAUDE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        print("  [ERROR] claude -p timed out.")
        return None
    if proc.returncode != 0:
        print(f"  [ERROR] claude -p exited {proc.returncode}: {proc.stderr.strip()[:500]}")
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        print("  [ERROR] claude -p --output-format json did not return valid JSON.")
        return None


def _extract_affects(result):
    text = str((result or {}).get('result', '') or '')
    m = re.search(r'^AFFECTS:\s*(.+)$', text, re.MULTILINE)
    return m.group(1).strip() if m else 'unspecified'


def process_one_ticket(ticket, cfg, state):
    print(f"Processing candidate ticket: {ticket.slug} (category: {ticket.category})")

    if _project_status_dirty():
        print("  [SKIP] outer repo already has uncommitted changes - something else is mid-edit "
              "there; not attributing this tick's work to it.")
        return

    result = invoke_claude(build_prompt(ticket))
    if result is None:
        ticket_scan.record_attempt(state, ticket.slug, 'agent_error')
        return

    if _project_status_dirty():
        print("  [ABORT] agent wrote into the outer repo - discarding toolkit\\'s changes only; "
              "the outer repo's working tree needs manual inspection, left untouched.")
        _discard_working_tree_changes()
        ticket_scan.record_attempt(state, ticket.slug, 'protected_path_touched')
        return

    changed = _changed_paths()
    if not changed:
        print("  [SKIP] agent made no changes.")
        ticket_scan.record_attempt(state, ticket.slug, 'agent_error')
        return

    check = subprocess.run([cfg['python_launcher'], str(CHECK_SCRIPT)], capture_output=True, text=True)
    if check.returncode != 0:
        print("  [FAIL] check_tower_crane.py failed on the proposed fix - discarding.")
        _discard_working_tree_changes()
        ticket_scan.record_attempt(state, ticket.slug, 'check_failed')
        return

    # Local commit only, in toolkit\ - never pushes.
    try:
        _git(['add'] + changed)
        _git(['commit', '-m', f"Automated fix: {ticket.slug}"])
    except subprocess.CalledProcessError as e:
        print(f"  [ERROR] toolkit\\ commit failed: {e.stderr}")
        _discard_working_tree_changes()
        ticket_scan.record_attempt(state, ticket.slug, 'commit_failed')
        return

    sha = _git(['rev-parse', 'HEAD']).stdout.strip()[:9]
    affects = _extract_affects(result)
    today = date.today().isoformat()
    ticket_scan.append_log_line(
        ticket.path,
        f"- {today} — automation: fix applied (commit {sha} in toolkit\\), affects: {affects}; "
        f"awaiting {affects} verify.",
    )
    _git(['add', str(ticket.path.relative_to(PROJECT_ROOT))], cwd=PROJECT_ROOT)
    _git(['commit', '-m', f"Ticket bookkeeping: {ticket.slug} fix applied"], cwd=PROJECT_ROOT)
    _git(['push', 'origin', 'main'], cwd=PROJECT_ROOT)

    ticket_scan.clear_attempts(state, ticket.slug)
    print(f"  [OK] fix applied (toolkit\\ commit {sha}) for {ticket.slug}.")


def main():
    parser = argparse.ArgumentParser(description="Hourly unattended ticket-processing tick.")
    parser.add_argument('--dry-run', action='store_true',
                         help="Run the mechanical scan/bookkeeping only; never invoke claude or apply a fix.")
    args = parser.parse_args()

    cfg = get_shared_config(SHARED_ROOT)
    automation = cfg.get('automation') or {}
    if not automation.get('enabled', False):
        print("automation.enabled is false in config.local.json - nothing to do.")
        return

    mode = automation.get('mode', 'apply_direct')
    if mode != 'apply_direct':
        print(f"Unsupported automation.mode '{mode}' - skipping.")
        return

    max_tickets = int(automation.get('max_tickets_per_tick', 1))
    max_attempts = int(automation.get('max_attempts', 3))

    print("=== run_automation.py ===")

    # Outer repo: ordinary, unconditional pull.
    _git(['pull', '--ff-only'], cwd=PROJECT_ROOT)

    # toolkit\: never pulled/merged here. --notify is a plain, non-mutating surfacing check.
    notify = subprocess.run([cfg['python_launcher'], str(UPDATE_SCRIPT), '--notify'],
                            capture_output=True, text=True)
    print(notify.stdout.strip())

    subprocess.run([cfg['python_launcher'], str(CHECK_SCRIPT), '--write-guidance'])

    tickets = ticket_scan.scan()
    bookkeeping = ticket_scan.mark_done(tickets, dry_run=args.dry_run)
    print(f"Mechanical bookkeeping: done_flipped={bookkeeping['done_flipped']}")
    if bookkeeping['touched'] and not args.dry_run:
        rel = [str(p.relative_to(PROJECT_ROOT)) for p in bookkeeping['touched']]
        try:
            _git(['add'] + rel, cwd=PROJECT_ROOT)
            _git(['commit', '-m', f"automation: ticket bookkeeping ({len(rel)} file(s))"], cwd=PROJECT_ROOT)
            _git(['push', 'origin', 'main'], cwd=PROJECT_ROOT)
        except subprocess.CalledProcessError as e:
            print(f"  [ERROR] ticket bookkeeping commit/push failed: {e.stderr}")

    state = ticket_scan.load_state()
    candidates = ticket_scan.needs_fix_candidates(tickets, state, max_attempts)[:max_tickets]
    if not candidates:
        print("No fix-worthy candidate tickets this tick.")
    elif args.dry_run:
        print(f"[dry-run] would process: {[t.slug for t in candidates]}")
    else:
        for ticket in candidates:
            process_one_ticket(ticket, cfg, state)

    ticket_scan.save_state(state)


if __name__ == '__main__':
    main()
