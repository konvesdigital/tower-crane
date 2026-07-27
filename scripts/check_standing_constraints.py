#!/usr/bin/env python3
"""
check_standing_constraints.py - the mechanical half of Fix 3 Checkpoint 1's authoring assistant
(design\\update_trust_review.md's "propose upstream" Phase 2 build): a deterministic exact-match
check for whether a proposed change touches AGENTS.md's "## Standing Constraints" section.

Why this needs to be a script rather than an agent judgment call: the whole point of the
refuse-and-ask gate is to fire reliably on ANY edit to that section, including a subtle
paraphrase that quietly weakens a MUST/MUST NOT clause - the same fuzzy-match-detection discipline
this project already applies to code (hooks\\consistency_check.py), aimed at prose instead. An
exact-text compare is the only thing that can't be argued past.

This is advisory, not a hard block (Locked 2026-07-26 - "overridable warning") - it always exits 0
and leaves the decision to the human via the calling procedure (AGENTS.md's "propose upstream").
Output is a small set of stable text markers the calling agent reads, same protocol as
update_toolkit.py's [PASS]/[BLOCKED]/=== BEGIN DIFF ===:

  [UNCHANGED]  Standing Constraints section is byte-identical to the base ref's version.
  [CHANGED]    it differs - printed alongside the literal before/after text.

A second caller, `checkpoint`'s new soft disclosure guardrail (design\\update_trust_review.md's
"Refinement 2026-07-27"), reuses this same exact-text detector before committing a `toolkit\\`
change - but compared against the previous *pushed* state, not a merge-base with `main` (checkpoint
commits straight to `main`, no PR branch). Pass `--head worktree` for this mode: `--base` is then
read literally (no merge-base computation) and the "after" text comes from the file currently on
disk, uncommitted changes included, instead of a committed ref.

Usage:
  python scripts\\check_standing_constraints.py [--base main] [--file AGENTS.md]
  python scripts\\check_standing_constraints.py --base HEAD --head worktree   (checkpoint's pre-commit form)
Run from anywhere; always resolves paths against this toolkit\\ repo, not the caller's cwd.
"""

import argparse
import subprocess
import sys
from pathlib import Path

SHARED_ROOT = Path(__file__).resolve().parent.parent
SECTION_HEADING = '## Standing Constraints'


def _git(args, check=True):
    return subprocess.run(['git', '-C', str(SHARED_ROOT)] + args,
                           capture_output=True, text=True, check=check)


def extract_section(text):
    """Returns the literal text from SECTION_HEADING (inclusive) up to the next line starting
    with '## ' (exclusive), or to EOF if there is no next '## ' heading. None if the heading isn't
    present at all."""
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.strip().startswith(SECTION_HEADING):
            start = i
            break
    if start is None:
        return None

    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith('## '):
            end = i
            break
    return '\n'.join(lines[start:end])


def read_file_at(ref, rel_path):
    proc = _git(['show', f'{ref}:{rel_path}'], check=False)
    if proc.returncode != 0:
        return None
    return proc.stdout


def read_worktree_file(rel_path):
    # Deliberately no explicit encoding: must decode with the same platform-default codec
    # subprocess(text=True) uses for git show's output below, or byte-identical files compare
    # unequal on a non-UTF8-default console (verified live on Windows/cp1252 - forcing utf-8 here
    # while git show implicitly uses cp1252 turned em-dashes into false [CHANGED] positives).
    path = SHARED_ROOT / rel_path
    if not path.exists():
        return None
    return path.read_text()


def main():
    parser = argparse.ArgumentParser(
        description="Exact-match check: does a proposed change touch AGENTS.md's Standing "
                     "Constraints section? (Fix 3 Checkpoint 1's mechanical gate.)"
    )
    parser.add_argument('--base', default='main',
                         help="Ref to compare against (default: main). With --head worktree, this "
                              "ref is read literally - no merge-base computation.")
    parser.add_argument('--head', default='HEAD',
                         help="Ref to read the 'after' text from (default: HEAD), or the literal "
                              "string 'worktree' to read the current on-disk file instead - used by "
                              "checkpoint's pre-commit disclosure guardrail to see uncommitted "
                              "changes.")
    parser.add_argument('--file', default='AGENTS.md',
                         help="Path, relative to toolkit\\, of the file to check (default: AGENTS.md).")
    args = parser.parse_args()

    if args.head == 'worktree':
        base_sha = args.base
        head_text = read_worktree_file(args.file)
        head_label = 'working tree'
    else:
        merge_base = _git(['merge-base', 'HEAD', args.base], check=False)
        if merge_base.returncode != 0:
            print(f"[ERROR] couldn't find a merge-base between HEAD and '{args.base}' - is "
                  f"'{args.base}' a valid ref in this clone?")
            sys.exit(1)
        base_sha = merge_base.stdout.strip()
        head_text = read_file_at(args.head, args.file)
        head_label = args.head

    if head_text is None:
        print(f"[ERROR] '{args.file}' not found at {head_label}.")
        sys.exit(1)

    base_text = read_file_at(base_sha, args.file)
    if base_text is None:
        print(f"[UNCHANGED] '{args.file}' doesn't exist at the base ref ({base_sha[:8]}) - nothing "
              "to compare; treating as no prior Standing Constraints to have changed.")
        sys.exit(0)

    base_section = extract_section(base_text)
    head_section = extract_section(head_text)

    if base_section == head_section:
        print(f"[UNCHANGED] '{SECTION_HEADING}' in {args.file} is identical to {args.base} "
              f"({base_sha[:8]}). No standing-constraint edit detected.")
        sys.exit(0)

    print(f"[CHANGED] '{SECTION_HEADING}' in {args.file} differs from {args.base} ({base_sha[:8]}).")
    print()
    print(f"=== BEFORE ({args.base}) ===")
    print(base_section if base_section is not None else "(section absent)")
    print(f"=== AFTER ({head_label}) ===")
    print(head_section if head_section is not None else "(section absent)")
    print("=== END ===")
    print()
    print("This is an overridable warning, not a hard block (Locked 2026-07-26) - surface it to the "
          "user plainly. If called from 'propose upstream': get explicit confirmation this edit is "
          "deliberate before continuing. If called from checkpoint's pre-commit disclosure guardrail: "
          "this is a notice only, nothing to confirm - the push cannot be blocked, only disclosed.")
    sys.exit(0)


if __name__ == '__main__':
    main()
