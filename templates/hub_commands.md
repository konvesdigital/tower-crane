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

Per the reciprocal-tracks rule (design\optimize_ux.md): when a query lands on one side of a pair
below, volunteer the other side as the single next-best follow-up - don't wait to be asked.

| If the query is about... | ...also mention |
|---|---|
| `checkpoint` | `resume` (and vice versa) |
| `archive` (work log) | `checkpoint` - only worth mentioning once the work log has actually grown large enough to need archiving, not on every checkpoint |
| `update` (pulling the public repo in) | `propose upstream` (pushing a local fix back out) - not `update consumers`, which is a different boundary (pushing already-adopted hub functionality out to registered projects, not pulling anything in) |
| processing a filed ticket | the reverse is a consumer's own `filing` skill - "that's how a project gets a ticket to you in the first place" |
| `self hooks` (what's turned on for this hub itself) | a consumer project has the same question about its own opted-in tools, asked from inside that project |
| `curate shared resources` (this hub pushing an insight to every consumer) | a consumer can already pull the same thing on its own via its own `shared resources` search/browse - curation is an accelerant, not a requirement |
| `new tool` | `modify tool` (sibling lifecycle actions - create vs. change) |
| `update consumers` (this hub pushing functionality to every consumer) | a consumer can already pull the same thing on its own via its own `update` skill - bulk push here is an accelerant for when you just built something and know every local consumer wants it, not a requirement. Distinct from the hub's own `update` (pulls the public repo in - doesn't touch consumers at all) despite the shared name |

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
