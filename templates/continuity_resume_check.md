<!--
Shared protocol piece: continuity_resume_check.md (OPTIONAL, default-on when continuity is
adopted — decision 9). Home: ~\Documents\Claude\tower_crane\toolkit\templates\continuity_resume_check.md
Imported by a consumer's CLAUDE.md via:
  @~/Documents/Claude/tower_crane/toolkit/templates/continuity_resume_check.md
Split out of continuity.md on 2026-07-31 (design\directive_economy.md's "continuity.md: split
three ways" — resume stays Track 2, checkpoint and archive both move to Track 1 skills). This is
the one piece that fires almost immediately in nearly every session, so it stays a plain
always-resident import — deferring it to a skill trigger would pay the trigger-and-load cost
with none of the laziness benefit. It also carries the "Two tiers" explanation, since resume is
what decides which shape a given project's `project_progress.md` uses. Everything else —
checkpoint, archive — lives in Track-1 skills (project-local .claude\skills\checkpoint\SKILL.md /
.claude\skills\archive\SKILL.md, each pointing at the still-canonical templates\continuity.md).
Keep this file terse and project-agnostic — refer to "this project", never a specific consumer
name.
-->

## Session continuity

Source of truth for cross-session state is **`project_progress.md`** in the project root — this
filename in **both** tiers below; a phased project does not rename it. At session start read
only the sections your project actually uses (see the tier that fits), and do not re-derive
facts already logged there.

### Two tiers — pick the shape that fits the work

Cross-session state lives in one `project_progress.md`. Use the **base** shape by default; add
the **expanded** sections only when the work is genuinely multi-phase. Adding them is just
writing more of the same file — no new import, no rename, no opt-in flag.

**Base (default — simple projects).** Four sections:
- **Current Status** — where things stand *now*, in prose. Present state only — not a recap of
  finished work (that lives in the Work Log).
- **Next Up** — the concrete next step(s) still open.
- **Decisions** — a table with an Open → Locked status column.
- **Work Log** — dated entries, newest on top. The single home for completed-work detail.

**Expanded (optional — phased migration/build work).** Everything a base project has, plus:
- **Current Focus** — a short narrative *distinct from Next Up*: it explains **why** the next
  step is next and what it gates. Next Up is the terse action; Current Focus is the reasoning
  and the standing frame around it. (In the expanded tier this often replaces the flat "Current
  Status" as the top-of-file orientation.)
- **Phases** — the ordered plan as a checklist of stages, so partial progress across sessions is
  legible at a glance (which phase is active, what's done, what's next).
- **Decisions split into `Decisions (Locked)` and `Decisions (Open)`** — instead of one table
  with a status column. Locked decisions are standing constraints: **do not re-litigate a Locked
  decision without explicit sign-off.** Open decisions are still in play. The split keeps that
  "settled vs. live" emphasis the single table loses.
- **To Reconcile** — a backlog of scoped inputs still to fold in (external TODO files, handoff
  notes, findings from other work) that a large migration accumulates and must not silently drop.

A project may adopt any subset — e.g. add just **Phases** and a **Current Focus** and keep the
single Decisions table. The procedures below (and the "checkpoint"/"archive" skills, when the
model reaches for them) read whatever is present.

### "resume"

1. `git pull` (this project's own repo).
2. **Check the shared tower_crane hub for updates and compliance guidance** — both steps below are
   read-only from this project's point of view (neither pulls or mutates the hub), so there's no
   yes/no gate needed the way an actual pull would require:
   - The hub is two nested git repos in one folder: an outer, private repo (nothing this project
     imports lives there) and an inner `toolkit\` repo that actually holds the shared tools/
     templates this project imports — the same location this project's `@import` lines resolve to
     (see the filing protocol, mandatory for every consumer, if you need the exact path; `toolkit\`
     is what's named there).
   - From inside the hub's `toolkit\` folder, run `python scripts\update_toolkit.py --notify` (a
     plain fetch + comparison against the hub's own last-reviewed baseline — never merges
     anything). If it reports an update is available, mention it to the user, but do **not** `git
     pull` `toolkit\` from this project's own session — reviewing and pulling it is the gated
     `update` action, which only runs in a Claude Code session opened directly in the hub (the
     diff-review procedure lives in the hub's own `CLAUDE.md`, not here). Pulling it from here
     would bypass that trust-review gate.
   - Then, from that same `toolkit\` folder, run `scripts\check_tower_crane.py --write-guidance`
     (unfiltered, no `--consumer` flag — the hub's own per-machine `host:` scoping already limits
     what that write touches to consumers registered on this machine). This runs against whatever
     version of the checker is already present — no pull required. Pure Python, zero AI cost,
     using whichever of `python3`/`python` this machine has.
3. **Check for shared-tools compliance guidance** — see the compliance protocol: if
   `COMPLIANCE_GUIDANCE.md` exists in the project root, surface it now (this is also where
   anything step 2's `--write-guidance` run just produced would show up).
4. Read `project_progress.md` — only the live-state sections your project uses: **Current
   Status** and/or **Current Focus**, **Next Up**, the **Decisions** (table, or the Locked/Open
   sections), the **active Phase** if the project is phased, and the **most recent Work Log
   entry** only. Skip settled Work Log history and anything already Locked.
5. State status and next step in 1–3 lines. Do not replay full history.

### "quick resume"

A deliberately thinner `resume`, for reopening a terminal seconds after closing one — the only way
to actually flush a long context window mid-session, since nothing invoked from inside a session
can flush that same session. Typically right after a `checkpoint`. Skips step 1 (`git pull`) and
step 2-3 above (the shared-hub update/compliance checks) entirely, on the reasoning that a session
opened moments after its own `checkpoint`'s push has nothing new to find. No tag or disclaimer
noting what was skipped — the point is speed back into the work that was just interrupted, not a
staleness warning. Use plain `resume` instead at the start of a day or after any gap long enough
that something could actually have changed.

1. Read `project_progress.md` — same scope as `resume` step 4 above.
2. State status and next step in 1–3 lines. Do not replay full history.
