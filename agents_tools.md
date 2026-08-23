# Tool lifecycle procedures (AGENTS.md companion)

Full mechanics for the `"new tool"` / `"new private tool"` / `"self hooks"` / `"modify tool"`
triggers named in `AGENTS.md`'s Procedures section. Read this file when one of those triggers
fires — it is not preloaded.

## Adding a new tool
**Trigger: "new tool" — ask public or private first** (or jump straight in via `"new private
tool"`). Public reaches every consumer via the shared `toolkit\` repo; private
(`design\private_tools.md`) reaches every consumer the same automatic way but stays in this
machine's own outer repo, never touching `toolkit\`'s public GitHub origin.

**Language:** consumer-runtime scripts (hooks, subagents) are cross-platform Python by default;
this repo's maintainer scripts are Python throughout too.

**Skill triggers, if this tool is a Track-1 skill:** a short, closed-form command the user would
say verbatim ("checkpoint," "archive") gets an **exact-phrase** trigger — fuzzy matching on that
shape risks colliding with `capability_relationships`' own broad description-matching.
Open-ended/no-single-phrase asks (e.g. filing a bug report) can stay fuzzy. `capability_relationships`
itself is the catch-all for anything broader than one named command; don't add a second one.

**Public branch:**
1. Build and test it like normal project work.
2. Strip anything project-specific — no hardcoded paths, project names, or repo-structure
   assumptions. Must work unmodified for any future project.
2a. If wired as an automatic hook (`hooks\`, or a future `agents\` subagent): on failure, exit
   code **2**, write the report to **stderr** — never exit 1 (see README.md "Why hooks exit 2, not
   1"; `hooks\consistency_check.py` is the reference implementation). Doesn't apply to a
   manually-invoked script.
3. Place it in `hooks\`, `agents\`, or `scripts\`.
4. Add a row to `MENU.md` (name, file, what it does, trigger if a hook) and write the exact opt-in
   snippet a consuming project needs (literal absolute path, matching MENU.md's existing style).
5. Checkpoint (`agents_continuity.md`): commit and push.

**Private branch** (`toolkit_private\`, outer repo, sibling of `toolkit\`):
1. Build and test it the same way.
2. Skip the generalize/strip-project-specifics step — it never leaves this machine, so
   `check_file_surface.py`'s leak-scan doesn't apply. 2a's exit-2/stderr contract still applies.
3. Place it in `toolkit_private\hooks\` / `scripts\`, or `toolkit_private\templates\skills\<name>\
   SKILL.md` for a Track-1 skill.
4. Add a row to `toolkit_private\MENU.md` and an opt-in at
   `toolkit_private\templates\optins\<name>.json` (`{{PRIVATE_ROOT}}` in place of
   `{{SHARED_ROOT}}`). A consumer opts in via `update`/`update consumers`, never by hand-editing
   its own `.claude\settings.json`.
5. Checkpoint (`agents_continuity.md`): the ordinary outer-repo commit+push already covers it — no
   leak-scan gate.

**Migrating private → public:** re-run the public branch with the content copied over (same
generalize pass any new public tool needs). Default: delete the `toolkit_private\` copy once the
public version works; "keep both" is a per-tool choice, not the default.

## Self-use (dogfooding)
**Trigger: "self hooks".**
This repo is not a registered consumer of itself. `scripts\self_hooks.py` turns a tool on for THIS
repo/machine only: `--list` (default), `--enable <tool>`, `--disable <tool>`. State lives in
gitignored `.claude\settings.local.json`; a mirror auto-regenerates at
`.claude\self_hooks_status.md` (open directly to check state). Every tool self-enables the moment
its `templates\optins\<tool>.json` exists.

## Changing or removing an existing tool
**Trigger: "modify tool".**
1. Check the consumer registry (`consumers\`, the source of truth) for who's opted in first.
2. If any project uses it, confirm with the user before editing — a consuming project can't see
   this repo's Work Log. Exception: a minor benevolent change (prose/workflow refinement or
   strictly-additive guardrail) propagates silently, logged in the Work Log only.
3. Update `MENU.md`. If the opt-in snippet itself changed, say so clearly in the Work Log entry
   so it's obvious which consuming projects need to update their own `.claude\settings.json`.
