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


_LEADING_COMMENT_RE = re.compile(r'^\s*<!--.*?-->\s*', re.DOTALL)


def materialize_skill_stub(canon_path, import_base=None):
    """Read a canonical templates\\skills\\<name>\\SKILL.md source and return the content that
    should actually be installed (scaffolded to a consumer, self-hooked into the hub, or applied
    by update_consumers.py): the leading maintainer HTML-comment header stripped, and
    {{IMPORT_BASE}} substituted if import_base is given (omit for a private, copy-only stub).

    The header strip matters, not just tidiness: every canonical stub carries that comment BEFORE
    the YAML frontmatter, which breaks the harness's name/description parsing on the installed
    copy - the skill listing shows the raw comment text instead of the real description. Mirrors
    the header strip new_consumer.py already does for CLAUDE.md's own template header; this is
    the same fix extended to skill stubs, which never got it (found 2026-08-04).
    """
    text = Path(canon_path).read_text(encoding='utf-8')
    text = _LEADING_COMMENT_RE.sub('', text, count=1)
    if import_base is not None:
        text = text.replace('{{IMPORT_BASE}}', str(import_base))
    return text
