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

1. Host identity: read `shared_root:` from this project's own `.claude\hub_pointer.md`, then read
   `host_id` from `{shared_root}\config.local.json` — the same value and the same file the hub's
   own `resume` reads directly (`toolkit\AGENTS.md` step 1), just reached through one extra
   indirection hop (mirrors how `_hub_dispatch.py` locates the hub for hook calls). Never infer
   machine identity any other way (path, `hostname`, prior context). If `.claude\hub_pointer.md`
   doesn't exist, Tower Crane connection is not active on this machine for this project — do not
   attempt to determine which machine this is by any other means (path, hostname, prior context);
   it doesn't matter, since nothing host-specific applies while disconnected. (A consumer that
   predates pointer-indirection and never had this file also hits this branch — same skip, same
   reasoning.)
2. `git pull` (this project's own repo).
3. Check the shared tower_crane hub — both steps read-only, no gate needed, chained into one call
   (`design\command_procedure_audit.md`'s B1 audit re-run on consumer `resume`):
   `python "<hub root>\toolkit\scripts\consumer_resume_check.py"` (same `toolkit\` folder this
   file itself resolved through). Runs, in order, what used to be two separately prose-sequenced
   calls:
   - `update_toolkit.py --notify` (fetch + compare against the hub's last-reviewed baseline —
     never merges). If it reports an update, mention it, but do **not** `git pull` `toolkit\` from
     this project's session — that's the gated `update` action, run only in a session opened
     directly in the hub.
   - `check_tower_crane.py --write-guidance` (no `--consumer` flag — the hub's per-machine `host:`
     scoping already limits it). Pure Python, no pull required.
   - This checks only whether the **hub's own toolkit source** has fallen behind its public
     upstream — separate from whether **this project** has adopted everything the hub already
     offers. That's this project's own on-demand `update` skill (if adopted): say "update" anytime
     to pull in a hook, toolkit skill, or mandatory/default-on piece not yet picked up. This step
     never runs that scan.
4. If `COMPLIANCE_GUIDANCE.md` exists in the project root, surface it now (see the compliance
   protocol) — this is also where anything step 3's `--write-guidance` run just produced shows up.
5. Read `project_progress.md` — only the live-state sections your project uses: **Current
   Status**/**Current Focus**, **Next Up**, the **Decisions** (table or Locked/Open), the active
   **Phase** if phased, and the **most recent Work Log entry** only.
6. State status and next step in 1–3 lines, leading with the host identity from step 1 (when
   available — see that step's skip condition). Do not replay full history.

### "quick resume"

A thinner `resume`, for reopening a terminal seconds after closing one — the only way to actually
flush a long context window mid-session, typically right after a `checkpoint`. Skips step 2
(`git pull`) and steps 3–4 (the shared-hub update/compliance checks) entirely: a session reopened
moments after its own `checkpoint`'s push has nothing new to find. No tag or disclaimer noting
what was skipped. Use plain `resume` instead at the start of a day or after any gap long enough
that something could actually have changed.

1. Host identity: same read as `resume` step 1 above.
2. Read `project_progress.md` — same scope as `resume` step 5 above.
3. State status and next step in 1–3 lines, leading with the host identity from step 1 (when
   available).
