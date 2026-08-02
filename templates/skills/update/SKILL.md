<!--
Canonical Track-1 skill stub source: update (toolkit-governed — design\consumer_update.md).
Home: ~\Documents\Claude\tower_crane\toolkit\templates\skills\update\SKILL.md
Scaffolded into a consumer's own project-local .claude\skills\update\SKILL.md — not @imported;
a consumer re-copies this file (with {{IMPORT_BASE}} resolved to its own home-relative import
path, same convention as its other @import lines) to pick up a changed trigger description here.
The target this stub points at (templates\update.md) still floats on HEAD normally; only this
stub's own trigger wording is a point-in-time copy taken at scaffold/hand-wire time. Drift
check: check_tower_crane.py's Pass B compares each consumer's stub against this file verbatim
(with {{IMPORT_BASE}} resolved) and FAILs on any mismatch — re-copy this file to clear it.
Unlike filing/checkpoint/archive, this skill has no always-resident Track-2 companion piece — it
is purely on-demand, never a resume-time check (design\consumer_update.md's "no nagging, ever").
-->
---
name: update
description: Use when the user says "update" or asks to check for new tower_crane hub
  functionality (hooks, toolkit skills, protocol pieces) this project hasn't adopted yet. Not for
  shared_resources content - that's the "shared resources" command's own job.
---
Read `{{IMPORT_BASE}}/update.md` in full and follow it exactly — scanning what's available,
presenting the list, and applying chosen items are all covered there. Do not paraphrase or act
from memory of a previous read; the file floats on HEAD and may have changed since you last read
it.
