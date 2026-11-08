<!--
Canonical Track-1 skill stub source: shared_resources (toolkit-governed).
MANDATORY for every consumer since 2026-08-01 — mechanism delivery is mandatory, not optional.
Home: ~\Documents\Claude\tower_crane\toolkit\templates\shared_resources.md
Reached via a thin skill stub at .claude\skills\shared_resources\SKILL.md (sourced from
toolkit\templates\skills\shared_resources\SKILL.md), same copy-and-substitute pattern as
filing/checkpoint/archive — NOT a flat @import. The one part of the old flat-imported file that
genuinely can't wait for a trigger (the resume-time reference-existence/drift checks) was split out
to templates\shared_resources_resume_check.md, always-@imported alongside the skill stub. Float-on-
HEAD: this file is the one canonical source the stub always re-reads live. Keep this file
project-agnostic — it must read correctly reached from ANY consumer. Refer to "this project", never
a specific consumer name, and never a real path/client name (this file lives in `toolkit\`, the
public repo).

This file explains how to use the mechanism it covers. `capability_relationships` explains how
this mechanism works and how it relates to other mechanisms.
-->

## Using shared resources and insights

This hub keeps a **`shared_resources\`** folder at the hub root (one level up from `toolkit\` —
see `templates\filing.md` if the hub-root/`toolkit\` split is unfamiliar). Unlike everything else
at the hub root, this one folder is not off-limits to write from inside a project session — see
"Saving" below. It holds three kinds of entry, indexed in one catalog,
`shared_resources\CATALOG.md` (`Name | Kind | File | Category | Tier | Description | Added |
Status`). `Category`/`Tier` are optional metadata
— a broad domain tag plus a Category-scoped retrieval-circumstance pointer — and a companion file,
`shared_resources\resource_relationships.yaml`, holds typed edges between entries plus each
Category's situational-tier circumstance definitions. See "Saving" and "Retrieval" below for how
these get written and read; an entry with no Category is unaffected by any of this.
Retrieval runs through the Category skills and the scaffolded `CLAUDE.md` "Adopted Shared
Resources" directive; there is no keyword hook.

- **`reference`** — passive, read-on-demand domain knowledge (methodology, facts). Using one means
  reading it, or `@import`ing it if it's plain prose with no spaced paths.
- **`tool`** — a pointer to a proprietary or personal script/tool that lives elsewhere on disk,
  invoked on demand rather than auto-run. Using one means knowing it exists and how to call it.
- **`insight`** — a workflow habit, code fragment, decision, or diagnosis that gets *consumed
  into* this project (adapted or copied in), not pointed at externally. Unlike the other two
  kinds, an insight is retrieved by deliberate human recall of a past pain point, never a keyword
  match — see "Insights are different" below.

This is a **pull-only** mechanism: nothing here scans or prompts automatically at `resume`.
Discovery only happens when this project's own session goes looking, because a resource relevant
to one project (SEO methodology, say) has no business surfacing in an unrelated one.

### Entering shared-resources context: an exact trigger, not a buried keyword

Working in a project normally means thinking only about that project. Using this mechanism means
deliberately switching to thinking across every project — a real gear-switch, not a minor aside,
so it needs an unmistakable trigger rather than something inferred from a keyword that happened to
appear somewhere in a sentence.

**The trigger is the exact phrase "shared resources," used as the message's own deliberate point —
not its position in the sentence.** The test is never "does it lead the message" — natural phrasing
routinely puts the object at the end (*"make a note about this in shared resources"*, *"save this
as a shared resource"*) and that's just as much a deliberate invocation as leading with the phrase.
The real test: is the whole message *about* invoking this mechanism (whether announcing it upfront,
trailing it after describing the request, or standing alone), or does the phrase merely surface in
passing while the message is actually about something else (*"that reminds me, shared resources
probably has something on this — anyway, back to the bug"*)? The former fires; the latter does not.
When genuinely ambiguous, ask rather than guess either way. It can be followed immediately by the
actual request in the same breath (*"shared resources — save this as an insight"*), precede it
(*"everything we've figured out about X, make a note of this in shared resources"*), or stand
alone, in which case ask what's wanted (save, search, browse, apply, forget, archive).

On firing, say so out loud before doing anything else — e.g. *"Switching to shared resources —
thinking across projects now, not just this one."* — so the context-switch is visible, not just
assumed. Everything below happens **inside** that acknowledged context. There's no separate exit
trigger: the mode is scoped to completing the one action (a search, a save, etc.), and the
conversation returns to ordinary project-local framing once it resolves — unlike `checkpoint`/
`resume`, there's no separate repo or session to deliberately zoom back out of.

### Saving — the narrow write exception

A project's session may write **directly into `shared_resources\`** — one new entry file plus one
new line in `CATALOG.md` — with no ticket, no round-trip, no separate hub session. This is the
**only** write a consuming project may make outside its own project folder; everything else at the
hub root (`toolkit\`, `consumers\`, `change_requests\`, `project_progress.md`) stays off-limits per
`templates\filing.md`.

Before saving, classify what's being saved — this classification is the actual safeguard, not a
formality:

- **Names a private project or client** (check it against the hub's own `consumers\*.md`
  registry, or it's plainly project-specific either way) → save it into `shared_resources\`. It
  structurally cannot go anywhere else — never offer to route it into `toolkit\`.
- **Requests a change to Claude's own deterministic behavior** — a hook, a script, a workflow
  convention, not domain knowledge — → this is **not** `shared_resources\` content either way, but
  where it actually goes depends on whether it's generic: content that should apply the same way
  for anyone points at the ticket system instead (`templates\filing.md`'s `Type: proposal` ticket,
  or an ordinary bug ticket); content that's genuinely project/client-specific goes to
  `toolkit_private\` instead, built directly in a hub session (`AGENTS.md`'s "new private tool") —
  no ticket, no genericity requirement, since it never leaves that machine. If this same content
  already lives in `shared_resources\` and has proven itself broadly, see filing.md's graduation
  path instead of re-filing from scratch.
- **Neither is obvious** → ask before saving.

Then work through the rest of this flow — never another design interview, fast in the moment
because a real save happens inside a task already in progress. **Governing principle: this is
never classification for its own sake.** Every save is fundamentally "I want Claude to know this
fact" — the only question this flow actually needs answered is *"under what circumstances should
Claude surface it?"* Category/Tier are a compressed way of storing that answer, never an
organizational scheme applied on top of it.

1. **Classify** — `kind`, `Category`, one-line description. `Category` is free text, discovered by
   checking whether any other `CATALOG.md` row already carries it — no separate registry lists
   valid values. No Category is a legitimate answer (leaves both columns blank, unaffected by
   everything below). **If this save introduces a Category no existing `CATALOG.md` row already
   carries, also ask:** *"Should resources in `[Category]` be able to define a project's identity
   once comprehensively adopted (a strong 'treat this as authoritative' directive in `CLAUDE.md`),
   or is this a utility/occasional category?"* ("Adopted Shared Resources," below, needs this
   answered once per Category — it's never inferred later from adoption counts, since a
   single-member category would otherwise wrongly read as "100% adopted" the instant anyone
   touches it.) Answer stored as `identity_eligible` — see step 6.
2. **Circumstance** — if this entry has a Category, ask: *"Should Claude know this always, in
   `[Category]` contexts, or only under specific circumstances?"*
   - **Always** → Tier is `Primary`, no entry in `resource_relationships.yaml`'s `tiers:` block
     (nothing to compare a future save against). Skip to step 3.
   - **Specific circumstances** → resolve which one, grounded in the cheapest real evidence
     available, never an abstract taxonomy question:
     - **No situational tiers exist yet in this Category** — ask directly what circumstance
       triggers it, and that answer becomes the first tier's `circumstance:` text verbatim, named
       from the user's own words.
     - **Situational tiers already exist** — surface, as context informing the user's own answer,
       never a presumed default: (a) this session's own active circumstance, if one is in play, as
       one candidate among others (a save can just as easily be an unrelated aside); (b) this
       Category's other existing tiers and their `circumstance:` text (never another Category's
       tiers). The user states the circumstance; an exact or close match folds in; a near match
       broadens the existing tier's `circumstance:` text (a small, cheap edit) and folds in; no
       match names a new tier from the circumstance just given. Tier names/definitions stay
       revisable going forward — expect renaming, broadening, or splitting as more entries test a
       tier's boundary, never a one-time-locked taxonomy.
3. **Show the active node's existing edge-neighborhood, don't ask an open question.** If a
   process/entry already in play this session has existing edges in `resource_relationships.yaml`,
   show them compactly (an `Entry | Edges` table) and ask whether to tie the new entry to it the same way — answerable
   yes/no/adjust, not a blank "what should this tie to?" Edge types: `process-material`
   (directional, "reach for this while doing that" — the dominant shape), `prerequisite`
   (directional, a real specific dependency, not a generic "A is foundational" claim),
   `lifecycle-sibling` (undirected, same object/question at a different stage), `related`
   (undirected, no specific claim — the zero-effort default, always available, needs no
   justification). Grep every existing `shared_resources\*.md` file for a literal, backtick-quoted citation of this entry's own filename, and grep this entry's own content for a citation of any existing file's name. If that grep found this entry's filename literally cited inside an
   existing file (or vice versa), that pair gets a `process-material` edge
   — a deterministic outcome from the grep hit, not a judgment call the way the rest of this step is. Only a
   literal-citation hit earns an edge this way, never a strong-but-inferred relationship.
4. **No obvious active node** (a genuinely cold save) — fall back to asking, scoped by Category:
   *"Which of `[Category]`'s existing entries/processes does this belong near, if any — or is this
   a first-of-its-kind save?"* — never the full graph dumped at once.
5. **Confirm before writing anything** — the entry's name, `kind`, `Category`/`Tier`, one-line
   description, any edge(s) from steps 3–4, and that it's about to be written into
   `shared_resources\` plus a new `CATALOG\*.md` row (plus any `resource_relationships.yaml` change).
   Only write after
   confirmation — this is the one disk-writing action in the whole mechanism and the one carrying
   the classification call above, so it gets its own explicit checkpoint even though entering the
   mode already got one.
6. **Write.** For a `reference`/`tool` entry: create one new file in `shared_resources\`, append
   one row to `CATALOG\*.md` (`Status` blank — active by default) with its `Category`/`Tier`, write
   any new/updated `tiers:` circumstance text or edge(s) into `shared_resources\resource_relationships.yaml`. **If this save is
   that Category's first entry, also write step 1's `identity_eligible` answer** into a top-level
   `identity_eligible:` block in `shared_resources\resource_relationships.yaml` (create it with an
   empty mapping first if it doesn't exist yet), keyed by Category name — e.g.
   `identity_eligible: {SEO: true}`. For `insight`, see "Insights are different" below —
   its save flow is a negotiation, not a fixed write, but ends the same way. Either way, before
   propagating, **run `python toolkit/scripts/check_shared_resource_catalog.py --entry
   shared_resources/<the entry file>`** (path from the hub root) and fix every `[!]` line it prints
   by editing the entry, then re-run until it exits 0 — see "No absolute paths in an entry" below.
   Then finish with **propagate the write** (see below).
7. **Coverage guarantee, then a precision offer — only when this entry has a Category.** Two
   distinct things, not one:
   - **This save is the Category's very first entry, of any kind** (`Primary`, or the first entry
     of a brand-new situational Tier) — offer immediately, always deferrable like every offer in
     this flow: build a generic **Category-level fallback skill** (`AGENTS.md`'s "new private
     tool" procedure) whose trigger is deliberately broad ("use when doing any `[Category]` work")
     and whose body reads the *whole Category's* live graph via the retrieval procedure below, not
     just one Tier's. This is what guarantees autonomous coverage exists from this Category's very
     first entry, before any Tier has had the chance to prove itself.
   - **A situational Tier just reached its 2nd entry** (via a new save or a merge) — *now* offer,
     always deferrable, to split a narrower Tier-scoped skill out of the fallback: a better-tuned
     trigger, a smaller live-read scope. This is a precision upgrade layered on the fallback that
     already covers this Tier, never the entry's first route to being surfaced — declining it
     changes nothing observable.
   - Below the 2-entry mark, with the fallback already in place, say nothing further — no
     automation debt implied.
   - Either skill is built to read its scope's anchor entry and graph neighbors *live* from
     `CATALOG.md`/`resource_relationships.yaml` (see "Retrieval" below), never hardcoded — so
     building the fallback at entry #1, or a Tier-scoped skill at its 2-entry mark, automatically
     covers every entry that already existed, no separate backfill.
8. **Propagate the new skill to subscribed consumers, right then** — once a skill from step 7 is
   actually built, check `consumers\*.md` for every project whose `private_categories:` list
   already names this Category and offer to push it to each of them immediately, in this same
   session, rather than leaving it to chance that a project happens to run its own `update` soon.
   Still confirmed per push. Declining for a given consumer doesn't remove its subscription — that
   consumer's own next `update` scan surfaces the gap again on its own.

**If the entry is a `tool`, or a `reference` whose real content is a pointer to something kept
outside `shared_resources\` (not copied into the entry file itself)** — never write a flat target
path. Instead give the entry a `**Hosts:**` block, keyed by this machine's own `host_id` (read it
from `<hub root>\toolkit\config.local.json`, the same file the hub itself reads at every session):

```markdown
# <Entry Name>

**Kind:** tool
**Hosts:**
  <this host's host_id>:
    path: <the real target's absolute path on this machine>
    registered: YYYY-MM-DD
```

See "Per-host availability for pointer entries" below for why, and for what happens when a project
that adopted this entry runs on a machine not yet in this list.

**Every `reference` or `tool` entry states its host availability on one of two forms** (an `insight`
is always hub-resident and states nothing):
- **Content lives inside the entry's own file** (a hub-resident `reference`, or one whose target is
  only a web link or Drive URL) → write the one line `**Hosts:** any` directly under the `**Kind:**`
  line. No `Hosts:` block.
- **Anything else** (a `tool`, or a `reference` pointing at a file or folder on a machine) → the
  `Hosts:` block above, one key per machine that has it. A `tool` never takes `any`, and a pointer
  never takes `any` even if every machine has the target today.

**Host tag in the catalog row.** When the entry has a `Hosts:` block, start its `CATALOG.md`
`Description` with a tag naming those machines: `[<host_a> only]` for one, `[<host_a>, <host_b>]` (sorted) for
several. Rows for `any` entries and insights carry no tag. Update the tag in the same edit whenever a
host is added to the block (including "register host" and the `[HOST-GAP]` "Connect it now" option).
`check_shared_resource_catalog.py` reports a mismatch at `resume`; the tag exists so skills that read
`CATALOG.md` directly see which machines have an entry without opening it.

**No absolute paths in an entry.** The `path:` line inside an entry's `Hosts:` block is the only
place an absolute path (a drive letter, `~/`, a network share, `/Users/...`, an environment-variable
path, a `file://` link) may appear in any `shared_resources\` file. Everywhere else — the entry's
prose, its examples, its code blocks — write the thing by name only. Before drafting an entry,
sort each path you are about to mention into one of two cases:
- **It names another hub file** → write that file's name alone (`weekly_ticket_triage_workflow.md`),
  never a path to it.
- **It names something outside the hub** (a script, folder, or program on this machine) → the entry
  is machine-local: make it a `tool` (or a pointer `reference`), put the path in its `Hosts:` block
  under this machine's `host_id`, and refer to the thing in the body by name only.

Web links (`https://...`) are not paths and are fine. `check_shared_resource_catalog.py` enforces
this with no exemptions — `save` runs it on the new entry (step 6) before propagating, and the
hub's `resume` runs it over every entry. Nothing marks an absolute path as "intentional"; if
the entry needs a path in its prose, it needs a `Hosts:` block instead.

### Every write here ends with the same propagation step

Any write into `shared_resources\` — a new `reference`/`tool`/`insight` entry, a
`insight` archive edit, or a new-host addition to
an existing entry's `Hosts:` block (see "Per-host availability for pointer entries" below) —
finishes with a scoped commit+push against the **hub's own outer repo**
(the private repo one level above `toolkit\`, not this project's own repo), run immediately, from
this session, right after the write:

```
git -C <hub root> add shared_resources
git -C <hub root> commit -m "shared_resources: <entry name>"
git -C <hub root> push
```

Never `git add -A` here — that could sweep in an unrelated in-flight hub-root edit (a
`project_progress.md` draft mid-edit, say) that nobody has reviewed yet; scope the add to exactly
`shared_resources\`. No leak-scan gate applies (that guards pushes to `toolkit\`'s *public* remote;
the hub's own outer repo is private) and no `change_requests\` ticket is needed — this is the same
self-approving write "Saving" already established, just made durable and visible instead of sitting
uncommitted until some unrelated hub-level `checkpoint` happens to run. A second machine's own
`resume` (its ordinary `git pull` on the outer repo) picks it up the normal way — nothing new
needed on the receiving side. If the push fails (no remote, auth problem, non-fast-forward), say so
plainly rather than silently leaving the write local-only — the write itself already succeeded on
disk either way, only its propagation to other machines is at risk.

### Per-host availability for pointer entries

`shared_resources\` itself syncs to every machine this operator uses (per the propagation step
above) — but a `tool` entry, or a pointer-authored `reference` entry, only ever describes something
that lives *outside* the hub, genuinely machine-local (a proprietary script, say). The entry
reaching a second machine doesn't mean the thing it points at reached that machine too — no path
fix can conjure a script onto a computer that never had it. This is a **different problem** from
"Adopted-stub path portability" above: that one is a stale-but-fixable path; this one is a target
that may genuinely not exist here at all.

**Browse/search** tags a hit with which host(s) actually have it whenever the entry carries a
`Hosts:` block (e.g. `[<host_id> only]`) — never presents something as usable somewhere it isn't. A
self-contained entry (its content lives inside its own `shared_resources\` file, nothing external
to point at) never carries a `Hosts:` block and is never tagged this way.

**At `resume`,** `scripts\check_shared_resource_refs.py` (run by
`templates\shared_resources_resume_check.md`) checks every adopted `tool`/pointer-`reference` skill
stub against its entry's `Hosts:` block. If this host is missing, it prints `[HOST-GAP]` —
notify-only, never blocking — and the acting agent presents three options, same shape as an
unresolved `## Broadcast` section:

1. **Ignore** — this host genuinely will never have the thing (e.g. a tool that only ever makes
   sense on the machine it was built for). Add this host's id to the stub's own adoption marker's
   `hosts-ignored:` field (comma-separated if more than one host is already ignored). Never asked
   about again for this project, on this host — the check finds the marker and goes quiet.
2. **Connect it now** — the user places the real target on this machine (there's no assumption its
   path corresponds to any other host's path — ask for the new path plus whatever else is needed to
   actually use it here) and confirms it's ready. Append a `hosts.<this host>` entry to the entry's
   own `Hosts:` block in `shared_resources\` (same self-approving write as any other addition to an
   existing entry — no ticket), then propagate it (see "Every write here ends with the same
   propagation step" above). Resolves the gap for good — the next `resume`'s check finds this host
   in the list and goes quiet too.
3. **Proceed without deciding** — use this session without the tool/reference, decide nothing yet.
   Neither the entry nor the stub's marker changes, so the exact same `[HOST-GAP]` notice — with the
   same three options — resurfaces at the next `resume` on this host, and every one after that,
   until it's resolved via option 1 or 2. This is the default when the user doesn't pick a lane, not
   a failure state — matches how an unresolved `## Broadcast` section already behaves.

### Retrieval — one canonical procedure, every domain skill routes through it

A Category-level fallback skill or Tier-scoped skill (built via Saving's step 7 above) never
hardcodes which entries exist — it routes through this procedure, live, every time it fires. This
is what a flat "read this whole file in full" instruction (a single monolithic index file naming
every entry) couldn't guarantee: that instruction was easy for a session to satisfy from memory
instead of actually doing. Naming the concrete next action — read *this specific file* — closes
that gap structurally instead of restating the same prose instruction more emphatically:

1. **Identify the specific active anchor entry** for the current task — a nameable file, not an
   abstract "the whole tier" — from the task's own shape (e.g. a recurring report in progress
   names `weekly_ticket_triage_workflow.md` directly; a head-to-head competitor comparison names
   `competitor_pricing_reference.md` directly). A Category-level fallback skill does this across
   the whole Category's live graph; a Tier-scoped skill does it within just its own Tier.
2. **Read that entry.** Not a paraphrase from memory of a previous read — `CATALOG.md` and
   `resource_relationships.yaml` float on HEAD and may have changed since. If the entry has a
   `Hosts:` block (its `CATALOG.md` row carries a `[...]` tag), the standing "Hosts" rule applies:
   use only your own host's path. Say so only when the task actually reaches for the entry, never
   as an unprompted notice.
3. **Look up its graph neighbors in `resource_relationships.yaml`** and state them by title —
   never preload their content just because an edge exists. E.g. completing a recurring report's
   "why" analysis surfaces `trend_shape_vs_period_totals.md` and `backlog_age_diagnostic.md` by
   name via their `process-material` edges into `weekly_ticket_triage_workflow.md`, without a
   separate full-file read to discover they exist.
4. **Anything not directly linked but still in the same Category/Tier stays reachable via an
   ordinary browse** (see "Discovery" below) — the graph narrows what's surfaced by default, it
   doesn't hide the rest.

### Discovery: search or browse, then select, then apply

Once something exists to find — either saved here just now, or in an earlier session — three
explicit steps — never collapsed into one, since a query can turn up more than one genuinely
distinct match.

1. **Search or browse** the catalog:
   - **Search** — ask in natural language, e.g. *"shared resources — any SEO resources in
     there?"*. Check `shared_resources\CATALOG.md` (cheap — one line per entry) and list what
     matches, across both active and archived entries (a deliberate query can still legitimately
     want something archived — label any archived hit clearly as such).
   - **Browse/list** — ask to see everything, e.g. *"shared resources — list everything"*, with no
     keyword. Useful when you don't remember what's there, or don't remember whether *this*
     project already adopted something. Lists every **active** entry by default (an entry marked
     `Archived` in the `Status` column is hidden unless asked for — e.g. *"include archived"* —
     since an archived entry has already been independently absorbed by every active project and
     shouldn't clutter an ordinary listing, while still staying reachable for a brand-new project
     that hasn't hit that pain point yet). Refinable by:
     - a count limit (most recent N);
     - an added-date filter (e.g. "added in the last month");
     - an **in-use indicator relative to this project** — for `reference`/`tool`, check whether
       this project's own `CLAUDE.md` already contains a pointer/`@import` to that entry's file,
       or a project-local `.claude\skills\<name>\SKILL.md` stub carrying that entry's adoption
       marker (see "Apply", below); for `insight`, check for that entry's adoption marker (see
       "Insights are different") — where one exists. An insight applied with nothing persisted
       (see "Apply routes through a destination question" there) has no marker to find; that's an
       accepted gap, not a bug.
     - a **host-availability tag** for a `tool`/pointer-`reference` entry carrying a `Hosts:`
       block — see "Per-host availability for pointer entries" below.
2. **Select** — ask which of the matching/listed entries actually apply here. Don't assume a
   single match is automatically wanted.
3. **Apply** — adopt the selected entry:
   - **`reference`/`tool`** — turn it into a project-local Claude Code Skill rather than a
     standing `@import` (Track 1's autonomous on-demand loading — the model notices when a live
     question matches and pulls the content in, instead of it sitting resident in every session
     forever). Concretely:
     1. Read the entry's own file. Many entries are themselves a thin index over further
        material rather than the content itself (see the entry's own file for whether it points
        further, and if so, on demand rather than preloading all of it).
     2. Draft a trigger description ("use when...") from the entry's own topic/file breakdown,
        tuned to this project's context — never copied from `CATALOG.md`'s `Description` column,
        which is written for a human scanning many rows, not for recognizing an
        organically-arising question in conversation.
     3. Carry forward into the stub's body any provenance/authorship framing the entry itself
        draws (e.g. distinguishing the entry-author's own synthesized material from third-party
        material kept only for cross-reference) — never flatten that distinction away. Add an
        adoption marker, same convention as an `insight`'s (see "Insights are different"), so
        browse's in-use indicator and forget can find it later — plus a sha256 of the entry
        file's own current content, so a later `resume` can notice if that content has changed
        since the trigger above was drafted from it (drift mechanics, checked by
        `scripts\check_shared_resource_drift.py` — see "Checking adopted
        references at resume" below) — plus the entry file's own path relative to the hub root
        (`hub-rel:`), so a later `relocate.py` run can recompute the stub's embedded path for
        whichever host it's running on rather than leaving it baked to the host that adopted it
        (the stub body's own
        `Read ~/.../shared_resources/<file>` line stays a concrete, resolved path for this host
        right now; `hub-rel:` is only the portable anchor used to regenerate it later, never
        written into the body itself). **Place the marker as the first line of the stub's body,
        immediately after the closing `---` of the frontmatter — never before the opening `---`.**
        A leading comment before the frontmatter delimiter breaks Claude Code's YAML frontmatter
        parsing entirely, so the skill's `description` field never reaches the always-resident
        skill listing (the harness falls back to showing raw file content instead):
        ```
        <!-- shared_resources: <entry name> adopted YYYY-MM-DD index-sha256:<hash of the entry
        file's content at adoption time> hub-rel:shared_resources/<entry file's own name> -->
        ```
     4. **Show the draft — trigger description and stub body — to the user and confirm before
        writing anything.** Same checkpoint this file already requires for Saving, above.
     5. On confirmation, write the skill stub to this project's own
        `.claude\skills\<name>\SKILL.md` only — never into `toolkit\`. This content is
        private-only by construction: no canonical stub source for it ever lives in the public
        toolkit repo, not even the trigger wording or the target path.
     6. **Then run the "Adopted Shared Resources" check, below** — every `reference`/`tool` Apply
        ends here, not just the ones that turn out project-defining.
   - **`insight`** — see "Insights are different" below; never a plain pointer and not a
     lazily-loaded skill stub either in the `reference`/`tool` sense — an insight is content that
     gets consumed into the project, by a destination decided at apply time.

### Adopted Shared Resources: a directive proportional to how central it is

The skill stub above makes an adopted resource *reachable* (autonomous relevance-matching) — it
doesn't make the model reach for it. A resource that's genuinely occasional in this project is
fine relying on that alone (its own vocabulary is unusual enough in everyday conversation that the
skill's own matching is the right primary tool). A resource — or a whole Category — this project's
work is actually *about* is not: relying on autonomous triggering alone for something this central
is exactly the failure mode that motivated this section (a real client SEO question, phrased with
zero SEO jargon, answered from generic training-data knowledge because nothing backstopped the
skill's own judgment). So this project's own `CLAUDE.md` carries a `### Adopted Shared Resources`
subsection, mechanically maintained from the first adoption onward (never hand-edited; treat any
manual edit found there as drift to reconcile, same as any other mechanically-owned content in
this mechanism) — every `reference`/`tool` Apply ends by writing/updating its **listing** (below).

**Two parts, only one of them ever changes.** The subsection opens with a **fixed general
paragraph** — what `shared_resources` is, how adoption works, and the two possible outcomes
(mandate vs. situational) — true regardless of what's actually been adopted, so it ships as part
of the scaffolded template itself (`consumer_CLAUDE.md.tmpl`), never written or edited by Apply/
Forget. Underneath it sits the **listing** — a `_None yet._` roster-line fallback, or a real
roster line plus, once a Category reaches 100% coverage, a Project-defining paragraph — which is
the only part Apply/Forget ever touch. This split exists specifically so
nothing here only reads correctly in one adoption state: a project with zero adoptions, one
occasional resource, or a fully-adopted defining domain all get the same correct general framing,
because that framing was never conditional on adoption state to begin with.

**Fixed location, and why it's fixed there specifically:** as the last subsection in the file,
after `## Shared Workflow Protocol`'s `{{PROTOCOL_IMPORTS}}` line — never before `## Tower Crane In
Use`, even though this content is itself project-specific like a hand-authored directive. Three
reasons, all load-bearing:
1. `## Tower Crane In Use` must stay the first Tower-Crane-related heading in the file — Tower
   Crane may be adopted mid-lifecycle onto a `CLAUDE.md` that already carries any amount of
   unrelated hand-authored content (a real, live consumer's `CLAUDE.md` has ten unrelated headings
   before it), and this mechanism is Tower-Crane-owned content, not the user's own — it belongs
   after that marker, not ahead of it, same as everything else Tower Crane manages.
2. **General before specific, all the way down.** `shared_resources` is itself one of the pieces
   `## Shared Workflow Protocol` imports — a specific kind of shared workflow, which is in turn a
   specific facility `## Tower Crane In Use` provides. Placing this subsection ahead of `## Shared
   Workflow Protocol` would introduce the specific mechanism before the general one it belongs to;
   placing it ahead of `## Tower Crane In Use` entirely would introduce it before Tower Crane
   itself. Last, after everything more general, is the only position consistent with that ordering
   — and it's also why the subsection's own internal ordering mirrors it: the fixed general
   paragraph (what `shared_resources` is, in general) before the listing's own project-specific
   entries (what *this* project has actually adopted).
3. `disconnect_consumer.py`'s `replace_prose_sections()` finds the removal boundary by searching
   for `## Tower Crane In Use` and sweeping to the next `## ` heading after `## Shared Workflow
   Protocol` (or EOF — where it lands today, since nothing after that heading is itself a `## `
   heading). A `###` subsection is invisible to that search regardless of where it sits in
   between, so it's always safely inside the sweep; a sibling `##` heading would either sit
   entirely outside the sweep (before `## Tower Crane In Use`) or become the sweep's own premature
   end boundary (right after `## Shared Workflow Protocol`), either way surviving a disconnect that
   should have removed it.

**The fixed general paragraph, verbatim** (part of `consumer_CLAUDE.md.tmpl` — reproduced here so
this file's own reasoning above stays checkable against the real text):
> One of the pieces above, `shared_resources`, governs a cross-project reference library the
> operator maintains centrally in the hub and reuses across projects — search, adopt, save, and
> retrieval all follow that piece's own mechanism.
>
> 1. **General directive.** If a shared resource has been opted into, consult it whenever the
>    current question is relevant to its topic.
> 2. **Project-defining directive.** If an opted-in shared resource is project-defining, default
>    to consulting it before gathering other information or answering — do not first judge
>    whether the question is "relevant enough" to warrant the check; treat the check itself as the
>    default action, not a conditional one. This default governs only *whether* to consult the
>    resource, not *which part* of it to read — leave that selection to the resource's own
>    skill(s)/mechanism.

**Before computing anything, two gates — both required — decide whether this entry's Category can
ever be treated as project-defining at all:**

1. **`identity_eligible: true`** for this entry's Category, read from `shared_resources\
   resource_relationships.yaml`'s `identity_eligible:` block (written at Saving, step 1/6, when the
   Category was first created). Missing or `false` → this gate fails. No Category at all → this
   gate fails, trivially (there is nothing to be eligible).
2. **More than one active `CATALOG.md` entry** in this Category. A 1-member category can't be
   "comprehensively adopted" in any meaningful sense — 100% of one is degenerate, not a signal.

**If either gate fails**, this entry just joins the roster line (below) with no Project-defining
paragraph — no percentage of anything gets computed. This is what keeps something like
`git_permission_allowlist` (an `insight` with no Category at all) from ever being mistaken for
project-defining, no matter how many other resources this project goes on to adopt.

**If both gates pass, measure Tier coverage, not entry coverage.** The adoption unit in this
mechanism is a *skill* (Saving step 7's Category-level fallback, or a narrower Tier-scoped skill
split out of it), and a single skill can legitimately cover every entry in a whole Tier — or, for
the fallback, the whole Category — live off `CATALOG.md`/`resource_relationships.yaml`, with no
per-entry adoption step at all. Counting individual `CATALOG.md` rows would wrongly read a
one-skill, whole-category fallback adoption as a sliver of coverage. Instead:

- **Denominator**: every distinct `Tier` value with at least one active `CATALOG.md` entry in this
  Category (e.g. a Category with Primary, Evaluation, Planning, and Process Tiers has a
  denominator of 4).
- **Numerator**: how many of those Tiers this project has an adopted skill actually covering.
  Read this project's own `.claude\skills\*\SKILL.md` stubs tagged with this Category (`category:`
  frontmatter) to see which Tier(s) each one's own scope names — a Category's first-ever skill is
  typically the whole-Category fallback and covers every Tier by itself; a later-split Tier-scoped
  skill covers just its own (see "Discovery: search or browse, then select, then apply" and Saving
  step 7 for how these get built). A `private_categories:` subscription counts as covering every
  Tier at once, present and future, the same as the fallback. Include the entry/skill just applied.

**The listing has two pieces, both mechanically maintained:**
- **Roster line** — always present once at least one resource is adopted, superseding the
  `_None yet._` fallback the scaffolder writes:
  > **Shared resources adopted for this project:** {{ADOPTED_RESOURCES}}.

  where `{{ADOPTED_RESOURCES}}` is every currently-adopted resource's own identifier (its skill
  name where adoption produced one, else its `CATALOG.md` entry name), comma-separated and each in
  backticks — regardless of Tier 1/Tier 2 status. Every Apply appends this entry's identifier to
  the existing list (order doesn't matter); every Forget removes it (see "Forgetting," below).
- **Project-defining paragraph** — present only when at least one Category has reached 100% Tier
  coverage (below); absent entirely otherwise, since Tier 2 items need nothing beyond the roster
  line above and the general paragraph's own "General directive." No separate per-resource topic
  sentence for Tier 2 items — the roster line's name plus the resource's own skill/mechanism is
  enough for the general directive to act on; don't add one back.

- **100%** — draft the Project-defining paragraph and show it for confirmation before writing, same
  discipline as every other write in this mechanism. The general paragraph above already covers
  *why* a missed trigger matters and what the mandate directive requires — this paragraph only
  needs to name the domain and scope the assumption:
  > **Project-defining shared resource(s) for this project:** {{CATEGORY}}, reached via the skills
  > above. Assume most matters discussed in this project are at least adjacent to this resource
  > unless the session's topic clearly falls outside its domain.
  >
  > If a real decision turns on a principle no existing entry covers, say so explicitly rather than
  > filling the gap silently — that's the moment to save a new entry, not reason around quietly.

  If more than one Category has independently reached 100%, list them comma-separated after the
  label (`{{CATEGORY_1}}, {{CATEGORY_2}}, reached via the skills above.`) rather than writing a
  separate paragraph per Category — one shared closing sentence covers all of them (this mechanism
  favors speed over precision). If this
  Category is newly reaching 100% and the Project-defining paragraph doesn't exist yet, add it;
  the roster line itself never needed to change to get here, so there is nothing to consolidate.
- **A large majority but not all** (rule of thumb: roughly four-fifths or more, or "all but one" of
  a small Tier count) — draft nothing beyond the roster-line addition. Ask directly whether this
  project's identity centers on the Category; if so, name the specific not-yet-covered Tier(s) and
  offer to adopt a skill for each (each adoption re-runs this same check). Only write the
  Project-defining paragraph once coverage actually reaches 100%, whether via this prompt or
  independently later.
- **Below that** — the entry's identifier joins the roster line and nothing else is written.

A `private_categories:` subscription grant is a parallel trigger point for this same check, not a
separate mechanism — subscribing to a Category is an instant path to 100% coverage of it (present
and future entries alike), so it runs the same two gates and, if both pass, drafts the same
Project-defining paragraph.

### Forgetting

**Forget** removes *this project's own adopted reference* — the `@import` line, pointer note,
project-local `.claude\skills\<name>\SKILL.md` stub, or an adopted `insight` artifact (a
`CLAUDE.md` section, pasted code/config, or a skill stub — whichever destination Apply chose) plus
its adoption marker where one exists — from this project. It never touches the entry in
`shared_resources\` itself, which stays available for this or any other project to re-adopt later.
Use it when a resource was adopted for a one-off task and is now just `CLAUDE.md` bloat, or to
reset this project's behavior back to before adoption. If Claude's advice in some domain seems
off, checking whether a relevant resource was ever adopted (via browse's in-use indicator) — and
forgetting it if it's stale — is a reasonable first move.

**Also update `### Adopted Shared Resources`'s listing** (see above — never its fixed general
paragraph, which stays exactly as scaffolded regardless of what's adopted): remove this entry's
identifier from the roster line, and, if it was part of a Category currently covered by the
Project-defining paragraph, recompute that Category's Tier coverage — dropping below 100% removes
the Category from the Project-defining paragraph (or removes the paragraph entirely if no Category
still qualifies), while the forgotten entry's identifier simply disappears from the roster line
along with it. If this project's last shared_resources adoption anywhere is forgotten, revert the
roster line to its scaffolded fallback (`**Shared resources adopted for this project:** _None
yet._`) — the general paragraph above it and the `### Adopted Shared Resources` heading itself
never change.

### Backfilling "Adopted Shared Resources" for pre-existing adoptions

A one-time retrofit, for this reason: "Adopted Shared Resources" only runs
*during* an Apply or a `private_categories:` grant, so any resource a project adopted before this
mechanism existed has no line/paragraph for it yet, and nothing will ever trigger the check on its
own — there's no future Apply coming for something already fully adopted. Triggered by something
like *"shared resources — backfill Adopted Shared Resources"* (every consumer) or *"...for
`<consumer>`"* (one project):

0. If this project's `CLAUDE.md` predates this mechanism entirely (scaffolded before `### Adopted
   Shared Resources` existed, or missing it for any other reason), first add the section itself —
   the `### Adopted Shared Resources` heading plus its fixed general paragraph, verbatim from
   `consumer_CLAUDE.md.tmpl`, positioned per "Fixed location" above — before drafting any listing
   content. Confirm before writing, same as everything else here.
1. For the project(s) in scope, read its effective adopted set (`private_opted_in:` plus any
   `private_categories:` subscription's current members) and group by Category.
2. For each Category with any adoption at all, run the same two gates and the same Tier-coverage
   computation as Apply's own check, above — reading each adopted `.claude\skills\*\SKILL.md`
   stub's own scope to determine which Tier(s) it actually covers, never assuming skill-count
   equals Tier-count (a whole-Category fallback is one skill covering every Tier at once).
3. Draft the resulting state for the whole project in one pass — the roster line naming every
   adopted resource, plus a Project-defining paragraph for whichever Category(ies) reach 100% (or
   none) — and show it for confirmation before writing, same as any other write here. This can
   *replace* a hand-authored "Adopted Shared Resources" section (or an
   older CLAUDE.md paragraph pre-dating this mechanism entirely) with the mechanism's own real
   output — the point of running a backfill is to confirm the mechanical result matches, not to
   trust a hand-written guess at what it would say.
4. Write, then propagate once per project (not once per Category).

### Retrieval Audit — noticing, comparing, and fixing a gap in one pass

A moment for noticing, comparing, and fixing a retrieval gap in one pass. Enter this whenever the
literal `"shared resources"` phrase is used to ask it directly ("did we use the right resources,"
"what would have caught this"), or the user otherwise asks what was retrieved and why.

**Why this exists as its own named flow, not left to ad hoc reconstruction:** a real consumer
session once needed three separate manual asks in sequence to get from "what did you use and why" to
a drafted fix. This flow does all of that in one pass and states the self-serve fact plainly, at the
exact moment it's needed.

1. **Narrate what happened, unprompted, in one pass** — every `shared_resources\`-adjacent read or
   tool call actually made (this session, or the task in question), what surfaced it, and whether
   that was the right call. Produce this table shape proactively, in one reply, rather than waiting
   for it to be drawn out across several separate asks.
2. **Compare against what plausibly should have fired** — the same Category/Tier peers,
   `CATALOG\*.md` rows, and `resource_relationships.yaml` graph neighbors of whatever was actually
   read — and name anything not read that arguably should have been.
3. **For each real gap, diagnose which kind it is before proposing a fix** — these are not
   interchangeable:
   - A Category skill's `description:` didn't match this session's actual wording → widen the
     description (a small edit to the skill stub).
   - The skill matched but its routing (Retrieval procedure) never reached the entry → a catalog
     problem: the entry's `Category`/`Tier` placement, or a missing `resource_relationships.yaml` edge.
   - The gap is a skill/gate never invoked at all (e.g. a Category's own fallback/Primary-tier skill
     depending on a separate self-initiated call that never happened) → a skill-design question, out
     of this flow's scope, for the operator to take up separately (as a hub-session change, per
     `agents_tools\*.md`'s tool-lifecycle procedures).
4. **Draft the concrete fix immediately** for whichever of the first two kinds applies, presented
   for one-step approval, never an open "what should the fix be" question. **State plainly that
   approval writes directly to the hub with no ticket and no separate session** — the same
   self-approving write every other write in this file already is. This sentence is the actual fix
   for the belief that caused the 2026-09-06 gap; say it, don't assume it's already known.

### Insights are different

An `insight` isn't referenced in place or lazily loaded — it's consumed into the adopting project,
by value. It carries up to three parts, and how much of each varies per entry rather than being
fixed by a template:

1. **Retrieval hook** — the pain-point framing that should trigger a *future session's human*
   recall. Written symptom-first, not solution-first (*"SEO client wants AI-visibility metrics we
   can't get from Search Console"*, not *"notes on AEO/GEO tracking limitations"*) — retrieval
   depends on a future session's human recognizing "I've hit this exact wall before," not on
   scanning a catalog description written for a different job.
2. **Summary** — the settled conclusion, framed so retrieval means "apply this, don't re-derive or
   re-argue it." The judgment call already happened once; the point of saving it is to not pay
   that reasoning cost again.
3. **Zero or more verbatim blocks** — content marked "use this exactly," not "understand and
   adapt." Can be absent entirely (a pure judgment call, like a diagnosis or a strategic decision),
   present alongside a summary, or be effectively the entire entry.

**Why retrieval is always human-triggered, never a model trigger:** `reference`/`tool` are
converging toward autonomous Track-1 skill triggers because the *model* needs to recognize
relevance across a conversation without the user saying the right words. `insight` deliberately
never gets this treatment — the retrieval trigger is a human noticing **"I've already solved this
exact pain point in another project,"** a memory chain only the human has, since one Claude Code
session in one project has no memory of any other. This is permanent, not a gap waiting on a
future Track-1 conversion.

#### Saving an insight — a negotiation, not a fixed write

Triggered by something like *"shared resources — save this as an insight."* Unlike a `reference`/
`tool` save (fixed classify → confirm → write), Claude actively helps shape the entry, because the
right hook/summary/verbatim split genuinely varies per entry and isn't derivable from a template:

1. **Propose** a retrieval hook drawn from whatever pain point actually triggered the preceding
   conversation — never a blank "what should the trigger be?" — and propose which parts of the
   conversation warrant a verbatim block versus synthesis into the summary.
2. The user confirms or adjusts both.
3. Same confirm-before-write checkpoint every other write in this mechanism requires: show the
   full drafted entry, get an explicit go-ahead, then write it as one new file in
   `shared_resources\` with `Kind: insight` in `CATALOG.md`, roughly shaped:
   ```markdown
   # <Entry Name>

   **Kind:** insight
   **Retrieval hook:** <symptom-first framing>

   ## Summary
   <settled conclusion>

   ## Verbatim: <label>
   ```
   <exact content to reuse as-is>
   ```
   ```
   (repeat the `## Verbatim:` block zero or more times; omit the whole section if this entry is a
   pure judgment call with nothing to reuse verbatim)
4. Propagate the write (see "Every write here ends with the same propagation step" above).

This can be as small as a one-line hook plus a one-sentence summary, saved in under a minute, or as
long as several separately-labeled verbatim blocks for a deep investigation — don't impose ceremony
on the simple end.

**If a verbatim block is a script/hook/command that needs to reference its own file's location**
(not an external target — see "Per-host availability for pointer entries" above for that case),
it must self-resolve on every host and every adopting project without any hand-filled path: use
the runtime's own live self-location mechanism (e.g. Claude Code's `$CLAUDE_PROJECT_DIR` for a
hook `command` field), never `<path-to-this-script>`-style fill-in-the-blank prose. An insight is
copied by value into each adopting project with no central re-sync (see "Insights are different"
above) — a hardcoded absolute path baked into a verbatim block is guaranteed to go stale the next
time that project's directory moves or is renamed, and nothing in the system will ever catch it or
fix it after the fact. This is a different case from a `tool`/pointer-`reference`'s `Hosts:`
block: that tracks per-machine paths to *one shared external target*; a self-referencing script has
no external target to track at all — each adopting project's own copy must resolve independently,
so it needs no `Hosts:` block either.

#### Applying an insight — routes through a destination question

Triggered by something like *"shared resources — get the checkpoint insight from another project
and apply it here."* Runs the same search/browse/select flow above to find the right entry, then
asks which destination fits — decided **per adopting project, at apply time**, not fixed at save
time, since the same insight can legitimately land differently in different projects:

1. **Becomes project code/config** (a verbatim permissions list, a code fragment) — write it
   directly into the file it belongs in. Zero ongoing context/token cost afterward — it's just
   normal file content now, not a directive sitting in `CLAUDE.md`. Add the adoption marker as a
   comment near what was written if the file format supports comments; if it doesn't (e.g. JSON),
   skip the marker — adoption tracking for this destination is an accepted gap (see "Adoption
   tracking" below).
2. **Becomes a standing `CLAUDE.md` rule** — run the same Track 1/2 test `continuity.md`'s split
   already established: needed at or near the start of every session, with an unacceptable failure
   mode if missed (Track 2 — write it directly into `CLAUDE.md`, adapting the summary/verbatim
   content into this project's own wording where adaptation is needed, verbatim blocks kept
   verbatim), or only relevant in occasional, recognizable moments (Track 1 — reuse the skill-stub
   Apply procedure above: draft a trigger description from the retrieval hook, confirm, write the
   adapted summary/verbatim content directly into this project's own `.claude\skills\<name>\
   SKILL.md` — the insight's content itself, not a live pointer back into `shared_resources\`,
   since the whole point of an insight is that the judgment call already happened and doesn't need
   re-reading from the source). Either way, add the adoption marker:
   ```
   <!-- shared_resources: <entry name> adopted YYYY-MM-DD -->
   ```
3. **Informs judgment only, right now** — the conclusion changes this conversation's answer or
   action; nothing gets persisted anywhere. Zero cost by construction, and a legitimate, common
   outcome, not a failure to produce an artifact. No adoption marker, since nothing was written.

In every case, never paste an insight's saved content verbatim into a *different* wording context
without adapting it first, except inside an actual `## Verbatim:` block — the summary exists
precisely so the rest of the entry can be adapted rather than copy-pasted wholesale.

#### Adoption tracking and archiving

In-use tracking for `insight` is fuzzier than for `reference`/`tool`: once "nothing persisted" is a
legitimate Apply outcome, there's no reliable place to leave a marker for browse to find. Where an
artifact *is* created (destinations 1 or 2 above), add the adoption marker so browse's in-use
indicator and forget can find it; where nothing is persisted, that's an accepted gap, not a bug —
adoption tracking there reverts to the same human-memory-chain reasoning that makes discovery work
in the first place.

**An insight can outlive its usefulness in `shared_resources\`, unlike `reference`/`tool`.** Once
every currently-active project has independently rediscovered and adopted a given insight, it's no
longer earning its slot in an ordinary browse listing — it's already folded into however many
projects absorbed it. **Archive** it rather than deleting: triggered by something like *"shared
resources — archive the checkpoint-pattern insight, it's everywhere now."* This is a narrow write
in the same self-approving spirit as Saving above — no ticket, no round-trip:

1. State what's about to happen and get an explicit go-ahead, same as every other write here.
2. Edit that entry's row in `CATALOG.md`, setting the `Status` column to `Archived YYYY-MM-DD`.
   Never delete the entry's own file or its catalog row — an archived entry stays fully readable
   and re-adoptable, just hidden from an ordinary browse listing (see "Discovery" above) so a
   brand-new project that hasn't hit this pain point yet can still find it instead of quietly
   re-solving the same problem from zero.
3. Propagate the write (see "Every write here ends with the same propagation step" above).

Archiving is always a deliberate, user-initiated call — never automatic, matching this project's
own `project_progress_archive.md` archiving stance. `reference`/`tool` entries don't get this
treatment: they don't expire the way an insight does, since ongoing domain knowledge stays useful
indefinitely rather than being "absorbed" once and done.

### Maintenance you might encounter

`shared_resources\` entries can be split, consolidated, renamed, or deleted over time as ordinary
upkeep. None of that should silently change this project's behavior. If an adopted entry's file no
longer resolves (a broken `@import`, a pointer to a file that's gone), that's a signal something
was restructured without a working stub left behind — treat it as worth a note back to a hub
session, not something to silently work around. This risk doesn't apply to an already-adopted
`insight`: its content was copied or adapted into this project at apply time, not referenced live,
so deleting or restructuring the source entry later can't retroactively break what this project
already has.

### Checking adopted references at resume

This now lives in `templates\shared_resources_resume_check.md` — the Track-2 companion piece every
consumer always imports alongside this skill, since a broken reference must fail loudly at the next `resume`, not
whenever a session happens to re-trigger this mechanism. Nothing to do here — it runs on its own.
