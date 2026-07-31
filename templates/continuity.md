<!--
Shared protocol piece: continuity.md (Track 1, on-demand — design\directive_economy.md).
Home: ~\Documents\Claude\tower_crane\toolkit\templates\continuity.md
As of 2026-07-31 this file is no longer @imported directly (when continuity is adopted). A
consumer instead carries two thin skill stubs — .claude\skills\checkpoint\SKILL.md and
.claude\skills\archive\SKILL.md (sourced from toolkit\templates\skills\checkpoint\SKILL.md /
templates\skills\archive\SKILL.md) — whose bodies say to read this file and follow the matching
procedure below when the model recognizes a checkpoint- or archive-shaped moment. Float-on-HEAD
still holds — this file is the one canonical source both stubs always re-read live. Keep this
file project-agnostic — refer to "this project", never a specific consumer name.

The one part of the old continuity.md that must stay always-resident — resume, which fires
almost immediately in nearly every session, so lazy-loading it would pay the trigger-and-load
cost with none of the benefit — now lives in the separate, still-@imported
templates\continuity_resume_check.md. That file also carries the "Two tiers" (base/expanded)
explanation the "checkpoint" procedure below refers to; by the time checkpoint fires, resume has
already loaded it earlier in the same session.
-->

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
