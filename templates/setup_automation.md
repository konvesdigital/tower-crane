<!--
Home: templates\setup_automation.md  (part of the tower_crane pattern — floats on HEAD)
This is the hub-operator-only runbook for turning on Piece 3 (design\sync_automation.md): the
unattended ticket-processing agent. Read directly, never `@import`ed by any consumer project —
same category as templates\setup_machine.md.

How it's used: open this hub in Claude Code and say "read templates\setup_automation.md and
follow it." **The only assumed prerequisite is Claude Code itself** — the headless `claude` CLI's
own resolvability is checked live, never assumed. Ask-don't-assume throughout, same posture as
setup_machine.md: check first, confirm with the user, never silently guess a config value or a
scheduler setting.

Keep this file project/OS-agnostic. Edits here are canonical.
-->

# Turn on unattended ticket processing (automation)

You (the agent running in THIS hub) are walking the user through enabling Piece 3 — an hourly,
unattended pass that refreshes compliance guidance (`check_tower_crane.py --write-guidance`, zero
AI cost) and applies at most one fix-worthy `change_requests\` ticket per tick, directly — no PR,
no branch (local-only ticket processing, `design\local_first_reframe.md`; concrete repo targeting
in `design\automation_repo_targeting.md`). The tool fix itself commits locally to `toolkit\`'s own
history, unpushed; the ticket's round-trip log line commits and pushes to the outer (private)
repo. It never flips a ticket's `Status` directly, and it never pulls/merges `toolkit\`'s own
`origin` (that stays the separate, always-user-initiated `update` action) — it only surfaces a
one-line "update available" notice if one exists. Full design: `design\sync_automation.md`,
`design\automation_repo_targeting.md`.

This is entirely opt-in and off by default (`automation.enabled: false`). Nothing below runs on
its own until both this setup finishes AND that flag is flipped to `true`.

## Step 0 — Confirm prerequisites, live

1. `claude --version` — must resolve; this is the headless CLI Piece 3 shells out to.

If this fails, stop and tell the user plainly what's missing rather than proceeding with a guess.

## Step 1 — Walk `config.local.json`'s `automation` block

Confirm each field with the user rather than silently defaulting all of them — show the proposed
values and get a go-ahead, same as `setup_machine.md` Step 7:

- `enabled` — leave `false` until Step 2's scheduled task is actually wired up and tested; flip to
  `true` only at the very end.
- `mode` — `"apply_direct"` is the only value that exists; nothing to ask.
- `cadence_minutes` — `60` (hourly) is the locked default (design\sync_automation.md). Only change
  this if the user explicitly wants a different cadence AND has re-pointed the scheduled task in
  Step 2 to match.
- `max_tickets_per_tick` — `1` is the default; ask if the user expects enough ticket volume to want
  more (raising it adds no new git-isolation logic — each candidate is still processed one at a
  time in the same tick, sequentially).
- `max_attempts` — `3` is the default before a stuck ticket backs off and waits for a human.
- `target_remote` — leave empty (`""`) unless this machine's automation should watch a hub other
  than this clone's own `identity.git_remote` (rare — ask before filling this in).

## Step 2 — Schedule the hourly tick

`toolkit\scripts\run_automation.py` is the script the scheduler invokes — note the `toolkit\`
prefix; the outer hub root and the inner toolkit repo are two different folders post-split
(`design\local_first_reframe.md`'s outer/inner split), and this script physically lives in the
inner one. It no-ops harmlessly if `automation.enabled` is still `false`, so it's safe to wire up
the schedule before Step 3.

**Windows (Task Scheduler).** Confirm the hub's actual path and this machine's Python launcher
(from `config.local.json`) before proposing the command — don't hardcode the example path below.
```
schtasks /create /tn "TowerCraneAutomation" /sc HOURLY /mo 1 /st 00:05 ^
  /tr "cmd /c \"cd /d C:\Users\you\Documents\Claude\tower_crane && python toolkit\scripts\run_automation.py >> logs\automation.log 2>&1\""
```
`claude`'s stored auth generally needs an interactive user session, so Task Scheduler's default
**"Run only when user is logged on"** is the safe choice for v1 — automation pauses while the
machine is locked or logged out, which is an acceptable tradeoff, not something to solve here via a
stored password. If `schtasks /create` prompts for credentials or the task fails silently, fall
back to the GUI (Task Scheduler → Create Task): trigger = repeat every 1 hour indefinitely; action
= start `python.exe` with `toolkit\scripts\run_automation.py`'s full path as the argument and the
outer hub root as "Start in."

**Verify it actually runs** before relying on it: `schtasks /run /tn "TowerCraneAutomation"` and
confirm `logs\automation.log` shows a completed tick (this dir is already gitignored, matching the
existing per-machine `logs\` convention).

**cron / launchd (documented for later — no non-Windows consumer exists yet).**
```
0 * * * * python3 /home/you/Documents/Claude/tower_crane/toolkit/scripts/run_automation.py >> /home/you/Documents/Claude/tower_crane/logs/automation.log 2>&1
```
launchd: a `LaunchAgent` plist with `StartInterval` set to `3600`, `ProgramArguments` pointing at
the same script, matching the cron line's cadence and log redirection.

## Step 3 — Turn it on

Flip `automation.enabled` to `true` in `config.local.json`. Confirm with the user first — this is
the actual switch; everything before this step was inert setup.

## Step 4 — First live tick

Run `python toolkit\scripts\run_automation.py --dry-run` once by hand and confirm the mechanical
scan/bookkeeping output looks sane (no crash, sensible ticket categorization) before letting the
real scheduled task fire with `--dry-run` off. If there's a genuinely fix-worthy ticket queued, the
next real tick (scheduled, or run by hand without `--dry-run`) will apply it directly — confirm the
fix landed as a local commit in `toolkit\`'s own history (`git -C toolkit log -1`) and the ticket's
round-trip log line landed on the outer repo's `main` in the expected format.

## Step 5 — Finish

Confirm to the user: automation is scheduled, `config.local.json` reflects it, and the first tick's
behavior was verified. Point them at `design\sync_automation.md` /
`design\automation_repo_targeting.md` for the full round-trip vocabulary and remind them the fix
itself stays local to `toolkit\` (unpushed) until they separately run `"propose upstream"` if they
want to share it.
