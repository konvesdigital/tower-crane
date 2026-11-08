<!--
Shared protocol piece: update.md (OPTIONAL / self-scaffolding for every consumer - Track 1,
on-demand, no always-resident companion).
Home: ~\Documents\Claude\tower_crane\toolkit\templates\update.md
Reached via a thin skill stub at .claude\skills\update\SKILL.md (sourced from
toolkit\templates\skills\update\SKILL.md), same copy-and-substitute pattern as filing/checkpoint/
archive. Float-on-HEAD: this file is the one canonical source the stub always re-reads live. Keep
this file project-agnostic - it must read correctly from ANY consumer. Refer to "this project",
never a specific consumer name.

This file explains how to use the mechanism it covers. `capability_relationships` explains how
this mechanism works and how it relates to other mechanisms.
-->

## Pulling in new hub features this project hasn't adopted yet

This project imports mandatory/default-on pieces from a local **tower_crane** hub at scaffold or
registration time, but a hub feature that ships *after* that point (a new hook, a new toolkit
Track-1 skill, a new mandatory/default-on protocol piece) never retroactively reaches an
already-set-up project on its own. `update` is the on-demand, pull-only fix: run it whenever you
want to check, never automatically, and never at `resume` (no staleness nagging, by design).

**Scope is functionality, not data.** `update` exists to bring this project to *functionality
parity with a project scaffolded fresh today* - the same hooks, toolkit skills, and protocol
pieces `new_consumer.py` would wire in right now. It never touches `shared_resources\` content,
which is data, not functionality.

You reached this file via a skill stub whose own path resolved somewhere under a `toolkit\`
folder. That `toolkit\` folder's parent is **the hub root** (where `shared_resources\` lives); the
concrete path to `scripts\scan_consumer_update.py` below is `toolkit\scripts\scan_consumer_update.py`
relative to the same `toolkit\` you're inside right now.

### Step 1 — scan

Fill in the three placeholders used here and in Steps 3 and 4 (and in `continuity.md`'s
`checkpoint` command, which points back to this step):
- `<python_launcher>` = the `python_launcher:` value in this project's own `.claude\hub_pointer.md`
  (`Read` that file; use the value exactly as written).
- `<hub root>` = the folder one level above the `shared_root:` value in the same file (`shared_root:` is the `toolkit` folder itself).
- `<this project's absolute root>` = the folder that contains this project's `CLAUDE.md`.

Then run, as one bare command (no pipes):

```
<python_launcher> "<hub root>/toolkit/scripts/scan_consumer_update.py" --project-root "<this project's absolute root>"
```

This is a deterministic scan - no hub-side read dependency beyond files already on disk, no
trust-review gate (unlike the hub's own `update`, which pulls from a public remote; this source is
the same local hub this project already imports mandatory pieces from at the same trust level).
It checks this project's own local state directly (`.claude\settings.json`, `CLAUDE.md` `@import`
lines, `.claude\skills\` listing) against three categories of hub-side surface - every one of them
something `new_consumer.py` would wire into a brand-new consumer today:

| Category | What "available" means |
|---|---|
| Hook | A `MENU.md` hook this project hasn't opted into (a hook whose opt-in names a narrower `audience`, such as `blind_clone`, is never offered) |
| Toolkit skill | A `STANDALONE_SKILLS` Track-1 skill (`update`, `commands`) not present under `.claude\skills\` |
| Protocol piece | `filing`/`compliance`/`continuity` not `@import`ed (flat or Track-1 form) |

It also compares this project's `CLAUDE.md` `## Tower Crane In Use` / `## Shared Workflow Protocol`
block against what the current template would produce and lists each difference as a **CLAUDE.md block
deviation**, showing the exact text that patching removes and what goes in.

It prints an indexed list under plain headings that say what is wrong with each item: **REMOVE**
(in place but shouldn't be), **REPLACE** (in place but out of date), **ADD** (should be there but is
missing), and **FIX BY HAND**. Keep those headings when you show it. Anything that merely *could* be
added (a private tool this project never opted into) is not numbered or applied by `all`; the script
ends with one "Optional, not listed" line instead. Relay that line, but treat it as information: do
not recommend or ask about those items unless the user does (`--include-optional` lists them, on the
`--apply` call too, so the numbers match). If the list is empty, this project already has everything
the hub currently expects - stop here (but still relay the exceptions reminder line, if the script
printed one).

### Step 2 — present the list and ask

Show the printed list to the user as-is and ask which items (if any) to adopt: all, some (by
number), or none. Nothing chosen is nothing lost - an unpicked item just stays available for a
future run; the scan is always freshly recomputed, nothing to track in between.

If a **protocol piece** item appears for something this project deliberately opted out of (e.g. it
manages continuity a different way - register.md's own "omit only if..." caveat), say so and skip
it rather than assuming it should be adopted.

For **CLAUDE.md block deviations**, say plainly that patching removes the custom text shown (custom
text can break Tower Crane), and recommend `all`. If the user wants to keep a deviation, that is a
separate, explicit choice (`--keep <n>` in Step 3), not a way of declining.

### Step 3 — apply

For a chosen **hook**, **toolkit skill**, **protocol piece**, or **CLAUDE.md block deviation** item,
re-run the same script with `--apply`:

```
<python_launcher> "<hub root>/toolkit/scripts/scan_consumer_update.py" --project-root "<this project's absolute root>" --apply <numbers-or-'all'>
```

`<numbers>` are the printed item numbers (comma-separated), e.g. `--apply 1,3`, or `--apply all`
for every mechanically-applicable item. This performs the actual write - the same mechanic each
item type already uses elsewhere in this platform (a hook's opt-in JSON merge, a Track-1 skill's
verbatim-copy-plus-`{{IMPORT_BASE}}`-substitution, a protocol piece's `@import` line) - nothing new
to learn.

To **keep** a block deviation instead of patching it, add `--keep <n>` (e.g. `--apply all --keep 4`
means everything except item 4; `--keep 4` alone records only that). The script writes the kept text to
`.claude\tower_crane_exceptions.json` in this project, prints a warning that Tower Crane may not behave
100% as expected, and never lists that text again. Relay the warning.

If the user says **"reset exceptions"**, run the Step 1 command with `--reset-exceptions` added: it
clears this project's recorded exceptions and lists them as ordinary deviations again; then continue
from Step 2 (patch all is the default). Never reset on your own.

### Step 4 — tell the hub about what changed (hooks and toolkit skills only)

After an `--apply` that touched a **hook** or a **toolkit skill**, the script prints a
`[reminder]` line — the hub's own `consumers\<slug>.md` registry entry doesn't know about the
change yet, and two things there actually depend on it staying accurate: `scripts\relocate.py`
regenerating hook commands after a machine move, and the "who's opted in" check before a
behavior-changing shared-tool edit. File a short registration-update ticket the same way
`templates\filing.md` describes (a lightweight ticket, not a bug report), naming what was added.
**Not needed** for a flat `@import`-only protocol piece like `compliance` (a live reference,
nothing copied to go stale — registry write-back only matters for content that's actually copied).

### Step 5 — close

Finish with exactly this line: `Update: <n> applied | <n> skipped | hub registry: <ticket filed | not needed>`.

If the script printed an exceptions reminder (`N CLAUDE.md exceptions kept — say "reset exceptions" ...`),
repeat it verbatim on the line after. It is information only: ask nothing, offer nothing else.
