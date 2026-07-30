#!/usr/bin/env python3
"""
check_shared_resource_refs.py - Group B2 of design\\resource_sharing_model.md: a project's own
"is what I adopted from shared_resources\\ still there" check, run at that project's `resume`
(see templates\\shared_resources.md's "Checking adopted references at resume").

Why a script and not a written resume-time instruction: the same "prefer a deterministic check
over LLM judgment" reasoning already governing consistency_check.py and check_tower_crane.py's
golden suite - an existence check has one right answer, so let something outside the model give
it, for free, instead of spending agent reasoning/tokens re-deriving it every resume.

What it checks: every `@import`-syntax line in the given project's CLAUDE.md whose target path
contains a `shared_resources/` segment - a reference/tool-kind adoption per
templates\\shared_resources.md's "Apply" step. Expands a leading `~` to the current user's home
directory (the only @import form Claude Code resolves - design\\portability.md decision 7), then
checks the target file actually exists. Flags anything that doesn't resolve, so a folder-
maintenance operation (split/consolidate/rename/delete) that broke a stub never fails silently
(design\\resource_sharing_model.md's "Shared resources folder maintenance" principle).

Deliberately out of scope: free-text "pointer note" adoptions (a `tool`-kind entry invoked
on-demand, or any adoption written as prose mentioning a spaced path rather than a literal
`@import` line). Those aren't machine-parseable by construction - templates\\shared_resources.md
itself only requires the strict `@import` syntax for content with "no spaced paths"; anything
else is free prose with no fixed shape to check deterministically.

Usage: python scripts\\check_shared_resource_refs.py [--project-root <path>]
Defaults --project-root to the current working directory (the normal case: run from inside the
consuming project during its own `resume`). Prints [OK]/[FAIL]/[N/A] lines; exit 0 if nothing is
broken (including "nothing adopted"), exit 1 if any adopted reference no longer resolves.
"""

import argparse
import re
import sys
from pathlib import Path

IMPORT_LINE_RE = re.compile(r'^@(\S+)\s*$', re.MULTILINE)


def resolve_import_path(raw):
    """Expand a Claude Code @import path (home-relative '~/...', the only form ever proven to
    resolve) to an absolute Path. Returns None if it isn't home-relative - out of scope, not an
    error, since every real shared_resources\\ import in this project always uses that form."""
    normalized = raw.replace('\\', '/')
    if not normalized.startswith('~/'):
        return None
    return (Path.home() / normalized[2:]).resolve()


def find_shared_resource_imports(claude_md_text):
    hits = []
    for m in IMPORT_LINE_RE.finditer(claude_md_text):
        raw = m.group(1)
        if 'shared_resources/' not in raw.replace('\\', '/'):
            continue
        hits.append(raw)
    return hits


def main():
    parser = argparse.ArgumentParser(
        description="Checks that this project's adopted shared_resources\\ @import references "
                     "still resolve to real files."
    )
    parser.add_argument('--project-root', default='.', help="Defaults to the current directory.")
    args = parser.parse_args()

    claude_md = Path(args.project_root).resolve() / 'CLAUDE.md'
    print("=== check_shared_resource_refs.py ===")

    if not claude_md.exists():
        print(f"[N/A] no CLAUDE.md found at {claude_md} - nothing to check.")
        sys.exit(0)

    text = claude_md.read_text(encoding='utf-8')
    imports = find_shared_resource_imports(text)

    if not imports:
        print("[N/A] this project's CLAUDE.md has no shared_resources\\ @import lines - "
              "nothing adopted, nothing to check.")
        sys.exit(0)

    broken = 0
    for raw in imports:
        resolved = resolve_import_path(raw)
        if resolved is None:
            print(f"[N/A] '@{raw}' isn't in the home-relative '~/...' form every real "
                  "shared_resources\\ import uses - skipping (out of scope, not a failure).")
            continue
        if resolved.exists():
            print(f"[OK] '@{raw}' resolves.")
        else:
            broken += 1
            print(f"[FAIL] '@{raw}' does NOT resolve (expected file at {resolved}) - this "
                  "adopted reference is broken, likely a shared_resources\\ entry that was "
                  "renamed/deleted/split without a stub left behind. Worth a note back to a hub "
                  "session to fix the source, or 'forget' this adoption if it's no longer needed.")

    print()
    if broken:
        print(f"=== {broken} broken shared_resources\\ reference(s) - see [FAIL] lines above ===")
        sys.exit(1)
    print(f"=== all {len(imports)} adopted shared_resources\\ reference(s) resolve ===")
    sys.exit(0)


if __name__ == '__main__':
    main()
