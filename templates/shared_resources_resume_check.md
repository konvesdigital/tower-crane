<!--
Shared protocol piece: shared_resources_resume_check.md (MANDATORY for every consumer - Track 2,
always resident). Home: ~\Documents\Claude\tower_crane\toolkit\templates\shared_resources_resume_check.md
Imported by a consumer's CLAUDE.md via:
  @~/Documents/Claude/tower_crane/toolkit/templates/shared_resources_resume_check.md
Track 2 half of shared_resources.md: a broken reference must fail loudly at the next resume, not
whenever a session happens to trigger the mechanism again. Everything else - search, browse,
select, apply, save, forget, archive - lives in the `shared_resources` skill (project-local
.claude\skills\shared_resources\SKILL.md, pointing at templates\shared_resources.md), loaded only
on the exact trigger phrase "shared resources." Keep this file terse and project-agnostic.

This file explains how to use the mechanism it covers. `capability_relationships` explains how
this mechanism works and how it relates to other mechanisms.
-->

## Checking adopted shared_resources references

Only relevant if this project has adopted a `reference`/`tool` entry (or an `insight` whose
Track-1 destination still carries a live reference) - otherwise skip both procedures below.

Awareness of an adopted resource is controlled entirely by its own Skill stub (name+description
always resident, regardless of `resume` vs `quick resume`) - the checks below are pure
maintenance, catching a broken or stale reference, never whether the agent knows to use one.

### At `resume`

Run, chained into one call (`design\command_procedure_audit.md`'s consumer-side sweep, finding
B4 — the same "stop reconstructing a fixed two-call sequence from prose every time" fix B1 already
applied to `resume` step 3):

```
python <hub root>\toolkit\scripts\shared_resource_resume_check.py --project-root <this project's
root>
```

(`<hub root>` = whatever this file's own `@import` line resolves to, one level above its
`toolkit\`.) Runs, in order, what used to be two separately prose-sequenced calls:

- `check_shared_resource_refs.py` - a deterministic existence check covering both adopted forms: a
  literal `@import` line into `shared_resources\`, and a `~/...`-form path inside a project-local
  `.claude\skills\<name>\SKILL.md` stub (the Track-1 "Apply" form). `[FAIL]` on a broken target -
  report plainly, never silently (per "Shared resources folder maintenance" in
  `shared_resources.md`). Out of scope: a `tool`-kind entry adopted as free-text "pointer note"
  prose (no fixed shape to check); an adopted `insight` (its content was copied/adapted in,
  nothing left pointing back).

  Also prints `[HOST-GAP]` for a `tool`/pointer-`reference` entry whose `Hosts:` block doesn't
  list this machine - notify-only, never causes a failure exit. On a `[HOST-GAP]`, present the
  ignore / connect-now / proceed-and-re-ask remedy from `shared_resources.md`'s "Per-host
  availability for pointer entries" - don't silently skip past it.

- `check_shared_resource_drift.py` - notify-only (`[DRIFT]`, always exits 0). Compares the sha256
  stamped into a Track-1 stub's adoption marker at Apply time against the source entry's current
  content. On `[DRIFT]`: re-read the named source file, and only if it's genuinely grown a topic
  the stub's trigger doesn't cover, redraft the trigger and confirm with the user before
  overwriting, then re-run the underlying script (not the chained wrapper — see its own
  `--project-root` usage) so the marker's hash reflects the new content. `[N/A]` (no
  `index-sha256` in the marker - an `insight` adoption, a pre-existing stub, or a free-text `tool`
  adoption) is not a gap.

Both checks are guaranteed side-effect-free and always exit 0 (notify-only), so this consolidated
call does no pass/fail interpretation of its own — read each check's own output per the rules
above, same "consolidate the CALL, not the interpretation" split the rest of this hub's chained
resume checks already use.

### At `quick resume`

**Skip both scripts entirely.** They're maintenance, not awareness (see above) - the same
reasoning `continuity_resume_check.md` uses to skip its own hub-sync steps: a session reopened
seconds after its own `checkpoint` has nothing new to find. No tag or disclaimer noting the skip.
Use plain `resume` instead at the start of a day or after any gap long enough that a reference
could actually have broken or a source file could actually have drifted.
