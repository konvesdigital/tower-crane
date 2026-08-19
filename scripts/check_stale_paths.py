#!/usr/bin/env python3
"""
check_stale_paths.py - resume-time nudge for a stale hand-written absolute path left in a
connected consumer's own tracked prose (design\\grt_connectivity_audit.md item (iv)).

Corrected target, found during grounding research before this was built: the real incident this
item was named after (a hand-written line naming a real backup-drive path that only exists on one
of the operator's two machines) is NOT a same-tracked-file-different-host-value collision the way
the actual skill-stub issue (item (i)/(ii)) was - it's a legitimate single-host-only reference,
already explicitly named as needing human judgment in
design\\consumer_reference_indirection.md's "Explicitly out of scope" section.
check_file_surface.py's check 8c (host-id-substring matching, public-repo diff gate) wouldn't catch
this shape at all - the signal here isn't a host name, it's a plain path that happens not to exist
on whichever machine is currently reading it.

Scans each locally-connected consumer's own CLAUDE.md / project_progress.md for backtick-quoted
absolute Windows paths and flags any that don't resolve on THIS host's filesystem. Deliberately a
notify-only nudge, same shape as check_multi_machine.py/check_hook_activation.py - never mutates,
never blocks. A legitimate single-host-only reference is SUPPOSED to fail this check forever on
every other host; only a human can tell "stale, needs updating" apart from "intentionally
single-host" (matching the project's standing default of strong nudges over hard blocks).

Silencing a known-intentional match (added 2026-08-19, after the alert-fatigue concern this
mechanism would otherwise create - a check nagged into being ignored stops protecting against the
NEXT, genuinely-stale reference): write an inline `<!-- stale-path-ok -->` HTML comment right after
the closing backtick, on the same line - e.g. a line reading "Backups live at
`C:/Users/example/Documents/backup_folder` <!-- stale-path-ok: single-host -->" (the `: reason`
part is optional, purely for a human reader; forward or back slashes both match). Same convention
this project already uses elsewhere for a machine-readable annotation living next to human prose
without disrupting it (the shared_resources\\ adoption marker, hub_pointer.md's own header comment)
- deliberately inline, not a separate allowlist file, so the exception can never outlive or drift
from the line it excuses: if that line is later edited or deleted, the marker goes with it, nothing
to separately clean up. A brand-new stale reference has no marker yet, so it still surfaces
normally the first time anyone looks - marking a match is a one-time human judgment call recorded
once, not a standing suppression that could mask something new.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config_lib import get_shared_config
from registry_lib import parse_registry, host_path

SHARED_ROOT = Path(__file__).resolve().parent.parent
# consumers\ is private hub state, not shipped toolkit content - it lives at the outer root
# (design\local_first_reframe.md's outer/inner split), one level above SHARED_ROOT (toolkit\).
PROJECT_ROOT = SHARED_ROOT.parent
CONSUMERS_DIR = PROJECT_ROOT / 'consumers'

# Backtick-quoted absolute Windows paths only (narrower than a bare-path scan) - matches the
# actual observed shape (a Decisions-row line naming a path in backticks) and keeps false
# positives down for this first pass.
PATH_RE = re.compile(r'`([A-Za-z]:[\\/][^`]+)`')
# The inline silencing marker (see module docstring) - checked against whatever follows a matched
# path on the SAME line only, so a marker elsewhere in the file can never accidentally silence an
# unrelated match.
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
