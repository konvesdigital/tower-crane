# Tower Crane Menu

Catalog of reusable hooks, subagents, and scripts available to any project. Nothing here runs
automatically - a project opts in by adding a reference to the relevant item in its own
`.claude\settings.json` (hooks) or `.claude\agents\` (subagents), then listing it under
"Tower Crane In Use" in that project's own CLAUDE.md.

When adding a new item to this menu: drop the file in the matching subfolder, add a row below,
and write the CLAUDE.md snippet a project needs to opt in.

**Who has opted into what lives in your own hub's private `consumers\<name>.md` registry, never
here.** This file tracks the public `konvesdigital/tower-crane` repo, so it can never carry a
project or client name — check your own hub's `consumers\` folder (`ls consumers\`, the index the
scaffolder writes and the checker reads) instead. Opt-in JSON snippets are canonical in
`templates\optins\<tool>.json` — MENU references them, and the scaffolder merges them into a new
consumer's `settings.json`. Don't duplicate a snippet's JSON here; point at its file.

## Hooks

| Name | File | What it does | Trigger |
|---|---|---|---|
| consistency_check | `hooks\consistency_check.py` | AST-based static analysis on a `.py` file: undefined names, function call arg-count mismatches, inconsistent string-key/column spellings. No AI, no tokens - pure static analysis. | PostToolUse, after any `.py` write/edit |
| shared_resources_trigger_match | `hooks\shared_resources_trigger_match.py` | Case-insensitive substring match of the submitted prompt against `shared_resources\trigger_index.yaml`'s authored trigger phrases; on a hit, surfaces the candidate entry as additional context. No AI, no tokens, no network call - a deterministic recognition layer under the existing skill-gate mechanism (`design\shared_resources_mechanical_trigger.md`). Requires `templates\shared_resources.md` (shared_resources itself). | UserPromptSubmit, every submitted message |

### consistency_check - opt-in snippet
Canonical snippet: **`templates\optins\consistency_check.json`**. Merge it into the project's
`.claude\settings.json` (into any existing `hooks` block — don't replace it). The scaffolder
(`scripts\new_consumer.py`) does this merge automatically. The snippet's command is a **config
template** (`{{PYTHON_LAUNCHER}} "{{SHARED_ROOT}}/hooks/consistency_check.py"`) — the real per-machine
values come from `config.local.json` and are injected by the scaffolder/checker/relocate. No
machine-specific path is committed anywhere; the hook is pure Python (a `python_launcher` on PATH is
the only runtime, and it was already required).

The script no-ops on any file that isn't `.py`, so this is safe to add even to a project with
little Python. **If this install ever moves (or a fresh clone lands on another machine), you don't
hand-edit any consumer** — update `config.local.json` and run `scripts\relocate.py`, which
regenerates every registered consumer's hook command from config.

### shared_resources_trigger_match - opt-in snippet
Canonical snippet: **`templates\optins\shared_resources_trigger_match.json`**. Merge it into the
project's `.claude\settings.json` (into any existing `hooks` block — don't replace it). Same
config-template convention as `consistency_check`'s command
(`{{PYTHON_LAUNCHER}} "{{SHARED_ROOT}}/hooks/shared_resources_trigger_match.py"`).

Fails open on any error (missing/malformed `trigger_index.yaml`, unreadable `CATALOG.md`, bad
stdin) — never blocks or alters the submitted prompt, exits 0 either way. A hub with no
`shared_resources\trigger_index.yaml` yet, or one with no entries, produces no output at all — safe
to opt into before any resource has been given trigger phrases (see the design doc's "Backfill").
Not folded into `shared_resources.md`'s own MANDATORY status; opt in per project like any other
`toolkit\` tool.

## Subagents
*(none yet)*

## Scripts
*(none yet)*
