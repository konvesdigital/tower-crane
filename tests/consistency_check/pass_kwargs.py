# Golden fixture: MUST produce [PASS] (exit 0).
# Regression test: calling a function with a REQUIRED (non-default) param passed by keyword must
# NOT be flagged as an arg-count mismatch. Before the fix, the checker only counted node.args
# (positional), so any call using `name=value` for a required param was wrongly flagged as
# missing that arg - found live 2026-08-12 while building the reconnect-after-disconnect fix
# (design\disconnect.md).


def build(has_git, remote, needs_overview):
    return has_git, remote, needs_overview


build(True, None, False)
build(True, None, needs_overview=False)
build(True, remote=None, needs_overview=False)
