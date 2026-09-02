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
tickets that need this project's attention. Run (`design\command_procedure_audit.md`'s A4 finding
— the consumer-side port of the hub's own A3 fix, same idea: don't re-derive a categorization a
script already computes exactly):

```
<python_launcher> "<hub root>\toolkit\scripts\ticket_scan.py" --project "<this project's full
name>" "<this project's registry slug>" [--json]
```

Pass every form this project is known by — its full/display name (matching the `Filed by:`
convention) and its registry slug at minimum, plus any abbreviation this project has actually
seen used in a ticket before (e.g. from a prior round-trip log entry) — a single form is not
reliable on its own (real ticket text mixes all three). This prints every OPEN ticket that
mentions any of those strings, each already categorized (`awaiting_consumer`, `no_activity`,
`still_fails`, `verified_pass`, …) using the exact rule below, instead of hand-deriving that from
the raw `## Round-trip log` text.

Three categories need this project's attention now:

- `awaiting_consumer` — the ball may be in this project's court. **Still open the ticket and
  confirm its own last `## Round-trip log` line actually names this project** before acting — the
  script's `--project` filter is a coarse text match (a ticket can legitimately mention more than
  one consumer, e.g. a cross-consumer verify-request affecting several projects), so a hit means
  "plausibly relevant," not "confirmed, act now." This is the one residual manual step the script
  doesn't eliminate.
- a **verify-request ticket that names this project** (`Relates to: <original>`) — same
  confirm-before-acting step as above.
- `unknown_state` — the log has real activity the script couldn't classify; it deliberately
  declines to guess rather than mis-file it as "nothing to do." Open the ticket and read the actual
  entry — it's often the shape a diverged-from-proposal or converged-with-another-ticket closing
  note takes (the hub's `agents_change_requests.md`, "What a ticket actually is"), and may name a
  *different* Suggested test than the one the ticket originally shipped with. Same
  confirm-before-acting step as above.

Every other category (`no_activity`, `still_fails`, `verified_pass`) on a filtered hit means the
ball is elsewhere (the shared agent's turn, or already handled) — skip.

If the scan surfaces anything, use the `filing` skill's round-trip procedure to respond (re-run
the Suggested test, append a verify/re-verify line, `git add`/`commit`/`push` from the hub root).
Do not flip a ticket's `Status` yourself — that stays the shared repo's call.
