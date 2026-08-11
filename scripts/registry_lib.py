#!/usr/bin/env python3
"""
registry_lib.py - shared consumers\\<slug>.md registry parser/writer (design\\multi_machine_hub.md,
"Problem 2 - scoping pass").

Schema (2026-08 migration, replacing the old single `path:`/`host:` pair):
  scope: local | multi_machine
  remote: <git remote URL> (optional, top-level - design\\consumer_reconnect.md)
  hosts:
    <host_id>:
      path: <absolute path, forward-slash form>
      registered: <YYYY-MM-DD - when THIS host connected, not the project's overall registered:>

`scope` is a declared field with a mechanical floor, not purely derived (see the design doc's
correction): registration sets it directly, but any tool that touches the registry must persist-
correct it to `multi_machine` the moment 2+ hosts: entries exist, regardless of the declared
value. reconcile_scope_floor() below is that correction, meant to be called by every script that
walks the registry (check_tower_crane.py Pass B, relocate.py).

`remote` (design\\consumer_reconnect.md) is a project-level property (sibling to `scope`/`owner`,
not nested under any one host) recording the consumer's OWN git remote URL, captured once at first
registration from `git remote get-url origin` when available. Deliberately static - seed-once, no
continuous drift-check (see that design doc's rationale). Absent for a consumer registered before
this field existed, or one with no git remote configured at registration time; `new_consumer.py`
reads it to offer a clone-before-scaffold bootstrap when connecting an already-registered consumer
to an empty target folder.

Single source of truth for registry parsing - check_tower_crane.py, relocate.py,
update_consumers.py, and broadcast_guidance.py all import parse_registry() from here instead of
each hand-rolling their own copy (they did, pre-migration; consolidated here since the schema
change touches all of them identically).
"""

import re
from pathlib import Path

YAML_BLOCK_RE = re.compile(r'```yaml\s*\r?\n(.*?)\r?\n```', re.DOTALL)


def parse_registry(path):
    """Parse a consumers/<slug>.md registry file's fenced yaml block. Returns None if no
    parseable yaml block. `hosts` is always a dict (host_id -> {'path':.., 'registered':..}),
    empty for a malformed entry. `scope` is the raw declared value ('local'/'multi_machine') or
    None if absent - callers wanting the floor-corrected value should call effective_scope()
    rather than trust this raw field (the floor is a self-correcting invariant applied on each
    registry-touching run, not guaranteed already-applied at read time)."""
    raw = Path(path).read_text(encoding='utf-8')
    m = YAML_BLOCK_RE.search(raw)
    if not m:
        return None
    lines = re.split(r'\r?\n', m.group(1))

    obj = {
        'name': None, 'scope': None, 'remote': None, 'hosts': {}, 'owner': None, 'registered': None,
        'opted_in': [], 'imported': [], 'private_opted_in': [], 'file': str(path),
    }
    section = None
    current_host = None
    for line in lines:
        m1 = re.match(r'^name:\s*(.+?)\s*$', line)
        if m1:
            obj['name'] = m1.group(1)
            section = None
            continue
        m1 = re.match(r'^scope:\s*(.+?)\s*$', line)
        if m1:
            obj['scope'] = m1.group(1)
            section = None
            continue
        m1 = re.match(r'^remote:\s*(.+?)\s*$', line)
        if m1:
            obj['remote'] = m1.group(1)
            section = None
            continue
        m1 = re.match(r'^owner:\s*(.+?)\s*$', line)
        if m1:
            obj['owner'] = m1.group(1)
            section = None
            continue
        m1 = re.match(r'^registered:\s*(.+?)\s*$', line)
        if m1:
            obj['registered'] = m1.group(1)
            section = None
            continue
        if re.match(r'^hosts:\s*$', line):
            section = 'hosts'
            current_host = None
            continue
        if re.match(r'^opted_in:\s*\[\s*\]\s*$', line):
            obj['opted_in'] = []
            section = None
            continue
        if re.match(r'^opted_in:\s*$', line):
            section = 'opted_in'
            continue
        if re.match(r'^imported:\s*\[\s*\]\s*$', line):
            obj['imported'] = []
            section = None
            continue
        if re.match(r'^imported:\s*$', line):
            section = 'imported'
            continue
        if re.match(r'^private_opted_in:\s*\[\s*\]\s*$', line):
            obj['private_opted_in'] = []
            section = None
            continue
        if re.match(r'^private_opted_in:\s*$', line):
            section = 'private_opted_in'
            continue

        if section == 'hosts':
            m1 = re.match(r'^  (\S+):\s*$', line)
            if m1:
                current_host = m1.group(1)
                obj['hosts'][current_host] = {'path': None, 'registered': None}
                continue
            m1 = re.match(r'^    path:\s*(.+?)\s*$', line)
            if m1 and current_host:
                obj['hosts'][current_host]['path'] = m1.group(1)
                continue
            m1 = re.match(r'^    registered:\s*(.+?)\s*$', line)
            if m1 and current_host:
                obj['hosts'][current_host]['registered'] = m1.group(1)
                continue
            continue

        if section == 'opted_in':
            m1 = re.match(r'^\s*-\s*tool:\s*(.+?)\s*$', line)
            if m1:
                obj['opted_in'].append({'name': m1.group(1), 'since': None})
                continue
        if section == 'imported':
            m1 = re.match(r'^\s*-\s*piece:\s*(.+?)\s*$', line)
            if m1:
                obj['imported'].append({'name': m1.group(1), 'since': None})
                continue
        if section == 'private_opted_in':
            m1 = re.match(r'^\s*-\s*tool:\s*(.+?)\s*$', line)
            if m1:
                obj['private_opted_in'].append({'name': m1.group(1), 'since': None})
                continue

        m1 = re.match(r'^\s*since:\s*(.+?)\s*$', line)
        if m1:
            if section == 'opted_in' and obj['opted_in']:
                obj['opted_in'][-1]['since'] = m1.group(1)
            elif section == 'imported' and obj['imported']:
                obj['imported'][-1]['since'] = m1.group(1)
            elif section == 'private_opted_in' and obj['private_opted_in']:
                obj['private_opted_in'][-1]['since'] = m1.group(1)
            continue
    return obj


def effective_scope(consumer):
    """The floor-corrected scope, computed live regardless of whether reconcile_scope_floor() has
    already persisted it: 2+ hosts always means multi_machine, no matter what's on disk."""
    if len(consumer['hosts']) >= 2:
        return 'multi_machine'
    return consumer.get('scope') or 'local'


def host_path(consumer, host_id):
    """This host's registered path for this consumer, or None if not connected here."""
    h = consumer['hosts'].get(host_id)
    return h['path'] if h else None


def reconcile_scope_floor(path, consumer):
    """The design doc's '2-host write-back floor': if 2+ hosts: entries are present but the
    declared `scope:` line isn't already multi_machine, persist-correct it now. Meant to be
    called by every registry-touching tool (check_tower_crane.py Pass B, relocate.py) on each
    consumer it visits. Returns True if the file was rewritten; mutates consumer['scope'] to
    match on success so the caller's in-memory view stays consistent for the rest of its pass."""
    if len(consumer['hosts']) < 2 or consumer.get('scope') == 'multi_machine':
        return False
    raw = Path(path).read_text(encoding='utf-8')
    new_raw, n = re.subn(r'(?m)^scope:\s*.+?\s*$', 'scope: multi_machine', raw, count=1)
    if n == 0:
        return False
    Path(path).write_text(new_raw, encoding='utf-8', newline='\n')
    consumer['scope'] = 'multi_machine'
    return True


def add_host_to_text(raw_text, host_id, path_str, registered_date):
    """Adds a `hosts.<host_id>` entry to a registry file's raw text - the slug-collision /
    'connect a second machine' merge (design\\multi_machine_hub.md's locked routing: additive
    merge, never a duplicate file or blind overwrite). Idempotent: a no-op (already_present=True)
    if that host already has an entry, never touching its existing path/registered date. Also
    applies the 2-host floor to `scope:` if this addition brings the host count to 2+.

    Returns (new_text, already_present, host_count_after). Raises ValueError if the file has no
    parseable yaml block or no `hosts:` key (should never happen post-migration).
    """
    m = YAML_BLOCK_RE.search(raw_text)
    if not m:
        raise ValueError("no parseable yaml block")
    yaml_text = m.group(1)
    lines = yaml_text.split('\n')

    hosts_start = None
    for i, line in enumerate(lines):
        if re.match(r'^hosts:\s*$', line):
            hosts_start = i
            break
    if hosts_start is None:
        raise ValueError("no hosts: block found")
    hosts_end = len(lines)
    for i in range(hosts_start + 1, len(lines)):
        if re.match(r'^\S', lines[i]):  # next top-level key ends the hosts: block
            hosts_end = i
            break

    block = lines[hosts_start + 1:hosts_end]
    existing_ids = [mm.group(1) for l in block for mm in [re.match(r'^  (\S+):\s*$', l)] if mm]
    already_present = host_id in existing_ids
    host_count_after = len(existing_ids) if already_present else len(existing_ids) + 1

    if not already_present:
        new_entry = [f'  {host_id}:', f'    path: {path_str}', f'    registered: {registered_date}']
        lines = lines[:hosts_end] + new_entry + lines[hosts_end:]

    if host_count_after >= 2:
        for i, line in enumerate(lines):
            if re.match(r'^scope:\s*.+?\s*$', line):
                lines[i] = 'scope: multi_machine'
                break

    new_yaml_text = '\n'.join(lines)
    new_raw = raw_text[:m.start(1)] + new_yaml_text + raw_text[m.end(1):]
    return new_raw, already_present, host_count_after


def format_hosts_block(hosts):
    """Renders a hosts: dict (host_id -> {'path':.., 'registered':..}) as yaml lines, for a
    brand-new registry entry. `hosts` insertion order is preserved (Python dict semantics)."""
    lines = ['hosts:']
    for host_id, entry in hosts.items():
        lines.append(f'  {host_id}:')
        lines.append(f"    path: {entry['path']}")
        lines.append(f"    registered: {entry['registered']}")
    return '\n'.join(lines)


def set_remote_if_absent(raw_text, remote):
    """Adds a top-level `remote:` line (sibling to `scope:`, before `hosts:`) if this registry
    entry doesn't already have one - design\\consumer_reconnect.md's seed-once backfill for a
    consumer registered before the field existed. Never overwrites an existing `remote:` value.
    Returns (new_text, was_added)."""
    m = YAML_BLOCK_RE.search(raw_text)
    if not m:
        raise ValueError("no parseable yaml block")
    yaml_text = m.group(1)
    if re.search(r'(?m)^remote:\s*.+?\s*$', yaml_text):
        return raw_text, False
    lines = yaml_text.split('\n')
    scope_idx = None
    for i, line in enumerate(lines):
        if re.match(r'^scope:\s*.+?\s*$', line):
            scope_idx = i
            break
    if scope_idx is None:
        raise ValueError("no scope: line found")
    lines = lines[:scope_idx + 1] + [f'remote: {remote}'] + lines[scope_idx + 1:]
    new_yaml_text = '\n'.join(lines)
    new_raw = raw_text[:m.start(1)] + new_yaml_text + raw_text[m.end(1):]
    return new_raw, True
