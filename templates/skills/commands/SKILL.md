<!--
Canonical Track-1 skill stub source: commands (toolkit-governed — design\optimize_ux.md).
Home: ~\Documents\Claude\tower_crane\toolkit\templates\skills\commands\SKILL.md
Scaffolded into a consumer's own project-local .claude\skills\commands\SKILL.md — not @imported;
a consumer re-copies this file (with {{IMPORT_BASE}} resolved to its own home-relative import
path, same convention as its other @import lines) to pick up a changed trigger description here.
The target this stub points at (templates\commands.md) still floats on HEAD normally; only this
stub's own trigger wording is a point-in-time copy taken at scaffold/hand-wire time. Drift check:
check_tower_crane.py's Pass B compares each consumer's stub against this file verbatim (with
{{IMPORT_BASE}} resolved) and FAILs on any mismatch — re-copy this file to clear it.
No always-resident Track-2 companion — purely on-demand, same shape as `update`.
-->
---
name: commands
description: Use when the user says "commands", asks something like "what can I do here" or
  "what commands are there", or signals they're new/confused about this project's Tower Crane
  setup — e.g. "I'm new here, what do I do", "I just got handed this project" — any phrasing
  meaning they don't already know what's available. Not a fixed keyword list.
---
Read `{{IMPORT_BASE}}/commands.md` in full and follow it exactly — which of the two response
tiers to render (a terse cheat sheet vs. a guided beginner story) depends on which phrasing
triggered this skill, both covered there. Do not paraphrase or act from memory of a previous
read; the file floats on HEAD and may have changed since you last read it.
