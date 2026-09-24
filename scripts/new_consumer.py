#!/usr/bin/env python3
"""
new_consumer.py - scaffold a new tower_crane consumer project, deterministic, non-interactive.

Creates ALL files a new consumer needs:
  <target>/.claude/settings.json   - opt-in hook snippet(s) for the chosen tools (merged)
  <target>/CLAUDE.md               - from templates/consumer_CLAUDE.md.tmpl, with @import lines
  <target>/README.md               - from templates/consumer_README.md.tmpl, once, if absent
                                     (project narrative - CLAUDE.md stays directives-only)
  <target>/.claude/skills/<name>/  - Track-1 skill stub(s) for toolkit-governed pieces in
                                     SKILL_PIECES plus every STANDALONE_SKILLS entry
  <target>/project_progress.md      - continuity skeleton (only when continuity is on)
  consumers/<slug>.md               - registry entry (this repo)

consumers/<slug>.md is the ONLY place a project name is recorded - it lives in the outer, private
hub repo, never in toolkit\\ itself, which tracks the public konvesdigital/tower-crane repo.

Recognized existing-CLAUDE.md shapes, each handled non-destructively (see the "CLAUDE.md from
template" section below): a registered consumer connecting another host (host-merge, patches
@import lines only), a disconnected project reconnecting (strips the DISCONNECTED_HEADING marker,
re-appends the live sections), and an unregistered hand-copied project with no Tower Crane content
at all (adoption - appends the live sections to whatever's already there).

What's still left for the user on this machine is reported by readiness.py at the end of the run
(and again at every `resume`) - no static checklist file is written.

--dry-run still writes every <target> file above, but writes nothing in the hub (the registry
entry is printed, not written) and runs no git clone/pull/commit/push in either repo.

Generated files (settings.json, CLAUDE.md, README.md, project_progress.md, registry entry) use LF line endings universally.
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import readiness
from config_lib import (
    get_shared_config, get_expanded_optin, materialize_skill_stub,
    build_new_cmd_map, apply_hook_command_fixes, print_diagnose_inline,
    TC_IN_USE_HEADING, WORKFLOW_HEADING, DISCONNECTED_HEADING, DISCONNECT_NOTES_FILENAME,
    CONSUMER_OWNED_PATHS,
    HUB_POINTER_IMPORT_LINE, HUB_POINTER_RELPATH, HUB_DISPATCH_RELPATH, HUB_DISPATCH_TEMPLATE,
    get_dispatch_optin, build_hub_pointer_content, build_dispatch_cmd_map,
    write_new_connection_files, collapse_imports_to_pointer, fix_imports, commit_hub_changes,
    commit_consumer_changes, path_is_clean, commit_consumer_progress_note, scoped_status_paths,
    sync_consumer_repo, merge_bash_allowlist,
)
import registry_lib

SHARED_ROOT = Path(__file__).resolve().parent.parent
# consumers\ is private hub state, not shipped toolkit content - it lives at the outer root
# (the outer/inner repo split), one level above SHARED_ROOT (toolkit\).
PROJECT_ROOT = SHARED_ROOT.parent
TEMPLATES_DIR = SHARED_ROOT / 'templates'
OPTINS_DIR = TEMPLATES_DIR / 'optins'
CONSUMERS_DIR = PROJECT_ROOT / 'consumers'
TMPL_PATH = TEMPLATES_DIR / 'consumer_CLAUDE.md.tmpl'
README_TMPL_PATH = TEMPLATES_DIR / 'consumer_README.md.tmpl'
# Private, automatic tools living outside toolkit\, never shipped.
PRIVATE_ROOT = PROJECT_ROOT / 'toolkit_private'
PRIVATE_OPTINS_DIR = PRIVATE_ROOT / 'templates' / 'optins'
PRIVATE_SKILLS_DIR = PRIVATE_ROOT / 'templates' / 'skills'

# short human blurb per known tool for the "Tower Crane In Use" list (falls back to the name)
TOOL_BLURBS = {
    'consistency_check': 'AST static analysis on Python writes/edits - undefined names, arg-count, '
                          'string-key spelling (PostToolUse hook).',
}

# The "Adopted Shared Resources" subsection's general paragraph is fixed template text, shipped
# with every scaffold. This fallback is only the "what's been adopted" LISTING underneath it,
# which shared_resources.md's Apply/Forget procedures own from the first real adoption onward.
ADOPTED_SHARED_RESOURCES_NONE = '**Shared resources adopted for this project:** _None yet._'

# Toolkit-governed Track-1 skill pieces: a piece name in here is scaffolded as one or more
# project-local skill stubs (each sourced from templates/skills/<skill>/SKILL.md) plus a
# still-@imported Track-2 "resume check" companion, instead of a flat @import <name>.md.
# compliance stays flat.
SKILL_PIECES = {
    'filing': {'companion': 'filing_resume_check', 'skills': ['filing']},
    'continuity': {'companion': 'continuity_resume_check', 'skills': ['checkpoint', 'archive']},
    'shared_resources': {'companion': 'shared_resources_resume_check', 'skills': ['shared_resources']},
}

# Standalone Track-1 skills with no @import companion: scaffolded for every new consumer
# unconditionally, alongside the SKILL_PIECES protocol pieces above.
STANDALONE_SKILLS = ['update', 'commands', 'capability_relationships']


def write_utf8(path, content):
    path.write_text(content, encoding='utf-8', newline='\n')


def get_slug(name):
    s = name.lower().strip()
    s = re.sub(r'[^a-z0-9]+', '_', s)
    s = re.sub(r'^_+|_+$', '', s)
    return s


def try_capture_remote(target_path):
    """Best-effort `git remote get-url origin` from target_path's own clone, or None if there's
    no .git\\ yet, no `origin` remote, or git isn't available."""
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
    history - fallback when the notes file doesn't carry the field. Returns None on any failure
    (no git, empty history, never registered, shallow clone) - never raises."""
    try:
        proc = subprocess.run(
            ['git', '-C', str(PROJECT_ROOT), 'log', '--format=%ci', '--', f'consumers/{slug}.md'],
            capture_output=True, text=True)
    except OSError:
        return None
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    return proc.stdout.strip().splitlines()[-1][:10]  # oldest is last (git log is newest-first)


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
                             progress_commit_result, registry_commit_result, dry_run=False):
    """One block, printed once at the end of the run, from the classification/commit-result
    variables main() already computed. "Left uncommitted" re-checks git directly rather than
    being sourced from an already-known variable."""
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
    elif dry_run:
        print("Registered in the hub's own registry: no (dry run - readiness below reports it missing).")

    remaining = readiness.format_lines(readiness.check(target_path), indent='  ')
    if remaining:
        print("Remaining on this machine (readiness.py - `resume` re-checks this every session):")
        for line in remaining:
            print(line)
    else:
        print("Readiness: nothing left to do on this machine.")


def main():
    parser = argparse.ArgumentParser(description="Scaffold a new tower_crane consumer project.")
    parser.add_argument('--target-path', required=True, help="Absolute path to the new consumer's project root.")
    parser.add_argument('--project-name', required=True, help='Full title in Title Case (e.g. "My Cool Project").')
    parser.add_argument('--tools', nargs='*', default=['consistency_check', 'shared_resources_trigger_match'],
                         help="Tools to opt into (each needs templates/optins/<tool>.json). Pass --tools with no "
                              "values for a consumer with no hooks. Default: consistency_check, "
                              "shared_resources_trigger_match (rides along with the shared_resources protocol "
                              "piece, which every consumer gets unconditionally).")
    parser.add_argument('--private-tools', nargs='*', default=[],
                         help="Private tools to opt into - each needs either "
                              "toolkit_private/templates/optins/<name>.json (hook) or "
                              "toolkit_private/templates/skills/<name>/SKILL.md (Track-1 skill). Default: none.")
    parser.add_argument('--no-continuity', action='store_true',
                         help="Opt out of the (default-on) continuity protocol piece. filing + compliance + "
                              "shared_resources are always imported.")
    parser.add_argument('--date', default=None, help="Scaffold date (YYYY-MM-DD). Defaults to today.")
    parser.add_argument('--scope', choices=['local', 'multi_machine'], default='local',
                         help="'local' (default) if this consumer should live on "
                              "only this machine, 'multi_machine' to declare it available to all connected "
                              "machines immediately (so other hosts' resume can nudge about connecting it too). "
                              "Only meaningful for a BRAND NEW registry entry - connecting an already-registered "
                              "consumer's 2nd host always sets multi_machine automatically (the 2-host floor), "
                              "regardless of this flag.")
    parser.add_argument('--force', action='store_true',
                         help="Overwrite an existing CLAUDE.md / project_progress.md. Never "
                              "applies to an already-registered consumer's registry file - a slug collision "
                              "there always routes into an additive host-merge (the locked "
                              "slug-collision routing), never a blind overwrite.")
    parser.add_argument('--no-clone', action='store_true',
                         help="When connecting an already-registered consumer to "
                              "an empty target folder and its registry has a remote: on record, the default is "
                              "to `git clone` it before scaffolding. Pass this to scaffold a blank folder instead.")
    parser.add_argument('--dry-run', action='store_true',
                         help="Scaffold the target folder's files as normal, but write nothing in the hub "
                              "(registry entry printed, not written) and run no git clone/pull/commit/push "
                              "in either repo. The target folder IS written - point it at a scratch folder.")
    args = parser.parse_args()

    target_path = Path(args.target_path)
    project_name = args.project_name
    tools = args.tools
    private_tools = args.private_tools
    scaffold_date = args.date or date.today().isoformat()

    # Close-out summary state, threaded out here so step 8 can report it directly.
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

    # An already-registered consumer is never an error and never a --force overwrite target - it
    # always routes into an additive host-merge below (step 6a).
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

    # A "new connection" is any brand-new consumer, reconnect, adoption, or a genuinely NEW host
    # joining an already-registered consumer - every one of those gets the new
    # hub_pointer.md/_hub_dispatch.py indirection. A host that's ALREADY connected is excluded, so
    # it keeps its existing direct-path behavior untouched.
    is_new_connection = existing_consumer is None or not already_connected_here

    # Blank-folder bootstrap: connecting an already-registered consumer whose target folder is
    # empty and whose registry carries a remote: clone before any scaffolding touches the folder.
    # Once cloned, the folder falls through to the same file-existence-keyed patch logic below.
    if existing_consumer is not None and not already_connected_here and not args.no_clone:
        remote = existing_consumer.get('remote')
        folder_empty = not target_path.exists() or (target_path.is_dir() and not any(target_path.iterdir()))
        if remote and folder_empty and args.dry_run:
            print(f"  [dry-run] would git clone {remote} {target_path} - scaffolding the empty folder instead")
        elif remote and folder_empty:
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

    # Pull target_path's own repo current before any of the read-and-patch-in-place steps below.
    # No-op for a brand-new scaffold (no .git yet) or a folder just cloned above.
    if target_path.exists() and not args.dry_run:
        sync_consumer_repo(target_path, log=print)

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

    # The piece names actually @imported into CLAUDE.md - a SKILL_PIECES entry substitutes its
    # companion; everything else imports itself directly.
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
    # Written before settings.json below, since that step's tool-merge loop needs
    # is_new_connection decidable to choose get_dispatch_optin() over get_expanded_optin().
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
        # A new connection gets the dispatch-wrapper command form; an already-connected host's
        # re-scaffold keeps its direct-path form untouched.
        if is_new_connection:
            return get_dispatch_optin(Path(optins_dir) / f"{tool_name}.json", tool_name, config)
        return get_expanded_optin(Path(optins_dir) / f"{tool_name}.json", config)

    if settings_existed and existing_consumer is not None:
        # host-merge branch: repoint any already-present hook command for tools the registry
        # already lists as opted-in, reusing relocate.py's own regeneration.
        existing_tool_names = [o['name'] for o in existing_consumer['opted_in']]
        existing_private_names = [o['name'] for o in existing_consumer['private_opted_in']]
        if is_new_connection:
            # A genuinely new host joining an already-registered consumer gets the
            # dispatch-wrapper command form here too - one command shape per settings.json.
            stale_cmd = build_dispatch_cmd_map(existing_tool_names, existing_private_names, config, OPTINS_DIR, PRIVATE_OPTINS_DIR)
        else:
            stale_cmd = build_new_cmd_map(existing_tool_names, existing_private_names, config, OPTINS_DIR, PRIVATE_OPTINS_DIR)
        if apply_hook_command_fixes(settings, stale_cmd, existing_tool_names + existing_private_names,
                                     dry_run=False, log=print, needs_shell=is_new_connection):
            print(f"  patched stale hook command(s) in {settings_path}")

    # Every consumer reads canonical Track-1 skill/resume-check content straight out of
    # toolkit\templates, which is outside the project root - without an allow rule every such
    # read prompts.
    allow_list = settings.setdefault('permissions', {}).setdefault('allow', [])
    read_rule = f"Read({import_base}/**)"
    if read_rule not in allow_list:
        allow_list.append(read_rule)
    merge_bash_allowlist(settings, 'consumer')

    for t in tools:
        # Expand config placeholders into the concrete command - dispatch-wrapper form for a new
        # connection, direct-path form otherwise.
        optin = _get_optin(OPTINS_DIR, t)
        if 'hooks' in optin:
            for evt, groups in optin['hooks'].items():
                existing = settings['hooks'].setdefault(evt, [])
                # dedupe so re-running the scaffolder (--force) doesn't append the same hook twice
                existing_json = [json.dumps(e, separators=(',', ':')) for e in existing]
                for entry in groups:
                    entry_json = json.dumps(entry, separators=(',', ':'))
                    if entry_json not in existing_json:
                        existing.append(entry)

    for t, kind in private_tool_kinds.items():
        if kind != 'hook':
            continue
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
    # A new connection gets the single, host-invariant indirection line.
    protocol_imports = HUB_POINTER_IMPORT_LINE if is_new_connection else '\n'.join(
        f"@{import_base}/{p}.md" for p in import_pieces)

    # claude_md_existed is captured once, before any write, and is the signal other steps below
    # consult about CLAUDE.md's prior state - never is_reconnect/is_adoption themselves, which can
    # be True even when CLAUDE.md itself doesn't exist.
    claude_md_existed = claude_md_path.exists()
    notes_path = target_path / DISCONNECT_NOTES_FILENAME
    notes_existed = notes_path.exists()

    # Reconnect detection: a previously disconnected project has no registry entry (same as brand
    # new) but either still carries the DISCONNECTED_HEADING pointer in CLAUDE.md, or - if that
    # marker was hand-removed - the surviving TOWER_CRANE_DISCONNECT_NOTES.md is itself evidence
    # of a prior connection.
    is_reconnect = False
    if existing_consumer is None:
        has_marker = claude_md_existed and DISCONNECTED_HEADING in claude_md_path.read_text(encoding='utf-8')
        is_reconnect = has_marker or notes_existed

    # Adoption detection: an existing hand-copied project that was never put through
    # new_consumer.py has a CLAUDE.md with no TC_IN_USE_HEADING and no protocol-piece @import
    # line.
    is_adoption = False
    if claude_md_path.exists() and existing_consumer is None and not is_reconnect:
        existing_text = claude_md_path.read_text(encoding='utf-8')
        has_import_line = bool(re.search(
            r'(?m)^@\S+/(filing_resume_check|compliance|shared_resources_resume_check|'
            r'continuity_resume_check)\.md\s*$', existing_text))
        is_adoption = TC_IN_USE_HEADING not in existing_text and not has_import_line

    if claude_md_path.exists() and existing_consumer is not None and not is_new_connection:
        # already-connected-here re-scaffold: patch only the @import lines in place via
        # relocate.py's fix_imports(). The project overview and everything else in CLAUDE.md is
        # left untouched.
        if fix_imports(target_path, import_pieces, import_base, dry_run=False, log=print):
            print(f"  patched {claude_md_path} (@import lines only)")
        else:
            print(f"  skip   {claude_md_path} already current (@import lines match)")
    elif claude_md_path.exists() and existing_consumer is not None and is_new_connection:
        # host-merge branch, genuinely new host: collapse whatever direct-form @import lines are
        # already present into the single host-invariant pointer line - this host's own
        # hub_pointer.md (written above) resolves it. A piece with no existing line just isn't
        # found.
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
        # live sections (TC_IN_USE_HEADING onward).
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
                          .replace('{{ADOPTED_SHARED_RESOURCES}}', ADOPTED_SHARED_RESOURCES_NONE)
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
                     .replace('{{ADOPTED_SHARED_RESOURCES}}', ADOPTED_SHARED_RESOURCES_NONE)
                     .replace('{{PROTOCOL_IMPORTS}}', protocol_imports))
        write_utf8(claude_md_path, claude_md)
        print(f"  wrote  {claude_md_path}")

    # --- 3a. recover original registered: date on reconnect, then clean up the stale notes file --
    # Per-file principle reframe: TOWER_CRANE_DISCONNECT_NOTES.md
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

    # --- 3d. private skill stubs (copy-only, no {{IMPORT_BASE}}) ----
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

    # --- 3e. README.md (narrative skeleton, written once if absent) -------------------------
    # No Tower-Crane-owned markers to preserve here (unlike CLAUDE.md's TC_IN_USE_HEADING dance) -
    # every branch (brand-new/reconnect/adoption/host-merge) reduces to one check: write it if
    # absent, otherwise leave whatever's there (a user's own narrative, or an inherited unrelated
    # README predating Tower Crane) untouched. readme_written feeds needs_overview below, since a
    # fresh README also introduces an unfilled placeholder even when CLAUDE.md's own content is
    # already real (reconnect/adoption).
    readme_path = target_path / 'README.md'
    readme_written = False
    if readme_path.exists():
        print(f"  skip   {readme_path} exists (not touched - narrative content is yours)")
    else:
        readme_tmpl = README_TMPL_PATH.read_text(encoding='utf-8')
        readme_tmpl = re.sub(r'^\s*<!--.*?-->\s*', '', readme_tmpl, count=1, flags=re.DOTALL)
        readme_content = readme_tmpl.replace('{{PROJECT_NAME}}', project_name)
        write_utf8(readme_path, readme_content)
        print(f"  wrote  {readme_path}")
        readme_written = True

    # --- 4. project_progress.md skeleton (continuity only) -----------------------------------
    # progress_pre_clean: captured BEFORE either
    # branch below touches project_progress.md, since it's not wholly hub-owned like the rest of
    # what step 6c commits - only safe to auto-commit later when this path's own working tree was
    # already clean immediately before this run's edit (so the post-edit diff is guaranteed to be
    # exactly this run's own addition, never a user's unrelated in-progress edit swept in).
    # Defaults False when continuity is off, since nothing was touched to (safely) commit.
    progress_pre_clean = False
    if not args.no_continuity:
        progress_path = target_path / 'project_progress.md'
        progress_pre_clean = path_is_clean(target_path, 'project_progress.md')
        # Per-file principle reframe: gated on progress_path's OWN
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
                              "file. Registered in the shared consumer registry.")
            progress = f"""# Project Progress

## Current Status
{status_line}

## Next Up
- [ ] Resolve anything `resume`'s readiness check reports ([TODO] lines: git, import approval, overview).

## Decisions
| Item | Status | Notes |
|---|---|---|

## Work Log (newest first - say "archive" anytime to move old, settled entries into project_progress_archive.md)
### {scaffold_date}
{work_log_line}
"""
            write_utf8(progress_path, progress)
            print(f"  wrote  {progress_path}")

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
            # Backfill remote: if this consumer predates the field
            # and this machine's own clone can supply it - seed-once, never overwrites a value
            # that's already there.
            if not existing_consumer.get('remote'):
                captured_remote = try_capture_remote(target_path)
                if captured_remote:
                    new_raw, remote_added = registry_lib.set_remote_if_absent(new_raw, captured_remote)
                    if remote_added:
                        print(f"  note   backfilled remote: {captured_remote}")
            if args.dry_run:
                print(f"  [dry-run] would write {registry_path}:")
                print(new_raw)
            else:
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
        if args.dry_run:
            print(f"  [dry-run] would write {registry_path}:")
            print(registry)
        else:
            write_utf8(registry_path, registry)
            print(f"  wrote  {registry_path}")

    # --- 6b. commit the registry write into the outer hub repo itself, now, not left for a later
    # optional `checkpoint`: the registry is
    # functionality-critical state (check_tower_crane.py / every host's own resume reads it for a
    # correct answer), not user work-in-progress - skipped entirely when already_connected_here
    # left the registry file untouched above.
    if args.dry_run:
        print("  [dry-run] skipped registry commit/push and consumer-repo commit(s)")
    elif not (existing_consumer is not None and already_connected_here):
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

    # --- 6c. commit into the consumer's OWN repo, now:
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
    # CONSUMER_OWNED_PATHS (committed below) still includes FIRST_RUN_FILENAME so a legacy file's
    # deletion commits cleanly. project_progress.md is NOT in that tuple (not wholly
    # hub-owned) and gets its own separate, narrower commit further down, gated additionally on
    # progress_pre_clean.
    if is_new_connection and not args.dry_run:
        has_git_now = (target_path / '.git').exists()
        if existing_consumer is not None:
            needs_overview_now = readme_written
            commit_msg = f"Tower Crane: connected via 'connect project' (host: {config['host_id']})"
        else:
            needs_overview_now = not (claude_md_existed and (is_reconnect or is_adoption)) or readme_written
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

            # project_progress.md's dated note:
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
            # placeholder. Never framed as a warning - deferred to the user; readiness.py reports
            # both the placeholder and the uncommitted files until they're done.
            print(f"  note   {project_name}'s setup changes are uncommitted until the overview "
                  "placeholder is filled in - see the readiness lines below.")

    # --- 7. next steps -------------------------------------------------------------------------
    print()
    if existing_consumer is not None and already_connected_here:
        print("Done. Nothing new to do - this host was already connected.")
    else:
        print(f"Done. Next: open {target_path} in a fresh Claude Code session and say `resume` -")
        print("its readiness check reports anything still left (also listed below).")

    # --- 8. close-out summary ---------------------------------------------------------------
    print_close_out_summary(
        project_name, target_path, existing_consumer, already_connected_here, is_reconnect,
        is_adoption, consumer_commit_result, progress_commit_result, registry_commit_result,
        dry_run=args.dry_run)


if __name__ == '__main__':
    main()
