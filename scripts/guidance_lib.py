#!/usr/bin/env python3
"""
guidance_lib.py - shared read/write helpers for a consumer's COMPLIANCE_GUIDANCE.md, the
two-way compliance channel's down-direction courier file (design\\consumer_platform.md decision 11).

Two independent writers share one file, each owning a separate named section:
  - check_tower_crane.py  -> '## Checker deviations' (derived - computed by auditing a consumer)
  - broadcast_guidance.py -> '## Broadcast'           (authored - hand-written guidance prose)

Namespacing (design\\broadcast_guidance.md, "Collision fix", locked 2026-07-23): each writer
replaces only its own named section and preserves whatever the other section currently holds,
regardless of run order. The file is deleted entirely once both sections are empty, so "file
present = something pending" holds for either writer, not just one.

Import it:  from guidance_lib import read_sections, write_section, SECTION_BROADCAST, SECTION_CHECKER
"""

import re
from pathlib import Path

GUIDANCE_FILENAME = 'COMPLIANCE_GUIDANCE.md'

# Canonical section headers, in the order they're written to the file. Both writers must use
# these exact names - do not add a third without updating both writers + templates\compliance.md.
SECTION_BROADCAST = 'Broadcast'
SECTION_CHECKER = 'Checker deviations'
SECTION_ORDER = [SECTION_BROADCAST, SECTION_CHECKER]


def guidance_path(consumer_root):
    return Path(consumer_root) / GUIDANCE_FILENAME


def read_sections(consumer_root):
    """Return {section_name: body_text} for whichever named sections currently exist in this
    consumer's COMPLIANCE_GUIDANCE.md. A missing file, or a section with no content, is simply
    absent from the dict - never an empty-string entry - so callers can test presence with
    `section in read_sections(...)`.
    """
    path = guidance_path(consumer_root)
    if not path.exists():
        return {}
    raw = path.read_text(encoding='utf-8')
    # Split on '## <header>' lines; parts alternate [preamble, header, body, header, body, ...].
    # parts[0] (the title line before the first '##') is discarded - it's regenerated on write.
    parts = re.split(r'(?m)^##[ \t]+(.+?)[ \t]*$', raw)
    sections = {}
    for i in range(1, len(parts), 2):
        name = parts[i].strip()
        body = parts[i + 1].strip('\n')
        if name in SECTION_ORDER and body.strip():
            sections[name] = body
    return sections


def write_section(consumer_root, consumer_name, section_name, body_lines):
    """Replace `section_name`'s content with `body_lines` (a list of str; do not include the
    '## Header' line itself), preserving whatever the other named section currently holds.
    Pass body_lines=None or [] to clear/remove this writer's section.

    Deletes COMPLIANCE_GUIDANCE.md once no named section has content left, so "file present"
    keeps meaning "something pending" for either writer. Returns True if the file exists after
    the call (something still pending), False if it was removed / never created.
    """
    if section_name not in SECTION_ORDER:
        raise ValueError(f"Unknown guidance section '{section_name}' - must be one of {SECTION_ORDER}.")

    path = guidance_path(consumer_root)
    sections = read_sections(consumer_root)

    body = '\n'.join(body_lines).strip('\n') if body_lines else ''
    if body:
        sections[section_name] = body
    else:
        sections.pop(section_name, None)

    if not sections:
        if path.exists():
            path.unlink()
        return False

    lines = [f"# Compliance Guidance - {consumer_name}", '']
    for name in SECTION_ORDER:
        if name in sections:
            lines.append(f"## {name}")
            lines.append('')
            lines.append(sections[name])
            lines.append('')
    path.write_text('\n'.join(lines).rstrip('\n') + '\n', encoding='utf-8', newline='\n')
    return True
