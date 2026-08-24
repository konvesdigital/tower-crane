<!--
Home: toolkit\templates\setup_machine.md  (part of the tower_crane pattern — floats on HEAD)
This is the CANONICAL per-machine setup courier: fills config.local.json for THIS machine/clone by
checking and asking, never assuming. Referenced (never copied/duplicated) from:
  - README.md's "Setup (fresh clone / new machine)" section — Federate: joining or re-setting up a
    clone of an existing hub.
  - This file's own Step 0 flat-clone branch (0c) — Replicate: standing up a brand-new independent
    hub from a fresh public clone of `toolkit\`. Retired 2026-07-27:
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

This file explains how to use the mechanism it covers. `capability_relationships` explains how
this mechanism works and how it relates to other mechanisms.
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

Mechanized as `scripts\setup_machine_preflight.py` (`design\command_procedure_audit.md`'s C1-C6) —
run it, don't reconstruct this sequence by hand or improvise around whatever error comes up first.
Step 2 below is what formally settles this machine's `python_launcher` — that hasn't happened yet
here, so just try `python3` first and fall back to `python` (same order Step 2 uses) for every
invocation of this script in Step 0; if neither responds at all, Step 2 will catch and resolve that
properly once you reach it.

**Bringing an existing hub to a new machine? Clone, don't copy.** If the user mentions they
physically copied (or are about to copy) the folder from another machine rather than `git clone`ing
both repos fresh, stop and steer them toward cloning instead: it's strictly less total work (no
separate reconcile-with-remotes step afterward) and it structurally avoids stale gitignored
per-machine state (`config.local.json`'s `host_id`, `.claude\settings.local.json`'s baked hook
paths) riding along from the old machine — see README.md's "Second machine" section for the exact
two-clone steps. A copy isn't fatal (this file still works from one), but it invites exactly the
kind of stale-state bugs `design\second_machine_onboarding.md` documents a live session hitting.

**0a. Ask reconnect-vs-new first, before touching any file (C1).** Does the user already have an
existing outer hub remote (a private GitHub repo from a previous machine, or one they just want to
attach a fresh clone to), or is this the first time this hub exists anywhere? Ask directly — don't
infer it from whatever's currently sitting in the folder. This also covers the recovery case: if
`setup machine` was already run once this session under the wrong assumption (a fresh outer scaffold
got written, then the user remembered they have an existing remote), the fix is to reconcile —
discard or move the just-scaffolded files — not a separate procedure.

**0b. Detect the current shape:** the script's own path depends on the shape you're trying to
detect, so try both from cwd: `scripts\setup_machine_preflight.py --detect` (resolves if cwd is
flat, or if cwd is `toolkit\` itself) first, then `toolkit\scripts\setup_machine_preflight.py
--detect` (resolves if cwd is an outer root with a `toolkit\` subfolder already) if the first path
doesn't exist. If **neither** path exists at all, that's the ambiguous case below — nothing to run,
go straight to asking. Whichever one resolves reports one of:
- `[NESTED]` — already correctly structured (either cwd is the outer root with a `toolkit\`
  subfolder, or cwd is `toolkit\` itself with a populated outer folder one level up). Nothing further
  needed — skip straight to Step 1.
- `[FLAT]` — cwd **is** the toolkit content itself (`hooks\`, `scripts\`, `templates\`, `AGENTS.md`,
  `config.example.json` all present directly here), no outer wrapper around it yet. Continue to 0c.
- `[AMBIGUOUS]` — neither shape found (C5). Don't assume cwd is the right place — ask the user
  directly where they actually cloned things, relative to where this session is running, and re-run
  `--detect` from the real location once you know it.

**0c. If flat: nest, then build or attach the outer layer.** Note the script's own path changes
mid-sequence: before step 1 it's flat in cwd (`scripts\setup_machine_preflight.py`); from step 2
onward `--nest` has already moved it down (`toolkit\scripts\setup_machine_preflight.py`).
1. `python scripts\setup_machine_preflight.py --nest` — creates a `toolkit\` subfolder in cwd and
   moves the flat content down into it (`.git\` included). cwd itself never moves, so this needs no
   session restart — the whole sequence below continues in the same session.
2. Per step 0a's answer:
   - **New hub, no existing remote yet:** `python toolkit\scripts\setup_machine_preflight.py
     --new-outer` (add `--git-remote-url <url>` if the user already has one — see the "if they want a
     private GitHub repo" note below for creating one first). Scaffolds `CLAUDE.md`, `.gitignore`,
     `consumers\`/`change_requests\`/`design\`, and a skeleton `project_progress.md`. Writes files
     and runs `git init` only — nothing is committed or pushed yet.
   - **Reconnect to an existing remote:** `python toolkit\scripts\setup_machine_preflight.py
     --attach-existing --git-remote-url <url>` — runs `git init` / `remote add origin` / `fetch` /
     `checkout -b main --track origin/main` (C2's workaround for `git clone` refusing a non-empty
     target directory, which cwd now is thanks to the just-created `toolkit\` subfolder).
3. If you scaffolded a new outer (not attached an existing one), commit and push it now through the
   ordinary checkpoint flow: `toolkit\scripts\checkpoint_git.py --message "Initial hub scaffold"
   --include-all`.
4. **If the user wants a private GitHub repo backing a brand-new outer hub** (recommended, for
   backup/continuity — see `design\local_first_reframe.md` if curious why this matters) and doesn't
   have one yet: this is the one moment `gh` might be needed (C4 — check lazily, right here, never
   earlier) — `gh --version`; if missing, tell the user plainly and point at `gh`'s install docs, or
   let them create the repo manually on GitHub's website instead. Then `gh repo create <name>
   --private`, and pass the resulting URL as `--git-remote-url` to `--new-outer` above (or `git
   remote add origin <url>` by hand afterward if `--new-outer` already ran without it).

Once Step 0 finishes (nested from the start, or freshly nested-and-built/attached above), continue
to Step 1 from inside the now-correctly-structured hub.

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
user if you can't run shell commands directly). Don't just propose it and wait for a yes — the raw
hostname alone gives no frame of reference for what a `host_id` actually looks like (C6): from
inside `toolkit\`, run `scripts\setup_machine_preflight.py --known-hosts` first (same
launcher-agnostic `python`/`python3` fallback as Step 0) and offer whatever it lists (nicknames a
prior machine's setup chose, e.g. something short and memorable rather than a raw system name)
alongside the raw hostname, then ask directly whether this machine has connected to this hub before,
under one of those names or a different one — don't try to infer it. Example framing: *"Host ID:
this computer's system name is `DESKTOP-XYZ123` — want to use something else? Already-known hosts
on this hub: `<name from --known-hosts>`. Has this machine connected before, under a different
name?"* Empty `--known-hosts` output (a genuinely
first-ever machine) just means propose the raw hostname with no further context, same as before.

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

## Step 8a — Register this host in shared_resources (if any exist)
If `shared_resources\CATALOG.md` exists and has at least one non-`Archived`, non-`insight` row, run
the `"register host"` procedure now (`agents_continuity.md`,
`design\shared_resources_bulk_host_registration.md`) — a brand-new machine otherwise has zero
visibility into which catalog entries it could register a local path for until something happens to
adopt one and hit the lazy per-project `[HOST-GAP]` check. Skip silently if the catalog doesn't
exist yet or every entry is already `Archived`/`insight`.

## Step 9 — Finish
Confirm to the user: `config.local.json` is filled and validated. This machine is ready to
scaffold/check consumers, or to onboard as a Federate participant on an existing hub.
