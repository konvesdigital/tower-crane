# Changelog

All notable changes to Tower Crane are documented here, newest version first. Each version below
also has a matching GitHub Release (see the "Releases" link on this repo's page) with a
downloadable zip of that version's files — if a newer version doesn't work for you, you can always
get an older one from there.

## [1.0.0] - 2026-07-22
**First version for public release: test**

### Added
- **Consumer platform** — reusable hooks, subagents, and scripts that any project can opt into via
  `@import`. A change made here, once ratified, propagates to every consuming project.
- **`consistency_check` hook** (pure Python) — catches undefined names, wrong arg counts, and
  string-key mistakes before they ship.
- **Scaffolder + health checker** (`new_consumer.py`, `check_tower_crane.py`) — onboard a new
  consumer project and validate the whole fleet stays in sync.
- **Portability foundation** — config-driven install (no hardcoded machine paths), cross-platform
  runtime, and `relocate.py` so the platform can run across your own machines (Federate).
- **This distribution mechanism** — a generator that produces a clean, independent copy of the hub
  and publishes it here as a versioned release.
