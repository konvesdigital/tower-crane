<!--
Shared protocol piece: continuity.md (Track 1, on-demand).
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

This file explains how to use the mechanism it covers. `capability_relationships` explains how
this mechanism works and how it relates to other mechanisms.
-->

### "checkpoint"

1. Update `project_progress.md`:
   - **Fold in what changed this session** — edit the existing text of **Current Status** (base)
     and/or **Current Focus** (expanded) and **Next Up** in place (update or delete a stale fact) to
     match what's true right now, or add a line only for something this session discovered that
     doesn't already fit an existing one. Never append a bullet narrating what this session did;
     that's the dated Work Log entry's job, even for something still true right now. A session that
     changed nothing about present-tense reality needs no edit to these sections at all (a Work Log
     entry still always gets added). Do not re-scan the whole section for calcified or misplaced
     content here — that full audit (the Inclusion Test) is `"archive"`'s job below, not paid at
     every checkpoint. (Ticking a **Phases** checkbox is terse status, not a recap — that stays.)
   - If the project uses **Phases**: update the phase checklist — tick completed stages, mark
     which phase is now active.
   - Move any settled decisions from Open → Locked: flip the status column (base) **or** move the
     row from `Decisions (Open)` to `Decisions (Locked)` (expanded).
   - If the project uses **To Reconcile**: strike items that were folded in this session; add any
     new inputs that surfaced.
   - Prepend **one** dated Work Log entry, newest on top, in this fixed shape: a header line
      `**YYYY-MM-DD — <host_id> session (<topic>):**` followed on the same line by the first
      sentence, then the rest in this order — what changed (name files/scripts, not process), what
      was NOT run or verified (omit if everything was), and a final `Next:` sentence. Total cap:
      10 lines including the header, wrapped at 100 columns. Then run
      `python "<hub root>/toolkit/scripts/work_log_entry_check.py" --project-root "<this project's absolute root>"`; on `[OVER-CAP]`/`[BAD-HEADER]`,
      shorten or fix the entry and re-run until it prints `[OK]`.
   - Do **not** prune or move older entries automatically — the Work Log stays complete until
     the user runs "archive".
2. Git mechanics — mechanized:
   ```
   <python_launcher> "<hub root>/toolkit/scripts/checkpoint_consumer.py" --project-root "<this
   project's absolute root>" --message "<summary>"
   ```
   (`<summary>` = the title of the Work Log entry step 1 just prepended, copied verbatim.)
   (`<hub root>`/`<python_launcher>` resolved the same way `templates\update.md`'s Step 1
   describes — the `toolkit\` folder your skill stub's own path resolved through, one level below
   the hub root.) Handles staging and commit/push in one call:
   - **Untracked-file safety**: never a blind `git add -A`. Tracked-file modifications are staged
     automatically (`git add -u`, always safe). A genuinely untracked file — a real new file this
     session wrote, or a stray temp/report file — looks identical to git either way, so nothing
     here guesses: an `[UNTRACKED]` report blocks (exit 2, nothing touched) until each one is
     resolved. Per file: if this session created or edited it, include it; if this session did
     not touch it, ask the user before including it. Then re-run with `--include <path...>` (stage specific ones, exactly as printed),
     `--include-all` (stage everything listed), and/or `--skip-untracked` (leave everything else
     alone this round).
   - **No repo at all** (`[ABORT]`, no `.git\`): stop and ask the user whether to set one up now,
     rather than skipping silently.
   - **No `origin` remote configured**: soft, not an error — `[COMMITTED-NO-REMOTE]`: commits
     locally, skips the push. A local-only project is a normal, everyday state.
   - **A push failure**: the script names the specific condition (non-fast-forward — pull, then
     re-run; no remote/auth — check credentials/`git remote -v`) instead of a bare refusal.
   - Exit 0 = committed/pushed cleanly (or nothing to do, or committed with no remote). Re-running
     is always safe if a further edit lands dirty afterward — e.g. correcting this same Work Log
     entry once more — no separate verify-clean loop to operationalize by hand; just run it again.
3. Confirm to the user in one line: `Checkpoint: <short sha> pushed` (or `committed, no remote` /
   `failed: <reason>`).
4. **Suggest archiving when the file has grown** (resource conservation): the whole of
   `project_progress.md` is read into context each session, so a long Work Log is a recurring
   token cost for history you're no longer actively using. If the file is past
   **400 lines** or its Work Log holds more than **10** entries, *suggest* the
   user run "archive" to move old, settled entries out. This is only a prompt — archiving is
   always the user's explicit call (see below), never automatic. The cost is linear, so there's
   no hard cliff; this threshold is just where a one-time cleanup starts paying for itself.

### "archive" (user-initiated only — never automatic, never during "checkpoint")

Two legs, run together every time: Work Log relocation (1-5) and Current Status/Focus + Next Up
triage (6-10) — the latter is where the Inclusion Test actually gets enforced now that
`"checkpoint"` only does a light fold-in. Decisions, Phases, and To Reconcile stay live state in
`project_progress.md` always — only Work Log, Current Status/Focus, and Next Up are ever archived.

Run `<python_launcher> "<hub root>/toolkit/scripts/archive_candidates.py" --project-root "<this
project's absolute root>"` as one bare command first (placeholders resolved as in `templates\update.md`
Step 1); its output drives both legs.

Work Log leg:
1-3. Read the script's `=== WORK LOG ===` list (one verdict per entry, newest first). `[ARCHIVE]` =
   complete and nothing depends on it; `[KEEP]` = the newest entry, one cited by title in Current
   Status/Next Up/Decisions, or one naming a non-DONE ticket; `[ASK]` = holds an open-work phrase or
   sits beside a Work Log pointer. Archive every `[ARCHIVE]` entry without waiting, never moving a
   `[KEEP]` one. For each `[ASK]` entry, read its text and ask the user about that entry by name
   (never "where's the cutoff"); archive it only on a yes.
4. Move every entry being archived into `project_progress_archive.md`, appended in chronological order
   (oldest first) regardless of which entries were skipped in between. Create the file if it
   doesn't exist yet.
5. Remove those entries from `project_progress.md`.

Current Status/Focus + Next Up triage leg:
6. **Inclusion test**, applied to every remaining line in both headings: would a session miss this
   fact by re-deriving it itself (reading the code, running the action, reading a design doc), and
   would missing it degrade this session's decisions? If Claude would learn it anyway by doing the
   thing the fact describes, or it's inspectable in seconds, it doesn't belong here. Neither
   heading is a capability inventory.
7. Classify every item with the script's `=== CURRENT STATUS / NEXT UP ===` table (it applies the
   rules below in this order, first match wins), trimming a mixed item to its residue first, since a
   real open fact is often wrapped inside otherwise-historical narration:
   | Bucket | The item holds | Fixed word lists |
   |---|---|---|
   | **In-progress** | an open-caveat word, or no completion verb/acceptance phrase/date to place it elsewhere | not yet, still, unconfirmed, unproven, not started, unexercised, hasn't, has not, no design, not decided, not scoped, pending, todo, open, unfixed, no plan, unknown |
   | **Standing fact** (non-re-derivable, settled or accepted, nobody pursuing it) | an acceptance phrase | deliberately, not a bug, accepted, either way, by design, intentionally, left as is |
   | **Calcified** | a completion verb AND a `YYYY-MM-DD` date, with no open-caveat word | built, fixed, verified, confirmed, found, resolved, done, live-tested, audited |
   An item already captured in a Decisions row for the same fact and date is Calcified too (a
   redundant restatement) - the script cannot see that; check it by eye.
8. Present the classification to the user as a table before moving anything — this is judgment,
   not a mechanical diff, and a standing fact's destination (step 9) needs a human call.
9. Act per bucket:
   - **Calcified** → delete from Current Status/Focus/Next Up, append to
     `project_progress_archive.md` (same append-only, chronological pattern as the Work Log leg).
   - **Standing fact** → ask the user where it belongs: `project_progress_archive.md` by default,
     or a more specific log this project already maintains (a decisions-detail file, a domain log
     such as an SEO page log, etc.) when one fits better. Don't default silently.
   - **In-progress** → stays, trimmed to its present-tense residue only.
10. Confirm with exactly this line (counts only): `Archived: <n> Work Log entr(y/ies) | Calcified: <n>
    archived | Standing: <n> relocated | In-progress: <n> kept`.
