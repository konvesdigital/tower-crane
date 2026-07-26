# Golden fixture: MUST produce [FAIL] (exit 2) with a finding naming 'report'.
# Guards against the defaults fix over-correcting: omitting a REQUIRED (non-default)
# positional arg must still be caught.


def report(level, message, indent="  "):
    return f"{indent}[{level}] {message}"


report("WARN")  # missing required `message`
