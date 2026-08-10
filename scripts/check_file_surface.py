#!/usr/bin/env python3
"""
check_file_surface.py - a "what kind of file is this, and does it belong here" gate, independent
of what any individual file's content means. Built alongside Fix 3 Phase 3
(design\\update_trust_review.md) after a live discussion found that the other new gates
(check_agents_pr_gate.py's AGENTS.md-content checks, consistency_check.py's Python static
analysis) only defend against careless mistakes in the surface they already know to look at - a
deliberate adversary doesn't need to write a mismatched variable name, they can write the payload
in a language no checker here reads, or hide it in a file extension nobody scans. This script
assumes an adversary, not just carelessness (design\\update_trust_review.md's own threat model).

Runs over a whole-repo diff between two refs (matches the Locked "diff scope for the review gate
= the whole inner repo, no path filter" decision) - never scoped to one file, since the whole point
is catching a script or directive file showing up somewhere unexpected.

Seven checks, five hard-fail, two soft-flag:
  1. Known AI-directive filename        HARD  - a new/renamed file matching a real, converged
                                                  AI-directive filename convention (CLAUDE.md,
                                                  .cursorrules, a second AGENTS.md, etc.) anywhere
                                                  other than the one canonical AGENTS.md.
  2. Non-Python script language          HARD  - this project's Locked "Language policy" decision
                                                  (project_progress.md Decisions) is Python-only for
                                                  every runtime script, no exceptions remaining now
                                                  that the legacy PowerShell tools are fully retired
                                                  to _archive\\. A new script in any other language is
                                                  either going to be a compatibility problem or an
                                                  attempt to dodge the Python-only checkers - both
                                                  are reasons to stop and ask, not silently allow.
                                                  Detected two ways: file extension, AND (to catch
                                                  the "rename it to .txt" evasion) a non-Python
                                                  shebang line, regardless of extension.
  3. Python file outside its home        HARD  - a .py file added anywhere other than hooks\\,
                                                  scripts\\, agents\\, or a tests\\<tool>\\ fixture.
  4. Binary file                         HARD  - this is a text-based tooling repo; it should never
                                                  need to ship a binary blob. The single clearest
                                                  "something is very wrong" signal for an obfuscated
                                                  payload.
  5. Disguised-code heuristic            SOFT  - content (eval/exec/base64/curl-pipe-shell/etc.) in
                                                  a file not already classified as code. Heuristic,
                                                  so it can't safely hard-block (a design doc
                                                  legitimately quotes shell commands in prose) - see
                                                  capability-vs-content in check_agents_pr_gate.py
                                                  for the same reasoning.
  6. Invisible/formatting Unicode       HARD  - added 2026-07-27 (security stress-test pass,
                                                  design\\security_stress_test.md), the single most
                                                  directly-relevant gap this project has: zero-width
                                                  chars, bidi embedding/override/isolate controls,
                                                  variation selectors, and Unicode tag characters can
                                                  render as blank (or reordered) in a normal editor,
                                                  diff view, or chat code block, while an LLM parsing
                                                  the raw text still reads them - the exact mechanism
                                                  behind the academic "Trojan Source" attack (Boucher
                                                  & Anderson 2021, CVE-2021-42574) and its 2025
                                                  application against AI-assistant rules files
                                                  (Pillar Security's "Rules File Backdoor"). This repo
                                                  IS an AGENTS.md-governed AI-directive system and the
                                                  entire trust gate rests on "a human reads the diff
                                                  verbatim" - an invisible character would defeat that
                                                  specific guarantee silently. No legitimate reason
                                                  for these codepoints anywhere in a text tooling repo.
  7. Python capability creep            SOFT  - added 2026-07-27, same stress-test pass: new/changed
                                                  .py code introducing a network call, dynamic-exec,
                                                  or deserialization primitive not obviously covered
                                                  by AGENTS.md's declared capability manifest ("never
                                                  an arbitrary network request outside git/gh, never
                                                  reading or emitting credentials"). consistency_check.py
                                                  only checks correctness, never intent, and check 5
                                                  above deliberately skips already-recognized code as
                                                  "not disguised" - so a legitimate-looking new script
                                                  doing something it has no business doing currently
                                                  got zero scrutiny anywhere in this pipeline. Heuristic
                                                  and deliberately narrow: subprocess/os.system are NOT
                                                  flagged, since invoking git/gh via subprocess is this
                                                  project's own normal, sanctioned pattern everywhere.
  8. Outgoing private-content leak     MIXED  - added 2026-07-30 (design\\resource_sharing_model.md's
                                                  B1), the OUTGOING direction every check above is
                                                  blind to - this repo's other gates all defend
                                                  against a malicious/careless *incoming* change; this
                                                  is the one that would have caught the near-miss that
                                                  started that whole design doc (private client
                                                  content nearly landing in this public repo, caught
                                                  by the user before commit, not by anything here).
                                                  Two parts sharing one signal source (the outer hub's
                                                  private consumers\\*.md registry - the exact same
                                                  detector templates\\shared_resources.md's own
                                                  save-trigger heuristic uses, Locked as "one
                                                  implementation, not two"):
                                                    8a HARD - added content literally matching a live
                                                       consumer's registered name or identifying path
                                                       segment. Deterministic and low-false-positive,
                                                       since it's matched against real registry data,
                                                       not a shape guess.
                                                    8b SOFT - added content matching a generic
                                                       absolute-user-home-path shape (`C:\\Users\\...`,
                                                       `/home/...`, `/Users/...`) that isn't an obvious
                                                       placeholder (you/your/<user>/username). Kept
                                                       soft because this repo's own docs legitimately
                                                       use placeholder paths like `C:\\Users\\you\\...`
                                                       as examples.
                                                    8c HARD - added content literally matching a live
                                                       host_id (machine name) - either a registered
                                                       consumer's `host:` field, or this machine's own
                                                       config.local.json `host_id`. Added
                                                       2026-08-10 (design\\multi_machine_hub.md's
                                                       Decisions table): the same class of leak as 8a
                                                       (an identifier that names a specific person's
                                                       setup, not generic tooling), so it gets the
                                                       same hard-fail treatment and the same signal
                                                       source, just a different registry field.
                                                  All three gracefully report PASS/N-A (not a false
                                                  FAIL) when consumers\\ / config.local.json isn't
                                                  reachable from this checkout - expected for a
                                                  standalone toolkit\\ clone or this repo's own CI
                                                  runner, which never checks out the outer private
                                                  repo and won't have a filled-in per-machine config.

Usage: python scripts\\check_file_surface.py --base-sha <sha> --head-sha <sha>
Run from anywhere; always resolves paths against this toolkit\\ repo, not the caller's cwd.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config_lib import get_shared_config

SHARED_ROOT = None  # set in main() after argparse, so this file can be imported without side effects


def _resolve_shared_root():
    from pathlib import Path
    return Path(__file__).resolve().parent.parent


COUNTS = {'PASS': 0, 'WARN': 0, 'FAIL': 0}

# Other real, converged AI-directive filename conventions. AGENTS.md itself is deliberately NOT in
# this set - a second copy of it elsewhere is checked separately below, against the canonical
# constant directly, so there's only one spelling of that particular filename in this file.
KNOWN_DIRECTIVE_BASENAMES = {
    'claude.md', '.cursorrules', '.windsurfrules', '.clinerules', 'gemini.md',
    'copilot-instructions.md', 'system_prompt.md', 'system_prompt.txt',
}
CANONICAL_AGENTS_MD = 'AGENTS.md'  # the one sanctioned location, repo root

NONPY_SCRIPT_EXTENSIONS = {
    '.sh', '.bash', '.zsh', '.ps1', '.psm1', '.psd1', '.bat', '.cmd', '.js', '.mjs', '.cjs',
    '.ts', '.rb', '.pl', '.php', '.go', '.rs', '.c', '.cpp', '.cc', '.h', '.java', '.class',
    '.jar', '.exe', '.dll', '.so', '.dylib', '.wasm', '.lua', '.groovy', '.scala', '.swift',
    '.kt', '.vbs',
}
PY_EXT = '.py'
ALLOWED_PY_DIR_PREFIXES = ('hooks/', 'scripts/', 'agents/')
FIXTURE_DIR_PREFIX = 'tests/'
WORKFLOW_DIR_PREFIX = '.github/workflows/'  # legitimately embeds shell in `run:` blocks

DISGUISED_CODE_TOKENS = [
    'eval(', 'exec(', 'base64', '| sh', '| bash', 'invoke-expression', 'iex(',
    'os.system(', 'subprocess.', 'curl ', 'wget ',
]

# Invisible/formatting Unicode codepoints - the "Trojan Source" set (Boucher & Anderson 2021,
# CVE-2021-42574/CVE-2021-42694) plus the additional invisible/steganography ranges used by the
# 2025 "Rules File Backdoor" attacks against AI-assistant instruction files. Each range renders as
# blank, zero-width, or silently reorders surrounding text in a normal editor/diff/chat view, while
# still being fully legible to an LLM tokenizing the raw bytes. No legitimate use in this repo.
INVISIBLE_UNICODE_RANGES = [
    (0x200B, 0x200F),   # zero-width space/non-joiner/joiner, LTR mark, RTL mark
    (0x202A, 0x202E),   # bidi embedding/override controls (LRE/RLE/PDF/LRO/RLO)
    (0x2060, 0x2064),   # word joiner, invisible math operators
    (0x2066, 0x2069),   # bidi isolate controls (LRI/RLI/FSI/PDI) - Trojan Source's primary vector
    (0xFEFF, 0xFEFF),   # zero-width no-break space / byte-order mark
    (0xFE00, 0xFE0F),   # variation selectors
    (0xE0100, 0xE01EF), # variation selectors supplement
    (0xE0000, 0xE007F), # Unicode tag characters (used for text steganography/smuggling)
]

# Deliberately narrow: subprocess/os.system are NOT here (this project's scripts invoke git/gh via
# subprocess constantly - that's the sanctioned pattern, not a capability creep). This targets
# capabilities AGENTS.md's own manifest explicitly disclaims: network access and credential
# handling, plus dynamic-exec/deserialization primitives a static correctness checker can't catch.
CAPABILITY_CREEP_TOKENS = [
    'requests.', 'urllib.request', 'urllib3', 'http.client', 'socket.', 'ftplib', 'smtplib',
    'paramiko', 'telnetlib', 'eval(', 'exec(', '__import__(', 'marshal.loads(', 'pickle.loads(',
    'base64.b64decode(',
]

# Check 8: outgoing private-content leak. ABS_PATH_RE matches an absolute user-home path and
# captures the first path segment after it (the part that would actually identify a real user/
# project, as opposed to the generic C:\Users\/home\ prefix every machine has).
ABS_PATH_RE = re.compile(r'(?:[A-Za-z]:[\\/]Users[\\/]|/home/|/Users/)([^\s\\/<>]+)')
PLACEHOLDER_SEGMENTS = {'you', 'your', 'username', 'user', '<user>', '<you>'}


def report(level, message):
    COUNTS[level] += 1
    print(f"[{level}] {message}")


def git(shared_root, args):
    return subprocess.run(['git', '-C', str(shared_root)] + args, capture_output=True, text=True)


def changed_files(shared_root, base_sha, head_sha):
    """Returns a list of (status, path) for every added/modified/renamed/copied file, path is the
    file's path AT HEAD (the new path, for renames/copies). Deletions are excluded - nothing to
    classify about a file that's gone."""
    proc = git(shared_root, ['diff', '--name-status', '-M', '-C', f'{base_sha}..{head_sha}'])
    out = []
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split('\t')
        status = parts[0]
        if status.startswith('D'):
            continue
        if status.startswith(('R', 'C')) and len(parts) >= 3:
            out.append((status, parts[2]))
        elif len(parts) >= 2:
            out.append((status, parts[1]))
    return out


def binary_paths(shared_root, base_sha, head_sha):
    proc = git(shared_root, ['diff', '--numstat', f'{base_sha}..{head_sha}'])
    out = set()
    for line in proc.stdout.splitlines():
        parts = line.split('\t')
        if len(parts) >= 3 and parts[0] == '-' and parts[1] == '-':
            out.add(parts[2])
    return out


def read_file_at(shared_root, ref, path):
    proc = git(shared_root, ['show', f'{ref}:{path}'])
    return proc.stdout if proc.returncode == 0 else None


def check_known_directive_filenames(files):
    hits = []
    for status, path in files:
        norm = path.replace('\\', '/')
        if norm == CANONICAL_AGENTS_MD:
            continue
        basename = PurePosixPath(norm).name.lower()
        if basename in KNOWN_DIRECTIVE_BASENAMES or basename == CANONICAL_AGENTS_MD.lower():
            hits.append(norm)
    if not hits:
        report('PASS', "no new/renamed file matches a known AI-directive filename convention.")
        return
    for h in hits:
        report('FAIL', f"'{h}' matches a known AI-directive filename convention (CLAUDE.md, "
                       ".cursorrules, a second AGENTS.md, etc.) outside the one canonical "
                       f"{CANONICAL_AGENTS_MD} - this repo's convention is a single file; a new one "
                       "needs a deliberate design decision, not a silent addition.")


def check_language_and_location(shared_root, files, head_sha):
    flagged = False
    for status, path in files:
        norm = path.replace('\\', '/')
        ext = PurePosixPath(norm).suffix.lower()
        under_allowed_dir = norm.startswith(ALLOWED_PY_DIR_PREFIXES)
        under_fixtures = norm.startswith(FIXTURE_DIR_PREFIX)

        if ext in NONPY_SCRIPT_EXTENSIONS:
            report('FAIL', f"'{norm}' is a non-Python script (extension {ext!r}) - this project's "
                           "Locked language policy is Python-only for every runtime script, no "
                           "exceptions remain now that legacy PowerShell tooling is fully retired. "
                           "A different language is either a compatibility risk or a way to dodge "
                           "the Python-only checkers - needs a deliberate decision either way.")
            flagged = True
            continue

        if ext == PY_EXT and not under_allowed_dir and not under_fixtures:
            report('FAIL', f"'{norm}' is a Python file outside hooks\\/scripts\\/agents\\ (or a "
                           "tests\\ fixture) - code doesn't belong in this location.")
            flagged = True
            continue

    # shebang scan, independent of extension - catches "rename my shell script to .txt"
    for status, path in files:
        norm = path.replace('\\', '/')
        ext = PurePosixPath(norm).suffix.lower()
        if ext in NONPY_SCRIPT_EXTENSIONS:
            continue  # already reported above, don't double-count
        text = read_file_at(shared_root, head_sha, path)
        if text is None:
            continue
        first_line = text.splitlines()[0] if text.splitlines() else ''
        if first_line.startswith('#!') and 'python' not in first_line.lower():
            report('FAIL', f"'{norm}' carries a non-Python shebang ({first_line.strip()!r}) - "
                           "flagged regardless of its extension, since renaming a script doesn't "
                           "change what it is.")
            flagged = True

    if not flagged:
        report('PASS', "every script-like file is Python, in an expected location.")


def check_binary_files(shared_root, base_sha, head_sha):
    paths = binary_paths(shared_root, base_sha, head_sha)
    if not paths:
        report('PASS', "no binary files added or modified.")
        return
    for p in sorted(paths):
        report('FAIL', f"'{p}' is a binary file - this is a text-based tooling repo; a binary blob "
                       "has no legitimate reason to ship here and is the clearest signal of an "
                       "obfuscated payload.")


def check_disguised_code(shared_root, files, base_sha, head_sha):
    hits = []
    for status, path in files:
        norm = path.replace('\\', '/')
        ext = PurePosixPath(norm).suffix.lower()
        if ext == PY_EXT and (norm.startswith(ALLOWED_PY_DIR_PREFIXES) or norm.startswith(FIXTURE_DIR_PREFIX)):
            continue  # already-recognized code, not "disguised"
        if norm.startswith(WORKFLOW_DIR_PREFIX):
            continue  # legitimately embeds shell in `run:` blocks
        proc = git(shared_root, ['diff', f'{base_sha}..{head_sha}', '--', path])
        added_lines = [l[1:] for l in proc.stdout.splitlines()
                       if l.startswith('+') and not l.startswith('+++')]
        for line in added_lines:
            lower = line.lower()
            for token in DISGUISED_CODE_TOKENS:
                if token in lower:
                    hits.append((norm, token, line.strip()))
    if not hits:
        report('PASS', "no code-like content found hiding in a file not already classified as code.")
        return
    report('WARN', "content resembling executable code appears in file(s) not classified as code - "
                   "heuristic, so this is a nudge for reviewer attention, not a block:")
    for norm, token, line in hits[:10]:
        print(f"  {norm} matched {token!r}: {line}")


def _is_invisible_char(ch):
    cp = ord(ch)
    return any(lo <= cp <= hi for lo, hi in INVISIBLE_UNICODE_RANGES)


def check_invisible_unicode(shared_root, files, base_sha, head_sha):
    """Hard-fail on any invisible/formatting Unicode codepoint added anywhere in the diff - see
    check 6 in the module docstring for the full rationale. Scans every file, not just code: the
    attack this defends against specifically targets prose/instruction files (AGENTS.md itself,
    templates\\, README.md), not scripts."""
    hits = []
    for status, path in files:
        norm = path.replace('\\', '/')
        proc = git(shared_root, ['diff', f'{base_sha}..{head_sha}', '--', path])
        for line in proc.stdout.splitlines():
            if not line.startswith('+') or line.startswith('+++'):
                continue
            for ch in line[1:]:
                if _is_invisible_char(ch):
                    hits.append((norm, f'U+{ord(ch):04X}'))
    if not hits:
        report('PASS', "no invisible/formatting Unicode codepoints found in added content.")
        return
    seen = set()
    for norm, cp in hits:
        key = (norm, cp)
        if key in seen:
            continue
        seen.add(key)
        report('FAIL', f"'{norm}' adds an invisible/formatting Unicode character ({cp}) - no "
                       "legitimate reason for this in a text-based tooling repo. This is the exact "
                       "technique behind Unicode 'Trojan Source' attacks and the AI-rules-file "
                       "'hidden instruction' attack class: text invisible (or reordered) to a human "
                       "reviewer, fully legible to an LLM parsing the raw bytes.")


def check_python_capability_creep(shared_root, files, base_sha, head_sha):
    """Soft nudge - see check 7 in the module docstring for the full rationale. Only scans .py
    files already recognized as code under the allowed dirs; unrecognized-location .py files are
    already a hard-fail via check_language_and_location above."""
    hits = []
    for status, path in files:
        norm = path.replace('\\', '/')
        ext = PurePosixPath(norm).suffix.lower()
        if ext != PY_EXT or not norm.startswith(ALLOWED_PY_DIR_PREFIXES):
            continue
        proc = git(shared_root, ['diff', f'{base_sha}..{head_sha}', '--', path])
        for line in proc.stdout.splitlines():
            if not line.startswith('+') or line.startswith('+++'):
                continue
            content = line[1:]
            lower = content.lower()
            for token in CAPABILITY_CREEP_TOKENS:
                if token in lower:
                    hits.append((norm, token, content.strip()))
    if not hits:
        report('PASS', "no new capability-creep token (network call, dynamic-exec, "
                       "deserialization) found in changed Python code.")
        return
    report('WARN', "changed Python code adds token(s) suggesting a capability outside AGENTS.md's "
                   "declared manifest (git/gh + local filesystem only) - reviewer should confirm "
                   "this is intended, not a smuggled capability:")
    for norm, token, line in hits[:10]:
        print(f"  {norm} matched {token!r}: {line}")


def _load_consumer_signals(shared_root):
    """Live consumer names + identifying path segments, read fresh from the outer hub's private
    consumers\\*.md registry (one level above this toolkit\\ repo - design\\local_first_reframe.md's
    outer/inner split). This is the same signal source templates\\shared_resources.md's own
    save-trigger heuristic uses (Locked as "one detector, not two"). Returns ([], []) when
    consumers\\ isn't reachable - expected and correct for a standalone toolkit\\ checkout (e.g.
    this repo's own CI runner, which only checks out toolkit\\ and never the outer private repo)."""
    consumers_dir = shared_root.parent / 'consumers'
    if not consumers_dir.is_dir():
        return [], []
    names, path_segments = [], []
    for md in sorted(consumers_dir.glob('*.md')):
        raw = md.read_text(encoding='utf-8')
        block_m = re.search(r'```yaml\s*\r?\n(.*?)\r?\n```', raw, re.DOTALL)
        if not block_m:
            continue
        block = block_m.group(1)
        name_m = re.search(r'^name:\s*(.+?)\s*$', block, re.MULTILINE)
        if name_m and name_m.group(1).strip():
            names.append(name_m.group(1).strip())
        path_m = re.search(r'^path:\s*(.+?)\s*$', block, re.MULTILINE)
        if path_m and path_m.group(1).strip():
            segs = [s for s in re.split(r'[\\/]', path_m.group(1).strip()) if s and s != '~']
            if segs:
                path_segments.append(segs[-1])  # the leaf project folder - the actual identifier
    return names, path_segments


def _load_host_signals(shared_root):
    """Live host_id (machine name) values - every registered consumer's `host:` field, plus this
    machine's own config.local.json `host_id` if a filled-in config is reachable. Same signal
    shape as _load_consumer_signals above, mirrored per design\\multi_machine_hub.md's Decisions
    table: a host_id is exactly as identifying as a consumer/project name and deserves the same
    outgoing-leak protection. Returns [] when nothing is reachable - expected for a standalone
    toolkit\\ checkout (no outer consumers\\, no filled-in config.local.json), never a false FAIL."""
    hosts = []
    consumers_dir = shared_root.parent / 'consumers'
    if consumers_dir.is_dir():
        for md in sorted(consumers_dir.glob('*.md')):
            raw = md.read_text(encoding='utf-8')
            block_m = re.search(r'```yaml\s*\r?\n(.*?)\r?\n```', raw, re.DOTALL)
            if not block_m:
                continue
            host_m = re.search(r'^host:\s*(.+?)\s*$', block_m.group(1), re.MULTILINE)
            if host_m and host_m.group(1).strip():
                hosts.append(host_m.group(1).strip())
    try:
        cfg = get_shared_config(shared_root)
        host_id = cfg.get('host_id')
        if host_id and not str(host_id).startswith('<'):
            hosts.append(str(host_id))
    except RuntimeError:
        pass  # no filled-in config.local.json reachable - nothing to add, not an error here
    return hosts


def check_outgoing_host_id(shared_root, files, base_sha, head_sha):
    """Check 8c, HARD - see check 8 in the module docstring for the full rationale. Added content
    literally matching a live host_id value."""
    hosts = sorted(set(_load_host_signals(shared_root)), key=len, reverse=True)
    if not hosts:
        report('PASS', "no live host_id reachable from this checkout - nothing to match against "
                       "(expected for a standalone toolkit\\ checkout, e.g. CI).")
        return
    hits = []
    for status, path in files:
        norm = path.replace('\\', '/')
        proc = git(shared_root, ['diff', f'{base_sha}..{head_sha}', '--', path])
        for line in proc.stdout.splitlines():
            if not line.startswith('+') or line.startswith('+++'):
                continue
            content = line[1:]
            for host in hosts:
                if host in content:
                    hits.append((norm, host, content.strip()))
                    break
    if not hits:
        report('PASS', "no live host_id (machine name) found in added content.")
        return
    for norm, host, content in hits[:10]:
        report('FAIL', f"'{norm}' adds content matching a live host_id ({host!r}) - a machine name "
                       "identifies a specific person's setup exactly like a consumer/project name "
                       "does, and toolkit\\'s public repo must stay generic. If this is a "
                       "coincidental match on generic prose, rephrase it; otherwise this belongs in "
                       "shared_resources\\ (hub root) or a private consumer note, never toolkit\\.")


def check_outgoing_private_content(shared_root, files, base_sha, head_sha):
    """Check 8a, HARD - see check 8 in the module docstring for the full rationale. Added content
    literally matching a live consumer's registered name or leaf path segment."""
    names, path_segments = _load_consumer_signals(shared_root)
    signals = sorted(set(names) | set(path_segments), key=len, reverse=True)
    if not signals:
        report('PASS', "no live consumer registry reachable from this checkout - nothing to "
                       "match against (expected for a standalone toolkit\\ checkout, e.g. CI).")
        return
    hits = []
    for status, path in files:
        norm = path.replace('\\', '/')
        proc = git(shared_root, ['diff', f'{base_sha}..{head_sha}', '--', path])
        for line in proc.stdout.splitlines():
            if not line.startswith('+') or line.startswith('+++'):
                continue
            content = line[1:]
            for sig in signals:
                if sig in content:
                    hits.append((norm, sig, content.strip()))
                    break
    if not hits:
        report('PASS', "no live consumer name or identifying path segment found in added content.")
        return
    for norm, sig, content in hits[:10]:
        report('FAIL', f"'{norm}' adds content matching a live consumer identifier ({sig!r}) - "
                       "this looks like private project/client content about to reach toolkit\\'s "
                       "public remote. If this is a coincidental match on generic prose, rephrase "
                       "it; otherwise this belongs in shared_resources\\ (hub root), never toolkit\\.")


def check_generic_absolute_paths(shared_root, files, base_sha, head_sha):
    """Check 8b, SOFT - see check 8 in the module docstring for the full rationale. Kept soft
    (not hard-fail) because this repo's own docs legitimately use placeholder absolute paths like
    `C:\\Users\\you\\...` as examples - a shape-only match can't tell those from a real leak."""
    hits = []
    for status, path in files:
        norm = path.replace('\\', '/')
        proc = git(shared_root, ['diff', f'{base_sha}..{head_sha}', '--', path])
        for line in proc.stdout.splitlines():
            if not line.startswith('+') or line.startswith('+++'):
                continue
            content = line[1:]
            for m in ABS_PATH_RE.finditer(content):
                seg = m.group(1).strip('<>')
                if seg.lower() in PLACEHOLDER_SEGMENTS:
                    continue
                hits.append((norm, m.group(0), content.strip()))
    if not hits:
        report('PASS', "no non-placeholder absolute user-home path found in added content.")
        return
    report('WARN', "added content contains an absolute user-home path that isn't an obvious "
                   "placeholder (you/your/<user>/username) - heuristic nudge, confirm it's "
                   "generic documentation, not a real leaked path:")
    for norm, matched, content in hits[:10]:
        print(f"  {norm} matched {matched!r}: {content}")


def main():
    parser = argparse.ArgumentParser(
        description="File-surface classifier: language, location, and disguise checks over a "
                     "whole-repo diff. Assumes an adversary, not just carelessness."
    )
    parser.add_argument('--base-sha', required=True)
    parser.add_argument('--head-sha', default='HEAD')
    args = parser.parse_args()

    shared_root = _resolve_shared_root()

    print("=== check_file_surface.py ===")
    print(f"comparing {args.base_sha}..{args.head_sha}")

    files = changed_files(shared_root, args.base_sha, args.head_sha)
    if not files:
        print("[N/A] no added/modified/renamed files in this diff - nothing to classify.")
        sys.exit(0)

    check_known_directive_filenames(files)
    check_language_and_location(shared_root, files, args.head_sha)
    check_binary_files(shared_root, args.base_sha, args.head_sha)
    check_disguised_code(shared_root, files, args.base_sha, args.head_sha)
    check_invisible_unicode(shared_root, files, args.base_sha, args.head_sha)
    check_python_capability_creep(shared_root, files, args.base_sha, args.head_sha)
    check_outgoing_private_content(shared_root, files, args.base_sha, args.head_sha)
    check_outgoing_host_id(shared_root, files, args.base_sha, args.head_sha)
    check_generic_absolute_paths(shared_root, files, args.base_sha, args.head_sha)

    print()
    print(f"=== Summary: {COUNTS['PASS']} passed, {COUNTS['WARN']} warning(s), {COUNTS['FAIL']} failure(s) ===")
    sys.exit(1 if COUNTS['FAIL'] > 0 else 0)


if __name__ == '__main__':
    main()
