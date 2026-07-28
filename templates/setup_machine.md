<!--
Home: toolkit\templates\setup_machine.md  (part of the tower_crane pattern — floats on HEAD)
This is the CANONICAL per-machine setup courier: fills config.local.json for THIS machine/clone by
checking and asking, never assuming. Referenced (never copied/duplicated) from:
  - README.md's "Setup (fresh clone / new machine)" section — Federate: joining or re-setting up a
    clone of an existing hub.
  - This file's own Step 0 scenario B ("Bootstrapping the outer hub") — Replicate: standing up a
    brand-new independent hub from a fresh public clone of `toolkit\`. Retired 2026-07-27:
    `scripts\seed_hub.py`, `scripts\publish_release.py`, and the strip-in-place courier
    `templates\bootstrap_hub.md` (all three of which predated the outer/inner split) are gone —
    getting a hub of your own is now just an ordinary `git clone` of the public repo plus this
    scenario, nothing generated or stripped.

How it's used: open the hub (the outer folder — see Step 0 below if you're not sure one exists yet)
in Claude Code and say "read toolkit\templates\setup_machine.md and follow it." **The only assumed
prerequisite is Claude Code itself running this session** — Python, git, gh, and this machine's path
conventions are all checked live, never assumed.

Without Claude Code: every step below is still just a CLI command and a question — substitute
yourself for "the agent," run the same commands, answer the same questions.

Keep this file project/OS-agnostic. Edits here are canonical — the three consumers above only ever
point at it, never copy its content, so a change here reaches all three automatically.
-->

# Set up this machine (config.local.json)

You (the agent running in THIS repo/hub) are configuring this machine's copy of tower_crane so its
maintainer tooling and consumer hook work correctly here. Check and ask at every step below — never
silently write a guess into `config.local.json` and let a later script fail on it instead. If
something expected is missing, say so plainly and ask the user what to do.

Work through this **with the user in the loop**: narrate each check as you run it, and show the
final `config.local.json` for explicit confirmation before writing it (Step 7).

## Step 0 — Detect what you're starting from
The hub is two nested git repos in one folder: an outer, private repo (holds `project_progress.md`,
`consumers\`, `change_requests\` — the user's own continuity data) and an inner `toolkit\` repo
(holds `hooks\`, `scripts\`, `templates\`, `AGENTS.md`, `config.example.json` — this file included).
Two different starting points reach this file, and you need to tell them apart before doing
anything else — ask the user directly if it isn't obvious; don't guess from folder names alone.

**A. An existing hub, already set up.** You're running from inside `toolkit\`, and the outer folder
one level up already has (or is meant to have) `project_progress.md`/`consumers\`/
`change_requests\`. Verify `config.example.json` exists in **this** (`toolkit\`) folder's root. If
`config.local.json` also exists here and looks filled in (no `<...>` placeholders left), tell the
user and ask whether they want to redo it or stop here — don't overwrite a working config by
default. Otherwise, skip straight to Step 1.

**B. A fresh public clone — nothing wrapping it yet.** The user just cloned or downloaded
`konvesdigital/tower-crane` directly, so what they're sitting in right now **is** the toolkit
content itself (`hooks\`, `scripts\`, `templates\`, `AGENTS.md`, `config.example.json` all present),
but there's no outer folder around it — none of `project_progress.md`/`consumers\`/
`change_requests\`/`design\` exist anywhere yet. Tower Crane needs that outer layer to actually work
day to day (it's where the user's own project tracking and tickets live) — go to "Bootstrapping the
outer hub" below before continuing to Step 1.

### Bootstrapping the outer hub (only if B)
1. Explain plainly what's about to happen: this folder needs to become a `toolkit\` subfolder one
   level inside a new outer folder — the outer folder is the user's own **private** space (their
   own GitHub repo, never the public one) holding `project_progress.md`, `consumers\`,
   `change_requests\`, and a thin `CLAUDE.md` pointer importing `toolkit\AGENTS.md`.
2. Ask the user to confirm (or pick) the new outer folder's name and location — don't assume
   `tower_crane`; ask.
3. This session's own working directory sits inside the folder that needs to move, so **this step
   can't be finished by Claude Code alone, mid-session** — give the user the exact commands to run
   themselves (adapt for their OS/shell: e.g. on Windows, from the parent of the current folder,
   `mkdir <outer-name>` then `move <current-folder-name> <outer-name>\toolkit`; the `mv` equivalent
   on macOS/Linux), then ask them to close this session. `git remote -v` inside the moved folder
   should still show `origin` pointing at `konvesdigital/tower-crane` afterward — nothing about the
   toolkit clone itself changes, only its location.
4. Tell the user: once moved, open Claude Code fresh inside the new outer folder and say "read
   `toolkit\templates\setup_machine.md` and follow it" again — this time Step 0 detects scenario A,
   and the rest of this file builds `config.local.json` as normal.
5. If they want a private GitHub repo backing the new outer folder (recommended, for backup/
   continuity — see `design\local_first_reframe.md` if curious why this matters), offer to help once
   the new session starts: `gh repo create <name> --private`, `git init`, add the remote, a
   `.gitignore` with `/toolkit/`, a thin `CLAUDE.md` pointer (`@~/<path-to-outer>/toolkit/AGENTS.md`),
   empty `consumers\`/`change_requests\`/`design\` folders, and a skeleton `project_progress.md`
   (same shape `templates\register.md`'s Step 3 writes). One-time setup, only for a brand-new outer
   hub.

## Step 1 — This machine's OS
You already know this from your own environment context (the platform your session is running on) —
no need to probe for it. Keep it in mind below: a couple of defaults differ by OS (Python launcher
name, hostname command).

## Step 2 — Check for Python 3
The `consistency_check` hook is pure Python — this machine needs Python 3 on PATH to run it.

1. Try `python3 --version`. If that prints a `Python 3.x` version, that's your `python_launcher`.
2. If not, try `python --version`. If that's Python 3.x, use `python`. If it's Python 2.x, that won't
   work — tell the user and continue to 3.
3. If neither command produces a Python 3.x version: **stop and tell the user directly** — "This
   machine needs Python 3 installed and on PATH; I couldn't find it via `python3` or `python`. Do you
   have it somewhere else, or would you like help installing it?" Do not guess a launcher value.

## Step 3 — Confirm git, and gh only if needed
- Run `git --version` — this should always succeed (you're in a git repo). If it doesn't, something
  is unusually wrong with this machine; stop and ask.
- Ask the user: "Do you plan to publish releases or stand up your own independent hub from this one
  (Replicate)?" Only if yes: check `gh --version`, and if missing, tell them plainly and point at
  `gh`'s install docs. `gh` is not needed for ordinary use (scaffolding consumers, running the
  checker, Federate).

## Step 4 — shared_root and import_base: nothing to do
Both are computed automatically, live, by `config_lib.py` the moment any script reads
`config.local.json` — you don't compute them, ask the user for them, or write them into
`config.local.json` yourself. There's no conventional location or folder name to check for: this
hub works from wherever it actually sits, under whatever name the user gave the folder.

The one real constraint: **this repo must live somewhere under the user's home directory.**
Claude Code's `@import` (which consumers use to pull in shared workflow prose) only resolves
home-relative `~/...` paths — there's no other form proven to work. If Step 8 below errors out
saying this folder isn't under the home directory, tell the user plainly and ask them to move it
there (any subfolder, any name — just somewhere under `~`).

If the folder is ever moved or renamed later, the next script run notices on its own and prints a
`[NOTICE]` explaining what changed — at that point, offer to run `scripts\relocate.py` so
already-onboarded consumers pick up the new location too. Nothing needs to be pre-empted here;
just leave `config.local.json`'s `shared_root` field as `""` in Step 7 and let Step 8 fill it in.

## Step 5 — host_id
Get this machine's hostname (`$env:COMPUTERNAME` on Windows / `hostname` on macOS/Linux — or ask the
user if you can't run shell commands directly) and propose it as `host_id`. Confirm with the user
rather than silently accepting it — they may want a different label.

## Step 6 — Identity
`identity.git_remote` means the **outer** hub's own private remote (the one behind
`project_progress.md`/`consumers\`/`change_requests\`) — not `toolkit\`'s own `origin`, which
already points at the public `konvesdigital/tower-crane` repo and needs no separate recording here.
Don't ask blind — check first, then confirm:
- `git config user.name` / `git config user.email` — if already set, propose using those values.
- Run `git remote get-url origin` **from the outer folder** (one level up from `toolkit\`) — if set,
  propose that as `git_remote`. If the outer folder has no remote yet (a brand-new hub), ask the
  user for the GitHub URL they intend to use, or tell them to create one first if they haven't.
Only ask outright for whatever the checks above don't already answer.

## Step 7 — Write config.local.json (confirm first)
`config.local.json` lives inside `toolkit\` (alongside `config.example.json`), not in the outer
folder. Show the user the complete proposed `config.local.json` built from Steps 2-6 and get an
explicit go-ahead before writing it.

## Step 8 — Regenerate and verify
`toolkit\scripts\relocate.py` and `toolkit\scripts\check_tower_crane.py` are cross-platform Python —
they run the same way on Windows, macOS, and Linux, using whichever launcher Step 2 found (`python3`
or `python`).

From inside `toolkit\`, run `scripts\relocate.py` (regenerates any registered consumers' hook
commands for this machine), then `scripts\check_tower_crane.py` to confirm a clean bill of health.

## Step 9 — Finish
Confirm to the user: `config.local.json` is filled and validated. This machine is ready to
scaffold/check consumers, or to onboard as a Federate participant on an existing hub.
