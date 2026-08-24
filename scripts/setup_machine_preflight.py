#!/usr/bin/env python3
"""
setup_machine_preflight.py - templates\\setup_machine.md's revised Step 0 (design\\
command_procedure_audit.md's C1-C6): mechanizes the fixed, real-branching sequence that used to be
100% prose - shape detection (flat vs. already-nested vs. ambiguous), the in-place nesting mechanic,
building or attaching the outer layer, and the host_id context lookup (C6). Same Shape-B rationale
as resume_check.py/checkpoint_git.py (B1/B2): a mechanical sequence with real branches deserves one
deterministic call, not a checklist re-decided from scratch the one time it runs.

What this script deliberately does NOT do:
  - Ask "reconnect vs. new" (C1) or "where did you actually clone this" (C5's fallback question) -
    those are judgment questions for the user, not facts a script can check. `--detect` surfaces the
    evidence; the agent asks the human-facing question and picks the next subcommand accordingly.
  - Check `gh --version` (C4) - reversed to a lazy, exactly-when-needed check in setup_machine.md's
    own prose. Front-loading it here would be the exact over-eager-capability-check C4 rejected.
  - Commit or push anything `--new-outer` scaffolds - that reuses the ordinary checkpoint_git.py
    (B2) flow instead of duplicating its commit/leak-scan/push logic here (`checkpoint_git.py
    --include-all` stages and commits fresh, all-untracked scaffold content exactly the same way it
    stages any other checkpoint).

Subcommands (mutually exclusive):
  --detect
      Read-only. Classifies the CURRENT WORKING DIRECTORY as one of:
        flat       - cwd itself is a toolkit clone (hooks\\, scripts\\, templates\\, AGENTS.md,
                     config.example.json all present directly in cwd) with no outer wrapper around
                     it yet. Needs --nest.
        nested     - already correctly structured, either as outer-root-with-toolkit-subfolder or
                     as a toolkit\\ checkout one level under an already-populated outer folder.
                     Nothing further needed here - proceed to setup_machine.md's Step 1.
        ambiguous  - neither shape found. C5: ask the user directly where they actually cloned
                     things, relative to where this session is running.
      Prints the classification plus the evidence it was decided on.

  --nest
      Mutating. Only valid when --detect would say 'flat'. Creates a `toolkit\\` subfolder inside
      cwd and moves every existing top-level entry (dotfiles/`.git\\` included) down into it, except
      the newly created `toolkit\\` itself. cwd's own contents change; cwd itself never moves, so
      this needs no session restart (supersedes the old restart-required Bootstrapping Step 3).

  --new-outer [--git-remote-url URL]
      Mutating. Scaffolds a brand-new outer hub at cwd: a thin CLAUDE.md pointer (`@toolkit/
      AGENTS.md`), a `.gitignore` excluding `/toolkit/` and the two per-machine `.claude\\` files, empty
      `consumers\\`/`change_requests\\`/`design\\` folders, and a skeleton `project_progress.md`. Runs
      `git init` if cwd isn't already a repo. If --git-remote-url is given, also runs `git remote add
      origin <url>` (no commit/push - see "what this script does NOT do" above).

  --attach-existing --git-remote-url URL
      Mutating. The C2 workaround: `git init`, `git remote add origin <url>`, `git fetch origin`,
      `git checkout -b main --track origin/main`. Used both for a fresh outer folder that already has
      a remote to attach, and (reusing the identical workaround, per C2's own note) for the
      post-`--nest` reconnect branch, where cwd is now non-empty (the just-created `toolkit\\`
      subfolder) and a plain `git clone` would refuse it.

  --known-hosts
      Read-only (C6). Lists host identities this hub already knows about - every consumer registry's
      `hosts:` map (`consumers\\*.md`) plus `project_progress.md`'s own Work Log host tags
      (`**YYYY-MM-DD — HOST session:**`), exactly the two sources C6 names - so Step 5's host_id
      question can offer them as context instead of proposing only the raw hostname with nothing to
      compare it to. Deliberately does NOT scan `project_progress_archive.md`: its heading
      parenthetical isn't reliably a host tag at all (real examples found live: `(later session)`,
      `(discussion)` - free text, not host identities), so treating it as one would reintroduce the
      exact "designed around our own artifacts" mistake C6 explicitly rejected. Empty output is
      expected and fine on a genuinely first-ever machine.

Self-locating like every other script here: TOOLKIT_ROOT/PROJECT_ROOT are computed fresh from this
file's own current location on each run, never cached - so --known-hosts (which only makes sense
after --nest/--attach-existing/--new-outer has run) correctly resolves against the now-nested
`toolkit\\` even though this same file was sitting flat in cwd earlier in the same session.
"""

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from registry_lib import parse_registry

TOOLKIT_SIGNATURE = ['hooks', 'scripts', 'templates', 'AGENTS.md', 'config.example.json']
OUTER_SIGNATURE = ['project_progress.md', 'consumers', 'change_requests']


def _git(root, args):
    return subprocess.run(['git', '-C', str(root)] + args, capture_output=True, text=True)


def has_toolkit_signature(folder):
    return [name for name in TOOLKIT_SIGNATURE if not (folder / name).exists()]


def has_outer_signature(folder):
    return [name for name in OUTER_SIGNATURE if (folder / name).exists()]


def cmd_detect(cwd):
    missing_here = has_toolkit_signature(cwd)
    toolkit_sub = cwd / 'toolkit'
    missing_sub = has_toolkit_signature(toolkit_sub) if toolkit_sub.is_dir() else TOOLKIT_SIGNATURE

    if not missing_here:
        # cwd itself is a toolkit clone. Nested (old Scenario A) if the parent already looks like
        # an outer hub; otherwise flat, needing --nest.
        parent_found = has_outer_signature(cwd.parent)
        if parent_found:
            print(f"[NESTED] cwd ({cwd}) is a toolkit\\ checkout; its parent ({cwd.parent}) already "
                  f"has outer-hub markers: {', '.join(parent_found)}. Nothing further needed here - "
                  "proceed to setup_machine.md Step 1.")
        else:
            print(f"[FLAT] cwd ({cwd}) IS the toolkit content itself (all of "
                  f"{', '.join(TOOLKIT_SIGNATURE)} present directly here), with no outer wrapper "
                  "around it. Run --nest next.")
        return

    if not missing_sub:
        # cwd/toolkit is a toolkit clone - cwd itself is the outer root, already correctly nested.
        print(f"[NESTED] cwd ({cwd}) is the outer hub root; `toolkit\\` subfolder found and looks "
              "like a real toolkit checkout. Nothing further needed here - proceed to "
              "setup_machine.md Step 1.")
        return

    print(f"[AMBIGUOUS] Neither cwd ({cwd}) nor cwd\\toolkit\\ looks like a toolkit checkout.")
    print(f"  cwd missing: {', '.join(missing_here)}")
    print(f"  cwd\\toolkit\\ missing: {', '.join(missing_sub)}"
          if toolkit_sub.is_dir() else "  cwd\\toolkit\\ does not exist.")
    print("  C5: ask the user directly where they actually cloned things, relative to where this "
          "session is running - don't assume cwd is the right place.")


def cmd_nest(cwd):
    missing_here = has_toolkit_signature(cwd)
    if missing_here:
        print(f"[ABORT] cwd ({cwd}) doesn't look like a flat toolkit clone (missing: "
              f"{', '.join(missing_here)}) - re-run --detect before --nest.")
        sys.exit(1)
    toolkit_dir = cwd / 'toolkit'
    if toolkit_dir.exists():
        print(f"[ABORT] {toolkit_dir} already exists - this doesn't look like a fresh flat clone. "
              "Re-run --detect to check the real shape before proceeding.")
        sys.exit(1)

    toolkit_dir.mkdir()
    moved = []
    for entry in sorted(cwd.iterdir()):
        if entry.name == 'toolkit':
            continue
        shutil.move(str(entry), str(toolkit_dir / entry.name))
        moved.append(entry.name)

    print(f"[NESTED] Created {toolkit_dir} and moved {len(moved)} item(s) into it:")
    for name in moved:
        print(f"    {name}")
    print("cwd itself is unchanged - no session restart needed. Next: --new-outer or "
          "--attach-existing to build/attach the outer layer.")


CLAUDE_MD_TEMPLATE = """# Tower Crane — this machine's operator file

This is the one file in either repo (outer or `toolkit\\`) that keeps Claude Code's magic
`CLAUDE.md` name, so it's the only file anywhere that auto-loads. It exists for two reasons:

1. **It imports the actual, shared hub-operating instructions** — `toolkit\\AGENTS.md` — as one
   whole file (never split into pieces; splitting would break that file's cross-tool readability,
   since `@import` is Claude-Code-specific and other AI tools read `AGENTS.md` natively).
2. **It's where personal, unshared, per-machine customization for this hub belongs** — anything
   added directly here, below the import line, never floats to the public toolkit repo or any
   fork. There is nothing local-only to add yet; this file stays this short until there is.

@toolkit/AGENTS.md
"""

GITIGNORE_TEMPLATE = """/toolkit/
/.claude/settings.local.json
/.claude/self_hooks_status.md
"""

PROJECT_PROGRESS_TEMPLATE = """# Project Progress

## Current Status
(Dashboard — recent state deltas, active work-in-progress, and known standing defects that would
otherwise cost a session a wrong decision. Not a capability inventory: what's built lives in
`README.md`; settled calls live in the Decisions table below; completed work lives in the Work
Log. Registered consumers, opt-ins, and per-host connections are in `consumers\\*.md` — read there,
not restated here.)

## Next Up
(Queued — identified, not yet started. Graduates into Current Status the session someone actually
starts it; drops out entirely once done, with the Work Log carrying the history.)

## Decisions
| Item | Status | Notes |
|---|---|---|

## Work Log (newest first — stays complete; say "archive" anytime to move closed-out entries to project_progress_archive.md)
"""


def cmd_new_outer(cwd, git_remote_url):
    missing_here = has_toolkit_signature(cwd)
    if not missing_here:
        print(f"[ABORT] cwd ({cwd}) still looks like a flat toolkit clone (all of "
              f"{', '.join(TOOLKIT_SIGNATURE)} present directly here) - run --nest first.")
        sys.exit(1)
    found = has_outer_signature(cwd)
    if found:
        print(f"[ABORT] cwd ({cwd}) already has outer-hub markers ({', '.join(found)}) - refusing "
              "to scaffold over an existing hub. If this is the mistaken-run recovery case (C1), "
              "reconcile by hand: discard or move the previously-scaffolded files first.")
        sys.exit(1)

    written = []
    for name, content in [
        ('CLAUDE.md', CLAUDE_MD_TEMPLATE),
        ('.gitignore', GITIGNORE_TEMPLATE),
        ('project_progress.md', PROJECT_PROGRESS_TEMPLATE),
    ]:
        path = cwd / name
        path.write_text(content, encoding='utf-8')
        written.append(name)

    for name in ('consumers', 'change_requests', 'design'):
        (cwd / name).mkdir(exist_ok=True)
        written.append(name + '\\')

    print(f"[SCAFFOLDED] {cwd}:")
    for name in written:
        print(f"    {name}")

    if not (cwd / '.git').exists():
        init = _git(cwd, ['init'])
        print(f"[GIT INIT] {init.stdout.strip() or init.stderr.strip()}")

    if git_remote_url:
        remote = _git(cwd, ['remote', 'add', 'origin', git_remote_url])
        if remote.returncode == 0:
            print(f"[REMOTE] origin -> {git_remote_url}")
        else:
            print(f"[WARN] could not add remote: {remote.stderr.strip()}")

    print("Nothing committed or pushed yet - run the ordinary checkpoint flow next "
          "(`checkpoint_git.py --message \"Initial hub scaffold\" --include-all`) to commit and "
          "push this for real.")


def cmd_attach_existing(cwd, git_remote_url):
    if not git_remote_url:
        print("[ABORT] --attach-existing requires --git-remote-url.")
        sys.exit(1)
    if (cwd / '.git').exists():
        print(f"[ABORT] {cwd} is already a git repo - this doesn't look like the reconnect case. "
              "Re-run --detect to check the real shape before proceeding.")
        sys.exit(1)

    init = _git(cwd, ['init'])
    print(f"[GIT INIT] {init.stdout.strip() or init.stderr.strip()}")
    remote = _git(cwd, ['remote', 'add', 'origin', git_remote_url])
    if remote.returncode != 0:
        print(f"[ABORT] could not add remote: {remote.stderr.strip()}")
        sys.exit(1)
    print(f"[REMOTE] origin -> {git_remote_url}")

    fetch = _git(cwd, ['fetch', 'origin'])
    if fetch.returncode != 0:
        print(f"[ABORT] fetch failed: {fetch.stderr.strip()}")
        sys.exit(1)
    print("[FETCHED] origin.")

    checkout = _git(cwd, ['checkout', '-b', 'main', '--track', 'origin/main'])
    if checkout.returncode != 0:
        print(f"[ABORT] checkout failed: {checkout.stderr.strip()}\n"
              "A common cause: an existing local file collides with a path the remote already "
              "tracks - git's own error above says which. Resolve by hand, then re-run.")
        sys.exit(1)
    print(f"[ATTACHED] {cwd} now tracks origin/main.\n{checkout.stdout.strip()}")


HOST_TAG_RE = re.compile(
    r'^\*\*\d{4}-\d{2}-\d{2}\s*—\s*([A-Za-z][A-Za-z0-9_]*)\s+session', re.MULTILINE)


def cmd_known_hosts(cwd):
    project_root = Path(__file__).resolve().parent.parent.parent
    sources = {}  # host_id -> set of source descriptions

    consumers_dir = project_root / 'consumers'
    if consumers_dir.is_dir():
        for f in sorted(consumers_dir.glob('*.md')):
            c = parse_registry(f)
            if c is None:
                continue
            for host_id in c['hosts']:
                sources.setdefault(host_id, set()).add(f"consumers\\{f.name}")

    progress_path = project_root / 'project_progress.md'
    if progress_path.is_file():
        text = progress_path.read_text(encoding='utf-8', errors='replace')
        for m in HOST_TAG_RE.finditer(text):
            sources.setdefault(m.group(1), set()).add('project_progress.md')

    if not sources:
        print("[KNOWN-HOSTS] none found - this looks like a genuinely first-ever machine for this "
              "hub. Propose the raw hostname with no further context (today's plain behavior).")
        return

    print("[KNOWN-HOSTS] host identities already on record for this hub:")
    for host_id in sorted(sources):
        print(f"    {host_id}  (from: {', '.join(sorted(sources[host_id]))})")
    print("Offer these alongside the raw hostname, and ask directly whether this machine has "
          "connected before under one of them or a different name (C6) - don't infer it.")


def main():
    parser = argparse.ArgumentParser(
        description="templates\\setup_machine.md's Step 0 pre-flight sequence, mechanized "
                     "(design\\command_procedure_audit.md's C1-C6)."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--detect', action='store_true', help="Classify the current shape.")
    group.add_argument('--nest', action='store_true', help="Perform the in-place nesting mechanic.")
    group.add_argument('--new-outer', action='store_true',
                        help="Scaffold a brand-new outer hub at cwd.")
    group.add_argument('--attach-existing', action='store_true',
                        help="Attach an existing outer remote to cwd (the C2 workaround).")
    group.add_argument('--known-hosts', action='store_true',
                        help="List host identities already known to this hub (C6).")
    parser.add_argument('--git-remote-url', default=None,
                         help="Used by --new-outer (optional) and --attach-existing (required).")
    args = parser.parse_args()

    cwd = Path.cwd()

    if args.detect:
        cmd_detect(cwd)
    elif args.nest:
        cmd_nest(cwd)
    elif args.new_outer:
        cmd_new_outer(cwd, args.git_remote_url)
    elif args.attach_existing:
        cmd_attach_existing(cwd, args.git_remote_url)
    elif args.known_hosts:
        cmd_known_hosts(cwd)


if __name__ == '__main__':
    main()
