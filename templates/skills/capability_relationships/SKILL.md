<!--
Canonical Track-1 skill stub source: capability_relationships (toolkit-governed —
design\capability_relationships.md).
Home: ~\Documents\Claude\tower_crane\toolkit\templates\skills\capability_relationships\SKILL.md

Unlike every other Track-1 skill so far, this ONE canonical stub is distributed through BOTH
mechanisms rather than forking into a consumer/hub pair (contrast commands/hub_commands, which are
two separate files): scaffolded into a consumer's .claude\skills\capability_relationships\SKILL.md
via new_consumer.py's STANDALONE_SKILLS (same copy-and-substitute pattern as commands/update), AND
installed into THIS hub's own .claude\skills\capability_relationships\SKILL.md via self_hooks.py's
"skills" opt-in key (templates\optins\capability_relationships.json). This only works because
self_hooks.py resolves the substitution placeholder below the same way new_consumer.py does (using
this same hub's own computed import_base) before writing the installed copy — extended for this
skill rather than left unsubstituted like the earlier hub_commands precedent, since hub_commands's
body has no such placeholder to begin with and never needed it. Drift check for either
distribution path compares the installed copy against this file with that placeholder resolved the
same way: check_tower_crane.py's Pass B (consumers) and its Hub self-use skill drift check (this
hub).

NOTE for anyone editing this file: never write the literal two-brace placeholder token as prose
inside this comment block (like this note is carefully NOT doing) — self_hooks.py's and
new_consumer.py's substitution is a blind whole-file string replace, so any literal occurrence
gets substituted too, corrupting the comment. Only the one instruction line below should carry it.
-->
---
name: capability_relationships
description: Use when the question is about a specific Tower Crane mechanism or concept — a named
  capability ("what does `update` do", "what is `curate shared resources`") or a described need
  that names none ("how do I get the newest version of what I build in the hub into this
  project"). Not for broad "what can I do here"/"what's next"/"I'm new here" language — that's
  `commands`/`hub_commands`' job instead.
---
Read `{{IMPORT_BASE}}/capability_relationships.md` in full and follow it exactly — matching the
query to the capability graph, answering directly, and surfacing its nearest structural/thematic
neighbors are all covered there. Do not paraphrase or act from memory of a previous read; the file
floats on HEAD and may have changed since you last read it.
