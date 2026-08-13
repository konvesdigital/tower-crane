# Troubleshooting a broken project connection

Read this when `connect project` (`new_consumer.py`) or `disconnect project`
(`disconnect_consumer.py`) hits a fatal error and the obvious next step looks like either
abandoning the operation or forcing an overwrite that could destroy real project content. This is
**not** a deterministic fix — connections can break for more reasons than any script can
enumerate. It's a short list of the probable causes seen so far and the easy things to try first,
meant to put Claude and the user on a path to a real fix faster, not to guarantee one. If nothing
here fits, fall back to describing the actual error and reasoning about it directly with the user
— don't force a match to one of these shapes just because it's the closest.

**Before trying anything below:** never run `--force` (on `new_consumer.py`) as a first move. It
fully overwrites `CLAUDE.md` from the blank template, destroying any real project overview or
hand-added content. Every scenario below has a non-destructive path — reach for `--force` only
after those are ruled out, and only with the user's explicit go-ahead, per the standing
"actions with care" guidance (hard-to-reverse action, confirm first).

## Quick triage

| Error you see | Likely cause | Try first |
|---|---|---|
| `new_consumer.py`: "CLAUDE.md already exists ... doesn't match a recognized shape" | Registry drift: the file already carries real Tower Crane content (a `## Tower Crane In Use` heading or a protocol-piece `@import` line), but there's no `consumers\<slug>.md` entry to explain it. (A `CLAUDE.md` with genuinely *no* Tower Crane content at all, or the `## Tower Crane (disconnected)` marker, is no longer an error — `new_consumer.py` handles both automatically now.) | See "Registry entry missing but CLAUDE.md still looks live" below |
| `disconnect_consumer.py`: "No registry entry for '\<slug>' at \<path>" | Registry entry (`consumers\<slug>.md`) is missing entirely, but the project's `CLAUDE.md` may still show live Tower Crane content | See "Registry entry missing but CLAUDE.md still looks live" below |
| `disconnect_consumer.py`: "'\<slug>' has no hosts.\<host> entry on this machine" | The registry file exists (other hosts may still be listed) but *this machine's* `hosts.<host_id>` block was stripped | Same remedy as above, narrower scope — restore/add just this host's block |
| `disconnect_consumer.py`: "\<registry_path> isn't parseable" | The registry entry's yaml block is corrupted (bad hand-edit, merge conflict markers left in, etc.) | Fix the yaml by hand, or restore the whole file from git history (same technique as below) |
| `new_consumer.py`: "git clone of '\<remote>' into \<path> failed" | The registry's recorded `remote:` is stale, private without this machine's credentials, or deleted | Confirm the remote URL still resolves (`git ls-remote <url>`); if not, ask the user for the current one, or fall back to `--no-clone` + manual copy |

## CLAUDE.md exists and nothing recognizes it — this is registry drift

`new_consumer.py` auto-handles three shapes of an existing `CLAUDE.md`, no `--force` needed for
any of them: no registry entry *and* no Tower Crane content at all (adoption — register.md's old
target case, subsumed 2026-08-12), no registry entry *and* the `## Tower Crane (disconnected)`
marker (reconnect), and a registered consumer connecting another host (host-merge). Anything else
— live `## Tower Crane In Use` / protocol-piece `@import` lines already present, but no
`consumers\<slug>.md` entry to explain them — is registry drift, not a missing-conversion problem,
and falls through to the `--force` guard rather than being auto-resolved: the local content is
probably already correct, it's the registry that's out of sync, and guessing wrong here risks
silently adopting content from an unrelated project. See the next section.

## Registry entry missing but CLAUDE.md still looks live

This can't happen through normal use of the Tower Crane tools — `new_consumer.py` and
`disconnect_consumer.py` always write local content and the registry entry together, in the same
run. Reaching this state means something bypassed them with a direct git/file operation on
`consumers\<slug>.md`:
- The registry file (or just this host's `hosts.<host_id>` block within it) was deleted by hand,
  outside `disconnect project`.
- A `git merge`/rebase conflict on `consumers\<slug>.md` resolved by dropping the entry.
- A `git reset --hard` or `checkout <old-sha> -- consumers/` reverted past the registration commit,
  and that state got pushed.

**Remedy — restore or hand-author the registry entry; this alone unlocks both commands:**
1. **Check git history first**: `git log -- consumers/<slug>.md` in the hub root. If the deleting
   commit is still reachable (nothing force-pushed over it), restore the exact original entry:
   `git show <sha>:consumers/<slug>.md > consumers/<slug>.md`.
2. **If history doesn't have it** (the project was hand-edited into Tower Crane shape without ever
   going through `new_consumer.py`/`register.md`): hand-author a minimal valid entry. Copy the
   shape from an existing `consumers\*.md` file. Fill it in by inventorying the actual project —
   read `CLAUDE.md`'s `@import` lines for what belongs under `imported:`, read
   `.claude\settings.json`'s hooks for what belongs under `opted_in:`. This is the same inventory
   step `register.md`'s Step 1 already teaches, just run directly by the hub session instead of
   through the courier/ticket path.

Once a registry entry with the right `hosts.<host_id>` block exists:
- `disconnect project` now runs normally.
- `connect project` now routes into the existing, already-safe host-merge branch (patches only
  stale `@import` lines in place) — since the content is probably already correct, this will most
  likely just report "already current" and do nothing further.

**Verify the fix**: run `scripts\check_tower_crane.py`. Pass B compares the registry's declared
`opted_in`/`imported` against the project's actual `settings.json`/`CLAUDE.md` — any mismatch
between what was hand-authored and what's really there surfaces as a deviation finding, which
serves as a free correctness check on the repair.

## Wired in (2026-08-12)

`new_consumer.py`'s and `disconnect_consumer.py`'s fatal-error messages now name this file
directly. Not yet built: a `"fix connection"` trigger that reads it proactively before an error is
even hit.
