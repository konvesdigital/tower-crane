<!--
Canonical hub-operator content: hub_commands.md (design\optimize_ux.md). Reached via a thin skill
stub at .claude\skills\hub_commands\SKILL.md, installed only through self_hooks.py's per-tool
opt-in mechanism (templates\optins\hub_commands.json's "skills" key) — off by default, per-machine,
same as every other self-use tool. Float-on-HEAD: this file is the one canonical source the stub
always re-reads live. This file describes THIS hub's own operator-facing capabilities — it never
governs a consumer project's session (that's templates\commands.md instead).
-->

## Answering "what can I do here" from a hub-operator session

Nobody has to already know the exact trigger phrase for anything below - this file is what a
"commands"-shaped query from the hub operator draws from. **Never dump the whole picture.** Give
a direct answer to what was actually asked, plus the single next-best follow-up - never more.

**Which of the two tiers below to render is picked by the phrasing that triggered this skill, not
by any other signal:**
- An exact, already-fluent phrasing (**"commands"**, "what commands are there") → the **fluent
  tier**: a terse cheat sheet.
- A confused/new-to-this phrasing (**"I'm new here, what do I do"**, "I just set up tower_crane,
  now what") → the **beginner tier**: a guided sequential story, not a list.

Both tiers draw from the same underlying capability set below - only the rendering differs.

### Fluent tier - cheat sheet

One reply, grouped by track header, each line a bare command/phrase plus a one-line action. No
follow-up turn required.

```
commands

Efficiency habits:
  checkpoint — save state and push
  resume — pull state, check for updates
  quick resume — thin resume right after a checkpoint

Toolkit evolution:
  new tool — add a tool to the shared library
  modify tool — change/remove an existing tool
  propose upstream — send a local fix to the public repo
  update — pull the public repo's latest
  self hooks — toggle this hub's own dogfooding

Fleet operations:
  connect project — register a new or existing consumer
  update consumers — bulk-push new hub functionality to every registered consumer
  curate shared resources — push an insight to every consumer
  set up automation — wire up unattended ticket processing
```

### Beginner tier - guided story

Narrated as a sequential story pulled from the discovery-order track ("first do X, then Y, then
Z"), not a topical listing - answers "what's first," not "here's everything."

```
I'm new here, what do I do?

First, get the hub running: say "set up tower crane" and I'll walk you through it.
Once that's done, connect your first project: say "connect project" and tell me if it's new or
already exists.
After that, the two habits worth learning early are "checkpoint" (save your progress) and
"resume" (pick back up next session).

You can say "commands" any time to see everything else.
```

### Reciprocal pairs to volunteer

Per the reciprocal-tracks rule (design\optimize_ux.md): when a query lands on one side of a pair
below, volunteer the other side as the single next-best follow-up - don't wait to be asked.

| If the query is about... | ...also mention |
|---|---|
| `checkpoint` | `resume` (and vice versa) |
| `update` (pulling the public repo in) | `propose upstream` (pushing a local fix back out) |
| processing a filed ticket | the reverse is a consumer's own `filing` skill - "that's how a project gets a ticket to you in the first place" |
| `self hooks` (what's turned on for this hub itself) | a consumer project has the same question about its own opted-in tools, asked from inside that project |
| `curate shared resources` (this hub pushing an insight to every consumer) | a consumer can already pull the same thing on its own via its own `shared resources` search/browse - curation is an accelerant, not a requirement |
| `new tool` | `modify tool` (sibling lifecycle actions - create vs. change) |
| `update consumers` (this hub pushing functionality to every consumer) | a consumer can already pull the same thing on its own via its own `update` skill - bulk push here is an accelerant for when you just built something and know every local consumer wants it, not a requirement |

### A note on ground-reachability

Some of the above (scaffolding a brand-new project, `propose upstream`, `update`, `update
consumers`, `self hooks`, `curate shared resources`'s push side, `set up automation`, applying a
ticket's fix) can only run from here - the hub itself. A consumer-project session can *ask about* any of these (it has its
own `commands` skill, `templates\commands.md`) but can only *stage* the ones that queue for the
hub's own next session (filing a ticket, `register.md`'s registration ticket) - never execute them
directly. If an operator session gets a question that's actually about what a consumer project can
reach, answer from that framing, not this one.
