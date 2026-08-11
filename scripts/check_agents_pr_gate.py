#!/usr/bin/env python3
"""
check_agents_pr_gate.py - Fix 3 Checkpoint 2's mechanical half (design\\update_trust_review.md,
"Phase 3 - Checkpoint 2: merge-time CODEOWNERS + branch protection + mechanical checks"). Runs as
a GitHub Actions status check on any PR touching `AGENTS.md`, alongside CODEOWNERS-required human
review - this script is the deterministic teeth that give Checkpoint 2 real substance beyond "a
human eyeballed it," mirroring check_tower_crane.py's PASS/WARN/FAIL discipline aimed at code.

No-ops (prints "not applicable", exits 0) if the diff between --base-sha and --head-sha doesn't
touch AGENTS.md or one of its structural companion files at all - this gate only ever fires on the
files it's scoped to.

AGENTS.md's own 2026-08-11 split (design\\update_trust_review.md's "Fix 3 single-file vs.
split-into-pieces" row) moved most of its procedure content into four companion files
(COMPANION_FILES below) that AGENTS.md points to by plain filename, not @import - AGENTS.md itself
stays the one file carrying frontmatter and the Standing Constraints section. Checks 1-3 are about
that specific structure and stay scoped to AGENTS_FILE only; checks 4-6 are content-agnostic
(a keyword scan, a line-count diff, a PR-body string check) and run against every file in
ALL_GATED_FILES, so a PR touching only a companion still gets the same mechanical scrutiny a PR
touching AGENTS.md itself always got.

Six checks, split hard-fail (exit 1, blocks the status check) vs soft-flag (WARN, never fails the
build - same convention as check_tower_crane.py) per the Decisions table in
design\\update_trust_review.md:
  1. Filename invariant           HARD  - AGENTS.md must still exist, at that path, at head.
                                           AGENTS_FILE only.
  2. Frontmatter schema           HARD  - the 4 required keys, correct shape, all present.
                                           AGENTS_FILE only - the companions carry no frontmatter.
  3. Standing Constraints match   HARD  - reuses check_standing_constraints.py's exact-text compare;
                                           unconditional, no exceptions (Locked 2026-07-27 - corrects
                                           a build drift: the doc's original design always specified
                                           hard-fail here, the 2026-07-27 build had incorrectly given
                                           it Checkpoint 1's overridable-warning treatment instead).
                                           No exception logic exists anywhere in this check - it
                                           can't distinguish a weakening edit from a legitimate
                                           tightening, so a blanket fail is the only version of "hard"
                                           that means anything. The amendment path is external to this
                                           script entirely: GitHub's own admin-override-merge action.
                                           AGENTS_FILE only - no companion carries this section.
  4. Capability-vs-content        SOFT  - heuristic keyword scan; a heuristic can't safely hard-fail.
                                           Runs against every touched file in ALL_GATED_FILES.
  5. Diff-size gate               SOFT  - Locked threshold (2026-07-26): >60 changed lines of a
                                           gated file. AGENTS_FILE additionally flags growing past
                                           its own declared max_lines; the companions carry no such
                                           declared cap, so only the flat line-count threshold
                                           applies to them.
  6. Required PR trailer          HARD  - PR body must carry both authoring-assistant headings
                                           ("### Contributor statement" / "### Independent read")
                                           whenever any file in ALL_GATED_FILES is touched. This is
                                           the one check that actually enforces Checkpoint 1 having
                                           been followed (or its output manually reproduced) -
                                           everything else here is advisory, so without this check
                                           Checkpoint 2 would have no real teeth of its own beyond
                                           CODEOWNERS review.

Reads the PR body from an environment variable (name given by --pr-body-env) rather than a CLI
argument - PR titles/bodies are attacker-controlled text, and interpolating them directly into a
shell command (including via GitHub Actions' `${{ github.event.pull_request.body }}` inside a
`run:` block) is a known script-injection vector. The calling workflow must pass it via `env:`
instead; see .github/workflows/agents_md_gate.yml.

Usage: python scripts\\check_agents_pr_gate.py --base-sha <sha> --head-sha <sha> [--pr-body-env PR_BODY]
Run from anywhere; always resolves paths against this toolkit\\ repo, not the caller's cwd.
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_standing_constraints import extract_section  # noqa: E402  (path insert above)

SHARED_ROOT = Path(__file__).resolve().parent.parent
TARGET_FILE = 'AGENTS.md'  # AGENTS_FILE alias below - kept for checks 1-3, which are AGENTS.md-only
AGENTS_FILE = TARGET_FILE
COMPANION_FILES = [
    'agents_tools.md', 'agents_consumers.md', 'agents_change_requests.md', 'agents_continuity.md',
]
ALL_GATED_FILES = [AGENTS_FILE] + COMPANION_FILES
DIFF_SIZE_THRESHOLD = 60
REQUIRED_TRAILERS = ['### Contributor statement', '### Independent read']

COUNTS = {'PASS': 0, 'WARN': 0, 'FAIL': 0}


def report(level, message):
    COUNTS[level] += 1
    print(f"[{level}] {message}")


def git(args):
    return subprocess.run(['git', '-C', str(SHARED_ROOT)] + args, capture_output=True, text=True)


def show(ref, path):
    proc = git(['show', f'{ref}:{path}'])
    return proc.stdout if proc.returncode == 0 else None


def touched_gated_files(base_sha, head_sha):
    proc = git(['diff', '--name-only', f'{base_sha}..{head_sha}', '--'] + ALL_GATED_FILES)
    touched = set(proc.stdout.splitlines())
    return [f for f in ALL_GATED_FILES if f in touched]


# --- check 1: filename invariant -----------------------------------------------------------------
def check_filename_invariant(head_text):
    if head_text is None:
        report('FAIL', f"'{TARGET_FILE}' not found at head - renamed or deleted. The canonical "
                        "AI-directive filename must not move without a design decision (see "
                        "design\\update_trust_review.md's Fix 3 filename lock).")
        return False
    report('PASS', f"'{TARGET_FILE}' exists at head, at its canonical path.")
    return True


# --- check 2: frontmatter schema -----------------------------------------------------------------
def parse_frontmatter(text):
    lines = text.splitlines()
    if not lines or lines[0].strip() != '---':
        return None
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == '---':
            end = i
            break
    if end is None:
        return None
    return lines[1:end]


def check_frontmatter_schema(head_text):
    fm = parse_frontmatter(head_text)
    if fm is None:
        report('FAIL', f"'{TARGET_FILE}' has no parseable '---' frontmatter block at head.")
        return None

    keys_present = {'scope': False, 'capabilities': False, 'max_lines': False,
                     'human_review_required': False}
    max_lines_value = None
    human_review_value = None
    capabilities_items = 0

    cur_key = None
    for line in fm:
        m = re.match(r'^(\w+):\s*(.*)$', line)
        if m and not line.startswith(' '):
            cur_key = m.group(1)
            rest = m.group(2).strip()
            if cur_key in keys_present:
                keys_present[cur_key] = True
            if cur_key == 'max_lines' and rest:
                max_lines_value = rest
            if cur_key == 'human_review_required' and rest:
                human_review_value = rest
            continue
        if cur_key == 'capabilities' and line.strip().startswith('- '):
            capabilities_items += 1

    missing = [k for k, present in keys_present.items() if not present]
    if missing:
        report('FAIL', f"'{TARGET_FILE}' frontmatter is missing required key(s): {', '.join(missing)}.")
        return None

    problems = []
    if capabilities_items < 1:
        problems.append("'capabilities:' has no list items")
    if max_lines_value is None or not max_lines_value.isdigit():
        problems.append(f"'max_lines:' is not a plain integer (got {max_lines_value!r})")
    if human_review_value != 'true':
        problems.append(f"'human_review_required:' must be exactly 'true' (got {human_review_value!r})")

    if problems:
        report('FAIL', f"'{TARGET_FILE}' frontmatter schema violation(s): {'; '.join(problems)}.")
        return None

    report('PASS', "frontmatter schema: all 4 required keys present and well-formed.")
    return int(max_lines_value)


# --- check 3: standing constraints exact-match (hard) ---------------------------------------------
def check_standing_constraints(base_text, head_text):
    base_section = extract_section(base_text) if base_text is not None else None
    head_section = extract_section(head_text)
    if base_section == head_section:
        report('PASS', "Standing Constraints section unchanged from base.")
        return
    report('FAIL', "Standing Constraints section DIFFERS from base - unconditional hard-fail "
                   "(Locked 2026-07-27), no exceptions. The only legitimate way for this PR to merge "
                   "is the repo owner's own admin-override-merge on GitHub - a distinct, logged "
                   "action, never something this script grants:")
    print("  --- BEFORE (base) ---")
    print(f"  {base_section!r}" if base_section is not None else "  (section absent)")
    print("  --- AFTER (head) ---")
    print(f"  {head_section!r}" if head_section is not None else "  (section absent)")


# --- check 4: capability-vs-content (soft, heuristic) --------------------------------------------
SUSPECT_TOKENS = [
    'http://', 'https://', 'curl ', 'wget ', 'requests.', 'urllib', 'fetch(', 'socket.',
    'ftp://', 'ssh ', 'password', 'api key', 'secret', 'credential', 'token=',
]


def check_capability_vs_content(base_sha, head_sha, touched_files):
    hits = []
    for path in touched_files:
        proc = git(['diff', f'{base_sha}..{head_sha}', '--', path])
        added_lines = [l[1:] for l in proc.stdout.splitlines()
                       if l.startswith('+') and not l.startswith('+++')]
        for line in added_lines:
            lower = line.lower()
            for token in SUSPECT_TOKENS:
                if token in lower:
                    hits.append((path, token, line.strip()))
    if not hits:
        report('PASS', "no added text suggests an undeclared capability.")
        return
    report('WARN', "added text mentions capability-like token(s) not obviously covered by the "
                   "declared 'capabilities:' list - reviewer should confirm the frontmatter still "
                   "matches what the new prose actually does:")
    for path, token, line in hits[:10]:
        print(f"  {path}: matched {token!r}: {line}")


# --- check 5: diff-size gate (soft) ---------------------------------------------------------------
def check_diff_size(base_sha, head_sha, touched_files, max_lines):
    flagged = False
    for path in touched_files:
        proc = git(['diff', '--numstat', f'{base_sha}..{head_sha}', '--', path])
        added = deleted = 0
        for line in proc.stdout.splitlines():
            parts = line.split('\t')
            if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
                added += int(parts[0])
                deleted += int(parts[1])
        changed = added + deleted

        path_flagged = False
        if changed > DIFF_SIZE_THRESHOLD:
            report('WARN', f"diff touches {changed} line(s) of {path} (+{added}/-{deleted}), "
                           f"over the {DIFF_SIZE_THRESHOLD}-line soft-flag threshold.")
            flagged = path_flagged = True
        if path == AGENTS_FILE and max_lines is not None:
            head_text = show(head_sha, path) or ''
            head_line_count = len(head_text.splitlines())
            if head_line_count > max_lines:
                report('WARN', f"{path} is {head_line_count} line(s) at head, past its own declared "
                               f"max_lines ({max_lines}).")
                flagged = path_flagged = True
        if not path_flagged:
            report('PASS', f"{path}: diff size ({changed} line(s)) within bounds.")
    return flagged


# --- check 6: required PR trailer (hard) -----------------------------------------------------------
def check_pr_trailer(pr_body, touched_files):
    missing = [t for t in REQUIRED_TRAILERS if t not in (pr_body or '')]
    if missing:
        report('FAIL', f"PR body is missing required heading(s): {', '.join(missing)}. Any PR "
                       f"touching {', '.join(touched_files)} must carry both the contributor's own "
                       "statement and Claude's independent read (AGENTS.md's \"propose upstream\" "
                       "step 2a-c) - this is the one check that actually enforces Checkpoint 1 was "
                       "followed.")
        return
    report('PASS', "PR body carries both required authoring-assistant headings.")


def main():
    parser = argparse.ArgumentParser(
        description="Fix 3 Checkpoint 2's mechanical merge-time gate for AGENTS.md PRs."
    )
    parser.add_argument('--base-sha', required=True, help="Base ref/SHA of the PR (e.g. main).")
    parser.add_argument('--head-sha', default='HEAD', help="Head ref/SHA of the PR (default: HEAD).")
    parser.add_argument('--pr-body-env', default='PR_BODY',
                         help="Name of the environment variable holding the PR body (default: PR_BODY). "
                              "Never pass PR body text as a CLI argument - see module docstring.")
    args = parser.parse_args()

    print("=== check_agents_pr_gate.py ===")
    print(f"comparing {args.base_sha}..{args.head_sha}")

    touched = touched_gated_files(args.base_sha, args.head_sha)
    if not touched:
        print(f"[N/A] this diff doesn't touch any of {', '.join(ALL_GATED_FILES)} - gate not "
              "applicable, nothing to check.")
        sys.exit(0)
    print(f"gated file(s) touched: {', '.join(touched)}")

    max_lines = None
    if AGENTS_FILE in touched:
        base_text = show(args.base_sha, AGENTS_FILE)
        head_text = show(args.head_sha, AGENTS_FILE)

        if not check_filename_invariant(head_text):
            print()
            print(f"=== Summary: {COUNTS['PASS']} passed, {COUNTS['WARN']} warning(s), {COUNTS['FAIL']} failure(s) ===")
            sys.exit(1)

        max_lines = check_frontmatter_schema(head_text)
        check_standing_constraints(base_text, head_text)
    else:
        print(f"[N/A] {AGENTS_FILE} itself not touched - checks 1-3 (filename/frontmatter/Standing "
              "Constraints, AGENTS.md-only) skipped.")

    check_capability_vs_content(args.base_sha, args.head_sha, touched)
    check_diff_size(args.base_sha, args.head_sha, touched, max_lines)
    check_pr_trailer(os.environ.get(args.pr_body_env), touched)

    print()
    print(f"=== Summary: {COUNTS['PASS']} passed, {COUNTS['WARN']} warning(s), {COUNTS['FAIL']} failure(s) ===")
    sys.exit(1 if COUNTS['FAIL'] > 0 else 0)


if __name__ == '__main__':
    main()
