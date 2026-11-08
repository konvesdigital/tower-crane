#!/usr/bin/env python3
"""
update_consumers.py - hub-operator "update consumers": the push-side counterpart to each
registered consumer's own pull-side `update` skill. Scope is identical - hooks, toolkit Track-1
skills (STANDALONE_SKILLS), and mandatory/default-on protocol pieces (SKILL_PIECES) a consumer
hasn't adopted yet. Never shared_resources content.

Reuses scan_consumer_update.py's per-project scan/apply functions directly against every
registered consumer's own path, one at a time. A consumer registered on another machine's clone is
skipped silently.

Two calls:
  --check (default)   scan every locally-reachable consumer and print one aggregated, indexed list
                       across all of them (grouped by consumer).
  --apply <spec>       apply items by their printed number (comma-separated) or 'all', across
                       every consumer shown in the last --check in the same process.

Registry write-back: this script runs in the hub and owns consumers\\<slug>.md directly, so an
applied hook/piece updates that registry entry's opted_in:/imported: list immediately, plus a
plain audit-trail note. A STANDALONE_SKILLS item (e.g. `update`, `commands`) gets only the
audit-trail note - no yaml `imported:` row for a skill with no @import companion.
"""

import argparse
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config_lib import get_shared_config, commit_consumer_changes
from check_tower_crane import parse_registry, CONSUMERS_DIR
from registry_lib import host_path, reconcile_scope_floor
from scan_consumer_update import (
    SKILL_PIECES, print_groups, optional_note, optional_names, read_consumer_state, all_items,
    apply_hook, apply_stale_hook,
    apply_skill, apply_piece, apply_private, apply_permissions, apply_block_items, split_keep,
    block_item_lines, exceptions_reminder, reset_exceptions,
)

SHARED_ROOT = Path(__file__).resolve().parent.parent  # toolkit\


def local_consumers(this_host, consumer_filter=None):
    if not CONSUMERS_DIR.is_dir():
        return []
    out = []
    for f in sorted(CONSUMERS_DIR.glob('*.md')):
        if consumer_filter and f.stem != consumer_filter:
            continue
        c = parse_registry(f)
        if c is None:
            print(f"  [skip] {f.name}: no parseable yaml registry block.")
            continue
        # 2-host write-back floor - applies to every consumer this tool touches.
        if reconcile_scope_floor(f, c):
            print(f"  [fixed] {f.stem}: scope -> multi_machine (2+ hosts: entries present).")
        if this_host not in c['hosts']:
            print(f"  [skip] {c['name']}: not connected on this machine ('{this_host}').")
            continue
        out.append(c)
    return out


def scan_all(cfg, consumers, this_host, include_optional=False):
    """Returns an ordered dict-like list of (slug, {'consumer': c, 'project_root': Path,
    'items': [...], 'omitted': [optional names left out]}) for every consumer that has at least
    one item to act on, or optional items worth mentioning."""
    result = []
    for c in consumers:
        this_path = host_path(c, this_host)
        project_root = Path(this_path)
        if not (project_root / 'CLAUDE.md').exists():
            print(f"  [skip] {c['name']}: no CLAUDE.md at {this_path} - path stale or moved?")
            continue
        state = read_consumer_state(project_root)
        items = all_items(cfg, state, project_root, include_optional)
        omitted = [] if include_optional else optional_names(cfg, state, project_root)
        if items or omitted:
            slug = Path(c['file']).stem
            result.append((slug, {'consumer': c, 'project_root': project_root, 'items': items,
                                  'omitted': omitted}))
    return result


def print_all(scanned):
    """Prints the aggregated, globally-numbered listing: per consumer, items under REMOVE / REPLACE /
    ADD / FIX BY HAND headings (OPTIONAL only with --include-optional, otherwise one trailing note).
    Returns the flat (slug, item) index list the printed numbers refer to, in print order."""
    if not any(data['items'] or data['omitted'] for _, data in scanned):
        print("Nothing to change - every locally-reachable consumer already has everything the "
              "hub currently expects.")
        return []
    global_index = []
    n = 0
    n_items = sum(len(data['items']) for _, data in scanned)
    print(f"=== AVAILABLE: {n_items} item(s) across {len(scanned)} consumer(s) ===")
    for slug, data in scanned:
        c = data['consumer']
        print(f"\n-- {c['name']} ({slug}) --")
        if not data['items']:
            print("  Nothing to change.")
        for slug_item in data['items']:
            global_index.append((slug, slug_item))
        n += print_groups(data['items'], first_number=n + 1, indent='')
        note = optional_note(data['omitted'])
        if note:
            print(note)
    print("=== END AVAILABLE ===")
    return global_index


def _yaml_add_list_item(yaml_text, key, entry_lines):
    """Appends entry_lines (already indented, e.g. ['  - tool: x', '    since: 2026-08-02']) to
    the block-style list under `key:` in yaml_text, converting a flow-style `key: []` to
    block-style first if that's the form found. Inserts a fresh `key:` block at the end if the
    key isn't present at all (shouldn't happen - the scaffolder always writes opted_in/imported)."""
    lines = yaml_text.splitlines()
    out = []
    i = 0
    inserted = False
    while i < len(lines):
        line = lines[i]
        m = re.match(rf'^{re.escape(key)}:\s*(\[\])?\s*$', line)
        if m:
            if m.group(1) == '[]':
                out.append(f'{key}:')
                out.extend(entry_lines)
                inserted = True
                i += 1
                continue
            out.append(line)
            i += 1
            while i < len(lines) and (lines[i].startswith('  ') or lines[i].strip() == ''):
                out.append(lines[i])
                i += 1
            out.extend(entry_lines)
            inserted = True
            continue
        out.append(line)
        i += 1
    if not inserted:
        out.append(f'{key}:')
        out.extend(entry_lines)
    return '\n'.join(out)


def _yaml_remove_list_item(yaml_text, key, tool):
    """Removes the `  - tool: <tool>` row (and its indented continuation lines, e.g. `since:`)
    from the block-style list under `key:`. No-op if the key or row isn't there."""
    lines = yaml_text.splitlines()
    out = []
    in_key = False
    i = 0
    while i < len(lines):
        line = lines[i]
        if re.match(rf'^{re.escape(key)}:', line):
            in_key = True
            out.append(line)
            i += 1
            continue
        if in_key and line and not line.startswith((' ', '\t')):
            in_key = False
        if in_key and re.match(rf'^\s+-\s+tool:\s*{re.escape(tool)}\s*$', line):
            i += 1
            while i < len(lines) and re.match(r'^\s{4,}\S', lines[i]) and not re.match(r'^\s+-\s', lines[i]):
                i += 1
            continue
        out.append(line)
        i += 1
    return '\n'.join(out)


def update_registry_entry(registry_path, entries, today):
    """entries: list of (category, name) tuples actually applied this run for this consumer.
    Rewrites opted_in:/imported: directly (hub-owned file, no ticket needed for this path) and
    appends a plain audit-trail note. A STANDALONE_SKILLS ('skill') entry gets the note only -
    matches the existing no-yaml-row convention for skills with no @import companion."""
    raw = registry_path.read_text(encoding='utf-8')
    m = re.search(r'(```yaml\s*\r?\n)(.*?)(\r?\n```)', raw, re.DOTALL)
    if not m:
        print(f"  [MANUAL] {registry_path.name}: no parseable yaml block - update opted_in/imported by hand.")
        return
    yaml_text = m.group(2)

    hook_names = [name for cat, name in entries if cat == 'hook']
    piece_names = [name for cat, name in entries if cat == 'piece']
    skill_names = [name for cat, name in entries if cat == 'skill']
    private_names = [name for cat, name in entries if cat == 'private']
    stale_names = [name for cat, name in entries if cat == 'stale_hook']
    permission_names = [name for cat, name in entries if cat == 'permission']

    for tool in hook_names:
        if f"tool: {tool}" in yaml_text:
            continue
        yaml_text = _yaml_add_list_item(yaml_text, 'opted_in', [f'  - tool: {tool}', f'    since: {today}'])

    for tool in stale_names:
        yaml_text = _yaml_remove_list_item(yaml_text, 'opted_in', tool)
        yaml_text = _yaml_remove_list_item(yaml_text, 'private_opted_in', tool)

    for p in piece_names:
        sp = SKILL_PIECES.get(p)
        piece_field = sp['companion'] if sp else p
        if f"piece: {piece_field}" in yaml_text:
            continue
        yaml_text = _yaml_add_list_item(yaml_text, 'imported', [f'  - piece: {piece_field}', f'    since: {today}'])

    # Both hook- and skill-kind private items get a row here.
    for tool in private_names:
        if f"tool: {tool}" in yaml_text:
            continue
        yaml_text = _yaml_add_list_item(yaml_text, 'private_opted_in', [f'  - tool: {tool}', f'    since: {today}'])

    new_raw = raw[:m.start(2)] + yaml_text + raw[m.end(2):]

    note_items = (hook_names + [f'removal of retired hook {t}' for t in stale_names] + piece_names
                  + skill_names + private_names + permission_names)
    if note_items:
        note = (f"\n**`update consumers` applied {', '.join(note_items)} — {today}, pushed "
                f"directly from the hub (no filing ticket needed; the hub owns this file).**\n")
        fence_end = new_raw.index('```', new_raw.index('```yaml') + 7) + 3
        new_raw = new_raw[:fence_end] + '\n' + note + new_raw[fence_end:]

    registry_path.write_text(new_raw, encoding='utf-8', newline='\n')
    print(f"  [registry] {registry_path.name} updated directly (opted_in/imported + audit note).")


def do_apply(cfg, scanned, global_index, spec, today, keep_spec=None):
    numbers, keeps = split_keep([it for _, it in global_index], spec, keep_spec)
    if not numbers and not keeps:
        print("Nothing valid to apply.")
        return
    scanned_by_slug = dict(scanned)
    per_consumer_writeback = {}
    block_work = {}  # slug -> {'patch': [items], 'keep': [items]}
    for i in keeps:
        slug, item = global_index[i - 1]
        block_work.setdefault(slug, {'patch': [], 'keep': []})['keep'].append(item)
    for i in numbers:
        slug, item = global_index[i - 1]
        data = scanned_by_slug[slug]
        c, project_root = data['consumer'], data['project_root']
        print(f"[{i}] {c['name']} :: {item['name']} ({item['category']}):")
        if item['category'] == 'hook':
            if apply_hook(project_root, cfg, item):
                per_consumer_writeback.setdefault(slug, []).append(('hook', item['name']))
        elif item['category'] == 'stale_hook':
            if apply_stale_hook(project_root, cfg, item):
                per_consumer_writeback.setdefault(slug, []).append(('stale_hook', item['name']))
        elif item['category'] == 'skill':
            if apply_skill(project_root, cfg, item):
                per_consumer_writeback.setdefault(slug, []).append(('skill', item['name']))
        elif item['category'] == 'piece':
            if apply_piece(project_root, cfg, item):
                per_consumer_writeback.setdefault(slug, []).append(('piece', item['name']))
        elif item['category'] == 'private':
            if apply_private(project_root, cfg, item):
                per_consumer_writeback.setdefault(slug, []).append(('private', item['name']))
        elif item['category'] == 'permission':
            if apply_permissions(project_root, cfg, item):
                per_consumer_writeback.setdefault(slug, []).append(('permission', item['name']))
        elif item['category'] == 'claude_md_block':
            block_work.setdefault(slug, {'patch': [], 'keep': []})['patch'].append(item)
        elif item['category'] == 'claude_md_manual':
            print(f"  [MANUAL] {item['detail']}")

    # CLAUDE.md block: each consumer's chosen hunks are written together (offsets shift otherwise).
    # No registry change - the block isn't a registry fact - but the consumer's repo still gets a commit.
    block_changed = {}
    for slug, work in block_work.items():
        c = scanned_by_slug[slug]['consumer']
        print(f"{c['name']} :: CLAUDE.md block:")
        if apply_block_items(scanned_by_slug[slug]['project_root'], work['patch'], work['keep']):
            block_changed[slug] = (f"claude_md_block: {len(work['patch'])} patched, "
                                   f"{len(work['keep'])} kept")

    # Commits and pushes into each consumer's own repo, since no live session there would
    # otherwise notice and checkpoint this change.
    for slug in dict.fromkeys(list(per_consumer_writeback) + list(block_changed)):
        entries = per_consumer_writeback.get(slug, [])
        c = scanned_by_slug[slug]['consumer']
        if entries:
            update_registry_entry(Path(c['file']), entries, today)
        names = ', '.join([f"{cat}:{name}" for cat, name in entries]
                          + ([block_changed[slug]] if slug in block_changed else []))
        result = commit_consumer_changes(
            scanned_by_slug[slug]['project_root'],
            f"Tower Crane sync: applied {names}", log=print,
            config=cfg, imports=[i['name'] for i in c['imported']], shared_root=SHARED_ROOT)
        if result == 'committed-pushed':
            print(f"  [git] {c['name']}: committed and pushed in its own repo.")
        elif result == 'committed-no-remote':
            print(f"  [git] {c['name']}: committed in its own repo (no origin remote to push to).")
        elif result == 'reconciled-pushed':
            # A real divergence was auto-resolved by
            # resetting and regenerating this host's own Tower-Crane-owned values.
            print(f"  [git] {c['name']}: push conflict auto-reconciled (reset + regenerated), "
                  f"committed and pushed.")


def main():
    parser = argparse.ArgumentParser(
        description="Hub-operator `update consumers`: bulk-push hub functionality (hooks, "
                     "toolkit skills, protocol pieces) to every locally-reachable registered consumer."
    )
    parser.add_argument('--consumer', default=None, help="Scope to one consumer slug. Default: all local consumers.")
    parser.add_argument('--apply', default=None,
                         help="Comma-separated global item numbers from the last --check listing, or 'all'.")
    parser.add_argument('--keep', default=None,
                         help="Comma-separated global numbers of CLAUDE.md block deviations to keep as "
                              "recorded exceptions instead of patching (alone, or with --apply all).")
    parser.add_argument('--reset-exceptions', action='store_true',
                         help="Clear recorded CLAUDE.md exceptions for every consumer in this run "
                              "(scope with --consumer) and commit that in each consumer's own repo; "
                              "the scan then lists them as ordinary deviations.")
    parser.add_argument('--include-optional', action='store_true',
                         help="Also list OPTIONAL items (private tools a consumer never opted into). "
                              "Pass it on the --apply call too, so the numbers match the listing.")
    args = parser.parse_args()

    cfg = get_shared_config(SHARED_ROOT)
    this_host = str(cfg.get('host_id', ''))
    consumers = local_consumers(this_host, args.consumer)
    if args.consumer and not consumers:
        print(f"[ABORT] No local registry entry for consumer '{args.consumer}'.")
        sys.exit(1)

    if args.reset_exceptions:
        reset_all_exceptions(cfg, consumers, this_host)

    scanned = scan_all(cfg, consumers, this_host, args.include_optional)
    global_index = print_all(scanned)

    if args.apply is None and args.keep is None:
        if global_index:
            print()
            print("Re-run with --apply <numbers-or-'all'> to push (e.g. --apply 1,3 or --apply all). "
                  "Add --keep <numbers> to keep a CLAUDE.md block deviation as an exception instead.")
        print_reminders(consumers, this_host)
        return

    if not global_index:
        print("Nothing available to apply - run without --apply first, or nothing has changed.")
        print_reminders(consumers, this_host)
        return

    do_apply(cfg, scanned, global_index, args.apply, date.today().isoformat(), args.keep)
    print_reminders(consumers, this_host)


def reset_all_exceptions(cfg, consumers, this_host):
    """Clear each consumer's recorded CLAUDE.md exceptions and commit that in its own repo."""
    for c in consumers:
        project_root = Path(host_path(c, this_host))
        if not reset_exceptions(project_root):
            print(f"  [reset] {c['name']}: no recorded CLAUDE.md exceptions.")
            continue
        print(f"  [reset] {c['name']}: recorded CLAUDE.md exceptions cleared.")
        result = commit_consumer_changes(
            project_root, "Tower Crane sync: reset CLAUDE.md exceptions", log=print,
            config=cfg, imports=[i['name'] for i in c['imported']], shared_root=SHARED_ROOT)
        if result in ('committed-pushed', 'committed-no-remote', 'reconciled-pushed'):
            print(f"  [git] {c['name']}: reset committed in its own repo.")


def print_reminders(consumers, this_host):
    """One closing line per consumer that still has recorded CLAUDE.md exceptions - printed after
    the work, never a question. Covers consumers with nothing new pending too."""
    lines = []
    for c in consumers:
        project_root = Path(host_path(c, this_host))
        if (project_root / 'CLAUDE.md').exists():
            line = exceptions_reminder(project_root, label=f"{c['name']}: ")
            if line:
                lines.append(line.replace('say "reset exceptions"',
                                          f'say "reset exceptions" (or "reset exceptions for {Path(c["file"]).stem}")'))
    if lines:
        print()
        print('\n'.join(lines))


if __name__ == '__main__':
    main()
