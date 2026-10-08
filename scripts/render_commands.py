#!/usr/bin/env python3
"""
render_commands.py - the deterministic half of `"commands"` / `hub_commands`: renders the
catalog-derived parts of those answers straight from capability_catalog.yaml, so the agent copies
text instead of re-filtering ~40 nodes by hand each time. Read-only; prints to stdout.

Modes (pick one; --context hub|consumer says which session is asking, default consumer):
  --theme NAME [NAME...]  one block per theme: nodes whose `context` fits and whose `themes`
                          carries NAME, one `trigger - summary` line each. Nodes sharing the
                          literal trigger prefix before ` "` or ` search` (every `shared
                          resources "..."` node) collapse into one line listing their actions.
  --path                  the catalog's `path` section, in order, filtered to nodes whose
                          `context` fits (the beginner tier's spine).
  --reach                 consumer view: three tiers - fully reachable, partially reachable
                          (`partial_reach` naming consumer), hub-only.
  --neighbors NODE_ID     the node's edge neighbors, one line each, skipping `name-collision`
                          and `backs`; a hub-only neighbor is marked as such.

`context: both` fits either session. A summary is the description up to its first `: `, `. ` or
` - ` / em dash. The catalog is read with a small hand-rolled parser (no PyYAML: consumer
machines have only the standard library). Default catalog: `capability_catalog.yaml` at the
toolkit root, found relative to this script; override with --catalog.

Exit 0 on success; 1 on a missing/unparseable catalog or an unknown node id.
"""

import argparse
import json
import re
import sys
from pathlib import Path

DEFAULT_CATALOG = Path(__file__).resolve().parent.parent / 'capability_catalog.yaml'
SKIP_EDGES = {'name-collision', 'backs'}
SUMMARY_CUT = re.compile(r': |\. | — | - ')


def _scalar(text):
    text = text.strip()
    if text.startswith('"'):
        return json.loads(text)
    if text.startswith('['):
        inner = text.strip('[]').strip()
        return [p.strip() for p in inner.split(',')] if inner else []
    if text in ('null', '~', ''):
        return None
    if text in ('true', 'false'):
        return text == 'true'
    return text


def _items(lines, start):
    """Yield (key -> value) dicts for each `  - ` list item under the section starting at
    lines[start]; folded `>-` values are joined; one level of nested mapping is kept as a dict."""
    items, cur, folded_key, nested_key = [], None, None, None
    for raw in lines[start + 1:]:
        if raw and not raw[0].isspace() and not raw.startswith('#'):
            break                                    # next top-level key
        if not raw.strip() or raw.lstrip().startswith('#'):
            continue
        indent = len(raw) - len(raw.lstrip())
        body = raw.strip()
        if indent == 2 and body.startswith('- '):
            cur = {}
            items.append(cur)
            folded_key = nested_key = None
            body, indent = body[2:], 4
        if cur is None:
            continue
        if folded_key and indent > 4 and not (nested_key and indent >= 6 and ':' in body):
            cur[folded_key] = (cur[folded_key] + ' ' + body).strip()
            continue
        m = re.match(r'([A-Za-z_]+):\s*(.*)$', body)
        if not m:
            continue
        key, val = m.group(1), m.group(2)
        target = cur
        if indent >= 6 and nested_key:
            target = cur[nested_key]
        else:
            nested_key = None
        if val == '>-':
            folded_key = key
            target[key] = ''
        elif val == '' and indent == 4:
            nested_key, folded_key = key, None
            cur[key] = {}
        else:
            folded_key = None
            target[key] = _scalar(val)
    return items


def load_catalog(path):
    lines = Path(path).read_text(encoding='utf-8').splitlines()
    out = {}
    for name in ('nodes', 'edges'):
        idx = next((i for i, l in enumerate(lines) if l.startswith(name + ':')), None)
        if idx is None:
            raise ValueError(f'no top-level `{name}:` in {path}')
        out[name] = _items(lines, idx)
    idx = next((i for i, l in enumerate(lines) if l.startswith('path:')), None)
    if idx is None:
        raise ValueError(f'no top-level `path:` in {path}')
    out['path'] = []
    for raw in lines[idx + 1:]:
        m = re.match(r'\s+-\s+([a-z_]+)', raw)
        if m:
            out['path'].append(m.group(1))
    out['by_id'] = {n['id']: n for n in out['nodes']}
    return out


def fits(node, ctx):
    return node.get('context') in (ctx, 'both')


def summary(node):
    desc = ' '.join(str(node.get('description', '')).split())
    return SUMMARY_CUT.split(desc, maxsplit=1)[0].rstrip('.')


def render_theme(cat, ctx, theme):
    lines, groups = [], {}
    picked = [n for n in cat['nodes'] if fits(n, ctx) and theme in (n.get('themes') or [])]
    keys = [re.split(r' "| search', n['trigger'])[0] for n in picked]
    for n, key in zip(picked, keys):
        if keys.count(key) < 2:
            lines.append(('node', n))
        elif key in groups:
            groups[key].append(n)
        else:
            groups[key] = [n]
            lines.append(('group', key))
    out = [f'{theme}:']
    for kind, val in lines:
        if kind == 'node':
            out.append(f'  {val["trigger"]} - {summary(val)}')
        else:
            actions = [m['trigger'][len(val):].strip() for m in groups[val]]
            actions = [a if a else 'bare' for a in actions]
            out.append(f'  {val} - {", ".join(actions)}')
    if len(out) == 1:
        out.append('  (no nodes carry this theme for this session)')
    return '\n'.join(out)


def render_path(cat, ctx):
    out, step = [], 0
    for nid in cat['path']:
        n = cat['by_id'].get(nid)
        if n is None:
            out.append(f'[!] path names unknown node id: {nid}')
        elif fits(n, ctx):
            step += 1
            out.append(f'{step}. {n["trigger"]} - {summary(n)}')
    return '\n'.join(out)


def render_reach(cat):
    full = [n for n in cat['nodes'] if n.get('context') == 'consumer']
    part = [n for n in cat['nodes'] if n.get('context') == 'hub'
            and (n.get('partial_reach') or {}).get('from') == 'consumer']
    hub = [n for n in cat['nodes'] if n.get('context') == 'hub' and n not in part]
    out = ['Fully reachable from here (no hub session ever needed):']
    out += [f'  {n["trigger"]} - {summary(n)}' for n in full]
    out.append('Partially reachable from here (the rest needs a hub session):')
    out += [f'  {n["trigger"]} - {n["partial_reach"]["note"]}' for n in part]
    out.append('Hub-only (needs a hub-operator session):')
    out += [f'  {n["trigger"]} - {summary(n)}' for n in hub]
    return '\n'.join(out)


def render_neighbors(cat, node_id, ctx):
    node = cat['by_id'].get(node_id)
    if node is None:
        return None
    out = []
    for e in cat['edges']:
        if e['type'] in SKIP_EDGES or node_id not in (e['a'], e['b']):
            continue
        other_id = e['b'] if e['a'] == node_id else e['a']
        other = cat['by_id'].get(other_id)
        if other is None:
            out.append(f'[!] edge names unknown node id: {other_id}')
            continue
        line = f'{node["trigger"]} -> also mention: {other["trigger"]} ({e["type"]}'
        if e['type'] == 'accelerant':
            line += ', ' + ('this side accelerates the other' if e['a'] == node_id
                            else 'the other side accelerates this one')
        line += ')'
        if e.get('note'):
            line += f' - {e["note"]}'
        if not fits(other, ctx):
            line += (' [hub-only: exists but not reachable from this session]' if ctx == 'consumer'
                     else ' [a consumer-session capability: already possible without this hub side]')
        out.append(line)
    return '\n'.join(out) if out else f'{node["trigger"]}: no structural neighbors'


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[1])
    ap.add_argument('--context', choices=('hub', 'consumer'), default='consumer')
    ap.add_argument('--catalog', default=str(DEFAULT_CATALOG))
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument('--theme', nargs='+')
    mode.add_argument('--path', action='store_true')
    mode.add_argument('--reach', action='store_true')
    mode.add_argument('--neighbors', metavar='NODE_ID')
    args = ap.parse_args()
    try:
        cat = load_catalog(args.catalog)
    except (OSError, ValueError) as exc:
        print(f'[FAIL] cannot read catalog: {exc}')
        return 1
    if args.theme:
        print('\n\n'.join(render_theme(cat, args.context, t) for t in args.theme))
    elif args.path:
        print(render_path(cat, args.context))
    elif args.reach:
        print(render_reach(cat))
    else:
        text = render_neighbors(cat, args.neighbors, args.context)
        if text is None:
            print(f'[FAIL] unknown node id: {args.neighbors}')
            return 1
        print(text)
    return 0


if __name__ == '__main__':
    sys.exit(main())
