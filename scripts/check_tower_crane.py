#!/usr/bin/env python3
"""
check_tower_crane.py - cross-consumer checker for tower_crane, the executable teeth behind
"mandatory pre-apply validation" (consumer_platform design, component 2 / decision 4).

Two passes, plus an optional compliance-guidance writer:

  Pass A - Golden regression suite (decision 4, "golden"):
    For each tests/<tool>/ folder that has an expected.yaml, invoke hooks/<tool>.py against
    every fixture and assert the checker's exit code + a required substring. Catches the class
    of bug a reference-only scan ships blind to (valid code starts failing / a real failure
    stops being caught).

  Pass B - Reference & drift scan (decision 4, "reference"):
    Read every consumers/<name>.md registry entry and, for each consumer:
      - assert its path exists on disk (WARN + skip if gone);
      - for each opted-in tool: assert the canonical snippet exists, the hook file it
        references exists, and the consumer's .claude/settings.json still contains that
        snippet (drift);
      - for each @import in the consumer's CLAUDE.md: assert the referenced protocol piece
        exists shared-side (broken import);
      - IMPORT DRIFT tripwire: a consumer whose CLAUDE.md no longer imports a piece its
        registry lists (decision 8 - opt-out is detectable, not preventable);
      - mandatory-piece glance: filing + compliance + shared_resources not imported -> WARN (a
        SKILL_PIECES entry like 'filing' is also satisfied by its Track-1 skill-stub form -
        design\\directive_economy.md);
      - Track-1 skill stub drift (toolkit-governed only, design\\directive_economy.md): for each
        skill name any SKILL_PIECES entry scaffolds, plus every STANDALONE_SKILLS entry (design\\
        consumer_update.md / design\\optimize_ux.md - a Track-1 skill with no @import companion,
        e.g. `update`, `commands`), a consumer's project-local .claude/skills/<name>/SKILL.md must
        still match the canonical templates/skills/<name>/SKILL.md (with {{IMPORT_BASE}} resolved and
        the leading maintainer-comment header stripped - config_lib.materialize_skill_stub).

  Hub self-use skill drift (design\\optimize_ux.md, addendum to Pass B): the hub is not a
    registered consumer of its own scaffolder, so `hub_commands` (installed only via
    self_hooks.py's "skills" opt-in key) isn't covered by the per-consumer loop above - checked
    separately, once, against this hub's own .claude/skills/ regardless of --consumer scoping.

  Compliance guidance (decision 11, the two-way channel, down direction):
    With --write-guidance, for each reachable consumer that has consumer-actionable FAILs,
    write the '## Checker deviations' section of <consumer>/COMPLIANCE_GUIDANCE.md (deviations +
    exact fixes, date + SHA stamped) via guidance_lib.py. A now-compliant consumer's section is
    cleared (the file itself is removed once no section has content). NEVER edits a consumer's
    live files - only drops the guidance file the consumer's own agent scans. This is one of two
    writers sharing that file: broadcast_guidance.py owns the sibling '## Broadcast' section -
    see design\\broadcast_guidance.md.

  --diagnose (design\\connection_diagnostics.md) - fact-reporting only mode for a non-standard
    connect_project/disconnect_consumer.py state that doesn't fit either script's deterministic
    branches. Prints a flat present/absent fact list from two source categories (Tower-Crane-
    specific current-state files, and durable git-history signals that survive hand-deletion or
    corruption) - never a verdict, never a fix, mirroring hooks\\consistency_check.py's own
    report-don't-fix split. Standalone-reachable (--path and/or --slug) and auto-invoked inline by
    new_consumer.py's/disconnect_consumer.py's fatal-error paths via config_lib.print_diagnose_inline.
    Runs standalone - does not touch Pass A/B's PASS/WARN/FAIL counters or exit code.

Exit code: 0 if no FAILs, 1 otherwise. WARNs never fail the build.

OS-reach Tier 2 port of check_tower_crane.ps1 (design\\portability.md, "OS-reach Tier 2: full
cross-platform design"). Logic is a direct translation - see that doc's Build order for the
parity-check approach used to verify this against the original (no existing golden suite for
the checker itself, so parity is validated by diffing old-vs-new output against the same
registry). Generated files (COMPLIANCE_GUIDANCE.md) now use LF line endings universally (the
locked line-endings decision, bundled into this port).
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import namedtuple
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config_lib import (
    get_shared_config, get_expanded_optin, get_dispatch_optin, materialize_skill_stub,
    HUB_POINTER_IMPORT_LINE, HUB_POINTER_RELPATH, HUB_DISPATCH_RELPATH, HUB_DISPATCH_TEMPLATE,
    parse_hub_pointer,
)
from guidance_lib import read_sections, write_section, SECTION_CHECKER
from registry_lib import parse_registry, effective_scope, host_path, reconcile_scope_floor

SHARED_ROOT = Path(__file__).resolve().parent.parent
# consumers\ is private hub state, not shipped toolkit content - it lives at the outer root
# (design\local_first_reframe.md's outer/inner split), one level above SHARED_ROOT (toolkit\).
PROJECT_ROOT = SHARED_ROOT.parent
HOOKS_DIR = SHARED_ROOT / 'hooks'
TEMPLATES_DIR = SHARED_ROOT / 'templates'
OPTINS_DIR = TEMPLATES_DIR / 'optins'
SKILLS_DIR = TEMPLATES_DIR / 'skills'
CONSUMERS_DIR = PROJECT_ROOT / 'consumers'
TESTS_DIR = SHARED_ROOT / 'tests'
# design\private_tools.md - the private, automatic analog to toolkit\ itself. Lives at the outer
# root as a sibling of toolkit\, same level as consumers\; may not exist yet on a fresh clone.
PRIVATE_ROOT = PROJECT_ROOT / 'toolkit_private'
PRIVATE_OPTINS_DIR = PRIVATE_ROOT / 'templates' / 'optins'
PRIVATE_SKILLS_DIR = PRIVATE_ROOT / 'templates' / 'skills'

# Toolkit-governed Track-1 skill pieces (design\directive_economy.md): piece name -> the Track-2
# "resume check" companion a consumer imports instead of a flat @import <name>.md, plus the list
# of skill-stub folder names it scaffolds (usually one, but 'continuity' splits into two:
# 'checkpoint' + 'archive', since 'resume' itself stays Track 2). Mirrors
# scripts\new_consumer.py's SKILL_PIECES - keep in sync.
SKILL_PIECES = {
    'filing': {'companion': 'filing_resume_check', 'skills': ['filing']},
    'continuity': {'companion': 'continuity_resume_check', 'skills': ['checkpoint', 'archive']},
    'shared_resources': {'companion': 'shared_resources_resume_check', 'skills': ['shared_resources']},
}

# Standalone Track-1 skills with no @import companion (design\consumer_update.md, design\
# optimize_ux.md, design\capability_relationships.md): still toolkit-governed, so a consumer's
# stub still gets the same drift check below. Mirrors scripts\new_consumer.py's
# STANDALONE_SKILLS - keep in sync.
STANDALONE_SKILLS = ['update', 'commands', 'capability_relationships']

COUNTS = {'PASS': 0, 'WARN': 0, 'FAIL': 0}

# Deviation record used by pass B + the guidance writer.
#   target: 'consumer' (the consumer's own agent can fix it) | 'shared' (a tower_crane bug) |
#           'registry' (registry integrity, e.g. path gone)
Dev = namedtuple('Dev', ['severity', 'target', 'message', 'fix'])


def report(level, message, indent='  '):
    COUNTS[level] += 1
    print(f"{indent}[{level}] {message}")


# --- expected.yaml parser (constrained shape, no YAML module needed) ---------------------------
#   fixture.py:
#     exit: 0
#     must_contain: "..."
def parse_expected(lines):
    out = {}
    cur = None
    for line in lines:
        if re.match(r'^\s*#', line) or line.strip() == '':
            continue
        m = re.match(r'^(\S.*?):\s*$', line)
        if m:
            cur = m.group(1).strip()
            out[cur] = {'exit': None, 'must_contain': None}
            continue
        if cur is None:
            continue
        m = re.match(r'^\s+exit:\s*(\d+)\s*$', line)
        if m:
            out[cur]['exit'] = int(m.group(1))
            continue
        m = re.match(r'^\s+must_contain:\s*(.+?)\s*$', line)
        if m:
            v = m.group(1).strip()
            if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
                v = v[1:-1]
            out[cur]['must_contain'] = v
            continue
    return out


# registry (consumers/<slug>.md) parsing lives in registry_lib.py (parse_registry, effective_scope,
# host_path, reconcile_scope_floor) - imported above, shared with relocate.py/update_consumers.py/
# broadcast_guidance.py so the schema (design\multi_machine_hub.md's scope:/hosts: map) has exactly
# one parser instead of N drifting copies.


# ==================================================================================================
# Pass A - golden regression suite
# ==================================================================================================
def invoke_golden_suite(config):
    print()
    print("--- Pass A: golden regression suite ---")

    if not TESTS_DIR.is_dir():
        report('WARN', "No tests/ folder - skipping golden suite.")
        return

    tool_dirs = sorted(
        d for d in TESTS_DIR.iterdir() if d.is_dir() and (d / 'expected.yaml').exists()
    )
    if not tool_dirs:
        report('WARN', "No tests/<tool>/expected.yaml found - nothing to run.")
        return

    # sandbox project dir so the hook (which needs CLAUDE_PROJECT_DIR and writes logs) has a
    # harmless place to write; removed at the end.
    sandbox = Path(tempfile.gettempdir()) / f"check_tower_crane_sandbox_{os.getpid()}"
    sandbox.mkdir(parents=True, exist_ok=True)
    saved_proj_dir = os.environ.get('CLAUDE_PROJECT_DIR')
    os.environ['CLAUDE_PROJECT_DIR'] = str(sandbox)

    try:
        for td in tool_dirs:
            tool = td.name
            hook = HOOKS_DIR / f"{tool}.py"
            if not hook.exists():
                report('FAIL', f"{tool} : no hook at hooks/{tool}.py (test folder references a missing tool).")
                continue
            expected = parse_expected((td / 'expected.yaml').read_text(encoding='utf-8').splitlines())
            for fixture, exp in expected.items():
                fx = td / fixture
                if not fx.exists():
                    report('FAIL', f"{tool} / {fixture} : fixture file missing.")
                    continue
                proc = subprocess.run(
                    [config['python_launcher'], str(hook), str(fx)],
                    capture_output=True, text=True,
                )
                out = proc.stdout
                code = proc.returncode

                code_ok = exp['exit'] is None or code == exp['exit']
                sub_ok = not exp['must_contain'] or exp['must_contain'] in out

                if code_ok and sub_ok:
                    report('PASS', f"{tool} / {fixture} (exit {code}, matched \"{exp['must_contain']}\")")
                else:
                    why = []
                    if not code_ok:
                        why.append(f"exit {code} != {exp['exit']}")
                    if not sub_ok:
                        why.append(f"missing substring \"{exp['must_contain']}\"")
                    report('FAIL', f"{tool} / {fixture} : {'; '.join(why)}")
    finally:
        if saved_proj_dir is None:
            os.environ.pop('CLAUDE_PROJECT_DIR', None)
        else:
            os.environ['CLAUDE_PROJECT_DIR'] = saved_proj_dir
        shutil.rmtree(sandbox, ignore_errors=True)


# ==================================================================================================
# Pass B - per-consumer reference & drift scan
# ==================================================================================================
def test_consumer(c, config, this_host):
    devs = []
    raw_path = host_path(c, this_host)
    cpath = Path(raw_path) if raw_path else None

    if not cpath or not cpath.exists():
        devs.append(Dev('WARN', 'registry', f"Consumer path not found on disk: {raw_path}", None))
        return devs  # unreachable - can't check settings / CLAUDE.md

    settings_path = cpath / '.claude' / 'settings.json'
    claude_md_path = cpath / 'CLAUDE.md'

    # --- settings.json ---------------------------------------------------------------------
    consumer_settings = None
    if settings_path.exists():
        try:
            consumer_settings = json.loads(settings_path.read_text(encoding='utf-8'))
        except json.JSONDecodeError:
            devs.append(Dev('FAIL', 'consumer', "'.claude/settings.json' is not valid JSON.",
                             "Fix the JSON syntax in .claude/settings.json (a stray comma or brace)."))
    elif c['opted_in']:
        names = ', '.join(t['name'] for t in c['opted_in'])
        devs.append(Dev('FAIL', 'consumer', "No '.claude/settings.json' but registry lists opted-in tool(s).",
                         f"Create .claude/settings.json and merge the opt-in snippet(s) for: {names}."))

    for ti in c['opted_in']:
        tool = ti['name']
        optin_path = OPTINS_DIR / f"{tool}.json"
        if not optin_path.exists():
            devs.append(Dev('FAIL', 'shared',
                             f"Registered tool '{tool}' has no canonical opt-in snippet (templates/optins/{tool}.json).",
                             None))
            continue
        # Expand config placeholders so the canonical command matches what a compliant consumer's
        # settings.json actually contains (the single source of truth for the command form).
        optin = get_expanded_optin(optin_path, config)

        # canonical snippet references hook file(s) that must exist shared-side
        if 'hooks' in optin:
            for evt, groups in optin['hooks'].items():
                for grp in groups:
                    for h in grp.get('hooks', []):
                        # command form is `<launcher> "<script path>"` - grab the quoted path.
                        m = re.search(r'"([^"]+)"', h.get('command', ''))
                        if m:
                            hook_file = m.group(1)
                            if not Path(hook_file).exists():
                                devs.append(Dev('FAIL', 'shared',
                                                 f"opt-in '{tool}' references a missing hook file: {hook_file}",
                                                 None))

        # consumer's settings.json must still contain the canonical snippet (drift) - EITHER the
        # direct-path form (optin, computed above) OR the dispatch-wrapper form (design\
        # consumer_reference_indirection.md: a new-connection consumer's settings.json legitimately
        # contains this shape instead, and both are equally compliant, never mixed-and-matched
        # tolerance for an actually-wrong command).
        dispatch_optin = get_dispatch_optin(optin_path, tool, config)
        if consumer_settings is not None:
            missing = False
            if 'hooks' in optin:
                for evt, groups in optin['hooks'].items():
                    # Normalize path separators before comparing: the canonical command uses '/'
                    # (cross-platform), but a consumer scaffolded earlier may still carry '\'. In
                    # compressed JSON a Windows separator is escaped to '\\', so collapsing
                    # '\\' -> '/' makes the two forms compare equal without masking any
                    # non-separator drift (path text, launcher, matcher still compared).
                    canon_direct = [
                        json.dumps(g, separators=(',', ':')).replace('\\\\', '/') for g in groups
                    ]
                    canon_dispatch = [
                        json.dumps(g, separators=(',', ':')).replace('\\\\', '/')
                        for g in dispatch_optin.get('hooks', {}).get(evt, [])
                    ]
                    have = []
                    consumer_hooks = consumer_settings.get('hooks') if isinstance(consumer_settings, dict) else None
                    if isinstance(consumer_hooks, dict) and evt in consumer_hooks:
                        have = [
                            json.dumps(g, separators=(',', ':')).replace('\\\\', '/')
                            for g in consumer_hooks[evt]
                        ]
                    direct_ok = all(entry in have for entry in canon_direct)
                    dispatch_ok = bool(canon_dispatch) and all(entry in have for entry in canon_dispatch)
                    if not (direct_ok or dispatch_ok):
                        missing = True
            if missing:
                devs.append(Dev('FAIL', 'consumer',
                                 f"settings.json no longer contains the canonical opt-in snippet for '{tool}'.",
                                 f"Re-merge templates/optins/{tool}.json into .claude/settings.json (or re-run the scaffolder: new_consumer.py --force)."))

    # --- CLAUDE.md imports -----------------------------------------------------------------
    md_imports = []
    if claude_md_path.exists():
        md = claude_md_path.read_text(encoding='utf-8')
        # '.' (not '\S') so an import_base path containing a space still matches - '.' excludes
        # only newlines, and an @import line is always exactly one line, so this can't
        # over-match into the next line.
        md_imports = re.findall(r'@.*?templates/(\w+)\.md', md)

        # design\consumer_reference_indirection.md: a new-connection consumer's CLAUDE.md carries
        # only the single @.claude/hub_pointer.md line - the real per-piece imports live one hop
        # deeper, in that gitignored, per-host file. Resolve through it so every check below
        # (mandatory-piece glance, import-drift tripwire) keeps working transparently for either
        # shape, old or new.
        if HUB_POINTER_IMPORT_LINE in md:
            pointer = parse_hub_pointer(cpath / HUB_POINTER_RELPATH)
            if pointer is None:
                devs.append(Dev('FAIL', 'consumer',
                                 f"CLAUDE.md imports '{HUB_POINTER_IMPORT_LINE}' but "
                                 f"{HUB_POINTER_RELPATH} doesn't exist (or isn't parseable) on this "
                                 "host - every protocol-piece import is broken here.",
                                 "Re-run \"connect project\" (or scripts\\relocate.py) from the hub "
                                 "to regenerate it."))
            else:
                md_imports = list(md_imports) + pointer['imports']
                if pointer['shared_root'] != config['shared_root'] or pointer['import_base'] != config['import_base']:
                    devs.append(Dev('FAIL', 'consumer',
                                     f"{HUB_POINTER_RELPATH} is stale on this host (doesn't match "
                                     "this machine's live shared_root/import_base).",
                                     "Re-run scripts\\relocate.py (or \"connect project\") from the hub."))
    elif c['imported']:
        names = ', '.join(p['name'] for p in c['imported'])
        devs.append(Dev('FAIL', 'consumer', "No CLAUDE.md but registry lists imported protocol piece(s).",
                         f"Create a CLAUDE.md that imports: {names}."))

    # broken import: CLAUDE.md imports a piece that doesn't exist shared-side
    seen = []
    for p in md_imports:
        if p not in seen:
            seen.append(p)
    for p in seen:
        if not (TEMPLATES_DIR / f"{p}.md").exists():
            devs.append(Dev('FAIL', 'shared', f"Consumer imports templates/{p}.md, which does not exist in tower_crane.", None))

    # import drift: registry lists a piece the CLAUDE.md no longer imports (the tripwire)
    for pi in c['imported']:
        if pi['name'] not in md_imports:
            devs.append(Dev('FAIL', 'consumer',
                             f"Import drift: registry lists piece '{pi['name']}' but CLAUDE.md no longer imports it.",
                             f"Re-add the line '@{config['import_base']}/{pi['name']}.md' to CLAUDE.md, or (if the opt-out was intentional) file a request to update this consumer's registry entry."))

    # mandatory pieces (filing + compliance + shared_resources) - a glance, not a hard fail. A
    # SKILL_PIECES entry (e.g. 'filing') is satisfied either the old flat way (imports itself
    # directly) or the Track-1 way (imports its companion + carries a project-local skill stub).
    for m in ('filing', 'compliance', 'shared_resources'):
        if m in md_imports:
            continue
        skill_piece = SKILL_PIECES.get(m)
        if skill_piece and skill_piece['companion'] in md_imports:
            missing = [s for s in skill_piece['skills']
                       if not (cpath / '.claude' / 'skills' / s / 'SKILL.md').exists()]
            if not missing:
                continue
            devs.append(Dev('FAIL', 'consumer',
                             f"Imports '{skill_piece['companion']}' (the Track-1 resume-check companion for "
                             f"'{m}') but is missing the skill stub(s): "
                             + ', '.join(f".claude/skills/{s}/SKILL.md" for s in missing) + ".",
                             f"Copy each missing stub from {SKILLS_DIR}/<name>/SKILL.md into "
                             f".claude/skills/<name>/SKILL.md, replacing {{{{IMPORT_BASE}}}} with "
                             f"'{config['import_base']}'."))
            continue
        devs.append(Dev('WARN', 'consumer', f"Mandatory protocol piece '{m}' is not imported by CLAUDE.md.",
                         f"Add '@{config['import_base']}/{m}.md' to CLAUDE.md's Shared Workflow Protocol section."))

    # --- Track-1 skill stub drift (toolkit-governed only) -----------------------------------
    # Same mechanism as the opt-in hook check above: a consumer's project-local stub must still
    # match the canonical source (with {{IMPORT_BASE}} resolved), or its trigger/body has drifted.
    # One piece can scaffold more than one skill (e.g. 'continuity' -> checkpoint + archive), so
    # iterate the flattened skill-name list, not the piece names themselves.
    skill_names = sorted({name for sp in SKILL_PIECES.values() for name in sp['skills']} | set(STANDALONE_SKILLS))
    for name in skill_names:
        stub_path = cpath / '.claude' / 'skills' / name / 'SKILL.md'
        if not stub_path.exists():
            continue
        canon_path = SKILLS_DIR / name / 'SKILL.md'
        if not canon_path.exists():
            devs.append(Dev('FAIL', 'shared',
                             f"Consumer has a '{name}' skill stub but tower_crane has no canonical source "
                             f"at templates/skills/{name}/SKILL.md.", None))
            continue
        # design\consumer_reference_indirection.md: a stub matching EITHER the direct-substitution
        # rendering (not-yet-migrated consumer) OR the .claude/hub_pointer.md-indirected rendering
        # (new connection) is compliant - both are independently valid canonical shapes.
        expected_direct = materialize_skill_stub(canon_path, config['import_base'], use_pointer=False)
        expected_pointer = materialize_skill_stub(canon_path, config['import_base'], use_pointer=True)
        actual = stub_path.read_text(encoding='utf-8')
        if actual not in (expected_direct, expected_pointer):
            devs.append(Dev('FAIL', 'consumer',
                             f"'{name}' skill stub (.claude/skills/{name}/SKILL.md) has drifted from the "
                             f"canonical source.",
                             f"Re-copy {canon_path} into .claude/skills/{name}/SKILL.md, replacing "
                             f"{{{{IMPORT_BASE}}}} with '{config['import_base']}'."))

    # --- _hub_dispatch.py drift (design\consumer_reference_indirection.md) -------------------
    # Tracked, host-invariant content - byte-identical on every host, forever, so this is a plain
    # verbatim compare (no substitution), same shape as the skill-stub drift check above.
    dispatch_path = cpath / HUB_DISPATCH_RELPATH
    if dispatch_path.exists():
        canon_dispatch_path = TEMPLATES_DIR / HUB_DISPATCH_TEMPLATE
        if not canon_dispatch_path.exists():
            devs.append(Dev('FAIL', 'shared',
                             f"Consumer has {HUB_DISPATCH_RELPATH} but tower_crane has no canonical "
                             f"source at templates/{HUB_DISPATCH_TEMPLATE}.", None))
        elif dispatch_path.read_text(encoding='utf-8') != canon_dispatch_path.read_text(encoding='utf-8'):
            devs.append(Dev('FAIL', 'consumer',
                             f"{HUB_DISPATCH_RELPATH} has drifted from the canonical source.",
                             f"Re-copy {canon_dispatch_path} into {HUB_DISPATCH_RELPATH} verbatim."))

    # --- private_opted_in: (design\private_tools.md, decision 4) ----------------------------
    # Each entry is either a private hook (has a canonical snippet in PRIVATE_OPTINS_DIR) or a
    # private Track-1 skill (has a canonical stub in PRIVATE_SKILLS_DIR) - inferred by which
    # exists, since private tool names are unique within toolkit_private\. Unlike the public
    # STANDALONE_SKILLS loop above (which only checks whatever's physically present, since public
    # skills aren't individually registry-tracked), an entry here IS an explicit registry
    # declaration - same "declared but missing = drift" semantics as the public opted_in: hook
    # loop, so a missing private skill stub is a FAIL, not a silent skip.
    for ti in c['private_opted_in']:
        tool = ti['name']
        priv_optin_path = PRIVATE_OPTINS_DIR / f"{tool}.json"
        priv_skill_path = PRIVATE_SKILLS_DIR / tool / 'SKILL.md'

        if priv_optin_path.exists():
            optin = get_expanded_optin(priv_optin_path, config)
            if 'hooks' in optin:
                for evt, groups in optin['hooks'].items():
                    for grp in groups:
                        for h in grp.get('hooks', []):
                            m = re.search(r'"([^"]+)"', h.get('command', ''))
                            if m and not Path(m.group(1)).exists():
                                devs.append(Dev('FAIL', 'shared',
                                                 f"private opt-in '{tool}' references a missing hook file: {m.group(1)}",
                                                 None))
            if consumer_settings is not None and 'hooks' in optin:
                missing = False
                for evt, groups in optin['hooks'].items():
                    canon = [json.dumps(g, separators=(',', ':')).replace('\\\\', '/') for g in groups]
                    have = []
                    consumer_hooks = consumer_settings.get('hooks') if isinstance(consumer_settings, dict) else None
                    if isinstance(consumer_hooks, dict) and evt in consumer_hooks:
                        have = [json.dumps(g, separators=(',', ':')).replace('\\\\', '/')
                                for g in consumer_hooks[evt]]
                    for entry in canon:
                        if entry not in have:
                            missing = True
                if missing:
                    devs.append(Dev('FAIL', 'consumer',
                                     f"settings.json no longer contains the canonical private opt-in snippet for '{tool}'.",
                                     f"Re-merge toolkit_private/templates/optins/{tool}.json into .claude/settings.json."))
        elif priv_skill_path.exists():
            stub_path = cpath / '.claude' / 'skills' / tool / 'SKILL.md'
            if not stub_path.exists():
                devs.append(Dev('FAIL', 'consumer',
                                 f"Registry lists private tool '{tool}' as opted-in but its skill stub "
                                 f"(.claude/skills/{tool}/SKILL.md) is missing.",
                                 f"Copy {priv_skill_path} into .claude/skills/{tool}/SKILL.md."))
            else:
                expected = materialize_skill_stub(priv_skill_path)
                actual = stub_path.read_text(encoding='utf-8')
                if actual != expected:
                    devs.append(Dev('FAIL', 'consumer',
                                     f"'{tool}' private skill stub (.claude/skills/{tool}/SKILL.md) has "
                                     f"drifted from the canonical source.",
                                     f"Re-copy {priv_skill_path} into .claude/skills/{tool}/SKILL.md."))
        else:
            devs.append(Dev('FAIL', 'shared',
                             f"Registered private tool '{tool}' has no canonical source in toolkit_private\\ "
                             f"(checked templates/optins/{tool}.json and templates/skills/{tool}/SKILL.md).",
                             None))

    return devs


def write_guidance(c, this_host, devs, head_sha, today):
    actionable = [d for d in devs if d.severity == 'FAIL' and d.target == 'consumer']
    cpath = host_path(c, this_host)

    if not actionable:
        had_section = SECTION_CHECKER in read_sections(cpath)
        write_section(cpath, c['name'], SECTION_CHECKER, None)
        if had_section:
            print("  guidance: removed stale checker-deviations section (consumer now compliant).")
        return

    body_lines = [
        f"Generated by tower_crane `check_tower_crane.py` on {today} from tower_crane HEAD `{head_sha}`.",
        '',
        'This project has drifted from the tower_crane consumer baseline. Per the imported',
        '`compliance.md` protocol, your agent should surface this at session start, summarize it,',
        '**ask before changing anything**, apply on confirmation, then delete this file. If a listed',
        'item was an intentional local choice, leave it and note it - do not auto-change it.',
        '',
    ]
    for n, d in enumerate(actionable, 1):
        body_lines.append(f"{n}. {d.message}")
        if d.fix:
            body_lines.append(f"   Fix: {d.fix}")
        body_lines.append('')
    body_lines.append('Once every item above is resolved (or consciously declined), delete this file.')

    write_section(cpath, c['name'], SECTION_CHECKER, body_lines)
    print(f"  guidance: wrote checker-deviations section ({len(actionable)} actionable deviation(s)).")


def invoke_reference_scan(config, this_host, consumer_filter, write_guidance_flag, head_sha, today):
    print()
    print("--- Pass B: reference & drift scan ---")

    if not CONSUMERS_DIR.is_dir():
        report('WARN', "No consumers/ folder - nothing to scan.")
        return
    files = sorted(CONSUMERS_DIR.glob('*.md'))
    if consumer_filter:
        files = [f for f in files if f.stem == consumer_filter]
    if not files:
        if consumer_filter:
            report('FAIL', f"No registry entry for consumer '{consumer_filter}' (consumers/{consumer_filter}.md).")
        else:
            report('WARN', "No consumer registry entries found.")
        return

    for f in files:
        c = parse_registry(f)
        if c is None:
            report('FAIL', f"{f.name} : no parseable `yaml` registry block.")
            continue

        # 2-host write-back floor (design\multi_machine_hub.md): applies to every consumer this
        # tool touches, regardless of whether it's reachable on THIS machine - a human opening the
        # file directly must always see state that matches reality.
        if reconcile_scope_floor(f, c):
            print(f"  [fixed] {f.stem}: scope -> multi_machine (2+ hosts: entries present).")

        print()
        owner_suffix = f" - owner: {c['owner']}" if c['owner'] else ''
        print(f"Consumer: {c['name']} ({f.stem}) - scope: {effective_scope(c)}{owner_suffix}")

        # Federate (#1): a consumer with no hosts.<this_host> entry isn't on THIS disk, so its
        # path/settings can't be validated here. Skip silently (not a WARN).
        if this_host not in c['hosts']:
            print(f"  [skip] not connected on this machine ('{this_host}') - hosts: "
                  f"{', '.join(sorted(c['hosts'])) or '(none)'}.")
            continue

        devs = test_consumer(c, config, this_host)
        if not devs:
            report('PASS', "no deviations.")
        else:
            for d in devs:
                report(d.severity, d.message)

        if write_guidance_flag:
            write_guidance(c, this_host, devs, head_sha, today)


def check_hub_self_use_skills(config):
    """Hub self-use skill drift (design\\optimize_ux.md): the hub isn't a registered consumer of
    its own scaffolder, so a skill installed via self_hooks.py's "skills" opt-in key (e.g.
    hub_commands, capability_relationships) never passes through the per-consumer loop above.
    Scans every templates/optins/*.json for a "skills" list and, for each name that's actually
    installed on this machine (.claude/skills/<name>/SKILL.md exists - not installed is a valid
    off state, not a drift), compares it against the canonical templates/skills/<name>/SKILL.md
    with {{IMPORT_BASE}} resolved the same way self_hooks.py resolves it before writing the
    installed copy (same substitution the per-consumer loop above already applies at line ~430) -
    a no-op for a stub with no such placeholder, like hub_commands."""
    print()
    print("--- Hub self-use skill drift ---")
    found_any = False
    for optin_path in sorted(OPTINS_DIR.glob('*.json')):
        optin = json.loads(optin_path.read_text(encoding='utf-8'))
        for name in optin.get('skills', []):
            found_any = True
            stub_path = PROJECT_ROOT / '.claude' / 'skills' / name / 'SKILL.md'
            if not stub_path.exists():
                print(f"  [skip] '{name}' not installed on this machine (self_hooks.py --enable {name} to turn it on).")
                continue
            canon_path = SKILLS_DIR / name / 'SKILL.md'
            if not canon_path.exists():
                report('FAIL', f"Hub self-use skill '{name}' is installed but tower_crane has no "
                                f"canonical source at templates/skills/{name}/SKILL.md.")
                continue
            expected = materialize_skill_stub(canon_path, config['import_base'])
            actual = stub_path.read_text(encoding='utf-8')
            if actual != expected:
                report('FAIL', f"Hub self-use skill '{name}' (.claude/skills/{name}/SKILL.md) has drifted "
                                f"from the canonical source.")
                print(f"        fix: re-run `python scripts\\self_hooks.py --enable {name}` to refresh it.")
            else:
                report('PASS', f"'{name}' matches canonical source.")
    if not found_any:
        print("  (no optin declares a 'skills' key yet)")


# ==================================================================================================
# --diagnose - fact-reporting only, no verdict (design\connection_diagnostics.md)
# ==================================================================================================
# Tower-Crane-authored commit-message patterns, matched against a consumer's own git log (Category
# B - durable, survives hand-deletion of the files those commits touched).
DIAGNOSE_COMMIT_PATTERNS = [
    ('disconnect', re.compile(r'^Tower Crane: disconnected')),
    ('checkpoint', re.compile(r'^Checkpoint:')),
    ('archive', re.compile(r'^Archive:')),
]

# The four protocol-piece @import targets a live CLAUDE.md carries - mirrors SKILL_PIECES'
# companion values above plus 'compliance' (the one piece that stays flat, never Track-1).
DIAGNOSE_IMPORT_NAMES = ('filing_resume_check', 'compliance', 'shared_resources_resume_check',
                          'continuity_resume_check')


def diagnose_fact(present, label, indent):
    tag = '[present]' if present else '[absent] '
    print(f"{indent}{tag} {label}")


def diagnose_git_log(repo_dir, pathspec=None):
    """(sha, date, subject) tuples, newest first, for `repo_dir`'s git log (optionally scoped to
    `pathspec`). Returns [] for anything short of success (no .git, empty history, git missing) -
    every check in --diagnose is best-effort and must never itself raise."""
    cmd = ['git', '-C', str(repo_dir), 'log', '--format=%H%x1f%ci%x1f%s']
    if pathspec:
        cmd += ['--', pathspec]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
    except OSError:
        return []
    if proc.returncode != 0:
        return []
    out = []
    for line in proc.stdout.splitlines():
        parts = line.split('\x1f')
        if len(parts) == 3:
            out.append((parts[0], parts[1], parts[2]))
    return out


def diagnose_consumer_git_history(consumer_repo):
    print("  consumer's own repo - Tower-Crane-authored commit patterns:")
    if not (consumer_repo / '.git').exists():
        print("    [absent]  no .git\\ at this path - can't check history here.")
        return
    commits = diagnose_git_log(consumer_repo)
    if not commits:
        print("    [absent]  no git history readable (empty repo, or git unavailable).")
        return
    for label, pattern in DIAGNOSE_COMMIT_PATTERNS:
        matches = [c for c in commits if pattern.search(c[2])]
        if matches:
            sha, dt, subj = matches[0]
            print(f"    [present] {len(matches)} '{label}'-shaped commit(s) - most recent "
                  f"{dt[:10]} ({sha[:8]}): \"{subj}\"")
        else:
            print(f"    [absent]  no '{label}'-shaped commit found.")


def diagnose_hub_registry_history(slug):
    print(f"  hub's own repo - consumers/{slug}.md history:")
    commits = diagnose_git_log(PROJECT_ROOT, pathspec=f"consumers/{slug}.md")
    if not commits:
        print(f"    [absent]  no commits touching consumers/{slug}.md (never registered under "
              f"this slug, or this hub clone's history doesn't reach back far enough).")
        return
    sha, dt, subj = commits[0]
    print(f"    [present] {len(commits)} commit(s) - most recent {dt[:10]} ({sha[:8]}): \"{subj}\"")


def diagnose_consumer_files(path):
    cpath = Path(path)
    print("  consumer's own project files (Category A - unreliable if hand-edited/corrupted):")
    if not cpath.exists():
        print(f"    [absent]  path does not exist on disk: {cpath}")
        return

    claude_md_path = cpath / 'CLAUDE.md'
    if claude_md_path.exists():
        text = claude_md_path.read_text(encoding='utf-8')
        diagnose_fact(True, "CLAUDE.md exists", '    ')
        diagnose_fact('## Tower Crane In Use' in text, "'## Tower Crane In Use' heading", '    ')
        diagnose_fact('## Shared Workflow Protocol' in text, "'## Shared Workflow Protocol' heading", '    ')
        diagnose_fact('## Tower Crane (disconnected)' in text, "'## Tower Crane (disconnected)' marker", '    ')
        diagnose_fact(HUB_POINTER_IMPORT_LINE in text,
                      f"'{HUB_POINTER_IMPORT_LINE}' indirection line (design\\consumer_reference_indirection.md)",
                      '    ')
        live_imports = sorted(set(re.findall(r'(?m)^@\S+/(\w+)\.md\s*$', text)) & set(DIAGNOSE_IMPORT_NAMES))
        if live_imports:
            print(f"    [present] live @import line(s) for: {', '.join(live_imports)}")
        else:
            print("    [absent]  no live @import line for any protocol piece")
    else:
        diagnose_fact(False, "CLAUDE.md exists", '    ')

    diagnose_fact((cpath / HUB_POINTER_RELPATH).exists(), f"{HUB_POINTER_RELPATH} (gitignored, this host)", '    ')
    diagnose_fact((cpath / HUB_DISPATCH_RELPATH).exists(), f"{HUB_DISPATCH_RELPATH}", '    ')

    settings_path = cpath / '.claude' / 'settings.json'
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text(encoding='utf-8'))
            diagnose_fact(True, ".claude/settings.json exists (valid JSON)", '    ')
            hook_names = set()
            for groups in (settings.get('hooks') or {}).values():
                for grp in groups:
                    for h in grp.get('hooks', []):
                        cmd = h.get('command', '')
                        m = re.search(r'hooks[\\/](\w+)\.py', cmd)
                        if m:
                            hook_names.add(m.group(1))
                        m = re.search(r'_hub_dispatch\.py"?\s+(\w+)', cmd)
                        if m:
                            hook_names.add(m.group(1))
            if hook_names:
                print(f"    [present] hook entry/entries: {', '.join(sorted(hook_names))}")
            else:
                print("    [absent]  no tower_crane hook entries")
            allow = (settings.get('permissions') or {}).get('allow') or []
            has_read_rule = any(a.startswith('Read(') and 'templates' in a for a in allow)
            diagnose_fact(has_read_rule, "a Read(.../templates/**) permission rule", '    ')
        except json.JSONDecodeError:
            print("    [present] .claude/settings.json exists but is NOT valid JSON")
    else:
        diagnose_fact(False, ".claude/settings.json exists", '    ')

    skills_dir = cpath / '.claude' / 'skills'
    if skills_dir.is_dir():
        names = sorted(d.name for d in skills_dir.iterdir() if d.is_dir())
        if names:
            print(f"    [present] .claude/skills/ subdirectories: {', '.join(names)}")
        else:
            print("    [absent]  .claude/skills/ exists but is empty")
    else:
        diagnose_fact(False, ".claude/skills/ directory", '    ')

    diagnose_fact((cpath / 'FIRST_RUN.md').exists(), "FIRST_RUN.md", '    ')
    diagnose_fact((cpath / 'TOWER_CRANE_DISCONNECT_NOTES.md').exists(), "TOWER_CRANE_DISCONNECT_NOTES.md", '    ')

    progress_path = cpath / 'project_progress.md'
    if progress_path.exists():
        text = progress_path.read_text(encoding='utf-8')
        work_log_idx = text.find('## Work Log')
        work_log_text = text[work_log_idx:] if work_log_idx != -1 else text
        n_mentions = len(re.findall(r'Tower Crane|Checkpoint:|Archive:', work_log_text))
        print(f"    [present] project_progress.md exists (Work Log mentions Tower Crane/"
              f"Checkpoint/Archive: {n_mentions} time(s))")
    else:
        diagnose_fact(False, "project_progress.md", '    ')


def diagnose_hub_side(slug):
    registry_path = CONSUMERS_DIR / f"{slug}.md"
    print("  hub's own state (Category A):")
    if registry_path.exists():
        c = parse_registry(registry_path)
        if c is None:
            print(f"    [present] consumers/{slug}.md exists but is NOT parseable")
        else:
            hosts = ', '.join(sorted(c['hosts'])) or '(none)'
            print(f"    [present] consumers/{slug}.md - scope: {effective_scope(c)}, hosts: {hosts}")
    else:
        print(f"    [absent]  consumers/{slug}.md (no registry entry)")
    change_requests_dir = PROJECT_ROOT / 'change_requests'
    if change_requests_dir.is_dir():
        tickets = sorted(p.name for p in change_requests_dir.glob(f"*{slug}*"))
        if tickets:
            print(f"    [present] change_requests\\ ticket(s) naming '{slug}': {', '.join(tickets)}")
        else:
            print(f"    [absent]  no change_requests\\ ticket naming '{slug}'")


def run_diagnose(path, slug):
    print("=== check_tower_crane.py --diagnose ===")
    print("Fact-reporting only - present/absent, no verdict. See troubleshoot_project_connection.md")
    print("for how to read these.")
    if not path and not slug:
        print("  (neither --path nor --slug given - nothing to check.)")
        return
    print()
    print(f"path: {path or '(not given)'}")
    print(f"slug: {slug or '(not given)'}")

    # Priority principle (design\connection_diagnostics.md): durable git history survives hand-
    # deletion/corruption of the current-state files Category A reads, so it's checked - and shown
    # - first, not after.
    print()
    print("--- Category B: durable git history (checked first - survives file deletion) ---")
    if path:
        diagnose_consumer_git_history(Path(path))
    else:
        print("  consumer's own repo: (skipped - no --path given)")
    if slug:
        diagnose_hub_registry_history(slug)
    else:
        print("  hub's own repo: (skipped - no --slug given)")

    print()
    print("--- Category A: Tower-Crane-specific current-state files ---")
    if path:
        diagnose_consumer_files(path)
    else:
        print("  consumer's own project files: (skipped - no --path given)")
    if slug:
        diagnose_hub_side(slug)
    else:
        print("  hub's own state: (skipped - no --slug given)")

    print()
    print("=== end diagnose ===")


def get_head_sha():
    try:
        result = subprocess.run(
            ['git', '-C', str(SHARED_ROOT), 'rev-parse', '--short', 'HEAD'],
            capture_output=True, text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except OSError:
        pass
    return 'unknown'


# ==================================================================================================
# main
# ==================================================================================================
def main():
    parser = argparse.ArgumentParser(description="Cross-consumer checker for tower_crane.")
    parser.add_argument('--consumer', default=None, help="Slug of a single consumer to scope pass B to. Default: all.")
    parser.add_argument('--write-guidance', action='store_true',
                         help="Write COMPLIANCE_GUIDANCE.md for audited consumers with actionable FAILs.")
    parser.add_argument('--skip-golden', action='store_true', help="Skip pass A.")
    parser.add_argument('--skip-reference', action='store_true', help="Skip pass B (and guidance writing).")
    parser.add_argument('--diagnose', action='store_true',
                         help="Fact-reporting mode for a non-standard connect/disconnect state "
                              "(design\\connection_diagnostics.md) - present/absent facts only, "
                              "no verdict or fix. Combine with --path and/or --slug. Runs "
                              "standalone; ignores every other flag above.")
    parser.add_argument('--path', default=None, help="--diagnose: consumer project path to inspect.")
    parser.add_argument('--slug', default=None, help="--diagnose: registry slug to inspect.")
    args = parser.parse_args()

    config = get_shared_config(SHARED_ROOT)

    if args.diagnose:
        run_diagnose(args.path, args.slug)
        sys.exit(0)

    this_host = str(config.get('host_id', ''))
    head_sha = get_head_sha()
    today = date.today().isoformat()

    print("=== check_tower_crane.py ===")
    print(f"tower_crane HEAD: {head_sha}")
    if args.consumer:
        print(f"scope: consumer '{args.consumer}'")

    if not args.skip_golden:
        invoke_golden_suite(config)
    if not args.skip_reference:
        invoke_reference_scan(config, this_host, args.consumer, args.write_guidance, head_sha, today)
        check_hub_self_use_skills(config)

    print()
    print(f"=== Summary: {COUNTS['PASS']} passed, {COUNTS['WARN']} warning(s), {COUNTS['FAIL']} failure(s) ===")

    sys.exit(1 if COUNTS['FAIL'] > 0 else 0)


if __name__ == '__main__':
    main()
