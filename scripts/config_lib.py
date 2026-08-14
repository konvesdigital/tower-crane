#!/usr/bin/env python3
"""
config_lib.py - shared config loader for the maintainer tools (scaffolder, checker, relocate).

Import it:  from config_lib import get_shared_config, get_expanded_optin

Provides:
  get_shared_config   - read + validate config.local.json (the per-machine, gitignored file).
  expand_optin_command / get_expanded_optin - substitute config values into an opt-in snippet's
    command templates, so scaffolder / checker / relocate all compute the SAME concrete command.

Portability foundation (design\\portability.md): the canonical opt-in snippets
(templates\\optins\\<tool>.json) carry PLACEHOLDER commands ({{PYTHON_LAUNCHER}}, {{SHARED_ROOT}});
the real machine values are injected here. This is the "config -> regenerate" seam - no
machine-specific path is committed anywhere.

shared_root / import_base are NEVER read from config.local.json as authoritative values - they
are always recomputed live from wherever this repo is actually running, so this folder can live
at any path, under any name, and moving or renaming it later can't leave either value stale (no
"conventional location" to configure or drift from). config.local.json's own 'shared_root' key
is kept only as a last-known-location marker for detecting a move (see get_shared_config), and
self-corrects automatically. python_launcher / host_id / identity / publish.* are the only
fields that genuinely differ per machine and need a human to fill them in.

OS-reach Tier 2 port of config_lib.ps1 (design\\portability.md, "OS-reach Tier 2: full
cross-platform design"). Logic is a direct translation, not a rewrite - see that doc's Build
order for the parity-check approach used to verify this against the original.
"""

import json
import os
import platform
import re
import subprocess
from pathlib import Path


def get_shared_config(shared_root=None):
    """Read config.local.json from the tower_crane repo root. Raises RuntimeError with a clear,
    actionable message if it is missing (the #1 first-run mistake) so a fresh clone gets told
    exactly what to do.

    shared_root: repo root. Callers pass their script's parent dir; defaults to this file's
                 parent (scripts\\ -> repo root) for interactive use.
    """
    if shared_root is None:
        shared_root = Path(__file__).resolve().parent.parent
    else:
        shared_root = Path(shared_root)

    local_path = shared_root / 'config.local.json'
    example_path = shared_root / 'config.example.json'
    if not local_path.exists():
        raise RuntimeError(
            f"config.local.json not found at {local_path}\n"
            "This per-machine config is gitignored - each clone creates its own. To fix:\n"
            "  1. Copy config.example.json to config.local.json\n"
            "  2. Fill in host_id / identity for THIS machine (shared_root / import_base fill\n"
            "     themselves in automatically the first time any script runs)\n"
            "  3. Re-run. (See design\\portability.md / README.md.)"
        )

    try:
        with open(local_path, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"config.local.json is not valid JSON ({local_path}): {e}")

    for req in ('python_launcher',):
        val = cfg.get(req)
        if not val or not isinstance(val, str) or val.strip() == '' or val.startswith('<'):
            raise RuntimeError(
                f"config.local.json is missing or has an unfilled placeholder for '{req}' "
                f"(see {example_path})."
            )

    # host_id is optional but recommended; default to the machine name so #1-Federate host:
    # scoping still has a value on a config that predates the field.
    host_id = cfg.get('host_id')
    if not host_id or not isinstance(host_id, str) or host_id.strip() == '' or host_id.startswith('<'):
        cfg['host_id'] = platform.node()

    # shared_root: always recomputed from where this repo is actually running - never trusted
    # from the file. config.local.json's own 'shared_root' is kept only as a last-known-location
    # marker so a move/rename is detectable; it self-corrects below rather than ever going stale
    # in a way that matters. Normalize to forward-slash before comparing: the locked path
    # convention is forward-slash always (design\portability.md, OS-reach Tier 2), but a resolved
    # path is backslash form on Windows regardless of how the config stores it.
    live_root = str(shared_root.resolve()).rstrip('\\/').replace('\\', '/')
    raw_marker = cfg.get('shared_root')
    marker = (str(raw_marker).rstrip('\\/').replace('\\', '/')
              if raw_marker and not str(raw_marker).startswith('<') else None)
    if marker and marker != live_root:
        print(f"[NOTICE] This tower_crane folder moved or was renamed since last run "
              f"(was '{marker}', now '{live_root}').")
        print("         The location marker just self-corrected - nothing broken here. But every "
              "registered")
        print("         consumer still has the OLD path baked into its hook command / @import "
              "lines, AND")
        print("         so does this hub's own outer CLAUDE.md self-import and its own self-use "
              "hooks. If")
        print("         you're an agent running this on the user's behalf: tell them, and offer "
              "to run")
        print("         scripts\\relocate.py now - it brings every consumer AND this hub's own "
              "self-import")
        print("         back in sync in one pass (self-use hooks under `self_hooks.py` are "
              "project-relative")
        print("         and don't need this - see config_lib.py's space check below for the "
              "other half of what")
        print("         broke a live session this way once already).")
    if marker != live_root:
        cfg['shared_root'] = live_root
        try:
            with open(local_path, 'w', encoding='utf-8') as f:
                json.dump(cfg, f, indent=2)
                f.write('\n')
        except OSError:
            pass  # best-effort - a read-only config just means the marker won't self-correct
    else:
        cfg['shared_root'] = live_root

    # import_base: Claude Code's @import only resolves home-relative '~/...' paths (the only form
    # ever proven to work - design\portability.md decision 7), so compute it fresh from live_root
    # every call rather than storing it. Error clearly if this repo isn't under the home directory
    # at all, since there's no other resolvable form to fall back to.
    try:
        rel = shared_root.resolve().relative_to(Path.home().resolve())
    except ValueError:
        raise RuntimeError(
            f"This tower_crane folder ({live_root}) isn't inside your home directory "
            f"({Path.home()}). Claude Code's @import only resolves home-relative '~/...' paths, "
            "so consumers' imports can't work from here - move this folder to anywhere under "
            "your home directory (any name, any depth)."
        )
    cfg['import_base'] = '~/' + str(rel).replace('\\', '/') + '/templates'

    # Claude Code's own @import parser splits on whitespace with no quoting support, so a single
    # space anywhere in this path silently kills EVERY @import line that resolves through it - no
    # error, no warning, the imported content just never loads (confirmed permanent upstream
    # limitation: github.com/anthropics/claude-code/issues/56927, closed "not planned"). This is
    # not a Tower Crane path-convention rule - the repo can live anywhere, under any name, per the
    # portability design above - it is a warning about a real Claude Code parser limitation that
    # would otherwise fail completely silently. Checked live_root only (not the '~/...' form),
    # since a space anywhere under the home directory reproduces the bug identically.
    if ' ' in live_root:
        print(f"[WARNING] This tower_crane folder's path contains a space: '{live_root}'.")
        print("          Claude Code's @import directive silently fails to load anything through "
              "a path")
        print("          containing a space - no error, no dialog, the imported file just never "
              "reaches")
        print("          context (github.com/anthropics/claude-code/issues/56927, a confirmed, "
              "permanent")
        print("          upstream limitation, closed 'not planned'). This breaks every consumer's "
              "@import")
        print("          lines AND this hub's own outer CLAUDE.md self-import, every time, "
              "completely")
        print("          silently. The only reliable fix is removing the space from this path - "
              "not moving")
        print("          to any particular location, just renaming the offending folder segment "
              "(e.g. 'My")
        print("          Folder' -> 'My_Folder'). Tower Crane still doesn't care where or what "
              "this folder")
        print("          is named otherwise - this is the one literal character its @import "
              "mechanism can't")
        print("          route around.")

    # private_root: design\private_tools.md - the private, automatic analog to shared_root, always
    # recomputed live the same way (never trusted from the file) so a move/rename can't leave it
    # stale either. Points at toolkit_private\, a sibling of this toolkit\ folder in the outer repo
    # - it may not exist yet on a fresh clone or before the first private tool is added, which is
    # fine, since it's just a path string until an opt-in snippet's {{PRIVATE_ROOT}} placeholder is
    # actually expanded against it.
    live_private_root = str(shared_root.resolve().parent / 'toolkit_private').replace('\\', '/')
    raw_private_marker = cfg.get('private_root')
    private_marker = (str(raw_private_marker).rstrip('\\/').replace('\\', '/')
                       if raw_private_marker and not str(raw_private_marker).startswith('<') else None)
    if private_marker and private_marker != live_private_root:
        print(f"[NOTICE] toolkit_private\\'s location moved along with this tower_crane folder "
              f"(was '{private_marker}', now '{live_private_root}'). Any consumer opted into a "
              "private tool needs scripts\\relocate.py to catch up, same as a public-tool move.")
    if private_marker != live_private_root:
        cfg['private_root'] = live_private_root
        try:
            with open(local_path, 'w', encoding='utf-8') as f:
                json.dump(cfg, f, indent=2)
                f.write('\n')
        except OSError:
            pass  # best-effort - a read-only config just means the marker won't self-correct
    else:
        cfg['private_root'] = live_private_root

    return cfg


def expand_optin_command(command, config):
    """Substitute config placeholders in a single command string.
      {{PYTHON_LAUNCHER}} -> config.python_launcher
      {{SHARED_ROOT}}     -> config.shared_root
      {{PRIVATE_ROOT}}    -> config.private_root (design\\private_tools.md)
    """
    return (command
            .replace('{{PYTHON_LAUNCHER}}', str(config.get('python_launcher', '')))
            .replace('{{SHARED_ROOT}}', str(config.get('shared_root', '')))
            .replace('{{PRIVATE_ROOT}}', str(config.get('private_root', ''))))


def get_expanded_optin(optin_path, config):
    """Read templates\\optins\\<tool>.json and return it as a dict with every hook command's
    placeholders resolved from config. This is the single source of truth for a consumer's
    concrete hook command - scaffolder merges it, checker drift-compares against it, relocate
    regenerates to it.
    """
    with open(optin_path, 'r', encoding='utf-8') as f:
        optin = json.load(f)
    if 'hooks' in optin:
        for evt, groups in optin['hooks'].items():
            for grp in groups:
                if 'hooks' in grp:
                    for h in grp['hooks']:
                        if 'command' in h:
                            h['command'] = expand_optin_command(h['command'], config)
    return optin


# design\consumer_reference_indirection.md: the fixed, host-invariant wrapper form of a hook
# command, used for any NEW connection (a brand-new consumer, or a not-yet-connected host joining
# an already-registered one) from this build forward. An already-connected host's existing
# settings.json keeps the direct-path form from get_expanded_optin() above untouched - no forced
# migration - so both forms must stay independently valid canonical shapes; see
# HUB_DISPATCH_RELPATH's docstring for how check_tower_crane.py's Pass B accepts either.
HUB_POINTER_RELPATH = '.claude/hub_pointer.md'
HUB_POINTER_IMPORT_LINE = f'@{HUB_POINTER_RELPATH}'
HUB_DISPATCH_RELPATH = '.claude/hooks/_hub_dispatch.py'
HUB_DISPATCH_TEMPLATE = 'hooks/_hub_dispatch.py'  # under templates\, the canonical tracked source


def get_dispatch_optin(optin_path, tool_name, config):
    """Same hooks event/matcher SHAPE as get_expanded_optin() (read from the same canonical
    templates\\optins\\<tool>.json - one file, no duplicated second canonical source), but every
    hook's command replaced with the fixed dispatch-wrapper invocation:
    '<launcher> "$CLAUDE_PROJECT_DIR/.claude/hooks/_hub_dispatch.py" <tool_name>'. This command
    string never contains the hub's real path, so it never needs per-host regeneration - only
    python_launcher varies, same narrow axis get_expanded_optin() already substitutes today.
    """
    with open(optin_path, 'r', encoding='utf-8') as f:
        optin = json.load(f)
    launcher = str(config.get('python_launcher', ''))
    command = f'{launcher} "$CLAUDE_PROJECT_DIR/{HUB_DISPATCH_RELPATH}" {tool_name}'
    if 'hooks' in optin:
        for evt, groups in optin['hooks'].items():
            for grp in groups:
                if 'hooks' in grp:
                    for h in grp['hooks']:
                        if 'command' in h:
                            h['command'] = command
    return optin


def build_dispatch_cmd_map(tools, private_tools, config, optins_dir, private_optins_dir):
    """Dispatch-wrapper analog of build_new_cmd_map() above: tool name -> its dispatch-wrapper
    command (get_dispatch_optin() instead of get_expanded_optin()). Used for a NEW connection only
    (design\\consumer_reference_indirection.md) - new_consumer.py's host-merge branch, when the
    joining host is genuinely new."""
    new_cmd = {}
    for t in tools:
        optin_path = Path(optins_dir) / f"{t}.json"
        if not optin_path.exists():
            continue
        optin = get_dispatch_optin(optin_path, t, config)
        for evt, groups in optin.get('hooks', {}).items():
            for grp in groups:
                for h in grp.get('hooks', []):
                    if 'command' in h:
                        new_cmd[t] = h['command']
    for t in private_tools:
        optin_path = Path(private_optins_dir) / f"{t}.json"
        if not optin_path.exists():
            continue
        optin = get_dispatch_optin(optin_path, t, config)
        for evt, groups in optin.get('hooks', {}).items():
            for grp in groups:
                for h in grp.get('hooks', []):
                    if 'command' in h:
                        new_cmd[t] = h['command']
    return new_cmd


def build_hub_pointer_content(config, import_pieces):
    """Renders .claude\\hub_pointer.md's full content for THIS host, right now
    (design\\consumer_reference_indirection.md): a fenced yaml block carrying the raw
    shared_root:/import_base: values config_lib.get_shared_config() just computed, followed by the
    literal @import lines for every mandatory/imported protocol piece this consumer has - the exact
    lines that used to live directly in CLAUDE.md. Gitignored, one per consumer, one value per
    host - regenerated fresh by new_consumer.py (scaffold/host-merge) and relocate.py, never
    hand-edited.
    """
    import_base = config['import_base']
    lines = [
        '<!-- Tower Crane hub pointer - auto-regenerated per host, never hand-edit or commit',
        '     (this file is gitignored). See design\\consumer_reference_indirection.md. -->',
        '',
        '```yaml',
        f"shared_root: {config['shared_root']}",
        f"import_base: {import_base}",
        '```',
        '',
    ]
    lines.extend(f"@{import_base}/{p}.md" for p in import_pieces)
    return '\n'.join(lines) + '\n'


def fix_hub_pointer(consumer_path, config, import_pieces, dry_run=False, log=None):
    """Regenerates .claude\\hub_pointer.md for THIS host, but ONLY for a consumer whose CLAUDE.md
    already carries the HUB_POINTER_IMPORT_LINE indirection (design\\
    consumer_reference_indirection.md) - an old-style, not-yet-migrated consumer is left
    completely untouched (no unrequested file appears in its working tree). Called by relocate.py
    on every regeneration pass, same as fix_imports()/fix_skill_stubs() above. Returns True if
    written (or would be, under dry_run)."""
    consumer_path = Path(consumer_path)
    claude_path = consumer_path / 'CLAUDE.md'
    if not claude_path.exists() or HUB_POINTER_IMPORT_LINE not in claude_path.read_text(encoding='utf-8'):
        return False
    pointer_path = consumer_path / HUB_POINTER_RELPATH
    expected = build_hub_pointer_content(config, import_pieces)
    current = pointer_path.read_text(encoding='utf-8') if pointer_path.exists() else None
    if current == expected:
        return False
    if log:
        verb = 'would regenerate' if dry_run else 'regenerate'
        log(f"  [{verb}] {HUB_POINTER_RELPATH}")
    if not dry_run:
        pointer_path.parent.mkdir(parents=True, exist_ok=True)
        pointer_path.write_text(expected, encoding='utf-8', newline='\n')
    return True


def fix_hub_dispatch_wrapper(consumer_path, templates_dir, dry_run=False, log=None):
    """Refreshes .claude\\hooks\\_hub_dispatch.py against the canonical
    templates\\hooks\\_hub_dispatch.py source, but ONLY for a consumer that already has this file
    (i.e. already migrated - design\\consumer_reference_indirection.md) - never introduces it to a
    not-yet-migrated consumer. Content is host-invariant (no substitution), same drift shape as
    fix_skill_stubs() above. Returns True if written (or would be, under dry_run)."""
    dst = Path(consumer_path) / HUB_DISPATCH_RELPATH
    if not dst.exists():
        return False
    src = Path(templates_dir) / HUB_DISPATCH_TEMPLATE
    if not src.exists():
        return False
    expected = src.read_text(encoding='utf-8')
    if dst.read_text(encoding='utf-8') == expected:
        return False
    if log:
        verb = 'would regenerate' if dry_run else 'regenerate'
        log(f"  [{verb}] {HUB_DISPATCH_RELPATH}")
    if not dry_run:
        dst.write_text(expected, encoding='utf-8', newline='\n')
    return True


HUB_POINTER_YAML_RE = re.compile(r'```yaml\s*\r?\n(.*?)\r?\n```', re.DOTALL)


def parse_hub_pointer(path):
    """Reads a consumer's own .claude\\hub_pointer.md (this host's copy) and returns
    {'shared_root':.., 'import_base':.., 'imports': [piece_name, ...]}, or None if the file
    doesn't exist or has no parseable yaml block. `imports` is derived from the literal @import
    lines below the yaml block (the same piece-name extraction CLAUDE.md's own scan already used
    before this indirection existed)."""
    path = Path(path)
    if not path.exists():
        return None
    text = path.read_text(encoding='utf-8')
    m = HUB_POINTER_YAML_RE.search(text)
    if not m:
        return None
    yaml_text = m.group(1)
    result = {'shared_root': None, 'import_base': None, 'imports': []}
    sr = re.search(r'(?m)^shared_root:\s*(.+?)\s*$', yaml_text)
    if sr:
        result['shared_root'] = sr.group(1)
    ib = re.search(r'(?m)^import_base:\s*(.+?)\s*$', yaml_text)
    if ib:
        result['import_base'] = ib.group(1)
    result['imports'] = re.findall(r'(?m)^@.*?templates/(\w+)\.md\s*$', text)
    return result


_LEADING_COMMENT_RE = re.compile(r'^\s*<!--.*?-->\s*', re.DOTALL)
_READ_INSTRUCTION_RE = re.compile(r'\{\{READ_INSTRUCTION:([\w.]+)\}\}')


def _render_read_instruction(target, import_base, use_pointer):
    """The one sentence fragment design\\consumer_reference_indirection.md's skill-stub fix
    actually changes: for a new-connection consumer (use_pointer=True), points the agent at this
    project's own .claude\\hub_pointer.md instead of a baked import_base path - for a
    not-yet-migrated consumer (use_pointer=False, the default - no forced migration), the
    original direct-substitution wording is unchanged. Both forms are independently valid
    canonical shapes; check_tower_crane.py's Pass B accepts either."""
    if use_pointer:
        return (f"Read this project's `.claude/hub_pointer.md`, take its `import_base:` value, "
                 f"and read `<that value>/{target}` in full")
    return f"Read `{import_base}/{target}` in full"


def materialize_skill_stub(canon_path, import_base=None, use_pointer=False):
    """Read a canonical templates\\skills\\<name>\\SKILL.md source and return the content that
    should actually be installed (scaffolded to a consumer, self-hooked into the hub, or applied
    by update_consumers.py): the leading maintainer HTML-comment header stripped, {{IMPORT_BASE}}
    substituted if import_base is given (omit for a private, copy-only stub), and any
    {{READ_INSTRUCTION:<target>}} placeholder rendered per use_pointer (design\\
    consumer_reference_indirection.md - defaults False, i.e. the pre-existing direct-substitution
    wording, so every existing caller that doesn't pass this explicitly keeps its current
    behavior unchanged).

    The header strip matters, not just tidiness: every canonical stub carries that comment BEFORE
    the YAML frontmatter, which breaks the harness's name/description parsing on the installed
    copy - the skill listing shows the raw comment text instead of the real description. Mirrors
    the header strip new_consumer.py already does for CLAUDE.md's own template header; this is
    the same fix extended to skill stubs, which never got it (found 2026-08-04).
    """
    text = Path(canon_path).read_text(encoding='utf-8')
    text = _LEADING_COMMENT_RE.sub('', text, count=1)
    text = _READ_INSTRUCTION_RE.sub(
        lambda m: _render_read_instruction(m.group(1), import_base, use_pointer), text)
    if import_base is not None:
        text = text.replace('{{IMPORT_BASE}}', str(import_base))
    return text


def build_new_cmd_map(tools, private_tools, config, optins_dir, private_optins_dir, warn=None):
    """tool name -> its current concrete hook command, read from the canonical opt-in snippets.
    Single source of truth for 'what should this tool's hook command be right now' - relocate.py's
    regeneration pass and new_consumer.py's host-merge reuse of it both call this instead of each
    hand-rolling the same walk (design\\consumer_reconnect.md).

    `warn`, if given, is called with a message for a tool with no canonical opt-in file (public
    tools only - a private "tool" may be a Track-1 skill instead of a hook, so a missing private
    opt-in is silently skipped, matching relocate.py's prior behavior).
    """
    new_cmd = {}
    for t in tools:
        optin_path = Path(optins_dir) / f"{t}.json"
        if not optin_path.exists():
            if warn:
                warn(f"no canonical opt-in for '{t}' - skipping that tool.")
            continue
        optin = get_expanded_optin(optin_path, config)
        for evt, groups in optin.get('hooks', {}).items():
            for grp in groups:
                for h in grp.get('hooks', []):
                    if 'command' in h:
                        new_cmd[t] = h['command']
    for t in private_tools:
        optin_path = Path(private_optins_dir) / f"{t}.json"
        if not optin_path.exists():
            continue
        optin = get_expanded_optin(optin_path, config)
        for evt, groups in optin.get('hooks', {}).items():
            for grp in groups:
                for h in grp.get('hooks', []):
                    if 'command' in h:
                        new_cmd[t] = h['command']
    return new_cmd


def apply_hook_command_fixes(settings, new_cmd, all_tools, dry_run=False, log=None):
    """Rewrite, in place, any hook command in `settings` (an already-loaded settings.json dict)
    that references an opted-in tool's hook file (hooks/<tool>.ps1 or .py) to that tool's current
    command from `new_cmd` (see build_new_cmd_map). Never adds, removes, or reorders unrelated
    hooks. Returns True if anything changed (or would, under dry_run).
    """
    changed = False
    for evt, groups in settings.get('hooks', {}).items():
        for grp in groups:
            for h in grp.get('hooks', []):
                if 'command' not in h:
                    continue
                for t in all_tools:
                    if t not in new_cmd:
                        continue
                    pattern = r'hooks[\\/]' + re.escape(t) + r'\.(ps1|py)'
                    if re.search(pattern, h['command']) and h['command'] != new_cmd[t]:
                        if log:
                            verb = 'would change' if dry_run else 'change'
                            log(f"  [{verb}] {t}")
                            log(f"      from: {h['command']}")
                            log(f"      to:   {new_cmd[t]}")
                        h['command'] = new_cmd[t]
                        changed = True
    return changed


def fix_skill_stubs(consumer_path, templates_dir, import_base, dry_run=False, log=None, use_pointer=False):
    """Regenerate every installed .claude\\skills\\<name>\\SKILL.md stub whose content doesn't
    match what materialize_skill_stub() would produce right now from the canonical
    templates\\skills\\<name>\\SKILL.md source (design\\consumer_reconnect.md - closes a
    pre-existing gap: stubs are baked with {{IMPORT_BASE}} at scaffold time and were never
    revisited by anything, even on a single-machine rename). Skips a skill dir with no matching
    canonical source (e.g. a private-tool-managed skill). `use_pointer` (design\\
    consumer_reference_indirection.md) selects which of the two valid renderings to regenerate
    TO - the caller decides per-consumer (a migrated consumer's CLAUDE.md already carries
    HUB_POINTER_IMPORT_LINE; an un-migrated one doesn't, and stays on the direct-substitution
    form, the default). Returns True if anything changed (or would, under dry_run).
    """
    skills_dir = Path(consumer_path) / '.claude' / 'skills'
    if not skills_dir.is_dir():
        return False
    changed = False
    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        stub_path = skill_dir / 'SKILL.md'
        canon_path = Path(templates_dir) / 'skills' / skill_dir.name / 'SKILL.md'
        if not stub_path.exists() or not canon_path.exists():
            continue
        expected = materialize_skill_stub(canon_path, import_base, use_pointer=use_pointer)
        current = stub_path.read_text(encoding='utf-8')
        if current != expected:
            if log:
                verb = 'would regenerate' if dry_run else 'regenerate'
                log(f"  [{verb}] skill stub: {skill_dir.name}")
            if not dry_run:
                stub_path.write_text(expected, encoding='utf-8', newline='\n')
            changed = True
    return changed


# design\directive_economy.md's "Adopted-stub path portability" - a shared_resources\-adopted
# reference/tool skill stub (private-only, no canonical toolkit\ source - see fix_skill_stubs()'s
# docstring for that contrast) still needs its embedded path to survive a move across hosts. The
# adoption-marker comment templates\shared_resources.md's Apply step already writes carries an
# optional `hub-rel:<path>` field (the entry file's path relative to the hub root, e.g.
# `shared_resources/seo_resources.md`) precisely so this can be recomputed for whichever host it
# runs on, the same way {{IMPORT_BASE}} already is for toolkit-governed stubs - just with no whole
# canonical file to diff against, only this one anchor.
ADOPTED_MARKER_RE = re.compile(
    r'<!--\s*shared_resources:\s*(?P<entry>.+?)\s+adopted\s+\d{4}-\d{2}-\d{2}'
    r'(?:\s+index-sha256:[0-9a-f]{64})?'
    r'(?:\s+hub-rel:(?P<hubrel>\S+))?'
    r'(?:\s+hosts-ignored:(?P<hostsignored>\S+))?'
    r'\s*-->'
)


def hub_root_tilde(hub_root):
    """Home-relative '~/...' form of the hub root (one level above shared_root/toolkit\\) - the
    same form import_base already computes, and the only path shape this mechanism's backtick-
    quoted references (and Claude Code's own @import) ever resolve reliably."""
    rel = Path(hub_root).resolve().relative_to(Path.home().resolve())
    return '~/' + str(rel).replace('\\', '/')


def fix_adopted_stub_paths(consumer_path, hub_root, dry_run=False, log=None):
    """Regenerate a private, shared_resources\\-adopted skill stub's embedded path for THIS host,
    using the hub-relative fragment recorded in its own adoption marker at Apply time
    (design\\directive_economy.md's "Adopted-stub path portability"). Unlike fix_skill_stubs(),
    there's no canonical templates\\skills\\ source to diff a whole file against - an adopted
    stub's trigger/body is bespoke, private, written once. The marker's `hub-rel:` field is the
    only portable anchor: `~/<hub-relative fragment>` recomputed against THIS host's live
    hub_root, substituted for whatever backtick-quoted `~/...shared_resources/...` path currently
    appears in the stub body, only if it differs. A stub with no `hub-rel:` field (an insight
    adoption, or one written before this feature existed) is left untouched - out of scope, not a
    failure. Returns True if anything changed (or would, under dry_run).
    """
    skills_dir = Path(consumer_path) / '.claude' / 'skills'
    if not skills_dir.is_dir():
        return False
    changed = False
    for skill_md in sorted(skills_dir.glob('*/SKILL.md')):
        text = skill_md.read_text(encoding='utf-8')
        m = ADOPTED_MARKER_RE.search(text)
        if not m or not m.group('hubrel'):
            continue
        expected = f"{hub_root_tilde(hub_root)}/{m.group('hubrel')}"
        new_text, n = re.subn(r'`~/[^`]*shared_resources/[^`]*`', f'`{expected}`', text)
        if n and new_text != text:
            if log:
                verb = 'would regenerate' if dry_run else 'regenerate'
                log(f"  [{verb}] adopted stub path: {skill_md.parent.name}")
            if not dry_run:
                skill_md.write_text(new_text, encoding='utf-8', newline='\n')
            changed = True
    return changed


# Shared markers between disconnect_consumer.py (writer) and new_consumer.py (reader, for the
# reconnect branch - design\\connect_disconnect.md "Reconnect-after-disconnect gap"): the two live sections
# a disconnect replaces, the pointer heading it replaces them with, and the breadcrumb notes file
# that heading points to. Centralized here (rather than defined in disconnect_consumer.py alone) so
# the two scripts can't drift out of sync on what marker text means "disconnected".
TC_IN_USE_HEADING = '## Tower Crane In Use'
WORKFLOW_HEADING = '## Shared Workflow Protocol'
DISCONNECTED_HEADING = '## Tower Crane (disconnected)'
DISCONNECT_NOTES_FILENAME = 'TOWER_CRANE_DISCONNECT_NOTES.md'

# The Tower-Crane-owned paths inside a consumer project's own working tree - every hub-invoked
# writer (relocate.py, update_consumers.py) is confirmed to touch only these three (fix_imports/
# apply_piece -> CLAUDE.md; apply_hook_command_fixes/apply_hook/apply_private -> .claude/settings.json;
# fix_skill_stubs/fix_adopted_stub_paths/apply_skill/apply_piece/apply_private -> .claude/skills/).
# disconnect_consumer.py additionally writes DISCONNECT_NOTES_FILENAME (the generated breadcrumb
# manifest a this-only local cleanup leaves behind) - harmless no-op for the other two writers,
# which never touch that filename. HUB_DISPATCH_RELPATH (design\consumer_reference_indirection.md)
# is tracked, host-invariant content - a real committable path, unlike HUB_POINTER_RELPATH, which
# is gitignored and must NEVER appear here (an explicit `git add` of a gitignored path stages it
# anyway, bypassing .gitignore).
CONSUMER_OWNED_PATHS = ('CLAUDE.md', '.claude/settings.json', '.claude/skills',
                         HUB_DISPATCH_RELPATH, '.gitignore', DISCONNECT_NOTES_FILENAME)


def commit_consumer_changes(consumer_path, message, log=None):
    """Commit (and push, if a remote is configured) any pending change under a consumer
    project's OWN Tower-Crane-owned paths, into THAT PROJECT'S OWN git repo - never the hub's.

    Why this exists: a hub-invoked routine pass (relocate.py's path/hook regeneration,
    update_consumers.py's bulk push) writes directly into a consumer's working tree with no live
    session there to notice and checkpoint it - unlike a consumer's own session adopting something
    itself, which naturally checkpoints right after. Left alone, that write just sits uncommitted
    indefinitely, with no reminder mechanism short of a human remembering. Mirrors
    `shared_resources\\`'s own "saving now propagates itself" fix
    (design\\resource_sharing_model.md) one level down: don't ask, don't rely on a human/agent
    remembering to push later - make the routine pass close its own loop, every time, as its own
    last step for that consumer.

    Scoped add (CONSUMER_OWNED_PATHS only, never `-A`) so an unrelated in-progress edit elsewhere
    in that project (the user's own client work, mid-edit) is never swept in - same discipline as
    `shared_resources\\`'s own scoped `git add shared_resources`.

    Returns one of: 'not-a-repo' (no .git\\ here - nothing this function can do), 'noop' (nothing
    changed under the owned paths), 'committed-pushed', 'committed-no-remote' (committed locally;
    no 'origin' remote configured to push to), 'commit-failed', 'push-failed'. Never raises on a
    git failure - reports it via the return value / `log` instead, so one consumer's git trouble
    can't abort a batch run touching several.
    """
    consumer_path = Path(consumer_path)
    if not (consumer_path / '.git').is_dir():
        return 'not-a-repo'

    owned = [p for p in CONSUMER_OWNED_PATHS if (consumer_path / p).exists()]
    if not owned:
        return 'noop'

    def _git(git_args):
        return subprocess.run(['git', '-C', str(consumer_path)] + git_args,
                               capture_output=True, text=True)

    status = _git(['status', '--porcelain', '--'] + owned)
    if not status.stdout.strip():
        return 'noop'

    _git(['add', '--'] + owned)
    commit = _git(['commit', '-m', message])
    if commit.returncode != 0:
        if log:
            log(f"  [warn] commit failed in {consumer_path}: {commit.stderr.strip() or commit.stdout.strip()}")
        return 'commit-failed'

    remotes = _git(['remote'])
    if 'origin' not in remotes.stdout.split():
        return 'committed-no-remote'

    push = _git(['push'])
    if push.returncode != 0:
        if log:
            log(f"  [warn] push failed in {consumer_path}: {push.stderr.strip() or push.stdout.strip()}")
        return 'push-failed'
    return 'committed-pushed'


def print_diagnose_inline(config, path=None, slug=None, log=print):
    """Best-effort inline invocation of `check_tower_crane.py --diagnose` (design\\
    connection_diagnostics.md): shells out rather than importing, matching update_toolkit.py's own
    existing pattern of invoking check_tower_crane.py as a subprocess (also sidesteps an import
    cycle, since check_tower_crane.py itself imports from this module). Called from
    new_consumer.py's/disconnect_consumer.py's failure paths right before they raise, so the fact
    table prints inline ahead of the error instead of a bare error string. Never raises: a diagnose
    failure here must never mask the original fatal error it exists to add context to.
    """
    if not path and not slug:
        return
    script = Path(config['shared_root']) / 'scripts' / 'check_tower_crane.py'
    cmd = [config['python_launcher'], str(script), '--diagnose']
    if path:
        cmd += ['--path', str(path)]
    if slug:
        cmd += ['--slug', str(slug)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
        log(proc.stdout + proc.stderr)
    except OSError:
        pass
