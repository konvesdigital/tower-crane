<!--
Canonical Track-1 skill stub source: shared_resources (toolkit-governed — design\directive_economy.md,
MANDATORY for every consumer since 2026-08-01 — design\resource_sharing_model.md's "Mechanism
delivery: mandatory, not optional").
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
Status`). `Category`/`Tier` are optional metadata (`design\shared_resources_relationship_graph.md`)
— a broad domain tag plus a Category-scoped retrieval-circumstance pointer — and a companion file,
`shared_resources\resource_relationships.yaml`, holds typed edges between entries plus each
Category's situational-tier circumstance definitions. See "Saving" and "Retrieval" below for how
these get written and read; an entry with no Category is unaffected by any of this. A second,
optional sidecar, `shared_resources\trigger_index.yaml`, holds hand-authored string-match trigger
phrases per entry — a deterministic recognition layer under the Category/Tier skill mechanism,
consulted by a `UserPromptSubmit` hook rather than by an agent's own judgment
(`design\shared_resources_mechanical_trigger.md`); see Saving step 2a below for how entries get
triggers, and `MENU.md`'s `shared_resources_trigger_match` row for the opt-in.

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
alone, in which case ask what's wanted (save, search, browse, apply, forget, archive, adjust
triggers, backfill triggers).

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
   everything below). If the message that triggered this save itself carried a `shared_resources
   mechanical trigger` hit (the `additionalContext` block `shared_resources_trigger_match.py`
   injects, when opted in — `design\shared_resources_mechanical_trigger.md`), treat the entry it
   named as a live candidate for "this might not be new" — folding into that entry or tying an edge
   to it in step 3 — before treating this as a fresh save. A matcher hit firing on the very message
   that starts a save is exactly the situation it's most useful for: the content is topically close
   enough to trip an existing trigger, which is real evidence worth weighing, not noise to ignore.
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
2a. **Draft trigger phrases** (`design\shared_resources_mechanical_trigger.md`) — draft 3-8 short
    string-match phrases from the entry's **own full content**, never just its one-line `CATALOG.md`
    description or title (same anti-pattern the Apply procedure's skill-trigger drafting already
    calls out, below — a description written for a human scanning many rows isn't shaped for
    recognizing an organically-arising question). Specific multi-word phrases, not single common
    words, and deliberately covering more than one angle rather than minor rewordings of the same
    phrase:
    - the entry's own jargon/terminology, as written;
    - a plain-English restatement of the same terms (both the spelled-out and the abbreviated form
      where one exists, e.g. `"Google Search Console"` alongside `"GSC"`);
    - at least one **symptom-first** phrasing of the underlying pain point — the same framing
      `insight`'s retrieval hook already uses (below): describing the situation that needs this
      entry, not the entry's own solution/vocabulary. This is the angle most likely to be missed by
      just restating the content, and it's exactly the shape of phrasing that motivated this
      mechanism in the first place (`design\shared_resources_mechanical_trigger.md`'s Part 1 — the
      real incident's own phrasing named neither the entry nor its vocabulary).

    Before showing the draft, check it against `trigger_index.yaml`'s existing phrases and flag —
    never silently allow — an exact or near-duplicate of another entry's phrase, or a phrase generic
    enough to fire on unrelated messages (a single common word, or anything overlapping the literal
    `"shared resources"` gate phrase itself); the user decides whether to keep, narrow, or drop each
    flagged phrase. Show the draft, let the user edit/approve. This is a one-time cost paid once per
    entry, at the moment a session is already engaged with its content; skipping this step is fine
    (an entry can always get triggers later, or never) — it only means this entry stays reachable
    through the existing skill-gate/search/browse paths, not this mechanical one.
3. **Show the active node's existing edge-neighborhood, don't ask an open question.** If a
   process/entry already in play this session has existing edges in `resource_relationships.yaml`,
   show them compactly (the same `Entry | Edges` shape `design\shared_resources_relationship_graph.md`'s
   worked SEO table uses) and ask whether to tie the new entry to it the same way — answerable
   yes/no/adjust, not a blank "what should this tie to?" Edge types: `process-material`
   (directional, "reach for this while doing that" — the dominant shape), `prerequisite`
   (directional, a real specific dependency, not a generic "A is foundational" claim),
   `lifecycle-sibling` (undirected, same object/question at a different stage), `related`
   (undirected, no specific claim — the zero-effort default, always available, needs no
   justification).
4. **No obvious active node** (a genuinely cold save) — fall back to asking, scoped by Category:
   *"Which of `[Category]`'s existing entries/processes does this belong near, if any — or is this
   a first-of-its-kind save?"* — never the full graph dumped at once.
5. **Confirm before writing anything** — the entry's name, `kind`, `Category`/`Tier`, one-line
   description, any edge(s) from steps 3–4, any trigger phrases from step 2a, and that it's about to
   be written into `shared_resources\` plus a new `CATALOG.md` row (plus any
   `resource_relationships.yaml`/`trigger_index.yaml` change). Only write after confirmation — this
   is the one disk-writing action in the whole mechanism and the one carrying the classification
   call above, so it gets its own explicit checkpoint even though entering the mode already got one.
6. **Write.** For a `reference`/`tool` entry: create one new file in `shared_resources\`, append
   one row to `CATALOG.md` (`Status` blank — active by default) with its `Category`/`Tier`, write
   any new/updated `tiers:` circumstance text or edge(s) into
   `shared_resources\resource_relationships.yaml`, and — if step 2a produced any trigger phrases —
   append a `resource`/`triggers` entry to `shared_resources\trigger_index.yaml` (create the file
   with an `entries: []` skeleton first if it doesn't exist yet). For `insight`, see "Insights are
   different" below — its save flow is a negotiation, not a fixed write, but ends the same way.
   Either way, finish with **propagate the write** (see below).
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

### Every write here ends with the same propagation step

Any write into `shared_resources\` — a new `reference`/`tool`/`insight` entry, a
`trigger_index.yaml` addition (step 2a above), an `insight` archive edit, or a new-host addition to
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
is what a flat "read this whole file in full" instruction (the retired `seo_*_index.md` shape)
couldn't guarantee: that instruction was easy for a session to satisfy from memory instead of
actually doing (`2026-08-31_toolkit_private_seo-skill-index-not-read-in-full.md`). Naming the
concrete next action — read *this specific file* — closes that gap structurally instead of
restating the same prose instruction more emphatically:

1. **Identify the specific active anchor entry** for the current task — a nameable file, not an
   abstract "the whole tier" — from the task's own shape (e.g. a monthly report in progress names
   `monthly_movement_report_workflow.md` directly; a head-to-head competitor comparison names
   `seo_evaluator_gem.md` directly). A Category-level fallback skill does this across the whole
   Category's live graph; a Tier-scoped skill does it within just its own Tier.
2. **Read that entry.** Not a paraphrase from memory of a previous read — `CATALOG.md` and
   `resource_relationships.yaml` float on HEAD and may have changed since.
3. **Look up its graph neighbors in `resource_relationships.yaml`** and state them by title —
   never preload their content just because an edge exists. E.g. completing a monthly report's
   "why" analysis surfaces `trend_shape_vs_period_totals.md` and `gsc_position_diagnostic.md` by
   name via their `process-material` edges into `monthly_movement_report_workflow.md`, without a
   separate full-file read to discover they exist.
4. **Anything not directly linked but still in the same Category/Tier stays reachable via an
   ordinary browse** (see "Discovery" below) — the graph narrows what's surfaced by default, it
   doesn't hide the rest.

### Discovery: search or browse, then select, then apply

Once something exists to find — either saved here just now, or by someone else in another session
— three explicit steps — never collapsed into one, since a query can turn up more than one genuinely
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
     standing `@import` (`design\directive_economy.md`'s Track 1: autonomous on-demand
     loading — the model notices when a live question matches and pulls the content in, instead
     of it sitting resident in every session forever). Concretely:
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
        since the trigger above was drafted from it (`design\directive_economy.md`'s "Drift
        mechanics", checked by `scripts\check_shared_resource_drift.py` — see "Checking adopted
        references at resume" below) — plus the entry file's own path relative to the hub root
        (`hub-rel:`), so a later `relocate.py` run can recompute the stub's embedded path for
        whichever host it's running on rather than leaving it baked to the host that adopted it
        (`design\directive_economy.md`'s "Adopted-stub path portability" — the stub body's own
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
        private-only by construction (see "Two homes within Track 1" in
        `design\directive_economy.md`): no canonical stub source for it ever lives in the public
        toolkit repo, not even the trigger wording or the target path.
   - **`insight`** — see "Insights are different" below; never a plain pointer and not a
     lazily-loaded skill stub either in the `reference`/`tool` sense — an insight is content that
     gets consumed into the project, by a destination decided at apply time.

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

### Adjusting triggers — recalibrating after living with them

Triggered by something like *"shared resources — the position diagnostic trigger keeps firing on
unrelated stuff"* or *"shared resources — add a trigger for X, it should have caught this."* A
trigger phrase in `trigger_index.yaml` is a calibration, not a locked decision
(`design\shared_resources_mechanical_trigger.md`'s own framing: a real reliability trade, not a
perfect guarantee) — this is the narrow write that lets it drift toward better precision/recall in
either direction, same self-approving spirit as Saving:

1. **Identify the entry** — same search/browse flow as any other action, if not already named.
2. **Show its current `trigger_index.yaml` phrases**, or state plainly it has none yet and route to
   "Backfilling triggers" below instead.
3. **Diagnose which direction:**
   - **Too greedy** (fired on something unrelated) — the actual message that mis-fired is the best
     evidence for which phrase was too broad; use it, don't guess abstractly. Narrow the phrase's
     wording or remove it outright.
   - **Too stingy** (a real need didn't surface it) — draft additional phrase(s) covering the missed
     angle, same guidance as Saving step 2a (full entry content, jargon/plain-English/symptom-first
     mix, cross-checked against every entry's existing phrases for collision/genericity).
4. **Confirm before writing**, same checkpoint every other write here requires.
5. **Write** the updated phrase list to `trigger_index.yaml`, then **propagate** (see "Every write
   here ends with the same propagation step" above).

### Backfilling triggers for pre-existing entries

Triggered by something like *"shared resources — backfill triggers"* (a whole-catalog pass) or
*"shared resources — add triggers for `<entry>`"* (one entry). Every entry that predates this
mechanism, or was saved without trigger phrases, has no `trigger_index.yaml` entry yet — this closes
that gap without a separate registration step
(`design\shared_resources_mechanical_trigger.md`'s "Backfill"):

1. List every **active** `CATALOG.md` entry with no `trigger_index.yaml` entry yet. An archived
   entry is still reachable via ordinary browse either way — skip it unless asked for by name.
2. For each, draft phrases exactly as Saving step 2a does (full content, jargon/plain-English/
   symptom-first mix, collision/genericity check against phrases already drafted this pass *and*
   against every entry already in `trigger_index.yaml`).
3. Show the whole batch for review in one pass rather than confirming entry-by-entry — cheaper for a
   genuine backfill — but let the user pull any single entry out for adjustment before approving the
   rest.
4. Write every approved entry to `trigger_index.yaml` in one pass, then **propagate once for the
   whole batch** (a single commit covering the sweep, not one per entry — this is maintenance, not
   an ongoing stream of individual saves).

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
consumer always imports alongside this skill (`design\directive_economy.md`'s "shared_resources.md's
own mechanism moves to Track 1"), since a broken reference must fail loudly at the next `resume`, not
whenever a session happens to re-trigger this mechanism. Nothing to do here — it runs on its own.
