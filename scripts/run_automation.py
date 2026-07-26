#!/usr/bin/env python3
"""
run_automation.py - Piece 3 of sync automation (design\\sync_automation.md): the wrapper an
OS-level scheduled task (Task Scheduler / cron, see templates\\setup_automation.md) invokes
hourly to keep the hub clone current, carry Piece 2b's compliance-guidance write, and propose a
PR for at most one fix-worthy change_requests\\ ticket per tick.

No-op (exit 0) unless config.local.json's automation.enabled is true - the scheduled task can
exist unconditionally; the config flag is the real switch (same "available but off by default"
posture as scripts\\self_hooks.py).

HARD ARCHITECTURAL RULE - judgment vs. mechanics split (locked in design\\sync_automation.md's
Piece 3 planning): the headless `claude -p` invocation this script makes gets NO git/gh/Bash
access. It edits the target shared-tool file(s) and nothing else. Every git/gh call - branch,
commit, push, PR creation - and the check_tower_crane.py pass/fail gate live here, in
deterministic Python. This makes "never push an unvalidated fix" and "the agent can't merge/push/
branch on its own" true by construction, not by trusting a prompt instruction. A defensive diff
check (PROTECTED_PATHS) still runs before anything is staged, in case the agent tries anyway.

VERIFIED LIVE (2026-07-24, do not regress this): `scripts\\automation_settings.json` must list
Bash (and WebFetch/WebSearch/Agent/NotebookEdit) under `permissions.deny`, not merely omit them
from `permissions.allow`. Live-tested both ways against this exact settings file: an allow-only
list (no `deny`) let a `claude -p --permission-mode dontAsk` session run an arbitrary Bash command
anyway - `--permission-mode dontAsk`'s "auto-deny anything not in permissions.allow" behavior does
NOT hold for an allow-only list in practice. Only adding Bash to an explicit `permissions.deny`
actually removed the tool from the model's toolset entirely (confirmed: the agent reported having
no Bash tool available, not "denied when attempted" - `permission_denials` stayed empty because it
was never offered the tool to try). Re-verify this empirically again if `automation_settings.json`
or the `claude` CLI's permission handling ever changes.

Never merges its own PR. Never flips a ticket's Status directly (only ticket_scan.py's
mechanical, zero-judgment DONE-flip for an already-consumer-verified ticket does that).
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config_lib import get_shared_config
import ticket_scan

SHARED_ROOT = Path(__file__).resolve().parent.parent
CHECK_SCRIPT = SHARED_ROOT / 'scripts' / 'check_tower_crane.py'
AUTOMATION_SETTINGS = SHARED_ROOT / 'scripts' / 'automation_settings.json'
PROTECTED_PATHS = ('change_requests', 'project_progress.md')
CLAUDE_TIMEOUT_SECONDS = 20 * 60


def write_utf8(path, content):
    path.write_text(content, encoding='utf-8', newline='\n')


# --- small git/gh helpers (no shared helper exists anywhere in this repo's scripts\ - matches the
# existing ad hoc-per-script convention, e.g. publish_release.py) ---------------------------------
def _git(args, check=True):
    return subprocess.run(['git', '-C', str(SHARED_ROOT)] + args,
                           capture_output=True, text=True, check=check)


def _changed_paths():
    """Both modified-tracked and new-untracked files (git diff alone misses untracked new files
    an agent may have created, e.g. a brand-new hook)."""
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
    # Discards only THIS script's own agent-invocation working-tree changes (never committed yet),
    # not any pre-existing user work - main is always freshly pulled at the top of each tick.
    _git(['checkout', '--', '.'], check=False)
    _git(['clean', '-fd'], check=False)


def _parse_remote_owner(cfg):
    remote = str((cfg.get('identity') or {}).get('git_remote') or '')
    m = re.search(r'github\.com[:/]+([^/]+)/', remote)
    return m.group(1) if m else 'maintainer'


def _lookup_pr_number(branch):
    proc = subprocess.run(
        ['gh', 'pr', 'list', '--head', branch, '--json', 'number', '--limit', '1'],
        cwd=str(SHARED_ROOT), capture_output=True, text=True,
    )
    if proc.returncode != 0:
        return None
    try:
        rows = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    return rows[0]['number'] if rows else None


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


def build_pr_body(ticket, checker_output):
    truncated = checker_output if len(checker_output) < 4000 else checker_output[:4000] + '\n... (truncated)'
    return f"""**Agent-authored - not reviewed by a human.** Do not merge without review.

Proposed by Tower Crane's unattended sync-automation agent (Piece 3, `design\\sync_automation.md`)
for ticket `change_requests\\{ticket.path.name}`.

`scripts\\check_tower_crane.py` output at the time this PR was opened:

```
{truncated}
```
"""


def process_one_ticket(ticket, cfg, state):
    print(f"Processing candidate ticket: {ticket.slug} (category: {ticket.category})")
    result = invoke_claude(build_prompt(ticket))
    if result is None:
        ticket_scan.record_attempt(state, ticket.slug, 'agent_error')
        return

    changed = _changed_paths()
    protected_hit = [p for p in changed if p.startswith(PROTECTED_PATHS[0]) or p == PROTECTED_PATHS[1]]
    if protected_hit:
        print(f"  [ABORT] agent touched protected path(s) {protected_hit} - discarding.")
        _discard_working_tree_changes()
        ticket_scan.record_attempt(state, ticket.slug, 'protected_path_touched')
        return

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

    branch = f"auto/{ticket.slug}"
    try:
        _git(['checkout', '-b', branch])
        _git(['add'] + changed)
        _git(['commit', '-m', f"Automated fix: {ticket.slug}"])
        _git(['push', '-u', 'origin', branch])

        pr_body = build_pr_body(ticket, check.stdout)
        # mkstemp() returns an open fd as well as a path; that fd must be closed here or Windows
        # refuses to unlink() the file later (a handle still open in this same process blocks its
        # own delete) - same fix as publish_release.py's make_notes_file().
        fd, tmp_path = tempfile.mkstemp(suffix='.md')
        os.close(fd)
        fd_path = Path(tmp_path)
        write_utf8(fd_path, pr_body)
        try:
            subprocess.run(
                ['gh', 'pr', 'create', '--title', f"Automated fix: {ticket.slug}",
                 '--body-file', str(fd_path), '--head', branch, '--base', 'main'],
                cwd=str(SHARED_ROOT), check=True,
            )
        finally:
            fd_path.unlink(missing_ok=True)

        pr_number = _lookup_pr_number(branch)
        if pr_number is None:
            raise RuntimeError("gh pr create succeeded but the PR number could not be looked up")
    except Exception as e:
        print(f"  [ERROR] branch/PR creation failed: {e}")
        _git(['checkout', 'main'], check=False)
        _git(['branch', '-D', branch], check=False)
        ticket_scan.record_attempt(state, ticket.slug, 'push_or_pr_failed')
        return

    _git(['checkout', 'main'])
    _git(['pull', '--ff-only'])

    affects = _extract_affects(result)
    remote_owner = _parse_remote_owner(cfg)
    today = date.today().isoformat()
    ticket_scan.append_log_line(
        ticket.path,
        f"- {today} — automation: fix proposed (branch {branch}), PR #{pr_number} opened, "
        f"affects: {affects}; awaiting {remote_owner} review.",
    )
    _git(['add', str(ticket.path.relative_to(SHARED_ROOT))])
    _git(['commit', '-m', f"Ticket bookkeeping: {ticket.slug} PR #{pr_number} opened"])
    _git(['push', 'origin', 'main'])

    ticket_scan.clear_attempts(state, ticket.slug)
    print(f"  [OK] PR #{pr_number} opened for {ticket.slug}.")


def main():
    parser = argparse.ArgumentParser(description="Piece 3: hourly unattended ticket-processing tick.")
    parser.add_argument('--dry-run', action='store_true',
                         help="Run the mechanical scan/bookkeeping only; never invoke claude or open a PR.")
    args = parser.parse_args()

    cfg = get_shared_config(SHARED_ROOT)
    automation = cfg.get('automation') or {}
    if not automation.get('enabled', False):
        print("automation.enabled is false in config.local.json - nothing to do.")
        return

    mode = automation.get('mode', 'propose_only')
    if mode != 'propose_only':
        print(f"Unsupported automation.mode '{mode}' (only 'propose_only' exists in v1) - skipping.")
        return

    max_tickets = int(automation.get('max_tickets_per_tick', 1))
    max_attempts = int(automation.get('max_attempts', 3))

    print("=== run_automation.py ===")
    _git(['checkout', 'main'])
    _git(['pull', '--ff-only'])

    # Piece 2b cadence-carry: unconditional, zero AI cost.
    subprocess.run([cfg['python_launcher'], str(CHECK_SCRIPT), '--write-guidance'])

    tickets = ticket_scan.scan()
    bookkeeping = ticket_scan.apply_mechanical_actions(tickets, dry_run=args.dry_run)
    print(f"Mechanical bookkeeping: {bookkeeping}")

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
