<!--
Home: templates\setup_machine.md  (part of the tower_crane pattern — floats on HEAD)
This is the CANONICAL per-machine setup courier: fills config.local.json for THIS machine/clone by
checking and asking, never assuming. Referenced (never copied/duplicated) from three places, so it
stays the single source of truth:
  - README.md's "Setup (fresh clone / new machine)" section — Federate: joining or re-setting up a
    clone of an existing hub.
  - templates\bootstrap_hub.md Step 7 — Replicate: a freshly-bootstrapped independent hub's first
    setup.
  - the generated SETUP.md that scripts\seed_hub.py writes into every distributed hub — Replicate
    recipient's first setup. (This file ships automatically — templates\ is a KEEP dir.)

How it's used: open this repo/hub in Claude Code and say "read templates\setup_machine.md and
follow it." **The only assumed prerequisite is Claude Code itself running this session** — Python,
git, gh, and this machine's path conventions are all checked live, never assumed.

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

## Step 0 — Confirm there's something to set up
Verify `config.example.json` exists in this repo's root. If `config.local.json` already exists and
looks filled in (no `<...>` placeholders left), tell the user and ask whether they want to redo it or
stop here — don't overwrite a working config by default.

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
Don't ask blind — check first, then confirm:
- `git config user.name` / `git config user.email` — if already set, propose using those values.
- `git remote get-url origin` — if set, propose that as `git_remote`. If this is a brand-new hub with
  no remote yet, ask the user for the GitHub URL they intend to use (or tell them to create one first
  if they haven't).
Only ask outright for whatever the checks above don't already answer.

## Step 7 — Write config.local.json (confirm first)
Show the user the complete proposed `config.local.json` built from Steps 2-6 and get an explicit
go-ahead before writing it.

## Step 8 — Regenerate and verify
`scripts\relocate.py` and `scripts\check_tower_crane.py` are cross-platform Python — they run the
same way on Windows, macOS, and Linux, using whichever launcher Step 2 found (`python3` or `python`).

Run `scripts\relocate.py` (regenerates any registered consumers' hook commands for this machine),
then `scripts\check_tower_crane.py` to confirm a clean bill of health.

## Step 9 — Finish
Confirm to the user: `config.local.json` is filled and validated. This machine is ready to
scaffold/check consumers, or to onboard as a Federate participant on an existing hub.
