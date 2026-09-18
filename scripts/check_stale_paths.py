#!/usr/bin/env python3
"""
check_stale_paths.py - resume-time nudge for a stale hand-written absolute path left in a
connected consumer's own tracked prose.

Scans each locally-connected consumer's own CLAUDE.md / project_progress.md for backtick-quoted
absolute Windows paths and flags any that don't resolve on THIS host's filesystem. Notify-only:
never mutates, never blocks.

Silencing a known match: write an inline `<!-- stale-path-ok -->` HTML comment right after the
closing backtick, on the same line - e.g. a line reading "Backups live at
`C:/Users/example/Documents/backup_folder` <!-- stale-path-ok: single-host -->" (the `: reason`
part is optional; forward or back slashes both match).
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config_lib import get_shared_config
from registry_lib import parse_registry, host_path

SHARED_ROOT = Path(__file__).resolve().parent.parent
# consumers\ lives one level above SHARED_ROOT (toolkit\).
PROJECT_ROOT = SHARED_ROOT.parent
CONSUMERS_DIR = PROJECT_ROOT / 'consumers'

# Backtick-quoted absolute Windows paths only.
PATH_RE = re.compile(r'`([A-Za-z]:[\\/][^`]+)`')
# Inline silencing marker (see module docstring); matched only against text following the path
# on the same line.
STALE_PATH_OK_RE = re.compile(r'<!--\s*stale-path-ok(?::[^>]*)?\s*-->')
SCAN_FILES = ('CLAUDE.md', 'project_progress.md')


def main():
    config = get_shared_config(SHARED_ROOT)
    this_host = str(config.get('host_id', ''))

    if not CONSUMERS_DIR.is_dir():
        return

    for f in sorted(CONSUMERS_DIR.glob('*.md')):
        c = parse_registry(f)
        if c is None:
            continue
        this_path = host_path(c, this_host)
        if not this_path or not Path(this_path).exists():
            continue

        for filename in SCAN_FILES:
            file_path = Path(this_path) / filename
            if not file_path.exists():
                continue
            text = file_path.read_text(encoding='utf-8', errors='ignore')
            for line in text.splitlines():
                for m in PATH_RE.finditer(line):
                    candidate = m.group(1)
                    if Path(candidate).exists():
                        continue
                    if STALE_PATH_OK_RE.search(line[m.end():]):
                        continue  # explicitly marked as an intentional single-host reference
                    print(f"[STALE-PATH] '{c['name']}': {filename} references '{candidate}' - "
                          f"doesn't exist on this host ('{this_host}'). Stale, or intentionally "
                          f"single-host-only? Mark it `<!-- stale-path-ok -->` right after the "
                          f"path on the same line if intentional.")


if __name__ == '__main__':
    main()
