#!/usr/bin/env python3
"""
migrate_consumer_indirection.py - one-time migration of an ALREADY-CONNECTED host onto the
consumer-reference-indirection pointer form (design\\grt_connectivity_audit.md item (iii)).

design\\consumer_reference_indirection.md's original 2026-08-14 decision applied the pointer-file
model to NEW connections only - a brand-new consumer, or a genuinely new host joining an
already-registered one - on the reasoning that new_consumer.py's host-merge branch already
re-scaffolds a joining host's files, so it gets the new form for free. An ALREADY-connected host
was left on the old direct-baked-path form indefinitely - not a considered permanent policy, just
cheap and low-risk at the time. That gap is what produced a real cross-host skill-stub collision
(two hosts each baking their own absolute path into the identical tracked files); this
script is the missing one-time conversion path, confirmed against the actual code (not assumed) -
neither new_consumer.py's re-scaffold branch nor relocate.py ever converts an already-connected
host from direct to pointer form on their own.

Because CLAUDE.md's pointer line / hook command / skill-stub prose are shared, tracked content
(identical on every host once written), only ONE connected host needs to run this. Every other
already-connected host converges automatically on its own next relocate.py/resume pass -
config_lib.fix_hub_pointer() already bootstraps a missing hub_pointer.md (not just refreshes an
existing one - confirmed by reading its body), so nothing further is needed there.

Deliberately NOT folded into "connect project" (new_consumer.py) - a command already run routinely
on an already-connected consumer shouldn't silently start rewriting shared tracked content that
affects every other connected host too. This is a separate, explicitly-named, one-time action -
trigger phrase "migrate consumer to reference-indirection" (toolkit\\agents_consumers.md).

No script-level interactive prompt - matching disconnect_consumer.py/remove_hub.py's documented
convention, the confirmation gate is conversational: the calling agent states exactly what will be
rewritten before running this.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config_lib import (
    get_shared_config, write_new_connection_files, collapse_imports_to_pointer,
    build_dispatch_cmd_map, apply_hook_command_fixes, fix_skill_stubs, commit_consumer_changes,
    print_diagnose_inline, HUB_POINTER_IMPORT_LINE,
)
import registry_lib

SHARED_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = SHARED_ROOT.parent
CONSUMERS_DIR = PROJECT_ROOT / 'consumers'
TEMPLATES_DIR = SHARED_ROOT / 'templates'
OPTINS_DIR = TEMPLATES_DIR / 'optins'
PRIVATE_OPTINS_DIR = PROJECT_ROOT / 'toolkit_private' / 'templates' / 'optins'

COMMIT_LABELS = {
    'committed-pushed': "  [git] committed and pushed in this consumer's own repo.",
    'committed-no-remote': "  [git] committed in this consumer's own repo (no origin remote to push to).",
    'reconciled-pushed': "  [git] push conflict auto-reconciled (reset + regenerated), committed and pushed.",
}


def main():
    parser = argparse.ArgumentParser(
        description="One-time migration of THIS already-connected host onto reference-indirection "
                    "form (design\\grt_connectivity_audit.md item (iii)).")
    parser.add_argument('--slug', required=True, help="Registry slug (consumers\\<slug>.md).")
    args = parser.parse_args()

    config = get_shared_config(SHARED_ROOT)
    this_host = config['host_id']

    registry_path = CONSUMERS_DIR / f"{args.slug}.md"
    if not registry_path.exists():
        print_diagnose_inline(config, slug=args.slug)
        raise SystemExit(f"No registry entry for '{args.slug}' at {registry_path}.")
    consumer = registry_lib.parse_registry(registry_path)
    if consumer is None:
        print_diagnose_inline(config, slug=args.slug)
        raise SystemExit(f"{registry_path} isn't parseable.")
    if this_host not in consumer['hosts']:
        raise SystemExit(
            f"'{args.slug}' has no hosts.{this_host} entry - this migration only applies to an "
            "ALREADY-connected host. Use \"connect project\" instead if this host isn't connected yet.")

    target_path = Path(consumer['hosts'][this_host]['path'])
    claude_md_path = target_path / 'CLAUDE.md'
    if not claude_md_path.exists():
        raise SystemExit(f"{claude_md_path} not found.")
    if HUB_POINTER_IMPORT_LINE in claude_md_path.read_text(encoding='utf-8'):
        print(f"'{args.slug}' on this host ('{this_host}') is already on reference-indirection "
              "form. Nothing to do.")
        return

    import_pieces = [i['name'] for i in consumer['imported']]
    tools = [i['name'] for i in consumer['opted_in']]
    private_tools = [i['name'] for i in consumer['private_opted_in']]

    print(f"Migrating '{consumer['name']}' ({args.slug}) on this host ('{this_host}') to "
          "reference-indirection form...")
    write_new_connection_files(target_path, config, import_pieces, SHARED_ROOT, log=print)

    result = collapse_imports_to_pointer(claude_md_path, import_pieces, log=print)
    if result == 'no-match':
        raise SystemExit(f"{claude_md_path} has no recognized @import lines to collapse - "
                          "inspect it by hand before retrying.")

    settings_path = target_path / '.claude' / 'settings.json'
    if settings_path.exists() and (tools or private_tools):
        settings = json.loads(settings_path.read_text(encoding='utf-8'))
        new_cmd = build_dispatch_cmd_map(tools, private_tools, config, OPTINS_DIR, PRIVATE_OPTINS_DIR)
        if apply_hook_command_fixes(settings, new_cmd, tools + private_tools, dry_run=False, log=print,
                                     needs_shell=True):
            settings_path.write_text(json.dumps(settings, indent=2), encoding='utf-8', newline='\n')
            print(f"  wrote  {settings_path} (hook command(s) -> dispatch-wrapper form)")

    fix_skill_stubs(target_path, TEMPLATES_DIR, config['import_base'], dry_run=False, log=print,
                     use_pointer=True)

    result = commit_consumer_changes(
        target_path, f"Tower Crane: migrated to reference-indirection (host: {this_host})",
        log=print, config=config, imports=import_pieces, shared_root=SHARED_ROOT)
    label = COMMIT_LABELS.get(result)
    if label:
        print(label)

    print()
    print("Done. Every OTHER host still connected to this consumer picks up the pointer form "
          "automatically on its own next relocate.py/resume pass - no action needed there.")


if __name__ == '__main__':
    main()
