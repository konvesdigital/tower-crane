#!/usr/bin/env python3
"""
self_hooks.py - toggle tower_crane's own hooks ON for this repo/machine (self-use / dogfooding),
off by default.

Tower Crane is not a registered consumer of itself (no consumers\\<slug>.md entry) - self-use is
kept deliberately separate from the consumer registry/scaffolder/checker machinery, which is built
for tracking OTHER projects (design discussion: project_progress.md, 2026-07-22 "Self-use
(dogfooding) mechanism" entry). Every available tool already has a single canonical opt-in snippet
at templates\\optins\\<tool>.json - this script is the only piece that was actually missing: a
personal, per-machine way to flip one on/off for THIS repo's own use.

An opt-in snippet may carry a 'hooks' key (merged into .claude\\settings.local.json, as always) and/
or a 'skills' key - a list of Track-1 skill names whose canonical templates\\skills\\<name>\\SKILL.md
gets copied into this hub's own .claude\\skills\\<name>\\SKILL.md (design\\optimize_ux.md's
hub_commands - the hub-operator side of the "commands" discoverability mechanism, distributed this
way since the hub isn't a registered consumer of new_consumer.py's scaffolder). Any {{IMPORT_BASE}}
placeholder in the canonical stub is resolved the same way new_consumer.py resolves it for a real
consumer - using this same hub's own computed import_base - before the copy is written; a stub with
no such placeholder (e.g. hub_commands) is unaffected, since the substitution is a no-op on it. This
lets a single canonical stub serve both a consumer scaffold and this hub's own self-install (see
design\\capability_relationships.md's capability_relationships skill for the first case that needed
this - a skill that fires the same way from either a consumer or a hub session).

  --list              (default) show every available tool and whether it's currently on here.
  --enable <tool>     merge templates\\optins\\<tool>.json's hook(s) into .claude\\settings.local.json.
  --disable <tool>    remove them again.

Every run also rewrites .claude\\self_hooks_status.md, a plain human-readable mirror of current
on/off state - open it directly, no command needed just to *check* (same "generated artifact,
never hand-edited" pattern as check_tower_crane.py's COMPLIANCE_GUIDANCE.md).

Both .claude\\settings.local.json and .claude\\self_hooks_status.md are gitignored: this is
personal/per-machine state, never committed, never shipped in a release - a fresh clone or a
downloaded hub always starts with nothing enabled.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config_lib import get_shared_config, get_expanded_optin, materialize_skill_stub

SHARED_ROOT = Path(__file__).resolve().parent.parent
# Self-use only ever targets THIS hub's own repo, whose layout is always outer-root/toolkit\ post-
# split - .claude\ (where Claude Code actually writes session state) lives at the outer root, one
# level above SHARED_ROOT (toolkit\), not inside it.
PROJECT_ROOT = SHARED_ROOT.parent
OPTINS_DIR = SHARED_ROOT / 'templates' / 'optins'
SKILLS_DIR = SHARED_ROOT / 'templates' / 'skills'
CLAUDE_DIR = PROJECT_ROOT / '.claude'
SETTINGS_PATH = CLAUDE_DIR / 'settings.local.json'
STATUS_PATH = CLAUDE_DIR / 'self_hooks_status.md'
SKILLS_INSTALL_DIR = CLAUDE_DIR / 'skills'


def write_utf8(path, content):
    # Python's utf-8 encoding never writes a BOM (unlike PS 5.1's -Encoding utf8); newline='\n'
    # keeps embedded '\n' as LF instead of Windows-translating it to CRLF on write.
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8', newline='\n')


def available_tools():
    return sorted(p.stem for p in OPTINS_DIR.glob('*.json'))


def load_settings():
    if SETTINGS_PATH.exists():
        settings = json.loads(SETTINGS_PATH.read_text(encoding='utf-8'))
        if settings is None:
            settings = {}
    else:
        settings = {}
    settings.setdefault('hooks', {})
    return settings


def save_settings(settings):
    write_utf8(SETTINGS_PATH, json.dumps(settings, indent=2))


# Normalize a hook-group dict to a comparable string. Collapses '\\\\' -> '/' so a canonical
# forward-slash command and a compressed-JSON escaped-backslash command compare equal (same
# normalization check_tower_crane.py's drift check uses).
def _normalize(entry):
    return json.dumps(entry, separators=(',', ':')).replace('\\\\', '/')


def _hooks_on(optin, settings):
    hooks = settings.get('hooks') if isinstance(settings, dict) else None
    for evt, groups in optin['hooks'].items():
        canon = [_normalize(g) for g in groups]
        have = []
        if isinstance(hooks, dict) and evt in hooks:
            have = [_normalize(e) for e in hooks[evt]]
        if any(entry not in have for entry in canon):
            return False
    return True


def _skills_on(optin, config):
    for name in optin['skills']:
        canon_path = SKILLS_DIR / name / 'SKILL.md'
        installed_path = SKILLS_INSTALL_DIR / name / 'SKILL.md'
        if not installed_path.exists():
            return False
        expected = materialize_skill_stub(canon_path, config['import_base'])
        if installed_path.read_text(encoding='utf-8') != expected:
            return False
    return True


def tool_status(tool, settings, config):
    """Returns 'on' / 'off' / 'n/a' (n/a = the opt-in snippet has neither a 'hooks' nor a 'skills'
    key - nothing here to toggle yet). 'on' requires every declared hook AND every declared skill
    (whichever keys are present) to already match; a mismatched/missing skill copy counts as 'off',
    same as a missing hook entry."""
    optin = get_expanded_optin(OPTINS_DIR / f"{tool}.json", config)
    has_hooks = 'hooks' in optin
    has_skills = 'skills' in optin
    if not has_hooks and not has_skills:
        return 'n/a'
    if has_hooks and not _hooks_on(optin, settings):
        return 'off'
    if has_skills and not _skills_on(optin, config):
        return 'off'
    return 'on'


def write_status(config, settings=None):
    if settings is None:
        settings = load_settings()
    tools = available_tools()
    lines = [
        "# Self-use hooks status (this machine only)",
        "",
        "Regenerated by `scripts\\self_hooks.py` - do not hand-edit, it is overwritten on the next "
        "run. Mirrors `.claude\\settings.local.json` (gitignored: personal/per-machine, never "
        "committed, never shipped in a release).",
        "",
        "| Tool | Status |",
        "|---|---|",
    ]
    if not tools:
        lines.append("| _(none available yet)_ | |")
    else:
        for t in tools:
            lines.append(f"| {t} | {tool_status(t, settings, config).upper()} |")
    lines += [
        "",
        "Toggle: `python scripts\\self_hooks.py --enable <tool>` / `--disable <tool>`. "
        "List with `python scripts\\self_hooks.py --list`.",
    ]
    write_utf8(STATUS_PATH, '\n'.join(lines) + '\n')


def cmd_list(config):
    settings = load_settings()
    tools = available_tools()
    print("=== self_hooks.py: available tools ===")
    if not tools:
        print("  (none - no templates\\optins\\*.json found)")
    for t in tools:
        print(f"  [{tool_status(t, settings, config)}] {t}")
    write_status(config, settings)
    print()
    print(f"Status mirror: {STATUS_PATH}")
    print("Toggle: python scripts\\self_hooks.py --enable <tool> / --disable <tool>")


def _enable_skills(optin, config):
    changed = False
    for name in optin['skills']:
        canon_path = SKILLS_DIR / name / 'SKILL.md'
        if not canon_path.exists():
            raise RuntimeError(f"Canonical skill stub missing for '{name}': {canon_path}")
        installed_path = SKILLS_INSTALL_DIR / name / 'SKILL.md'
        canon_content = materialize_skill_stub(canon_path, config['import_base'])
        if not installed_path.exists() or installed_path.read_text(encoding='utf-8') != canon_content:
            write_utf8(installed_path, canon_content)
            changed = True
    return changed


def _disable_skills(optin):
    changed = False
    for name in optin['skills']:
        installed_path = SKILLS_INSTALL_DIR / name / 'SKILL.md'
        if installed_path.exists():
            installed_path.unlink()
            changed = True
        skill_dir = installed_path.parent
        if skill_dir.exists() and not any(skill_dir.iterdir()):
            skill_dir.rmdir()
    return changed


def cmd_enable(tool, config):
    optin_path = OPTINS_DIR / f"{tool}.json"
    if not optin_path.exists():
        raise RuntimeError(f"Unknown tool '{tool}' - no opt-in snippet at {optin_path}. "
                            f"Available: {', '.join(available_tools()) or '(none)'}")
    optin = get_expanded_optin(optin_path, config)
    if 'hooks' not in optin and 'skills' not in optin:
        raise RuntimeError(f"'{tool}' has nothing to enable (no 'hooks' or 'skills' key in {optin_path}).")

    changed = False
    settings = load_settings()
    if 'hooks' in optin:
        for evt, groups in optin['hooks'].items():
            existing = settings['hooks'].setdefault(evt, [])
            existing_norm = [_normalize(e) for e in existing]
            for entry in groups:
                if _normalize(entry) not in existing_norm:
                    existing.append(entry)
                    changed = True
        save_settings(settings)
    if 'skills' in optin:
        changed = _enable_skills(optin, config) or changed
    write_status(config, settings)
    if changed:
        print(f"Enabled '{tool}' for this machine.")
    else:
        print(f"'{tool}' was already enabled - no change.")


def cmd_disable(tool, config):
    optin_path = OPTINS_DIR / f"{tool}.json"
    if not optin_path.exists():
        raise RuntimeError(f"Unknown tool '{tool}' - no opt-in snippet at {optin_path}. "
                            f"Available: {', '.join(available_tools()) or '(none)'}")
    optin = get_expanded_optin(optin_path, config)
    if 'hooks' not in optin and 'skills' not in optin:
        raise RuntimeError(f"'{tool}' has nothing to disable (no 'hooks' or 'skills' key in {optin_path}).")

    changed = False
    settings = load_settings()
    if 'hooks' in optin:
        for evt, groups in optin['hooks'].items():
            canon = [_normalize(g) for g in groups]
            have = settings['hooks'].get(evt, [])
            kept = [e for e in have if _normalize(e) not in canon]
            if len(kept) != len(have):
                changed = True
            if kept:
                settings['hooks'][evt] = kept
            else:
                settings['hooks'].pop(evt, None)
        save_settings(settings)
    if 'skills' in optin:
        changed = _disable_skills(optin) or changed
    write_status(config, settings)
    if changed:
        print(f"Disabled '{tool}' for this machine.")
    else:
        print(f"'{tool}' was not enabled - no change.")


def main():
    parser = argparse.ArgumentParser(
        description="Toggle tower_crane's own hooks on for this repo/machine (self-use, off by default)."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--list', action='store_true',
                        help="List available tools and current on/off state here. Default if no flag given.")
    group.add_argument('--enable', metavar='TOOL', help="Turn a tool on for this machine.")
    group.add_argument('--disable', metavar='TOOL', help="Turn a tool off for this machine.")
    args = parser.parse_args()

    config = get_shared_config(SHARED_ROOT)

    if args.enable:
        cmd_enable(args.enable, config)
    elif args.disable:
        cmd_disable(args.disable, config)
    else:
        cmd_list(config)


if __name__ == '__main__':
    main()
