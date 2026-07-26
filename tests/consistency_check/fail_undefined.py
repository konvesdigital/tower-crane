# Golden fixture: MUST produce [FAIL] (exit 2) with a finding naming `y`.
# Guards against the fix over-correcting: `x` is now a bound param and must NOT
# be flagged, but `y` is genuinely undefined and must still be caught.


def compute(x):
    return x + y  # `y` is never defined or imported anywhere in this file
