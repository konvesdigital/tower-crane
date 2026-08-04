<!--
Shared protocol piece: capability_relationships.md (OPTIONAL / self-scaffolding, Track 1,
on-demand, no always-resident companion - design\capability_relationships.md). Unlike every other
Track-1 piece so far, this one fires from BOTH a consumer session and a hub session under the same
skill name - see the SKILL.md stub's own header comment for how the two distribution paths
(new_consumer.py's STANDALONE_SKILLS scaffold / self_hooks.py's "skills" opt-in) both resolve to a
working copy of this same file.
Home: ~\Documents\Claude\tower_crane\toolkit\templates\capability_relationships.md
Float-on-HEAD: this file is the one canonical source the stub always re-reads live. Keep this file
context-agnostic - it must read correctly from a consumer session or a hub session alike. Refer to
"this session", never a specific consumer name or "the hub" as if that's the only possible caller.
-->

## Answering a "what does X do" / "how do I do Y" question from the capability graph

This project (or hub) has access to `capability_catalog.yaml`, a structured map of every Tower
Crane capability and how they relate to each other - not a flat list, a graph. You reached this
file via a skill stub whose own path resolved somewhere under a `toolkit\` folder. That same
`toolkit\` folder is where `capability_catalog.yaml` lives, at its root (`toolkit\capability_catalog.yaml`,
relative to the same `toolkit\` you're inside right now).

**Read the catalog file fresh every time this skill fires — never answer from memory of a previous
read.** It floats on HEAD and may have changed since you last looked.

### When this fires

A question about a *specific mechanism or concept* — whether or not it names a capability
explicitly:
- **Named**: "what does `update` do", "what is `curate shared resources`".
- **Described, unnamed**: "how do I get the newest version of what I build in the hub into this
  project" (names no capability, but describes `update_consumer`'s exact function).

This is **not** for broad "what can I do here"/"what's next"/"I'm new here" language — that's
`commands`/`hub_commands`' territory (`templates\commands.md` / `templates\hub_commands.md`), which
render the catalog's own `path` section as a guided story. Route there instead if that's what's
actually being asked.

### How to answer

1. **Match the query to the `nodes` it plausibly fits** — by `trigger`, or by matching a described
   need against each node's `description`.
   - **One node clearly fits, or several fit but are already linked to each other** (an `edges`
     entry, or a shared `themes` tag — so the normal answer in steps 2-3 below will surface them
     together anyway): treat the best match as the anchor and continue to step 2.
   - **Two or more nodes fit comparably well and are NOT already linked to each other**: this is a
     genuinely ambiguous query, not one with a clear right answer sitting under loose context — a
     query can fit two nodes equally well while those nodes share no edge and no theme tag, so the
     normal single-anchor flow would silently pick one and make the other invisible. Don't silently
     pick one. Instead, ask a short clarifying question: list the plausible candidates by `trigger`
     plus one terse gloss each — shorter than a normal answer, no neighbors or context notes yet,
     that comes after narrowing — and ask what they're actually trying to do, specific enough to
     distinguish between the candidates. Once they narrow it down, answer that one node normally via
     steps 2-5 below.
2. **Check whether the matched node's own answer branches** — not which node to match (step 1 already
   resolved that), but whether the matched node itself has more than one genuinely valid way to go
   once you're inside it (its `description` names more than one valid option, or its `context` plus a
   `partial_reach` note together describe more than one place the work could genuinely happen). If it
   branches, state every valid branch plainly, including whatever actually distinguishes them, before
   recommending or assuming any one — never silently collapse real branches into a single answer just
   because they reach a similar outcome. Ask a short clarifying question if the distinguishing factor
   isn't already clear from the query; otherwise answer the branch the query already specifies.
3. **Answer directly** from that node's `description` (or the branch narrowed in step 2), naming
   its exact `trigger` phrase — several nodes now fire autonomously only on that literal word
   (`checkpoint`, `archive`, `update`), so surfacing it is the actionable takeaway, not decoration.
   Check `context` against the session you're actually in:
   - Matches, or no `partial_reach` note exists: answer plainly.
   - Doesn't match, but a `partial_reach` note names this session's side: say plainly what can
     genuinely start here per that note, and what still needs the other location to finish — don't
     default to "ask about it, can't execute it here" when real partial work is actually possible.
   - Doesn't match, and no `partial_reach` note exists: say so plainly — this can be *asked about*
     from here, but not executed here.
   - The query is specifically about *which location* is the better place to do this, and more than
     one location is genuinely reachable: reason it live rather than defaulting to whichever location
     this session happens to be in — a tie in effort goes to the consuming project; a location wins
     outright only by taking fewer steps, or by offering a consolidated/bulk equivalent the other side
     lacks (design doc methodology principle 4).
4. **Surface its nearest family, never the whole graph:**
   - **Structural neighbors** — every `edges` entry naming this node as `a` or `b`. State the
     relationship type plainly (reciprocal / parallel / lifecycle-sibling / accelerant), and
     mention a `note`/`conditional` field if present. Skip `name-collision` and `backs` edges
     unless the query is specifically about disambiguating that pair or about the primitive/
     application relationship itself — they're informational cautions, not real neighbors to lead
     with.
   - **Thematic neighbors** — other nodes sharing a `themes` tag with this one, mentioned more
     loosely ("also related by purpose: ...") since a theme link is deliberately broad, not a close
     match.
5. **Path position is supporting color only** — you may mention where this node sits in `path`
   ("this typically comes right after X") if it's genuinely useful context, but never let that
   become the reply's main content.
6. **Never dump the whole picture.** One direct answer, its nearest family, done — same discipline
   `commands.md`/`hub_commands.md` already follow.
