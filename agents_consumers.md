# Adding / removing a consumer (AGENTS.md companion)

Full mechanics for the `"connect project"`, `"disconnect project"`, and `"remove"`/`"uninstall"`
triggers named in `AGENTS.md`'s Procedures section. Read this file when any of those fire — it is
not preloaded.

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
2. **Existing (hand-copied) project** — the human copies `templates\register.md` into that
   project's root and tells its agent to follow it; that agent swaps pasted workflow prose for
   `@import` lines and files a `register` ticket here (per `agents_change_requests.md`'s
   "Registration tickets" section — that's where the local/multi_machine question actually gets
   asked and recorded, since the consumer-side session filing the ticket has no `config.local.json`
   access to know its own `host_id`).
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

Either path: run `scripts\check_tower_crane.py` to confirm the consumer validates clean.

## Disconnecting a consumer
**Trigger: "disconnect project"** — reciprocal with `"connect project"`. Ask which mode if not
already stated: **this machine only**, **every other machine** (keep this one), or **everywhere**.

**Before running anything: show exactly what will be removed and get explicit go-ahead.** Name the
consumer, the mode, which host(s) will be dropped from the registry, and — for this machine's own
connection specifically — which local files in the consumer's own project folder will be stripped
(`CLAUDE.md`'s `@import` lines, `.claude\settings.json`'s hook entries + the `Read` permission
rule, every `.claude\skills\<name>\` directory). State the reversibility honestly: there's no
dedicated undo, but running `"connect project"` again on the same path is the practical way back —
it re-registers or host-merges correctly, just with a fresh `registered:`/`since:` date rather than
restoring the old one, and a re-clone if the local folder is also gone. Don't imply a safety net
that isn't actually there. Only proceed once the user has clearly said yes.

Then run `scripts\disconnect_consumer.py --slug <slug> --mode this-only|all-but-this|all` from
inside `toolkit\`. Deliberately NOT touched (say so in the summary, don't just skip silently): any
`shared_resources\` adopted stub (its `hub-rel:` marker goes stale, doesn't break) and
`COMPLIANCE_GUIDANCE.md`'s broadcast section. Full design: `design\disconnect.md`.

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
`config.local.json`) from inside `toolkit\`. Full design: `design\disconnect.md`.
