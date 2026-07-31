<!--
Shared protocol piece: shared_resources.md (OPTIONAL — opt in when a project wants to use the
resource/pattern-sharing mechanism; not yet wired into the scaffolder or filing.md's mandatory
set — that wiring is separate follow-up work).
Home: ~\Documents\Claude\tower_crane\toolkit\templates\shared_resources.md
Imported by a consumer's CLAUDE.md via:
  @~/Documents/Claude/tower_crane/toolkit/templates/shared_resources.md
Float-on-HEAD: edits here reach every consumer that has imported it the next time it runs. Keep
this file project-agnostic — it must read correctly imported into ANY consumer. Refer to "this
project", never a specific consumer name, and never a real path/client name (this file lives in
`toolkit\`, the public repo).
-->

## Using shared resources and patterns

This hub keeps a **`shared_resources\`** folder at the hub root (one level up from `toolkit\` —
see `templates\filing.md` if the hub-root/`toolkit\` split is unfamiliar). Unlike everything else
at the hub root, this one folder is not off-limits to write from inside a project session — see
"Saving" below. It holds three kinds of entry, indexed in one catalog,
`shared_resources\CATALOG.md` (`Name | Kind | File | Description | Added`):

- **`reference`** — passive, read-on-demand domain knowledge (methodology, facts). Using one means
  reading it, or `@import`ing it if it's plain prose with no spaced paths.
- **`tool`** — a pointer to a proprietary or personal script/tool that lives elsewhere on disk,
  invoked on demand rather than auto-run. Using one means knowing it exists and how to call it.
- **`pattern`** — a `CLAUDE.md` convention or workflow habit. Unlike the other two kinds, a
  pattern is copied and adapted into this project's own `CLAUDE.md`, not referenced by pointer —
  see "Patterns are different" below.

This is a **pull-only** mechanism: nothing here scans or prompts automatically at `resume`.
Discovery only happens when this project's own session goes looking, because a resource relevant
to one project (SEO methodology, say) has no business surfacing in an unrelated one.

### Entering shared-resources context: an exact trigger, not a buried keyword

Working in a project normally means thinking only about that project. Using this mechanism means
deliberately switching to thinking across every project — a real gear-switch, not a minor aside,
so it needs an unmistakable trigger rather than something inferred from a keyword that happened to
appear somewhere in a sentence.

**The trigger is the exact phrase "shared resources," said as the substance of the message** —
the same bar the hub's own `checkpoint`/`resume` triggers already use: mentioned in passing
mid-conversation about something else, it does nothing; said as the message's lead content, it
fires. It can be followed immediately by the actual request in the same breath (*"shared
resources — save this as a pattern"*) or stand alone, in which case ask what's wanted (search,
browse, save, retrieve, forget).

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
     matches.
   - **Browse/list** — ask to see everything, e.g. *"shared resources — list everything"*, with no
     keyword. Useful when you don't remember what's there, or don't remember whether *this*
     project already adopted something. Always lists every entry, refinable by:
     - a count limit (most recent N);
     - an added-date filter (e.g. "added in the last month");
     - an **in-use indicator relative to this project** — for `reference`/`tool`, check whether
       this project's own `CLAUDE.md` already contains a pointer/`@import` to that entry's file,
       or a project-local `.claude\skills\<name>\SKILL.md` stub carrying that entry's adoption
       marker (see "Apply", below); for `pattern`, check for that entry's adoption marker (see
       "Patterns are different") since adapted prose won't verbatim-match its source.
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
        adoption marker, same convention as a `pattern`'s (see "Patterns are different"), so
        browse's in-use indicator and forget can find it later:
        ```
        <!-- shared_resources: <entry name> adopted YYYY-MM-DD -->
        ```
     4. **Show the draft — trigger description and stub body — to the user and confirm before
        writing anything.** Same checkpoint this file already requires for Saving, below.
     5. On confirmation, write the skill stub to this project's own
        `.claude\skills\<name>\SKILL.md` only — never into `toolkit\`. This content is
        private-only by construction (see "Two homes within Track 1" in
        `design\directive_economy.md`): no canonical stub source for it ever lives in the public
        toolkit repo, not even the trigger wording or the target path.
   - **`pattern`** — see "Patterns are different" below; never a plain pointer and not a skill
     stub either — a pattern is `CLAUDE.md` prose adapted by value, not content referenced by
     pointer or lazily loaded.

### Forgetting

**Forget** removes *this project's own adopted reference* — the `@import` line, pointer note,
project-local `.claude\skills\<name>\SKILL.md` stub, or adapted `pattern` section plus its
adoption marker — from this project. It never
touches the entry in `shared_resources\` itself, which stays available for this or any other
project to re-adopt later. Use it when a resource was adopted for a one-off task and is now just
`CLAUDE.md` bloat, or to reset this project's behavior back to before adoption. If Claude's advice
in some domain seems off, checking whether a relevant resource was ever adopted (via browse's
in-use indicator) — and forgetting it if it's stale — is a reasonable first move.

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
  (`templates\filing.md`'s `Type: proposal` ticket, or an ordinary bug ticket).
- **Neither is obvious** → ask before saving.

Then, before writing anything, state what's about to happen and get an explicit go-ahead: the
entry's name, its `kind`, a one-line description, and that it's about to be written into
`shared_resources\` plus a new `CATALOG.md` row. Only write after confirmation — this is the one
disk-writing action in the whole mechanism and the one carrying the classification call above, so
it gets its own explicit checkpoint even though entering the mode already got one.

When saving: create one new file in `shared_resources\` (kind `reference` or `tool`; for `pattern`
see below), then append one row to `shared_resources\CATALOG.md`.

### Patterns are different

A `pattern` entry is a `CLAUDE.md` convention or workflow habit — referenced **by value** (copied
and adapted), not by pointer, because each project's `CLAUDE.md` is its own tailored prose. This
needs its own pair of actions rather than the resource save/apply pair above:

- **Save a pattern** — triggered by something like *"shared resources — note this CLAUDE.md
  pattern"*. Copy the actual resulting `CLAUDE.md` section **verbatim** — the pattern's real text,
  not a git-diff-style before/after, and not a paraphrase — into a new `shared_resources\` file
  with `Kind: pattern` in `CATALOG.md`. Don't generalize or strip this project's specifics at save
  time: the saved entry is a faithful record of what actually worked here, and it's private
  hub-root storage, so carrying this project's own names/paths in it is fine. Generalizing now
  would just be a second lossy paraphrase on top of whatever the retrieving session does later — do
  it once, at retrieve time, from the real source. Same confirm-before-write step as above: name,
  kind, one-line description, destination — confirmed before the file is written.
- **Retrieve a pattern** — triggered by something like *"shared resources — get the checkpoint
  pattern from XYZ and apply it here"*. Runs the same search/browse/select flow above to find the
  right entry, then **adapts** the verbatim saved text into this project's own `CLAUDE.md` wording —
  this is the one point where generalization happens, informed by the actual concrete original
  rather than an earlier summary of it. Never pastes it verbatim. After adapting, add an adoption
  marker near the new section so browse's in-use indicator and forget can find it later, e.g.:
  ```
  <!-- shared_resources: <entry name> adopted YYYY-MM-DD -->
  ```

### Maintenance you might encounter

`shared_resources\` entries can be split, consolidated, renamed, or deleted over time as ordinary
upkeep. None of that should silently change this project's behavior. If an adopted entry's file no
longer resolves (a broken `@import`, a pointer to a file that's gone), that's a signal something
was restructured without a working stub left behind — treat it as worth a note back to a hub
session, not something to silently work around.

### Checking adopted references at resume

Only relevant if this project has actually adopted anything from `shared_resources\` — otherwise
skip this. At `resume`, run
`python <hub root>\toolkit\scripts\check_shared_resource_refs.py --project-root <this project's
root>` (the `<hub root>` prefix is whatever this file's own `@import` line resolves to, one level
above its `toolkit\`). It's a deterministic file-existence check, not an LLM judgment call — zero
tokens either way, and it catches 100% of the case it checks rather than relying on this session
noticing on its own. It covers two adopted forms: a literal `@import` line pointing into
`shared_resources\`, and a `~/...`-form path referenced inside a project-local
`.claude\skills\<name>\SKILL.md` stub (the Track-1 form "Apply" now produces — see above). Either
form gets a `[FAIL]` if its target no longer exists; report any `[FAIL]` to the user plainly (per
"Shared resources folder maintenance" — a broken reference must never fail silently). Out of scope
by design: a `tool`-kind entry adopted as free-text "pointer note" prose with no fixed shape (not a
literal `@import` line and not a backtick-quoted `~/...` path inside a skill stub) — that has no
fixed shape to check deterministically. Separately, a skill stub's **trigger description** going
stale relative to its source entry's current topic footprint is a different, non-existence
concern — see `design\directive_economy.md`'s "Drift mechanics" for why that's notify-only and not
covered by this existence check.
