<!--
Canonical Track-1 skill stub source: capability_relationships (toolkit-governed).
Home: ~\Documents\Claude\tower_crane\toolkit\templates\skills\capability_relationships\SKILL.md

Distributed through both mechanisms: scaffolded into a consumer's
.claude\skills\capability_relationships\SKILL.md via new_consumer.py's STANDALONE_SKILLS, AND
installed into this hub's own .claude\skills\capability_relationships\SKILL.md via self_hooks.py's
"skills" opt-in key (templates\optins\capability_relationships.json). This hub's own self-install
always resolves to the direct-substitution form (this hub has no hub_pointer.md concept for
itself).

Never write the literal two-brace placeholder token as prose inside this comment block -
materialize_skill_stub() strips this whole header comment before substitution, so a stray literal
occurrence here would survive unresolved. Only the one instruction line below should carry it.
-->
---
name: capability_relationships
description: A structured map of every Tower Crane capability and how they relate to each other —
  not a flat list, a graph. Use when a question is about what a specific mechanism does, how
  mechanisms compare or differ, or how to accomplish something whose name the user doesn't know —
  a named capability ("what does `update` do", "what is `curate shared resources`") or a described
  need that names none ("how do I get the newest version of what I build in the hub into this
  project", "can I build stuff that applies to all my projects connected to tower crane"). Not for
  broad "what can I do here"/"what's next"/"I'm new here" language — that's `commands`/
  `hub_commands`' job instead.
---
{{READ_INSTRUCTION:capability_relationships.md}} and follow it exactly — matching the query to the
capability graph, answering directly, and surfacing its nearest structural/thematic neighbors are
all covered there. Do not paraphrase or act from memory of a previous read; the file floats on HEAD
and may have changed since you last read it.
