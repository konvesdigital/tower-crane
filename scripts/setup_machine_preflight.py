#!/usr/bin/env python3
"""
setup_machine_preflight.py - templates\\setup_machine.md's Step 0: shape detection (flat vs.
already-nested vs. ambiguous), the in-place nesting mechanic, building or attaching the outer
layer, and the host_id context lookup.

What this script does NOT do:
  - Ask "reconnect vs. new" or "where did you actually clone this" - those are judgment questions
    for the user, not facts a script can check. `--detect` surfaces the evidence; the agent asks
    the human-facing question and picks the next subcommand accordingly.
  - Check `gh --version`.
  - Commit or push anything `--new-outer` scaffolds - that goes through the ordinary
    checkpoint_git.py flow instead (`checkpoint_git.py --include-all` stages and commits fresh,
    all-untracked scaffold content the same way it stages any other checkpoint).

Subcommands (mutually exclusive):
  --detect
      Read-only. Classifies the CURRENT WORKING DIRECTORY as one of:
        flat       - cwd itself is a toolkit clone (hooks\\, scripts\\, templates\\, AGENTS.md,
                     config.example.json all present directly in cwd) with no outer wrapper around
                     it yet. Needs --nest.
        nested     - already correctly structured, either as outer-root-with-toolkit-subfolder or
                     as a toolkit\\ checkout one level under an already-populated outer folder.
                     Nothing further needed here - proceed to setup_machine.md's Step 1.
        ambiguous  - neither shape found. Ask the user directly where they actually cloned things,
                     relative to where this session is running.
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
      Read-only. Lists host identities this hub already knows about - every consumer registry's
      `hosts:` map (`consumers\\*.md`) plus `project_progress.md`'s own Work Log host tags
      (`**YYYY-MM-DD — HOST session:**`). Does not scan `project_progress_archive.md`: its heading
      parenthetical isn't reliably a host tag at all (real examples found: `(later session)`,
      `(discussion)` - free text, not host identities). Empty output is expected on a genuinely
      first-ever machine.

  --reattach-origin --git-remote-url URL
      Mutating. Restores a removed 'origin' remote on an already-nested, already-historied repo -
      unlike --attach-existing, this never runs `git init`/`checkout -b`: local `main` and its
      history are untouched, just `remote add` + `fetch` + restoring the upstream-tracking
      relationship. Never merges or resets - any real divergence from being disconnected is left
      for the ordinary `update`/`checkpoint` flow to surface. `cmd_detect`'s NESTED output reports
      `[ORIGIN-MISSING]` per-repo when this is needed.

  --clear-uninstall-note
      Mutating. Deletes a stale TOWER_CRANE_UNINSTALLED.md from cwd (the outer hub root) if
      present. No-op, not an error, if the file isn't there.

Self-locating like every other script here: TOOLKIT_ROOT/PROJECT_ROOT are computed fresh from this
file's own current location on each run, never cached - so --known-hosts (which only makes sense
after --nest/--attach-existing/--new-outer has run) correctly resolves against the now-nested
`toolkit\\` even though this same file was sitting flat in cwd earlier in the same session.
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from registry_lib import parse_registry
from config_lib import get_shared_config, merge_bash_allowlist

TOOLKIT_SIGNATURE = ['hooks', 'scripts', 'templates', 'AGENTS.md', 'config.example.json']
OUTER_SIGNATURE = ['project_progress.md', 'consumers', 'change_requests']


def _git(root, args):
    return subprocess.run(['git', '-C', str(root)] + args, capture_output=True, text=True)


def has_toolkit_signature(folder):
    return [name for name in TOOLKIT_SIGNATURE if not (folder / name).exists()]


def has_outer_signature(folder):
    return [name for name in OUTER_SIGNATURE if (folder / name).exists()]


def _origin_status(repo_dir):
    """None if repo_dir isn't a git repo; else True/False for whether 'origin' is configured."""
    if not (repo_dir / '.git').exists():
        return None
    return 'origin' in _git(repo_dir, ['remote']).stdout.split()


def _report_origin_and_note(outer_dir, toolkit_dir):
    """Shared by both NESTED branches of cmd_detect(): reports each repo's 'origin' status and
    whether a stale uninstall note is sitting in the outer root."""
    for label, repo_dir in (("outer hub repo", outer_dir), ("toolkit\\", toolkit_dir)):
        status = _origin_status(repo_dir)
        if status is None:
            continue
        if status:
            print(f"[ORIGIN-OK] {label} ({repo_dir}) has an 'origin' remote configured.")
        else:
            print(f"[ORIGIN-MISSING] {label} ({repo_dir}) has no 'origin' remote - likely a prior "
                  "\"uninstall\" on this exact clone. Ask the "
                  "user for this repo's remote URL, then run `--reattach-origin --git-remote-url "
                  f"<url>` from inside {repo_dir}.")
    note_path = outer_dir / 'TOWER_CRANE_UNINSTALLED.md'
    if note_path.exists():
        print(f"[UNINSTALL-NOTE] {note_path} is present (left by a prior uninstall) - stale now "
              "that this machine is being set up again. Run --clear-uninstall-note from the outer "
              "root once any reattachment above is done.")


def cmd_detect(cwd):
    missing_here = has_toolkit_signature(cwd)
    toolkit_sub = cwd / 'toolkit'
    missing_sub = has_toolkit_signature(toolkit_sub) if toolkit_sub.is_dir() else TOOLKIT_SIGNATURE

    if not missing_here:
        # cwd itself is a toolkit clone. Nested if the parent already looks like an outer hub;
        # otherwise flat, needing --nest.
        parent_found = has_outer_signature(cwd.parent)
        if parent_found:
            print(f"[NESTED] cwd ({cwd}) is a toolkit\\ checkout; its parent ({cwd.parent}) already "
                  f"has outer-hub markers: {', '.join(parent_found)}. Proceed to setup_machine.md "
                  "Step 1 once anything reported below is resolved.")
            _report_origin_and_note(cwd.parent, cwd)
        else:
            print(f"[FLAT] cwd ({cwd}) IS the toolkit content itself (all of "
                  f"{', '.join(TOOLKIT_SIGNATURE)} present directly here), with no outer wrapper "
                  "around it. Run --nest next.")
        return

    if not missing_sub:
        # cwd/toolkit is a toolkit clone - cwd itself is the outer root, already correctly nested.
        print(f"[NESTED] cwd ({cwd}) is the outer hub root; `toolkit\\` subfolder found and looks "
              "like a real toolkit checkout. Proceed to setup_machine.md Step 1 once anything "
              "reported below is resolved.")
        _report_origin_and_note(cwd, toolkit_sub)
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


def cmd_reattach_origin(cwd, git_remote_url):
    """--reattach-origin --git-remote-url URL: restores a removed 'origin' remote on an
    already-nested, already-historied repo. Unlike cmd_attach_existing, never runs
    `git init`/`checkout -b` - local main and its history are untouched, just `remote add` +
    `fetch` + restoring the upstream-tracking relationship. Never merges or resets - any real
    divergence from being disconnected is left for the ordinary `update`/`checkpoint` flow to
    surface."""
    if not git_remote_url:
        print("[ABORT] --reattach-origin requires --git-remote-url.")
        sys.exit(1)
    if not (cwd / '.git').exists():
        print(f"[ABORT] {cwd} is not a git repo - nothing to reattach.")
        sys.exit(1)
    if 'origin' in _git(cwd, ['remote']).stdout.split():
        print(f"[ABORT] {cwd} already has an 'origin' remote - nothing to do. Re-run --detect if "
              "this is unexpected.")
        sys.exit(1)

    remote = _git(cwd, ['remote', 'add', 'origin', git_remote_url])
    if remote.returncode != 0:
        print(f"[ABORT] could not add remote: {remote.stderr.strip()}")
        sys.exit(1)
    print(f"[REMOTE] origin -> {git_remote_url}")

    fetch = _git(cwd, ['fetch', 'origin'])
    if fetch.returncode != 0:
        print(f"[WARN] fetch failed: {fetch.stderr.strip()} - remote added but not fetched; retry "
              "`git fetch origin` by hand, or run `update`/`checkpoint` later, which will surface "
              "the same problem.")
        return
    print("[FETCHED] origin.")

    branch = _git(cwd, ['rev-parse', '--abbrev-ref', 'HEAD']).stdout.strip()
    if branch and branch != 'HEAD':
        track = _git(cwd, ['branch', f'--set-upstream-to=origin/{branch}', branch])
        if track.returncode == 0:
            print(f"[TRACKING] {branch} -> origin/{branch}")
        else:
            print(f"[WARN] could not set upstream tracking: {track.stderr.strip()} - `origin/"
                  f"{branch}` may not exist yet on the remote, or the local branch name differs. "
                  "Resolve by hand.")
    print(f"[REATTACHED] {cwd} is connected to origin again. Local history untouched - if it has "
          "diverged from origin while disconnected, the ordinary `update`/`checkpoint` flow will "
          "surface that normally.")


def cmd_clear_uninstall_note(cwd):
    """--clear-uninstall-note: deletes a stale TOWER_CRANE_UNINSTALLED.md from cwd (the outer hub
    root) if present. No-op, not an error, if the file isn't there."""
    note_path = cwd / 'TOWER_CRANE_UNINSTALLED.md'
    if note_path.exists():
        note_path.unlink()
        print(f"[REMOVED] {note_path} (stale now that this machine is set up again).")
    else:
        print(f"[OK] no {note_path.name} found in {cwd} - nothing to clear.")


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


def cmd_write_bash_allowlist(cwd):
    """--write-bash-allowlist: merges the hub-scope Bash/PowerShell rules from
    templates\\bash_allowlist.json into this machine's own, gitignored .claude\\settings.local.json.
    Self-locating like every other command here (ignores cwd); safe to re-run any time
    (append-if-missing)."""
    toolkit_root = Path(__file__).resolve().parent.parent
    project_root = toolkit_root.parent
    cfg = get_shared_config(toolkit_root)
    settings_path = project_root / '.claude' / 'settings.local.json'
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings = {}
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text(encoding='utf-8')) or {}
        except json.JSONDecodeError:
            settings = {}
    merge_bash_allowlist(settings, 'hub', cfg)
    settings_path.write_text(json.dumps(settings, indent=2), encoding='utf-8', newline='\n')
    print(f"[OK] hub Bash/PowerShell allowlist merged into {settings_path}")


def main():
    parser = argparse.ArgumentParser(
        description="templates\\setup_machine.md's Step 0 pre-flight sequence, mechanized."
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
    group.add_argument('--write-bash-allowlist', action='store_true',
                        help="Merge the hub-scope Bash allowlist into this machine's own "
                             "settings.local.json.")
    group.add_argument('--reattach-origin', action='store_true',
                        help="Restore a removed 'origin' remote on an already-nested repo.")
    group.add_argument('--clear-uninstall-note', action='store_true',
                        help="Delete a stale TOWER_CRANE_UNINSTALLED.md from the outer root, if "
                             "present.")
    parser.add_argument('--git-remote-url', default=None,
                         help="Used by --new-outer (optional), --attach-existing (required), and "
                              "--reattach-origin (required).")
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
    elif args.write_bash_allowlist:
        cmd_write_bash_allowlist(cwd)
    elif args.reattach_origin:
        cmd_reattach_origin(cwd, args.git_remote_url)
    elif args.clear_uninstall_note:
        cmd_clear_uninstall_note(cwd)


if __name__ == '__main__':
    main()
