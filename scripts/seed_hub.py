#!/usr/bin/env python3
"""
seed_hub.py - generate a clean, distributable copy of this tower_crane hub, the Replicate
GENERATOR (design\\portability.md, "Replicate distribution").

Produces a fresh, independent hub from the LIVE repo by ALLOWLIST copy: only the known-good KEEP
set is copied into a new output directory; everything else - the source hub's instance state
(design\\, consumers\\, change_requests\\, both project_progress*.md) and any file NOT on the
allowlist (a new sensitive doc added later, the gitignored config.local.json) - is excluded BY
DEFAULT. Allowlist-copy is the security upgrade over the in-place courier's denylist-delete:
anything new is left behind unless it is deliberately on the KEEP list.

This is the single audited "workshop -> storefront" bridge. It NEVER mutates the live repo and
NEVER ships live git history (git history is permanent, so it can never be handed out). The output
is a clone-and-go hub with no instance state to strip - the recipient only ever runs SETUP.md
(git init + fill config.local.json). Use it two ways:
  --out <path>          hand the folder directly to someone (ephemeral, nothing committed).
  --out <path> --zip     also produce <path>.zip for a versioned download / release asset.

Publishing a versioned release is a SEPARATE, manual step (not this script's job): commit the
output into the separate PUBLIC storefront repo and `gh release create <ver>` + attach the zip.
Keeping generate and publish separate is deliberate - the public repo's own clean linear history is
the version record (git tags = versions).

OS-reach Tier 2 port of seed_hub.ps1 (design\\portability.md, "OS-reach Tier 2: full
cross-platform design"). Logic is a direct translation - see that doc's Build order for the
parity-check approach used to verify ports in this series.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

SHARED_ROOT = Path(__file__).resolve().parent.parent

# --- the ALLOWLIST (the whole security model lives here) ---------------------------------------
# KEEP directories: their tracked subtree ships verbatim (the reusable pattern). A NEW top-level
# folder is NOT here, so it is excluded by default - that is the allowlist's point.
KEEP_DIRS = ['hooks', 'agents', 'scripts', 'tests', 'templates']
# KEEP root files: copied verbatim.
KEEP_ROOT_FILES = ['AGENTS.md', 'config.example.json', '.gitignore', 'CHANGELOG.md']
# REGENERATE root files: written fresh below (never copied from the source - they carry instance
# narrative). Listed here only so the summary can report them as "regenerated, not copied".
REGEN_ROOT_FILES = ['README.md', 'MENU.md', 'project_progress.md']

TEXT_EXT = ('.md', '.json', '.ps1', '.py', '.txt', '.yaml', '.yml', '.tmpl')


def write_utf8(path, content):
    # Mirrors Write-Utf8NoBom: creates the parent dir if missing. Python's utf-8 encoding never
    # writes a BOM (unlike PS 5.1's -Encoding utf8); newline='\n' keeps embedded '\n' as LF
    # instead of Windows-translating it to CRLF on write.
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8', newline='\n')


def main():
    parser = argparse.ArgumentParser(
        description="Generate a clean, distributable copy of this tower_crane hub (Replicate generator)."
    )
    parser.add_argument('--out', required=True, help="Destination directory for the generated hub. Must be OUTSIDE this repo.")
    parser.add_argument('--zip', action='store_true', help="Also produce a sibling <out>.zip of the generated hub.")
    parser.add_argument('--version', default=None, help="Optional version label (e.g. 1.0.0), stamped into SETUP.md and used in the zip filename.")
    parser.add_argument('--force', action='store_true', help="Overwrite / clear a non-empty --out directory first.")
    args = parser.parse_args()

    # --- safety gate ----------------------------------------------------------------------------
    try:
        git_top = subprocess.run(
            ['git', '-C', str(SHARED_ROOT), 'rev-parse', '--show-toplevel'],
            capture_output=True, text=True
        )
        git_top = git_top.stdout.strip() if git_top.returncode == 0 else ''
    except FileNotFoundError:
        git_top = ''
    if not git_top:
        raise RuntimeError(f"Source ({SHARED_ROOT}) is not a git repository - the generator copies tracked files, so it must run inside the live repo.")

    out_full = os.path.abspath(args.out)
    src_full = str(SHARED_ROOT.resolve()).rstrip('\\')
    out_cmp = out_full.rstrip('\\').lower()
    src_cmp = src_full.lower()
    if out_cmp == src_cmp:
        raise RuntimeError("--out must not be the source repo itself.")
    if out_cmp.startswith(src_cmp + '\\'):
        raise RuntimeError(f"--out ({out_full}) is inside the source repo. Choose a destination OUTSIDE {src_full}.")

    out_full_path = Path(out_full)
    if out_full_path.exists():
        existing = list(out_full_path.iterdir())
        if existing and not args.force:
            raise RuntimeError(f"--out ({out_full}) exists and is not empty. Pass --force to clear it.")
        if existing and args.force:
            for child in existing:
                if child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink()
    out_full_path.mkdir(parents=True, exist_ok=True)

    print("Generating clean hub")
    print(f"  from: {src_full}")
    print(f"  to:   {out_full}")
    print()

    # --- 1. allowlist copy of tracked files ------------------------------------------------------
    # `git ls-files` yields ONLY tracked files -> gitignored cruft (config.local.json, _archive\,
    # temp logs) is never even a candidate. We then keep only files whose top-level segment is on
    # the allowlist. New tracked files UNDER a KEEP dir (e.g. a new template) do ship - correct,
    # they are part of the pattern. Anything at root not explicitly kept, and any non-KEEP dir
    # (design\, consumers\, change_requests\), is excluded.
    tracked_raw = subprocess.run(
        ['git', '-C', str(SHARED_ROOT), 'ls-files'],
        capture_output=True, text=True, check=True
    ).stdout
    tracked = [line.strip() for line in tracked_raw.split('\n') if line.strip()]
    copied = 0
    excluded_top = set()
    for rel in tracked:
        seg = rel.split('/')[0]
        is_dir = '/' in rel
        keep = (seg in KEEP_DIRS) if is_dir else (seg in KEEP_ROOT_FILES)
        if not keep:
            excluded_top.add(f"{seg}/" if is_dir else seg)
            continue
        src_path = SHARED_ROOT / rel
        dst_path = out_full_path / rel
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_path, dst_path)
        copied += 1
    print(f"Copied {copied} tracked file(s) from the KEEP allowlist.")
    if excluded_top:
        print("Excluded by allowlist (instance state / not on KEEP list):")
        for e in sorted(excluded_top):
            print(f"  - {e}")

    # --- 2. empty structural dirs (a fresh hub starts with no consumers / no inbox) --------------
    for d in ('consumers', 'change_requests', 'agents'):
        p = out_full_path / d
        p.mkdir(parents=True, exist_ok=True)
        write_utf8(p / '.gitkeep', '')

    # --- 3. gather what to scrub (source consumers + this machine's config values) --------------
    # Enumerate the LIVE consumers so we don't hardcode a slug, and read the per-machine config
    # values, so the global scrub (section 8) can strip every trace of the source project + author
    # machine from the copied prose - the generator ships CLEAN, not "clean if you remember to
    # hand-edit."
    src_consumers = []
    consumers_dir = SHARED_ROOT / 'consumers'
    if consumers_dir.is_dir():
        for f in sorted(consumers_dir.glob('*.md')):
            slug = f.stem
            name = None
            raw = f.read_text(encoding='utf-8')
            for line in raw.splitlines():
                m = re.match(r'^\s*name:\s*(.+?)\s*$', line)
                if m:
                    name = m.group(1).strip()
                    break
            src_consumers.append({'slug': slug, 'name': name})
    consumer_names = [c['name'] for c in src_consumers if c['name']]

    # Neutral placeholder swapped in wherever the author's real machine path leaks into a copied
    # file. There's no install-convention location to point at any more - shared_root/import_base
    # are always computed live (config_lib.py), so a recipient can place this hub anywhere under
    # their home directory. Kept in backslash form to match the templates' Windows-path prose style.
    CONVENTION_ROOT = r'<wherever you place this folder>'

    # Per-machine config values to strip if they appear in any copied file (the templates
    # currently carry the author's absolute shared_root, which leaks the OS username). identity/
    # host values too, defensively. shared_root comes from this script's own live-computed
    # SHARED_ROOT (never config.local.json's marker, which may be stale) - it's always the real
    # answer regardless of whether relocate.py has been run since a move.
    machine_path = str(SHARED_ROOT.resolve()).rstrip('\\/')
    identity_vals = []
    local_cfg = SHARED_ROOT / 'config.local.json'
    if local_cfg.exists():
        try:
            lc = json.loads(local_cfg.read_text(encoding='utf-8'))
            identity = lc.get('identity') or {}
            for v in (lc.get('host_id'), identity.get('git_user_name'), identity.get('git_user_email'), identity.get('git_remote')):
                if v and str(v).strip() and not str(v).startswith('<'):
                    identity_vals.append(str(v))
        except (json.JSONDecodeError, AttributeError):
            pass

    def invoke_scrub(text):
        # Strip every source-hub / author-machine trace from a text blob, replacing with neutral
        # placeholders / the install convention. Idempotent; safe on already-clean text.
        # NOTE: PowerShell's `-replace` operator is case-INSENSITIVE by default, so every
        # replacement below except the consumer-name swap (a plain, case-sensitive .Replace() in
        # the original) uses re.IGNORECASE to match that behavior.
        # repl passed as a lambda (not a raw string) throughout: re.sub treats backslashes in a
        # string replacement as backreference/escape syntax, and both CONVENTION_ROOT and the
        # "consumers\<slug>.md" replacement contain literal backslashes.
        if machine_path:
            text = re.sub(re.escape(machine_path), lambda m: CONVENTION_ROOT, text, flags=re.IGNORECASE)
            text = re.sub(re.escape(machine_path.replace('\\', '/')), lambda m: CONVENTION_ROOT, text, flags=re.IGNORECASE)
        for iv in identity_vals:
            text = re.sub(re.escape(iv), lambda m: '<redacted>', text, flags=re.IGNORECASE)
        for c in src_consumers:
            text = re.sub(re.escape(f"consumers\\{c['slug']}.md"), lambda m: 'consumers\\<slug>.md', text, flags=re.IGNORECASE)
            text = re.sub(r'\b' + re.escape(c['slug']) + r'\b', lambda m: '<slug>', text, flags=re.IGNORECASE)
            if c['name']:
                text = text.replace(c['name'], '<Project Name>')
        return text

    # --- 4. regenerate MENU.md (kept, but every "In use by" cell reset to none) ------------------
    # Structural blanking only here (detecting a consumer-name cell needs the name intact); the
    # global scrub in section 8 then neutralizes any residual name text.
    menu_src = SHARED_ROOT / 'MENU.md'
    menu_lines = menu_src.read_text(encoding='utf-8').splitlines()
    new_menu_lines = []
    for line in menu_lines:
        if re.match(r'^\s*\|.*\|\s*$', line) and not re.match(r'^\s*\|[\s:|-]+\|\s*$', line):
            cells = line.strip().strip('|').split('|')
            last = cells[-1].strip()
            if any(last.lower() == n.lower() for n in consumer_names):
                cells[-1] = ' - '
                line = '|' + '|'.join(cells) + '|'
        new_menu_lines.append(line)
    write_utf8(out_full_path / 'MENU.md', '\n'.join(new_menu_lines) + '\n')

    # --- 5. regenerate README.md (clean skeleton, no source narrative / design pointers) ---------
    readme = r"""# Tower Crane

A shared library of reusable Claude Code **tools** (hooks, subagents, scripts) *and* shared
**workflow conventions** that other projects opt into. It is not a product or a client
deliverable - it is the single source of truth those projects point at.

This hub was generated from the tower_crane pattern and starts **empty** - no consumers yet. See
`SETUP.md` for the one-time setup on this machine before anything below will work.

## Why this exists

**The real driver is token economy, not tidiness.** Every Claude Code session pays for whatever's
loaded into context, and `CLAUDE.md` is loaded on *every single session* - so a `CLAUDE.md` that
accumulates history, workflow instructions, and completed-work recaps burns real tokens on every
future session, forever, whether or not that content is still relevant. `README.md`, by contrast,
is human-facing documentation Claude Code never auto-loads - so it's the right place for anything
long-form a human might read once, while `CLAUDE.md` stays terse and purely operational.

That split is the seed of everything else here:
- **`project_progress.md`'s checkpoint/resume/archive discipline** keeps the same problem from
  recurring one level down: Current Status and Next Up describe only the present, not a growing
  "done" list; completed work lives exactly once, in a dated Work Log entry; and when that log
  grows long, "archive" moves settled entries out to `project_progress_archive.md`, which is
  never read back into context unless something specifically calls for old history.
- **The checkpoint process itself** (update the doc, commit, push) is what makes this reliably
  repeatable instead of ad hoc - and, as a side effect, means the project is never more than one
  checkpoint away from being safely in git instead of sitting unsaved on a local disk.
- **Referenced-not-copied sharing (float-on-HEAD)** is the same economy applied across *projects*
  instead of within one: hand-copying a good convention or hook into every project's `CLAUDE.md`
  would both re-bloat each project's context and drift the moment one copy gets fixed and the
  others don't. Referencing it once, here, keeps every consuming project's own `CLAUDE.md` as
  short as if it had never needed the convention at all.

**The governing idea** that makes referencing work in practice: *an improvement discovered in one
project, once ratified here, benefits every project.* Fix a shared hook or refine a shared
workflow rule once, and every consuming project picks it up the next time it runs - no
copy-paste, no drift.

Time saved and history preserved - nothing lost to an unmanaged folder, everything backed up in
git at each checkpoint - are real benefits, but they're downstream of the token-economy design,
not the reason for it.

**What happens without this.** A person can start Claude Code in any folder with zero setup - but
left alone, that folder's `CLAUDE.md` tends to grow without bound as instructions and history
pile up in the one file read every session, nothing gets pushed to git until someone remembers
to, and there's no discipline for what belongs in context versus what a human can read on their
own later. This workflow is what fixes that, and it works the same way whether you're starting a
project from scratch with it already in place, or retrofitting it onto a project that's already
in that ballooning state (`templates\register.md` - see Track 1's "Getting set up," or Track 2
§2.2 if you're the one doing it for someone else).

---

## Which of these is you?

1. **You're working in a project that already uses this hub, or is about to.**
   -> [Track 1 - Consumer / Project User](#track-1--consumer--project-user)
2. **You're running this hub, or just downloaded/generated it and want to get it going.**
   -> [Track 2 - Hub Operator](#track-2--hub-operator)
3. **You're changing how this hub itself works, not just using it.**
   -> [Track 3 - Hub Architect](#track-3--hub-architect)

Most first-time readers are #2.

---

## Track 1 - Consumer / Project User

Your project's `CLAUDE.md` has `@import` lines pointing at this hub, or someone just handed you
this hub and said your project should use it. (Nobody's wired this up for you yet? See "Getting
set up" below - it's minimal.)

### How this changes day-to-day use of Claude Code
The habits that matter most, roughly in order of how often you'll reach for them:

1. **"checkpoint"** - say it any time you want to save progress. Your agent updates
   `project_progress.md` (refreshes Current Status / Next Up, moves resolved Decisions, prepends
   one dated Work Log entry), then commits and pushes. Nothing sits unsaved on local disk for
   long.
2. **"resume"** - say it at the start of a session. Your agent pulls latest and reads only
   Current Status, Next Up, and the most recent Work Log entry - not the whole project history -
   then tells you where things stand in a couple of lines.
3. **`project_progress.md`** - the one file that carries state between sessions. Current Status
   and Next Up describe only the present; anything finished lives exactly once, in its dated Work
   Log entry, never restated at the top. That's what keeps the file cheap to read every session
   instead of growing without bound.
4. **"archive"** - user-initiated, any time the Work Log has grown long. Moves settled entries out
   to `project_progress_archive.md`, which is never read back into context unless something
   specifically calls for old history.
5. **`README.md` vs `CLAUDE.md`** - `CLAUDE.md` is loaded every session, so it stays terse and
   purely operational; anything long-form a human might want to read once (rationale, onboarding,
   history) belongs in `README.md`, which Claude Code never auto-loads.

This is the actual substance of what this hub gives a project - the token-economy discipline
covered above ("Why this exists"), ready to use instead of reinvented (or skipped) per project.
Full mechanics: `templates\continuity.md`.

### What opting in means
A project that opts in is a **consumer**. Nothing here runs automatically *to* your project -
you opted in by adding reference lines (a hook command in `.claude\settings.json`, `@import`
lines in `CLAUDE.md`), and you can opt out any time by deleting them. Everything you get is
**referenced, never copied**: your project holds a pointer to the shared file, not a duplicate.
**If your project and this hub sit on the same machine, a fix reaches you the moment it's
committed - no update to pull.** If the hub lives on a *different* machine (Federate, 2.4), the
pointer only resolves to the current version once *your own machine's clone* of the hub is up to
date - and nothing pulls that clone for you automatically today; your project's own `resume` only
pulls your project's own repo. Run `git pull` yourself inside this hub's folder to pick up a fix
(a `resume`-time prompt to do this is planned, not yet built).

### Getting set up
Minimal version - full detail (and the hub-operator's-eye view) lives in
[Track 2](#track-2--hub-operator) if you ever need it, but you shouldn't have to read it just to
use this as a consumer:
- **Someone already set this up for you** (they ran the scaffolder, or handed you a project whose
  `CLAUDE.md` already has `@import` lines) - you're done, nothing else to do.
- **You're wiring your own existing project into this hub yourself** - copy
  `templates\register.md` from this hub into your project's root, open your project in Claude
  Code, and say *"read register.md and follow it."* It swaps any pasted workflow prose for
  `@import` lines and writes a registration request into the hub's `change_requests\` folder -
  **you still need to `git add`/`commit`/`push` that file yourself** from inside the hub clone;
  `register.md` doesn't do this for you yet. Once it's pushed, someone with hub access turns it
  into a registry entry the next time they work in that repo. Nothing else from Track 2 is
  required to do this part yourself.

### What else you'll see, day to day
- **Filing a bug or improvement in a shared tool** - you don't fix it yourself. Drop a ticket in
  this hub's `change_requests\` folder per `templates\filing.md` (already imported into your
  `CLAUDE.md` if you're set up correctly), **then `git add`/`commit`/`push` it yourself** from
  inside the hub clone - filing.md doesn't yet prompt for that push, and a ticket sitting
  uncommitted on your own disk is invisible to the hub until you do.
- **Receiving guidance from the hub** - if this hub's checker finds your project has drifted, or
  the hub operator broadcasts a one-off notice, you'll find a `COMPLIANCE_GUIDANCE.md` file
  dropped in your project's root. Your own agent surfaces it at session start; see
  `templates\compliance.md` for what to do with it. It never edits your files directly - you (or
  your agent, with your OK) apply the change.

That's the whole of what you need from this side. Everything else in this README is about
*running* the hub, not using it from inside a consumer project.

---

## Track 2 - Hub Operator

You're running this hub - or getting it running for the first time, including if you just
downloaded or generated it.

### 2.1 Get this hub running for the first time
You already have the folder - the only question is whether it's ready to use. Follow `SETUP.md`
in this hub's root: it confirms this folder sits somewhere under your home directory (the one
real constraint - Claude Code's `@import` only resolves home-relative `~/...` paths, and
`shared_root`/`import_base` compute themselves automatically from wherever it actually is, so
there's nothing to type in), points git at a repo you own, and walks you through
`templates\setup_machine.md` to fill `config.local.json`.

**If this folder ever moves or gets renamed later:** the next script you run notices on its own
and prints a `[NOTICE]` explaining what changed. Nothing is broken - the location marker
self-corrects automatically - but every already-onboarded consumer still has the OLD path baked
into its hook command / `@import` lines. When you see that notice, run `scripts\relocate.py` to
bring them back in sync.

Maintainer tooling (`relocate.py`, `check_tower_crane.py`, the scaffolder, `seed_hub.py`,
`publish_release.py`) is cross-platform Python. Run each with whichever Python 3 launcher
`setup_machine.md` found on this machine (`python` on Windows, typically `python3` on
macOS/Linux).

### 2.2 Onboard a project as a consumer

**Your own project (new or existing):**

*A brand-new project* -> run the scaffolder in this hub:
```
scripts\new_consumer.py --target-path C:\Users\you\Documents\MyNewProject --project-name "My New Project"
```
It creates *all* of the consumer's files in one shot - `.claude\settings.json` (opt-in hooks),
`CLAUDE.md` (with `@import` lines), a skeleton `project_progress.md`, and a one-time
`FIRST_RUN.md` checklist - plus the registry entry here. By default it opts into the
`consistency_check` hook and imports the `filing` + `compliance` + `continuity` workflow pieces.
Useful flags: `--no-continuity` (skip that piece), `--tools` with no values (no hooks), `--force`
(overwrite). The new project's first session then runs `FIRST_RUN.md`: `git init`, **accept the
one-time import dialog** (declining it disables `@import` permanently), and fill in the project
overview.

*An existing, hand-built project* -> copy `templates\register.md` into that project's root, open
it in Claude Code, and say *"read register.md and follow it."* Its agent swaps any pasted
workflow prose for `@import` lines and writes a registration request into `change_requests\` -
**that project then needs to `git add`/`commit`/`push` the request itself** (register.md doesn't
automate this push yet); only once it lands on this hub's GitHub remote does your next session
here turn it into a registry entry. This is the migration path - it preserves everything
project-specific and only replaces shared, canonical prose.

**Someone else's project:** mechanically identical to the above - you can run `new_consumer.py`
pointed at their path yourself, or just point them at
[Track 1](#track-1--consumer--project-user) and let them self-serve `register.md` from there
(covered under its "Getting set up"). Either way, they're now a **consumer, not an operator** -
Track 1 is the complete set of hub mechanics they need; nothing else here is required.

### 2.3 Run the hub day-to-day

**Health check.** `scripts\check_tower_crane.py` is the platform's health check. It runs two
passes: a **golden regression suite** (exercises each tool against known fixtures so a behavior
regression is caught before it ships to consumers) and a **reference & drift scan** (confirms
every consumer's wiring still resolves - hook paths exist, opt-in snippets still match, every
`@import` a consumer is registered for is still present). Run it before shipping any
behavior-changing fix, and any time you want to confirm the fleet is healthy. Exit code is
non-zero if anything fails.

**The change-request round-trip.** A consumer that finds a bug or thinks of an improvement
*files a request* rather than editing the shared file directly - this keeps each repo's git
history honest (filing and fixing happen in separate repos and sessions).
1. The consumer's agent drops a ticket into `change_requests\` (`Status: OPEN`) - **and the
   consumer must commit and push it themselves** from inside the hub clone; nothing does this for
   them yet. An uncommitted ticket is invisible to the hub.
2. The next time someone works in **this** hub and scans `change_requests\`, it gets picked up,
   validated against *every* consumer (not just the filer), fixed, checked, and the commit SHA
   recorded in the ticket. There's no automatic or scheduled processing yet - this only happens
   when a human is actually working in this hub. The ticket stays **OPEN**.
3. The consumer re-runs its own test and appends "verified PASS." Only then does this hub flip
   the ticket to **DONE**. *DONE means consumer-verified - not merely "fix applied."*

The same machinery governs both executable tools **and** workflow prose. Not every change needs
this ceremony, though - see [Track 3](#track-3--hub-architect) for when a change can propagate
silently.

**Push a fix down to one consumer.** When a consumer has drifted, this hub never reaches in and
edits it. Instead, run the checker with `--write-guidance`: it drops a `COMPLIANCE_GUIDANCE.md`
into that consumer's folder listing the exact deviations and fixes. The consumer's own agent
surfaces that file at session start, summarizes it, asks the human, applies on confirmation, and
deletes it.

**Broadcast a notice to everyone at once.** `scripts\broadcast_guidance.py` pushes one
hand-authored guidance file to the whole registry (or a single consumer via `--consumer`) through
the same `COMPLIANCE_GUIDANCE.md` channel - for a one-off notice that isn't worth promoting into a
permanent imported `templates\` piece.
```
python scripts\broadcast_guidance.py --broadcast <notice.md>              # push to everyone
python scripts\broadcast_guidance.py --broadcast <notice.md> --consumer geo_rank_tracker
python scripts\broadcast_guidance.py --status                             # who still has it pending
```
`--status` is a live re-scan (recomputes from the registry every run) - a consumer's
`## Broadcast` section still present means pending/declined; gone means their agent applied it.

**Turn this hub's own tools on for itself (dogfooding).** This hub is not a registered consumer
of itself by default - none of its own tools run on it unless you turn them on:
```
python scripts\self_hooks.py --list                       # what's available, what's on here
python scripts\self_hooks.py --enable consistency_check    # turn one on
python scripts\self_hooks.py --disable consistency_check   # turn it back off
```
State lives in `.claude\settings.local.json` (gitignored - a fresh hub always starts with nothing
enabled). Check what's on without running anything by opening `.claude\self_hooks_status.md`.

### 2.4 Bring another machine or person onto this hub (Federate)
Access control is **GitHub repo permissions - never a bespoke auth layer**. "Admin" just means
*whoever holds merge/branch-protection rights* on this hub's GitHub remote; everyone else is a
contributor who files tickets/PRs the same way any consumer project already does. Every clone -
yours or theirs - is an equal peer; GitHub is the master copy, not any one machine.

1. **Grant them GitHub access** - collaborator or org team member. In practice, give **write**
   access: filing a ticket currently means pushing a file to this hub yourself (see 2.3), so
   read-only access isn't enough to actually participate today, even though filing conceptually
   shouldn't require it. A true read-only filing path (fork+PR) isn't built.
2. **They clone it wherever they want** (anywhere under their own home directory - see 2.1) and
   run [2.1](#21-get-this-hub-running-for-the-first-time) on their own machine.
3. **`gh auth login` + `git config user.*`** on their machine - ambient auth, never stored in a
   tracked file.
4. **The registry stays one shared union** - every consumer project from every person lives in
   the same `consumers\` folder; `owner:` is attribution only, never a visibility boundary. If
   you need to actually hide one person's projects, that's Replicate (2.5), not a registry
   setting.
5. **Round-trip log lines name the person**, not just the project, once there's more than one
   contributor.
6. **"Never edit a shared file directly" (`filing.md`) is a written convention, not a
   GitHub-enforced rule** - anyone with write access can technically push straight to
   `hooks\`/`scripts\`/`templates\`. Branch protection to actually block that is a one-time
   GitHub repo setting you can add yourself; this hub's own scripts don't configure it.

### 2.5 Stand up a separate, independent hub (Replicate)
To hand someone a **separate** hub - its own GitHub repo, its own empty registry, none of this
hub's state - run the generator:
```
scripts\seed_hub.py --out <path>                          # clean copy to hand off directly
scripts\seed_hub.py --out <path> --version 1.0.0 --zip    # + a versioned release zip
```
It **allowlist-copies** only the reusable pattern into a fresh directory, so this hub's instance
state (`design\`, `consumers\`, `change_requests\`, progress docs) and anything new not on the
allowlist are excluded by default. It regenerates a skeleton `README.md`/`project_progress.md`,
writes a recipient `SETUP.md`, scrubs the source consumer names + your machine path from the
copied prose, and runs a leak scan.

**Before you hand the output to anyone: read the leak-scan output.** It's the one safety check
standing between "clean hub" and "a copy that leaks your consumer names or machine path" - don't
skip past it just because the command exited 0.

The in-place courier `templates\bootstrap_hub.md` is the ad-hoc alternative if someone already
cloned the whole repo and wants to convert it in place - it's one-way and destructive, meant for
a fresh copy, never a live hub.

### 2.6 Publish a versioned public release
`scripts\publish_release.py` cuts a version and puts it on GitHub, at a **separate public
storefront repo**. The one deliberately manual step is writing the release notes; everything else
is automatic:

| Step | Do this | Detail |
|---|---|---|
| 1 | Write a `## [X.Y.Z] - YYYY-MM-DD` section in `CHANGELOG.md` | Plain language - the audience is often non-technical. |
| 2 | Commit it here | A new file only ships once it's git-tracked. |
| 3 | Run `python scripts\publish_release.py --version X.Y.Z` | Regenerates the hub, syncs it into the persistent local public clone, commits, tags, pushes, and runs `gh release create` with the CHANGELOG section as notes plus a zip. Requires `gh auth login` once on this machine. |
| 4 (optional) | Fix a past release's notes | Edit `CHANGELOG.md`, then `--sync-notes` - no regenerate/tag/new-release. |

**Deciding when a public repo goes public is a separate, one-time call - not part of this
mechanism.** A repo created via `gh repo create` defaults to whatever visibility you pick there;
nothing about publishing a release changes it after the fact. `gh repo edit <owner>/<repo>
--visibility public` when you're ready. No code change either way.

### 2.7 Add a new shareable tool to the catalog
Full mechanical steps live in `CLAUDE.md` ("Adding a new tool") since that's what your agent
follows - but in short: build and test the tool in whichever project prompted the need, strip
anything project-specific (no hardcoded paths or project names - it must work unmodified from any
future project), drop it in the matching folder (`hooks\`, `agents\`, or `scripts\`), and add a
row + opt-in snippet to `MENU.md`. If it's an automatic hook, it must exit code 2 with the failure
report on stderr on a FAIL - see [Track 3](#track-3--hub-architect) for why. Commit and push like
any other change.

---

## Track 3 - Hub Architect

You're extending this hub's own protocol or mechanics - not just using it.

### The mental model
Two kinds of things are shared, and they reach a consumer two different ways:

| Shared thing | Example | How a consumer gets it |
|---|---|---|
| **Tools** - executable | `hooks\consistency_check.py` (a Python static-analysis hook) | The consumer's `.claude\settings.json` points at the shared file by a command generated per machine from `config.local.json`. |
| **Workflow** - prose conventions | how to file a bug, checkpoint/resume, receive compliance guidance | The consumer's `CLAUDE.md` `@import`s the shared prose by path. |

Both are **referenced, never copied** ("float-on-HEAD"). A project that has opted in is a
**consumer**; the registry (`consumers\`) is the source of truth for who has opted into what.

It is also a **cooperative convention system, not a sandbox.** A consumer can always opt out of
any piece or override a rule locally. Opt-out can't be *prevented*, only *detected* - the checker
flags drift as a tripwire, never a lock.

### Why hooks exit 2, not 1
The hooks in this pattern exist because a human's judgment about what's genuinely necessary is
worth encoding as a script that doesn't drift, doesn't get talked out of itself, and doesn't
forget. That only works if a failing hook actually reaches the agent instead of quietly writing
to a log file nobody's watching. Claude Code only auto-feeds a PostToolUse hook's output back
into the calling agent's context when the hook exits **code 2** on **stderr** - any other
non-zero exit is "non-blocking," shown to the human only. This is the standing contract for any
automatic Claude Code hook in this hub (`CLAUDE.md` "Adding a new tool" step 2a). It doesn't apply
to a manually-invoked maintainer script like `check_tower_crane.py` - its output is already fully
visible to whoever runs it.

### Silent minor-change propagation
Not every shared fix needs the full change-request ceremony. A *minor benevolent* change made
here - a prose or workflow refinement, a strictly-additive guardrail, nothing a consumer must
re-verify or re-wire - is allowed to propagate silently: it reaches consumers on their next
session with no announcement, and the only requirement is that it's logged in this hub's Work
Log. This is safe as long as **one human is the user across every consumer project** - that
human's own memory is the backstop for noticing something changed. Revisit once projects have
separate human owners.

### What actually ships - private vs. public content
| Category | Files | Effect of editing here |
|---|---|---|
| **KEEP** (git-tracked, copied verbatim + scrubbed) | `hooks\`, `agents\`, `scripts\`, `tests\`, `templates\`, `CLAUDE.md`, `config.example.json`, `.gitignore`, `CHANGELOG.md` | Ships in the next generate/release - once committed. |
| **Derived** | `MENU.md` | Catalog rows/opt-in snippets ship through; "In use by" cells are blanked. |
| **Regenerated** (hardcoded inside `scripts\seed_hub.py`'s own script body) | `README.md`, `project_progress.md`, `SETUP.md` | No effect - this hub's own copy of these files is never read by the generator. To change what a hub generated *from this one* has its README say, edit the `readme` string inside `scripts\seed_hub.py` here. |
| **Excluded** | `design\`, `consumers\`, `change_requests\`, `project_progress_archive.md` | Never ships. This is why this file has no `design\*.md` to point you to for deeper rationale: the hub you generated this one from keeps that folder private by design, and every hub generated from *this* one will do the same to yours. |

This file (`README.md`) and `project_progress.md` are safe places for private, internal notes -
they structurally cannot leak into a public release. `CLAUDE.md`, by contrast, *is* a KEEP file,
so keep it to generic process rules only.

> **Never hand-edit files inside a local `*_public` clone used by `publish_release.py`.** It
> fully overwrites its tracked content (preserving `.git`) on every run. To make a change, edit
> the source here per the table above, then re-run `publish_release.py`.

---

## Reference

### Where things live
| Path | What it is |
|---|---|
| `MENU.md` | Catalog of the shareable tools and their opt-in snippets. |
| `consumers\` | The consumer registry - one file per opted-in project. |
| `templates\` | Shared workflow prose (`filing`, `compliance`, `continuity`) + couriers (`register.md`, `bootstrap_hub.md`, `setup_machine.md`) + opt-in JSON under `optins\`. |
| `change_requests\` | The inbox - tickets from consumers and registration requests. |
| `scripts\` | Maintainer tooling - see 2.1-2.7 above for what each one does. |
| `hooks\`, `agents\` | The executable tools themselves. |
| `.claude\settings.local.json`, `.claude\self_hooks_status.md` | This hub's own self-use state - gitignored, per-machine. |
| `CHANGELOG.md` | What's in each public release. |
| `config.example.json` / `config.local.json` | Per-machine config. `.example` committed; `.local` gitignored. |
| `SETUP.md` | One-time per-machine setup for this generated hub - see 2.1. |
| `project_progress.md` | Cross-session working state for this hub. |
| `CLAUDE.md` | The Claude Code agent's per-session operating manual. Not human onboarding - that's this file. |

### Quick-start cheat sheet
| I want to... | Do this |
|---|---|
| Get this hub running | Follow `SETUP.md` - 2.1 |
| Onboard a project | `scripts\new_consumer.py` (new) or `templates\register.md` (existing) - 2.2 |
| Confirm the fleet is healthy | `scripts\check_tower_crane.py` - 2.3 |
| Push a drift fix to one consumer | checker with `--write-guidance` - 2.3 |
| Push a notice to everyone | `scripts\broadcast_guidance.py --broadcast <file>` - 2.3 |
| Turn on this hub's own tools | `scripts\self_hooks.py --enable <tool>` - 2.3 |
| Add another machine/person (Federate) | 2.4 |
| Generate an independent hub (Replicate) | `scripts\seed_hub.py --out <path>` - 2.5 |
| Publish a release | `CHANGELOG.md` entry + `scripts\publish_release.py --version X.Y.Z` - 2.6 |
| Add a new shareable tool | 2.7 |
"""
    write_utf8(out_full_path / 'README.md', readme)

    # --- 6. regenerate project_progress.md (fresh skeleton) ----------------------------------------
    gen_date = date.today().isoformat()
    progress = r"""# Project Progress

## Current Status
Fresh tower_crane hub, generated {{DATE}} from the tower_crane pattern (Replicate generator).
Registry and change-request inbox are empty; no consumers yet. Complete per-machine setup via
`SETUP.md` before onboarding the first consumer.

## Next Up
- [ ] Complete `SETUP.md` (fill `config.local.json`, point git at your own remote, first commit).
- [ ] Onboard the first consumer - a new project via `scripts\new_consumer.py`, or an existing
      one via `templates\register.md`.

## Decisions
| Item | Status | Notes |
|---|---|---|

## Work Log (newest first - say "archive" anytime to move settled entries to project_progress_archive.md)
### {{DATE}} - Hub generated
Stood up this independent tower_crane hub from the pattern via the Replicate generator
(`scripts\seed_hub.py`): it carries the reusable tooling + conventions and none of the source
hub's instance state (registry, ticket history, design docs, progress, git history). Next: complete
`SETUP.md`.
"""
    progress = progress.replace('{{DATE}}', gen_date)
    write_utf8(out_full_path / 'project_progress.md', progress)

    # --- 7. SETUP.md (recipient-side setup; replaces the courier's setup half) ---------------------
    ver_line = f"> **Version {args.version}** (generated {gen_date})." if args.version else f"> Generated {gen_date}."
    setup = r"""# Set up this tower_crane hub

{{VERLINE}}

This is a clean, independent hub generated from the tower_crane pattern. It carries the reusable
tooling and conventions but **none** of the source hub's state - the registry and change-request
inbox start empty. Nothing here needs stripping; you only do one-time setup.

## Prerequisites
- **Python 3** on PATH (the `consistency_check` hook is pure Python - verify: `python --version`,
  or `python3 --version` on macOS/Linux).
- **git** (and optionally the GitHub CLI `gh`) with your own ambient identity - `gh auth login` /
  `git config user.*`. Credentials live in those ambient stores, **never** in a tracked file.

## Steps
1. **Place this hub wherever you want it** - any folder name, any path - as long as it's
   somewhere under your home directory (Claude Code's `@import` only resolves home-relative
   `~/...` paths). `shared_root` and `import_base` in `config.local.json` compute themselves
   automatically from wherever you put it the first time any script here runs - nothing to type
   in by hand. Moving or renaming it again later is safe too: the next script run notices, fixes
   the marker automatically, and tells you to run `scripts\relocate.py` to bring any already-
   onboarded consumers back in sync.
2. **Point git at a repo you own** (this hub ships with no git history):
   ```
   git init
   git branch -M main
   git remote add origin <YOUR empty GitHub repo URL>
   git config user.name  "<you>"      # if not already global
   git config user.email "<you@example.com>"
   ```
3. **Fill `config.local.json`** for this machine: open this hub in Claude Code and say *"read
   `templates\setup_machine.md` and follow it"* - the canonical, ask-don't-assume setup courier. It
   checks live for Python/git/`gh` rather than assuming any of them, and confirms the final
   `config.local.json` with you before writing it. Without Claude Code, that same file is still just
   a plain checklist of CLI commands you can run and read yourself.
   `config.local.json` is gitignored - non-secret pointers only.
4. **Verify the pattern survived.** Run `scripts\check_tower_crane.py` - expect the golden suite
   green and **0 consumers** to validate (a clean, empty hub).
5. **First commit and push:**
   ```
   git add -A
   git commit -m "Bootstrap tower_crane hub"
   git push -u origin main
   ```
6. **Onboard your first consumer** - a new project with
   `scripts\new_consumer.py --target-path <path> --project-name "<Name>"`, or an existing one by
   copying `templates\register.md` into it and saying *"read register.md and follow it."*

You can delete this `SETUP.md` once setup is done - the hub also keeps `templates\bootstrap_hub.md`
for the ad-hoc "clone the whole thing and strip it in place" path.
"""
    setup = setup.replace('{{VERLINE}}', ver_line)
    write_utf8(out_full_path / 'SETUP.md', setup)

    # --- 8. global scrub: strip source-hub / author-machine traces from every copied text file -----
    # The KEEP set ships "verbatim", but verbatim copies of CLAUDE.md, the scripts' help examples,
    # and the templates carry the source consumer name and the author's absolute path. Neutralize
    # them all here so the output is clean BY CONSTRUCTION (the leak scan below is then a check,
    # not the fix).
    scrubbed = 0
    for file in out_full_path.rglob('*'):
        if not file.is_file():
            continue
        if file.suffix in TEXT_EXT or file.name == '.gitignore':
            orig = file.read_text(encoding='utf-8')
            new = invoke_scrub(orig)
            if new != orig:
                write_utf8(file, new)
                scrubbed += 1
    print()
    print(f"Scrubbed source-hub/author traces from {scrubbed} copied file(s).")

    # --- 9. leak scan (belt-and-suspenders over the allowlist + scrub) -----------------------------
    # Scan every generated text file for any residual source-hub identifier. The allowlist excludes
    # instance state and the scrub neutralizes known tokens; this final check catches anything
    # missed (e.g. a NEW sensitive token the scrub doesn't know), so the author never publishes a
    # leak unknowingly.
    needles = []
    for c in src_consumers:
        needles.append(c['slug'])
        if c['name']:
            needles.append(c['name'])
    if machine_path:
        needles.append(machine_path)
    needles.extend(identity_vals)
    needles = sorted({n for n in needles if n and len(n.strip()) >= 3})
    leaks = []
    if needles:
        for file in out_full_path.rglob('*'):
            if not file.is_file():
                continue
            if file.suffix in TEXT_EXT or file.name == '.gitignore':
                content = file.read_text(encoding='utf-8')
                content_lower = content.lower()
                for n in needles:
                    if n.lower() in content_lower:
                        leaks.append((str(file.relative_to(out_full_path)), n))
    if leaks:
        print()
        print("[WARN] Potential source-hub traces remain in the generated output - review before publishing:")
        for rel_file, needle in leaks:
            print(f"  - {rel_file}: '{needle}'")
    else:
        print()
        print("Leak scan clean: no source consumer names / config values found in the output.")

    # --- 10. optional zip -------------------------------------------------------------------------
    if args.zip:
        zip_base = f"tower-crane-{args.version}" if args.version else out_full_path.name
        zip_path = out_full_path.parent / f"{zip_base}.zip"
        if zip_path.exists():
            zip_path.unlink()
        shutil.make_archive(str(zip_path.with_suffix('')), 'zip', root_dir=str(out_full_path))
        print()
        print(f"Zipped: {zip_path}")

    # --- 11. summary --------------------------------------------------------------------------------
    print()
    print(f"Done. Clean hub generated at: {out_full}")
    print(f"  Copied (allowlist):   {copied} tracked file(s) under {', '.join(KEEP_DIRS)} + {', '.join(KEEP_ROOT_FILES)}")
    print(f"  Regenerated:          {', '.join(REGEN_ROOT_FILES)}, SETUP.md; empty consumers\\, change_requests\\, agents\\")
    print("  Live repo untouched.  No git history shipped - recipient runs SETUP.md.")
    print()
    print("Next (manual, separate step): publish to the PUBLIC storefront repo and cut a release -")
    print("  commit this output into that repo, then: gh release create <ver> [attach the zip].")


if __name__ == '__main__':
    main()
