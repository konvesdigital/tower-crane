<!--
Canonical Track-1 skill stub source: capability_relationships (toolkit-governed —
design\capability_relationships.md).
Home: ~\Documents\Claude\tower_crane\toolkit\templates\skills\capability_relationships\SKILL.md

Unlike every other Track-1 skill so far, this ONE canonical stub is distributed through BOTH
mechanisms rather than forking into a consumer/hub pair (contrast commands/hub_commands, which are
two separate files): scaffolded into a consumer's .claude\skills\capability_relationships\SKILL.md
via new_consumer.py's STANDALONE_SKILLS (same copy-and-substitute pattern as commands/update), AND
installed into THIS hub's own .claude\skills\capability_relationships\SKILL.md via self_hooks.py's
"skills" opt-in key (templates\optins\capability_relationships.json).

The {{READ_INSTRUCTION:capability_relationships.md}} placeholder below renders to ONE of two forms
depending on use_pointer (design\consumer_reference_indirection.md), same mechanism and same
convention every other Track-1 skill stub already uses: the direct-substitution wording
(not-yet-migrated consumers, the default) or the .claude\hub_pointer.md-indirected wording (new
connections). Both are independently valid canonical shapes - check_tower_crane.py's Pass B accepts
either. **This hub's own self-install via self_hooks.py is unaffected either way** - its calls into
materialize_skill_stub() never pass use_pointer, so they always resolve to the direct-substitution
form (using this same hub's own computed import_base), which is exactly the wording this template
produced before this stub gained the placeholder - the hub has no hub_pointer.md concept for
itself, and nothing here changes that. (Originally left as a permanent direct-substitution-only
exception for this reason - design\consumer_reference_indirection.md's Decisions table, 2026-08-14
- revisited and closed once it was confirmed the two concerns are actually independent: consumer
distribution can use the placeholder freely without touching self_hooks.py's call site at all.)

NOTE for anyone editing this file: never write the literal two-brace placeholder token as prose
inside this comment block - materialize_skill_stub() strips this whole header comment before doing
any substitution, so a stray literal occurrence here would survive into confusing maintainer-only
noise rather than being resolved. Only the one instruction line below should carry it.
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
