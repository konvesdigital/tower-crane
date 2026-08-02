<!--
Shared protocol piece: update.md (OPTIONAL / self-scaffolding for every consumer - Track 1,
on-demand, no always-resident companion - design\consumer_update.md).
Home: ~\Documents\Claude\tower_crane\toolkit\templates\update.md
Reached via a thin skill stub at .claude\skills\update\SKILL.md (sourced from
toolkit\templates\skills\update\SKILL.md), same copy-and-substitute pattern as filing/checkpoint/
archive. Float-on-HEAD: this file is the one canonical source the stub always re-reads live. Keep
this file project-agnostic - it must read correctly from ANY consumer. Refer to "this project",
never a specific consumer name.
-->

## Pulling in new hub features this project hasn't adopted yet

This project imports mandatory/default-on pieces from a local **tower_crane** hub at scaffold or
registration time, but a hub feature that ships *after* that point (a new hook, a new
`shared_resources\` entry, a new toolkit Track-1 skill, a new mandatory/default-on protocol piece)
never retroactively reaches an already-set-up project on its own. `update` is the on-demand,
pull-only fix: run it whenever you want to check, never automatically, and never at `resume` (no
staleness nagging by design - see `design\consumer_update.md`'s "Staleness nagging" decision).

You reached this file via a skill stub whose own path resolved somewhere under a `toolkit\`
folder. That `toolkit\` folder's parent is **the hub root** (where `shared_resources\` lives); the
concrete path to `scripts\scan_consumer_update.py` below is `toolkit\scripts\scan_consumer_update.py`
relative to the same `toolkit\` you're inside right now.

### Step 1 — scan

Run, from anywhere, substituting this project's own absolute root:

```
<python_launcher> "<hub root>\toolkit\scripts\scan_consumer_update.py" --project-root "<this project's absolute root>"
```

This is a deterministic scan - no hub-side read dependency beyond files already on disk, no
trust-review gate (unlike the hub's own `update`, which pulls from a public remote; this source is
the same local hub this project already imports mandatory pieces from at the same trust level).
It checks this project's own local state directly (`.claude\settings.json`, `CLAUDE.md` `@import`
lines, `.claude\skills\` listing) against four categories of hub-side surface:

| Category | What "available" means |
|---|---|
| Hook | A `MENU.md` hook this project hasn't opted into |
| Toolkit skill | A `toolkit\templates\skills\*\` Track-1 skill not present under `.claude\skills\` |
| Protocol piece | `filing`/`compliance`/`continuity` not `@import`ed (flat or Track-1 form) |
| Shared-resources insight | An active (non-archived) `shared_resources\CATALOG.md` entry with no adoption marker found in this project |

It prints an indexed, categorized list. If it's empty, this project already has everything the hub
currently offers - stop here.

### Step 2 — present the list and ask

Show the printed list to the user as-is and ask which items (if any) to adopt: all, some (by
number), or none. Nothing chosen is nothing lost - an unpicked item just stays available for a
future run; the scan is always freshly recomputed, nothing to track in between.

If a **protocol piece** item appears for something this project deliberately opted out of (e.g. it
manages continuity a different way - register.md's own "omit only if..." caveat), say so and skip
it rather than assuming it should be adopted.

### Step 3 — apply

For a chosen **hook**, **toolkit skill**, or **protocol piece** item, re-run the same script with
`--apply`:

```
<python_launcher> "<hub root>\toolkit\scripts\scan_consumer_update.py" --project-root "<this project's absolute root>" --apply <numbers-or-'all'>
```

`<numbers>` are the printed item numbers (comma-separated), e.g. `--apply 1,3`, or `--apply all`
for every mechanically-applicable item. This performs the actual write - the same mechanic each
item type already uses elsewhere in this platform (a hook's opt-in JSON merge, a Track-1 skill's
verbatim-copy-plus-`{{IMPORT_BASE}}`-substitution, a protocol piece's `@import` line) - nothing new
to learn.

For a chosen **shared-resources insight**, do **not** use `--apply` - `scan_consumer_update.py`
deliberately skips these with a pointer, since adopting an insight is a negotiated draft (a
retrieval hook and summary shaped for this project, confirmed before writing), not a mechanical
copy. Instead follow `templates\shared_resources.md`'s own "Applying an insight" procedure for
that entry (e.g. say "shared resources — apply `<entry name>`").

### Step 4 — tell the hub about what changed (hooks and toolkit skills only)

After an `--apply` that touched a **hook** or a **toolkit skill**, the script prints a
`[reminder]` line — the hub's own `consumers\<slug>.md` registry entry doesn't know about the
change yet, and two things there actually depend on it staying accurate: `scripts\relocate.py`
regenerating hook commands after a machine move, and the "who's opted in" check before a
behavior-changing shared-tool edit. File a short registration-update ticket the same way
`templates\filing.md` describes (a lightweight ticket, not a bug report), naming what was added.
**Not needed** for a `shared_resources` insight (already self-auditing, independent of the
registry) or a flat `@import`-only protocol piece like `compliance` (a live reference, nothing
copied to go stale) — see `design\consumer_update.md`'s "Does registry write-back actually
matter?" for the full reasoning.
