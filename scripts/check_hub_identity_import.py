#!/usr/bin/env python3
"""
check_hub_identity_import.py - resume-time check of the hub's own outer CLAUDE.md imports. Notify-only,
never mutates.

Prints one `[NO-IDENTITY-IMPORT]` line when the outer CLAUDE.md exists but has no line
`@toolkit/templates/identity.md`, and one `[NO-HUB-CAPABILITIES-IMPORT]` line when it has no line
`@toolkit/templates/hub_capabilities.md` (each line of that form, with or without a leading path prefix
before `templates/<file>`). The fix is a hand edit: add the line directly below the
`@toolkit/AGENTS.md` line.

Prints one `[HUB-CAPABILITIES-STALE]` line when templates\\hub_capabilities.md is missing or differs from
what render_hub_capabilities.py builds from the catalog.

Silent when everything is current, and silent about the imports when there is no outer CLAUDE.md at all
(the outer repo is an operator snapshot; absent or changed files are tolerated).
"""

import re
from pathlib import Path

import render_hub_capabilities

SHARED_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = SHARED_ROOT.parent
IMPORTS = [
    ('NO-IDENTITY-IMPORT', 'identity.md'),
    ('NO-HUB-CAPABILITIES-IMPORT', 'hub_capabilities.md'),
]


def main():
    claude_md = PROJECT_ROOT / 'CLAUDE.md'
    if claude_md.is_file():
        text = claude_md.read_text(encoding='utf-8', errors='replace')
        for tag, name in IMPORTS:
            if not re.search(rf'(?m)^@\S*templates/{re.escape(name)}\s*$', text):
                print(f"[{tag}] {claude_md} has no {name} import line - add "
                      f"'@toolkit/templates/{name}' below the '@toolkit/AGENTS.md' line.")
    render_hub_capabilities.report_stale()


if __name__ == '__main__':
    main()
