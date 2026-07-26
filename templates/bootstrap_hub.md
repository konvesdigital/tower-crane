<!--
Home: templates\bootstrap_hub.md  (part of the tower_crane pattern — floats on HEAD)
This is the REPLICATE courier. It turns a fresh COPY/CLONE of tower_crane into your OWN
independent hub: it strips the source hub's instance state (registry, change-request history,
design docs, progress, git history) and re-points everything at a repo you own.

How it's used: clone or copy the tower_crane repo to a new location that will be YOUR hub, open
that copy in Claude Code, and say "read templates\bootstrap_hub.md and follow it."

Unlike register.md (a one-time courier that self-deletes from a foreign project), this file is
part of the reusable pattern and STAYS in templates\ — your new hub can itself be replicated later.
Keep it project-agnostic and path-relative: it operates on "this copy," so it must never hardcode a
machine path. Edits here are the canonical version.
-->

# Bootstrap a fresh tower_crane hub (Replicate)

You (the agent running in THIS copy of tower_crane) are standing up an **independent hub** from the
tower_crane **pattern**. The result is a clean, empty hub that carries the reusable tooling and
conventions but **none of the source hub's state** — no registered consumers, no ticket history, no
design narrative, no git history, no identity. It is yours to grow from zero.

> **Replicate vs Federate.** This is *Replicate* — a separate, independent hub with its own GitHub
> repo and its own (initially empty) registry. If instead you want another machine to **join an
> existing hub** (same repo, same shared registry), that is *Federate*: don't run this — just clone
> the existing repo, fill `config.local.json`, and run `scripts\relocate.py`. Bootstrapping is
> one-way and destructive; Federating is not.

---

## ⚠️ Safety gate — read before doing anything

This runbook **deletes files**. It is meant to run against a **fresh copy** you intend to convert
into your own hub — **never** against someone's live working hub. Before any deletion:

1. Confirm with the user, out loud, that **this directory is a throwaway copy meant to become their
   own independent hub**, not the original.
2. Run `git remote -v`. If it points at someone else's repo (the hub you copied from), that is
   expected for a fresh clone — but you will replace it in Step 6, and you must **never push to it**.
3. If anything is ambiguous — the path looks like the original hub, there are uncommitted changes you
   didn't make, the user hesitates — **STOP and ask.** Do not proceed on assumption.

Work through the steps **with the user in the loop**. Show the plan in Step 1 and get an explicit
"go" before deleting anything.

---

## Step 0 — Confirm this is a tower_crane copy
Verify this directory looks like tower_crane: it has `CLAUDE.md`, `MENU.md`, `templates\`,
`scripts\`, `hooks\`, and `consumers\`. If not, stop — you're in the wrong place.

## Step 1 — Show the plan and get a go
Present these three lists to the user and wait for explicit confirmation before Step 2.

**STRIP (source hub's instance state — deleted):**
- `consumers\*` — the source hub's registered projects. Emptied (keep the folder).
- `change_requests\*` — the source hub's ticket/registration history. Emptied (keep the folder).
- `design\` — the source hub's design narrative (references its own consumers, dates, decisions).
  Removed entirely — this is the "pattern-only, no trace of the source project" choice.
- `project_progress.md` and `project_progress_archive.md` — the source hub's work log. Regenerated
  as a skeleton (Step 4).
- `config.local.json` — if a folder-copy carried it, it holds the **source owner's** machine values
  and identity. Deleted (you'll write your own in Step 7). *(A `git clone` won't have it — it's
  gitignored — but a raw copy might.)*
- `_archive\` — if present (gitignored source scratch). Deleted.
- The source hub's **git history and remote** — replaced with a fresh history + your remote (Step 6).

**KEEP verbatim (the reusable pattern):**
- `hooks\`, `agents\`, `scripts\`, `tests\` — the executable tools + golden fixtures + maintainer
  tooling.
- `templates\` — all workflow prose (`filing`, `compliance`, `continuity`), the opt-in JSON under
  `optins\`, `register.md`, and this `bootstrap_hub.md` (it stays — see Step 10).
- `CLAUDE.md` — the governance operating manual (lightly generalized in Step 5).
- `config.example.json`, `.gitignore` — pattern, no instance data.

**REGENERATE as skeletons (Steps 3–4):**
- `MENU.md` — kept, but its "In use by" entries reset to none.
- `README.md` — replaced with a clean skeleton (the source README carries the source project's
  narrative + `design\` pointers).
- `project_progress.md` — fresh skeleton.

## Step 2 — Strip instance state
After the go, delete:
- everything inside `consumers\` (leave the folder; a `.gitkeep` is fine if your tooling wants a
  non-empty dir),
- everything inside `change_requests\`,
- the entire `design\` folder,
- `project_progress.md`, `project_progress_archive.md`,
- `config.local.json` and `_archive\` **if they exist** (skip silently if not).

Do **not** touch `hooks\`, `agents\`, `scripts\`, `tests\`, `templates\`, `CLAUDE.md`,
`config.example.json`, or `.gitignore`.

## Step 3 — Reset MENU and regenerate README
**MENU.md** — keep the whole file; only blank each tool's "In use by" cell (a fresh hub has no
consumers). For the table row(s), set the last column to `—`.

**README.md** — replace it with this clean skeleton (adjust wording freely, but keep it free of any
reference to the source hub — no `design\` pointers, no source consumer names, no machine paths):

```markdown
# Tower Crane

A shared library of reusable Claude Code **tools** (hooks, subagents, scripts) *and* shared
**workflow conventions** that other projects on this machine opt into. An improvement made here,
once ratified, propagates to every consuming project — no copy-paste, no drift.

This hub was bootstrapped from the tower_crane pattern and starts **empty** — no consumers yet.

## Core ideas
- **Referenced, never copied ("float-on-HEAD").** A consumer holds a pointer to a shared tool or
  workflow rule, not a duplicate, so a change here propagates automatically.
- **Opt-in.** Nothing runs automatically *to* a project; each project opts in by adding a reference,
  and opts out by deleting it.
- **Consumer registry.** `consumers\` (one file per opted-in project) is the source of truth for
  who has opted into what.

## Get started
- **Set up this machine:** copy `config.example.json` → `config.local.json` and fill in `host_id` /
  `python_launcher` / `identity` (`shared_root` / `import_base` compute themselves automatically —
  leave that field as `""`). It's gitignored — non-secret pointers only; real auth stays in
  `gh auth login` / `git config`.
- **Onboard a new project:** `scripts\new_consumer.py --target-path <path> --project-name "<Name>"`.
- **Onboard an existing project:** copy `templates\register.md` into it and say
  *"read register.md and follow it."*
- **Check fleet health:** `scripts\check_tower_crane.py`.

## Where things live
| Path | What it is |
|---|---|
| `CLAUDE.md` | The Claude Code agent's per-session operating manual for this repo. |
| `MENU.md` | Catalog of shareable tools + their opt-in snippets. |
| `consumers\` | The consumer registry — one file per opted-in project (source of truth). |
| `templates\` | Shared workflow prose consumers `@import` + `register.md` / `bootstrap_hub.md` couriers + opt-in JSON under `optins\`. |
| `change_requests\` | The inbox — tickets from consumers and registration requests. |
| `scripts\`, `hooks\`, `agents\` | The executable tools plus maintainer tooling. |
| `config.example.json` / `config.local.json` | Per-machine config (`.example` committed, `.local` gitignored — each clone fills its own). |
| `project_progress.md` | Cross-session working state for this repo. |
```

## Step 4 — Regenerate the progress skeleton
Write a fresh `project_progress.md` (replace `<DATE>` with today's date, `YYYY-MM-DD`):

```markdown
# Project Progress

## Current Status
Fresh tower_crane hub bootstrapped <DATE> from the tower_crane pattern (via
`templates\bootstrap_hub.md`). Registry and change-request inbox are empty; no consumers yet.

## Next Up
- [ ] Onboard the first consumer — a new project via `scripts\new_consumer.py`, or an existing one
      via `templates\register.md`.

## Decisions
| Item | Status | Notes |
|---|---|---|

## Work Log (newest first — say "archive" anytime to move settled entries to project_progress_archive.md)
### <DATE> — Hub bootstrapped
Stood up this independent tower_crane hub from the pattern via `templates\bootstrap_hub.md`:
stripped the source hub's instance state (registry, ticket history, design docs, progress, git
history), re-pointed git at this hub's own remote, and filled `config.local.json` for this machine.
```

## Step 5 — Generalize CLAUDE.md's example references
`CLAUDE.md` is the governance pattern — keep it. It references the source hub's example consumer file
by name in a couple of places (e.g. "same format as `consumers\<something>.md`"). Since you deleted
that file, generalize those pointers to `consumers\<slug>.md` so nothing dangles. Change nothing
else in `CLAUDE.md`.

## Step 6 — Re-point git at YOUR hub
Give this hub a clean history and your own remote — the source hub's commit history is its instance
state, not yours.

1. Create an **empty GitHub repo you own** (no README/license, so the first push is clean). Note its
   URL.
2. Fresh history: remove the copied `.git` and re-init —
   ```
   rm -rf .git    # PowerShell: Remove-Item -Recurse -Force .git
   git init
   git branch -M main
   git remote add origin <YOUR repo URL>
   ```
   *(Preserving the source history instead is possible — keep `.git`, just `git remote set-url origin`
   — but the default is a clean start, consistent with "no trace of the source project.")*
3. Set this machine's git identity if not already global:
   `git config user.name "<you>"` / `git config user.email "<you@example.com>"`. Ambient only —
   never put credentials in a tracked file.

## Step 7 — Fill config.local.json for this machine
Read `templates\setup_machine.md` and follow it — the canonical, ask-don't-assume setup courier
(checks live for Python/git/`gh`, fills `config.local.json`, confirms with the user before writing).
Its Step 6 (identity) can reuse the `git_remote` you just set in Step 6 above.

`config.local.json` is gitignored (via the preserved `.gitignore`) — it never leaves this machine and
holds non-secret pointers only.

## Step 8 — Verify the pattern survived the strip
Run `scripts\check_tower_crane.py`. Expect: the golden suite (Pass A, `tests\`) green, and the
drift scan (Pass B) reporting **0 consumers** with nothing to validate — a clean, empty hub. If the
checker errors on an empty registry rather than passing cleanly, that's a real bug worth fixing before
you build on this hub.

## Step 9 — First commit and push
```
git add -A
git commit -m "Bootstrap fresh tower_crane hub"
git push -u origin main
```

## Step 10 — Finish
- Confirm the strip lists from Step 1 are gone and the skeletons are in place.
- **Do NOT delete `templates\bootstrap_hub.md`** — unlike `register.md`, it is part of the pattern
  and stays, so this hub can itself be replicated later.
- Your hub is live and empty. Onboard its first consumer with `scripts\new_consumer.py` (a new
  project) or `templates\register.md` (an existing one).
