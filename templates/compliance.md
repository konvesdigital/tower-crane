<!--
Shared protocol piece: compliance.md (MANDATORY for every consumer).
Home: ~\Documents\Claude\tower_crane\templates\compliance.md
Imported by a consumer's CLAUDE.md via:
  @~/Documents/Claude/tower_crane/templates/compliance.md
RECEIVE side of the two-way compliance channel: check_tower_crane.py writes '## Checker
deviations', broadcast_guidance.py writes '## Broadcast', both into this project's
COMPLIANCE_GUIDANCE.md. Neither ever edits this project's live files directly. Mandatory so even a
project that opts out of continuity still receives guidance. Keep project-agnostic.

This file explains how to use the mechanism it covers. `capability_relationships` explains how
this mechanism works and how it relates to other mechanisms.
-->

## Shared-tools compliance guidance

The tower_crane repo audits this project from the outside and, when it finds a deviation from
how a properly-configured consumer should look, drops a file named **`COMPLIANCE_GUIDANCE.md`**
in this project's root. It **never edits this project's files** — it only writes that one
guidance file. Acting on it is your job, with the user's confirmation.

**The file can carry up to two independent, separately-headed sections** — a `## Checker
deviations` section (computed by auditing this project against the consumer baseline) and a
`## Broadcast` section (a one-off, hand-authored notice pushed to every registered project at
once). Either section may be present alone, or both at the same time. Treat them as **fully
independent** — resolve, decline, and remove them one at a time; never delete the whole file
unless *both* sections are gone.

**At session start (and whenever you run `resume`):** check whether `COMPLIANCE_GUIDANCE.md`
exists in the project root. If it does, for **each section present**:

1. Read it and, for each proposed change, show the **literal proposed text verbatim** (exact
   import line, hook command, config block) **alongside** a plain-language explanation of what it
   does and why. Show both together, always — never a paraphrase alone, never the raw text alone.
2. **Ask the user whether to apply them.** Do not apply silently — this is a human-in-the-loop
   gate, and you have full context on this project that the shared side does not.
3. On **yes**: apply the changes, confirm what you did, then **delete just that section**
   (its `## Heading` line and body) from `COMPLIANCE_GUIDANCE.md`. If that was the only section
   left, delete the file entirely.
4. On **no**: leave that section in place; it'll resurface next session (re-running the
   originating tool overwrites only its own section, and a now-resolved one simply stops being
   written — the other section, if any, is untouched either way).

If the guidance flags a *rogue override* — a local instruction in this project that deliberately
contradicts shared prose — it is surfaced for the user to judge, never auto-changed. Removing an
import line or overriding a shared rule locally is always a legitimate choice; the guidance is a
tripwire, not a lock.
