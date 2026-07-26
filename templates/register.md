<!--
Home: ~\Documents\Claude\tower_crane\toolkit\templates\register.md
This is the PORTABLE onboarding/migration file. Copy it into the ROOT of any existing project
that should join the tower_crane platform, then open that project in Claude Code and say:
"read register.md and follow it." It is deliberately self-contained: a project that hasn't
imported any shared protocol yet still has every instruction it needs inline.

Keep this file project-agnostic and float-on-HEAD (edits here are the canonical version). It is a
one-time courier file - the target project's agent executes the steps then DELETES its copy.
-->

# Register this project with tower_crane

You (the agent running in THIS project) are onboarding this repo onto the **tower_crane platform**
so it (a) receives shared workflow improvements automatically via `@import` (float-on-HEAD instead
of frozen copied prose) and (b) can be audited and receive compliance guidance from the shared side.

Work through the steps below **with the user in the loop** — show a diff and confirm before writing
to `CLAUDE.md`. This is a migration of an existing repo, so **preserve everything project-specific**;
only shared, canonical workflow prose gets replaced by imports.

---

## Step 0 — Locate the shared hub and compute this machine's import base
Ask the user where their tower_crane hub lives on this machine — **do not assume.** As a starting
guess you may check whether `~\Documents\Claude\tower_crane\` exists and offer it as the likely
answer, but confirm either way: there is no fixed conventional install location (tower_crane's own
self-locating install design — the hub can live anywhere, under any folder name, as long as it's
somewhere under the user's home directory). The hub itself is two nested git repos in one folder —
an outer, private **hub root**, and an inner `toolkit\` repo that actually holds the shared
templates this project will import. Verify `<hub root>\toolkit\templates\` exists at the confirmed
path (not `<hub root>\templates\` — that's the pre-split layout); if not, stop and ask again —
every later step depends on it.

Once confirmed, compute this machine's **import base**: take the hub root's absolute path, express
it relative to the user's home directory, forward-slash form, prefixed `~/` and suffixed
`/toolkit/templates` — e.g. a hub root at `C:\Users\<user>\Documents\Claude\tower_crane` gives
`~/Documents/Claude/tower_crane/toolkit/templates`. (This mirrors the hub's own `config_lib.py`
`import_base` computation — same algorithm, done by hand here since this project has no copy of
that script.) Call this value `<import_base>` — use it everywhere a path into `toolkit\` is needed
below; never hardcode the example path above. `change_requests\` (Step 5) lives directly under the
**hub root**, not inside `toolkit\` — keep the two paths distinct.

## Step 1 — Inventory this project
- Read this project's `CLAUDE.md` (if any). Identify **pasted shared-workflow prose** — checkpoint /
  resume / archive routines, change-request / filing instructions, compliance instructions — that
  duplicates the shared templates. This is the frozen copy we are replacing with live imports.
- Read `.claude\settings.json` (if any). Note any hook whose command points under
  `tower_crane\hooks\` — each is an **opted-in tool** to record in the registration request.
  (If this project only has copied prose and no such hooks, `opted_in` will be empty — that's fine.)
- Keep, untouched: the project overview, and any project-specific rules that are NOT part of the
  shared canon.

## Step 2 — Replace pasted prose with imports (non-destructive; confirm with a diff)
The shared protocol is modular. Add these `@import` lines, using the `<import_base>` computed in
Step 0 (forward-slash form — the documented, Windows-safe syntax) and **remove the now-duplicated
pasted prose** they replace:

```
@<import_base>/filing.md
@<import_base>/compliance.md
@<import_base>/continuity.md
```
(e.g. if Step 0 computed `~/Documents/Claude/tower_crane/templates`, the first line reads
`@~/Documents/Claude/tower_crane/templates/filing.md`.)

- `filing.md` (**mandatory**) — how to report bugs/improvements in shared tools up the change-request
  channel. Replaces any pasted filing/change-request prose.
- `compliance.md` (**mandatory**) — surfaces `COMPLIANCE_GUIDANCE.md` at session start / on `resume`.
  This is what lets the shared side's audit reach this project; without it, guidance files are never
  seen. There is almost certainly no pasted equivalent (this protocol post-dates most copies) — just
  add it.
- `continuity.md` (**default-on**) — checkpoint / resume / archive conventions. Replaces the pasted
  checkpoint/resume/archive prose. **Omit only** if this project deliberately manages continuity a
  different way; if so, tell the user it's being skipped and why.

Put them under a `## Shared Workflow Protocol` heading. If this project has **no** `CLAUDE.md`, create
one: a project-overview placeholder + a `## Shared Workflow Protocol` section with the imports above.

## Step 3 — Continuity file
If you kept `continuity.md` and there is no `project_progress.md`, create the skeleton it expects:

```markdown
# Project Progress

## Current Status
_Migrated onto tower_crane <DATE>. Fill in on the next working session._

## Next Up

## Decisions
| Item | Status | Notes |
|---|---|---|

## Work Log (newest first - say "archive" anytime to move old, settled entries to project_progress_archive.md)
### <DATE>
Migrated onto the tower_crane platform via register.md: replaced pasted workflow prose with
`@import` lines and filed a registration request.
```
If `project_progress.md` already exists, leave it — just prepend a Work Log line noting the migration.

## Step 4 — One-time import-approval dialog
Tell the user: the first launch after adding `@import` lines triggers a **one-time approval dialog**.
They must **accept** it, or the imported protocol pieces won't load (declining disables `@import`
permanently for this project).

## Step 5 — File the registration request (the shared side creates the registry entry)
You **cannot** edit tower_crane files directly — that's the platform's governance rule (consumers
only *file*; the registry entry is authored in a tower_crane session). So drop a registration request
into the shared change-request inbox, inside the hub root located in Step 0 — **not** inside
`toolkit\`. Create:

`<hub root>\change_requests\<YYYY-MM-DD>_register_<slug>.md`

where `<slug>` is this project's name lowercased with every run of non-alphanumeric characters turned
into a single underscore (e.g. "My Cool Project" -> `my_cool_project`). Contents (the outer fence below
is 4 backticks only so this example can show the ticket's own 3-backtick ```yaml block; the real ticket
starts at `Status: OPEN` and uses a normal 3-backtick fence):

````markdown
Status: OPEN
Type: registration

# Register: <Full Project Name in Title Case>

Requesting registration on the tower_crane platform. Create `consumers\<slug>.md` from the block
below and append this project to MENU "In use by" for each opted-in tool.

```yaml
name: <Full Project Name in Title Case>
path: <THIS project's absolute root, forward-slash form even on Windows, e.g. C:/Users/<you>/Documents/My_Cool_Project>
owner: <your name, matching identity.git_user_name in YOUR config.local.json — omit this line entirely if you're the sole/platform owner>
registered: <YYYY-MM-DD>
opted_in:
  - tool: <tool name, e.g. consistency_check>
    since: <YYYY-MM-DD>
imported:
  - piece: filing
    since: <YYYY-MM-DD>
  - piece: compliance
    since: <YYYY-MM-DD>
  - piece: continuity
    since: <YYYY-MM-DD>
```

Notes: migrated from hand-copied prose via register.md.
````

Rules for filling the block:
- **`name`** = full title in Title Case, never an acronym (matches the registry + MENU convention).
- **`path`** = this project's absolute root in **forward-slash** form, even on Windows (the checker,
  `Test-Path`, and `Join-Path` all accept forward slash natively there too — one path convention
  across the whole repo, matching `@import` lines).
- **`owner`** = your name, matching `identity.git_user_name` in your own `config.local.json` — only
  needed if this hub has more than one contributor (multi-user); omit the line if you're the sole
  owner of this tower_crane hub.
- **`opted_in`** = one `{ tool, since }` per shared hook found in Step 1; use `opted_in: []` if none.
- **`imported`** = one `{ piece, since }` per `@import` line you added in Step 2 (drop `continuity` if
  you skipped it). `since` = today.

Once the ticket file is written and filled in, **from inside the hub root** (not `toolkit\` —
`change_requests\` belongs to the hub root's own repo, with its own remote), `git add` it, commit
(e.g. `git commit -m "Register: <slug>"`), and `git push`. The registration only reaches the shared
side once it's pushed to the hub root repo's GitHub remote — this requires write access to that
repo, not just read.

## Step 6 — Finish
- Confirm the registration request file was written into the hub root's `change_requests\` folder
  **and pushed** to its GitHub remote.
- **Delete this `register.md`** from the project root (it's a one-time courier file).
- Tell the user: the tower_crane agent will create the `consumers\<slug>.md` registry entry on its
  next session (it scans `change_requests\` for `register` tickets). After that, the shared checker can
  audit this project and, if it drifts, drop a `COMPLIANCE_GUIDANCE.md` that your `compliance.md`
  import will surface here.
