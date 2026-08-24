# Session continuity — rarer verbs (AGENTS.md companion)

Full mechanics for `"checkpoint"`, `"archive"`, `"update"`, `"propose upstream"`, `"curate shared
resources"`, and `"update consumers"`, named in `AGENTS.md`'s Procedures section. `"resume"` and
`"quick resume"` stay in `AGENTS.md` itself (they fire at session start, so deferring them here
would pay the lookup cost with no benefit) — read this file only when one of the verbs above is
actually invoked.

**"checkpoint"**
1. Update `project_progress.md`:
   - **`## Current Status` and `## Next Up` are two distinct headings, not one blended section.**
     Current Status is a dashboard: recent state deltas (not true at the start of last session),
     work genuinely in progress (designed-not-built, built-not-tested, tested-and-found-buggy), and
     known standing defects a session needs to not trip over — even ones with no plan yet. Next Up
     is a queue: work identified but not yet started, deferred until its time comes. An item
     graduates Next Up → Current Status the session someone actually starts it, and out of Current
     Status → Work Log the session it's done — never sideways.
   - **Inclusion test, applied to every line in both headings**: would a session miss this fact by
     re-deriving it itself (reading the code, running the action, reading a design doc), and would
     missing it degrade this session's decisions? If Claude would learn it anyway by doing the thing
     the fact describes, or it's inspectable in seconds (e.g. who's registered — read `consumers\`,
     don't restate the roster), it doesn't belong here. Neither heading is a capability inventory —
     a fully-built feature with no open caveat belongs in `README.md`; a settled call belongs in the
     Decisions table. Point to the canonical source instead of duplicating it.
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
   - **A new or edited Decisions row's Notes column is a pointer, never prose.** Point to the
     `design\X.md` that's the real source if one exists; otherwise, if the decision is operative
     (should govern a future action), put the actual rule in whichever procedure/companion file
     enforces that action and point there instead; anything left over (pure historical rationale
     with no other home) goes in `decisions_detail.md`, one short section per row, pointed to from
     here. The Item + Status columns stay resident and readable at a glance; full detail is always
     one click away, never inline — same shape as a skill stub vs. its template.
   - Prepend one dated Work Log entry (what changed, what's next). Newest on top.
   - Do NOT prune or move older entries automatically — only "archive" does that.
2. Git mechanics for both repos — mechanized (`design\command_procedure_audit.md`'s B2; mechanical
   steps live in the script, same split as `update_toolkit.py` keeps below):
   `python scripts\checkpoint_git.py --message "<summary>"` from inside `toolkit\`. Handles, for
   both the outer project repo and the inner `toolkit\` repo in one call: staging, the
   leak-scan-first gate, the Standing Constraints disclosure guardrail, commit, push, and (after a
   successful `toolkit\` push) the `last_reviewed_sha` self-heal (the "B2 addendum" —
   `design\command_procedure_audit.md`).
   - **Untracked-file safety**: never a blind `git add -A`. Tracked-file modifications are staged
     automatically (`git add -u`, always safe). A genuinely untracked file in either repo — a real
     new design doc/script this session wrote, or a stray temp/report file dropped in a repo root —
     looks identical to git either way, so nothing here guesses: an `[UNTRACKED]` report blocks
     (exit 2, nothing touched) until each one is resolved. Decide per file from this session's own
     context (ask the user if genuinely unclear), then re-run with `--include <path...>` (stage
     specific ones, exactly as printed in the report), `--include-all` (stage everything listed),
     and/or `--skip-untracked` (leave everything else alone this round).
   - **Leak-scan FAIL** (check_file_surface.py, hard checks only): exit 1, `toolkit\` left
     unstaged/uncommitted — the outer repo is unaffected and still commits/pushes normally. Fix the
     flagged content (likely belongs in `shared_resources\` instead), re-run.
   - **Standing Constraints `[CHANGED]`** with no note given: exit 1, `toolkit\` left
     unstaged/uncommitted. Surface the printed before/after text to the user as an explicit notice
     — never skip silently — then re-run with `--standing-constraints-note "<one-line reason>"`
     (lands as a `Standing-Constraints-changed:` commit trailer).
   - **A push failure** (either repo): the script names the specific condition (non-fast-forward —
     run `update`, then re-run `checkpoint`; no remote/auth — check credentials/`git remote -v`)
     instead of a bare refusal. On a `toolkit\` push failure specifically: correct step 1's
     already-written `project_progress.md` text to say "committed locally only, blocked on:
     `<reason>`" (with the SHA), never leave a stray "built"/"pushed" claim standing — amend with a
     second small outer-repo commit once fixed.
   - Exit 0 = both repos committed/pushed cleanly (or nothing to do). Re-running is always safe
     (idempotent) if a further edit lands dirty afterward — e.g. correcting this same Work Log
     entry once more — no separate verify-clean loop to operationalize by hand; just run it again.
3. Confirm to the user: saved and pushed, **both repos' working trees clean** (note whether
   `toolkit\` push happened, was skipped clean, or failed).
4. **Suggest archiving** if the file has grown past roughly **400 lines (~40 KB)**, or the Work Log
   holds many settled entries — a prompt only, never automatic.

**"archive"** (user-initiated only — never automatic, never during "checkpoint")
1. Determine which Work Log entries are both fully completed and not themselves a dependency for
   current or other work items.
2. List current Work Log entries — date + one-line title only, newest first — marking with a
   checkmark those found fully complete and non-dependent in step 1.
3. Ask the user where to draw the cutoff. Do not guess. Wait for an explicit answer.
4. Move every entry at or before that cutoff into `project_progress_archive.md`, appended in
   chronological order (oldest first). Create the archive file if it doesn't exist yet.
5. Remove those entries from `project_progress.md`. Confirm what was archived.

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
(`konvesdigital/tower-crane`) as a fork + PR (`design\local_first_reframe.md`). **For a clone
without direct write access to `origin`** (an external contributor's fork, or any downloaded copy
of the public repo) — the operator's own hub clone has real write access (branch-protection admin
bypass) and lands `AGENTS.md`/companion-file edits through the ordinary `"checkpoint"` procedure's
guardrail-gated push instead, never needing this flow. User-initiated only, run from inside
`toolkit\` — ordinary `git`/`gh` steps. **If the change touches `AGENTS.md`**, step 2a adds Fix 3's
authoring-assistant behavior (`design\update_trust_review.md`, Phase 2).
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

**"register host"** — bulk-registers THIS machine into every `shared_resources\` entry it's missing
from, instead of waiting for `check_shared_resource_refs.py`'s per-adoption `[HOST-GAP]` check to
catch each one separately, one already-adopting consumer project at a time
(`design\shared_resources_bulk_host_registration.md`). User-initiated, any time — also run
automatically as `setup_machine.md` Step 8a on a newly connected machine.
1. Run `python scripts\check_shared_resource_hosts.py` from inside `toolkit\` — notify-only,
   catalog-wide, exit 0 always. Buckets every non-`Archived`, non-`insight` catalog row as `[OK]`
   (already registered here — skip silently), `[UNREGISTERED]` (has a `Hosts:` block, this host
   isn't in it), or `[NO-HOSTS-BLOCK]` (no `Hosts:` block at all — ambiguous).
2. For every `[NO-HOSTS-BLOCK]` hit: ask the user to resolve the ambiguity. Genuinely self-contained
   (nothing to ever register) → skip, no marker written (re-judged next pass — cheap while the
   catalog stays small). An unmigrated pointer entry → migrate it to `Hosts:` block form first
   (same shape as `seo_resources.md`'s 2026-08-20 fix — including a quick existence check on any
   pre-existing flat path before trusting it, since that's exactly what caught that entry's own
   drift), then treat it as `[UNREGISTERED]` below.
3. For every `[UNREGISTERED]` hit (including one just migrated): ask whether this host wants/has
   this entry. **Yes** — ask for the real path on **this** machine specifically (never assume it
   matches another host's path), confirm it exists on disk, then write a new `hosts.<this host>`
   entry into that entry's own `Hosts:` block. **No** — leave it unregistered; this pass re-asks
   next time it's run (no suppression marker — on-demand, not run automatically every session).
4. One combined propagation commit+push against the hub's own outer repo, scoped to
   `shared_resources\` (`templates\shared_resources.md`'s "Every write here ends with the same
   propagation step") — not one commit per entry.
5. Report a short summary: how many entries newly registered, how many declined, how many resolved
   as self-contained.

**"update consumers"** — push-side of `update`: same scope as a consumer's own pull-side `update`
skill (hooks, Track-1 skills, mandatory pieces; never `shared_resources`). User-initiated only.
1. `python scripts\update_consumers.py` (optionally `--consumer <slug>`) — indexed list across
   every locally-reachable consumer (Federate: other hosts skip silently); show it, ask what to apply.
2. `python scripts\update_consumers.py --apply <numbers-or-'all'>` — writes each touched project
   plus its `consumers\<slug>.md` registry entry directly (no filing ticket needed), then run
   `scripts\check_tower_crane.py` to confirm it validates clean.
