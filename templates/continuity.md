<!--
Shared protocol piece: continuity.md (OPTIONAL, default-on — decision 9).
Home: ~\Documents\Claude\tower_crane\templates\continuity.md
Imported by a consumer's CLAUDE.md via:
  @~/Documents/Claude/tower_crane/templates/continuity.md
Generalized from the tower_crane repo's own checkpoint/resume/archive conventions, stripped
of tower_crane-specifics so it reads correctly in ANY consumer. The scaffolder imports this
by default; a project opts out by dropping the import line (a clean, per-piece choice). Keep
project-agnostic — refer to "this project", never a specific consumer name.

Two tiers (do NOT fork this file — one canonical piece serves both):
  - BASE (flat) is the default; small projects use it unchanged.
  - EXPANDED (phased) adds OPTIONAL sections for migration/build work with an ordered plan.
A project grows into the expanded tier by adding those sections to the SAME
`project_progress.md`. The filename is fixed at `project_progress.md` in both tiers — a phased
project does not get its own doc name. The checkpoint/resume/archive procedures below act on
whichever sections are present, so nothing forces the optional ones on a simple project.
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
single Decisions table. The procedures below read whatever is present.

### "checkpoint"

1. Update `project_progress.md`:
   - Refresh **Current Status** (base) and/or **Current Focus** (expanded) and **Next Up** so they
     describe only the PRESENT — where things stand now and what is still open. When something is
     finished, remove it from these sections; its detail belongs solely in the dated Work Log entry
     you add below. **Never let completed work accumulate here** — no "landed so far" recap, no
     growing list of done/`[x]` items. These sections load into context every session, so restating
     finished work is a recurring token cost, and it defeats archiving (moving Work Log entries out
     can't shrink the file while the same done-detail is duplicated up top). Done work has one home:
     its dated Work Log entry. (Ticking a **Phases** checkbox is terse status, not a recap — that
     stays.)
   - If the project uses **Phases**: update the phase checklist — tick completed stages, mark
     which phase is now active.
   - Move any settled decisions from Open → Locked: flip the status column (base) **or** move the
     row from `Decisions (Open)` to `Decisions (Locked)` (expanded).
   - If the project uses **To Reconcile**: strike items that were folded in this session; add any
     new inputs that surfaced.
   - Prepend **one** dated Work Log entry (what changed, what's next). Newest entry on top.
   - Do **not** prune or move older entries automatically — the Work Log stays complete until
     the user runs "archive".
2. Git: `git add -A && git commit -m "Checkpoint: <summary>" && git push`
   - If no repo/remote is found: stop and ask the user whether to set one up now, rather than
     skipping silently.
3. Confirm to the user: saved and pushed.
4. **Suggest archiving when the file has grown** (resource conservation): the whole of
   `project_progress.md` is read into context each session, so a long Work Log is a recurring
   token cost for history you're no longer actively using. If the file has grown past roughly
   **400 lines (~40 KB)**, or the Work Log holds many months of settled entries, *suggest* the
   user run "archive" to move old, settled entries out. This is only a prompt — archiving is
   always the user's explicit call (see below), never automatic. The cost is linear, so there's
   no hard cliff; this threshold is just where a one-time cleanup starts paying for itself.

### "archive" (user-initiated only — never automatic, never during "checkpoint")

1. List current Work Log entries — date + one-line title only, newest first.
2. Ask the user where to draw the cutoff. Do not guess. Wait for an explicit answer.
3. Move every entry at or before that cutoff into `project_progress_archive.md`, appended in
   chronological order (oldest first). Create the archive file if it doesn't exist yet.
4. Remove those entries from `project_progress.md`. Confirm what was archived. Only the **Work
   Log** is archived — Current Status/Focus, Next Up, Decisions, Phases, and To Reconcile are
   live state and stay in `project_progress.md`.

### "resume"

1. `git pull` (this project's own repo).
2. **Ask whether to also sync the shared tower_crane hub** — a per-session yes/no question, not
   a silent background pull: *"Also pull the shared tower_crane hub? (picks up new/fixed tools,
   runs a local compliance check, and clears any pending guidance.)"* On **yes**:
   - `git pull` inside the tower_crane hub clone — the same location this project's `@import`
     lines resolve to (see the filing protocol, mandatory for every consumer, if you need the
     exact path).
   - Then, from inside that same clone, run `scripts\check_tower_crane.py --write-guidance`
     (unfiltered, no `--consumer` flag — the hub's own per-machine `host:` scoping already
     limits what that write touches to consumers registered on this machine). Pure Python, zero
     AI cost, using whichever of `python3`/`python` this machine has.
   On **no**: skip both — this project's guidance may lag until a future `resume` says yes, or
   until the hub's own automation (if built) catches it on its own cadence.
3. **Check for shared-tools compliance guidance** — see the compliance protocol: if
   `COMPLIANCE_GUIDANCE.md` exists in the project root, surface it now (this is also where
   anything step 2's write-guidance just produced would show up).
4. Read `project_progress.md` — only the live-state sections your project uses: **Current
   Status** and/or **Current Focus**, **Next Up**, the **Decisions** (table, or the Locked/Open
   sections), the **active Phase** if the project is phased, and the **most recent Work Log
   entry** only. Skip settled Work Log history and anything already Locked.
5. State status and next step in 1–3 lines. Do not replay full history.
