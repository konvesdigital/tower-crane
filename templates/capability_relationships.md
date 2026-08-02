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

1. **Match the query to one `nodes` entry** — by `trigger`, or by matching a described need against
   each node's `description` until one clearly fits.
2. **Answer directly** from that node's `description`. If its `context` doesn't match the session
   you're in right now (e.g. the matched node is `context: hub` but this is a consumer session),
   say so plainly — this can be *asked about* from here, but not executed here.
3. **Surface its nearest family, never the whole graph:**
   - **Structural neighbors** — every `edges` entry naming this node as `a` or `b`. State the
     relationship type plainly (reciprocal / parallel / lifecycle-sibling / accelerant), and
     mention a `note`/`conditional` field if present. Skip `name-collision` and `backs` edges
     unless the query is specifically about disambiguating that pair or about the primitive/
     application relationship itself — they're informational cautions, not real neighbors to lead
     with.
   - **Thematic neighbors** — other nodes sharing a `themes` tag with this one, mentioned more
     loosely ("also related by purpose: ...") since a theme link is deliberately broad, not a close
     match.
4. **Path position is supporting color only** — you may mention where this node sits in `path`
   ("this typically comes right after X") if it's genuinely useful context, but never let that
   become the reply's main content, and never trigger this skill on its own for "what's next"-shaped
   phrasing (see "When this fires" above).
5. **Never dump the whole picture.** One direct answer, its nearest family, done — same discipline
   `commands.md`/`hub_commands.md` already follow.
