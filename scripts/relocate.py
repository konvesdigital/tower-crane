#!/usr/bin/env python3
"""
relocate.py - regenerate every registered consumer's hook command(s) from config.local.json,
the "config -> regenerate" action of the portability foundation (design\\portability.md).

Reads config.local.json, walks the consumer registry (consumers/*.md), and for each consumer
that lives on THIS machine rewrites the hook command in its .claude/settings.json to the concrete
command computed from config (python launcher + shared_root path + hooks/<tool>.py). shared_root
itself is always the live, current location (config_lib.py never trusts a stale stored value), so
this is the one-run fix that brings every consumer's ALREADY-BAKED hook command/@import lines back
in sync after this repo moved or was renamed - config_lib.py notices that automatically and points
here; this script is what actually pushes the fix out to consumers. Also the path that migrates a
consumer from the old PowerShell hook (hooks/<tool>.ps1) to the pure-Python hook (hooks/<tool>.py).

It rewrites ONLY the command string of hooks that reference an opted-in tool's hook file
(hooks/<tool>.ps1 or .py). It never adds, removes, or reorders unrelated settings/hooks. On the
current machine with an already-current settings.json it is a no-op.

Cross-repo note: this writes into each consumer's OWN repo working tree (it does not commit). The
consumer's next session verifies the hook still fires and commits - the change-request round-trip
(a behavior-changing edit to a live consumer). Run --dry-run first to preview.

OS-reach Tier 2 port of relocate.ps1 (design\\portability.md, "OS-reach Tier 2: full
cross-platform design"). Logic is a direct translation - see that doc's Build order for the
parity-check approach used to verify this against the original.
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config_lib import (get_shared_config, build_new_cmd_map, build_dispatch_cmd_map,
                         apply_hook_command_fixes, fix_skill_stubs, fix_adopted_stub_paths,
                         commit_consumer_changes, fix_hub_pointer, fix_hub_dispatch_wrapper,
                         fix_imports, sync_consumer_repo, HUB_POINTER_IMPORT_LINE)
from registry_lib import parse_registry, host_path, reconcile_scope_floor

SHARED_ROOT = Path(__file__).resolve().parent.parent
# consumers\ is private hub state, not shipped toolkit content - it lives at the outer root
# (design\local_first_reframe.md's outer/inner split), one level above SHARED_ROOT (toolkit\).
PROJECT_ROOT = SHARED_ROOT.parent
TEMPLATES_DIR = SHARED_ROOT / 'templates'
OPTINS_DIR = TEMPLATES_DIR / 'optins'
CONSUMERS_DIR = PROJECT_ROOT / 'consumers'
# design\private_tools.md - a moved/renamed hub needs its consumers' private hook commands
# regenerated too, same as public ones.
PRIVATE_OPTINS_DIR = PROJECT_ROOT / 'toolkit_private' / 'templates' / 'optins'

COUNTS = {'changed': 0, 'noop': 0, 'skipped': 0, 'warn': 0}


def write_utf8(path, content):
    # Python's utf-8 encoding never writes a BOM (unlike PS 5.1's -Encoding utf8); newline='\n'
    # keeps embedded '\n' as LF instead of Windows-translating it to CRLF on write.
    path.write_text(content, encoding='utf-8', newline='\n')


# registry parsing lives in registry_lib.py (shared with check_tower_crane.py/update_consumers.py/
# broadcast_guidance.py) - this wrapper just reshapes its opted_in:/imported:/private_opted_in:
# (each a list of {'name':, 'since':} dicts) into the flat name lists this script's own loop below
# was already written against.
def read_registry_entry(path):
    obj = parse_registry(path)
    if obj is None:
        return None
    obj['tools'] = [ti['name'] for ti in obj['opted_in']]
    obj['imports'] = [pi['name'] for pi in obj['imported']]
    obj['private_tools'] = [ti['name'] for ti in obj['private_opted_in']]
    return obj


# fix_imports() now lives in config_lib.py (design\grt_connectivity_audit.md item (ii), moved
# 2026-08-19 so commit_consumer_changes()'s own push-failure reconciliation can call it
# in-process) - imported above alongside the other Tower-Crane-owned-file regenerators.

# design\resource_sharing_model.md's "Saving now propagates itself" fix, one level down
# (project_progress.md's 2026-08-11 Work Log): this pass writes into a consumer's own repo with
# no live session there to notice and checkpoint it, so it closes its own loop instead of leaving
# uncommitted state for a human to remember later.
COMMIT_LABELS = {
    'not-a-repo': None,  # nothing this function can do - not worth a line every run
    'noop': None,        # nothing changed here - not worth a line every run
    'committed-pushed': '  [git] committed and pushed in this consumer\'s own repo.',
    'committed-no-remote': '  [git] committed in this consumer\'s own repo (no origin remote to push to).',
    'commit-failed': None,   # commit_consumer_changes() already logged the warn line itself
    'push-failed': None,     # ditto
    # design\grt_connectivity_audit.md item (ii): a real divergence was auto-resolved by
    # resetting and regenerating this host's own Tower-Crane-owned values - never a text merge.
    # _reconcile_diverged_push() already logged the detail; this is just the summary line.
    'reconciled-pushed': '  [git] push conflict auto-reconciled (reset + regenerated), committed and pushed.',
}


def report_consumer_commit(this_path, dry_run, config, imports):
    if dry_run:
        return
    result = commit_consumer_changes(
        this_path, "Tower Crane sync: relocate.py path/hook regeneration", log=print,
        config=config, imports=imports, shared_root=SHARED_ROOT)
    label = COMMIT_LABELS.get(result)
    if label:
        print(label)


def main():
    parser = argparse.ArgumentParser(
        description="Regenerate every registered consumer's hook command(s) from config.local.json."
    )
    parser.add_argument('--consumer', default=None, help="Slug of a single consumer to scope to (e.g. my_cool_project). Default: all.")
    parser.add_argument('--dry-run', action='store_true', help="Show what would change without writing anything.")
    args = parser.parse_args()

    config = get_shared_config(SHARED_ROOT)
    this_host = str(config.get('host_id', ''))

    print("=== relocate.py ===")
    print(f"shared_root : {config['shared_root']}")
    print(f"launcher    : {config['python_launcher']}")
    print(f"this host   : {this_host}")
    if args.dry_run:
        print("MODE        : DRY RUN (no files written)")

    files = sorted(CONSUMERS_DIR.glob('*.md')) if CONSUMERS_DIR.is_dir() else []
    if args.consumer:
        files = [f for f in files if f.stem == args.consumer]
    if not files:
        if args.consumer:
            raise SystemExit(f"No registry entry for consumer '{args.consumer}' (consumers/{args.consumer}.md).")
        print("No consumer registry entries found.")
        return

    for f in files:
        c = read_registry_entry(f)
        if c is None:
            print(f"  [warn] {f.name}: no parseable yaml block - skipping.")
            COUNTS['warn'] += 1
            continue

        print()
        print(f"Consumer: {c['name']} ({f.stem})")

        # 2-host write-back floor (design\multi_machine_hub.md) - applies regardless of whether
        # this consumer is reachable on this machine.
        if reconcile_scope_floor(f, c):
            print(f"  [fixed] scope -> multi_machine (2+ hosts: entries present).")

        # Federate (#1): only regenerate consumers connected on this machine.
        this_path = host_path(c, this_host)
        if not this_path:
            print(f"  [skip] not connected on this machine ('{this_host}') - hosts: "
                  f"{', '.join(sorted(c['hosts'])) or '(none)'}.")
            COUNTS['skipped'] += 1
            continue
        if not Path(this_path).exists():
            print(f"  [warn] path not found on disk: {this_path}")
            COUNTS['warn'] += 1
            continue

        # Pull this consumer's own repo current BEFORE reading/regenerating anything below, so the
        # edit is never computed against a stale snapshot (config_lib.py's sync_consumer_repo() -
        # see that function's own docstring for the real 2026-08-22 push conflict this closes).
        # No-op in a dry run - nothing downstream will be written anyway.
        if not args.dry_run:
            sync_consumer_repo(this_path, log=print)

        imports_changed = fix_imports(this_path, c['imports'], config['import_base'], args.dry_run,
                                       log=print)
        # design\consumer_reference_indirection.md: regenerate stubs to whichever form this
        # consumer already uses - a migrated consumer's CLAUDE.md carries the pointer indirection
        # line; an un-migrated one doesn't and stays on the direct-substitution form.
        claude_md_this = Path(this_path) / 'CLAUDE.md'
        use_pointer_here = claude_md_this.exists() and HUB_POINTER_IMPORT_LINE in claude_md_this.read_text(encoding='utf-8')
        skills_changed = fix_skill_stubs(this_path, TEMPLATES_DIR, config['import_base'], args.dry_run,
                                          log=print, use_pointer=use_pointer_here)
        # design\directive_economy.md's "Adopted-stub path portability" - a private
        # shared_resources\-adopted stub has no canonical source, so it regenerates from its own
        # marker's hub-rel: anchor instead of a diff against templates\skills\.
        adopted_changed = fix_adopted_stub_paths(this_path, PROJECT_ROOT, args.dry_run, log=print)
        # design\consumer_reference_indirection.md - both are no-ops for a not-yet-migrated
        # consumer (fix_hub_pointer/fix_hub_dispatch_wrapper each check for their own file's prior
        # presence before touching anything, so an old-style consumer never gets these introduced).
        pointer_changed = fix_hub_pointer(this_path, config, c['imports'], args.dry_run, log=print)
        dispatch_changed = fix_hub_dispatch_wrapper(this_path, SHARED_ROOT, args.dry_run, log=print)
        skills_changed = skills_changed or adopted_changed or pointer_changed or dispatch_changed

        all_tools = c['tools'] + c['private_tools']
        if not all_tools:
            if imports_changed or skills_changed:
                COUNTS['changed'] += 1
            else:
                print("  [no-op] no opted-in tools (prose-only consumer).")
                COUNTS['noop'] += 1
            report_consumer_commit(this_path, args.dry_run, config, c['imports'])
            continue

        settings_path = Path(this_path) / '.claude' / 'settings.json'
        if not settings_path.exists():
            print("  [warn] no .claude/settings.json but registry lists opted-in tool(s).")
            COUNTS['warn'] += 1
            continue

        try:
            settings = json.loads(settings_path.read_text(encoding='utf-8'))
        except json.JSONDecodeError:
            print("  [warn] settings.json is not valid JSON - skipping.")
            COUNTS['warn'] += 1
            continue

        # Build tool -> new concrete command map from the canonical opt-ins (public + private -
        # design\private_tools.md; a private command's path already contains 'hooks/<tool>.py'
        # same as a public one, so the rewrite below needs no separate pattern per source). Shared
        # with new_consumer.py's host-merge reuse (design\consumer_reconnect.md) - config_lib.py's
        # build_new_cmd_map/build_dispatch_cmd_map/apply_hook_command_fixes. Target form mirrors
        # use_pointer_here (same signal fix_skill_stubs already keys off, above) - a consumer
        # already migrated to the dispatch-wrapper form must regenerate TO that form, never forced
        # back to direct-path just because apply_hook_command_fixes can now also recognize it.
        def _warn(msg):
            print(f"  [warn] {msg}")
            COUNTS['warn'] += 1
        if use_pointer_here:
            new_cmd = build_dispatch_cmd_map(c['tools'], c['private_tools'], config, OPTINS_DIR, PRIVATE_OPTINS_DIR)
        else:
            new_cmd = build_new_cmd_map(c['tools'], c['private_tools'], config, OPTINS_DIR, PRIVATE_OPTINS_DIR, warn=_warn)

        # Rewrite any command that references an opted-in tool's hook file (hooks/<tool>.ps1 or
        # .py) to that tool's new command. This handles both path relocation and the .ps1 -> .py
        # migration in one motion.
        changed_here = apply_hook_command_fixes(settings, new_cmd, all_tools, args.dry_run, log=print,
                                                 needs_shell=use_pointer_here)

        if changed_here:
            if args.dry_run:
                print("  (dry run - not written)")
            else:
                write_utf8(settings_path, json.dumps(settings, indent=2))
                print(f"  wrote {settings_path}")
            COUNTS['changed'] += 1
        elif imports_changed or skills_changed:
            COUNTS['changed'] += 1
        else:
            print("  [no-op] settings already current.")
            COUNTS['noop'] += 1
        report_consumer_commit(this_path, args.dry_run, config, c['imports'])

    print()
    print(f"=== Summary: {COUNTS['changed']} changed, {COUNTS['noop']} no-op, {COUNTS['skipped']} off-host, {COUNTS['warn']} warning(s) ===")


if __name__ == '__main__':
    main()
