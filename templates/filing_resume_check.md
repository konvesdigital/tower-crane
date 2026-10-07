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

The person operating this project and the person operating the tower_crane hub are the same
individual, in a different session — not two parties handing tickets back and forth. A ticket you
find here `OPEN` and untouched is that same operator's own earlier note to their future hub self,
not a request pending from someone else; a ticket you find already `DONE`, or carrying a round-trip
entry this session didn't write, most likely means the operator took a manual action in the hub
(or another session of this project) that this session simply has no visibility into — treat that
as expected, not as something to flag or second-guess.

At session start, and on every `resume`, `consumer_resume_check.py` step 4 runs the scan of the hub
root's `change_requests\` folder (name and slug taken from the registry); read its output. Never
list, grep, or `cat` that folder by hand. Outside `resume`, or for `--json`, run the command below
(the consumer-side port of the hub's own scan fix: a script computes the categorization exactly):

```
<python_launcher> "<hub root>/toolkit/scripts/ticket_scan.py" --project "<this project's full
name>" "<this project's registry slug>" [--json]
```

Pass every form this project is known by — its full/display name (matching the `Filed by:`
convention) and its registry slug at minimum, plus any abbreviation this project has actually
seen used in a ticket before (e.g. from a prior round-trip log entry) — a single form is not
reliable on its own (real ticket text mixes all three). This prints every OPEN ticket that
mentions any of those strings, each already categorized (`awaiting_consumer`, `no_activity`,
`still_fails`, `verified_pass`, ...) using the exact rule below, instead of hand-deriving that from
the raw `## Round-trip log` text.

The scan then ends with a `needs this project's attention` list. Each entry in it is one of three
kinds — `awaiting_consumer` (the ball may be in this project's court), `verify_request` (a
hub-filed cross-consumer verify ticket), or `unknown_state` (the log has real activity the script
couldn't classify; often a diverged-from-proposal or converged-with-another-ticket closing note,
see the hub's `agents_change_requests.md` "What a ticket actually is", and it may name a
*different* Suggested test than the ticket shipped with) — and prints, for each: the ticket's
absolute path, its last log line verbatim, and `names this project: yes|NO`, which the script
computes from the ticket's last log entry (or, for a verify-request with no log yet, its Suggested
test section). `yes` means the ticket is waiting on this project; `NO` means it only mentions this
project somewhere, so leave it alone. The coarse `--project` text match is why a hit can still say
`NO`.

On `resume`, report every `yes` entry on the `Needs you` line (file name plus the last log line as
printed) and stop there: running a ticket's Suggested test and appending the verify line happens
only when the operator asks. To read a ticket in full, use the `Read` tool on the absolute path the
scan printed.

Every other category (`no_activity`, `still_fails`, `verified_pass`) on a filtered hit means the
next move belongs to a hub session, or the ticket's already handled — skip.

When the operator asks you to act on a `yes` entry, use the `filing` skill's round-trip procedure (re-run
the Suggested test, append a verify/re-verify line, commit via `checkpoint_git.py` from the hub
root — see the `filing` skill, never raw git directly).
Don't flip a ticket's `Status` yourself on your own judgment — that default exists because this
session lacks the hub's cross-project context, not because some other party owns the decision.
The one exception: the operator directly instructs you to close it (an "operator override" — see
the `filing` skill for the logging convention). That's not overriding someone else's authority;
it's the same operator you're already taking instructions from, settling it themselves.
