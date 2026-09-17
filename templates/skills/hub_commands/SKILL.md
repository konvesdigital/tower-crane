<!--
Canonical Track-1 skill stub source: hub_commands (toolkit-governed).
Home: ~\Documents\Claude\tower_crane\toolkit\templates\skills\hub_commands\SKILL.md

Not scaffolded into consumer projects. Reaches this hub's own
.claude\skills\hub_commands\SKILL.md via self_hooks.py's per-tool opt-in
(`self_hooks.py --enable hub_commands`), off by default, per-machine — see
templates\optins\hub_commands.json. No substitution placeholder — the target path below is a
plain literal.
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
