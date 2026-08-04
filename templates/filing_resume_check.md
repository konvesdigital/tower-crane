<!--
Shared protocol piece: filing_resume_check.md (MANDATORY for every consumer - Track 2, always
resident). Home: ~\Documents\Claude\tower_crane\toolkit\templates\filing_resume_check.md
Imported by a consumer's CLAUDE.md via:
  @~/Documents/Claude/tower_crane/toolkit/templates/filing_resume_check.md
Track 2 half of filing.md: the resume-time ticket scan, which can't wait for the model to notice a
filing-shaped moment. Everything else - how to file a new ticket, round-trip verify mechanics -
lives in the `filing` skill (project-local .claude\skills\filing\SKILL.md, pointing at
templates\filing.md), loaded only when actually needed. Keep this file terse and project-agnostic.

This file explains how to use the mechanism it covers. `capability_relationships` explains how
this mechanism works and how it relates to other mechanisms.
-->

## Change-request ticket scan (resume)

At session start, and on every `resume`, scan the hub root's `change_requests\` folder for OPEN
tickets that need this project's attention. Read each OPEN ticket's **last** `## Round-trip log`
line — two kinds need this project now:

- a ticket **this project filed** whose latest line reads `… awaiting <this project> verify`; or
- a **verify-request ticket that names this project** (`Relates to: <original>`).

Skip tickets whose last line shows the ball is elsewhere (e.g. `awaiting <another project>
verify`, or a fix the shared agent still owns).

If the scan surfaces anything, use the `filing` skill's round-trip procedure to respond (re-run
the Suggested test, append a verify/re-verify line, `git add`/`commit`/`push` from the hub root).
Do not flip a ticket's `Status` yourself — that stays the shared repo's call.
