# Golden fixture: MUST produce [FAIL] (exit 2) with a finding naming 'user_id'.
# Guards against the 2026-07-23 false-positive fixes over-correcting: this is a genuine drift
# bug - the same conceptual dict key spelled two different ways ('user_id' vs 'user-id'), which
# is exactly what this check exists to catch. Neither form is a CLI flag, a dunder sentinel, or
# an f-string literal fragment, so none of that day's exclusions should apply here.


def load(record):
    return record['user_id']


def save(record, value):
    record['user-id'] = value
