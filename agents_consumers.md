# Adding / removing a consumer (AGENTS.md companion)

Full mechanics for the `"connect project"`, `"disconnect project"`, `"remove"`/`"uninstall"`, and
`"migrate consumer to reference-indirection"` triggers named in `AGENTS.md`'s Procedures section.
Read this file when any of those fire — it is not preloaded.

## Adding a consumer
**Trigger: "connect project".** Ask new-from-scratch vs. existing project first, then always ask
**local to this machine only, or available to all connected machines?** (`design\multi_machine_hub.md`
"Problem 2" — the answer is never assumed and never depends on how many machines the hub already
has). Either path, the consumer ends up in the registry (`consumers\<slug>.md`) and floats on this
repo's HEAD.
1. **New project from scratch** — `scripts\new_consumer.py --target-path <abs path> --project-name
   "<Full Title>" --scope local|multi_machine` (per the question above; default `local`). Writes ALL
   consumer files (`.claude\settings.json`, `CLAUDE.md` with `@import` lines, skeleton
   `project_progress.md`, `FIRST_RUN.md`) plus the registry entry. Defaults: opts into
   `consistency_check`, imports `filing` + `compliance` + `continuity`. Flags: `-Tools @()` for no
   hooks, `-NoContinuity` to skip, `-Force` to overwrite. Does NOT run git — the new project's first
   session does that via its `FIRST_RUN.md`.
2. **Existing (hand-copied) project, never Tower-Crane-shaped** — same `scripts\new_consumer.py`
   invocation as #1, pointed at the project's existing local folder, run directly from this hub
   session (register.md's old courier-and-ticket detour is retired — this used to require copying
   that file into the target project and filing a ticket back here from a separate session).
   `new_consumer.py` detects a `CLAUDE.md` with no `## Tower Crane In Use`
   heading and no protocol-piece `@import` line and treats it as a recognized, safe-to-automate
   shape: the entire existing file (project overview, any hand-added content) is left untouched
   and the live "Tower Crane In Use" / "Shared Workflow Protocol" sections are appended, the same
   way item 4's reconnect branch works. Before invoking it, inventory the project by hand first:
   read `.claude\settings.json` for any hook already pointing at `tower_crane\hooks\` and pass
   those tool names via `--tools` so they land in the registry's `opted_in:` list. Also ask **local
   to this machine only, or available to all connected machines?** the same as #1 (`--scope`).
   **Routing check first:** if the target `CLAUDE.md` already contains `## Tower Crane
   (disconnected)`, this is NOT this case — it's a previously disconnected project; route through
   item 4 instead. If it already carries live Tower Crane content but no registry entry, that's
   registry drift, not adoption — `new_consumer.py` refuses to guess and points at
   `troubleshoot_project_connection.md` instead of silently forcing a match.
3. **Already registered, connecting another machine** — same `new_consumer.py` invocation as #1,
   pointed at wherever this project lives on THIS machine. The slug collision is detected
   automatically and routes into an additive `hosts.<this_host_id>` merge instead of erroring or
   overwriting (`design\multi_machine_hub.md`'s locked slug-collision routing) — `scope`
   self-corrects to `multi_machine` the moment a 2nd host lands, regardless of what was asked at
   original registration. If the target folder already has files (a physical copy, a hand-recovered
   clone), the host-merge branch patches only what's stale in place — `CLAUDE.md`'s `@import`
   lines, `settings.json`'s hook command(s), and any drifted `.claude\skills\` stub — via
   `relocate.py`'s own regeneration logic, and never touches `project_progress.md` or (re)writes
   `FIRST_RUN.md`. If the target folder is empty and the registry has a `remote:` on record
   (`design\consumer_reconnect.md`), it's cloned from there before any scaffolding runs; pass
   `--no-clone` to scaffold a blank folder instead. If the target folder is empty and the registry
   has **no** `remote:` on record (an older registration, or the project was never pushed
   anywhere), **ask the user for the project's git remote URL**, then `git clone <url>
   <target-path>` directly before calling `new_consumer.py` — the folder is no longer empty at
   that point, so the same patch-in-place branch above handles it, and the registry-write step
   backfills `remote:` from the freshly cloned `.git\` automatically (seed-once, never overwrites
   an existing value), so future connects for this project skip the question. If the user has no
   remote either, fall back to asking them to get the files onto this machine themselves (copy or
   clone) before repeating this same invocation. Recovering a lost/corrupted local clone is the
   same flow — empty the broken folder first, then run this same invocation.
4. **Reconnecting a previously disconnected project** — same `new_consumer.py` invocation as #1,
   pointed at the project's existing local folder (its registry entry is gone — a full disconnect
   hard-deletes it — but the local files, including real project history, are still there).
   `new_consumer.py` detects the `## Tower Crane (disconnected)` marker in `CLAUDE.md`, strips just
   that section, and re-appends the live "Tower Crane In Use" / "Shared Workflow Protocol" sections
   — everything else in `CLAUDE.md` (the real project overview, any hand-added content) is left
   untouched, and the stale `TOWER_CRANE_DISCONNECT_NOTES.md` is deleted (superseded — the
   connection is live again). Never needs `--force`; this is a recognized shape, not the ambiguous
   collision that gate exists to protect against. A fresh registry entry is written, but the
   original `registered:` date is recovered where possible rather than always stamped with today
   (`design\connect_disconnect.md`'s "per-file principle reframe" — read from a surviving
   `TOWER_CRANE_DISCONNECT_NOTES.md`, else the oldest hub-git-log commit touching
   `consumers\<slug>.md`, else today as a last resort). The per-host `since:` date is still always
   today, since that genuinely reflects when *this host* connected. `FIRST_RUN.md`'s checklist (see
   below) only lists what a project in this position actually still needs — usually just
   re-accepting the import-approval dialog, since git/a remote/the overview are almost always
   already there.

**Every file `new_consumer.py` touches decides its own fate from its own most-direct signal — a
per-file model, not a shared classification tied to specific numbered items above**
(`design\connect_disconnect.md`'s "per-file principle reframe"): `.claude\settings.json` and
`.claude\skills\*` key off their own path's existence; `CLAUDE.md` decides its own content from
its own signal chain (does *this file* carry the disconnected marker, or does a surviving
`TOWER_CRANE_DISCONNECT_NOTES.md` prove it was connected before); `project_progress.md` keys on
its own presence alone (present → always preserved with a dated note, absent → skeleton built);
`TOWER_CRANE_DISCONNECT_NOTES.md` is deleted unconditionally the moment a connection succeeds,
regardless of which branch fired; `FIRST_RUN.md`'s overview-placeholder line asks whether
`CLAUDE.md` itself existed before this run, not the reconnect/adoption classification. It also
checks for an existing `.git\` and an existing `origin` remote at the target path before writing
the checklist: a `git init` line is only included if `.git\` is genuinely missing, a remote-setup
line is offered as optional only if none is configured. This covers every combination honestly —
a never-connected project someone already `git init`'d and pushed to GitHub by hand gets a
checklist with almost nothing left to do; a reconnecting project with git removed for some reason
gets told to reinitialize it, same as a brand-new one would.

Either path: run `scripts\check_tower_crane.py` to confirm the consumer validates clean.

## Disconnecting a consumer
**Trigger: "disconnect project"** — reciprocal with `"connect project"`. Runs
`scripts\disconnect_consumer.py --slug <slug> --mode this-only|all-but-this|all` from inside
`toolkit\`: it drops the target host(s)' `hosts.<id>` entries from the registry, and — for this
machine's own connection specifically — strips `CLAUDE.md`'s `@import` lines,
`.claude\settings.json`'s hook entries + the `Read` permission rule, and every
`.claude\skills\<name>\` directory from the local copy, then prints a close-out summary of exactly
what it found and removed. That summary is the authoritative record — relay it, don't predict it in
advance. Deliberately NOT touched: any `shared_resources\` adopted stub (its `hub-rel:` marker goes
stale, doesn't break) and `COMPLIANCE_GUIDANCE.md`'s broadcast section. Full design:
`design\connect_disconnect.md`.

Two things are required to run it — ask for whichever isn't already stated in the request:
1. **Which consumer.** Identify from the registry (`consumers\<slug>.md`) — never infer from a Next
   Up/Work Log entry or other conversational context.
2. **Which mode.** This machine only, every other machine (keep this one), or everywhere.

State the consumer, mode, and target host(s) back to the user, plus the reversibility note — no
dedicated undo, but running `"connect project"` again on the same path re-registers or host-merges
correctly (fresh `registered:`/`since:` date, re-clone if the local folder is also gone) — and get
explicit go-ahead before running.

## Removing this machine
**Trigger: "remove" / "uninstall"** — reciprocal with `setup_machine`. Reverses this machine's
setup entirely: disconnects every consumer connected here (this-only, so any other machine's own
connection to the same consumer is untouched), then clears this machine's own gitignored state
(`config.local.json`, `.claude\settings.local.json`, `.claude\self_hooks_status.md`,
`.claude\automation_state.json`, `.claude\skills\`). Never touches `.claude\hooks\` (tracked
personal content, not this hub's to delete) or the hub folder itself — physically deleting that,
if wanted, is a manual step afterward, the same "can't finish mid-session" shape
`setup_machine.md`'s own "Bootstrapping the outer hub" scenario already has.

**Before running: list every consumer that will be disconnected here, by name, and get explicit
go-ahead** — same discipline as above. State the reversal path honestly too: `setup_machine.md`
run again on this machine, then reconnecting whichever consumers are wanted via `"connect
project"` — a rebuild, not a restore.

Then run `scripts\remove_hub.py` (no args — operates on this machine via its own
`config.local.json`) from inside `toolkit\`. Full design: `design\connect_disconnect.md`.

## Migrating an already-connected host to reference-indirection
**Trigger: "migrate consumer to reference-indirection"** — a one-time, explicit action, distinct
from `"connect project"` on purpose: a command already run routinely on an already-connected
consumer shouldn't silently start rewriting shared, tracked content that affects every other
connected host too. Applies only to a consumer/host combination that's still on the old
direct-baked-path form (`design\consumer_reference_indirection.md`'s original "new connections
only" scope left an already-connected host on that form indefinitely — the recurring cross-host
skill-stub collision this closes, `design\grt_connectivity_audit.md` item (iii)).

**Before running: state exactly what will be rewritten and get explicit go-ahead** — CLAUDE.md's
`@import` lines collapse to the single pointer line, `.claude\settings.json`'s hook command(s)
switch to the dispatch-wrapper form, and every `.claude\skills\<name>\SKILL.md` stub regenerates to
pointer-indirection wording. All of that is shared, tracked content — every OTHER host still
connected to this consumer picks it up automatically on its own next `relocate.py`/`resume` pass,
no separate action needed there.

Then run `scripts\migrate_consumer_indirection.py --slug <slug>` from inside `toolkit\`. No-ops
cleanly (prints a message, changes nothing) if this host is already on pointer form. Run
`scripts\check_tower_crane.py` afterward to confirm the consumer still validates clean. Full
design: `design\grt_connectivity_audit.md` item (iii).
