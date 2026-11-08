#!/usr/bin/env python3
"""
scan_consumer_update.py - the deterministic scan/apply half of the consumer-side `update` skill.
Scope is functionality parity with a fresh new_consumer.py scaffold only - hooks, toolkit Track-1
skills (STANDALONE_SKILLS + SKILL_PIECES), and mandatory/default-on protocol pieces a consumer
project hasn't adopted yet, plus the reverse: hook entries still running a tool the hub has since retired
(offered for removal as 'Retired hooks to remove'). Excludes shared_resources content - that's data, adopted through the
"shared resources" command instead.

Two calls:
  --check (default)   scan and print an indexed list of everything available but not adopted.
  --apply <spec>       apply items by their printed number (comma-separated) or 'all'.

Numbering is recomputed fresh on every call (no persisted pending-list file). Re-run without
--apply first if in doubt.

Ground truth for "already have" is this project's own local state (.claude\\settings.json,
CLAUDE.md @import lines, .claude\\skills\\ listing), never the hub's consumers\\<slug>.md registry
entry. Registry write-back for hooks/skills this script applies is a separate, manual
filing-channel step - see the reminder this script prints after an --apply that touches either
category.
"""

import argparse
import difflib
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config_lib import (
    get_shared_config, get_dispatch_optin, materialize_skill_stub, _LEADING_COMMENT_RE,
    merge_bash_allowlist, dead_hook_tools, strip_dead_hooks,
    find_block_region, render_claude_md_block, load_exceptions, save_exceptions,
    TC_IN_USE_HEADING, WORKFLOW_HEADING, DISCONNECTED_HEADING, HUB_POINTER_IMPORT_LINE,
    ADOPTED_SHARED_RESOURCES_NONE, ADOPTED_LISTING_ANCHOR, EXCEPTIONS_RELPATH,
)
from registry_lib import parse_registry, host_path

SHARED_ROOT = Path(__file__).resolve().parent.parent  # toolkit\
TEMPLATES_DIR = SHARED_ROOT / 'templates'
OPTINS_DIR = TEMPLATES_DIR / 'optins'
SKILLS_DIR = TEMPLATES_DIR / 'skills'
PROJECT_ROOT = SHARED_ROOT.parent  # hub root
# Private, automatic tools living outside toolkit\, never shipped.
# Every entry under PRIVATE_SKILLS_DIR is consumer-offerable.
PRIVATE_ROOT = PROJECT_ROOT / 'toolkit_private'
PRIVATE_OPTINS_DIR = PRIVATE_ROOT / 'templates' / 'optins'
PRIVATE_SKILLS_DIR = PRIVATE_ROOT / 'templates' / 'skills'
CONSUMERS_DIR = PROJECT_ROOT / 'consumers'

_FRONTMATTER_RE = re.compile(r'^---\s*\r?\n(.*?)\r?\n---\s*\r?\n', re.DOTALL)


def read_skill_category(skill_md_path):
    """The `category:` frontmatter field of a toolkit_private skill stub, or None if absent.
    Strips the canonical source's leading maintainer HTML comment first (same regex
    materialize_skill_stub() uses)."""
    if not skill_md_path.exists():
        return None
    text = _LEADING_COMMENT_RE.sub('', skill_md_path.read_text(encoding='utf-8'), count=1)
    m = _FRONTMATTER_RE.search(text)
    if not m:
        return None
    cm = re.search(r'^category:\s*(.+?)\s*$', m.group(1), re.MULTILINE)
    return cm.group(1) if cm else None


def find_private_categories(cfg, project_root):
    """This project's own `private_categories:` subscriptions, found by matching its
    hosts.<this host>.path against consumers\\*.md (registry_lib.host_path). Empty set if this
    project isn't registered yet, or no registry entry's host path resolves to project_root."""
    if not CONSUMERS_DIR.is_dir():
        return set()
    host_id = cfg.get('host_id')
    resolved = project_root.resolve()
    for f in sorted(CONSUMERS_DIR.glob('*.md')):
        c = parse_registry(f)
        if c is None:
            continue
        p = host_path(c, host_id)
        if p and Path(p).resolve() == resolved:
            return {pc['name'] for pc in c['private_categories']}
    return set()

# Keep in sync with scripts\new_consumer.py's SKILL_PIECES / check_tower_crane.py's SKILL_PIECES.
SKILL_PIECES = {
    'filing': {'companion': 'filing_resume_check', 'skills': ['filing']},
    'continuity': {'companion': 'continuity_resume_check', 'skills': ['checkpoint', 'archive']},
    'shared_resources': {'companion': 'shared_resources_resume_check', 'skills': ['shared_resources']},
}
MANDATORY_OR_DEFAULT_PIECES = ['filing', 'compliance', 'shared_resources', 'continuity']

# Keep in sync with scripts\new_consumer.py's STANDALONE_SKILLS. Anything else under
# templates\skills\* (e.g. hub_commands, distributed via self_hooks.py) must never be offered here.
STANDALONE_SKILLS = ['update', 'commands', 'capability_relationships']


def read_consumer_state(project_root):
    claude_md_path = project_root / 'CLAUDE.md'
    md_text = claude_md_path.read_text(encoding='utf-8') if claude_md_path.exists() else ''
    # '.' matches an import_base path containing a space; safe since an @import line is always
    # exactly one line.
    md_imports = set(re.findall(r'@.*?templates/(\w+)\.md', md_text))

    settings_path = project_root / '.claude' / 'settings.json'
    settings = {}
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text(encoding='utf-8')) or {}
        except json.JSONDecodeError:
            settings = {}

    skills_dir = project_root / '.claude' / 'skills'
    have_skills = {d.name for d in skills_dir.iterdir() if d.is_dir()} if skills_dir.is_dir() else set()

    return {'md_text': md_text, 'md_imports': md_imports, 'settings': settings,
            'have_skills': have_skills}


def scan_hooks(cfg, state):
    items = []
    have_hooks = state['settings'].get('hooks') if isinstance(state['settings'], dict) else None
    for optin_path in sorted(OPTINS_DIR.glob('*.json')):
        tool = optin_path.stem
        expanded = get_dispatch_optin(optin_path, tool, cfg)
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


def scan_stale_hooks(state):
    """Hook entries in this project's settings.json that run a hub tool whose script the hub has
    since removed - the reverse of scan_hooks(). One 'stale_hook' item per retired tool. Left in
    place such an entry errors on every firing (and a direct-path one on UserPromptSubmit blocks
    every prompt), so it is offered for removal the same way a missing hook is offered for adding."""
    items = []
    for tool in dead_hook_tools(state['settings'], SHARED_ROOT):
        items.append({'category': 'stale_hook', 'name': tool,
                      'detail': f'hooks/{tool}.py no longer exists in the toolkit; remove this project\'s entry for it'})
    return items


def apply_stale_hook(project_root, cfg, item):
    tool = item['name']
    settings_path = project_root / '.claude' / 'settings.json'
    if not settings_path.exists():
        print(f"  [skip] no .claude/settings.json - nothing to remove for '{tool}'")
        return False
    try:
        settings = json.loads(settings_path.read_text(encoding='utf-8')) or {}
    except json.JSONDecodeError:
        print(f"  [MANUAL] .claude/settings.json isn't valid JSON - remove the '{tool}' hook entry by hand")
        return False
    if not strip_dead_hooks(settings, [tool]):
        print(f"  [skip] no entry for '{tool}' found in .claude/settings.json")
        return False
    settings_path.write_text(json.dumps(settings, indent=2), encoding='utf-8', newline='\n')
    print(f"  [applied] retired hook '{tool}' removed from .claude/settings.json")
    return True  # needs registry write-back (drops its opted_in: row)


def _skill_current(project_root, name, canon_path, import_base=None):
    """True if project_root/.claude/skills/<name>/SKILL.md exists and matches the canonical
    source content exactly - either accepted rendering (direct-substitution or
    pointer-indirected) when import_base is given, or the single copy-only rendering when it's
    None (a private, toolkit_private skill). "Already adopted" means adopted and current, not
    just a folder with this name existing."""
    stub_path = project_root / '.claude' / 'skills' / name / 'SKILL.md'
    if not stub_path.exists():
        return False
    actual = stub_path.read_text(encoding='utf-8')
    if import_base is None:
        return actual == materialize_skill_stub(canon_path)
    expected_direct = materialize_skill_stub(canon_path, import_base, use_pointer=False)
    expected_pointer = materialize_skill_stub(canon_path, import_base, use_pointer=True)
    return actual in (expected_direct, expected_pointer)


def scan_skills(state, project_root, cfg):
    items = []
    for name in STANDALONE_SKILLS:
        canon_path = SKILLS_DIR / name / 'SKILL.md'
        if not (SKILLS_DIR / name).is_dir():
            continue
        detail = f'templates/skills/{name}/SKILL.md'
        if name in state['have_skills']:
            if _skill_current(project_root, name, canon_path, cfg['import_base']):
                continue
            items.append({'category': 'skill', 'name': name, 'detail': detail, 'drifted': True})
            continue
        items.append({'category': 'skill', 'name': name, 'detail': detail})
    return items


def scan_private(cfg, state, project_root):
    """Same shape as scan_hooks/scan_skills combined, pointed at toolkit_private\\ instead of
    toolkit\\. Yields nothing if toolkit_private\\ doesn't exist on this machine.

    Each scanned skill item also carries its own `category:` frontmatter (None if absent) and a
    `subscribed` flag - True when that category is in this project's own `private_categories:`
    registry list."""
    items = []
    subscribed_categories = find_private_categories(cfg, project_root)
    have_hooks = state['settings'].get('hooks') if isinstance(state['settings'], dict) else None
    if PRIVATE_OPTINS_DIR.is_dir():
        for optin_path in sorted(PRIVATE_OPTINS_DIR.glob('*.json')):
            tool = optin_path.stem
            expanded = get_dispatch_optin(optin_path, tool, cfg)
            missing = False
            for evt, groups in expanded.get('hooks', {}).items():
                canon = [json.dumps(g, separators=(',', ':')).replace('\\\\', '/') for g in groups]
                have = []
                if isinstance(have_hooks, dict) and evt in have_hooks:
                    have = [json.dumps(g, separators=(',', ':')).replace('\\\\', '/') for g in have_hooks[evt]]
                if any(c not in have for c in canon):
                    missing = True
            if missing:
                items.append({'category': 'private', 'kind': 'hook', 'name': tool,
                               'detail': f'toolkit_private/templates/optins/{tool}.json'})
    if PRIVATE_SKILLS_DIR.is_dir():
        for skill_dir in sorted(d for d in PRIVATE_SKILLS_DIR.iterdir() if d.is_dir()):
            name = skill_dir.name
            canon_path = skill_dir / 'SKILL.md'
            if not canon_path.exists():
                continue
            skill_category = read_skill_category(canon_path)
            item = {'category': 'private', 'kind': 'skill', 'name': name,
                    'detail': f'toolkit_private/templates/skills/{name}/SKILL.md',
                    'skill_category': skill_category,
                    'subscribed': skill_category is not None and skill_category in subscribed_categories}
            if name in state['have_skills']:
                if _skill_current(project_root, name, canon_path):
                    continue
                items.append({**item, 'drifted': True})
                continue
            items.append(item)
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


def scan_permissions(state):
    """The consumer-scope Bash/PowerShell allowlist in templates\\bash_allowlist.json - one
    aggregate item if any pattern in it is still missing from this project's own settings.json,
    never one item per pattern."""
    allowlist_path = TEMPLATES_DIR / 'bash_allowlist.json'
    if not allowlist_path.is_file():
        return []
    patterns = json.loads(allowlist_path.read_text(encoding='utf-8')).get('consumer', [])
    if not patterns:
        return []
    existing = (state['settings'].get('permissions', {}).get('allow', [])
                if isinstance(state['settings'], dict) else [])
    missing = any(f'Bash({p})' not in existing or f'PowerShell({p})' not in existing for p in patterns)
    if not missing:
        return []
    return [{'category': 'permission', 'name': 'bash_allowlist',
             'detail': 'templates/bash_allowlist.json (consumer)'}]


def apply_permissions(project_root, cfg, item):
    settings_path = project_root / '.claude' / 'settings.json'
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings = {}
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text(encoding='utf-8')) or {}
        except json.JSONDecodeError:
            settings = {}
    merge_bash_allowlist(settings, 'consumer')
    settings_path.write_text(json.dumps(settings, indent=2), encoding='utf-8', newline='\n')
    print("  [applied] consumer Bash/PowerShell allowlist merged into .claude/settings.json")
    return True  # audit-trail note only (update_registry_entry treats 'permission' like 'skill')


# ---------------------------------------------------------------------------------------------
# CLAUDE.md block patcher. A consumer's '## Tower Crane In Use' / '## Shared Workflow Protocol'
# block is rendered from the template at scaffold time and otherwise never touched, so it drifts.
# This renders what the CURRENT template would produce for this project, diffs it against the
# file, and offers each diff hunk ("deviation") as one numbered item. Everything here depends only
# on the project's own files and the toolkit, so the hub's `update consumers` and a project's own
# `update` (both import this module) behave identically.
# ---------------------------------------------------------------------------------------------

CATEGORY_LABELS = {'hook': 'Hook opt-ins', 'stale_hook': 'Retired hooks to remove', 'skill': 'Toolkit skills',
                   'piece': 'Protocol pieces', 'private': 'Private tools (toolkit_private)',
                   'permission': 'Permission allowlist', 'claude_md_block': 'CLAUDE.md block deviations',
                   'claude_md_manual': 'CLAUDE.md block (fix by hand)'}

_TOOL_BULLET_RE = re.compile(r'(?m)^- `([^`]+)` - ')
_WIRED_RE = re.compile(r'Opted-in tools \(wired (\d{4}-\d{2}-\d{2})\)')
_LISTING_RE = re.compile(r'(?m)^' + re.escape(ADOPTED_LISTING_ANCHOR))
_SENTINEL = '\x00ADOPTED\x00'
KEEP_WARNING = ("Tower Crane may not behave 100% as expected with this custom text kept in "
                "CLAUDE.md.")


def _tool_still_exists(tool):
    """False only for a tool bullet whose opt-in the hub has since retired. Where toolkit_private
    is absent (another machine) a tool not found in the toolkit can't be judged, so it is kept."""
    if (OPTINS_DIR / f'{tool}.json').exists():
        return True
    if not PRIVATE_ROOT.is_dir():
        return True
    return (PRIVATE_OPTINS_DIR / f'{tool}.json').exists() or (PRIVATE_SKILLS_DIR / tool).is_dir()


def _analyze_block(project_root):
    """Read-only. Returns None if there is nothing to analyze (no CLAUDE.md, or a disconnected
    project), else a dict: {'manual': message} when the headings aren't standard, or
    {'text','start','end','core','trailing','listing','head_lines','exp_lines','hunks'} where each
    hunk is {'kind': 'custom'|'missing', 'i1','i2','j1','j2','cur_text','exp_text','key'}."""
    md_path = Path(project_root) / 'CLAUDE.md'
    if not md_path.exists():
        return None
    text = md_path.read_text(encoding='utf-8')
    region = find_block_region(text)
    if region is None:
        if DISCONNECTED_HEADING in text:
            return None
        return {'manual': f"'{TC_IN_USE_HEADING}' / '{WORKFLOW_HEADING}' heading missing or "
                          "non-standard - Tower Crane can't tell what to patch; fix it by hand"}
    start, end = region
    block = text[start:end]
    core = block.rstrip()
    trailing = block[len(core):]

    # Slot values, all read from the existing block so the result is identical wherever it runs:
    # tools = the block's own bullets minus retired ones; date = its wired date; imports = its own
    # '@' lines (other mechanisms - apply_piece, relocate - own those); listing = verbatim.
    wf_idx = core.find(WORKFLOW_HEADING)
    tools_zone = core[:wf_idx] if wf_idx != -1 else core
    tools = [t for t in _TOOL_BULLET_RE.findall(tools_zone) if _tool_still_exists(t)]
    m = _WIRED_RE.search(core)
    wired = m.group(1) if m else date.today().isoformat()
    import_lines = [l.rstrip() for l in core[wf_idx:].splitlines() if re.match(r'^@\S+$', l.rstrip())] \
        if wf_idx != -1 else []
    imports = '\n'.join(import_lines) if import_lines else HUB_POINTER_IMPORT_LINE

    lm = _LISTING_RE.search(core)
    if lm:
        listing = core[lm.start():]
        head = core[:lm.start()]
        expected = render_claude_md_block(tools, wired, _SENTINEL, imports).split(_SENTINEL)[0]
    else:
        listing = None
        head = core
        expected = render_claude_md_block(tools, wired, ADOPTED_SHARED_RESOURCES_NONE, imports)

    head_lines = head.rstrip().split('\n')
    exp_lines = expected.rstrip().split('\n')
    sm = difflib.SequenceMatcher(None, [l.rstrip() for l in head_lines],
                                 [l.rstrip() for l in exp_lines], autojunk=False)
    hunks = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            continue
        cur_text = '\n'.join(head_lines[i1:i2]).rstrip()
        exp_text = '\n'.join(exp_lines[j1:j2]).rstrip()
        if not cur_text.strip() and not exp_text.strip():
            continue  # blank-line-count difference only; nothing to say about it
        kind = 'missing' if not cur_text.strip() else 'custom'
        hunks.append({'kind': kind, 'i1': i1, 'i2': i2, 'j1': j1, 'j2': j2, 'cur_text': cur_text,
                      'exp_text': exp_text, 'key': (kind, exp_text if kind == 'missing' else cur_text)})
    return {'text': text, 'start': start, 'end': end, 'core': core, 'trailing': trailing,
            'listing': listing, 'head_lines': head_lines, 'exp_lines': exp_lines, 'hunks': hunks}


def scan_block(project_root):
    """(items, live_exception_count). Items are the block deviations not already settled by a
    recorded exception, plus a 'claude_md_manual' item when the block can't be analyzed."""
    a = _analyze_block(project_root)
    if a is None:
        return [], 0
    if 'manual' in a:
        return [{'category': 'claude_md_manual', 'name': 'CLAUDE.md block', 'detail': a['manual']}], 0
    entries, err = load_exceptions(project_root)
    if err:
        return [{'category': 'claude_md_manual', 'name': 'CLAUDE.md block exceptions',
                 'detail': err + ' - fix or delete it by hand; until then block deviations are not scanned'}], 0
    kept_keys = {(e['kind'], e['text']) for e in entries}
    items, live = [], 0
    for h in a['hunks']:
        if h['key'] in kept_keys:
            live += 1
            continue
        n = len(items) + 1
        what = {'missing': 'template text this block lacks',
                'custom': 'custom text, not in the template'}[h['kind']]
        items.append({'category': 'claude_md_block', 'name': f'block change {n}', 'detail': what,
                      'kind': h['kind'], 'cur_text': h['cur_text'], 'exp_text': h['exp_text']})
    return items, live


def exceptions_reminder(project_root, label=''):
    """The one-line reminder printed after update work while exceptions are recorded, or ''."""
    _, live = scan_block(project_root)
    if not live:
        return ''
    noun = 'exception' if live == 1 else 'exceptions'
    return (f"{label}{live} CLAUDE.md {noun} kept — say \"reset exceptions\" to align everything "
            "with the template.")


def block_item_lines(it):
    """Indented lines showing exactly what patching this item removes/replaces and what goes in."""
    if it['category'] != 'claude_md_block':
        return []
    out = []
    if it['cur_text']:
        out.append('      patching removes:')
        out += [f'        | {l}' for l in it['cur_text'].split('\n')]
    if it['exp_text']:
        out.append('      and puts in:' if it['cur_text'] else '      patching adds:')
        out += [f'        | {l}' for l in it['exp_text'].split('\n')]
    return out


def apply_block_items(project_root, patch_items, keep_items):
    """Patch the chosen deviations in place (one CLAUDE.md write, however many) and record the
    kept ones as exceptions. Both lists hold scan_block() items; they are re-matched against a
    fresh analysis. Returns True if anything on disk changed."""
    a = _analyze_block(project_root)
    if a is None or 'manual' in a:
        print("  [MANUAL] CLAUDE.md block can't be analyzed - fix its headings by hand")
        return False
    entries, err = load_exceptions(project_root)
    if err:
        print(f"  [MANUAL] {err}")
        return False

    def find(it):
        for idx, h in enumerate(a['hunks']):
            if (h['kind'], h['cur_text'], h['exp_text']) == (it['kind'], it['cur_text'], it['exp_text']):
                return idx
        return None

    patch_idx = set()
    for it in patch_items:
        idx = find(it)
        if idx is None:
            print(f"  [skip] {it['name']} is no longer present")
        else:
            patch_idx.add(idx)
    keep_hunks = []
    for it in keep_items:
        idx = find(it)
        if idx is None:
            print(f"  [skip] {it['name']} is no longer present")
        else:
            keep_hunks.append(a['hunks'][idx])

    changed = False
    # Record kept exceptions; drop entries whose text no longer exists in the block (hand-reverted).
    live_keys = {h['key'] for h in a['hunks']}
    new_entries = [e for e in entries if (e['kind'], e['text']) in live_keys]
    have = {(e['kind'], e['text']) for e in new_entries}
    for h in keep_hunks:
        if h['key'] not in have:
            new_entries.append({'kind': h['kind'], 'text': h['key'][1], 'kept_on': date.today().isoformat()})
            have.add(h['key'])
    for h in keep_hunks:
        print(f"  [kept] {h['kind']} text recorded as an exception. {KEEP_WARNING}")
    if new_entries != entries:
        save_exceptions(project_root, new_entries)
        changed = True

    if patch_idx:
        out = []
        pos = 0
        for idx, h in enumerate(a['hunks']):
            out += a['head_lines'][pos:h['i1']]
            out += a['exp_lines'][h['j1']:h['j2']] if idx in patch_idx else a['head_lines'][h['i1']:h['i2']]
            pos = h['i2']
        out += a['head_lines'][pos:]
        new_core = '\n'.join(out)
        if a['listing'] is not None:
            new_core += '\n\n' + a['listing']
        new_text = a['text'][:a['start']] + new_core + a['trailing'] + a['text'][a['end']:]
        if new_text != a['text']:
            (Path(project_root) / 'CLAUDE.md').write_text(new_text, encoding='utf-8', newline='\n')
            changed = True
        print(f"  [applied] {len(patch_idx)} CLAUDE.md block deviation(s) patched to match the template")
    return changed


def reset_exceptions(project_root):
    """Delete the recorded exceptions so their text shows up as ordinary deviations again.
    True if a file was removed."""
    path = Path(project_root) / EXCEPTIONS_RELPATH
    if not path.exists():
        return False
    path.unlink()
    return True


def print_items(items):
    if not items:
        print("Nothing available - this project already has everything the hub currently offers.")
        return
    print(f"=== AVAILABLE ({len(items)}) ===")
    current_cat = None
    for i, it in enumerate(items, 1):
        if it['category'] != current_cat:
            current_cat = it['category']
            print(f"-- {CATEGORY_LABELS[current_cat]} --")
        # Call out a private skill matching one of this project's own private_categories:
        # subscriptions.
        tags = []
        if it.get('subscribed'):
            tags.append(f"{it['skill_category']} — subscribed")
        if it.get('drifted'):
            tags.append('drifted — needs re-sync')
        tag = f" [{', '.join(tags)}]" if tags else ''
        print(f"  [{i}] {it['name']}{tag}  ({it['detail']})")
        for line in block_item_lines(it):
            print(line)
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
    expanded = get_dispatch_optin(OPTINS_DIR / f'{tool}.json', tool, cfg)
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
    stub_content = materialize_skill_stub(stub_src, cfg['import_base'])
    skill_dir = project_root / '.claude' / 'skills' / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / 'SKILL.md').write_text(stub_content, encoding='utf-8', newline='\n')
    print(f"  [applied] skill '{name}' written to .claude/skills/{name}/SKILL.md")
    return True  # needs registry write-back


def apply_private(project_root, cfg, item):
    """Dispatches to the same hook-merge / skill-copy shape as apply_hook/apply_skill, pointed at
    toolkit_private\\. Private skills are copy-only (no {{IMPORT_BASE}} substitution)."""
    name = item['name']
    if item['kind'] == 'hook':
        expanded = get_dispatch_optin(PRIVATE_OPTINS_DIR / f'{name}.json', name, cfg)
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
        print(f"  [applied] private hook '{name}' merged into .claude/settings.json")
    else:  # 'skill'
        stub_src = PRIVATE_SKILLS_DIR / name / 'SKILL.md'
        skill_dir = project_root / '.claude' / 'skills' / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / 'SKILL.md').write_text(materialize_skill_stub(stub_src), encoding='utf-8', newline='\n')
        print(f"  [applied] private skill '{name}' written to .claude/skills/{name}/SKILL.md")
    return True  # needs registry write-back (private_opted_in:)


def apply_piece(project_root, cfg, item):
    p = item['name']
    sp = SKILL_PIECES.get(p)
    if sp:
        for skill_name in sp['skills']:
            stub_path = project_root / '.claude' / 'skills' / skill_name / 'SKILL.md'
            if stub_path.exists():
                continue
            stub_src = SKILLS_DIR / skill_name / 'SKILL.md'
            stub_content = materialize_skill_stub(stub_src, cfg['import_base'])
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


def split_keep(items, spec, keep_spec):
    """(numbers_to_apply, keep_numbers). `keep_spec` names block deviations to keep as
    exceptions instead of patching; they are removed from whatever `spec` selects (so
    `--apply all --keep 4` means 'all except 4'). Non-block numbers in keep_spec are ignored."""
    numbers = resolve_selection(spec, items) if spec is not None else []
    keeps = []
    for n in (resolve_selection(keep_spec, items) if keep_spec else []):
        if items[n - 1]['category'] == 'claude_md_block':
            keeps.append(n)
        else:
            print(f"[WARN] item {n} isn't a CLAUDE.md block deviation - only those can be kept; skipping.")
    return [n for n in numbers if n not in keeps], keeps


def do_apply(project_root, cfg, items, spec, keep_spec=None):
    numbers, keeps = split_keep(items, spec, keep_spec)
    if not numbers and not keeps:
        print("Nothing valid to apply.")
        return
    writeback = []
    block_patch = []
    for i in numbers:
        item = items[i - 1]
        print(f"[{i}] {item['name']} ({item['category']}):")
        if item['category'] == 'hook':
            if apply_hook(project_root, cfg, item):
                writeback.append(item['name'])
        elif item['category'] == 'stale_hook':
            if apply_stale_hook(project_root, cfg, item):
                writeback.append(item['name'])
        elif item['category'] == 'skill':
            if apply_skill(project_root, cfg, item):
                writeback.append(item['name'])
        elif item['category'] == 'piece':
            if apply_piece(project_root, cfg, item):
                writeback.append(item['name'])
        elif item['category'] == 'private':
            if apply_private(project_root, cfg, item):
                writeback.append(item['name'])
        elif item['category'] == 'permission':
            apply_permissions(project_root, cfg, item)
        elif item['category'] == 'claude_md_block':
            block_patch.append(item)  # written together below (hunks shift each other's offsets)
        elif item['category'] == 'claude_md_manual':
            print(f"  [MANUAL] {item['detail']}")
    block_keep = [items[n - 1] for n in keeps]
    if block_patch or block_keep:
        print("CLAUDE.md block:")
        apply_block_items(project_root, block_patch, block_keep)
    if writeback:
        print()
        print("[reminder] The hub's consumers/<slug>.md registry doesn't know about this yet - file "
              "a short registration-update ticket (templates/filing.md's filing shape) naming: "
              + ', '.join(writeback) + ". Needed so scripts/relocate.py and future opted-in-tool "
              "checks stay accurate (a private-tool item needs a private_opted_in: row specifically); "
              "not needed for flat @import-only pieces.")


def all_items(cfg, state, project_root):
    """Every available item for one project - the single list both this script and the hub's
    update_consumers.py build, so the two entry points can't disagree."""
    return (scan_hooks(cfg, state) + scan_stale_hooks(state) + scan_skills(state, project_root, cfg)
            + scan_pieces(state) + scan_private(cfg, state, project_root) + scan_permissions(state)
            + scan_block(project_root)[0])


def main():
    parser = argparse.ArgumentParser(
        description="Consumer-side `update`: scan/apply hub features this project hasn't adopted yet."
    )
    parser.add_argument('--project-root', default='.', help="This consumer project's root (default: cwd).")
    parser.add_argument('--apply', default=None,
                         help="Comma-separated item numbers from the last --check listing, or 'all'.")
    parser.add_argument('--keep', default=None,
                         help="Comma-separated CLAUDE.md block deviation numbers to keep as recorded "
                              "exceptions instead of patching (alone, or with --apply all).")
    parser.add_argument('--reset-exceptions', action='store_true',
                         help="Clear this project's recorded CLAUDE.md exceptions first, so they show "
                              "up as ordinary deviations again.")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    if not (project_root / 'CLAUDE.md').exists():
        print(f"[ABORT] No CLAUDE.md at {project_root} - is --project-root correct?")
        sys.exit(1)

    cfg = get_shared_config(SHARED_ROOT)
    if args.reset_exceptions:
        print("[reset] recorded CLAUDE.md exceptions cleared." if reset_exceptions(project_root)
              else "[reset] no recorded CLAUDE.md exceptions to clear.")
    state = read_consumer_state(project_root)
    items = all_items(cfg, state, project_root)

    if args.apply is None and args.keep is None:
        print_items(items)
        if items:
            print()
            print("Re-run with --apply <numbers-or-'all'> to adopt (e.g. --apply 1,3 or --apply all). "
                  "Add --keep <numbers> to keep a CLAUDE.md block deviation as an exception instead.")
        else:
            _print_reminder(project_root)
        return

    if not items:
        print("Nothing available to apply - run without --apply first, or nothing has changed.")
        _print_reminder(project_root)
        return

    do_apply(project_root, cfg, items, args.apply, args.keep)
    _print_reminder(project_root)


def _print_reminder(project_root):
    line = exceptions_reminder(project_root)
    if line:
        print()
        print(line)


if __name__ == '__main__':
    main()
