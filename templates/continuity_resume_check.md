<!--
Shared protocol piece: continuity_resume_check.md (OPTIONAL, default-on when continuity is
adopted). Home: ~\Documents\Claude\tower_crane\toolkit\templates\continuity_resume_check.md
Imported by a consumer's CLAUDE.md via:
  @~/Documents/Claude/tower_crane/toolkit/templates/continuity_resume_check.md
Track 2 (always-resident) half of continuity.md: resume/quick resume + the "Two tiers"
explanation, since resume decides which tier a project uses. `checkpoint`/`archive` are Track-1
skills (.claude\skills\checkpoint\SKILL.md / archive\SKILL.md), each pointing at the still-canonical
templates\continuity.md. Keep this file terse and project-agnostic — refer to "this project",
never a specific consumer name.

This file explains how to use the mechanism it covers. `capability_relationships` explains how
this mechanism works and how it relates to other mechanisms.
-->

## Session continuity

Source of truth: **`project_progress.md`** in the project root — same filename in both tiers below.
At session start read only the sections your project's tier uses, and don't re-derive facts
already logged there.

### Two tiers — pick the shape that fits the work

Use the **base** shape by default; add **expanded** sections only when the work is genuinely
multi-phase. Adding them is just writing more of the same file — no new import, no rename, no
opt-in flag.

**Base (default).** Four sections: **Current Status** (present state only — not a recap of
finished work, that's the Work Log), **Next Up** (the concrete next step(s)), **Decisions** (a
table, Open → Locked), **Work Log** (dated entries, newest on top — the single home for
completed-work detail).

**Expanded (phased migration/build work).** Everything Base has, plus: **Current Focus** (why the
next step is next and what it gates — distinct from Next Up's terse action), **Phases** (the
ordered plan as a checklist, so partial progress is legible at a glance), **Decisions split into
`(Locked)`/`(Open)`** instead of one table (don't re-litigate a Locked decision without explicit
sign-off), **To Reconcile** (a backlog of scoped inputs — handoff notes, external TODOs — not yet
folded in).

A project may adopt any subset. The procedures below (and the `checkpoint`/`archive` skills, when
reached) read whatever is present.

### "resume"

**Run-sheet — applies to every command issued while executing `resume`.**
- Make exactly these three tool calls, in this order, one at a time (each finishes before the next
  starts): **A.** `Read` on `.claude\hub_pointer.md`. **B.** `git pull`, as one bare command.
  **C.** `consumer_resume_check.py`, as one bare command (below). Every later file read uses the
  `Read` tool on an absolute path.
- The only Bash commands are B and C. Do not use `cd`, pipes, `cat`, `ls`, `grep`, `head`, `tail`,
  or `;`/`&&` chaining. To find or open a file use `Read`, `Glob` or `Grep`; never list or grep the
  hub's `change_requests\` folder (step 3's output already contains everything resume needs from it).
- If the classifier returns "no verdict" for B or C, retry that one command once, unchanged. If it
  still fails, continue and name the step that didn't run on the `Needs you` line.

1. Call A: read `shared_root:` from this project's own `.claude\hub_pointer.md`. If that file
   doesn't exist, Tower Crane connection is not active on this machine for this project — skip
   steps 2-3, do not try to determine the machine by any other means (path, hostname, prior
   context), and report `Host: not connected` on line 1 of step 5's block. (A consumer that predates
   pointer-indirection and never had this file takes this same branch.)
2. Call B: `git pull` (this project's own repo).
3. Call C: `python "<shared_root>/scripts/consumer_resume_check.py" --project-root "<this project's
   absolute root, forward slashes>"` (`<shared_root>` is the hub's `toolkit\` folder). It is
   read-only, runs after the pull on purpose, and prints: a `Host:` line (the machine identity,
   read from the hub's `config.local.json` — never infer it any other way), six numbered
   sections, and a final `RESUME SUMMARY` block. Read all of it. The sections:
   1. `update_toolkit.py --notify --consumer` — whether the hub's own toolkit source has fallen
      behind its public upstream (never merges). If it reports that, mention it but do **not**
      `git pull` `toolkit\` from this project's session — that's the gated `update` action, run
      only in a session opened directly in the hub. This is separate from whether **this project**
      has adopted everything the hub offers: that's this project's own on-demand `update` skill
      (say "update" anytime); resume never runs that scan.
   2. `check_tower_crane.py --write-guidance --consumer <slug>` — checks this project and writes
      `COMPLIANCE_GUIDANCE.md` if there are findings.
   3. `readiness.py` — what this project still needs on this machine. A `[TODO]`/`[UNKNOWN]` line
      is the user's to act on: report it, don't fix it unasked. `[HUB-MISMATCH]` means the hub's
      registry disagrees with this machine: point the user at `"connect project"` in the hub.
   4. `ticket_scan.py --project <name> <slug>` — open hub tickets; the closing `needs this
      project's attention` list is the one to act on, per `filing_resume_check.md`.
   5. `shared_resource_resume_check.py` — adopted shared-resource references (broken/drifted);
      interpret per `shared_resources_resume_check.md`.
   6. `resume_digest.py` — `project_progress.md`'s live-state sections (Current Status, Current
      Focus, Next Up, Decisions, Phases, newest Work Log entry), stating which sections are absent,
      then a `STATUS:` and a `NEXT:` line.
4. If the `RESUME SUMMARY` line `compliance guidance file` says PRESENT, `Read` the path it gives
   and surface it now (see the compliance protocol). That summary line is the only existence
   check; do not `Glob` for the file.
5. Output exactly three lines, then stop:
   - `Host: <Host line from step 3> | git: <already up to date | pulled | failed: <reason>> | checks: <clean | N area(s) flagged>`
   - `Needs you: nothing` — or, if any `RESUME SUMMARY` line is not clean, a `;`-separated list with
     one entry per flagged line: the area, then what it needs in a few words (a ticket by file
     name plus its `last log line` text; a `[TODO]` line; a hub-behind-upstream notice; guidance
     file present; a step that didn't run).
   - `Next: <the NEXT: line from section 6, copied as printed>`
   Resume reports and stops: do not begin the `Next` item, do not open `project_progress.md`
   (section 6 is the read of it; a `[truncated: …]` marker names the exact `Read` offset/limit to
   use only if the operator asks for that section), do not run any ticket's Suggested test, and do
   not replay history.

### "quick resume"

A thinner `resume`, for reopening a terminal seconds after closing one — the only way to actually
flush a long context window mid-session, typically right after a `checkpoint`. Skips `git pull` and
the whole `consumer_resume_check.py` chain except the digest: a session reopened moments after its
own `checkpoint`'s push has nothing new to find. No tag or disclaimer noting what was skipped. Use
plain `resume` instead at the start of a day or after any gap long enough that something could
actually have changed. The run-sheet above applies, with these two calls in this order:

1. `Read` on `.claude\hub_pointer.md` (no file → output the one line `Host: not connected` and
   stop).
2. `python "<shared_root>/scripts/resume_digest.py" --project-root "<this project's absolute root,
   forward slashes>"` as one bare command; read all of it.
3. Output exactly two lines, then stop: `Host: <the digest's Host line>` and
   `Status: <the STATUS: line> | Next: <the NEXT: line>`, both copied as printed.
