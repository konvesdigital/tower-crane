#!/usr/bin/env python3
"""
check_shared_resource_drift.py - notify-only, resume-time check for whether a Track-1
shared_resources\\ skill stub's trigger description has gone stale relative to its source entry's
current content.

Distinct from check_shared_resource_refs.py: that script checks whether the adopted reference
still exists ([FAIL], exit 1, blocking). This script checks whether the source content has
changed since the stub's trigger was drafted, which is non-blocking ([DRIFT], exit 0).

Mechanism: "Apply" (templates\\shared_resources.md's reference/tool step) stamps the stub's
adoption-marker comment with a sha256 of the source entry file's content at adoption time:
`<!-- shared_resources: <entry> adopted YYYY-MM-DD index-sha256:<hash> -->`. This script
recomputes that hash from the live source file and compares. A full-file hash can flag a purely
cosmetic edit as drift too; it never under-fires.

A stub with no index-sha256 in its marker (an insight-kind adoption, a pre-existing stub, or a
`tool` entry adopted as free-text prose) is out of scope, not a failure.

Usage: python scripts\\check_shared_resource_drift.py [--project-root <path>]
Defaults --project-root to the current working directory. Prints [OK]/[DRIFT]/[N/A] lines.
Always exits 0. On [DRIFT], the acting agent should re-read the source entry, compare its current
topic footprint against the stub's existing trigger description, and - only if it's actually
grown a topic the trigger doesn't cover - redraft the trigger and confirm with the user before
overwriting the stub, then re-run this script so the marker's hash is refreshed.
"""

import argparse
import hashlib
import re
import sys
from pathlib import Path

MARKER_RE = re.compile(
    r'<!--\s*shared_resources:\s*(?P<entry>.+?)\s+adopted\s+\d{4}-\d{2}-\d{2}'
    r'(?:\s+index-sha256:(?P<hash>[0-9a-f]{64}))?'
    # Optional trailing marker fields this script doesn't use but must tolerate.
    r'(?:\s+hub-rel:\S+)?'
    r'(?:\s+hosts-ignored:\S+)?'
    r'\s*-->'
)
SKILL_STUB_PATH_RE = re.compile(r'`(~/[^`]+)`')


def resolve_path(raw):
    """Resolves a home-relative '~/...' path. Returns None if not in that form."""
    normalized = raw.replace('\\', '/')
    if not normalized.startswith('~/'):
        return None
    return (Path.home() / normalized[2:]).resolve()


def sha256_of(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_stub(skill_md):
    text = skill_md.read_text(encoding='utf-8')
    marker = MARKER_RE.search(text)
    if not marker or not marker.group('hash'):
        return ('N/A', skill_md.parent.name,
                "no index-sha256 in this stub's adoption marker - out of scope (insight-kind "
                "adoption, a pre-existing stub written before this check existed, or a free-text "
                "pointer adoption with no fixed shape).")

    path_match = SKILL_STUB_PATH_RE.search(text)
    if not path_match:
        return ('N/A', skill_md.parent.name,
                "marker carries an index-sha256 but no backtick-quoted '~/...' path was found in "
                "the stub body to hash against - can't verify.")

    resolved = resolve_path(path_match.group(1))
    if resolved is None or not resolved.exists():
        return ('N/A', skill_md.parent.name,
                "source path doesn't resolve - that's check_shared_resource_refs.py's concern, "
                "not this script's.")

    live_hash = sha256_of(resolved)
    if live_hash == marker.group('hash'):
        return ('OK', skill_md.parent.name, f"source content unchanged since '{marker.group('entry')}' was adopted.")

    return ('DRIFT', skill_md.parent.name,
            f"source content at {resolved} has changed since '{marker.group('entry')}' was "
            "adopted - this stub's trigger description was drafted from the old content and may "
            "no longer cover everything the source now talks about. Worth re-reading the source "
            "and asking the user whether the trigger needs redrafting; not an error on its own.")


def main():
    parser = argparse.ArgumentParser(
        description="Notify-only check: has a Track-1 shared_resources\\ skill stub's source "
                     "content changed since its trigger was drafted?"
    )
    parser.add_argument('--project-root', default='.', help="Defaults to the current directory.")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    skills_dir = project_root / '.claude' / 'skills'
    print("=== check_shared_resource_drift.py ===")

    if not skills_dir.is_dir():
        print("[N/A] no .claude\\skills\\ directory - nothing adopted, nothing to check.")
        sys.exit(0)

    stubs = sorted(skills_dir.glob('*/SKILL.md'))
    if not stubs:
        print("[N/A] no skill stubs found - nothing to check.")
        sys.exit(0)

    drift_count = 0
    for skill_md in stubs:
        verdict, name, message = check_stub(skill_md)
        print(f"[{verdict}] '{name}': {message}")
        if verdict == 'DRIFT':
            drift_count += 1

    print()
    if drift_count:
        print(f"=== {drift_count} stub(s) flagged for possible drift - see [DRIFT] lines above "
              "(notify only, not a failure) ===")
    else:
        print("=== no drift detected ===")
    sys.exit(0)


if __name__ == '__main__':
    main()
