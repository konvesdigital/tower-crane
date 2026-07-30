<!--
Shared protocol piece: filing.md (MANDATORY for every consumer — Track 1, on-demand).
Home: ~\Documents\Claude\tower_crane\toolkit\templates\filing.md
As of 2026-07-30 (design\directive_economy.md's pilot) this file is no longer @imported
directly. A consumer instead carries a thin skill stub at .claude\skills\filing\SKILL.md
(sourced from toolkit\templates\skills\filing\SKILL.md) whose body says to read this file in
full when the model recognizes a filing-shaped moment. Float-on-HEAD still holds — this file is
the one canonical source the stub always re-reads live. Keep this file project-agnostic — it
must read correctly from ANY consumer. Refer to "this project", never a specific consumer name.
Changes to this file go through the tower_crane change-request round-trip like any other shared
artifact.

The one part of the old filing.md that must stay always-resident (a resume-time
change_requests\ scan can't wait for the model to notice a filing-shaped moment) now lives in
the separate, still-@imported templates\filing_resume_check.md — see that file.
-->

## Reporting bugs & improvements in shared tools

This project uses shared Claude Code tools that live in a local **tower_crane** hub — the same
hub this file's own `@import` line (in this project's `CLAUDE.md`) points at. That hub is two
nested git repos in one folder: an outer, private repo, and an inner `toolkit\` repo that
actually holds the shared tools/templates (including this file). This file's own `@import` path
is home-relative and resolves inside `toolkit\`, wherever the hub actually sits on this machine;
there is no fixed conventional location or folder name to assume (this repo's own self-locating
install design — see `design\portability.md` if curious). Below, **"the hub root"** means the
outer folder — one level up from `toolkit\`, and where `change_requests\` actually lives — and
**"`toolkit\`"** means the inner folder your `@import` resolves into. Those files are owned by
the tower_crane hub, not by this project.

This ticket system covers **`toolkit\` tool work only** — fixes or new content in
`hooks\`/`scripts\`/`templates\`/`agents\` that changes Claude's deterministic behavior the
same way for every consumer. Private reference material, a pointer to a proprietary tool, or a
reusable `CLAUDE.md` pattern doesn't belong here at all — see `templates\shared_resources.md`
(if this project has opted in) for that separate, ticket-free channel.

**Never edit any existing file inside the hub root or `toolkit\`.** The only writes a consumer may
make there are **filing a change request** in the hub root's `change_requests\` folder (and,
during a round-trip, appending a verification line to a ticket you filed), or — if this project
has opted into `templates\shared_resources.md` — writing directly into the hub root's
`shared_resources\` folder per that file's own narrower rules. Every other file, in either
location, stays off-limits. If a shared tool has a bug, or you think of an improvement, you *file
a request* — you do not fix it here. Filing and fixing happen in two different repos and two
different sessions, which keeps each repo's git history honest. The tower_crane hub is the single
place a shared tool actually changes.

### How to file

1. Create a markdown file in **the hub root's** `change_requests\` folder — **not** inside
   `toolkit\` — named
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

   **Proposing new shared content** (a template or reference doc that doesn't exist yet, rather
   than a bug/improvement in something that already exists) doesn't fit the shape above — use
   `Type: proposal` instead:
   ```
   Status: OPEN
   Filed by: <this project's full name> — <YYYY-MM-DD>
   Tool: <what's being proposed, and where it would live>
   Type: proposal

   ## Use case
   ## Proposed content
   ## Where it lives
   ## Suggested test

   ## Round-trip log
   ```
   Same round-trip as any other ticket (only `Type: registration` skips it) — the shared repo
   creates the proposed content and you still verify before it closes.

   **Before filing a proposal whose content would live in `toolkit\`:** confirm it contains no
   real absolute paths, machine-specific detail, or client/project names — `toolkit\` tracks the
   public `konvesdigital/tower-crane` repo. If it does carry any of that, it isn't a `toolkit\`
   proposal at all: private reference material, a proprietary-tool pointer, or a reusable
   `CLAUDE.md` pattern belongs in `shared_resources\` instead (see `templates\shared_resources.md`,
   if this project has opted in) — written directly, no ticket, no round-trip. Only file a
   `Type: proposal` ticket here for content that's genuinely generic and public.
3. **From inside the hub root** — not `toolkit\`; `change_requests\` belongs to a different git
   repo with a different remote — `git add` the new ticket file, commit (e.g.
   `git commit -m "File ticket: <slug>"`), and `git push`. Filing isn't done until the ticket
   reaches the hub root repo's GitHub remote — an uncommitted file sitting on your own disk never
   reaches the shared side. This requires write access to that repo, not just read.
4. Do **not** apply the fix yourself, and do **not** edit the shared repo's progress doc. Your
   job ends at filing until the shared repo ships a fix.

### The round-trip — your side of it

A ticket has only two statuses, `OPEN` and `DONE`, and **`DONE` means *you* verified the fix**,
not that the shared repo applied one. The ticket stays **OPEN through the entire round-trip**.
Every hand-off appends one dated line to the ticket's `## Round-trip log` (newest at the
bottom).

**Finding which tickets need your attention at resume is handled by the always-resident
`filing_resume_check.md` piece** (imported alongside this skill, mandatory for every consumer) —
it scans the hub root's `change_requests\` folder on every `resume` and identifies anything
awaiting this project. This section covers what to do once it's found one: re-run its Suggested
test on your side:

- If it works: append `YYYY-MM-DD — <this project> verified PASS`. **Leave `Status: OPEN`** —
  the tower_crane agent flips it to `DONE` on its next session (closing authority stays there).
  Do not flip it yourself.
- If it still fails: append `YYYY-MM-DD — <this project> re-verified, still fails: <what>`. The
  ticket stays OPEN and the ball returns to the shared agent.

Either way, `git add`/`commit`/`push` that edit from inside the hub root — same as filing, an
unpushed verify line never reaches the shared side.

**Multi-user attribution:** if more than one person works in this project (or files against this
hub), name yourself alongside the project in the line — e.g. `<name> (<this project>) verified
PASS` — so the log stays legible with concurrent contributors. A single-person project can keep the
terser project-only form above.

You never mark a ticket `DONE`, never edit a ticket you didn't file (except to add a verify
line to one that names this project), and never touch shared tool files directly (that means
anything inside `toolkit\`).
