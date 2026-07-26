# Golden fixture: MUST produce [PASS] (exit 0).
# Regression test for three string-key fuzzy-match false positives found + fixed 2026-07-23
# (see project_progress.md Work Log): a CLI-flag literal ('--consumer') vs the same bare word
# used as an unrelated field name ('consumer'); a dunder sentinel ('__main__') vs an unrelated
# bare word ('main'); and an f-string's own literal text fragment ('Release ' in
# f"Release {tag}") vs an unrelated CLI subcommand token ('release'). None of these are the same
# key spelled inconsistently - they're semantically unrelated strings that only collide after the
# checker's normalisation (lowercase, strip '_'/'-') is applied.

import argparse


def build_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('--consumer', default=None)
    return parser


def describe(consumer):
    return f"consumer: {consumer}"


def branch_name():
    return 'main'


def run_subprocess_stub(cmd):
    return list(cmd)


def tag_release(tag):
    run_subprocess_stub(['gh', 'release', 'view', tag])
    return f"Release {tag}"


if __name__ == "__main__":
    build_parser()
    describe("acme")
    branch_name()
    tag_release("v1.0.0")
