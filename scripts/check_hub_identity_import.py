#!/usr/bin/env python3
"""
check_hub_identity_import.py - resume-time check: the hub's own outer CLAUDE.md must import
templates\\identity.md (the file every Tower Crane agent reads). Notify-only, never mutates.

Prints one `[NO-IDENTITY-IMPORT]` line when the outer CLAUDE.md exists but has no line
`@toolkit/templates/identity.md` (a line of that form, with or without a leading path prefix before
`templates/identity.md`). Silent when the line is present, and silent when there is no outer
CLAUDE.md at all (the outer repo is an operator snapshot; absent or changed files are tolerated).
The fix is a hand edit: add the line directly below the `@toolkit/AGENTS.md` line.
"""

import re
from pathlib import Path

SHARED_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = SHARED_ROOT.parent
IMPORT_LINE = '@toolkit/templates/identity.md'


def main():
    claude_md = PROJECT_ROOT / 'CLAUDE.md'
    if not claude_md.is_file():
        return
    text = claude_md.read_text(encoding='utf-8', errors='replace')
    if re.search(r'(?m)^@\S*templates/identity\.md\s*$', text):
        return
    print(f"[NO-IDENTITY-IMPORT] {claude_md} has no identity import line - add '{IMPORT_LINE}' "
          f"below the '@toolkit/AGENTS.md' line.")


if __name__ == '__main__':
    main()
