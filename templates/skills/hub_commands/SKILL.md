<!--
Canonical Track-1 skill stub source: hub_commands (toolkit-governed — design\optimize_ux.md).
Home: ~\Documents\Claude\tower_crane\toolkit\templates\skills\hub_commands\SKILL.md

Unlike every other Track-1 skill (filing/checkpoint/archive/update/commands), this one is NOT
scaffolded into consumer projects by new_consumer.py — the hub is not a registered consumer of
its own scaffolder. It reaches THIS hub's own .claude\skills\hub_commands\SKILL.md purely through
self_hooks.py's per-tool opt-in mechanism (`self_hooks.py --enable hub_commands`), off by default,
per-machine — see templates\optins\hub_commands.json. Because self-use only ever targets this one
repo (never a floating consumer path), the copy is byte-for-byte verbatim — no {{IMPORT_BASE}}
substitution, unlike the consumer-side pattern. Drift check: check_tower_crane.py's hub self-use
skill check compares the installed copy against this file verbatim and FAILs on any mismatch —
re-run `self_hooks.py --enable hub_commands` to refresh it.
-->
---
name: hub_commands
description: Use when the operator says "commands", asks something like "what can I do here" or
  "what commands are there", or signals they're new to operating this hub — e.g. "I'm new here,
  what do I do", "I just set up tower_crane, now what" — any phrasing meaning they don't already
  know what's available. Not a fixed keyword list.
---
Read `toolkit\templates\hub_commands.md` in full and follow it exactly — which of the two response
tiers to render (a terse cheat sheet vs. a guided beginner story) depends on which phrasing
triggered this skill, both covered there. Do not paraphrase or act from memory of a previous read;
the file floats on HEAD and may have changed since you last read it.
