#!/usr/bin/env python3
# shared_resources_read_tracker.py
# SHARED TOOL - lives in tower_crane\hooks\, referenced by any project that opts in.
#
# The companion
# hook to shared_resources_trigger_match.py's edge-assist feature. Edge-assist needs to know which
# shared_resources\ entries are already "in play" this session (a cross-turn fact) before it can
# relax or waive another resource's own trigger bar - this hook is what actually tracks that.
#
# Triggered by Claude Code's PostToolUse hook, matched to Read|Grep calls only. On a Read whose
# file_path (or a Grep whose path) resolves to a specific file under this hub's own
# shared_resources\ folder, appends that file's stem to a small per-session state file. A directory-
# wide Grep (no specific file resolved) records nothing - the design's own reasoning for using a
# Read/Grep hit at all is that the resource's actual content is genuinely sitting in the agent's
# context, which a directory-wide grep hit across many files doesn't establish for any one of them.
#
# Deliberately does NOT re-read the target file's content (unlike consistency_check.py, which reads
# a file's content to analyze it) - only the resolved path itself is needed to identify which
# resource stem was read, so this hook does strictly less work than consistency_check.py already
# does on every relevant tool call today.
#
# State file: <CLAUDE_PROJECT_DIR>\logs\shared_resources_session_state\<session_id>.txt, one
# resource stem per line, deduplicated - colocated with this project's own logs\ folder, same
# convention consistency_check.py already uses for ITS log output, keyed by session_id since "in
# play" is scoped to one running Claude Code session, not the whole project. Read back by
# shared_resources_trigger_match.py's own read_in_play_resources().
#
# HARD CONTRACT, same as shared_resources_trigger_match.py's: this hook must NEVER exit 2 and must
# never print anything that could be mistaken for a guardrail failure - it is silent, best-effort
# plumbing, not a check. Any error (missing CLAUDE_PROJECT_DIR, missing session_id, unreadable/
# unwritable state path, malformed stdin JSON) fails open: no output, exit 0. Prints nothing on
# success either - a Read/Grep call happens far more often than a shared_resources\ hit, and this
# hook's whole job is to be invisible plumbing, not something the agent has to read past every time.
#
# To use in a project: add a PostToolUse hook (matcher "Read|Grep") in that project's
# .claude\settings.json pointing at this file (see MENU.md / templates\optins\
# shared_resources_read_tracker.json for the canonical snippet), then list it in that project's
# CLAUDE.md under "Tower Crane In Use". Optional - shared_resources_trigger_match.py's plain slot
# matching works fine without this hook wired; only edge-assist needs it.
#
# Invocation:
#   <python_launcher> shared_resources_read_tracker.py            # hook mode: reads stdin JSON
#
# Exit codes: always 0.

import json
import os
import sys
from pathlib import Path

SHARED_ROOT = Path(__file__).resolve().parent.parent
# Same outer/inner split convention as shared_resources_trigger_match.py - shared_resources\ lives
# at the hub root, one level above SHARED_ROOT (toolkit\), computed from this script's own fixed
# location rather than the calling (consuming) project's directory.
HUB_ROOT = SHARED_ROOT.parent
HUB_SHARED_RESOURCES = (HUB_ROOT / 'shared_resources').resolve()


def resolve_candidate_path(tool_name, tool_input):
    if tool_name == 'Read':
        return tool_input.get('file_path')
    if tool_name == 'Grep':
        return tool_input.get('path')
    return None


def main():
    try:
        raw = sys.stdin.read()
        raw = raw.lstrip(chr(0xFEFF))  # tolerate a UTF-8 BOM some Windows pipes prepend
        if not raw.strip():
            sys.exit(0)
        data = json.loads(raw)

        project_root = os.environ.get('CLAUDE_PROJECT_DIR')
        session_id = data.get('session_id')
        if not project_root or not session_id:
            sys.exit(0)

        path_str = resolve_candidate_path(data.get('tool_name', ''), data.get('tool_input', {}) or {})
        if not path_str:
            sys.exit(0)

        candidate = Path(path_str)
        if not candidate.is_absolute():
            candidate = Path(project_root) / candidate
        candidate = candidate.resolve()

        # Only a specific .md file, actually under the hub's own shared_resources\ folder, counts as
        # a resource "in play" - a directory-wide Grep (path resolves to a directory, or to
        # something outside shared_resources\ entirely) is skipped, not an error.
        if candidate.suffix.lower() != '.md':
            sys.exit(0)
        if HUB_SHARED_RESOURCES not in candidate.parents:
            sys.exit(0)
        if not candidate.is_file():
            sys.exit(0)

        resource_stem = candidate.stem

        state_dir = Path(project_root) / 'logs' / 'shared_resources_session_state'
        state_path = state_dir / f'{session_id}.txt'
        state_dir.mkdir(parents=True, exist_ok=True)

        existing = set()
        if state_path.exists():
            existing = {line.strip() for line in state_path.read_text(encoding='utf-8').splitlines() if line.strip()}
        if resource_stem not in existing:
            with open(state_path, 'a', encoding='utf-8') as f:
                f.write(resource_stem + '\n')

        sys.exit(0)
    except Exception:
        # Fail open, always - this is best-effort plumbing, never allowed to block a Read/Grep call.
        sys.exit(0)


if __name__ == '__main__':
    main()
