# Golden fixture: MUST produce [PASS] (exit 0).
# Exercises every locally-bound-name case the checker previously flagged as
# undefined (see change_requests\2026-07-17_consistency-check_local-binding-
# false-positives.md): function params (normal / *args / kw-only / **kwargs),
# lambda params, comprehension targets, and `except ... as`.


def add(a, b):
    return a + b


def scale(*values, factor=1, **opts):
    # `values` (*args), `factor` (kw-only), and `v` (comprehension target)
    # were all reported as undefined before the fix.
    return [v * factor for v in values]


double = lambda n: n * 2  # noqa: E731  -- lambda param `n`


def risky():
    try:
        return add(1, 2)
    except Exception as exc:  # `exc` is a locally-bound name
        return str(exc)
