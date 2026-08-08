#!/usr/bin/env python3
"""
check_shared_resource_refs.py - Group B2 of design\\resource_sharing_model.md: a project's own
"is what I adopted from shared_resources\\ still there" check, run at that project's `resume`
(see templates\\shared_resources.md's "Checking adopted references at resume").

Why a script and not a written resume-time instruction: the same "prefer a deterministic check
over LLM judgment" reasoning already governing consistency_check.py and check_tower_crane.py's
golden suite - an existence check has one right answer, so let something outside the model give
it, for free, instead of spending agent reasoning/tokens re-deriving it every resume.

What it checks, in two forms - both per templates\\shared_resources.md's "Apply" step:
1. Every `@import`-syntax line in the given project's CLAUDE.md whose target path contains a
   `shared_resources/` segment (the pre-directive_economy flat-import form).
2. Every backtick-quoted `~/...`-form path containing a `shared_resources/` segment inside any
   project-local `.claude\\skills\\<name>\\SKILL.md` file (the Track-1 skill-stub form "Apply" now
   produces - design\\directive_economy.md's "Apply procedure, resolved").
Both forms expand a leading `~` to the current user's home directory (the only such path form
proven to resolve - design\\portability.md decision 7), then check the target file actually
exists. Flags anything that doesn't resolve, so a folder-maintenance operation
(split/consolidate/rename/delete) that broke a stub never fails silently
(design\\resource_sharing_model.md's "Shared resources folder maintenance" principle).

Deliberately out of scope: free-text "pointer note" adoptions (a `tool`-kind entry invoked
on-demand, or any adoption written as prose mentioning a spaced path rather than a literal
`@import` line or a backtick-quoted `~/...` path in a skill stub). Those aren't machine-parseable
by construction - there's no fixed shape to check deterministically. Also out of scope: a skill
stub's trigger description going stale relative to its source entry's current topic footprint -
a different, notify-only concern (design\\directive_economy.md's "Drift mechanics"), not an
existence check.

Usage: python scripts\\check_shared_resource_refs.py [--project-root <path>]
Defaults --project-root to the current working directory (the normal case: run from inside the
consuming project during its own `resume`). Prints [OK]/[FAIL]/[N/A] lines; exit 0 if nothing is
broken (including "nothing adopted"), exit 1 if any adopted reference no longer resolves.
"""

import argparse
import re
import sys
from pathlib import Path

# '.' (not '\S') so an import_base path containing a space still matches - '.' excludes only
# newlines, and an @import line is always exactly one line, so this can't over-match into the
# next line. Same fix as check_tower_crane.py/scan_consumer_update.py's identical regex
# (2026-08-08) - found here the same day while auditing for other latent instances of the same
# whitespace-intolerant pattern.
IMPORT_LINE_RE = re.compile(r'^@(.+?)\s*$', re.MULTILINE)
SKILL_STUB_PATH_RE = re.compile(r'`(~/[^`]+)`')


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


def find_shared_resource_skill_refs(project_root):
    """Every project-local .claude\\skills\\<name>\\SKILL.md, scanned for a backtick-quoted
    '~/...' path containing a shared_resources/ segment (the Track-1 stub form). Returns a list
    of (skill_name, raw_path) pairs."""
    hits = []
    skills_dir = project_root / '.claude' / 'skills'
    if not skills_dir.is_dir():
        return hits
    for skill_md in sorted(skills_dir.glob('*/SKILL.md')):
        text = skill_md.read_text(encoding='utf-8')
        for m in SKILL_STUB_PATH_RE.finditer(text):
            raw = m.group(1)
            if 'shared_resources/' not in raw.replace('\\', '/'):
                continue
            hits.append((skill_md.parent.name, raw))
    return hits


def main():
    parser = argparse.ArgumentParser(
        description="Checks that this project's adopted shared_resources\\ @import references "
                     "still resolve to real files."
    )
    parser.add_argument('--project-root', default='.', help="Defaults to the current directory.")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    claude_md = project_root / 'CLAUDE.md'
    print("=== check_shared_resource_refs.py ===")

    imports = []
    if claude_md.exists():
        imports = find_shared_resource_imports(claude_md.read_text(encoding='utf-8'))
    skill_refs = find_shared_resource_skill_refs(project_root)

    if not imports and not skill_refs:
        print("[N/A] no shared_resources\\ @import lines in CLAUDE.md and no shared_resources\\ "
              "references in any .claude\\skills\\ stub - nothing adopted, nothing to check.")
        sys.exit(0)

    broken = 0
    checked = 0
    for raw in imports:
        checked += 1
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

    for skill_name, raw in skill_refs:
        checked += 1
        resolved = resolve_import_path(raw)
        if resolved is None:
            print(f"[N/A] skill stub '{skill_name}' references '{raw}', not in the "
                  "home-relative '~/...' form - skipping (out of scope, not a failure).")
            continue
        if resolved.exists():
            print(f"[OK] skill stub '{skill_name}' reference '{raw}' resolves.")
        else:
            broken += 1
            print(f"[FAIL] skill stub '{skill_name}' reference '{raw}' does NOT resolve "
                  f"(expected file at {resolved}) - this adopted reference is broken, likely a "
                  "shared_resources\\ entry that was renamed/deleted/split without a stub left "
                  "behind. Worth a note back to a hub session to fix the source, or 'forget' "
                  "this adoption if it's no longer needed.")

    print()
    if broken:
        print(f"=== {broken} broken shared_resources\\ reference(s) - see [FAIL] lines above ===")
        sys.exit(1)
    print(f"=== all {checked} adopted shared_resources\\ reference(s) resolve ===")
    sys.exit(0)


if __name__ == '__main__':
    main()
