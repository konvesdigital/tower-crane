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
   - **Fold in what changed this session** — edit the existing text in place to match what's true
     right now, or add a line only for something this session discovered that doesn't already fit
     an existing one. Never append a bullet narrating what this session did (that's the Work Log
     entry's job). A session with no present-tense change needs no edit here at all (Work Log entry
     still always gets added). Do not re-scan the whole section for calcified or misplaced content
     here — that full audit (the Inclusion Test) is `"archive"`'s job below, not paid at every
     checkpoint.
   - Move resolved Decisions rows from Open → Locked.
   - **A new or edited Decisions row's Notes column is a pointer, never prose.** Point to the
     `design\X.md` that's the real source if one exists; otherwise, if the decision is operative
     (should govern a future action), put the actual rule in whichever procedure/companion file
     enforces that action and point there instead; anything left over (pure historical rationale
     with no other home) goes in `decisions_detail.md`, one short section per row, pointed to from
     here. The Item + Status
     columns stay resident and readable at a glance; full detail is always one click away, never
     inline — same shape as a skill stub vs. its template.
   - Prepend one dated Work Log entry (what changed, what's next). Newest on top.
   - Do NOT prune or move older entries automatically — only "archive" does that.
2. Git mechanics for both repos — mechanized (mechanical
   steps live in the script, same split as `update_toolkit.py` keeps below):
   `python toolkit/scripts/checkpoint_git.py --message "<summary>"`. Handles, for
   both the outer project repo and the inner `toolkit\` repo in one call: staging, the
   leak-scan-first gate, the Standing Constraints disclosure guardrail, commit, push, and (after a
   successful `toolkit\` push) the `last_reviewed_sha` self-heal.
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
   - **Success also closes the loop, symmetrically with the failure branch above**: if step 1's
     Work Log entry or Current Status text carries any git-commit-state language describing *this*
     checkpoint's own work ("not yet committed," "pending `checkpoint`," "committed locally only,
     blocked on...," etc. — written truthfully while a prior blocked/partial run left it that way),
     and this run's git mechanics now succeed, that language is stale the instant it lands — commit
     status is exactly the kind of fact step 1's own Inclusion test already excludes (re-derivable
     via `git status` in seconds). Strike it, or fold in the commit SHA in its place, as part of
     this same checkpoint — never leave a "pending checkpoint" claim standing inside a commit that
     the checkpoint which just ran already made. Do not write this kind of language pre-emptively
     in the first place (step 2 is about to resolve it in the same invocation, or fails and the
     branch above documents the correction); it belongs only for a state that's actually still
     open when the entry is written, e.g. a run genuinely blocked on untracked files/leak-scan/
     standing constraints and left to resume later.
3. Confirm to the user: saved and pushed, **both repos' working trees clean** (note whether
   `toolkit\` push happened, was skipped clean, or failed).
4. **Suggest archiving** if the file has grown past roughly **400 lines (~40 KB)**, or the Work Log
   holds many settled entries — a prompt only, never automatic.

**"archive"** (user-initiated only — never automatic, never during "checkpoint")

Two legs, run together every time: Work Log relocation (1-5) and Current Status/Next Up triage
(6-10) — the latter is where the Inclusion Test actually gets enforced now that `"checkpoint"`
only does a light fold-in. Only Work Log, Current Status, and Next Up are ever touched — the
Decisions table stays live state in `project_progress.md` always.

Work Log leg:
1. Determine which Work Log entries are both fully completed and not themselves a dependency for
   current or other work items.
2. List current Work Log entries — date + one-line title only, newest first — marking with a
   checkmark those found fully complete and non-dependent in step 1.
3. Default: archive every ✓-marked entry from step 2 — these need not be contiguous; an older
   completed entry can be archived while a newer one stays live, and vice versa. Present the marked
   list as the plan and proceed on it without waiting for confirmation, unless a specific
   completion/dependency call is genuinely ambiguous — then ask about that entry specifically,
   never "where's the cutoff."
4. Move every ✓-marked entry into `project_progress_archive.md`, appended in chronological order
   (oldest first) regardless of which entries were skipped in between. Create the file if it
   doesn't exist yet.
5. Remove those entries from `project_progress.md`.

Current Status / Next Up triage leg:
6. **Inclusion test**, applied to every remaining line in both headings: would a session miss this
   fact by re-deriving it itself (reading the code, running the action, reading a design doc), and
   would missing it degrade this session's decisions? If Claude would learn it anyway by doing the
   thing the fact describes, or it's inspectable in seconds (e.g. who's registered — read
   `consumers\`, don't restate the roster), it doesn't belong here. Neither heading is a capability
   inventory — a fully-built feature with no open caveat belongs in `README.md`; a settled call
   belongs in the Decisions table.
7. Classify every line — trimming a mixed line to its residue first, since a real open fact is
   often wrapped inside otherwise-historical narration — into exactly one of three buckets:
   - **Calcified**: a completion verb (built, fixed, verified, confirmed, found, resolved, done,
     live-tested, audited) tied to a date, with no open caveat left once that narration is
     stripped — or the same fact/date already has a matching `Locked`/`Locked and BUILT` row in the
     Decisions table, making the line a redundant restatement.
   - **Standing fact**: a real, non-re-derivable fact describing a settled or accepted state nobody
     is actively pursuing (language like "deliberately," "not a bug," "accepted either way") —
     worth keeping somewhere, but not active work.
   - **In-progress**: everything else — an actively-worked task, or an unresolved defect/gap with
     no acceptance language (a known standing defect with no plan yet still counts as in-progress
     for this purpose).
8. Present the classification to the user as a table before moving anything — this is judgment,
   not a mechanical diff, and a standing fact's destination (step 9) needs a human call.
9. Act per bucket:
   - **Calcified** → delete from Current Status/Next Up, append to `project_progress_archive.md`
     (same append-only, chronological pattern as the Work Log leg).
   - **Standing fact** → ask the user where it belongs: `project_progress_archive.md` by default,
     `decisions_detail.md` when it's operative rationale with no other home, or another
     project-specific log this project already maintains when one fits better. Don't default
     silently.
   - **In-progress** → stays in Current Status/Next Up, trimmed to its present-tense residue only.
10. Confirm what was archived/relocated and what stayed, per bucket.

**"update"** — pulls `toolkit\`'s `origin` remote under a diff-review trust gate. User-initiated
only; mechanical steps live in `scripts\update_toolkit.py`, diff review/assessment below is manual
judgment.
1. Run `python toolkit/scripts/update_toolkit.py` (`--check`).
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
6. Ask whether to approve. Everything shown: `python toolkit/scripts/update_toolkit.py --approve` (also
   runs a post-merge `check_tower_crane.py`, auto-rolling back on failure before
   `last_reviewed_sha` advances). Only the leading items: `--approve --through <n>` (`<n>` = last
   approved item's 1-based index) — the rest stay queued. On no: `--reject` — a fully supported,
   indefinite steady state ("tools go stale but stay safe"), not a holdout to re-nag about.

**"propose upstream"** — sends a hand-built local fix in `toolkit\` back to the public repo
(`konvesdigital/tower-crane`) as a fork + PR. **For a clone
without direct write access to `origin`** (an external contributor's fork, or any downloaded copy
of the public repo) — the operator's own hub clone has real write access (branch-protection admin
bypass) and lands `AGENTS.md`/companion-file edits through the ordinary `"checkpoint"` procedure's
guardrail-gated push instead, never needing this flow. User-initiated only, run from inside
`toolkit\` — ordinary `git`/`gh` steps. **If the change touches `AGENTS.md`**, step 2a adds an
authoring-assistant behavior described below.
1. Check for a `fork` remote: `git remote get-url fork`. If it errors, this clone isn't pointed at
   one yet (don't assume no GitHub fork exists):
   a. `gh repo fork konvesdigital/tower-crane --remote=false` (idempotent; `--remote=false` keeps
      this clone's `origin` untouched).
   b. `gh api user -q .login` for the username, then
      `git remote add fork https://github.com/<username>/tower-crane.git`.
2. Branch off `main`: `git checkout -b <descriptive-branch-name>`.
2a. **If this change touches `AGENTS.md`** — run before committing (skipping risks rework at
   Checkpoint 2, `scripts/check_agents_pr_gate.py`):
   a. **Silently auto-fix the frontmatter** (`scope`/`capabilities`/`human_review_required`) to
      match the new content. Never touch Standing Constraints wording here — governed by (b).
   b. Run `python toolkit/scripts/check_standing_constraints.py` (verbatim compare against `main`).
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
   (`scripts/check_agents_pr_gate.py`, via `.github\CODEOWNERS`). Ordinary GitHub PR review, not
   the `change_requests\` ticket system — don't file a ticket.

**"curate shared resources"** — occasional bulk distribution of `shared_resources\` entries to
every (or one) registered consumer, via `scripts/broadcast_guidance.py --broadcast`. Lands one
pointer-only notice in a consumer's `COMPLIANCE_GUIDANCE.md` `## Broadcast` section — never the
full entry content. User-initiated only, never triggered by `checkpoint`.
1. **Curate** — list `shared_resources\CATALOG.md` (skip anything `Archived`). Ask the user which
   entries are worth pushing right now.
2. **Author a pointer-only file** — one line per selected entry (e.g. `<Name> — <one-line hook>,
   say "shared resources" to review`). Never the full entry content.
3. **Push**: `python toolkit/scripts/broadcast_guidance.py --broadcast <file.md>` (all consumers, or
   `--consumer <slug>` for one). Confirm the drafted file with the user first.
4. **Land** — nothing further here; the resume-time compliance check surfaces it on its own.

**"register host"** — bulk-registers THIS machine into every `shared_resources\` entry it's missing
from, instead of waiting for `check_shared_resource_refs.py`'s per-adoption `[HOST-GAP]` check to
catch each one separately, one already-adopting consumer project at a time. User-initiated, any
time — also run automatically as `setup_machine.md` Step 8a on a newly connected machine.
1. Run `python toolkit/scripts/check_shared_resource_hosts.py` — notify-only,
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
1. `python toolkit/scripts/update_consumers.py` (optionally `--consumer <slug>`) — indexed list across
   every locally-reachable consumer (Federate: other hosts skip silently); show it, ask what to apply.
2. `python toolkit/scripts/update_consumers.py --apply <numbers-or-'all'>` — writes each touched project
   plus its `consumers\<slug>.md` registry entry directly (no filing ticket needed), then run
   `toolkit/scripts/check_tower_crane.py` to confirm it validates clean.
