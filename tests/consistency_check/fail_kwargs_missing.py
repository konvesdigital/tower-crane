# Golden fixture: MUST produce [FAIL] (exit 2) with a finding naming 'build'.
# Guards against the keyword-arg fix over-correcting: a call still missing a required arg -
# whether passed positionally or by keyword - must still be caught.


def build(has_git, remote, needs_overview):
    return has_git, remote, needs_overview


build(True, remote=None)  # missing required `needs_overview`
