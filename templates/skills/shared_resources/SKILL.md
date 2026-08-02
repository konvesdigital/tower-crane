<!--
Canonical Track-1 skill stub source: shared_resources (toolkit-governed - design\directive_economy.md,
MANDATORY for every consumer since 2026-08-01 - design\resource_sharing_model.md's "Mechanism
delivery: mandatory, not optional").
Home: ~\Documents\Claude\tower_crane\toolkit\templates\skills\shared_resources\SKILL.md
Scaffolded into a consumer's own project-local .claude\skills\shared_resources\SKILL.md - not
@imported; a consumer re-copies this file (with {{IMPORT_BASE}} resolved to its own home-relative
import path, same convention as its other @import lines) to pick up a changed trigger description
here. The target this stub points at (templates\shared_resources.md) still floats on HEAD normally;
only this stub's own trigger wording is a point-in-time copy taken at scaffold/hand-wire time. Drift
check: check_tower_crane.py's Pass B compares each consumer's stub against this file verbatim (with
{{IMPORT_BASE}} resolved) and FAILs on any mismatch - re-copy this file to clear it.

DELIBERATELY NOT autonomous relevance-matching, unlike filing/checkpoint/archive: this skill governs
the "shared resources" CATALOG-MANAGEMENT command only (search/browse/select/apply/save/forget/
archive) - a real cross-project gear-switch that must be unmistakable, never inferred from a keyword
buried mid-sentence (templates\shared_resources.md's own "Entering shared-resources context"
section). It must NOT fire just because a topic that might relate to a shared resource comes up -
that's what an ALREADY-ADOPTED individual resource's own separate skill stub is for (autonomous,
fuzzy, exactly like filing/checkpoint), created by this skill's own "Apply" procedure. Keep the
description below's exact-phrase framing intact when re-copying; do not loosen it to match the other
skills' style.
-->
---
name: shared_resources
description: Use ONLY when the user says the exact phrase "shared resources" as the substance of
  their message (e.g. leading the message, or immediately followed by the actual request in the
  same breath) - never when the words merely appear in passing, and never just because the current
  topic seems related to something that might be in the catalog. This is a deliberate context-switch
  trigger to the cross-project search/browse/select/apply/save/forget/archive command, not
  autonomous relevance-matching.
---
Read `{{IMPORT_BASE}}/shared_resources.md` in full and follow it exactly - entering the context,
search/browse, select, apply, save, forget, and archive are all covered there. Do not paraphrase or
act from memory of a previous read; the file floats on HEAD and may have changed since you last read
it.
