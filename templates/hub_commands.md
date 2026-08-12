<!--
Canonical hub-operator content: hub_commands.md (design\optimize_ux.md). Reached via a thin skill
stub at .claude\skills\hub_commands\SKILL.md, installed only through self_hooks.py's per-tool
opt-in mechanism (templates\optins\hub_commands.json's "skills" key) — off by default, per-machine,
same as every other self-use tool. Float-on-HEAD: this file is the one canonical source the stub
always re-reads live. This file describes THIS hub's own operator-facing capabilities — it never
governs a consumer project's session (that's templates\commands.md instead).

Fluent-tier track sourcing (design\capability_relationships.md, "partial conversion" decision,
2026-08-02): only "Efficiency habits" below is catalog-derived - the only one of this file's three
tracks with a real matching theme tag in the locked design (`efficiency-rationale`). "Toolkit
evolution" and "Fleet operations" stay hand-authored - no matching theme tag exists for either yet,
and inventing one just to force uniformity would violate the theme-tag test itself (two members
from different structural clusters, nameable in one clause). No functional loss either way - the
theme layer is additive to `capability_relationships`' own answers regardless. Revisit only if a
real third theme naturally emerges - don't invent one for this. See templates\commands.md's own
header for the consumer-side half of the same call.

"Reciprocal pairs to volunteer" below is separately catalog-derived as of 2026-08-03, mirroring
templates\commands.md's own conversion the same day — see that file's header for the full
reasoning (predated the catalog build, had drifted into a redundant hand-maintained duplicate of
`edges` data).

This file explains how to use the mechanism it covers. `capability_relationships` explains how
this mechanism works and how it relates to other mechanisms.
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

**"Efficiency habits" is rendered live, not from a fixed list below:** read this hub's own
`capability_catalog.yaml` (`toolkit\capability_catalog.yaml`). Filter `nodes` to `context: hub` or
`both`, carrying the `efficiency-rationale` theme tag, and render one line per node using its
`description`.

```
commands

Efficiency habits:
  <rendered from capability_catalog.yaml, theme "efficiency-rationale" — expect roughly:>
  checkpoint — save state and push
  resume — pull state, check for updates
  quick resume — thin resume right after a checkpoint
  archive — move resolved Work Log entries into the archive file, once it's grown enough to need it

Toolkit evolution:
  new tool — add a tool to the shared library
  modify tool — change/remove an existing tool
  propose upstream — send a local fix to the public repo
  update — pull the public repo's latest
  self hooks — toggle this hub's own dogfooding

Fleet operations:
  connect project — register a new or existing consumer
  disconnect project — remove a consumer (this machine, every other machine, or everywhere)
  update consumers — bulk-push new hub functionality to every registered consumer
  curate shared resources — push an insight to every consumer
  set up automation — wire up unattended ticket processing
```

### Beginner tier - guided story

Narrated as a sequential walk through `capability_catalog.yaml`'s own `path` section, filtered to
nodes where `context` is `hub` or `both`, in that order - answers "what's first," not "here's
everything." Read the catalog fresh each time; don't render from the frozen example below. Note
this reorders the hub-side beginner story from an earlier hand-authored draft: the Path puts
`checkpoint`/`resume` immediately after `setup_machine`, ahead of `connect_project` (short, easy,
low-risk - genuinely the first thing worth doing with any fresh hub state, before even hub-specific
discovery steps), not after it.

```
I'm new here, what do I do?

First, get the hub running: say "set up tower crane" and I'll walk you through it. Once that's
done, "checkpoint" (save progress, push) and "resume" (pick back up next session) are worth
learning right away - the same two habits every project built off this hub relies on.

From here, "self hooks" shows what's turned on for this hub itself, and "connect project" brings
in your first project (new or already existing).

You can say "commands" any time to see everything else.
```

### Reciprocal pairs to volunteer

Per the reciprocal-tracks rule (design\optimize_ux.md): when a query lands on one node, volunteer
its nearest structural neighbor as the single next-best follow-up - don't wait to be asked. Not a
fixed list below - read this hub's own `capability_catalog.yaml` fresh (`toolkit\capability_catalog.yaml`,
same file the "Efficiency habits" track above and `capability_relationships` both resolve from).
For the node the query actually landed on, check `edges` for every entry naming it as `a` or `b`
(skip `name-collision` and `backs` - informational only, not real neighbors, same discipline
`capability_relationships.md` step 4 uses): reciprocal/parallel → mention the other side plainly;
lifecycle-sibling → mention it, using the edge's own `note` if present; accelerant → mention the
accelerated side as the thing that's already possible without this hub-side convenience.

```
checkpoint → also mention: resume (reciprocal)
archive (work log) → also mention: checkpoint (lifecycle-sibling, only once the Work Log has
  actually grown large enough to need archiving)
update (pulling the public repo in) → also mention: propose upstream (reciprocal)
new tool → also mention: modify tool (lifecycle-sibling)
update consumers → also mention: update, the consumer-side pull equivalent (accelerant - a
  consumer could already run its own)
```

### A note on ground-reachability

If an operator session gets a question that's actually about what a *consumer* project can reach -
not what this hub session itself can do - answer from that framing instead of this one.
`templates\commands.md`'s "Reaching the hub from here" section owns that logic and renders it live
from `capability_catalog.yaml`'s `context`/`partial_reach` fields (fully consumer-reachable first,
then partially-reachable-here-with-the-rest-needing-a-hub-session, then hub-only). Don't hand-answer
it differently from here - the two should never drift into disagreeing about the same underlying
facts, and per methodology principle 4 (design doc), the default answer to "where's the best place
to do this" favors the consuming project whenever it's genuinely reachable there, even when the
question was asked from inside the hub.
