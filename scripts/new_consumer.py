#!/usr/bin/env python3
"""
new_consumer.py - scaffold a new tower_crane consumer project, deterministic, non-interactive.

Creates ALL files a new consumer needs so it works like existing consumers from its first
session (consumer_platform design, decision 10):
  <target>/.claude/settings.json   - opt-in hook snippet(s) for the chosen tools (merged)
  <target>/CLAUDE.md               - from templates/consumer_CLAUDE.md.tmpl, with @import lines
  <target>/.claude/skills/<name>/  - Track-1 skill stub(s) for toolkit-governed pieces in
                                     SKILL_PIECES (design\\directive_economy.md) - `filing`,
                                     `checkpoint`, `archive` so far
  <target>/project_progress.md      - continuity skeleton (only when continuity is on)
  <target>/FIRST_RUN.md             - one-time checklist the new project runs then deletes
  consumers/<slug>.md               - registry entry (this repo)

consumers/<slug>.md is the ONLY place a project name is recorded - it lives in the outer, private
hub repo (design\\local_first_reframe.md's outer/inner split), never in toolkit\\ itself, which
tracks the public konvesdigital/tower-crane repo. MENU.md's "In use by" column was removed
2026-07-28 after it was found writing real consumer/client names into that public-repo-tracked
file - see project_progress.md.

This script does NOT run git - git init + first commit is a FIRST_RUN.md step in the new project.

OS-reach Tier 2 port of new_consumer.ps1 (design\\portability.md, "OS-reach Tier 2: full
cross-platform design"). Logic is a direct translation - see that doc's Build order for the
parity-check approach used to verify ports in this series. Generated files (settings.json,
CLAUDE.md, project_progress.md, FIRST_RUN.md, registry entry) now use LF line endings universally
(the locked line-endings decision, bundled into this port).
"""

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config_lib import get_shared_config, get_expanded_optin

SHARED_ROOT = Path(__file__).resolve().parent.parent
# consumers\ is private hub state, not shipped toolkit content - it lives at the outer root
# (design\local_first_reframe.md's outer/inner split), one level above SHARED_ROOT (toolkit\).
PROJECT_ROOT = SHARED_ROOT.parent
TEMPLATES_DIR = SHARED_ROOT / 'templates'
OPTINS_DIR = TEMPLATES_DIR / 'optins'
CONSUMERS_DIR = PROJECT_ROOT / 'consumers'
TMPL_PATH = TEMPLATES_DIR / 'consumer_CLAUDE.md.tmpl'

# short human blurb per known tool for the "Tower Crane In Use" list (falls back to the name)
TOOL_BLURBS = {
    'consistency_check': 'AST static analysis on Python writes/edits - undefined names, arg-count, '
                          'string-key spelling (PostToolUse hook).',
}

# Toolkit-governed Track-1 skill pieces (design\\directive_economy.md): a piece name in here is
# scaffolded as one or more project-local skill stubs (each sourced from
# templates/skills/<skill>/SKILL.md) plus a still-@imported Track-2 "resume check" companion,
# instead of a flat @import <name>.md. `filing` -> one skill of the same name (2026-07-30 pilot);
# `continuity` -> two skills, `checkpoint` and `archive` (2026-07-31 - `resume` itself stays
# Track 2, see continuity_resume_check.md). compliance stays flat - never piloted this way.
SKILL_PIECES = {
    'filing': {'companion': 'filing_resume_check', 'skills': ['filing']},
    'continuity': {'companion': 'continuity_resume_check', 'skills': ['checkpoint', 'archive']},
}


def write_utf8(path, content):
    # Python's utf-8 encoding never writes a BOM (unlike PS 5.1's -Encoding utf8); newline='\n'
    # keeps embedded '\n' as LF instead of Windows-translating it to CRLF on write.
    path.write_text(content, encoding='utf-8', newline='\n')


def get_slug(name):
    s = name.lower().strip()
    s = re.sub(r'[^a-z0-9]+', '_', s)
    s = re.sub(r'^_+|_+$', '', s)
    return s


def main():
    parser = argparse.ArgumentParser(description="Scaffold a new tower_crane consumer project.")
    parser.add_argument('--target-path', required=True, help="Absolute path to the new consumer's project root.")
    parser.add_argument('--project-name', required=True, help='Full title in Title Case (e.g. "Geo Rank Tracker").')
    parser.add_argument('--tools', nargs='*', default=['consistency_check'],
                         help="Tools to opt into (each needs templates/optins/<tool>.json). Pass --tools with no "
                              "values for a consumer with no hooks. Default: consistency_check.")
    parser.add_argument('--no-continuity', action='store_true',
                         help="Opt out of the (default-on) continuity protocol piece. filing + compliance are "
                              "always imported.")
    parser.add_argument('--date', default=None, help="Scaffold date (YYYY-MM-DD). Defaults to today.")
    parser.add_argument('--force', action='store_true',
                         help="Overwrite an existing CLAUDE.md / project_progress.md / FIRST_RUN.md / registry entry.")
    args = parser.parse_args()

    target_path = Path(args.target_path)
    project_name = args.project_name
    tools = args.tools
    scaffold_date = args.date or date.today().isoformat()

    config = get_shared_config(SHARED_ROOT)
    import_base = str(config['import_base'])

    # --- validate --------------------------------------------------------------------------
    if not TMPL_PATH.exists():
        raise RuntimeError(f"Template not found: {TMPL_PATH}")
    if not project_name.strip():
        raise RuntimeError("ProjectName is empty.")

    slug = get_slug(project_name)
    if not slug:
        raise RuntimeError(f"ProjectName '{project_name}' slugifies to empty.")

    for t in tools:
        optin_path = OPTINS_DIR / f"{t}.json"
        if not optin_path.exists():
            raise RuntimeError(f"Unknown tool '{t}' - no opt-in snippet at {optin_path}")

    registry_path = CONSUMERS_DIR / f"{slug}.md"
    if registry_path.exists() and not args.force:
        raise RuntimeError(f"Consumer '{slug}' already registered ({registry_path}). Use --force to overwrite.")

    # protocol pieces: filing + compliance mandatory; continuity default-on
    pieces = ['filing', 'compliance']
    if not args.no_continuity:
        pieces.append('continuity')
    for p in pieces:
        skill_piece = SKILL_PIECES.get(p)
        if skill_piece:
            for skill_name in skill_piece['skills']:
                stub_src = TEMPLATES_DIR / 'skills' / skill_name / 'SKILL.md'
                if not stub_src.exists():
                    raise RuntimeError(f"Canonical skill stub missing for protocol piece '{p}': {stub_src}")
            companion = skill_piece['companion']
            companion_path = TEMPLATES_DIR / f"{companion}.md"
            if not companion_path.exists():
                raise RuntimeError(f"Protocol piece '{p}' companion '{companion}' missing: {companion_path}")
        else:
            piece_path = TEMPLATES_DIR / f"{p}.md"
            if not piece_path.exists():
                raise RuntimeError(f"Protocol piece '{p}' missing: {piece_path}")

    # the piece names actually @imported into CLAUDE.md - a SKILL_PIECES entry substitutes its
    # companion (e.g. 'filing' -> 'filing_resume_check'); everything else imports itself directly.
    import_pieces = [SKILL_PIECES[p]['companion'] if p in SKILL_PIECES else p for p in pieces]

    print(f"Scaffolding consumer '{project_name}' (slug: {slug})")
    print(f"  target : {target_path}")
    print(f"  tools  : {', '.join(tools)}")
    print(f"  pieces : {', '.join(pieces)}")

    # --- 1. ensure <target>/.claude/ --------------------------------------------------------
    claude_dir = target_path / '.claude'
    claude_dir.mkdir(parents=True, exist_ok=True)

    # --- 2. settings.json (merge opt-in snippets) -------------------------------------------
    settings_path = claude_dir / 'settings.json'
    if settings_path.exists():
        settings = json.loads(settings_path.read_text(encoding='utf-8'))
        if settings is None:
            settings = {}
    else:
        settings = {}
    settings.setdefault('hooks', {})

    for t in tools:
        # Expand config placeholders ({{PYTHON_LAUNCHER}}, {{SHARED_ROOT}}) into the concrete command.
        optin = get_expanded_optin(OPTINS_DIR / f"{t}.json", config)
        if 'hooks' in optin:
            for evt, groups in optin['hooks'].items():
                existing = settings['hooks'].setdefault(evt, [])
                # dedupe so re-running the scaffolder (--force) doesn't append the same hook twice;
                # existing_json is computed once (not updated per append) to mirror the original
                # PowerShell's static comparison snapshot.
                existing_json = [json.dumps(e, separators=(',', ':')) for e in existing]
                for entry in groups:
                    entry_json = json.dumps(entry, separators=(',', ':'))
                    if entry_json not in existing_json:
                        existing.append(entry)
    write_utf8(settings_path, json.dumps(settings, indent=2))
    print(f"  wrote  {settings_path}")

    # --- 3. CLAUDE.md from template ----------------------------------------------------------
    claude_md_path = target_path / 'CLAUDE.md'
    if claude_md_path.exists() and not args.force:
        raise RuntimeError(f"CLAUDE.md already exists at {claude_md_path}. Use --force to overwrite.")

    if not tools:
        tools_list = '_No shared tools opted in yet._'
    else:
        tools_list = '\n'.join(
            f"- `{t}` - {TOOL_BLURBS.get(t, 'see tower_crane MENU.md.')}" for t in tools
        )
    protocol_imports = '\n'.join(f"@{import_base}/{p}.md" for p in import_pieces)

    tmpl = TMPL_PATH.read_text(encoding='utf-8')
    # strip the template's own leading HTML-comment header (documentation for maintainers, not consumers)
    tmpl = re.sub(r'^\s*<!--.*?-->\s*', '', tmpl, count=1, flags=re.DOTALL)
    claude_md = (tmpl
                 .replace('{{PROJECT_NAME}}', project_name)
                 .replace('{{DATE}}', scaffold_date)
                 .replace('{{SHARED_TOOLS_LIST}}', tools_list)
                 .replace('{{PROTOCOL_IMPORTS}}', protocol_imports))
    write_utf8(claude_md_path, claude_md)
    print(f"  wrote  {claude_md_path}")

    # --- 3b. Track-1 skill stubs (toolkit-governed pieces only) ------------------------------
    for p in pieces:
        if p not in SKILL_PIECES:
            continue
        for skill_name in SKILL_PIECES[p]['skills']:
            stub_src = TEMPLATES_DIR / 'skills' / skill_name / 'SKILL.md'
            skill_dir = claude_dir / 'skills' / skill_name
            skill_dir.mkdir(parents=True, exist_ok=True)
            stub_path = skill_dir / 'SKILL.md'
            if stub_path.exists() and not args.force:
                print(f"  skip   {stub_path} exists (use --force to overwrite)")
                continue
            stub_content = stub_src.read_text(encoding='utf-8').replace('{{IMPORT_BASE}}', import_base)
            write_utf8(stub_path, stub_content)
            print(f"  wrote  {stub_path}")

    # --- 4. project_progress.md skeleton (continuity only) -----------------------------------
    if not args.no_continuity:
        progress_path = target_path / 'project_progress.md'
        if progress_path.exists() and not args.force:
            print("  skip   project_progress.md exists (use --force to overwrite)")
        else:
            progress = f"""# Project Progress

## Current Status
_New project scaffolded {scaffold_date}. Fill this in on the first working session._

## Next Up
- [ ] Complete the `FIRST_RUN.md` checklist (git init, accept import dialog, fill overview).

## Decisions
| Item | Status | Notes |
|---|---|---|

## Work Log (newest first - say "archive" anytime to move old, settled entries into project_progress_archive.md)
### {scaffold_date}
Project scaffolded from tower_crane (`scripts/new_consumer.py`): `.claude/settings.json`,
`CLAUDE.md` with protocol imports, this file, and `FIRST_RUN.md`. Registered in the shared
consumer registry.
"""
            write_utf8(progress_path, progress)
            print(f"  wrote  {progress_path}")

    # --- 5. FIRST_RUN.md ----------------------------------------------------------------------
    first_run_path = target_path / 'FIRST_RUN.md'
    if first_run_path.exists() and not args.force:
        print("  skip   FIRST_RUN.md exists (use --force to overwrite)")
    else:
        first_run = f"""# First Run - one-time setup for {project_name}

Scaffolded from tower_crane on {scaffold_date}. Do these once, then delete this file.

- [ ] `git init` and make an initial commit. (The scaffolder does NOT run git - this is a
      one-time local step.)
- [ ] On first launch, **accept the one-time CLAUDE.md import-approval dialog.** Declining
      disables `@import` permanently, so the shared protocol pieces (filing, compliance,
      continuity) won't load.
- [ ] Fill in the project-overview placeholder near the top of `CLAUDE.md` (what this project
      is, who it's for, key constraints).
- [ ] Delete this file (`FIRST_RUN.md`) once the above are done.
"""
        write_utf8(first_run_path, first_run)
        print(f"  wrote  {first_run_path}")

    # --- 6a. registry entry --------------------------------------------------------------------
    if not tools:
        opted_in_yaml = 'opted_in: []'
    else:
        opted_in_yaml = 'opted_in:\n' + '\n'.join(f"  - tool: {t}\n    since: {scaffold_date}" for t in tools)
    imported_yaml = 'imported:\n' + '\n'.join(f"  - piece: {p}\n    since: {scaffold_date}" for p in import_pieces)

    registry_path_forward_slash = str(target_path).replace('\\', '/')
    registry = f"""# {project_name}

```yaml
name: {project_name}
path: {registry_path_forward_slash}
host: {config['host_id']}
owner: {config['identity']['git_user_name']}
registered: {scaffold_date}
{opted_in_yaml}
{imported_yaml}
```

Notes: scaffolded by `scripts/new_consumer.py` on {scaffold_date}. Registry format is documented in
`consumers/geo_rank_tracker.md` (the machine-readable block the scaffolder writes and
`check_tower_crane.py` reads).
"""
    write_utf8(registry_path, registry)
    print(f"  wrote  {registry_path}")

    # --- 7. next steps -------------------------------------------------------------------------
    print()
    print("Done. Next steps:")
    print(f"  1. In tower_crane: review + commit the new consumers/{slug}.md.")
    print(f"  2. Open {target_path} in a fresh Claude Code session and complete FIRST_RUN.md")
    print("     (git init, accept the import-approval dialog, fill the CLAUDE.md overview).")


if __name__ == '__main__':
    main()
