#!/usr/bin/env python3
"""
new_consumer.py - scaffold a new tower_crane consumer project, deterministic, non-interactive.

Creates ALL files a new consumer needs so it works like existing consumers from its first
session (consumer_platform design, decision 10):
  <target>/.claude/settings.json   - opt-in hook snippet(s) for the chosen tools (merged)
  <target>/CLAUDE.md               - from templates/consumer_CLAUDE.md.tmpl, with @import lines
  <target>/.claude/skills/<name>/  - Track-1 skill stub(s) for toolkit-governed pieces in
                                     SKILL_PIECES (design\\directive_economy.md) - `filing`,
                                     `checkpoint`, `archive`, `shared_resources` so far - plus every
                                     STANDALONE_SKILLS entry (design\\consumer_update.md,
                                     design\\optimize_ux.md) - `update`, `commands` so far
  <target>/project_progress.md      - continuity skeleton (only when continuity is on)
  <target>/FIRST_RUN.md             - one-time checklist the new project runs then deletes
  consumers/<slug>.md               - registry entry (this repo)

consumers/<slug>.md is the ONLY place a project name is recorded - it lives in the outer, private
hub repo (design\\local_first_reframe.md's outer/inner split), never in toolkit\\ itself, which
tracks the public konvesdigital/tower-crane repo. MENU.md's "In use by" column was removed
2026-07-28 after it was found writing real consumer/client names into that public-repo-tracked
file - see project_progress.md.

Recognized existing-CLAUDE.md shapes, each handled non-destructively (see the "CLAUDE.md from
template" section below): a registered consumer connecting another host (host-merge, patches
@import lines only), a disconnected project reconnecting (strips the DISCONNECTED_HEADING marker,
re-appends the live sections), and an unregistered hand-copied project with no Tower Crane content
at all (adoption - appends the live sections to whatever's already there). This third shape used to
require copying templates\\register.md into the target project and filing a ticket back here from
a separate session; that courier is retired (2026-08-12, design\\connect_disconnect.md's deferred
"register.md's fate" note) now that this script can just be run directly from a hub session, the
same as every other shape.

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
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config_lib import (
    get_shared_config, get_expanded_optin, materialize_skill_stub,
    build_new_cmd_map, apply_hook_command_fixes, print_diagnose_inline,
    TC_IN_USE_HEADING, WORKFLOW_HEADING, DISCONNECTED_HEADING, DISCONNECT_NOTES_FILENAME,
    FIRST_RUN_FILENAME, CONSUMER_OWNED_PATHS,
    HUB_POINTER_IMPORT_LINE, HUB_POINTER_RELPATH, HUB_DISPATCH_RELPATH, HUB_DISPATCH_TEMPLATE,
    get_dispatch_optin, build_hub_pointer_content, build_dispatch_cmd_map,
    write_new_connection_files, collapse_imports_to_pointer, fix_imports, commit_hub_changes,
    commit_consumer_changes, path_is_clean, commit_consumer_progress_note, scoped_status_paths,
)
import registry_lib

SHARED_ROOT = Path(__file__).resolve().parent.parent
# consumers\ is private hub state, not shipped toolkit content - it lives at the outer root
# (design\local_first_reframe.md's outer/inner split), one level above SHARED_ROOT (toolkit\).
PROJECT_ROOT = SHARED_ROOT.parent
TEMPLATES_DIR = SHARED_ROOT / 'templates'
OPTINS_DIR = TEMPLATES_DIR / 'optins'
CONSUMERS_DIR = PROJECT_ROOT / 'consumers'
TMPL_PATH = TEMPLATES_DIR / 'consumer_CLAUDE.md.tmpl'
# design\private_tools.md - private, automatic tools living outside toolkit\, never shipped.
PRIVATE_ROOT = PROJECT_ROOT / 'toolkit_private'
PRIVATE_OPTINS_DIR = PRIVATE_ROOT / 'templates' / 'optins'
PRIVATE_SKILLS_DIR = PRIVATE_ROOT / 'templates' / 'skills'

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
    'shared_resources': {'companion': 'shared_resources_resume_check', 'skills': ['shared_resources']},
}

# Standalone Track-1 skills with no @import companion at all (design\\consumer_update.md): scaffolded
# for every new consumer unconditionally, alongside (not through) the SKILL_PIECES protocol pieces
# above. `update` is purely on-demand - nothing resume-time ever checks for it. `commands`
# (design\\optimize_ux.md) is the consumer-side discoverability menu, same on-demand shape.
# `capability_relationships` (design\\capability_relationships.md) answers a specific
# mechanism/concept question by reading capability_catalog.yaml - also fires from a hub session,
# via self_hooks.py's separate "skills" opt-in mechanism (templates\\optins\\capability_relationships.json).
STANDALONE_SKILLS = ['update', 'commands', 'capability_relationships']


def write_utf8(path, content):
    # Python's utf-8 encoding never writes a BOM (unlike PS 5.1's -Encoding utf8); newline='\n'
    # keeps embedded '\n' as LF instead of Windows-translating it to CRLF on write.
    path.write_text(content, encoding='utf-8', newline='\n')


def get_slug(name):
    s = name.lower().strip()
    s = re.sub(r'[^a-z0-9]+', '_', s)
    s = re.sub(r'^_+|_+$', '', s)
    return s


def try_capture_remote(target_path):
    """Best-effort `git remote get-url origin` from target_path's own clone, or None if there's
    no .git\\ yet, no `origin` remote, or git isn't available - design\\consumer_reconnect.md's
    `remote:` registry field is seed-once/best-effort, never required."""
    if not (target_path / '.git').exists():
        return None
    try:
        result = subprocess.run(['git', '-C', str(target_path), 'remote', 'get-url', 'origin'],
                                 capture_output=True, text=True)
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def detect_git_state(target_path):
    """(has_git, remote) at target_path - design\\connect_disconnect.md's "Reconnect-after-disconnect gap":
    a reconnecting project (or a never-connected one someone already set up by hand) may already
    have git, or a remote, or both - never assume a consumer starts from nothing. Drives
    build_first_run_checklist() so the checklist only ever lists what's actually still missing."""
    has_git = (Path(target_path) / '.git').exists()
    return has_git, (try_capture_remote(target_path) if has_git else None)


def strip_disconnected_section(text):
    """Inverse of disconnect_consumer.py's replace_prose_sections(): removes the
    DISCONNECTED_HEADING section (that heading through the next '## ' heading, or EOF) instead of
    replacing it. Returns (new_text, found) - found is False if the marker isn't present."""
    idx_start = text.find(DISCONNECTED_HEADING)
    if idx_start == -1:
        return text, False
    idx_end = len(text)
    for m in re.finditer(r'(?m)^## .+$', text):
        if m.start() > idx_start:
            idx_end = m.start()
            break
    return text[:idx_start] + text[idx_end:], True


def find_oldest_registry_commit_date(slug):
    """Best-effort: date of the OLDEST commit touching consumers/<slug>.md in the hub's own git
    history - fallback when the notes file doesn't carry the field. Local to new_consumer.py, not
    reused from check_tower_crane.py's --diagnose (design\\connect_disconnect.md's rejected-
    alternatives note: importing that tool would pull its whole import graph into every plain
    scaffold invocation). Returns None on any failure (no git, empty history, never registered,
    shallow clone) - never raises."""
    try:
        proc = subprocess.run(
            ['git', '-C', str(PROJECT_ROOT), 'log', '--format=%ci', '--', f'consumers/{slug}.md'],
            capture_output=True, text=True)
    except OSError:
        return None
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    return proc.stdout.strip().splitlines()[-1][:10]  # oldest is last (git log is newest-first)


def build_first_run_checklist(has_git, remote, needs_overview):
    """Only lists what's actually still needed, based on detected state - a reconnecting project
    (real history, usually real git/remote already) and a never-connected one someone already set
    up by hand both deserve an accurate checklist, not a blanket "start from scratch" one
    (design\\connect_disconnect.md "Reconnect-after-disconnect gap")."""
    items = []
    if not has_git:
        items.append("- [ ] `git init` and make an initial commit. (The scaffolder does NOT run "
                      "git - this is a one-time local step.)")
    if not remote:
        items.append("- [ ] Optional: add a git remote (e.g. on GitHub) if you want off-machine "
                      "backup/sync - not required for Tower Crane itself.")
    items.append("- [ ] On first launch, **accept the one-time CLAUDE.md import-approval dialog** "
                 "if prompted. Declining disables `@import` permanently, so the shared protocol "
                 "pieces (filing, compliance, shared_resources, continuity) won't load.")
    if needs_overview:
        items.append("- [ ] Fill in the project-overview placeholder near the top of `CLAUDE.md` "
                      "(what this project is, who it's for, key constraints).")
    items.append("- [ ] Delete this file (`FIRST_RUN.md`) once the above are done.")
    return items


_COMMIT_RESULT_LABELS = {
    'noop': "nothing to commit",
    'committed-pushed': "committed and pushed",
    'committed-no-remote': "committed (no origin remote to push to)",
    'commit-failed': "commit FAILED - see warning above",
    'push-failed': "committed locally, push FAILED - see warning above",
    'reconciled-pushed': "push conflict auto-reconciled, committed and pushed",
}


def print_close_out_summary(project_name, target_path, existing_consumer, already_connected_here,
                             is_reconnect, is_adoption, consumer_commit_result,
                             progress_commit_result, registry_commit_result, remaining_checklist):
    """One explicit block, printed once at the very end of the run, from the same classification/
    commit-result variables main() already computed along the way (design\\
    script_action_reporting.md) - never re-derived a second time by whatever reads this output.
    "Left uncommitted" is the one line NOT sourced from an already-known variable: it re-checks git
    directly (evidence over intent), since "what's still dirty" is exactly the fact a script's own
    belief about what it just committed can be wrong about."""
    print()
    print(f"=== {project_name}: connect project summary ===")

    if existing_consumer is not None and already_connected_here:
        print("Branch: already connected (re-scaffolded local files only, no new commit)")
    elif existing_consumer is not None:
        print("Branch: host-merge (new host joining an already-registered consumer)")
    elif is_reconnect:
        print("Branch: reconnect (previously disconnected)")
    elif is_adoption:
        print("Branch: adoption (existing hand-copied project, no prior Tower Crane content)")
    else:
        print("Branch: brand new")

    has_git = (target_path / '.git').exists()
    print(f"git: {'present' if has_git else 'not present - run `git init` before your first session'}")

    if consumer_commit_result is not None:
        owned_now = [p + '/*' if (target_path / p).is_dir() else p
                     for p in CONSUMER_OWNED_PATHS if (target_path / p).exists()]
        label = _COMMIT_RESULT_LABELS.get(consumer_commit_result, consumer_commit_result)
        print(f"Committed to {project_name}'s own repo ({label}):")
        print("  " + (', '.join(owned_now) if owned_now else '(none present)'))

    if progress_commit_result is not None:
        label = _COMMIT_RESULT_LABELS.get(progress_commit_result, progress_commit_result)
        print(f"project_progress.md note: {label}")

    if has_git:
        left = scoped_status_paths(target_path, list(CONSUMER_OWNED_PATHS) + ['project_progress.md'])
        if left:
            print("Left uncommitted (not covered by this run's commit(s)):")
            print("  " + ', '.join(left))

    if registry_commit_result is not None:
        label = _COMMIT_RESULT_LABELS.get(registry_commit_result, registry_commit_result)
        print(f"Registered in the hub's own registry: {label}.")
    elif existing_consumer is not None and already_connected_here:
        print("Registered in the hub's own registry: unchanged (already had this host).")

    if remaining_checklist:
        print("Remaining for the user (from FIRST_RUN.md, or the equivalent for this branch):")
        for item in remaining_checklist:
            print(f"  {item}")


def main():
    parser = argparse.ArgumentParser(description="Scaffold a new tower_crane consumer project.")
    parser.add_argument('--target-path', required=True, help="Absolute path to the new consumer's project root.")
    parser.add_argument('--project-name', required=True, help='Full title in Title Case (e.g. "My Cool Project").')
    parser.add_argument('--tools', nargs='*', default=['consistency_check'],
                         help="Tools to opt into (each needs templates/optins/<tool>.json). Pass --tools with no "
                              "values for a consumer with no hooks. Default: consistency_check.")
    parser.add_argument('--private-tools', nargs='*', default=[],
                         help="Private tools to opt into (design\\private_tools.md) - each needs either "
                              "toolkit_private/templates/optins/<name>.json (hook) or "
                              "toolkit_private/templates/skills/<name>/SKILL.md (Track-1 skill). Default: none.")
    parser.add_argument('--no-continuity', action='store_true',
                         help="Opt out of the (default-on) continuity protocol piece. filing + compliance + "
                              "shared_resources are always imported.")
    parser.add_argument('--date', default=None, help="Scaffold date (YYYY-MM-DD). Defaults to today.")
    parser.add_argument('--scope', choices=['local', 'multi_machine'], default='local',
                         help="design\\multi_machine_hub.md: 'local' (default) if this consumer should live on "
                              "only this machine, 'multi_machine' to declare it available to all connected "
                              "machines immediately (so other hosts' resume can nudge about connecting it too). "
                              "Only meaningful for a BRAND NEW registry entry - connecting an already-registered "
                              "consumer's 2nd host always sets multi_machine automatically (the 2-host floor), "
                              "regardless of this flag.")
    parser.add_argument('--force', action='store_true',
                         help="Overwrite an existing CLAUDE.md / project_progress.md / FIRST_RUN.md. Never "
                              "applies to an already-registered consumer's registry file - a slug collision "
                              "there always routes into an additive host-merge (design\\multi_machine_hub.md's "
                              "locked slug-collision routing), never a blind overwrite.")
    parser.add_argument('--no-clone', action='store_true',
                         help="design\\consumer_reconnect.md: when connecting an already-registered consumer to "
                              "an empty target folder and its registry has a remote: on record, the default is "
                              "to `git clone` it before scaffolding. Pass this to scaffold a blank folder instead.")
    args = parser.parse_args()

    target_path = Path(args.target_path)
    project_name = args.project_name
    tools = args.tools
    private_tools = args.private_tools
    scaffold_date = args.date or date.today().isoformat()

    # Close-out summary state (design\script_action_reporting.md): the classification/commit-result
    # variables the script already computes below, threaded out here so the final summary block
    # (step 8) can report them directly instead of a caller re-deriving the same facts secondhand.
    remaining_checklist = None
    consumer_commit_result = None
    progress_commit_result = None
    registry_commit_result = None

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

    private_tool_kinds = {}  # name -> 'hook' | 'skill'
    for t in private_tools:
        if (PRIVATE_OPTINS_DIR / f"{t}.json").exists():
            private_tool_kinds[t] = 'hook'
        elif (PRIVATE_SKILLS_DIR / t / 'SKILL.md').exists():
            private_tool_kinds[t] = 'skill'
        else:
            raise RuntimeError(f"Unknown private tool '{t}' - no opt-in snippet at "
                                f"{PRIVATE_OPTINS_DIR / (t + '.json')} and no skill stub at "
                                f"{PRIVATE_SKILLS_DIR / t / 'SKILL.md'}")

    # Slug-collision routing (design\multi_machine_hub.md, locked 2026-08-10): an already-
    # registered consumer is never an error and never a --force blind overwrite target - it
    # always routes into an additive host-merge below (step 6a), so a second machine connecting
    # the same project can never destroy the first machine's hosts: entry.
    registry_path = CONSUMERS_DIR / f"{slug}.md"
    existing_consumer = None
    already_connected_here = False
    if registry_path.exists():
        existing_consumer = registry_lib.parse_registry(registry_path)
        if existing_consumer is None:
            print_diagnose_inline(config, path=target_path, slug=slug)
            raise RuntimeError(
                f"Consumer '{slug}' already registered ({registry_path}) but its yaml block "
                "isn't parseable - fix it by hand before scaffolding here. See "
                "toolkit\\troubleshoot_project_connection.md if the corruption's cause isn't obvious."
            )
        already_connected_here = config['host_id'] in existing_consumer['hosts']

    # design\consumer_reference_indirection.md: a "new connection" is any brand-new consumer,
    # reconnect, adoption, or a genuinely NEW host joining an already-registered consumer
    # (existing_consumer is not None and NOT already_connected_here) - every one of those gets the
    # new hub_pointer.md/_hub_dispatch.py indirection. Re-scaffolding a host that's ALREADY
    # connected is deliberately excluded (no forced migration of an existing, working connection -
    # see design\consumer_reference_indirection.md's "Migrate all 3 existing consumers now vs.
    # opportunistically" decision) - that one case keeps today's direct-path behavior untouched.
    is_new_connection = existing_consumer is None or not already_connected_here

    # Blank-folder bootstrap (design\consumer_reconnect.md): connecting an already-registered
    # consumer whose target folder is genuinely empty and whose registry carries a remote: -
    # clone before any scaffolding touches the folder. Ordering matters: cloning AFTER scaffolding
    # would hit `refusing to merge unrelated histories`, or a same-path merge conflict in
    # CLAUDE.md/settings.json/project_progress.md. Once cloned, the folder "already has files" and
    # falls straight through to the same file-existence-keyed patch logic below as a physical copy
    # would - no separate code path. Recovery (a corrupted/deleted local clone) reduces to this
    # same path once the broken folder has been emptied first.
    if existing_consumer is not None and not already_connected_here and not args.no_clone:
        remote = existing_consumer.get('remote')
        folder_empty = not target_path.exists() or (target_path.is_dir() and not any(target_path.iterdir()))
        if remote and folder_empty:
            print(f"Target folder is empty and '{project_name}' has a remote on record: {remote}")
            print(f"  cloning before scaffolding: git clone {remote} {target_path}")
            target_path.mkdir(parents=True, exist_ok=True)
            result = subprocess.run(['git', 'clone', remote, str(target_path)], capture_output=True, text=True)
            if result.returncode != 0:
                print_diagnose_inline(config, path=target_path, slug=slug)
                raise RuntimeError(
                    f"git clone of '{remote}' into {target_path} failed:\n{result.stderr}\n"
                    "See toolkit\\troubleshoot_project_connection.md's 'git clone ... failed' row."
                )
            print("  cloned OK")

    # protocol pieces: filing + compliance + shared_resources mandatory; continuity default-on
    pieces = ['filing', 'compliance', 'shared_resources']
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

    for skill_name in STANDALONE_SKILLS:
        stub_src = TEMPLATES_DIR / 'skills' / skill_name / 'SKILL.md'
        if not stub_src.exists():
            raise RuntimeError(f"Canonical skill stub missing for standalone skill '{skill_name}': {stub_src}")

    # the piece names actually @imported into CLAUDE.md - a SKILL_PIECES entry substitutes its
    # companion (e.g. 'filing' -> 'filing_resume_check'); everything else imports itself directly.
    import_pieces = [SKILL_PIECES[p]['companion'] if p in SKILL_PIECES else p for p in pieces]

    if existing_consumer is not None:
        if already_connected_here:
            print(f"Consumer '{project_name}' (slug: {slug}) already has a hosts.{config['host_id']} entry - "
                  "re-scaffolding local files only, registry unchanged.")
        else:
            print(f"Consumer '{project_name}' (slug: {slug}) is already registered elsewhere - "
                  f"connecting this machine ('{config['host_id']}') as an additional host.")
    else:
        print(f"Scaffolding consumer '{project_name}' (slug: {slug})")
    print(f"  target : {target_path}")
    print(f"  tools  : {', '.join(tools)}")
    if private_tools:
        print(f"  private: {', '.join(private_tools)}")
    print(f"  pieces : {', '.join(pieces)}")

    # --- 1. ensure <target>/.claude/ --------------------------------------------------------
    claude_dir = target_path / '.claude'
    claude_dir.mkdir(parents=True, exist_ok=True)

    # --- 1a. hub_pointer.md / _hub_dispatch.py / .gitignore (new connections only) -----------
    # design\consumer_reference_indirection.md: written BEFORE settings.json below, since that
    # step's own tool-merge loop needs is_new_connection to already be decidable (it is - computed
    # above) to choose get_dispatch_optin() over get_expanded_optin(). Reuses
    # write_new_connection_files() (config_lib.py) - design\grt_connectivity_audit.md item (iii)
    # factored this out so migrate_consumer_indirection.py's one-time already-connected-host
    # migration can call the identical write instead of a hand-copied duplicate.
    if is_new_connection:
        write_new_connection_files(target_path, config, import_pieces, SHARED_ROOT, log=print)

    # --- 2. settings.json (merge opt-in snippets) -------------------------------------------
    settings_path = claude_dir / 'settings.json'
    settings_existed = settings_path.exists()
    if settings_existed:
        settings = json.loads(settings_path.read_text(encoding='utf-8'))
        if settings is None:
            settings = {}
    else:
        settings = {}
    settings.setdefault('hooks', {})

    def _get_optin(optins_dir, tool_name):
        # design\consumer_reference_indirection.md: a new connection gets the fixed dispatch-
        # wrapper command form; an already-connected host's re-scaffold keeps today's direct-path
        # form untouched (no forced migration).
        if is_new_connection:
            return get_dispatch_optin(Path(optins_dir) / f"{tool_name}.json", tool_name, config)
        return get_expanded_optin(Path(optins_dir) / f"{tool_name}.json", config)

    if settings_existed and existing_consumer is not None:
        # host-merge branch (design\consumer_reconnect.md): repoint any ALREADY-PRESENT hook
        # command (from a physically-copied settings.json) for tools the registry already lists
        # as opted-in, reusing relocate.py's own regeneration. Fixes the double-hook-firing risk:
        # a stale other-machine-path entry and a freshly-appended current-path entry below would
        # never match as duplicates under the exact-JSON dedup the append loop uses.
        existing_tool_names = [o['name'] for o in existing_consumer['opted_in']]
        existing_private_names = [o['name'] for o in existing_consumer['private_opted_in']]
        if is_new_connection:
            # design\consumer_reference_indirection.md: a genuinely new host joining an
            # already-registered consumer gets the dispatch-wrapper command form here too, same as
            # the fresh-tool-merge loop below - one command shape per settings.json, never mixed.
            stale_cmd = build_dispatch_cmd_map(existing_tool_names, existing_private_names, config, OPTINS_DIR, PRIVATE_OPTINS_DIR)
        else:
            stale_cmd = build_new_cmd_map(existing_tool_names, existing_private_names, config, OPTINS_DIR, PRIVATE_OPTINS_DIR)
        if apply_hook_command_fixes(settings, stale_cmd, existing_tool_names + existing_private_names,
                                     dry_run=False, log=print):
            print(f"  patched stale hook command(s) in {settings_path}")

    # Every consumer reads canonical Track-1 skill/resume-check content straight out of
    # toolkit\templates (e.g. "Read {{IMPORT_BASE}}/filing.md in full") - that's outside the
    # project root, so without an allow rule every such read prompts. templates\ is read-only
    # content by convention (templates\filing.md: "never edit any existing file inside toolkit\"),
    # so blanket-allowing Read there carries no write risk.
    allow_list = settings.setdefault('permissions', {}).setdefault('allow', [])
    read_rule = f"Read({import_base}/**)"
    if read_rule not in allow_list:
        allow_list.append(read_rule)

    for t in tools:
        # Expand config placeholders into the concrete command - dispatch-wrapper form for a new
        # connection, direct-path form otherwise (design\consumer_reference_indirection.md).
        optin = _get_optin(OPTINS_DIR, t)
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

    for t, kind in private_tool_kinds.items():
        if kind != 'hook':
            continue
        # {{PRIVATE_ROOT}} expands the same way {{SHARED_ROOT}} does above.
        optin = _get_optin(PRIVATE_OPTINS_DIR, t)
        if 'hooks' in optin:
            for evt, groups in optin['hooks'].items():
                existing = settings['hooks'].setdefault(evt, [])
                existing_json = [json.dumps(e, separators=(',', ':')) for e in existing]
                for entry in groups:
                    entry_json = json.dumps(entry, separators=(',', ':'))
                    if entry_json not in existing_json:
                        existing.append(entry)
    write_utf8(settings_path, json.dumps(settings, indent=2))
    print(f"  wrote  {settings_path}")

    # --- 3. CLAUDE.md from template ----------------------------------------------------------
    claude_md_path = target_path / 'CLAUDE.md'
    # design\consumer_reference_indirection.md: a new connection gets the single, host-invariant
    # indirection line; only reachable when existing_consumer is None (reconnect/adoption/brand
    # new), which is always is_new_connection - the direct-lines join stays here only as a
    # defensive fallback, never actually exercised.
    protocol_imports = HUB_POINTER_IMPORT_LINE if is_new_connection else '\n'.join(
        f"@{import_base}/{p}.md" for p in import_pieces)

    # Per-file principle reframe (design\connect_disconnect.md): claude_md_existed is captured
    # ONCE, before any write, and is the one signal other files below should consult about
    # CLAUDE.md's prior state - never is_reconnect/is_adoption themselves, which are CLAUDE.md's
    # own content-driven classification and can legitimately be True even when CLAUDE.md itself
    # doesn't exist (a hand-removed DISCONNECTED_HEADING with the notes file still present).
    claude_md_existed = claude_md_path.exists()
    notes_path = target_path / DISCONNECT_NOTES_FILENAME
    notes_existed = notes_path.exists()

    # Reconnect detection (design\connect_disconnect.md "Reconnect-after-disconnect gap"): a previously
    # disconnected project has no registry entry (existing_consumer is None, same as brand new)
    # but either still carries the DISCONNECTED_HEADING pointer in CLAUDE.md, or - if that marker
    # was hand-removed - the surviving TOWER_CRANE_DISCONNECT_NOTES.md is itself durable evidence
    # of a prior connection (fixes the orphan bug: without this OR, a hand-stripped marker with the
    # notes file intact misrouted into the adoption branch and the notes file was never cleaned
    # up). Either way this is a recognized, safe-to-automate shape - not the ambiguous collision
    # the --force gate below exists to protect against.
    is_reconnect = False
    if existing_consumer is None:
        has_marker = claude_md_existed and DISCONNECTED_HEADING in claude_md_path.read_text(encoding='utf-8')
        is_reconnect = has_marker or notes_existed

    # Adoption detection (register.md's subsumption, 2026-08-12 - design\connect_disconnect.md's deferred
    # "register.md's fate" note): an existing hand-copied project that was never put through
    # new_consumer.py/register.md at all has a CLAUDE.md with no TC_IN_USE_HEADING and no
    # protocol-piece @import line - troubleshoot_project_connection.md's "no Tower Crane content at
    # all" shape, register.md's actual original target case. Recognized and safe to automate the
    # same way reconnect is: append, never overwrite - never routed through register.md, which is
    # retired (its no-hub-access scenario was already retired by design\local_first_reframe.md, and
    # every other recognized shape here already runs straight from a hub session with no ticket).
    is_adoption = False
    if claude_md_path.exists() and existing_consumer is None and not is_reconnect:
        existing_text = claude_md_path.read_text(encoding='utf-8')
        has_import_line = bool(re.search(
            r'(?m)^@\S+/(filing_resume_check|compliance|shared_resources_resume_check|'
            r'continuity_resume_check)\.md\s*$', existing_text))
        is_adoption = TC_IN_USE_HEADING not in existing_text and not has_import_line

    if claude_md_path.exists() and existing_consumer is not None and not is_new_connection:
        # already-connected-here re-scaffold: patch only the @import lines in place via
        # relocate.py's fix_imports(), instead of the old error-or-`--force` gate - `--force` used
        # to be the only way past this check, and it also unconditionally reset project_progress.md
        # to the blank skeleton. The project overview and everything else in CLAUDE.md is left
        # untouched. No forced migration to the pointer-indirection form here
        # (design\consumer_reference_indirection.md) - this host's connection already works.
        if fix_imports(target_path, import_pieces, import_base, dry_run=False, log=print):
            print(f"  patched {claude_md_path} (@import lines only)")
        else:
            print(f"  skip   {claude_md_path} already current (@import lines match)")
    elif claude_md_path.exists() and existing_consumer is not None and is_new_connection:
        # host-merge branch, genuinely new host (design\consumer_reconnect.md +
        # design\consumer_reference_indirection.md): collapse whatever direct-form @import lines
        # are already present (however many hosts wrote them before this one) into the single
        # host-invariant pointer line - this host's own hub_pointer.md (written above) is what
        # actually resolves it. A piece with no existing line just isn't found; not an error, since
        # the single pointer line covers every piece once hub_pointer.md exists. Reuses
        # collapse_imports_to_pointer() (config_lib.py) - design\grt_connectivity_audit.md item
        # (iii) factored this out for migrate_consumer_indirection.py's identical reuse.
        result = collapse_imports_to_pointer(claude_md_path, import_pieces, log=print)
        if result == 'already':
            print(f"  skip   {claude_md_path} already current (pointer import line present)")
        elif result == 'no-match':
            print(f"  note   {claude_md_path} has no recognized @import lines to collapse - "
                  f"add '{HUB_POINTER_IMPORT_LINE}' to its Shared Workflow Protocol section by hand.")
    elif claude_md_path.exists() and (is_reconnect or is_adoption):
        # Reconnect: strip the disconnected-pointer section first, preserving everything else.
        # Adoption: no marker to strip, just append to the existing content as-is. Either way,
        # reuses the same template the brand-new branch below renders from, sliced to just the two
        # live sections (TC_IN_USE_HEADING onward) so the project-name/overview-placeholder lines
        # at the top of the template are never applied over real content.
        if is_reconnect:
            text, _ = strip_disconnected_section(claude_md_path.read_text(encoding='utf-8'))
        else:
            text = claude_md_path.read_text(encoding='utf-8')
        if not tools:
            tools_list = '_No shared tools opted in yet._'
        else:
            tools_list = '\n'.join(
                f"- `{t}` - {TOOL_BLURBS.get(t, 'see tower_crane MENU.md.')}" for t in tools
            )
        tmpl = TMPL_PATH.read_text(encoding='utf-8')
        tmpl = re.sub(r'^\s*<!--.*?-->\s*', '', tmpl, count=1, flags=re.DOTALL)
        live_idx = tmpl.find(TC_IN_USE_HEADING)
        live_sections = tmpl[live_idx:] if live_idx != -1 else f"{TC_IN_USE_HEADING}\n\n{WORKFLOW_HEADING}\n\n"
        live_sections = (live_sections
                          .replace('{{DATE}}', scaffold_date)
                          .replace('{{SHARED_TOOLS_LIST}}', tools_list)
                          .replace('{{PROTOCOL_IMPORTS}}', protocol_imports))
        text = text.rstrip('\n') + '\n\n' + live_sections
        write_utf8(claude_md_path, text)
        if is_reconnect:
            print(f"  wrote  {claude_md_path} (reconnected: removed disconnected-pointer section, "
                  f"re-added Tower Crane In Use / Shared Workflow Protocol sections)")
        else:
            print(f"  wrote  {claude_md_path} (adopted: appended Tower Crane In Use / Shared "
                  f"Workflow Protocol sections to existing content - register.md's former "
                  f"target case, now handled directly)")
    elif claude_md_path.exists() and not args.force:
        print_diagnose_inline(config, path=target_path, slug=slug)
        raise RuntimeError(
            f"CLAUDE.md already exists at {claude_md_path} but doesn't match a recognized shape "
            "(no registry entry, not the disconnected-project marker, and it already carries some "
            "Tower Crane content - filing_resume_check/compliance/shared_resources_resume_check/"
            "continuity_resume_check imports or the 'Tower Crane In Use' heading). This usually "
            f"means registry drift: real content is present but consumers\\{slug}.md is missing. "
            "See toolkit\\troubleshoot_project_connection.md ('Registry entry missing but CLAUDE.md "
            "still looks live') before using --force."
        )
    else:
        if not tools:
            tools_list = '_No shared tools opted in yet._'
        else:
            tools_list = '\n'.join(
                f"- `{t}` - {TOOL_BLURBS.get(t, 'see tower_crane MENU.md.')}" for t in tools
            )

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

    # --- 3a. recover original registered: date on reconnect, then clean up the stale notes file --
    # Per-file principle reframe (design\connect_disconnect.md): TOWER_CRANE_DISCONNECT_NOTES.md
    # needs no classification of its own - if present at the moment a connection succeeds, its
    # contents are stale by definition, regardless of which CLAUDE.md branch fired above (covers
    # host-merge too). The date recovery must run BEFORE the delete below, since it reads the file.
    recovered_registered_date = None
    if is_reconnect:
        if notes_existed:
            m = re.search(r'Originally registered with Tower Crane:\s*\*\*([\d-]+)\*\*',
                           notes_path.read_text(encoding='utf-8'))
            if m:
                recovered_registered_date = m.group(1)
        if recovered_registered_date is None:
            recovered_registered_date = find_oldest_registry_commit_date(slug)

    if notes_path.exists():
        notes_path.unlink()
        print(f"  removed {notes_path} (stale as of this connection - superseded)")

    # --- 3b. Track-1 skill stubs (toolkit-governed pieces only) ------------------------------
    for p in pieces:
        if p not in SKILL_PIECES:
            continue
        for skill_name in SKILL_PIECES[p]['skills']:
            stub_src = TEMPLATES_DIR / 'skills' / skill_name / 'SKILL.md'
            skill_dir = claude_dir / 'skills' / skill_name
            skill_dir.mkdir(parents=True, exist_ok=True)
            stub_path = skill_dir / 'SKILL.md'
            if stub_path.exists() and not args.force and existing_consumer is None:
                print(f"  skip   {stub_path} exists (use --force to overwrite)")
                continue
            stub_content = materialize_skill_stub(stub_src, import_base, use_pointer=is_new_connection)
            write_utf8(stub_path, stub_content)
            print(f"  wrote  {stub_path}")

    # --- 3c. standalone Track-1 skills (no @import companion - always scaffolded) -------------
    for skill_name in STANDALONE_SKILLS:
        stub_src = TEMPLATES_DIR / 'skills' / skill_name / 'SKILL.md'
        skill_dir = claude_dir / 'skills' / skill_name
        skill_dir.mkdir(parents=True, exist_ok=True)
        stub_path = skill_dir / 'SKILL.md'
        if stub_path.exists() and not args.force and existing_consumer is None:
            print(f"  skip   {stub_path} exists (use --force to overwrite)")
            continue
        stub_content = materialize_skill_stub(stub_src, import_base, use_pointer=is_new_connection)
        write_utf8(stub_path, stub_content)
        print(f"  wrote  {stub_path}")

    # --- 3d. private skill stubs (design\private_tools.md - copy-only, no {{IMPORT_BASE}}) ----
    for t, kind in private_tool_kinds.items():
        if kind != 'skill':
            continue
        stub_src = PRIVATE_SKILLS_DIR / t / 'SKILL.md'
        skill_dir = claude_dir / 'skills' / t
        skill_dir.mkdir(parents=True, exist_ok=True)
        stub_path = skill_dir / 'SKILL.md'
        if stub_path.exists() and not args.force and existing_consumer is None:
            print(f"  skip   {stub_path} exists (use --force to overwrite)")
            continue
        write_utf8(stub_path, materialize_skill_stub(stub_src))
        print(f"  wrote  {stub_path}")

    # --- 4. project_progress.md skeleton (continuity only) -----------------------------------
    # progress_pre_clean (design\connect_project_commit_gate.md addendum): captured BEFORE either
    # branch below touches project_progress.md, since it's not wholly hub-owned like the rest of
    # what step 6c commits - only safe to auto-commit later when this path's own working tree was
    # already clean immediately before this run's edit (so the post-edit diff is guaranteed to be
    # exactly this run's own addition, never a user's unrelated in-progress edit swept in).
    # Defaults False when continuity is off, since nothing was touched to (safely) commit.
    progress_pre_clean = False
    if not args.no_continuity:
        progress_path = target_path / 'project_progress.md'
        progress_pre_clean = path_is_clean(target_path, 'project_progress.md')
        # Per-file principle reframe (design\connect_disconnect.md): gated on progress_path's OWN
        # presence alone, not on is_adoption - present always preserves + notes (Principle B, no
        # --force override escape hatch here, a deliberate behavior narrowing versus the old
        # is_adoption-only condition); absent always builds the skeleton (Principle A). Wording is
        # tri-state and purely cosmetic.
        if progress_path.exists():
            if is_reconnect:
                note_text = ("Reconnected via the tower_crane platform (`scripts/new_consumer.py`'s "
                              "reconnect branch): re-added the live Tower Crane In Use / Shared "
                              "Workflow Protocol sections, no ticket round-trip needed.")
            elif is_adoption:
                note_text = ("Migrated onto the tower_crane platform (`scripts/new_consumer.py`'s "
                              "adoption branch - register.md's former target case): replaced pasted "
                              "workflow prose with `@import` lines, no ticket round-trip needed.")
            else:
                note_text = ("Re-scaffolded via `scripts/new_consumer.py` - existing "
                              "`project_progress.md` content preserved as-is.")
            # Insert right after the "## Work Log" heading (newest-first convention); if that
            # heading is missing (an unusual pre-existing file), fall back to appending a new
            # section rather than guessing at unfamiliar structure.
            note = f"### {scaffold_date}\n{note_text}\n\n"
            text = progress_path.read_text(encoding='utf-8')
            marker = '## Work Log'
            idx = text.find(marker)
            if idx != -1:
                nl = text.find('\n', idx)
                insert_at = nl + 1 if nl != -1 else len(text)
                # skip a following blank line so the note lands immediately under the heading
                while insert_at < len(text) and text[insert_at] == '\n':
                    insert_at += 1
                text = text[:insert_at] + note + text[insert_at:]
            else:
                text = text.rstrip('\n') + '\n\n## Work Log\n' + note
            write_utf8(progress_path, text)
            print(f"  updated {progress_path} (prepended dated note to Work Log)")
        else:
            status_line = (f"_Migrated onto tower_crane {scaffold_date} via "
                            "`scripts/new_consumer.py`'s adoption branch. Fill in on the next "
                            "working session._" if is_adoption else
                            f"_New project scaffolded {scaffold_date}. Fill this in on the first "
                            "working session._")
            work_log_line = (f"Migrated onto the tower_crane platform (`scripts/new_consumer.py`'s "
                              "adoption branch): replaced pasted workflow prose with `@import` "
                              "lines. Registered in the shared consumer registry." if is_adoption else
                              "Project scaffolded from tower_crane (`scripts/new_consumer.py`): "
                              "`.claude/settings.json`, `CLAUDE.md` with protocol imports, this "
                              "file, and `FIRST_RUN.md`. Registered in the shared consumer registry.")
            progress = f"""# Project Progress

## Current Status
{status_line}

## Next Up
- [ ] Complete the `FIRST_RUN.md` checklist (git init, accept import dialog, fill overview).

## Decisions
| Item | Status | Notes |
|---|---|---|

## Work Log (newest first - say "archive" anytime to move old, settled entries into project_progress_archive.md)
### {scaffold_date}
{work_log_line}
"""
            write_utf8(progress_path, progress)
            print(f"  wrote  {progress_path}")

    # --- 5. FIRST_RUN.md (brand-new + reconnect only; never for host-merge) --------------------
    if existing_consumer is not None:
        # design\consumer_reconnect.md: an already-registered consumer connecting a host was never
        # a "first run" - its checklist (git init, fill in the overview placeholder) doesn't apply
        # to a project that already has real history and a real overview. A one-line reminder
        # replaces the file; FIRST_RUN.md is never (re)written in this branch.
        if not (target_path / '.git').exists():
            print(f"  note   no .git\\ found at {target_path} - run `git init` (or finish cloning) "
                  "before your first session here. Setup changes are waiting there uncommitted "
                  "until then (design\\connect_project_commit_gate.md).")
            remaining_checklist = ["- [ ] `git init` (or finish cloning), then commit the setup "
                                    "changes this run made."]
        remaining_checklist = (remaining_checklist or []) + [
            "- [ ] Open the project in a fresh Claude Code session and accept the CLAUDE.md "
            "import-approval dialog if prompted (this machine hasn't opened it before)."]
    else:
        # Checklist is built from actually-detected state, not assumed from scratch
        # (design\connect_disconnect.md "Reconnect-after-disconnect gap") - a reconnecting project (real
        # history) or a never-connected one someone already set up by hand may already have git
        # and/or a remote. needs_overview asks CLAUDE.md's own pre-run existence directly
        # (claude_md_existed), not the is_reconnect/is_adoption flags alone (per-file principle
        # reframe, design\connect_disconnect.md) - is_reconnect can be True purely from the notes
        # file surviving even when CLAUDE.md itself is genuinely gone, in which case a real
        # overview WAS lost and this checklist line must still appear.
        has_git, remote = detect_git_state(target_path)
        first_run_path = target_path / FIRST_RUN_FILENAME
        if first_run_path.exists() and not args.force:
            print("  skip   FIRST_RUN.md exists (use --force to overwrite)")
            remaining_checklist = ["- [ ] (see the existing `FIRST_RUN.md` - not overwritten this run)"]
        else:
            needs_overview = not (claude_md_existed and (is_reconnect or is_adoption))
            checklist = build_first_run_checklist(has_git, remote, needs_overview)
            remaining_checklist = checklist
            if is_reconnect:
                heading = "Reconnected via tower_crane on"
            elif is_adoption:
                heading = "Adopted onto tower_crane on"
            else:
                heading = "Scaffolded from tower_crane on"
            first_run = (
                f"# First Run - one-time setup for {project_name}\n\n"
                f"{heading} {scaffold_date}. Do these once, then delete this file.\n\n"
                + '\n'.join(checklist) + '\n'
            )
            write_utf8(first_run_path, first_run)
            print(f"  wrote  {first_run_path}")

    # --- 6a. registry entry --------------------------------------------------------------------
    if not tools:
        opted_in_yaml = 'opted_in: []'
    else:
        opted_in_yaml = 'opted_in:\n' + '\n'.join(f"  - tool: {t}\n    since: {scaffold_date}" for t in tools)
    imported_yaml = 'imported:\n' + '\n'.join(f"  - piece: {p}\n    since: {scaffold_date}" for p in import_pieces)
    if not private_tools:
        private_opted_in_yaml = 'private_opted_in: []'
    else:
        private_opted_in_yaml = 'private_opted_in:\n' + '\n'.join(
            f"  - tool: {t}\n    since: {scaffold_date}" for t in private_tools)

    registry_path_forward_slash = str(target_path).replace('\\', '/')

    if existing_consumer is not None:
        if already_connected_here:
            print(f"  skip   {registry_path} already has a hosts.{config['host_id']} entry - nothing to merge.")
        else:
            raw = registry_path.read_text(encoding='utf-8')
            new_raw, was_present, host_count = registry_lib.add_host_to_text(
                raw, config['host_id'], registry_path_forward_slash, scaffold_date)
            # Backfill remote: (design\consumer_reconnect.md) if this consumer predates the field
            # and this machine's own clone can supply it - seed-once, never overwrites a value
            # that's already there.
            if not existing_consumer.get('remote'):
                captured_remote = try_capture_remote(target_path)
                if captured_remote:
                    new_raw, remote_added = registry_lib.set_remote_if_absent(new_raw, captured_remote)
                    if remote_added:
                        print(f"  note   backfilled remote: {captured_remote}")
            write_utf8(registry_path, new_raw)
            floor_note = ", scope -> multi_machine (2-host floor)" if host_count >= 2 else ""
            print(f"  wrote  {registry_path} (added hosts.{config['host_id']}, now {host_count} host(s){floor_note})")
    else:
        captured_remote = try_capture_remote(target_path)
        remote_line = f"remote: {captured_remote}\n" if captured_remote else ""
        hosts_yaml = registry_lib.format_hosts_block(
            {config['host_id']: {'path': registry_path_forward_slash, 'registered': scaffold_date}})
        registry = f"""# {project_name}

```yaml
name: {project_name}
scope: {args.scope}
{remote_line}{hosts_yaml}
owner: {config['identity']['git_user_name']}
registered: {recovered_registered_date or scaffold_date}
{opted_in_yaml}
{imported_yaml}
{private_opted_in_yaml}
```

Notes: scaffolded by `scripts/new_consumer.py` on {scaffold_date}. Registry format is documented in
`consumers/<slug>.md` (the machine-readable block the scaffolder writes and
`check_tower_crane.py` reads).
"""
        write_utf8(registry_path, registry)
        print(f"  wrote  {registry_path}")

    # --- 6b. commit the registry write into the outer hub repo itself, now, not left for a later
    # optional `checkpoint` (design\grt_connectivity_audit.md item (i)): the registry is
    # functionality-critical state (check_tower_crane.py / every host's own resume reads it for a
    # correct answer), not user work-in-progress - skipped entirely when already_connected_here
    # left the registry file untouched above.
    if not (existing_consumer is not None and already_connected_here):
        registry_commit_msg = (
            f"Registry: connect '{slug}' (host: {config['host_id']})" if existing_consumer is None
            else f"Registry: add host '{config['host_id']}' to '{slug}'")
        registry_commit_result = commit_hub_changes(
            PROJECT_ROOT, [f"consumers/{slug}.md"], registry_commit_msg, log=print)
        registry_commit_labels = {
            'committed-pushed': f"  [git] {registry_path.name} committed and pushed in tower_crane's own outer repo.",
            'committed-no-remote': f"  [git] {registry_path.name} committed in tower_crane's own outer repo (no origin remote to push to).",
        }
        label = registry_commit_labels.get(registry_commit_result)
        if label:
            print(label)

    # --- 6c. commit into the consumer's OWN repo, now (design\connect_project_commit_gate.md):
    # extends 6b's "commit at the point of mutation" principle one level further, to the
    # consumer-repo side of the connect family - disconnect_consumer.py already does this via the
    # same commit_consumer_changes() helper; this closes the missing other half of that pair.
    # Gated on is_new_connection, same as 6b - an already-connected host re-scaffolding itself
    # gets no new automatic commit here, matching 6b's registry-commit skip for that case.
    # Safe exactly when has_git (a real repo exists to commit into) AND not needs_overview (the
    # content being committed is real, not a still-needed placeholder) both hold - two
    # independently-100%-reliable checks, no branch-identity logic needed. Host-merge never
    # computes needs_overview at all (content is always real there by construction - the
    # consumer's own project already exists), so its effective gate is just has_git.
    # CONSUMER_OWNED_PATHS (committed below) now includes FIRST_RUN_FILENAME - wholly hub-owned,
    # same as everything else there. project_progress.md is NOT in that tuple (not wholly
    # hub-owned) and gets its own separate, narrower commit further down, gated additionally on
    # progress_pre_clean (design\connect_project_commit_gate.md's addendum).
    if is_new_connection:
        has_git_now = (target_path / '.git').exists()
        if existing_consumer is not None:
            needs_overview_now = False
            commit_msg = f"Tower Crane: connected via 'connect project' (host: {config['host_id']})"
        else:
            needs_overview_now = not (claude_md_existed and (is_reconnect or is_adoption))
            commit_msg = ("Tower Crane: reconnected via 'connect project'" if is_reconnect
                          else "Tower Crane: connected via 'connect project'")

        if has_git_now and not needs_overview_now:
            result = commit_consumer_changes(
                target_path, commit_msg, log=print, config=config,
                imports=import_pieces, shared_root=SHARED_ROOT)
            consumer_commit_result = result
            commit_labels = {
                'not-a-repo': None,  # has_git_now already guards this case
                'noop': None,
                'committed-pushed': "  [git] committed and pushed in this consumer's own repo.",
                'committed-no-remote': "  [git] committed in this consumer's own repo (no origin remote to push to).",
                'commit-failed': None,  # commit_consumer_changes() already logged the warn line itself
                'push-failed': None,
                'reconciled-pushed': "  [git] push conflict auto-reconciled (reset + regenerated), committed and pushed.",
            }
            label = commit_labels.get(result)
            if label:
                print(label)

            # project_progress.md's dated note (design\connect_project_commit_gate.md addendum):
            # a separate, narrower commit on purpose - see commit_consumer_progress_note()'s own
            # docstring for why it's never folded into the commit above. Gated the same as that
            # commit (has_git_now and not needs_overview_now) PLUS progress_pre_clean, captured at
            # step 4 immediately before the note was prepended - withheld whenever the user had
            # their own unrelated uncommitted edit to that file already sitting there.
            if progress_pre_clean:
                progress_result = commit_consumer_progress_note(
                    target_path, commit_msg, log=print)
                progress_commit_result = progress_result
                progress_labels = {
                    'committed-pushed': "  [git] project_progress.md's note committed and pushed in this consumer's own repo.",
                    'committed-no-remote': "  [git] project_progress.md's note committed in this consumer's own repo (no origin remote to push to).",
                }
                progress_label = progress_labels.get(progress_result)
                if progress_label:
                    print(progress_label)
        elif has_git_now and needs_overview_now:
            # Gate correctly withholds: real git history may exist, but the content this run
            # wrote (or the pre-existing CLAUDE.md itself) still carries an unfilled overview
            # placeholder. Never framed as a warning - nothing is wrong, just deferred to the
            # user's own next action in that project (FIRST_RUN.md's checklist already produces a
            # covering commit as a side effect once completed).
            print(f"  note   {project_name}'s setup changes are uncommitted - completing "
                  "FIRST_RUN.md there finishes that.")

    # --- 7. next steps -------------------------------------------------------------------------
    # Branched, not one-size-fits-all: the import-approval dialog is a Claude Code trust decision
    # keyed per project-directory-per-machine, not something this script can guarantee will fire
    # (design\multi_machine_hub.md:104, design\consumer_platform.md "one-time...per consumer") -
    # every branch below hedges with "if prompted" rather than stating it as a flat requirement.
    print()
    if existing_consumer is not None and already_connected_here:
        # No-op re-run against a host already connected: nothing changed, nothing to open.
        print("Done. Nothing new to do - this host was already connected.")
    elif existing_consumer is not None:
        # Host-merge (genuinely new host joining an already-registered consumer): FIRST_RUN.md is
        # never written for this branch (step 5 above) - don't tell the user to complete a file
        # that doesn't exist. This machine has never opened this project path before, so the
        # dialog is the likely-but-not-guaranteed first-launch step here.
        print("Done. Next steps:")
        print(f"  1. Open {target_path} in a fresh Claude Code session and accept the")
        print("     CLAUDE.md import-approval dialog if prompted (this machine hasn't opened")
        print("     this project before).")
    else:
        print("Done. Next steps:")
        print(f"  1. Open {target_path} in a fresh Claude Code session and complete FIRST_RUN.md")
        print("     (git init, accept the CLAUDE.md import-approval dialog if prompted, fill the")
        print("     CLAUDE.md overview).")

    # --- 8. close-out summary ---------------------------------------------------------------
    print_close_out_summary(
        project_name, target_path, existing_consumer, already_connected_here, is_reconnect,
        is_adoption, consumer_commit_result, progress_commit_result, registry_commit_result,
        remaining_checklist)


if __name__ == '__main__':
    main()
