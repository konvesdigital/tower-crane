#!/usr/bin/env python3
"""
scan_consumer_update.py - the deterministic scan/apply half of the consumer-side `update` skill
(design\\consumer_update.md). Lists hub features (hooks, toolkit Track-1 skills, shared_resources
insights, mandatory/default-on protocol pieces) a consumer project hasn't adopted yet, and can
apply the purely-mechanical categories on request.

Mirrors update_toolkit.py's indexed list-and-choose shape without its trust-review gate: the
source here is the same local hub a consumer already imports mandatory pieces from at the same
trust level, so there is no diff to review - just a list and a choice.

Two calls:
  --check (default)   scan and print an indexed list of everything available but not adopted.
  --apply <spec>       apply items by their printed number (comma-separated) or 'all'. A
                       shared_resources insight is never auto-applied here - it's a negotiated
                       draft (templates\\shared_resources.md's own Apply procedure), not a
                       mechanical copy; selecting one just prints a pointer to that procedure.

Numbering is recomputed fresh on every call (no persisted pending-list file, unlike
update_toolkit.py) - deterministic given unchanged project/hub state, which holds across the
--check then --apply calls of one sitting. Re-run without --apply first if in doubt.

Ground truth for "already have" is this project's own local state (.claude\\settings.json,
CLAUDE.md @import lines, .claude\\skills\\ listing) - never the hub's consumers\\<slug>.md
registry entry (design\\consumer_update.md's "Ground truth for 'already have'"). Registry
write-back for hooks/skills this script applies is a separate, manual filing-channel step - see
the reminder this script prints after an --apply that touches either category.
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config_lib import get_shared_config, get_expanded_optin

SHARED_ROOT = Path(__file__).resolve().parent.parent  # toolkit\
TEMPLATES_DIR = SHARED_ROOT / 'templates'
OPTINS_DIR = TEMPLATES_DIR / 'optins'
SKILLS_DIR = TEMPLATES_DIR / 'skills'
PROJECT_ROOT = SHARED_ROOT.parent  # hub root
CATALOG_PATH = PROJECT_ROOT / 'shared_resources' / 'CATALOG.md'

# Mirrors scripts\new_consumer.py's SKILL_PIECES / check_tower_crane.py's SKILL_PIECES - keep in
# sync. 'update' itself is deliberately NOT in here: it has no always-resident companion (design\
# consumer_update.md - purely Track 1, no resume-time check), so it falls out as an ordinary
# toolkit skill in scan_skills() instead.
SKILL_PIECES = {
    'filing': {'companion': 'filing_resume_check', 'skills': ['filing']},
    'continuity': {'companion': 'continuity_resume_check', 'skills': ['checkpoint', 'archive']},
}
MANDATORY_OR_DEFAULT_PIECES = ['filing', 'compliance', 'continuity']


def read_consumer_state(project_root):
    claude_md_path = project_root / 'CLAUDE.md'
    md_text = claude_md_path.read_text(encoding='utf-8') if claude_md_path.exists() else ''
    md_imports = set(re.findall(r'@\S*?templates/(\w+)\.md', md_text))

    settings_path = project_root / '.claude' / 'settings.json'
    settings = {}
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text(encoding='utf-8')) or {}
        except json.JSONDecodeError:
            settings = {}

    skills_dir = project_root / '.claude' / 'skills'
    have_skills = {d.name for d in skills_dir.iterdir() if d.is_dir()} if skills_dir.is_dir() else set()

    # Text searched for shared_resources adoption markers - CLAUDE.md plus every project-local
    # skill stub (the two places "Apply" (templates\shared_resources.md) can write one).
    marker_text = md_text
    if skills_dir.is_dir():
        for f in skills_dir.glob('*/SKILL.md'):
            marker_text += '\n' + f.read_text(encoding='utf-8')

    return {'md_text': md_text, 'md_imports': md_imports, 'settings': settings,
            'have_skills': have_skills, 'marker_text': marker_text}


def scan_hooks(cfg, state):
    items = []
    have_hooks = state['settings'].get('hooks') if isinstance(state['settings'], dict) else None
    for optin_path in sorted(OPTINS_DIR.glob('*.json')):
        tool = optin_path.stem
        expanded = get_expanded_optin(optin_path, cfg)
        missing = False
        for evt, groups in expanded.get('hooks', {}).items():
            canon = [json.dumps(g, separators=(',', ':')).replace('\\\\', '/') for g in groups]
            have = []
            if isinstance(have_hooks, dict) and evt in have_hooks:
                have = [json.dumps(g, separators=(',', ':')).replace('\\\\', '/') for g in have_hooks[evt]]
            if any(c not in have for c in canon):
                missing = True
        if missing:
            items.append({'category': 'hook', 'name': tool, 'detail': f'templates/optins/{tool}.json'})
    return items


def scan_skills(state):
    covered = {name for sp in SKILL_PIECES.values() for name in sp['skills']}
    items = []
    if not SKILLS_DIR.is_dir():
        return items
    for d in sorted(SKILLS_DIR.iterdir(), key=lambda p: p.name):
        if not d.is_dir() or d.name in covered or d.name in state['have_skills']:
            continue
        items.append({'category': 'skill', 'name': d.name, 'detail': f'templates/skills/{d.name}/SKILL.md'})
    return items


def scan_pieces(state):
    items = []
    for p in MANDATORY_OR_DEFAULT_PIECES:
        if p in state['md_imports']:
            continue
        sp = SKILL_PIECES.get(p)
        if sp:
            if sp['companion'] in state['md_imports'] and all(s in state['have_skills'] for s in sp['skills']):
                continue
            detail = f"companion '{sp['companion']}' + skill stub(s): " + ', '.join(sp['skills'])
        else:
            detail = f'templates/{p}.md'
        items.append({'category': 'piece', 'name': p, 'detail': detail})
    return items


def parse_catalog():
    rows = []
    if not CATALOG_PATH.exists():
        return rows
    in_table = False
    for line in CATALOG_PATH.read_text(encoding='utf-8').splitlines():
        if line.startswith('| Name '):
            in_table = True
            continue
        if not in_table:
            continue
        if line.startswith('|---'):
            continue
        if not line.startswith('|'):
            in_table = False
            continue
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells) >= 6:
            rows.append({'name': cells[0], 'kind': cells[1], 'file': cells[2],
                         'description': cells[3], 'added': cells[4], 'status': cells[5]})
    return rows


def scan_insights(state):
    items = []
    for row in sorted(parse_catalog(), key=lambda r: r['name']):
        if row['status'].startswith('Archived'):
            continue
        marker_re = re.compile(r'shared_resources:\s*' + re.escape(row['name']) + r'\s+adopted')
        if marker_re.search(state['marker_text']):
            continue
        items.append({'category': 'insight', 'name': row['name'], 'detail': f"{row['kind']} - {row['file']}"})
    return items


def print_items(items):
    if not items:
        print("Nothing available - this project already has everything the hub currently offers.")
        return
    labels = {'hook': 'Hook opt-ins', 'skill': 'Toolkit skills', 'piece': 'Protocol pieces',
              'insight': 'Shared-resources insights'}
    print(f"=== AVAILABLE ({len(items)}) ===")
    current_cat = None
    for i, it in enumerate(items, 1):
        if it['category'] != current_cat:
            current_cat = it['category']
            print(f"-- {labels[current_cat]} --")
        print(f"  [{i}] {it['name']}  ({it['detail']})")
    print("=== END AVAILABLE ===")


def _insert_import_line(md_text, line):
    """Insert `line` at the end of the '## Shared Workflow Protocol' section. Returns None if
    that heading isn't found (caller falls back to telling the human to add it by hand); returns
    md_text unchanged if the line is already present."""
    heading = '## Shared Workflow Protocol'
    idx = md_text.find(heading)
    if idx == -1:
        return None
    after_heading = idx + len(heading)
    rest = md_text[after_heading:]
    m = re.search(r'\n## ', rest)
    end = m.start() if m else len(rest)
    block, tail = rest[:end], rest[end:]
    if line in block:
        return md_text
    new_block = block.rstrip('\n') + '\n' + line + '\n'
    return md_text[:after_heading] + new_block + tail


def apply_hook(project_root, cfg, item):
    tool = item['name']
    expanded = get_expanded_optin(OPTINS_DIR / f'{tool}.json', cfg)
    settings_path = project_root / '.claude' / 'settings.json'
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings = {}
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text(encoding='utf-8')) or {}
        except json.JSONDecodeError:
            settings = {}
    settings.setdefault('hooks', {})
    for evt, groups in expanded.get('hooks', {}).items():
        existing = settings['hooks'].setdefault(evt, [])
        existing_json = [json.dumps(e, separators=(',', ':')) for e in existing]
        for entry in groups:
            entry_json = json.dumps(entry, separators=(',', ':'))
            if entry_json not in existing_json:
                existing.append(entry)
    settings_path.write_text(json.dumps(settings, indent=2), encoding='utf-8', newline='\n')
    print(f"  [applied] hook '{tool}' merged into .claude/settings.json")
    return True  # needs registry write-back


def apply_skill(project_root, cfg, item):
    name = item['name']
    stub_src = SKILLS_DIR / name / 'SKILL.md'
    stub_content = stub_src.read_text(encoding='utf-8').replace('{{IMPORT_BASE}}', str(cfg['import_base']))
    skill_dir = project_root / '.claude' / 'skills' / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / 'SKILL.md').write_text(stub_content, encoding='utf-8', newline='\n')
    print(f"  [applied] skill '{name}' written to .claude/skills/{name}/SKILL.md")
    return True  # needs registry write-back


def apply_piece(project_root, cfg, item):
    p = item['name']
    sp = SKILL_PIECES.get(p)
    if sp:
        for skill_name in sp['skills']:
            stub_path = project_root / '.claude' / 'skills' / skill_name / 'SKILL.md'
            if stub_path.exists():
                continue
            stub_src = SKILLS_DIR / skill_name / 'SKILL.md'
            stub_content = stub_src.read_text(encoding='utf-8').replace('{{IMPORT_BASE}}', str(cfg['import_base']))
            stub_path.parent.mkdir(parents=True, exist_ok=True)
            stub_path.write_text(stub_content, encoding='utf-8', newline='\n')
            print(f"  [applied] skill '{skill_name}' written to .claude/skills/{skill_name}/SKILL.md")
        line = f"@{cfg['import_base']}/{sp['companion']}.md"
    else:
        line = f"@{cfg['import_base']}/{p}.md"

    claude_md_path = project_root / 'CLAUDE.md'
    md_text = claude_md_path.read_text(encoding='utf-8') if claude_md_path.exists() else ''
    new_text = _insert_import_line(md_text, line)
    if new_text is None:
        print(f"  [MANUAL] couldn't find '## Shared Workflow Protocol' in CLAUDE.md - add this "
              f"line yourself: {line}")
    elif new_text != md_text:
        claude_md_path.write_text(new_text, encoding='utf-8', newline='\n')
        print(f"  [applied] added '{line}' to CLAUDE.md")
    return bool(sp)  # needs registry write-back only when a skill stub was (or already is) involved


def apply_insight(item):
    print(f"  [manual] '{item['name']}' is a shared_resources insight - not applied here. Adopt it "
          "via templates\\shared_resources.md's own Apply procedure (negotiated trigger/summary, "
          "confirm before writing), e.g. say \"shared resources - apply " + item['name'] + "\".")
    return False


def resolve_selection(spec, items):
    if spec.strip().lower() == 'all':
        return list(range(1, len(items) + 1))
    out = []
    for tok in spec.split(','):
        tok = tok.strip()
        if not tok:
            continue
        if not tok.isdigit() or not (1 <= int(tok) <= len(items)):
            print(f"[WARN] '{tok}' isn't a valid item number (1..{len(items)}) - skipping.")
            continue
        out.append(int(tok))
    return out


def do_apply(project_root, cfg, items, spec):
    numbers = resolve_selection(spec, items)
    if not numbers:
        print("Nothing valid to apply.")
        return
    writeback = []
    for i in numbers:
        item = items[i - 1]
        print(f"[{i}] {item['name']} ({item['category']}):")
        if item['category'] == 'hook':
            if apply_hook(project_root, cfg, item):
                writeback.append(item['name'])
        elif item['category'] == 'skill':
            if apply_skill(project_root, cfg, item):
                writeback.append(item['name'])
        elif item['category'] == 'piece':
            if apply_piece(project_root, cfg, item):
                writeback.append(item['name'])
        elif item['category'] == 'insight':
            apply_insight(item)
    if writeback:
        print()
        print("[reminder] The hub's consumers/<slug>.md registry doesn't know about this yet - file "
              "a short registration-update ticket (templates/filing.md's filing shape) naming: "
              + ', '.join(writeback) + ". Needed so scripts/relocate.py and future opted-in-tool "
              "checks stay accurate; not needed for insights or flat @import-only pieces.")


def main():
    parser = argparse.ArgumentParser(
        description="Consumer-side `update`: scan/apply hub features this project hasn't adopted yet."
    )
    parser.add_argument('--project-root', default='.', help="This consumer project's root (default: cwd).")
    parser.add_argument('--apply', default=None,
                         help="Comma-separated item numbers from the last --check listing, or 'all'. "
                              "Applies hook/skill/piece items; an insight item just prints a pointer.")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    if not (project_root / 'CLAUDE.md').exists():
        print(f"[ABORT] No CLAUDE.md at {project_root} - is --project-root correct?")
        sys.exit(1)

    cfg = get_shared_config(SHARED_ROOT)
    state = read_consumer_state(project_root)
    items = scan_hooks(cfg, state) + scan_skills(state) + scan_pieces(state) + scan_insights(state)

    if args.apply is None:
        print_items(items)
        if items:
            print()
            print("Re-run with --apply <numbers-or-'all'> to adopt (e.g. --apply 1,3 or --apply all).")
        return

    if not items:
        print("Nothing available to apply - run without --apply first, or nothing has changed.")
        return

    do_apply(project_root, cfg, items, args.apply)


if __name__ == '__main__':
    main()
