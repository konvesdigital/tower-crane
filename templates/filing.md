<!--
Shared protocol piece: filing.md (MANDATORY for every consumer).
Home: ~\Documents\Claude\tower_crane\templates\filing.md
Imported by a consumer's CLAUDE.md via:
  @~/Documents/Claude/tower_crane/templates/filing.md
Float-on-HEAD: edits here reach every consumer the next time it runs. Keep this file
project-agnostic — it must read correctly imported into ANY consumer. Refer to "this
project", never a specific consumer name. Changes to this file go through the tower_crane
change-request round-trip like any other shared artifact.
-->

## Reporting bugs & improvements in shared tools

This project uses shared Claude Code tools that live in a local clone of the **tower_crane**
hub — the same repo this file's own `@import` line (in this project's `CLAUDE.md`) points at.
That `@import` path is home-relative and resolves to wherever the hub clone actually sits on
this machine; there is no fixed conventional location or folder name to assume (this repo's
own self-locating install design — see `design\portability.md` if curious). Below, "the hub
clone" always means that location. Those files are owned by the tower_crane repo, not by this
project.

**Never edit any existing file inside the hub clone.** The only write a consumer may make
there is **filing a change request** in its `change_requests\` folder (and, during a
round-trip, appending a verification line to a ticket you filed). If a shared tool has a bug,
or you think of an improvement, you *file a request* — you do not fix it here. Filing and
fixing happen in two different repos and two different sessions, which keeps each repo's git
history honest. The tower_crane repo is the single place a shared tool actually changes.

### How to file

1. Create a markdown file in the hub clone's
   `change_requests\` folder named
   `YYYY-MM-DD_<tool>_<slug>.md`
   (e.g. `2026-07-17_consistency_check_param-false-positives.md`). The filename convention is
   the index — there is no separate index file.
2. Use this template. **The first line must be the Status line.**
   ```
   Status: OPEN
   Filed by: <this project's full name> — <YYYY-MM-DD>
   Tool: <shared file, e.g. hooks\consistency_check.py>

   ## Symptom / repro
   ## Root cause
   ## Proposed fix (non-binding)
   ## Suggested test

   ## Round-trip log
   ```
   The **Proposed fix is a suggestion, not a mandate** — the tower_crane agent validates it
   against every consumer (which this project can't see) and owns the final call. Make the
   Symptom/repro concrete enough to reproduce, and make the Suggested test something the shared
   agent (and later you) can actually run.
3. **From inside the hub clone**, `git add` the new ticket file, commit (e.g.
   `git commit -m "File ticket: <slug>"`), and `git push`. Filing isn't done until the ticket
   reaches the hub's GitHub remote — an uncommitted file sitting on your own disk never reaches
   the shared side. This requires write access to the hub's repo, not just read.
4. Do **not** apply the fix yourself, and do **not** edit the shared repo's progress doc. Your
   job ends at filing until the shared repo ships a fix.

### The round-trip — your side of it

A ticket has only two statuses, `OPEN` and `DONE`, and **`DONE` means *you* verified the fix**,
not that the shared repo applied one. The ticket stays **OPEN through the entire round-trip**.
Every hand-off appends one dated line to the ticket's `## Round-trip log` (newest at the
bottom).

**At session start (and on `resume`), scan
the hub clone's `change_requests\` folder for OPEN tickets that need this
project's attention.** Two kinds need it, and you catch both the same way — read each OPEN
ticket's **last** `## Round-trip log` line:

- a ticket **this project filed** whose latest line reads `… awaiting <this project> verify` —
  the shared repo shipped a fix and is waiting on you; **or**
- a **verify-request ticket that names this project** (`Relates to: <original>`) — filed when a
  shared fix affects more than one consumer, so each *other* consumer re-checks.

Skip tickets whose last line shows the ball is elsewhere (e.g. `awaiting <another project>
verify`, or a fix the shared agent still owns). For any ticket the scan surfaces, re-run its
Suggested test on your side:

- If it works: append `YYYY-MM-DD — <this project> verified PASS`. **Leave `Status: OPEN`** —
  the tower_crane agent flips it to `DONE` on its next session (closing authority stays there).
  Do not flip it yourself.
- If it still fails: append `YYYY-MM-DD — <this project> re-verified, still fails: <what>`. The
  ticket stays OPEN and the ball returns to the shared agent.

Either way, `git add`/`commit`/`push` that edit from inside the hub clone — same as filing, an
unpushed verify line never reaches the shared side.

**Multi-user attribution:** if more than one person works in this project (or files against this
hub), name yourself alongside the project in the line — e.g. `<name> (<this project>) verified
PASS` — so the log stays legible with concurrent contributors. A single-person project can keep the
terser project-only form above.

You never mark a ticket `DONE`, never edit a ticket you didn't file (except to add a verify
line to one that names this project), and never touch shared tool files directly.
