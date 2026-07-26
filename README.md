# Tower Crane

A shared library of reusable Claude Code **tools** (hooks, subagents, scripts) *and* shared
**workflow conventions** that other projects opt into. It is not a product or a client
deliverable — it is the single source of truth those projects point at.

## Why this exists

**The real driver is token economy, not tidiness.** Every Claude Code session pays for whatever's
loaded into context, and `CLAUDE.md` is loaded on *every single session* — so a `CLAUDE.md` that
accumulates history, workflow instructions, and completed-work recaps burns real tokens on every
future session, forever, whether or not that content is still relevant. `README.md`, by contrast,
is human-facing documentation Claude Code never auto-loads — so it's the right place for anything
long-form a human might read once, while `CLAUDE.md` stays terse and purely operational.

That split is the seed of everything else here:
- **`project_progress.md`'s checkpoint/resume/archive discipline** keeps the same problem from
  recurring one level down: Current Status and Next Up describe only the present, not a growing
  "done" list; completed work lives exactly once, in a dated Work Log entry; and when that log
  grows long, "archive" moves settled entries out to `project_progress_archive.md`, which is
  never read back into context unless something specifically calls for old history. Every one of
  these rules exists so a session reads only what it needs to resume work, not the full history
  of everything that's ever happened.
- **The checkpoint process itself** (update the doc, commit, push) is what makes this reliably
  repeatable instead of ad hoc — and, as a side effect, means the project is never more than one
  checkpoint away from being safely in git instead of sitting unsaved on a local disk.
- **Referenced-not-copied sharing (float-on-HEAD)** is the same economy applied across *projects*
  instead of within one: hand-copying a good convention or hook into every project's `CLAUDE.md`
  would both re-bloat each project's context and drift the moment one copy gets fixed and the
  others don't. Referencing it once, here, keeps every consuming project's own `CLAUDE.md` as
  short as if it had never needed the convention at all.

**The governing idea** that makes referencing work in practice: *an improvement discovered in one
project, once ratified here, benefits every project.* Fix a shared hook or refine a shared
workflow rule once, and every consuming project picks it up the next time it runs — no
copy-paste, no drift.

Time saved and history preserved — nothing lost to an unmanaged folder, everything backed up in
git at each checkpoint — are real benefits, but they're downstream of the token-economy design,
not the reason for it.

**What happens without this.** A person can start Claude Code in any folder with zero setup — but
left alone, that folder's `CLAUDE.md` tends to grow without bound as instructions and history
pile up in the one file read every session, nothing gets pushed to git until someone remembers
to, and there's no discipline for what belongs in context versus what a human can read on their
own later. This workflow is what fixes that, and it works the same way whether you're starting a
project from scratch with it already in place, or retrofitting it onto a project that's already
in that ballooning state (`templates\register.md` — see Track 1's "Getting set up," or Track 2
§2.2 if you're the one doing it for someone else).

---

## Which of these is you?

1. **You're working in a project that already uses Tower Crane, or is about to.**
   → [Track 1 — Consumer / Project User](#track-1--consumer--project-user)
2. **You're running a Tower Crane hub, or want to start one** (including: you just downloaded
   this from GitHub).
   → [Track 2 — Hub Operator](#track-2--hub-operator)
3. **You're changing how Tower Crane itself works, not just using it.**
   → [Track 3 — Hub Architect](#track-3--hub-architect)

Most first-time readers are #2.

---

## Track 1 — Consumer / Project User

Your project's `CLAUDE.md` has `@import` lines pointing at this repo, or someone just handed you
this repo and said your project should use it. (Nobody's wired this up for you yet? See "Getting
set up" below — it's minimal.)

### How this changes day-to-day use of Claude Code
The habits that matter most, roughly in order of how often you'll reach for them:

1. **"checkpoint"** — say it any time you want to save progress. Your agent updates
   `project_progress.md` (refreshes Current Status / Next Up, moves resolved Decisions, prepends
   one dated Work Log entry), then commits and pushes. Nothing sits unsaved on local disk for
   long.
2. **"resume"** — say it at the start of a session. Your agent pulls latest and reads only
   Current Status, Next Up, and the most recent Work Log entry — not the whole project history —
   then tells you where things stand in a couple of lines.
3. **`project_progress.md`** — the one file that carries state between sessions. Current Status
   and Next Up describe only the present; anything finished lives exactly once, in its dated Work
   Log entry, never restated at the top. That's what keeps the file cheap to read every session
   instead of growing without bound.
4. **"archive"** — user-initiated, any time the Work Log has grown long. Moves settled entries out
   to `project_progress_archive.md`, which is never read back into context unless something
   specifically calls for old history.
5. **`README.md` vs `CLAUDE.md`** — `CLAUDE.md` is loaded every session, so it stays terse and
   purely operational; anything long-form a human might want to read once (rationale, onboarding,
   history) belongs in `README.md`, which Claude Code never auto-loads.

This is the actual substance of what Tower Crane gives a project — the token-economy discipline
covered above ("Why this exists"), ready to use instead of reinvented (or skipped) per project.
Full mechanics: `templates\continuity.md`.

### What opting in means
A project that opts in is a **consumer**. Nothing here runs automatically *to* your project —
you opted in by adding reference lines (a hook command in `.claude\settings.json`, `@import`
lines in `CLAUDE.md`), and you can opt out any time by deleting them. Everything you get is
**referenced, never copied**: your project holds a pointer to the shared file, not a duplicate.
**If your project and this hub sit on the same machine, a fix reaches you the moment it's
committed — no update to pull.** If the hub lives on a *different* machine (Federate, 2.4), the
pointer only resolves to the current version once *your own machine's clone* of the hub is up to
date — and nothing pulls that clone for you automatically today; your project's own `resume` only
pulls your project's own repo. Run `git pull` yourself inside `~\Documents\Claude\tower_crane\`
to pick up a fix (a `resume`-time prompt to do this is planned, not yet built — see
`design\sync_automation.md`).

### Getting set up
Minimal version — full detail (and the hub-operator's-eye view) lives in
[Track 2](#track-2--hub-operator) if you ever need it, but you shouldn't have to read it just to
use this as a consumer:
- **Someone already set this up for you** (they ran the scaffolder, or handed you a project whose
  `CLAUDE.md` already has `@import` lines) — you're done, nothing else to do.
- **You're wiring your own existing project into someone else's hub yourself** — copy
  `templates\register.md` from that hub into your project's root, open your project in Claude
  Code, and say *"read register.md and follow it."* It swaps any pasted workflow prose for
  `@import` lines and writes a registration request into the hub's `change_requests\` folder —
  **you still need to `git add`/`commit`/`push` that file yourself** from inside the hub clone;
  `register.md` doesn't do this for you yet. Once it's pushed, someone with hub access turns it
  into a registry entry the next time they work in that repo. Nothing else from Track 2 is
  required to do this part yourself.

### What else you'll see, day to day
- **Filing a bug or improvement in a shared tool** — you don't fix it yourself. Drop a ticket in
  this hub's `change_requests\` folder per `templates\filing.md` (already imported into your
  `CLAUDE.md` if you're set up correctly), **then `git add`/`commit`/`push` it yourself** from
  inside the hub clone — filing.md doesn't yet prompt for that push, and a ticket sitting
  uncommitted on your own disk is invisible to the hub until you do.
- **Receiving guidance from the hub** — if this hub's checker finds your project has drifted, or
  the hub operator broadcasts a one-off notice, you'll find a `COMPLIANCE_GUIDANCE.md` file
  dropped in your project's root. Your own agent surfaces it at session start; see
  `templates\compliance.md` for what to do with it. It never edits your files directly — you (or
  your agent, with your OK) apply the change.

That's the whole of what you need from this side. Everything else in this README is about
*running* the hub, not using it from inside a consumer project.

---

## Track 2 — Hub Operator

You're running a Tower Crane hub — or about to start one, including if you just downloaded this
from GitHub and want to set it up as your own.

### 2.1 Start a hub for the first time
The repo carries no machine-specific paths — each clone/download provides its own via a
gitignored config. This is the same first step whether it's your Nth machine on an existing hub
or a hub you just downloaded and are running for the very first time:

1. **Clone or unzip it wherever you want** — any path, any folder name — as long as it ends up
   somewhere under your home directory. That's the one real constraint: consumers' `@import`
   lines only resolve Claude Code's home-relative `~/...` form, so this repo needs to live under
   `~` for that to work; there's no other "correct" location beyond that. `shared_root` /
   `import_base` compute themselves from wherever you actually put it — nothing to type in.
2. **Open it in Claude Code and say "read `templates\setup_machine.md` and follow it."** This is
   the canonical, ask-don't-assume setup courier — it checks live for Python/git/`gh` rather than
   assuming any of them, fills `config.local.json` for this machine, and runs `relocate.py` +
   `check_tower_crane.py` to confirm a clean bill of health. **The only assumed prerequisite is
   Claude Code itself**; without it, the same file is still just a plain checklist of CLI
   commands a human can run and read the output of directly.

**If this folder ever moves or gets renamed later:** the next script you run notices on its own
and prints a `[NOTICE]` explaining what changed. Nothing is broken — the location marker
self-corrects automatically — but every already-onboarded consumer still has the OLD path baked
into its hook command / `@import` lines. When you see that notice, run `scripts\relocate.py` to
bring them back in sync.

Maintainer tooling (`relocate.py`, `check_tower_crane.py`, the scaffolder, `seed_hub.py`,
`publish_release.py`) is cross-platform Python. Run each with whichever Python 3 launcher
`setup_machine.md` found on this machine (`python` on Windows, typically `python3` on
macOS/Linux).

### 2.2 Onboard a project as a consumer

**Your own project (new or existing):**

*A brand-new project* → run the scaffolder in this repo:
```
scripts\new_consumer.py --target-path C:\Users\you\Documents\MyNewProject --project-name "My New Project"
```
It creates *all* of the consumer's files in one shot — `.claude\settings.json` (opt-in hooks),
`CLAUDE.md` (with `@import` lines), a skeleton `project_progress.md`, and a one-time
`FIRST_RUN.md` checklist — plus the registry entry here. By default it opts into the
`consistency_check` hook and imports the `filing` + `compliance` + `continuity` workflow pieces.
Useful flags: `--no-continuity` (skip that piece), `--tools` with no values (no hooks), `--force`
(overwrite). The new project's first session then runs `FIRST_RUN.md`: `git init`, **accept the
one-time import dialog** (declining it disables `@import` permanently), and fill in the project
overview.

*An existing, hand-built project* → copy `templates\register.md` into that project's root, open
it in Claude Code, and say *"read register.md and follow it."* Its agent swaps any pasted
workflow prose for `@import` lines and writes a registration request into `change_requests\` —
**that project then needs to `git add`/`commit`/`push` the request itself** (register.md doesn't
automate this push yet); only once it lands on this repo's GitHub remote does your next session
here turn it into a registry entry. This is the migration path — it preserves everything
project-specific and only replaces shared, canonical prose.

**Someone else's project:** mechanically identical to the above — you can run `new_consumer.py`
pointed at their path yourself, or just point them at
[Track 1](#track-1--consumer--project-user) and let them self-serve `register.md` from there
(covered under its "Getting set up"). Either way, they're now a **consumer, not an operator** —
Track 1 is the complete set of hub mechanics they need; nothing else here is required.

### 2.3 Run the hub day-to-day

**Health check.** `scripts\check_tower_crane.py` is the platform's health check. It runs two
passes: a **golden regression suite** (exercises each tool against known fixtures so a behavior
regression is caught before it ships to consumers) and a **reference & drift scan** (confirms
every consumer's wiring still resolves — hook paths exist, opt-in snippets still match, every
`@import` a consumer is registered for is still present). Run it before shipping any
behavior-changing fix, and any time you want to confirm the fleet is healthy. Exit code is
non-zero if anything fails.

**The change-request round-trip.** A consumer that finds a bug or thinks of an improvement
*files a request* rather than editing the shared file directly — this keeps each repo's git
history honest (filing and fixing happen in separate repos and sessions).
1. The consumer's agent drops a ticket into `change_requests\` (`Status: OPEN`) — **and the
   consumer must commit and push it themselves** from inside the hub clone; nothing does this for
   them yet (see `design\sync_automation.md`). An uncommitted ticket is invisible to the hub.
2. The next time someone works in **this** repo and scans `change_requests\`, it gets picked up,
   validated against *every* consumer (not just the filer), fixed, checked, and the commit SHA
   recorded in the ticket. The ticket stays **OPEN**. If [2.8](#28-turn-on-unattended-ticket-processing-automation)'s
   automation is turned on, this can also happen unattended — a fix arrives as a **PR** instead of
   a direct commit, waiting on a human to review and merge it, rather than waiting on a human to
   open a session here at all. Automation is off by default; without it, processing only happens
   when a human is actually working in this repo.
3. The consumer re-runs its own test and appends "verified PASS." Only then does this repo flip
   the ticket to **DONE**. *DONE means consumer-verified — not merely "fix applied."*

The same machinery governs both executable tools **and** workflow prose. Not every change needs
this ceremony, though — see [Track 3](#track-3--hub-architect) for when a change can propagate
silently.

**Push a fix down to one consumer.** When a consumer has drifted, this repo never reaches in and
edits it. Instead, run the checker with `--write-guidance`: it drops a `COMPLIANCE_GUIDANCE.md`
into that consumer's folder listing the exact deviations and fixes. The consumer's own agent
surfaces that file at session start, summarizes it, asks the human, applies on confirmation, and
deletes it.

**Broadcast a notice to everyone at once.** `scripts\broadcast_guidance.py` pushes one
hand-authored guidance file to the whole registry (or a single consumer via `--consumer`) through
the same `COMPLIANCE_GUIDANCE.md` channel — for a one-off notice that isn't worth promoting into a
permanent imported `templates\` piece.
```
python scripts\broadcast_guidance.py --broadcast <notice.md>              # push to everyone
python scripts\broadcast_guidance.py --broadcast <notice.md> --consumer geo_rank_tracker
python scripts\broadcast_guidance.py --status                             # who still has it pending
```
`--status` is a live re-scan (recomputes from the registry every run) — a consumer's
`## Broadcast` section still present means pending/declined; gone means their agent applied it.

**Turn this hub's own tools on for itself (dogfooding).** Tower Crane is not a registered
consumer of itself by default. `scripts\self_hooks.py` closes that gap, per machine:
```
python scripts\self_hooks.py --list                       # what's available, what's on here
python scripts\self_hooks.py --enable consistency_check    # turn one on
python scripts\self_hooks.py --disable consistency_check   # turn it back off
```
State lives in `.claude\settings.local.json` (gitignored). Check what's on without running
anything by opening `.claude\self_hooks_status.md`.

### 2.4 Bring another machine or person onto this hub (Federate)
Access control is **GitHub repo permissions — never a bespoke auth layer**. "Admin" just means
*whoever holds merge/branch-protection rights* on this repo's GitHub remote; everyone else is a
contributor who files tickets/PRs the same way any consumer project already does. Every clone —
yours or theirs — is an equal peer; GitHub is the master copy, not any one machine.

1. **Grant them GitHub access** — collaborator or org team member. In practice, give **write**
   access: filing a ticket currently means pushing a file to this repo yourself (see 2.3), so
   read-only access isn't enough to actually participate today, even though filing conceptually
   shouldn't require it. A true read-only filing path (fork+PR) isn't built.
2. **They clone it wherever they want** (anywhere under their own home directory — see 2.1) and
   run [2.1](#21-start-a-hub-for-the-first-time) on their own machine.
3. **`gh auth login` + `git config user.*`** on their machine — ambient auth, never stored in a
   tracked file.
4. **The registry stays one shared union** — every consumer project from every person lives in
   the same `consumers\` folder; `owner:` is attribution only, never a visibility boundary. If
   you need to actually hide one person's projects, that's Replicate (2.5), not a registry
   setting.
5. **Round-trip log lines name the person**, not just the project, once there's more than one
   contributor.
6. **"Never edit a shared file directly" (`filing.md`) is a written convention, not a
   GitHub-enforced rule** — anyone with write access can technically push straight to
   `hooks\`/`scripts\`/`templates\`. Branch protection to actually block that is a one-time
   GitHub repo setting you can add yourself; Tower Crane's own scripts don't configure it. This
   matters more, not less, once [2.8](#28-turn-on-unattended-ticket-processing-automation)'s
   automation is on — an unattended PR specifically needs a human's eyes before merge in a way a
   same-session human-authored change never did.

### 2.5 Stand up a separate, independent hub (Replicate)
To hand someone a **separate** hub — its own GitHub repo, its own empty registry, none of this
hub's state — run the generator:
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
standing between "clean hub" and "a copy that leaks your consumer names or machine path" — don't
skip past it just because the command exited 0.

The in-place courier `templates\bootstrap_hub.md` is the ad-hoc alternative if someone already
cloned the whole repo and wants to convert it in place — it's one-way and destructive, meant for
a fresh copy, never a live hub.

### 2.6 Publish a versioned public release
`scripts\publish_release.py` cuts a version and puts it on GitHub, at a **separate public
storefront repo**. The one deliberately manual step is writing the release notes; everything else
is automatic:

| Step | Do this | Detail |
|---|---|---|
| 1 | Write a `## [X.Y.Z] - YYYY-MM-DD` section in `CHANGELOG.md` | Plain language — the audience is often non-technical. |
| 2 | Commit it here | A new file only ships once it's git-tracked. |
| 3 | Run `python scripts\publish_release.py --version X.Y.Z` | Regenerates the hub, syncs it into the persistent local public clone, commits, tags, pushes, and runs `gh release create` with the CHANGELOG section as notes plus a zip. Requires `gh auth login` once on this machine. |
| 4 (optional) | Fix a past release's notes | Edit `CHANGELOG.md`, then `--sync-notes` — no regenerate/tag/new-release. |

**Deciding when the public repo goes public is a separate, one-time call — not part of this
mechanism.** The repo is created private by default; nothing about publishing a release changes
that. When you're ready: `gh repo edit <owner>/<repo> --visibility public`. No code change either
way.

### 2.7 Add a new shareable tool to the catalog
Full mechanical steps live in `CLAUDE.md` ("Adding a new tool") since that's what your agent
follows — but in short: build and test the tool in whichever project prompted the need, strip
anything project-specific (no hardcoded paths or project names — it must work unmodified from any
future project), drop it in the matching folder (`hooks\`, `agents\`, or `scripts\`), and add a
row + opt-in snippet to `MENU.md`. If it's an automatic hook, it must exit code 2 with the failure
report on stderr on a FAIL — see [Track 3](#track-3--hub-architect) for why. Commit and push like
any other change.

### 2.8 Turn on unattended ticket processing (automation)
Piece 3 of `design\sync_automation.md`: an hourly, unattended tick that keeps the hub clone
current, refreshes compliance guidance, and proposes a PR for at most one fix-worthy
`change_requests\` ticket — without anyone opening an interactive Claude Code session in this repo
that day. It **never** merges its own PR and **never** flips a ticket's `Status`; a human still
reviews and merges every actual change, same as always. Off by default
(`automation.enabled: false`). To turn it on: **"read `templates\setup_automation.md` and follow
it."** That runbook checks `gh`/`claude` prerequisites live, walks the `automation` config block,
and gives the OS-scheduler command (Windows Task Scheduler, with cron/launchd documented for
later).

A tighter, event-driven alternative — a GitHub Actions webhook firing on `push`/`pull_request`
against `change_requests\` — remains documented as an **operator-only future upgrade**, not the
default: it needs CI access on the target repo, which a pure consumer of someone else's hub
doesn't have, so it can't be the one mechanism Piece 3 relies on (design\sync_automation.md,
"Trigger: cadence vs. event-driven").

---

## Track 3 — Hub Architect

You're extending Tower Crane's own protocol or mechanics — not just running a hub.

### The mental model
Two kinds of things are shared, and they reach a consumer two different ways:

| Shared thing | Example | How a consumer gets it |
|---|---|---|
| **Tools** — executable | `hooks\consistency_check.py` (a Python static-analysis hook) | The consumer's `.claude\settings.json` points at the shared file by a command generated per machine from `config.local.json`. |
| **Workflow** — prose conventions | how to file a bug, checkpoint/resume, receive compliance guidance | The consumer's `CLAUDE.md` `@import`s the shared prose by path. |

Both are **referenced, never copied** ("float-on-HEAD"). A project that has opted in is a
**consumer**; the registry (`consumers\`) is the source of truth for who has opted into what.

It is also a **cooperative convention system, not a sandbox.** A consumer can always opt out of
any piece or override a rule locally. Opt-out can't be *prevented*, only *detected* — the checker
flags drift as a tripwire, never a lock.

### Why hooks exit 2, not 1
The hooks in this repo exist because a human's judgment about what's genuinely necessary is worth
encoding as a script that doesn't drift, doesn't get talked out of itself, and doesn't forget.
That only works if a failing hook actually reaches the agent instead of quietly writing to a log
file nobody's watching. Claude Code only auto-feeds a PostToolUse hook's output back into the
calling agent's context when the hook exits **code 2** on **stderr** — any other non-zero exit is
"non-blocking," shown to the human only. `hooks\consistency_check.py` originally exited 1 to
stdout only: every FAIL was logging correctly but never reaching the agent that needed to see it
— found 2026-07-23 via this repo's own dogfooding. This is now the standing contract for any
automatic Claude Code hook in this repo (`CLAUDE.md` "Adding a new tool" step 2a). It doesn't
apply to a manually-invoked maintainer script like `check_tower_crane.py` — its output is already
fully visible to whoever runs it.

### Silent minor-change propagation
Not every shared fix needs the full change-request ceremony. A *minor benevolent* change made
here — a prose or workflow refinement, a strictly-additive guardrail, nothing a consumer must
re-verify or re-wire — is allowed to propagate silently: it reaches consumers on their next
session with no announcement, and the only requirement is that it's logged in this repo's Work
Log. This is safe because **one human is the user across every project** — that human's own
memory is the backstop for noticing something changed. Revisit once projects have separate human
owners.

### What actually ships — private vs. public content
| Category | Files | Effect of editing here |
|---|---|---|
| **KEEP** (git-tracked, copied verbatim + scrubbed) | `hooks\`, `agents\`, `scripts\`, `tests\`, `templates\`, `CLAUDE.md`, `config.example.json`, `.gitignore`, `CHANGELOG.md` | Ships in the next generate/release — once committed. |
| **Derived** | `MENU.md` | Catalog rows/opt-in snippets ship through; "In use by" cells are blanked. |
| **Regenerated** (hardcoded inside `scripts\seed_hub.py`'s own script body) | `README.md`, `project_progress.md`, `SETUP.md` | No effect — this repo's own copy is never read. To change what a *new* hub's public README says, edit the `readme` string inside `scripts\seed_hub.py`. |
| **Excluded** | `design\`, `consumers\`, `change_requests\`, `project_progress_archive.md` | Never ships. |

This file (`README.md`) and `project_progress.md` are safe places for private, internal notes —
they structurally cannot leak into a public release. `CLAUDE.md`, by contrast, *is* a KEEP file,
so keep it to generic process rules only.

> **Never hand-edit files inside the local `tower_crane_public` clone.** `publish_release.py`
> fully overwrites its tracked content (preserving `.git`) on every run. To make a change, edit
> the source here per the table above, then re-run `publish_release.py`.

Full design rationale: `design\consumer_platform.md` (the 11 locked decisions behind the
platform), `design\portability.md` (config-driven install, cross-platform runtime, Federate vs.
Replicate), `design\broadcast_guidance.md` (the broadcast primitive's scoping decisions).

---

## Reference

### Where things live
| Path | What it is |
|---|---|
| `MENU.md` | Catalog of the shareable tools and their opt-in snippets. |
| `consumers\` | The consumer registry — one file per opted-in project. |
| `templates\` | Shared workflow prose (`filing`, `compliance`, `continuity`) + couriers (`register.md`, `bootstrap_hub.md`, `setup_machine.md`) + opt-in JSON under `optins\`. |
| `change_requests\` | The inbox — tickets from consumers and registration requests. |
| `scripts\` | Maintainer tooling — see 2.1-2.7 above for what each one does. |
| `hooks\`, `agents\` | The executable tools themselves. |
| `.claude\settings.local.json`, `.claude\self_hooks_status.md` | This repo's own self-use state — gitignored, per-machine. |
| `CHANGELOG.md` | What's in each public release. |
| `config.example.json` / `config.local.json` | Per-machine config. `.example` committed; `.local` gitignored. |
| `design\` | Rationale docs — see Track 3. |
| `project_progress.md` | Cross-session working state for this repo. |
| `CLAUDE.md` | The Claude Code agent's per-session operating manual. Not human onboarding — that's this file. |

### Quick-start cheat sheet
| I want to... | Do this |
|---|---|
| Onboard a project | `scripts\new_consumer.py` (new) or `templates\register.md` (existing) — 2.2 |
| Confirm the fleet is healthy | `scripts\check_tower_crane.py` — 2.3 |
| Push a drift fix to one consumer | checker with `--write-guidance` — 2.3 |
| Push a notice to everyone | `scripts\broadcast_guidance.py --broadcast <file>` — 2.3 |
| Turn on this hub's own tools | `scripts\self_hooks.py --enable <tool>` — 2.3 |
| Set up on a new machine | 2.1 |
| Add another machine/person (Federate) | 2.4 |
| Generate an independent hub (Replicate) | `scripts\seed_hub.py --out <path>` — 2.5 |
| Publish a release | `CHANGELOG.md` entry + `scripts\publish_release.py --version X.Y.Z` — 2.6 |
| Flip the public repo public | `gh repo edit <owner>/<repo> --visibility public` — 2.6 |
| Add a new shareable tool | 2.7 |
