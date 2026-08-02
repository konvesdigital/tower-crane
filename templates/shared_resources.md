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
-->

## Using shared resources and insights

This hub keeps a **`shared_resources\`** folder at the hub root (one level up from `toolkit\` —
see `templates\filing.md` if the hub-root/`toolkit\` split is unfamiliar). Unlike everything else
at the hub root, this one folder is not off-limits to write from inside a project session — see
"Saving" below. It holds three kinds of entry, indexed in one catalog,
`shared_resources\CATALOG.md` (`Name | Kind | File | Description | Added | Status`):

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
alone, in which case ask what's wanted (search, browse, save, apply, forget, archive).

On firing, say so out loud before doing anything else — e.g. *"Switching to shared resources —
thinking across projects now, not just this one."* — so the context-switch is visible, not just
assumed. Everything below happens **inside** that acknowledged context. There's no separate exit
trigger: the mode is scoped to completing the one action (a search, a save, etc.), and the
conversation returns to ordinary project-local framing once it resolves — unlike `checkpoint`/
`resume`, there's no separate repo or session to deliberately zoom back out of.

### Discovery: search or browse, then select, then apply

Three explicit steps — never collapsed into one, since a query can turn up more than one genuinely
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
        references at resume" below):
        ```
        <!-- shared_resources: <entry name> adopted YYYY-MM-DD index-sha256:<hash of the entry
        file's content at adoption time> -->
        ```
     4. **Show the draft — trigger description and stub body — to the user and confirm before
        writing anything.** Same checkpoint this file already requires for Saving, below.
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
  convention that should apply generically, not domain knowledge — → this is **not**
  `shared_resources\` content. Don't save it here; point at the ticket system instead
  (`templates\filing.md`'s `Type: proposal` ticket, or an ordinary bug ticket). If this same
  content already lives in `shared_resources\` and has proven itself broadly, see filing.md's
  graduation path instead of re-filing from scratch.
- **Neither is obvious** → ask before saving.

Then, before writing anything, state what's about to happen and get an explicit go-ahead: the
entry's name, its `kind`, a one-line description, and that it's about to be written into
`shared_resources\` plus a new `CATALOG.md` row. Only write after confirmation — this is the one
disk-writing action in the whole mechanism and the one carrying the classification call above, so
it gets its own explicit checkpoint even though entering the mode already got one.

When saving a `reference` or `tool` entry: create one new file in `shared_resources\`, then append
one row to `shared_resources\CATALOG.md` (`Status` column left blank — active by default). For
`insight`, see "Insights are different" below — its save flow is a negotiation, not a fixed
write.

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

This can be as small as a one-line hook plus a one-sentence summary, saved in under a minute, or as
long as several separately-labeled verbatim blocks for a deep investigation — don't impose ceremony
on the simple end.

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
