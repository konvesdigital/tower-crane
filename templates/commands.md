<!--
Shared protocol piece: commands.md (OPTIONAL / self-scaffolding for every consumer - Track 1,
on-demand, no always-resident companion - design\optimize_ux.md).
Home: ~\Documents\Claude\tower_crane\toolkit\templates\commands.md
Reached via a thin skill stub at .claude\skills\commands\SKILL.md (sourced from
toolkit\templates\skills\commands\SKILL.md), same copy-and-substitute pattern as
filing/checkpoint/archive/update. Float-on-HEAD: this file is the one canonical source the stub
always re-reads live. Keep this file project-agnostic - it must read correctly from ANY consumer.
Refer to "this project", never a specific consumer name.

Fluent-tier track sourcing (design\capability_relationships.md, "partial conversion" decision,
2026-08-02): "Efficiency habits" and "Sharing outward" below are catalog-derived (see their own
render instructions) - the only two of this file's four tracks that had a real matching theme tag
in the locked design. "Cross-project knowledge" and "Reaching the hub from here" stay hand-authored
- no matching theme tag exists for either yet, and inventing one just to force uniformity would
violate the theme-tag test itself (two members from different structural clusters, nameable in one
clause - design\capability_relationships.md's theme layer section). No functional loss either way:
the theme layer is additive to `capability_relationships`' own answers regardless of whether a track
here reflects it. Revisit only if a real third theme naturally emerges - don't invent one for this.
-->

## Answering "what can I do here" from this project's own session

This project imports Tower Crane pieces (protocol + opted-in tools + Track-1 skills). Nobody has
to already know the exact trigger phrase for any of them - this file is what a "commands"-shaped
query draws from. **Never dump the whole picture.** Give a direct answer to what was actually
asked, plus the single next-best follow-up - never more.

**Which of the two tiers below to render is picked by the phrasing that triggered this skill, not
by any other signal:**
- An exact, already-fluent phrasing (**"commands"**, "what commands are there") → the **fluent
  tier**: a terse cheat sheet.
- A confused/new-to-this phrasing (**"I'm new here, what do I do"**, "what can I do here", "I just
  got handed this project") → the **beginner tier**: a guided sequential story, not a list.

Both tiers draw from the same underlying capability set below - only the rendering differs.

### Fluent tier - cheat sheet

One reply, grouped by track header, each line a bare command/phrase plus a one-line action. No
follow-up turn required.

**"Efficiency habits" and "Sharing outward" are rendered live, not from a fixed list below:** read
this project's own `capability_catalog.yaml` (same `toolkit\` root `capability_relationships.md`
resolves it from - see that file's own self-locating note). For each track, filter `nodes` to
`context: consumer` or `both`, carrying the matching theme tag (`efficiency-rationale` for
"Efficiency habits", `push-outward` for "Sharing outward"), and render one line per node using its
`description` - except group nodes that share the same literal `trigger` prefix (e.g. every
`shared resources "..."` node) into a single combined line, same as the worked example below, so
the four shared_resources actions don't turn into four repetitive bullets.

```
commands

Efficiency habits:
  <rendered from capability_catalog.yaml, theme "efficiency-rationale" — expect roughly:>
  checkpoint — save this project's progress, commit, push
  resume — pull latest, check for hub compliance guidance, pick up where you left off
  quick resume — thin resume right after a checkpoint
  archive — move resolved Work Log entries into the archive file, once it's grown enough to need it
  shared resources — save something this project found, or search/browse/adopt what another
    project already has (Save/Browse/Apply/Forget/Archive, all one theme: doing this instead of
    redoing the work elsewhere)

Cross-project knowledge:
  shared resources — same capability as above, listed here too since it's fundamentally
    cross-project (save/search/browse/apply/forget/archive)
  update — pull in new hub features this project hasn't adopted yet

Sharing outward:
  <rendered from capability_catalog.yaml, theme "push-outward" — expect roughly:>
  shared resources — Save pushes an insight/tool/reference so every other project can pull it in
  filing (proposal) — propose something that should become an actual shared default, not just an
    optional insight

Reaching the hub from here:
  filing — report a bug, request a fix, or check a ticket you already filed
  connecting another project — file a registration ticket via "read register.md and follow it"
    (for an existing project) - a brand-new project needs the hub operator's own scaffolder
```

`update` moved from "Efficiency habits" to "Cross-project knowledge" in this rework - it was never
tagged `efficiency-rationale` in the locked catalog (its efficiency argument is "stay current
without manual sync," a different shape than the catalog's own token-economy/time-economy
definition of that tag), and "Cross-project knowledge" already fits it better in substance. Still
fully covered in the Reciprocal pairs table below either way.

### Beginner tier - guided story

Narrated as a sequential walk through `capability_catalog.yaml`'s own `path` section, filtered to
nodes where `context` is `consumer` or `both`, in that order (skipping hub-only steps like
`setup_machine` - this project's own session can't run those anyway) - answers "what's first," not
"here's everything." Read the catalog fresh each time; don't render from the frozen example below.

```
I'm new here, what do I do?

This project is already wired up to a shared toolkit (Tower Crane) for two habits worth learning
right away: "checkpoint" saves your progress here and pushes it, and "resume" picks a session
back up next time - say "quick resume" instead if you're just reopening seconds after a
checkpoint.

If you ever want to share something this project found (or see what another project has already
figured out), say "shared resources".

If you hit a bug in a shared tool, or want to request one, say something like "I found a bug" or
"can we get X" and I'll file it.

Once those feel routine, "update" checks whether the hub has picked up any new functionality this
project hasn't adopted yet - worth a look every so often, never automatic.

You can say "commands" any time to see everything else.
```

### Reciprocal pairs to volunteer

Per the reciprocal-tracks rule (design\optimize_ux.md): when a query lands on one side of a pair
below, volunteer the other side as the single next-best follow-up - don't wait to be asked.

| If the query is about... | ...also mention |
|---|---|
| `checkpoint` | `resume` (and vice versa) |
| `archive` (work log) | `checkpoint` - only worth mentioning once the work log has actually grown large enough to need archiving, not on every checkpoint |
| pulling in shared resources (search/browse/adopt) | `shared resources` `Save` - sharing something this project found, outward |
| filing a bug/problem | the round-trip check ("check my ticket") is part of the same `filing` skill |
| `update` (pulling in new hub features this project hasn't adopted yet) | the hub-operator side of the same content is `update consumers` (same features, pushed instead of pulled); if what you want doesn't exist as hub functionality yet, that's a `filing` proposal ticket instead, not `update` - and note the hub has its own separate `update` (pulling the *public* toolkit repo in), a different boundary this project can't reach at all |

### Reaching the hub from here

Some things genuinely need a human sitting in the hub itself (scaffolding a brand-new project,
`propose upstream`, `update` the toolkit, `self hooks`, `curate shared resources`'s push side,
`set up automation`, applying a ticket's fix) - this project's own session can't execute those,
only ask about them. Never answer with silence: say plainly that it needs a hub-operator session,
and if it's something this project can *stage* instead (filing a ticket, `register.md` for
connecting another existing project), say that too - staging it here still completes on the hub's
own next session, no synchronous hub visit required.
