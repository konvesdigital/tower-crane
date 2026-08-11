# Session continuity — rarer verbs (AGENTS.md companion)

Full mechanics for `"checkpoint"`, `"archive"`, `"update"`, `"propose upstream"`, `"curate shared
resources"`, and `"update consumers"`, named in `AGENTS.md`'s Procedures section. `"resume"` and
`"quick resume"` stay in `AGENTS.md` itself (they fire at session start, so deferring them here
would pay the lookup cost with no benefit) — read this file only when one of the verbs above is
actually invoked.

**"checkpoint"**
1. Update `project_progress.md`:
   - Update Current Status and Next Up in two passes: (1) **fold in what changed** — edit the
     existing text in place to match what's true right now, never append a new bullet narrating what
     this session did (that's the Work Log entry's job). (2) **Re-read the WHOLE section** and
     strike anything narrating a past event rather than present fact — a completion verb (built,
     fixed, verified, confirmed, found, resolved, done), a date tied to an event, or "this session"
     means it's history: delete it, or keep only its present-tense residue with no date/verb. A Next
     Up item whose action is done gets deleted outright, never marked done in place. A session with
     no present-tense change needs no edit here at all (Work Log entry still always gets added).
     (Rationale: `README.md` "Why this exists".)
   - Move resolved Decisions rows from Open → Locked.
   - Prepend one dated Work Log entry (what changed, what's next). Newest on top.
   - Do NOT prune or move older entries automatically — only "archive" does that.
2. Git — two independent repos live in this folder (`design\local_first_reframe.md`); handle both:
   a. Outer project repo (this repo root — `project_progress.md`, `consumers\`, `change_requests\`,
      `config.local.json`): `git add -A && git commit -m "Checkpoint: <summary>" && git push`
      - If no repo/remote is found: stop and ask the user whether to set one up now — flag it
        rather than skip silently.
   b. Inner `toolkit\` repo — only if `toolkit\` exists and `git -C toolkit status --porcelain`
      shows changes:
      - **Soft disclosure guardrail** (`design\update_trust_review.md`): if the pending changes
        touch `AGENTS.md`, run `python scripts\check_standing_constraints.py --base HEAD --head
        worktree` from inside `toolkit\`. `[UNCHANGED]`: proceed silently. `[CHANGED]`: surface the
        printed before/after text as an explicit notice before committing — never skip silently.
      - `git -C toolkit add -A && git -C toolkit commit -m "Checkpoint: <summary>"`.
      - **Hard outgoing leak-scan gate, before pushing** (`design\resource_sharing_model.md` B1):
        `git fetch origin`, then
        `python scripts\check_file_surface.py --base-sha origin/main --head-sha HEAD` (from inside
        `toolkit\`). `[FAIL]` (check 8a — added content matching a live `consumers\*.md` name or
        path segment) is a **hard block**: don't push. Report it verbatim, fix the offending
        content (likely belongs in `shared_resources\` instead), re-run this gate next checkpoint;
        the bad commit stays local-only until it passes. `[WARN]` (check 8b — generic
        absolute-path shape) doesn't block; mention it as a nudge.
      - `git -C toolkit push` — safe once the gate above passes.
      - **If the push fails** (`design\cross_machine_toolkit_sync.md`): don't block/roll back the
        outer-repo checkpoint (2a already landed) — but name the specific condition from git's
        output plus the exact resolving action, never a bare refusal. Non-fast-forward: state the
        pending-commit count and say "run `update`, then re-run `checkpoint`." No remote/auth: name
        that (check `git -C toolkit remote -v` / credentials). **Then correct step 1's
        already-written `project_progress.md` text** — it assumed this push would succeed. Work
        Log/Current Status must say "committed locally only, blocked on: `<reason>`" (with the
        SHA), never a stray "built" claim. Amend and re-push the outer repo — a second small commit
        beats a stale persisted claim.
3. Confirm to the user: saved and pushed (note whether `toolkit\` push happened, was skipped
   clean, or failed).
4. **Suggest archiving** if the file has grown past roughly **400 lines (~40 KB)**, or the Work Log
   holds many settled entries — a prompt only, never automatic.

**"archive"** (user-initiated only — never automatic, never during "checkpoint")
1. List current Work Log entries — date + one-line title only, newest first.
2. Ask the user where to draw the cutoff. Do not guess. Wait for an explicit answer.
3. Move every entry at or before that cutoff into `project_progress_archive.md`, appended in
   chronological order (oldest first). Create the archive file if it doesn't exist yet.
4. Remove those entries from `project_progress.md`. Confirm what was archived.

**"update"** — pulls `toolkit\`'s `origin` remote under a diff-review trust gate
(`design\update_trust_review.md`, `design\local_first_reframe.md`). User-initiated only; mechanical
steps live in `scripts\update_toolkit.py`, diff review/assessment below is manual judgment.
1. Run `python scripts\update_toolkit.py` (`--check`) from inside `toolkit\`.
2. "Already up to date": nothing else to do.
3. `[ABORT]` (remote-identity mismatch — `origin`'s URL no longer matches upstream): stop, report
   verbatim, get explicit confirmation before anything else. Never assume it's benign.
4. `[BLOCKED]` (a mechanical gate failed — golden suite, `consistency_check.py`, or
   `check_file_surface.py`): stop, report the failure verbatim. Hard block, no override. Offer to
   help investigate or file a fork+PR fix upstream; do not attempt `--approve`.
5. `=== PENDING COMMITS ===` / `=== BEGIN DIFF ===`…`=== END DIFF ===` (gates passed, review
   pending): present the pending-commit list first. Ask how many leading items the user wants to
   decide now; for those, read the diff and write your own plain-language assessment — benign, or
   destructive/obfuscated/exfiltration-shaped/inconsistent with the file's stated purpose? **Show
   both the literal diff and your assessment together, always** (`trust_and_values_draft.md` Part 1
   §4) — quoted verbatim in your own chat-visible response, never tool output alone.
6. Ask whether to approve. Everything shown: `python scripts\update_toolkit.py --approve` (also
   runs a post-merge `check_tower_crane.py`, auto-rolling back on failure before
   `last_reviewed_sha` advances). Only the leading items: `--approve --through <n>` (`<n>` = last
   approved item's 1-based index) — the rest stay queued. On no: `--reject` — a fully supported,
   indefinite steady state ("tools go stale but stay safe"), not a holdout to re-nag about.

**"propose upstream"** — sends a hand-built local fix in `toolkit\` back to the public repo
(`konvesdigital/tower-crane`) as a fork + PR (`design\local_first_reframe.md`). User-initiated
only, run from inside `toolkit\` — ordinary `git`/`gh` steps. **If the change touches `AGENTS.md`**,
step 2a adds Fix 3's authoring-assistant behavior (`design\update_trust_review.md`, Phase 2).
1. Check for a `fork` remote: `git remote get-url fork`. If it errors, this clone isn't pointed at
   one yet (don't assume no GitHub fork exists):
   a. `gh repo fork konvesdigital/tower-crane --remote=false` (idempotent; `--remote=false` keeps
      this clone's `origin` untouched).
   b. `gh api user -q .login` for the username, then
      `git remote add fork https://github.com/<username>/tower-crane.git`.
2. Branch off `main`: `git checkout -b <descriptive-branch-name>`.
2a. **If this change touches `AGENTS.md`** — run before committing (skipping risks rework at
   Checkpoint 2, `scripts\check_agents_pr_gate.py`):
   a. **Silently auto-fix the frontmatter** (`scope`/`capabilities`/`human_review_required`) to
      match the new content. Never touch Standing Constraints wording here — governed by (b).
   b. Run `python scripts\check_standing_constraints.py` (verbatim compare against `main`).
      `[UNCHANGED]`: continue silently. `[CHANGED]`: a standing-constraint edit — surface the
      before/after text as a warning and get explicit confirmation this is deliberate.
      **Overridable warning, not a hard block.**
   c. Ask the contributor "what changed?" and "why?", and separately write your own independent
      read of the diff. Render both into the PR body under `### Contributor statement` and
      `### Independent read` (never blended) — Phase 3's mechanical gate greps for these two exact
      headings on any PR touching `AGENTS.md`.
3. Commit with a plain-language message describing what changed and why.
4. Push to the fork: `git push fork <branch-name>`.
5. Draft a PR title/body in the user's own words — or, when 2a applied, the Contributor
   statement/Independent read structure (both shown, neither alone). Get explicit approval before
   opening anything.
6. On approval: `gh pr create --repo konvesdigital/tower-crane --head <username>:<branch-name>
   --title "<title>" --body "<body>"`.
7. Nothing further here — the PR runs the "AGENTS.md Fix 3 gate" GitHub Actions check
   (`scripts\check_agents_pr_gate.py`, via `.github\CODEOWNERS`). Ordinary GitHub PR review, not
   the `change_requests\` ticket system — don't file a ticket.

**"curate shared resources"** — occasional bulk distribution of `shared_resources\` entries to
every (or one) registered consumer, via `scripts\broadcast_guidance.py --broadcast`
(`design\resource_sharing_model.md`). Lands one pointer-only notice in a consumer's
`COMPLIANCE_GUIDANCE.md` `## Broadcast` section — never the full entry content. User-initiated
only, never triggered by `checkpoint`.
1. **Curate** — list `shared_resources\CATALOG.md` (skip anything `Archived`). Ask the user which
   entries are worth pushing right now.
2. **Author a pointer-only file** — one line per selected entry (e.g. `<Name> — <one-line hook>,
   say "shared resources" to review`). Never the full entry content.
3. **Push**: `python scripts\broadcast_guidance.py --broadcast <file.md>` (all consumers, or
   `--consumer <slug>` for one). Confirm the drafted file with the user first.
4. **Land** — nothing further here; the resume-time compliance check surfaces it on its own.

**"update consumers"** — push-side of `update`: same scope as a consumer's own pull-side `update`
skill (hooks, Track-1 skills, mandatory pieces; never `shared_resources`). User-initiated only.
1. `python scripts\update_consumers.py` (optionally `--consumer <slug>`) — indexed list across
   every locally-reachable consumer (Federate: other hosts skip silently); show it, ask what to apply.
2. `python scripts\update_consumers.py --apply <numbers-or-'all'>` — writes each touched project
   plus its `consumers\<slug>.md` registry entry directly (no filing ticket needed), then run
   `scripts\check_tower_crane.py` to confirm it validates clean.
