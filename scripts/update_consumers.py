#!/usr/bin/env python3
"""
update_consumers.py - hub-operator "update consumers": the push-side counterpart to each
registered consumer's own pull-side `update` skill (design\\consumer_update.md). Scope is
identical - hooks, toolkit Track-1 skills (STANDALONE_SKILLS), and mandatory/default-on protocol
pieces (SKILL_PIECES) a consumer hasn't adopted yet. Never shared_resources content - that stays
the "shared resources" command's own job, on either side.

Reuses scan_consumer_update.py's per-project scan/apply functions directly (no duplicated logic)
against every registered consumer's own path, one at a time. Federate model (design\\portability.md):
a consumer registered on another machine's clone is skipped silently, same as check_tower_crane.py
and relocate.py already do.

Two calls:
  --check (default)   scan every locally-reachable consumer and print one aggregated, indexed list
                       across all of them (grouped by consumer).
  --apply <spec>       apply items by their printed number (comma-separated) or 'all', across
                       every consumer shown in the last --check in the same process.

Registry write-back: unlike the per-consumer `update` skill (which can only print a "file a
ticket" reminder, since a consumer session has no write access to the hub's own repo), this script
runs IN the hub and owns consumers\\<slug>.md directly - so an applied hook/piece updates that
registry entry's opted_in:/imported: list immediately, plus a plain audit-trail note, and no
filing-ticket round-trip is needed for this path. A STANDALONE_SKILLS item (e.g. `update`,
`commands`) gets only the audit-trail note - matching the existing convention (see
consumers\\geo_rank_tracker.md's own prose entries for these) of no yaml `imported:` row for a
skill with no @import companion.
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
    SKILL_PIECES, read_consumer_state, scan_hooks, scan_skills, scan_pieces, scan_private,
    apply_hook, apply_skill, apply_piece, apply_private, resolve_selection,
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
        # 2-host write-back floor (design\multi_machine_hub.md) - applies to every consumer this
        # tool touches, regardless of whether it's reachable on THIS machine.
        if reconcile_scope_floor(f, c):
            print(f"  [fixed] {f.stem}: scope -> multi_machine (2+ hosts: entries present).")
        if this_host not in c['hosts']:
            print(f"  [skip] {c['name']}: not connected on this machine ('{this_host}').")
            continue
        out.append(c)
    return out


def scan_all(cfg, consumers, this_host):
    """Returns an ordered dict-like list of (slug, {'consumer': c, 'project_root': Path,
    'items': [...]}) for every consumer that has at least one available item."""
    result = []
    for c in consumers:
        this_path = host_path(c, this_host)
        project_root = Path(this_path)
        if not (project_root / 'CLAUDE.md').exists():
            print(f"  [skip] {c['name']}: no CLAUDE.md at {this_path} - path stale or moved?")
            continue
        state = read_consumer_state(project_root)
        items = scan_hooks(cfg, state) + scan_skills(state) + scan_pieces(state) + scan_private(cfg, state)
        if items:
            slug = Path(c['file']).stem
            result.append((slug, {'consumer': c, 'project_root': project_root, 'items': items}))
    return result


def print_all(scanned):
    """Prints the aggregated, globally-numbered listing grouped by consumer. Returns the flat
    (slug, item) index list the printed numbers refer to, in print order."""
    if not scanned:
        print("Nothing available - every locally-reachable consumer already has everything the "
              "hub currently offers.")
        return []
    labels = {'hook': 'Hook opt-ins', 'skill': 'Toolkit skills', 'piece': 'Protocol pieces',
              'private': 'Private tools (toolkit_private)'}
    global_index = []
    n = 0
    print(f"=== AVAILABLE across {len(scanned)} consumer(s) ===")
    for slug, data in scanned:
        c = data['consumer']
        print(f"\n-- {c['name']} ({slug}) --")
        current_cat = None
        for it in data['items']:
            n += 1
            global_index.append((slug, it))
            if it['category'] != current_cat:
                current_cat = it['category']
                print(f"   [{labels[current_cat]}]")
            print(f"  [{n}] {it['name']}  ({it['detail']})")
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

    for tool in hook_names:
        if f"tool: {tool}" in yaml_text:
            continue
        yaml_text = _yaml_add_list_item(yaml_text, 'opted_in', [f'  - tool: {tool}', f'    since: {today}'])

    for p in piece_names:
        sp = SKILL_PIECES.get(p)
        piece_field = sp['companion'] if sp else p
        if f"piece: {piece_field}" in yaml_text:
            continue
        yaml_text = _yaml_add_list_item(yaml_text, 'imported', [f'  - piece: {piece_field}', f'    since: {today}'])

    # design\private_tools.md decision 6: both hook- and skill-kind private items get a row here
    # (unlike public STANDALONE_SKILLS, there's no separate discovery-filter list on the private
    # side - this row is what the extended check_tower_crane.py needs to know to check the name
    # against toolkit_private\).
    for tool in private_names:
        if f"tool: {tool}" in yaml_text:
            continue
        yaml_text = _yaml_add_list_item(yaml_text, 'private_opted_in', [f'  - tool: {tool}', f'    since: {today}'])

    new_raw = raw[:m.start(2)] + yaml_text + raw[m.end(2):]

    note_items = hook_names + piece_names + skill_names + private_names
    if note_items:
        note = (f"\n**`update consumers` applied {', '.join(note_items)} — {today}, pushed "
                f"directly from the hub (no filing ticket needed; the hub owns this file).**\n")
        fence_end = new_raw.index('```', new_raw.index('```yaml') + 7) + 3
        new_raw = new_raw[:fence_end] + '\n' + note + new_raw[fence_end:]

    registry_path.write_text(new_raw, encoding='utf-8', newline='\n')
    print(f"  [registry] {registry_path.name} updated directly (opted_in/imported + audit note).")


def do_apply(cfg, scanned, global_index, spec, today):
    numbers = resolve_selection(spec, global_index)
    if not numbers:
        print("Nothing valid to apply.")
        return
    scanned_by_slug = dict(scanned)
    per_consumer_writeback = {}
    for i in numbers:
        slug, item = global_index[i - 1]
        data = scanned_by_slug[slug]
        c, project_root = data['consumer'], data['project_root']
        print(f"[{i}] {c['name']} :: {item['name']} ({item['category']}):")
        if item['category'] == 'hook':
            if apply_hook(project_root, cfg, item):
                per_consumer_writeback.setdefault(slug, []).append(('hook', item['name']))
        elif item['category'] == 'skill':
            if apply_skill(project_root, cfg, item):
                per_consumer_writeback.setdefault(slug, []).append(('skill', item['name']))
        elif item['category'] == 'piece':
            if apply_piece(project_root, cfg, item):
                per_consumer_writeback.setdefault(slug, []).append(('piece', item['name']))
        elif item['category'] == 'private':
            if apply_private(project_root, cfg, item):
                per_consumer_writeback.setdefault(slug, []).append(('private', item['name']))

    # design\resource_sharing_model.md's "Saving now propagates itself" fix, one level down
    # (project_progress.md's 2026-08-11 Work Log): this pushes into a consumer's own repo with no
    # live session there to notice and checkpoint it, so it closes its own loop per consumer
    # instead of leaving uncommitted state behind for a human to remember later.
    for slug, entries in per_consumer_writeback.items():
        c = scanned_by_slug[slug]['consumer']
        update_registry_entry(Path(c['file']), entries, today)
        names = ', '.join(f"{cat}:{name}" for cat, name in entries)
        result = commit_consumer_changes(
            scanned_by_slug[slug]['project_root'],
            f"Tower Crane sync: applied {names}", log=print,
            config=cfg, imports=[i['name'] for i in c['imported']], shared_root=SHARED_ROOT)
        if result == 'committed-pushed':
            print(f"  [git] {c['name']}: committed and pushed in its own repo.")
        elif result == 'committed-no-remote':
            print(f"  [git] {c['name']}: committed in its own repo (no origin remote to push to).")
        elif result == 'reconciled-pushed':
            # design\grt_connectivity_audit.md item (ii): a real divergence was auto-resolved by
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
    args = parser.parse_args()

    cfg = get_shared_config(SHARED_ROOT)
    this_host = str(cfg.get('host_id', ''))
    consumers = local_consumers(this_host, args.consumer)
    if args.consumer and not consumers:
        print(f"[ABORT] No local registry entry for consumer '{args.consumer}'.")
        sys.exit(1)

    scanned = scan_all(cfg, consumers, this_host)
    global_index = print_all(scanned)

    if args.apply is None:
        if global_index:
            print()
            print("Re-run with --apply <numbers-or-'all'> to push (e.g. --apply 1,3 or --apply all).")
        return

    if not global_index:
        print("Nothing available to apply - run without --apply first, or nothing has changed.")
        return

    do_apply(cfg, scanned, global_index, args.apply, date.today().isoformat())


if __name__ == '__main__':
    main()
