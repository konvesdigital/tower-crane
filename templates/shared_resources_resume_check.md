<!--
Shared protocol piece: shared_resources_resume_check.md (MANDATORY for every consumer - Track 2,
always resident). Home: ~\Documents\Claude\tower_crane\toolkit\templates\shared_resources_resume_check.md
Imported by a consumer's CLAUDE.md via:
  @~/Documents/Claude/tower_crane/toolkit/templates/shared_resources_resume_check.md
Split out of shared_resources.md on 2026-08-01 (design\directive_economy.md's "shared_resources.md's
own mechanism moves to Track 1" - a dangling thread from that doc's own "Two homes within Track 1"
section, raised 2026-07-30 and never actually built until now). This is the one piece of the old
shared_resources.md that genuinely can't wait for the model to notice a "shared resources"-shaped
moment - a broken reference must fail loudly at the next resume, not whenever a session happens to
trigger the mechanism again. Everything else - search, browse, select, apply, save, forget, archive -
lives in the `shared_resources` skill (project-local `.claude\skills\shared_resources\SKILL.md`,
pointing at templates\shared_resources.md), loaded only on the exact trigger phrase "shared
resources." Keep this file terse and project-agnostic.
-->

## Checking adopted shared_resources references (resume)

Only relevant if this project has actually adopted a `reference`/`tool` entry (or an `insight`
applied via the Track-1 skill-stub destination that still needed one - see the `shared_resources`
skill's own Apply procedure, most insight destinations don't carry a live reference at all) -
otherwise skip this. At `resume`, run `python <hub root>\toolkit\scripts\check_shared_resource_refs.py
--project-root <this project's root>` (the `<hub root>` prefix is whatever this file's own `@import`
line resolves to, one level above its `toolkit\`). It's a deterministic file-existence check, not an
LLM judgment call - zero tokens either way, and it catches 100% of the case it checks rather than
relying on this session noticing on its own. It covers two adopted forms: a literal `@import` line
pointing into `shared_resources\`, and a `~/...`-form path referenced inside a project-local
`.claude\skills\<name>\SKILL.md` stub (the Track-1 form "Apply" produces - see the `shared_resources`
skill). Either form gets a `[FAIL]` if its target no longer exists; report any `[FAIL]` to the user
plainly (per "Shared resources folder maintenance" in `shared_resources.md` - a broken reference must
never fail silently). Out of scope by design: a `tool`-kind entry adopted as free-text "pointer note"
prose with no fixed shape (not a literal `@import` line and not a backtick-quoted `~/...` path inside
a skill stub); an adopted `insight`, since its content was copied/adapted into this project rather
than referenced live, so there's nothing left pointing back at `shared_resources\` for this check to
verify. Separately, a skill stub's **trigger description** going stale relative to its source entry's
current topic footprint is a different, non-existence concern - see `design\directive_economy.md`'s
"Drift mechanics" for why that's notify-only and not covered by this existence check.

Same `resume`, also run `python <hub root>\toolkit\scripts\check_shared_resource_drift.py
--project-root <this project's root>` - the notify-only counterpart just named above. It compares the
sha256 stamped into a Track-1 stub's adoption marker at Apply time against the source entry file's
current content; a mismatch prints `[DRIFT]` but the script always exits 0, so it never blocks
`resume` the way a `[FAIL]` from `check_shared_resource_refs.py` does. On a `[DRIFT]` line: re-read
the named source file, compare its current topic footprint against the flagged stub's existing
trigger description, and - only if it's genuinely grown a topic the trigger doesn't cover - redraft
the trigger and confirm with the user before overwriting the stub (same confirm-before-write pattern
`shared_resources.md` requires for every write), then re-run the script so the marker's hash reflects
the new current content. A stub with no `index-sha256` in its marker (an `insight` adoption, a
pre-existing stub predating this check, or a free-text `tool` adoption) prints `[N/A]` - out of scope,
not a gap.
