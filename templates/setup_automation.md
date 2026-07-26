<!--
Home: templates\setup_automation.md  (part of the tower_crane pattern — floats on HEAD)
This is the hub-operator-only runbook for turning on Piece 3 (design\sync_automation.md): the
unattended ticket-processing agent. Read directly, never `@import`ed by any consumer project —
same category as templates\setup_machine.md / bootstrap_hub.md.

How it's used: open this hub in Claude Code and say "read templates\setup_automation.md and
follow it." **The only assumed prerequisite is Claude Code itself** — gh, and the headless
`claude` CLI's own auth, are checked live, never assumed. Ask-don't-assume throughout, same
posture as setup_machine.md: check first, confirm with the user, never silently guess a config
value or a scheduler setting.

Keep this file project/OS-agnostic. Edits here are canonical.
-->

# Turn on unattended ticket processing (automation)

You (the agent running in THIS hub) are walking the user through enabling Piece 3 — an hourly,
unattended pass that pulls the hub clone, refreshes compliance guidance
(`check_tower_crane.py --write-guidance`, zero AI cost), and proposes a PR for at most one
fix-worthy `change_requests\` ticket per tick. It never merges its own PR and never flips a
ticket's `Status`. Full design: `design\sync_automation.md`.

This is entirely opt-in and off by default (`automation.enabled: false`). Nothing below runs on
its own until both this setup finishes AND that flag is flipped to `true`.

## Step 0 — Confirm prerequisites, live

1. `gh --version` — must succeed; Piece 3 opens PRs via `gh pr create`.
2. `gh auth status` — must show an authenticated account with access to this hub's GitHub remote.
   If not, stop and tell the user to run `gh auth login` first.
3. `claude --version` — must resolve; this is the headless CLI Piece 3 shells out to.

If any check fails, stop and tell the user plainly what's missing rather than proceeding with a
guess.

## Step 1 — Walk `config.local.json`'s `automation` block

Confirm each field with the user rather than silently defaulting all of them — show the proposed
values and get a go-ahead, same as `setup_machine.md` Step 7:

- `enabled` — leave `false` until Step 3's scheduled task is actually wired up and tested; flip to
  `true` only at the very end.
- `mode` — `"propose_only"` is the only value that exists; nothing to ask.
- `cadence_minutes` — `60` (hourly) is the locked default (design\sync_automation.md). Only change
  this if the user explicitly wants a different cadence AND has re-pointed the scheduled task in
  Step 3 to match.
- `max_tickets_per_tick` — `1` is the default; ask if the user expects enough ticket volume to want
  more (raising it adds no new git-isolation logic — each candidate is still processed one at a
  time in the same tick, sequentially).
- `max_attempts` — `3` is the default before a stuck ticket backs off and waits for a human.
- `target_remote` — leave empty (`""`) unless this machine's automation should watch a hub other
  than this clone's own `identity.git_remote` (rare — ask before filling this in).

## Step 2 — Branch protection (recommended, not scripted)

Once automation opens PRs unattended, requiring review before merge on this hub's GitHub repo
matters more than it did for a purely human-driven workflow — a PR nobody reviews just sits there
looking merged-adjacent. This is a one-time GitHub repo setting the user configures directly
(Settings → Branches → branch protection rule for `main`, "Require a pull request before
merging"); nothing here scripts it.

## Step 3 — Schedule the hourly tick

`scripts\run_automation.py` is the script the scheduler invokes. It no-ops harmlessly if
`automation.enabled` is still `false`, so it's safe to wire up the schedule before Step 4.

**Windows (Task Scheduler).** Confirm the hub's actual path and this machine's Python launcher
(from `config.local.json`) before proposing the command — don't hardcode the example path below.
```
schtasks /create /tn "TowerCraneAutomation" /sc HOURLY /mo 1 /st 00:05 ^
  /tr "cmd /c \"cd /d C:\Users\you\Documents\Claude\tower_crane && python scripts\run_automation.py >> logs\automation.log 2>&1\""
```
`gh`'s and `claude`'s stored auth generally need an interactive user session, so Task Scheduler's
default **"Run only when user is logged on"** is the safe choice for v1 — automation pauses while
the machine is locked or logged out, which is an acceptable tradeoff, not something to solve here
via a stored password. If `schtasks /create` prompts for credentials or the task fails silently,
fall back to the GUI (Task Scheduler → Create Task): trigger = repeat every 1 hour indefinitely;
action = start `python.exe` with `scripts\run_automation.py`'s full path as the argument and the
hub root as "Start in."

**Verify it actually runs** before relying on it: `schtasks /run /tn "TowerCraneAutomation"` and
confirm `logs\automation.log` shows a completed tick (this dir is already gitignored, matching the
existing per-machine `logs\` convention).

**cron / launchd (documented for later — no non-Windows consumer exists yet).**
```
0 * * * * python3 /home/you/Documents/Claude/tower_crane/scripts/run_automation.py >> /home/you/Documents/Claude/tower_crane/logs/automation.log 2>&1
```
launchd: a `LaunchAgent` plist with `StartInterval` set to `3600`, `ProgramArguments` pointing at
the same script, matching the cron line's cadence and log redirection.

## Step 4 — Turn it on

Flip `automation.enabled` to `true` in `config.local.json`. Confirm with the user first — this is
the actual switch; everything before this step was inert setup.

## Step 5 — First live tick

Run `scripts\run_automation.py --dry-run` once by hand and confirm the mechanical scan/bookkeeping
output looks sane (no crash, sensible ticket categorization) before letting the real scheduled
task fire with `--dry-run` off. If there's a genuinely fix-worthy ticket queued, the next real tick
(scheduled, or run by hand without `--dry-run`) will open its first PR — watch for it on GitHub and
confirm the round-trip log line lands on `main` in the expected format.

## Step 6 — Finish

Confirm to the user: automation is scheduled, `config.local.json` reflects it, and the first tick's
behavior was verified. Point them at `design\sync_automation.md` for the full round-trip vocabulary
(`fix proposed` → `merged` → `consumer-verified`) and remind them a PR still needs a human to
actually merge it — that gate never goes away.
