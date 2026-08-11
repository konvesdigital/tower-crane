# Change Requests (AGENTS.md companion)

Full mechanics for the change-request ticket inbox named in `AGENTS.md`'s Procedures section. The
"Scanning at session start" section below is read every `resume` (per `AGENTS.md`'s `"resume"`
step 7); the rest of this file is read only when actually filing, fixing, or closing a ticket.

## Change Requests (from consumer projects)
Consumer projects can't edit shared tools — they only *file* requests. Filing and fixing happen in
two different sessions in two different repos, keeping each repo's git history honest. A ticket's
**Proposed fix is a suggestion, not a mandate** — this agent owns the final call.

Tickets are markdown files in `change_requests\`. The filename convention
(`YYYY-MM-DD_<tool>_<slug>.md`) is the index — no separate index file. The first line is always
`Status: OPEN` or `Status: DONE` — only two statuses; a ticket stays **OPEN through the entire
round-trip** (below).

**Registration tickets** (`YYYY-MM-DD_register_<slug>.md`, `Type: registration`): an existing
project onboarding itself via `templates\register.md`. Same inbox, **no round-trip** — see
"Registration tickets" below.

**Proposal tickets** (`Type: proposal`, template in `templates\filing.md`): a consumer proposing
new shared content rather than reporting a bug. Same round-trip as an ordinary ticket — action per
"Applying a fix" below, reading "Proposed content" as the equivalent of "Proposed fix."

### `DONE` means consumer-verified — not "fix applied"
`DONE` = the **filing consumer** has re-run its own test and confirmed the fix works. It does NOT
mean this agent applied a fix. Applying a fix and pushing it leaves the ticket **OPEN**, awaiting
the consumer's verification. Closing authority stays here: the consumer appends a "verified PASS"
line, and this agent flips `Status` to `DONE` on its next session.

### Round-trip log
Every hand-off appends one dated line to a `## Round-trip log` section at the bottom of the ticket
(same pattern as this repo's Work Log — chronological, newest at bottom):
- this agent: `2026-07-18 — fix applied (commit <sha>), affects: <slug>; awaiting <slug> verify`
- consumer:   `2026-07-19 — <slug> re-verified, still fails: <what>`   (ticket stays OPEN)
- consumer:   `2026-07-20 — <slug> verified PASS`                       (this agent flips DONE next session)

**Multi-user attribution:** with more than one committer, name the acting person alongside the project in each line (e.g. `fix applied by <name> (commit <sha>)…`). A single-owner hub keeps the terser project-only form above.

### Scanning at session start (including on `resume` — see `AGENTS.md`) or when asked to process requests
Scan `change_requests\` for `Status: OPEN`. A `register` ticket (`Type: registration`) is handled by
"Registration tickets" below; for a normal fix ticket, read the **last** `## Round-trip log` line to
know whose turn it is:
- No round-trip activity yet → this agent's turn: fix it (Applying a fix, below).
- "awaiting <consumer> verify" → ball is in the consumer's court; **skip**.
- consumer "verified PASS" → flip `Status` to **DONE**, commit, push. Closed.
- consumer "still fails: …" → this agent's turn again: re-fix.
- "automation: fix proposed ..., PR #<n> opened, awaiting <owner> review" → the unattended
  sync-automation agent (Piece 3, `design\sync_automation.md`) already opened a PR for this ticket;
  **skip** — don't also fix it by hand. If `scripts\ticket_scan.py`'s own mechanical pass hasn't
  already caught it, `gh pr view <n> --json state` tells you: `MERGED` → the fix landed, ticket is
  awaiting consumer verify (treat like any other applied fix); `CLOSED` (not merged) → this agent's
  turn again, same as "still fails."

Round-trip lines an unattended `scripts\run_automation.py` run writes are prefixed `automation:` to
distinguish them from live-session lines. It never flips `Status` to DONE itself except via
`ticket_scan.py`'s already-verified-PASS handling, and never merges a PR — a human always does.

### Registration tickets (this agent's turn — no round-trip)
A `register` ticket has two shapes — check for a fenced `yaml` block first, since that's what
tells them apart:

**New project joining** (fenced `yaml` block: name/path/opted_in/imported, filed by
`templates\register.md` since the consumer can't edit shared files itself — it carries no
`host:`/`hosts:` field, since the ticket-filing session has no `config.local.json` access to know
its own `host_id`). Action immediately:
1. Read the `yaml` block.
2. **Validate before trusting it:** confirm `path` exists on disk; for each `opted_in` tool,
   confirm `templates\optins\<tool>.json` exists; for each `imported` piece, confirm the project's
   `CLAUDE.md` actually imports it. Reconcile anything off rather than blindly copying.
3. Ask the user **local to this machine only, or available to all connected machines?**
   (`design\multi_machine_hub.md` "Problem 2") — this session's own `host_id`
   (`config.local.json`) is the host being connected.
4. If `consumers\<slug>.md` doesn't exist yet: create it with `scope:` from step 3 and a `hosts:`
   map holding this one host (path from the ticket, registered = today). Never record a
   project/client name anywhere in `toolkit\` itself (including `MENU.md`) — that repo tracks the
   public repo, and `consumers\` exists in the outer, private repo specifically so this never
   reaches it. If it already exists (slug collision — this project registered from another machine
   before): merge-add this `hosts.<host_id>` entry instead, never overwrite the file — `scope`
   self-corrects to `multi_machine` once 2 hosts exist, regardless of step 3's answer.
5. Run `scripts\check_tower_crane.py --consumer <slug>` to confirm the entry validates clean.
6. Flip `Status` to **DONE** (no consumer-verify round-trip — the registry entry existing *is* the
   completion). Log it in `project_progress.md`, commit, and push.

**Existing consumer reporting a standalone-skill/tool adoption** (no `yaml` block — filename shape
`register_<consumer>_<slug>.md`, e.g. after the consumer's own `update` skill applies a
`STANDALONE_SKILLS` item). The ticket body states the requested action in prose — **read and
action it before flipping DONE; "no round-trip" doesn't mean "nothing to do."** In practice:
append a short documentary note to the existing `consumers\<slug>.md` entry (same pattern as its
prior such notes) recording what was adopted and when — `check_tower_crane.py` won't catch a
skipped note, this convention isn't mechanically checked. Then run
`scripts\check_tower_crane.py --consumer <slug>` (confirms no unrelated drift), flip `Status` to
**DONE**, log it in `project_progress.md`, commit, and push.

### Applying a fix (this agent's turn)
1. Read the symptom/repro, root cause, and Proposed fix (a suggestion, not a mandate).
2. **Mandatory pre-apply validation:** enumerate *every* consumer in the registry (`consumers\`,
   the source of truth) and reason about impact on each, not just the filer. Consumers float on
   this repo's HEAD, so a fix reaches all of them the moment they next run.
3. Apply the fix (or a better one). Run **`scripts\check_tower_crane.py`**: its golden suite
   (`tests\<tool>\`) catches a behavior regression, its reference scan confirms no consumer's
   wiring/imports broke. Also run the ticket's Suggested test plus your own. Add/extend a golden
   fixture when the fix is behavior-changing.
4. Append a `## Round-trip log` line recording the **commit SHA** and affected consumers. Leave
   `Status: OPEN`. Log it in `project_progress.md`, naming affected consumers there too. Commit and
   push — the ticket closes only when the consumer verifies.

### Cross-consumer verify tickets (only when 2+ consumers exist)
When a behavior-changing fix ships and the registry (`consumers\`) lists consumers *other* than the
filer, file a one-line verify-request ticket in `change_requests\` for each other consumer
(`Status: OPEN`, `Relates to: <original ticket>`, naming the consumer to verify). With a single
consumer this step is a no-op.

### Reverts and regressions
No version tags or changelog — the **commit SHA in the round-trip log is the version handle**. A revert or regression is just another ticket: `Status: OPEN`, `Regression of: <original ticket>`,
citing the bad SHA. This agent decides revert vs. forward-fix and re-runs the same pre-apply
validation. Do NOT add per-consumer version pinning or `_vN` copies.
