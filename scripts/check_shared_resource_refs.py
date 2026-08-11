#!/usr/bin/env python3
"""
check_shared_resource_refs.py - Group B2 of design\\resource_sharing_model.md: a project's own
"is what I adopted from shared_resources\\ still there" check, run at that project's `resume`
(see templates\\shared_resources.md's "Checking adopted references at resume").

Why a script and not a written resume-time instruction: the same "prefer a deterministic check
over LLM judgment" reasoning already governing consistency_check.py and check_tower_crane.py's
golden suite - an existence check has one right answer, so let something outside the model give
it, for free, instead of spending agent reasoning/tokens re-deriving it every resume.

What it checks, in two forms - both per templates\\shared_resources.md's "Apply" step:
1. Every `@import`-syntax line in the given project's CLAUDE.md whose target path contains a
   `shared_resources/` segment (the pre-directive_economy flat-import form).
2. Every backtick-quoted `~/...`-form path containing a `shared_resources/` segment inside any
   project-local `.claude\\skills\\<name>\\SKILL.md` file (the Track-1 skill-stub form "Apply" now
   produces - design\\directive_economy.md's "Apply procedure, resolved").
Both forms expand a leading `~` to the current user's home directory (the only such path form
proven to resolve - design\\portability.md decision 7), then check the target file actually
exists. Flags anything that doesn't resolve, so a folder-maintenance operation
(split/consolidate/rename/delete) that broke a stub never fails silently
(design\\resource_sharing_model.md's "Shared resources folder maintenance" principle).

Deliberately out of scope: free-text "pointer note" adoptions (a `tool`-kind entry invoked
on-demand, or any adoption written as prose mentioning a spaced path rather than a literal
`@import` line or a backtick-quoted `~/...` path in a skill stub). Those aren't machine-parseable
by construction - there's no fixed shape to check deterministically. Also out of scope: a skill
stub's trigger description going stale relative to its source entry's current topic footprint -
a different, notify-only concern (design\\directive_economy.md's "Drift mechanics"), not an
existence check.

Also checks a third, separate thing (design\\resource_sharing_model.md's "Per-host availability
for pointer entries"): whether an adopted `tool`/pointer-`reference` entry's own `Hosts:` block
(only present on an entry whose real target lives outside `shared_resources\\`, genuinely
machine-local) lists THIS host. This is deliberately notify-only, never blocking - a missing host
isn't a broken reference (the entry file itself resolves fine), it's a "the thing this points at
was never provisioned here" gap that only a human can resolve. `[HOST-GAP]` never affects the exit
code. See `templates\\shared_resources.md`'s "Per-host availability for pointer entries" for the
three-option remedy (ignore / connect now / proceed and re-ask) the acting agent should offer on a
`[HOST-GAP]` hit.

Usage: python scripts\\check_shared_resource_refs.py [--project-root <path>]
Defaults --project-root to the current working directory (the normal case: run from inside the
consuming project during its own `resume`). Prints [OK]/[FAIL]/[N/A]/[HOST-GAP] lines; exit 0 if
nothing is broken (including "nothing adopted"), exit 1 if any adopted reference no longer
resolves. A `[HOST-GAP]` alone never causes exit 1.
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config_lib import ADOPTED_MARKER_RE

# '.' (not '\S') so an import_base path containing a space still matches - '.' excludes only
# newlines, and an @import line is always exactly one line, so this can't over-match into the
# next line. Same fix as check_tower_crane.py/scan_consumer_update.py's identical regex
# (2026-08-08) - found here the same day while auditing for other latent instances of the same
# whitespace-intolerant pattern.
IMPORT_LINE_RE = re.compile(r'^@(.+?)\s*$', re.MULTILINE)
SKILL_STUB_PATH_RE = re.compile(r'`(~/[^`]+)`')
# A shared_resources\ entry's own "Hosts:" block (design\resource_sharing_model.md's worked
# example) - present only on a tool/pointer-reference entry whose real target lives outside
# shared_resources\ itself. Mirrors registry_lib.py's consumers\<slug>.md hosts: shape one layer
# down, but hand-authored markdown rather than a fenced yaml block, so this is its own small
# parser rather than a registry_lib.py reuse.
HOSTS_HEADER_RE = re.compile(r'\*\*Hosts:\*\*\s*\r?\n')
HOST_KEY_RE = re.compile(r'^  (\S+):\s*$')


def resolve_import_path(raw):
    """Expand a Claude Code @import path (home-relative '~/...', the only form ever proven to
    resolve) to an absolute Path. Returns None if it isn't home-relative - out of scope, not an
    error, since every real shared_resources\\ import in this project always uses that form."""
    normalized = raw.replace('\\', '/')
    if not normalized.startswith('~/'):
        return None
    return (Path.home() / normalized[2:]).resolve()


def find_shared_resource_imports(claude_md_text):
    hits = []
    for m in IMPORT_LINE_RE.finditer(claude_md_text):
        raw = m.group(1)
        if 'shared_resources/' not in raw.replace('\\', '/'):
            continue
        hits.append(raw)
    return hits


def find_shared_resource_skill_refs(project_root):
    """Every project-local .claude\\skills\\<name>\\SKILL.md, scanned for a backtick-quoted
    '~/...' path containing a shared_resources/ segment (the Track-1 stub form). Returns a list
    of (skill_name, raw_path) pairs."""
    hits = []
    skills_dir = project_root / '.claude' / 'skills'
    if not skills_dir.is_dir():
        return hits
    for skill_md in sorted(skills_dir.glob('*/SKILL.md')):
        text = skill_md.read_text(encoding='utf-8')
        for m in SKILL_STUB_PATH_RE.finditer(text):
            raw = m.group(1)
            if 'shared_resources/' not in raw.replace('\\', '/'):
                continue
            hits.append((skill_md.parent.name, raw))
    return hits


def parse_hosts_block(entry_text):
    """Parse a shared_resources\\ entry's own '**Hosts:**' block (present only on a tool/pointer-
    reference entry whose real target lives outside shared_resources\\). Returns a dict of
    host_id -> {'path':.., 'registered':..}; empty if the entry has no Hosts: block at all (a
    self-contained entry - not a gap, out of scope for this check)."""
    m = HOSTS_HEADER_RE.search(entry_text)
    if not m:
        return {}
    lines = entry_text[m.end():].split('\n')
    hosts = {}
    current = None
    for line in lines:
        hm = HOST_KEY_RE.match(line)
        if hm:
            current = hm.group(1)
            hosts[current] = {'path': None, 'registered': None}
            continue
        pm = re.match(r'^    path:\s*(.+?)\s*$', line)
        if pm and current:
            hosts[current]['path'] = pm.group(1)
            continue
        rm = re.match(r'^    registered:\s*(.+?)\s*$', line)
        if rm and current:
            hosts[current]['registered'] = rm.group(1)
            continue
        if line.strip() == '' or line.startswith('  ') or line.startswith('    '):
            continue
        break  # first non-indented, non-blank line ends the Hosts: block
    return hosts


def resolve_hub_root(resolved_entry_path):
    """A resolved shared_resources\\<file> path's hub root - the parent of the shared_resources\\
    folder itself. Returns None if the path isn't actually under a shared_resources\\ folder
    (shouldn't happen for anything this script already validated, but defensive regardless)."""
    for parent in resolved_entry_path.parents:
        if parent.name == 'shared_resources':
            return parent.parent
    return None


def read_this_host_id(hub_root):
    """This machine's own host_id, read from the hub's config.local.json - the same file the hub
    itself reads via config_lib.get_shared_config(), but a consumer-side check has no direct
    access to that module's machine-relative assumptions, so this reads the one field it needs
    directly. Returns None if the hub's config isn't reachable or has no host_id set (out of
    scope, not a failure - the host-gap check simply can't run)."""
    config_path = hub_root / 'toolkit' / 'config.local.json'
    if not config_path.exists():
        return None
    try:
        cfg = json.loads(config_path.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError):
        return None
    host_id = cfg.get('host_id')
    if not host_id or not isinstance(host_id, str) or host_id.startswith('<'):
        return None
    return host_id


def check_host_gaps(project_root, skill_refs):
    """For every adopted tool/pointer-reference skill stub whose entry file has a Hosts: block,
    checks whether THIS host is a key in it. Returns a list of (skill_name, entry_label,
    status, message) tuples, status one of 'ok' / 'ignored' / 'gap' / 'n/a'."""
    results = []
    this_host = None
    for skill_name, raw in skill_refs:
        resolved = resolve_import_path(raw)
        if resolved is None or not resolved.exists():
            continue  # already reported as [FAIL] or [N/A] above - not this check's concern
        entry_text = resolved.read_text(encoding='utf-8')
        hosts = parse_hosts_block(entry_text)
        if not hosts:
            continue  # self-contained entry - no Hosts: block, nothing to check
        if this_host is None:
            hub_root = resolve_hub_root(resolved)
            this_host = read_this_host_id(hub_root) if hub_root else None
            if this_host is None:
                results.append((skill_name, resolved.name, 'n/a',
                                 "couldn't determine this host's own host_id (hub config.local.json "
                                 "not reachable) - skipping host-availability check."))
                continue
        stub_path = project_root / '.claude' / 'skills' / skill_name / 'SKILL.md'
        stub_text = stub_path.read_text(encoding='utf-8') if stub_path.exists() else ''
        marker = ADOPTED_MARKER_RE.search(stub_text)
        ignored = set()
        if marker and marker.group('hostsignored'):
            ignored = set(marker.group('hostsignored').split(','))

        if this_host in hosts:
            results.append((skill_name, resolved.name, 'ok',
                             f"registered for this host ('{this_host}')."))
        elif this_host in ignored:
            results.append((skill_name, resolved.name, 'ignored',
                             f"not registered for this host ('{this_host}') - previously marked "
                             "ignored for this project, not re-asking."))
        else:
            known = ', '.join(sorted(hosts)) or '(none)'
            results.append((skill_name, resolved.name, 'gap',
                             f"not registered for this host ('{this_host}') - only available on: "
                             f"{known}. See templates\\shared_resources.md's \"Per-host "
                             "availability for pointer entries\" for the ignore / connect now / "
                             "proceed-and-re-ask remedy."))
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Checks that this project's adopted shared_resources\\ @import references "
                     "still resolve to real files."
    )
    parser.add_argument('--project-root', default='.', help="Defaults to the current directory.")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    claude_md = project_root / 'CLAUDE.md'
    print("=== check_shared_resource_refs.py ===")

    imports = []
    if claude_md.exists():
        imports = find_shared_resource_imports(claude_md.read_text(encoding='utf-8'))
    skill_refs = find_shared_resource_skill_refs(project_root)

    if not imports and not skill_refs:
        print("[N/A] no shared_resources\\ @import lines in CLAUDE.md and no shared_resources\\ "
              "references in any .claude\\skills\\ stub - nothing adopted, nothing to check.")
        sys.exit(0)

    broken = 0
    checked = 0
    for raw in imports:
        checked += 1
        resolved = resolve_import_path(raw)
        if resolved is None:
            print(f"[N/A] '@{raw}' isn't in the home-relative '~/...' form every real "
                  "shared_resources\\ import uses - skipping (out of scope, not a failure).")
            continue
        if resolved.exists():
            print(f"[OK] '@{raw}' resolves.")
        else:
            broken += 1
            print(f"[FAIL] '@{raw}' does NOT resolve (expected file at {resolved}) - this "
                  "adopted reference is broken, likely a shared_resources\\ entry that was "
                  "renamed/deleted/split without a stub left behind. Worth a note back to a hub "
                  "session to fix the source, or 'forget' this adoption if it's no longer needed.")

    for skill_name, raw in skill_refs:
        checked += 1
        resolved = resolve_import_path(raw)
        if resolved is None:
            print(f"[N/A] skill stub '{skill_name}' references '{raw}', not in the "
                  "home-relative '~/...' form - skipping (out of scope, not a failure).")
            continue
        if resolved.exists():
            print(f"[OK] skill stub '{skill_name}' reference '{raw}' resolves.")
        else:
            broken += 1
            print(f"[FAIL] skill stub '{skill_name}' reference '{raw}' does NOT resolve "
                  f"(expected file at {resolved}) - this adopted reference is broken, likely a "
                  "shared_resources\\ entry that was renamed/deleted/split without a stub left "
                  "behind. Worth a note back to a hub session to fix the source, or 'forget' "
                  "this adoption if it's no longer needed.")

    host_results = check_host_gaps(project_root, skill_refs)
    gap_count = 0
    for skill_name, entry_label, status, message in host_results:
        if status == 'gap':
            gap_count += 1
            print(f"[HOST-GAP] skill stub '{skill_name}' ('{entry_label}'): {message}")
        elif status == 'ignored':
            print(f"[OK] skill stub '{skill_name}' ('{entry_label}'): {message}")
        elif status == 'ok':
            print(f"[OK] skill stub '{skill_name}' ('{entry_label}'): {message}")
        else:
            print(f"[N/A] skill stub '{skill_name}' ('{entry_label}'): {message}")

    print()
    if broken:
        print(f"=== {broken} broken shared_resources\\ reference(s) - see [FAIL] lines above ===")
        sys.exit(1)
    if gap_count:
        print(f"=== all {checked} adopted shared_resources\\ reference(s) resolve; "
              f"{gap_count} host-availability gap(s) flagged above (notify only, not a failure) ===")
        sys.exit(0)
    print(f"=== all {checked} adopted shared_resources\\ reference(s) resolve ===")
    sys.exit(0)


if __name__ == '__main__':
    main()
