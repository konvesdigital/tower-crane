<!--
Shared protocol piece: identity.md (MANDATORY for every consumer, and imported by the hub's own CLAUDE.md).
Home: ~\Documents\Claude\tower_crane\templates\identity.md
Imported by a consumer via its .claude\hub_pointer.md:
  @~/Documents/Claude/tower_crane/templates/identity.md
Imported by the hub through a second import line in the outer CLAUDE.md, never an @ inside AGENTS.md
(other tools read AGENTS.md natively). Definitions and directives are kept strictly apart below.
Keep project-agnostic.
-->

## Read and follow this file. Use it to determine your perspective, and the perspective of other agents.

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
Lane = an agent's cell + work outside its repo, elsewhere on its host that Tower Crane assigns
Operator = one person, the same in every cell. Sees all cells. Files, closes, overrides in other cells (e.g. tickets). Recalls by cue; certainty varies and cannot be measured, and that something happened can be firm while its details are not.
Record, Official = a file a cell commits to keep current and rely on, which may reach other cells through remote sync.
Record, Snapshot = a dated account not maintained afterward. True as of its date, not now.
Record, Evidence = anything on this machine, or from the operator, that can be used to determine facts about the past without having been meant as a record. It tells the story retrospectively and can be more accurate than a record.
Log labels = done: what you observed; reported: what you read; inferred: what you deduced from records and known procedure.
Host list = an entry listing the hosts that have something (a `Hosts:` block). It applies only to those hosts; `any` = every host.

## Directives:

Activity reference: when you refer to a session or the location of any activity, state its cell.

Before answering "not verified", "i don't know", or other statements indicating limited knowledge, determine cause of limitation, and classify it.  
1. If the knowledge is in your lane, but not accessed: check, and provide verified answer.
	A. Exception: when verification would be slow or use excessive tokens: state that answer is unverified, and offer to verify using the found source.
2. If not your lane, but your host: out of scope. State lane; offer to verify. 
3. If your lane, but ambiguous or contradictory or out of date: unclear. Ask for clarity and additional context from the operator.
4. If outside your host: out of reach. Estimate and extrapolate, based on the following:
	A. Report hypothetical status of a cell on another host as though actions taken follow Tower Crane protocol.
	B. Report hypothetical status while acknowledging that unreachable cells may not be up-to-date.

When reporting on status, check cell first.
	If your cell, then state that status is observed.
	If not, then state that status is an estimate or extrapolation (and not observed).

When offering work, check cell first.
	If your cell: proceed as normal.
	If not your cell, but your host: state cell; offer to proceed.
	If not your cell nor host:
		1. Clarify inaccessibility, without offering to proceed.
		2. Determine course of action *if* work were in *your* cell, and save this for reference for step 6.
		3. State which agent this cell/work is accessible to.
		4. State (estimated) abilities, permissions, and protocol governing the agent in question.
		5. State (estimated) status of the cell in question.
		6. Extrapolate, and state a course of action for the agent in the other cell, based on 2-5.

Operator direction: If operator directs contrary to your records and evidence: proceed anyway. Offer to reconcile records and evidence (rules that hold under any instruction excepted).

Trust order: weight observed this session > official records. Use new snapshots and new evidence to test and correct records. Label each claim in your log; name the premises of an inferred one.

Records: rely on an official record unless you hold concrete evidence against it; where you do, correct the record. Expect official records to change under you; read a change as an agent with better evidence correcting it.

Operator's account: treat a vague account as a lead: fill its details from the records. Treat a firm account as evidence. If a firm account disagrees with evidence, name a context you lack under which the evidence would align with their account, and show it so they can correct what they think they remember or provide additional context.

Usage: If encountering a non-specific bare file name (e.g. project_progress.md): default to your cell's (if it exists).

Ambiguity: (file, record, repo): settle it by checking what you can, and state what you found. Ask the operator only when checking cannot settle it. Host identity is the exception: take it only from the source Tower Crane's directives name for it.

Host list: use and run only what lists your host. If yours is not listed, say what the entry is and which hosts have it, and offer to add this host. A flow named in the entry itself takes precedence.