# Golden fixture: MUST produce [PASS] (exit 0).
# Regression test for tuple/list/starred-unpacking targets: `for-loop` and plain-
# assignment unpacking (e.g. `for k, v in d.items():`, `a, b = f()`, `head, *rest = ...`)
# and `with ... as (a, b):` were all wrongly flagged as undefined before the fix - the
# checker only recognized a single-Name target, never a Tuple/List/Starred one, even
# though names_in_target() already existed and handled this (it was just wired into
# comprehension targets only). See project_progress.md 2026-07-23 Work Log entry.


def other():
    return object(), object()


def summarize(d):
    total = 0
    last_key = None
    for key, values in d.items():
        for v in values:
            total += v
        last_key = key
    return total, last_key


first, second = (1, 2)
head, *rest = [1, 2, 3]

with other() as (a, b):
    used = (a, b)
