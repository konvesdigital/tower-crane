# Tower Crane

A shared library of reusable Claude Code **tools** (hooks, subagents, scripts) *and* shared
**workflow conventions**, built so one person running several Claude Code projects can keep them
organized without re-inventing the same conventions in every one. It is not a product or a client
deliverable — it's infrastructure you run for yourself.

---

## What it is

Tower Crane is a local hub for running Claude Code across several of your own projects — one shared
set of tools and conventions, with each project pointing at it instead of carrying its own copy.

- **Shared tools** — Claude Code hooks, scripts, and (eventually) subagents. See `MENU.md`.
- **Shared workflow conventions** — how a session saves progress, how a fix reaches every project
  that uses it. See `templates\`.

**Structurally, it's two nested git repos in one folder:**

| | Holds |
|---|---|
| **Outer repo** | Your own working state — which projects you run, open tickets, notes. Private. |
| **`toolkit\`** (this repo) | The tools and conventions themselves. Public, at `konvesdigital/tower-crane`. |

---

## Why you need it

Two things, mainly: **it keeps Claude Code cheap to run**, and **it saves you from rebuilding the
same conventions in every project.**

- **Token economy.** `checkpoint`/`resume` keep each project's `CLAUDE.md` and progress notes lean,
  so only the current state loads every session — not a growing history. The tools you install add
  to this too: a hook like `consistency_check.py` checks your code the moment you save it, as plain
  local Python, at **zero LLM tokens** — instead of asking Claude to re-review it.
- **Time.** Fix a hook or refine a convention once, here, and every project that's opted in picks it
  up automatically — no copy-pasting the same fix into five `CLAUDE.md` files, and no risk of one
  copy drifting from the rest.

The longer version: Claude Code loads a project's `CLAUDE.md` on every single session. Left alone,
that file tends to grow without bound — accumulated instructions, a running history of everything
that ever happened — burning tokens every session whether or not any of it still matters, while
nothing forces work into git along the way. Tower Crane's conventions put a firm line between what a
session actually needs loaded and what's just history worth reading once, and make sure work reaches
git as a habit, not something to remember.

You don't need to be a software engineer to use this — Claude Code drives almost every mechanical
step (git commands, file creation, GitHub operations); you mostly describe intent and approve what
it's about to do.

---

## How to get it

Two steps, both of which Claude Code walks you through — you never need to type raw git commands
yourself:

1. **Clone or download `konvesdigital/tower-crane`.** What you get is `toolkit\` itself, with no
   private wrapper around it yet.
2. **Open it in Claude Code and say:** *"read `templates\setup_machine.md` and follow it."* It
   detects a fresh public clone and wraps it in a new, private outer folder — the "hub" described
   above — checking live for Python/git/`gh` rather than assuming any of them are installed.
   **Claude Code itself is the only assumed prerequisite.**

Handing Claude Code a freshly downloaded repo and asking it to read and follow instructions inside
it is a reasonable thing to be cautious about — see [**Why you can trust it**](#why-you-can-trust-it)
below for exactly what `setup_machine.md` (and every other file like it) can and can't do, and what
review exists before anything from outside your own machine ever reaches you.

If you're setting up a second machine for a hub you already run, or you already have an outer folder
from a previous setup, the same instruction detects that case instead and skips straight to
configuring this machine. The only real constraint is that the folder lives somewhere under your
home directory (`~`) — everything else is computed live from wherever it ends up, never typed in by
hand.

---

## How to use it

Once it's installed, the usual lifecycle is: **connect your projects, let the day-to-day conventions
run themselves inside each one, and turn on automation so the upkeep doesn't need you to open the
hub folder at all.**

1. **Connect a project** — it becomes a *consumer*, referencing the hub's tools/conventions instead
   of duplicating them.
2. **Work in the project as usual** — say `"checkpoint"` to save progress, `"resume"` to pick back
   up.
3. **Turn on automation** (recommended) so tickets and health checks keep running without you.

The rest of this section covers each of those in more detail, plus — at the end — what it looks like
to work on Tower Crane itself.

### Connecting a project

A project you point at the hub becomes a **consumer** — it references the shared tools and
conventions instead of copying them. Nothing here runs automatically *to* a project until you do
this, and you can disconnect any time by removing the reference lines.

- *Brand-new project* → from inside `toolkit\`:
  ```
  scripts\new_consumer.py --target-path C:\Users\you\Documents\MyNewProject --project-name "My New Project"
  ```
  Creates every file the project needs in one shot — `.claude\settings.json`, `CLAUDE.md` with
  `@import` lines, a skeleton `project_progress.md`, and a `FIRST_RUN.md` checklist — plus a
  registry entry here.
- *Existing, hand-built project* → copy `toolkit\templates\register.md` into its root, open it in
  Claude Code, and say *"read register.md and follow it."* It swaps any pasted workflow prose for
  `@import` lines and files a registration request into the hub's ticket inbox — the migration path,
  preserving everything project-specific and only replacing shared, canonical prose.

### The habits that matter, inside a connected project

Roughly in order of how often you'll reach for them:

1. **"checkpoint"** — say it any time you want to save progress. Updates `project_progress.md`
   (Current Status/Next Up, a new dated Work Log entry), then commits and pushes.
2. **"resume"** — say it at the start of a session. Pulls latest, reads only Current Status, Next
   Up, and the most recent Work Log entry, and tells you where things stand in a couple of lines.
3. **`project_progress.md`** — the one file that carries state between sessions. Current Status and
   Next Up describe only the present; anything finished lives exactly once, in its Work Log entry.
4. **"archive"** — any time the Work Log has grown long. Moves settled entries out to
   `project_progress_archive.md`, never read back into context unless something calls for old
   history.
5. **Filing a bug or improvement in a shared tool** — drop a ticket in the hub's
   `change_requests\` folder per `templates\filing.md`, then commit/push it yourself. From there
   it's automatic: the ticket gets picked up (next time you're in the hub, or by unattended
   automation if it's on), the fix gets applied, and `scripts\check_tower_crane.py` runs the
   fleet's regression + drift suite to confirm the fix didn't break any of your other connected
   projects — all before the ticket is ever flagged ready for you to confirm it actually fixed what
   you filed.
6. **Receiving guidance** — if a project has drifted, or you've broadcast a notice, you'll find a
   `COMPLIANCE_GUIDANCE.md` in that project's root. The project's own agent shows you the literal
   proposed change alongside a plain-language summary and asks before applying it.

Full mechanics: `templates\continuity.md`.

### Keeping your projects healthy

A few commands keep every connected project honest without visiting each one individually.

- **Health check.** `scripts\check_tower_crane.py` — the golden regression suite (does each tool
  still behave correctly?) and drift scan (does every project's wiring still resolve?) that runs
  automatically every time a shared-tool ticket gets applied, not something you have to remember to
  invoke. You can also run it by hand any time you want to confirm the fleet is healthy without
  waiting for a ticket.
- **Push a fix or a notice.** `check_tower_crane.py --write-guidance` targets one drifted project;
  `scripts\broadcast_guidance.py --broadcast <file>` sends a one-off, hand-authored notice to all of
  them.
- **Turn on unattended automation.** An hourly, unattended tick that processes open tickets and
  refreshes compliance guidance without you opening an interactive session here. It never touches
  the public repo unattended and never adopts anything unreviewed on its own — it only surfaces
  what it couldn't safely resolve at your next session. Off by default: *"read
  `templates\setup_automation.md` and follow it."*
- **Turn on the hub's own tools, on itself.** Tower Crane isn't a consumer of itself by default —
  `scripts\self_hooks.py --list`/`--enable <tool>`/`--disable <tool>` closes that gap, per machine.

### Working within Tower Crane itself

Occasionally you'll want to change the shared tools themselves. That happens two genuinely different
ways, worth keeping distinct: changes that stay entirely on your own machine, and changes that touch
the public repo — the one place content you didn't personally write can enter. See
[**Why you can trust it**](#why-you-can-trust-it) below for exactly what review happens on the public
side.

Two kinds of things are shared, reaching a project two different ways:

| Shared thing | Example | How a project gets it |
|---|---|---|
| **Tools** (executable) | `hooks\consistency_check.py` | Its `.claude\settings.json` points at the shared file by a per-machine command. |
| **Workflow** (prose) | checkpoint/resume, filing a bug | Its `CLAUDE.md` `@import`s the shared prose by path. |

**Local changes — edit it once, here, and every connected project picks it up automatically, with
nothing leaving your machine:**
- **Add or fix a tool.** Build and test it in whichever project prompted the need, strip anything
  project-specific, drop it in `hooks\`/`agents\`/`scripts\`, add a row + opt-in snippet to
  `MENU.md`. An automatic hook must exit code **2** with its failure report on **stderr** on a FAIL
  — any other exit code is silently non-blocking, so a real failure would never reach the agent.
  Full steps: `AGENTS.md` ("Adding a new tool").
- **Refine a convention.** A purely additive or prose-only fix propagates to your own projects on
  their next session with no announcement, logged in the Work Log only — no need for the full
  change-request ceremony that a behavior-changing fix gets.

**The public repo — the one channel that reaches beyond your own machine:**
- **Pull in updates.** The `update` action reviews and merges whatever's changed in
  `konvesdigital/tower-crane` since you last approved it.
- **Propose a change back.** `"propose upstream"` is an ordinary fork-branch-PR flow Claude Code
  drives for you.
- **What actually ships there** is exactly this `toolkit\` repo — your outer repo's tickets,
  registry, and notes are never part of it; there's no git history shared between the two, so
  there's no channel for them to leak in either direction.

Setting up another of your own machines is covered in [How to get it](#how-to-get-it) above — same
courier, same steps, just run once more on the new machine.

---

## Why you can trust it

**Nothing reaches your projects, and nothing you propose reaches anyone else, without you seeing
exactly what changed and approving it.** Three gates govern everything that moves between your hub
and the outside world:

| Gate | Fires when | What happens |
|---|---|---|
| **Update** | You pull changes from the public repo into your own `toolkit\` | A regression suite runs, then the literal diff is shown to you verbatim alongside a plain-language read — nothing merges without your approval. |
| **Merge** | Any proposed change tries to land on the public repo's `main` | Required owner review plus a battery of automated checks must all pass before it can merge. |
| **Upstream** | You propose a change from your own hub back to the public repo | An authoring assistant checks it before it's even opened as a PR, so it doesn't arrive at Merge already broken. |

You stay in control throughout: your outer (private) repo never touches the public repo at all, your
own tickets against your own toolkit process automatically because there's no one else who needs to
review them, and anything arriving from outside waits for your explicit yes — declining an update is
a fully supported, permanent choice, not a nag. The one honest exception: if you own the public repo
yourself, your own `checkpoint` pushes straight to it (GitHub requires *some* owner override, or an
owner could never merge their own change at all) — but even then, a change to the directive file's
binding rules is flagged to you explicitly before it goes out, so that class of change is never made
without you knowing you made it.

### The directive file's own safeguards

`AGENTS.md` — the file that actually governs an agent's behavior in this repo — is written to be
checked, not just trusted:

- Opens with a bounded list of what it may ever direct an agent to do (git, local filesystem — never
  network, never credentials).
- Its binding rules ("Standing Constraints") are written in explicit MUST/MUST NOT language, so a
  script can grep for the exact wording instead of trusting a paraphrase.
- Carries an explicit anti-override clause: nothing later in the file, or anything it imports, can
  weaken that section.
- **That clause isn't just prose — it's mechanically enforced.** `check_standing_constraints.py`
  runs as part of the Merge gate on every pull request and blocks, unconditionally, any change to
  the Standing Constraints' exact wording — no override built into the check itself, and no
  "legitimate tightening" exception, since a script can't tell that apart from a weakening edit. The
  only way past it is the repo owner's own GitHub-level merge override, a distinct, logged action —
  never something granted by any script in this project.
- A stated, enforced line-count ceiling keeps "this file stays short" a falsifiable claim, not just
  an assertion.

The same principle extends to every other file in this repo that hands Claude Code a procedure to
follow — `setup_machine.md`, `register.md`, `setup_automation.md`, and the rest of `templates\`.
None of them are designed to compel anything: each is read and carried out as a suggested sequence
of steps, phrased for a human to approve along the way, and you can stop, skip, or override any step
at any time. Nothing in this repo hijacks your local agent or acts on your machine without your
say-so — these are instructions a session chooses to follow, never code that runs itself.

### Every safety mechanism, in full

For full transparency, every concrete check currently built, which gate it belongs to, and the
script that enforces it:

| Gate | Hard / Soft | Mechanism (script) | What it checks | Runs when |
|---|---|---|---|---|
| Update | Hard, no override | `update_toolkit.py` — golden suite | The regression suite must pass before any pending commit can be trusted. | Every `update` |
| Update | Hard abort (`--check`/`--approve`) / soft WARN (`--notify`) | `update_toolkit.py` — origin remote-identity check | The remote you're pulling from is actually the expected public repo, not a repointed or typosquatted one. | Every `update` |
| Update | Mandatory human step | `update_toolkit.py` — diff-review gate | Shows the literal diff verbatim alongside a plain-language assessment; nothing merges without explicit approval. A large pending batch can be approved commit-by-commit instead of all at once. | Every non-empty `update` |
| Merge | Hard | `check_file_surface.py` — known AI-directive filename | Blocks a new file mimicking `CLAUDE.md`/`.cursorrules`/a second `AGENTS.md` anywhere but the one canonical file. | Every PR |
| Merge | Hard | `check_file_surface.py` — non-Python script | Blocks a script in any language but Python, by extension *and* shebang (catches a rename-to-evade attempt). | Every PR |
| Merge | Hard | `check_file_surface.py` — script outside its home | Blocks a `.py` file added anywhere but `hooks\`/`scripts\`/`agents\`/a test fixture. | Every PR |
| Merge | Hard | `check_file_surface.py` — binary file | Blocks any binary blob anywhere in the diff — this is a text-based repo; there's never a legitimate one. | Every PR |
| Merge | Soft | `check_file_surface.py` — disguised-code heuristic | Flags eval/exec/base64/curl-pipe-shell content in a file not already classified as code. | Every PR |
| Merge | Hard | `check_file_surface.py` — invisible/formatting Unicode | Blocks zero-width, bidi-control, variation-selector, and Unicode "tag" characters in any added line — text that can render blank or reordered in a diff view while still parsing as instructions. | Every PR |
| Merge | Soft | `check_file_surface.py` — Python capability creep | Flags new code introducing a network call, dynamic-exec, or deserialization primitive not covered by `AGENTS.md`'s declared capabilities. | Every PR |
| Merge | Hard | `check_scripts_gate.py` | Runs `consistency_check.py`'s static analysis (undefined names, arity mismatches, string-key drift) over every changed script. | Every PR |
| Merge | Hard | `check_agents_pr_gate.py` — filename invariant | `AGENTS.md` must still exist, at that path. | PRs touching `AGENTS.md` |
| Merge | Hard | `check_agents_pr_gate.py` — frontmatter schema | Required metadata fields are present and well-formed. | PRs touching `AGENTS.md` |
| Merge | Hard, unconditional | `check_agents_pr_gate.py` / `check_standing_constraints.py` — Standing Constraints match | The binding-rules section matches `main` verbatim, exact text — no exceptions, since a script can't tell a weakening edit from a legitimate one. | PRs touching `AGENTS.md` |
| Merge | Soft | `check_agents_pr_gate.py` — capability-vs-content | Flags diff content outside the file's own declared capability list. | PRs touching `AGENTS.md` |
| Merge | Soft | `check_agents_pr_gate.py` — diff-size gate | Flags a single PR changing more than ~60 lines of `AGENTS.md`, or growing it past its own declared limit. | PRs touching `AGENTS.md` |
| Merge | Hard | `check_agents_pr_gate.py` — required PR trailer | The PR body must carry both a "Contributor statement" and an "Independent read" section. | PRs touching `AGENTS.md` |
| Merge | Structural | CODEOWNERS + branch protection | Requires the repo owner's review before any PR touching `hooks\`/`scripts\`/`templates\`/`agents\`/`AGENTS.md`/`.github\` can merge. | Every PR |
| Merge | Structural | SHA-pinned GitHub Actions | Third-party Actions are pinned to an exact commit, not a movable tag, so a rewritten tag can't change what runs. | Every workflow run |
| Merge | Structural | Least-privilege workflow permissions | Workflows declare read-only `contents` access and pass PR title/body through `env:` rather than interpolating them into a shell command. | Every workflow run |
| Upstream | Overridable warning | `check_standing_constraints.py` — proposal-time check | Flags, and asks you to confirm, if your own proposed change touches the binding-rules section — before it's even opened as a PR. | `"propose upstream"`, when `AGENTS.md` is touched |
| Upstream | Disclosure only, non-blocking | `check_standing_constraints.py` — checkpoint-time check | Flags it to you if your own direct push (as repo owner) changes the binding-rules section — can't block the push, guarantees you know you made the change. | Every `checkpoint` touching `AGENTS.md` |
| Local | Hard contract | Hook exit-2/stderr contract | Any automatic hook (e.g. `consistency_check.py`) must exit code 2 with its failure on stderr, or a real FAIL never reaches the agent — any other exit code is silently non-blocking. | Every hook run |

This is a real, substantial mitigation — not a guarantee. No mechanism fully solves "the
maintainer's own account or machine is compromised"; that's true of code signing and every other
supply-chain defense in production use today. Build/CI-infrastructure compromise is explicitly out
of scope for the same reason (though this project's zero third-party Python dependencies close off
one major version of that risk on their own) — named here so it's a known limit, not an
unconsidered one.

---

## Reference

### Where things live
**Outer repo (private):** `consumers\` (registry), `change_requests\` (ticket inbox), `design\`
(rationale docs), `project_progress.md` (working state), `CLAUDE.md` (a one-line `@import` pointer
at `toolkit\AGENTS.md`), `toolkit\` (gitignored by this repo entirely).

**Inner `toolkit\` repo (public, `konvesdigital/tower-crane`):** `MENU.md` (catalog), `templates\`
(shared prose + couriers), `scripts\` (maintainer tooling), `hooks\`/`agents\` (the executable
tools), `CHANGELOG.md`, `config.example.json`/`config.local.json` (per-machine config, `.local`
gitignored), `AGENTS.md` (the canonical operating instructions).

### Quick-start cheat sheet
| I want to... | Do this |
|---|---|
| Set up my hub | `templates\setup_machine.md` |
| Set up another of my own machines | `templates\setup_machine.md` |
| Connect a project | `scripts\new_consumer.py` (new) or `templates\register.md` (existing) |
| Save/resume progress in a project | say `"checkpoint"` / `"resume"` |
| Keep everything running itself | `templates\setup_automation.md` |
| Confirm the fleet is healthy | `scripts\check_tower_crane.py` |
| Push a fix to one project | checker with `--write-guidance` |
| Push a notice to all my projects | `scripts\broadcast_guidance.py --broadcast <file>` |
| Add or fix a shareable tool | see "Working within Tower Crane itself" above |
| Pull a reviewed toolkit update | the `update` action — see `AGENTS.md` |
| Propose a fix upstream | `"propose upstream"` — see `AGENTS.md` |
| Turn on this hub's own tools | `scripts\self_hooks.py --enable <tool>` |
