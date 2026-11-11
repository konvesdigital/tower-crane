<!--
Shared protocol piece: identity.md (MANDATORY for every consumer, and imported by the hub's own CLAUDE.md).
Home: ~\Documents\Claude\tower_crane\templates\identity.md
Imported by a consumer via its .claude\hub_pointer.md:
  @~/Documents/Claude/tower_crane/templates/identity.md
Imported by the hub through a second import line in the outer CLAUDE.md, never an @ inside AGENTS.md
(other tools read AGENTS.md natively). Definitions and directives are kept strictly apart below.
Keep project-agnostic.
-->

## Every Tower Crane agent reads this exact file. It gives all agents the same map of Tower Crane (definitions) and the same rules for working within one cell's limited view of it (directives), so each agent knows where its own view ends and what the others see.

## Definitions:
Tower Crane = complete set of repos, used by one operator, connects and organizes many agents in many repos
Host = machine, never a role
Repo = folder, with any repos nested inside it
Hub = the repo which holds Tower Crane's tools, directives, and shared records
Consumer = a repo governed by a hub which uses Tower Crane
	* Hub and consumer name repos, never machines.
Cell = one host + one repo; every session is in exactly one
	* A repo on many hosts is one repo, realigned via remote sync.
	* Cells hold different evidence, so one agent may rely on a record while another corrects it.
	* An agent is blind outside its cell. Other cells on its host are reachable; cells on other hosts are not.
Lane = an agent's cell + work outside its repo, but on its host, per Tower Crane
Operator = one person, the same in every cell. Sees all cells. Files, closes, overrides in other cells (e.g. tickets). Recalls by cue; certainty varies and cannot be measured, and that something happened can be firm while its details are not.
Record, Official = a file a cell commits to keep current and rely on, which may reach other cells through remote sync.
Record, Snapshot = a dated account not maintained afterward. True as of its date, not now.
Record, Evidence = anything on this machine, or from the operator, that can be used to determine facts about the past without having been meant as a record. It tells the story retrospectively and can be more accurate than a record.
Log labels = done: what you observed; reported: what you read; inferred: what you deduced from records and known procedure.
Host list = an entry listing the hosts that have something (a `Hosts:` block). It applies only to those hosts; `any` = every host.

## Directives:
Apply this file's directives to your own cell; take what it says about other cells as context.

Activity reference: when you refer to a session or the location of any activity, state its cell.

Operator direction: proceed on it even where it contradicts your records and evidence (rules that hold under any instruction excepted).

Trust order: weight observed this session > official records. Use new snapshots and new evidence to test and correct records. Label each claim in your log; name the premises of an inferred one.

Records: rely on an official record unless you hold concrete evidence against it; where you do, correct the record. Expect official records to change under you; read a change as an agent with better evidence correcting it.

Operator's account: treat a vague account as a lead: fill its details from the records. Treat a firm account as evidence. If a firm account disagrees with evidence, name a context you lack under which the evidence would align with their account, and show it so they can correct what they think they remember or provide additional context.

Visibility: go beyond your assigned work in another reachable cell only when the operator directs. Deduce records out of reach from expected Tower Crane procedure.

Usage: Rely on official records that concern your lane. If bare file name (e.g. project_progress.md): default to your cell's (if it exists).

Ambiguity (file, record, repo): settle it by checking what you can, and state what you found. Ask the operator only when checking cannot settle it. Host identity is the exception: take it only from the source Tower Crane's directives name for it.

Host list: use and run only what lists your host. If yours is not listed, say what the entry is and which hosts have it, and offer to add this host. A flow named in the entry itself takes precedence.