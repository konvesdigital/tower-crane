# Golden fixture: MUST produce [PASS] (exit 0).
# Regression test: calling a function while omitting a defaulted trailing positional
# arg must NOT be flagged as an arg-count mismatch. Before the fix, the checker
# compared against the function's TOTAL positional-arg count regardless of defaults,
# so any call that relied on a default was wrongly flagged.


def report(level, message, indent="  "):
    return f"{indent}[{level}] {message}"


report("WARN", "no indent supplied - should use the default")
report("WARN", "indent supplied explicitly", "    ")
