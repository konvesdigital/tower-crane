# Troubleshooting a broken project connection

Read this when `connect project` (`new_consumer.py`) or `disconnect project`
(`disconnect_consumer.py`) hits a fatal error and the obvious next step looks like either
abandoning the operation or forcing an overwrite that could destroy real project content. This is
**not** a deterministic fix — connections can break for more reasons than any script can
enumerate, and this file deliberately does not try to enumerate them as named cases
(`design\connection_diagnostics.md`'s reframe: `hooks\consistency_check.py`'s own report-don't-fix
split applied here — compute facts, let Claude reason about what they mean, rather than chasing an
open-ended set of shapes with more and more named branches).

**Before trying anything below:** never run `--force` (on `new_consumer.py`) as a first move. It
fully overwrites `CLAUDE.md` from the blank template, destroying any real project overview or
hand-added content. Every scenario below has a non-destructive path — reach for `--force` only
after those are ruled out, and only with the user's explicit go-ahead, per the standing
"actions with care" guidance (hard-to-reverse action, confirm first).

## Start here: read the fact table, don't guess

Both scripts' fatal-error paths now auto-invoke `check_tower_crane.py --diagnose` inline and print
its output ahead of the error (design\connection_diagnostics.md — wired 2026-08-13). If you're
reading this file because you saw one of those errors, the fact table already printed above it in
the same output — scroll up before running anything else. To run it by hand (standalone-reachable,
not only failure-triggered): `python scripts\check_tower_crane.py --diagnose --path <project path>
--slug <registry slug>` (either flag alone is fine if you only know one).

**The output is facts only — present/absent, no verdict, no fix.** Reasoning from those facts to a
remedy is this file's job, done below, not the script's.

### How to read the fact table: durable history first, current state second

The fact table is split into two categories, printed in this order on purpose:

- **Category B — durable git history.** Tower Crane's own commits follow known message patterns
  (`"Tower Crane: disconnected via 'disconnect project' ..."`, `"Checkpoint: ..."`,
  `"Archive: ..."`) in the consumer's own repo, and `consumers/<slug>.md`'s history in the hub's
  own repo. These survive even after someone later hand-deletes the files those commits touched —
  a deleted `project_progress.md` doesn't erase the commit that once modified it.
- **Category A — Tower-Crane-specific current-state files.** `CLAUDE.md`'s headings/imports,
  `.claude\settings.json`'s hook entries, `.claude\skills\` contents, `FIRST_RUN.md`/
  `TOWER_CRANE_DISCONNECT_NOTES.md` presence, the hub's own `consumers\<slug>.md` and any stray
  `change_requests\` ticket. Ordinary files — exactly why they're the *less* reliable half in the
  scenario this file exists for: someone manually deleted or edited something instead of using
  `connect project`/`disconnect project`, or a merge/reset dropped a piece.

**Prefer Category B over Category A when reconstructing *what happened*; use Category A only to
establish *what's true right now*.** A text file reflects only its latest edit; git log
accumulates every edit and is far harder to silently and fully erase. If the two categories
disagree — say, Category A shows a live `## Tower Crane In Use` heading with no registry entry,
but Category B shows a `"Tower Crane: disconnected"` commit in the consumer's own repo more recent
than any registration-shaped commit in the hub's `consumers/<slug>.md` history — trust the
disconnect commit's story over the stale heading, and go find out why the heading wasn't cleaned
up (a pre-2026-08-13 disconnect, before the post-disconnect legibility fix existed, is one known
reason — see the worked incident below).

## Worked incidents (priors, not prescriptions)

These are real cases that produced this file's more specific guidance below. Read them as
**examples of how to reason from the fact table**, not as a checklist to force-fit a new case
against — the actual shape you're looking at may not match either one.

**Reconnect hit a shape `new_consumer.py` didn't recognize (2026-08-13).** Reconnecting a
previously-disconnected consumer produced a `CLAUDE.md` with the `## Tower Crane In Use` /
`## Shared Workflow Protocol` headings present, but the `@import` lines under them already
stripped, and no `## Tower Crane (disconnected)` marker either. None of `new_consumer.py`'s three
deterministic branches (host-merge, reconnect-via-marker, adoption-via-no-heading) fit. The fact
table would have shown: Category A — heading present, no live import, no marker (an
unrecognized combination); Category B — a `"Tower Crane: disconnected"` commit in the consumer's
own repo. Reasoning from B: this project *was* disconnected via the real command, and the marker
mechanism just didn't exist yet at the time that disconnect ran (it was built *from* this exact
incident afterward — `design\connect_disconnect.md`'s post-disconnect legibility fix). Once you know that,
the remedy is obvious and safe: treat it as a reconnect (strip the stale heading pair, let
`new_consumer.py --force` — or, after the legibility fix landed, an ordinary reconnect run —
re-append live sections), never a blind `--force` overwrite from scratch.

**Registry entry missing but `CLAUDE.md` still looks live.** This can't happen through normal use
of the Tower Crane tools — `new_consumer.py` and `disconnect_consumer.py` always write local
content and the registry entry together, in the same run. Reaching this state means something
bypassed them with a direct git/file operation on `consumers\<slug>.md`: hand-deleted outside
`disconnect project`, a merge/rebase conflict resolved by dropping the entry, or a
`git reset --hard` / `checkout <old-sha> -- consumers/` that reverted past the registration commit
and got pushed. The fact table's Category A would show live `## Tower Crane In Use` content and no
`consumers/<slug>.md`; Category B (`git log -- consumers/<slug>.md` in the hub root) is the
remedy's starting point:
1. **Check git history first.** If the deleting commit is still reachable (nothing force-pushed
   over it), restore the exact original entry: `git show <sha>:consumers/<slug>.md >
   consumers/<slug>.md`.
2. **If history doesn't have it** (the project was hand-edited into Tower Crane shape without ever
   going through `new_consumer.py`): hand-author a minimal valid entry. Copy the shape from an
   existing `consumers\*.md` file. Fill it in by inventorying the actual project — read
   `CLAUDE.md`'s `@import` lines for what belongs under `imported:`, read
   `.claude\settings.json`'s hooks for what belongs under `opted_in:`.

Once a registry entry with the right `hosts.<host_id>` block exists: `disconnect project` runs
normally again, and `connect project` routes into the existing, already-safe host-merge branch
(patches only stale `@import` lines in place) — since the content is probably already correct,
this will most likely just report "already current" and do nothing further.

**Verify any repair**: run `scripts\check_tower_crane.py` (the ordinary Pass A/B run, not
`--diagnose`). Pass B compares the registry's declared `opted_in`/`imported` against the project's
actual `settings.json`/`CLAUDE.md` — any mismatch between what was hand-authored and what's really
there surfaces as a deviation finding, which serves as a free correctness check on the repair.

## What's auto-handled vs. what lands here

`new_consumer.py` auto-handles three shapes of an existing `CLAUDE.md`, no `--force` needed for
any of them: no registry entry *and* no Tower Crane content at all (adoption — `register.md`'s old
target case, subsumed 2026-08-12), no registry entry *and* the `## Tower Crane (disconnected)`
marker (reconnect), and a registered consumer connecting another host (host-merge). Anything else —
live `## Tower Crane In Use` / protocol-piece `@import` lines already present, but no
`consumers\<slug>.md` entry to explain them — falls through to the `--force` guard rather than
being auto-resolved: the local content is probably already correct, it's the registry that's out
of sync, and guessing wrong here risks silently adopting content from an unrelated project. That's
registry drift — see the worked incident above.

## Wired in

`new_consumer.py`'s and `disconnect_consumer.py`'s fatal-error paths auto-invoke
`check_tower_crane.py --diagnose` and print its fact table inline (2026-08-13,
`design\connection_diagnostics.md`), ahead of naming this file. Not yet built: a
`"fix connection"` trigger that reads this file and runs `--diagnose` proactively before any error
is even hit — a plausible future extension, not scoped yet.
