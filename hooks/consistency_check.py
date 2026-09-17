#!/usr/bin/env python3
# consistency_check.py
# SHARED TOOL - lives in tower_crane\hooks\, referenced by any project that opts in.
#
# Triggered by Claude Code PostToolUse hook after any .py file write or edit.
# Runs Python AST-based static analysis on the target file.
# Output: terminal stdout + timestamped log file + logs\latest_check.txt; on FAIL, also stderr.
#
# To use in a project: add a PostToolUse hook in that project's .claude\settings.json pointing at
# this file (see MENU.md / templates\optins\consistency_check.json for the canonical snippet), then
# list it in that project's CLAUDE.md under "Tower Crane In Use".
#
# Invocation:
#   <python_launcher> consistency_check.py            # hook mode: reads PostToolUse JSON on stdin
#   <python_launcher> consistency_check.py <file.py>  # direct/test mode: target passed as argv[1]
#
# Exit codes: 0 = PASS (skipped if no target, not a .py file, or CLAUDE_PROJECT_DIR unset).
# 2 = FAIL (certain failure(s) found), with the report also written to stderr - Claude Code only
# surfaces PostToolUse hook output to the calling agent on exit code 2, never on 1. Never exits 1.

import ast
import sys
import os
import io
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# Force UTF-8 stdout - Windows console defaults to cp1252 which breaks non-ASCII
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def emit(line, log_fh, latest_fh, also_stderr=False):
    """Print to terminal and write to both log files. also_stderr additionally prints to stderr."""
    print(line)
    log_fh.write(line + "\n")
    latest_fh.write(line + "\n")
    if also_stderr:
        print(line, file=sys.stderr)


def names_in_target(target):
    """Yield bound names from an assignment / for / comprehension target.
    Handles plain names plus tuple/list unpacking and starred targets, e.g.
    `a`, `(a, b)`, `[a, b]`, `a, *rest`."""
    if isinstance(target, ast.Name):
        yield target.id
    elif isinstance(target, (ast.Tuple, ast.List)):
        for elt in target.elts:
            yield from names_in_target(elt)
    elif isinstance(target, ast.Starred):
        yield from names_in_target(target.value)


def check_file(path):
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()

    findings = []

    # -- Parse ----------------------------------------------------------------
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError as e:
        findings.append({
            "severity": "CERTAIN_FAILURE",
            "lines": str(e.lineno),
            "issue": f"SyntaxError - file cannot be parsed: {e.msg}",
            "example": str(e)
        })
        return findings

    lines = source.splitlines()

    # -- Collect definitions ---------------------------------------------------
    assigned_names = {}       # name -> first line assigned
    imported_names = {}       # name -> line
    defined_functions = {}    # name -> (lineno, arg_count, arg_names)

    for node in ast.walk(tree):
        # Assignments (incl. tuple/list/starred unpacking, e.g. `a, b = f()`)
        if isinstance(node, ast.Assign):
            for target in node.targets:
                for nm in names_in_target(target):
                    if nm not in assigned_names:
                        assigned_names[nm] = node.lineno
        # Augmented assignments (+=, etc.)
        if isinstance(node, ast.AugAssign):
            if isinstance(node.target, ast.Name):
                if node.target.id not in assigned_names:
                    assigned_names[node.target.id] = node.lineno
        # Annotated assignments (x: int = ...)
        if isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                if node.target.id not in assigned_names:
                    assigned_names[node.target.id] = node.lineno
        # Imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name.split(".")[0]
                imported_names[name] = node.lineno
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name
                imported_names[name] = node.lineno
        # Function definitions
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = node.args
            positional = [a.arg for a in args.args]
            # args.defaults covers the TRAILING N positional args - a call may omit any of
            # them and still be valid, so the call-count check below compares against a
            # [min_args, arg_count] range rather than an exact count.
            defined_functions[node.name] = {
                "lineno": node.lineno,
                "arg_count": len(positional),
                "min_args": len(positional) - len(args.defaults),
                "arg_names": positional,
                "has_varargs": args.vararg is not None,
                "has_varkw": args.kwarg is not None,
            }
            # Function name is also a defined name
            assigned_names[node.name] = node.lineno
        # Class definitions
        if isinstance(node, ast.ClassDef):
            assigned_names[node.name] = node.lineno
        # For loop variables (incl. tuple/list/starred unpacking, e.g. `for k, v in d.items()`)
        if isinstance(node, (ast.For, ast.AsyncFor)):
            for nm in names_in_target(node.target):
                if nm not in assigned_names:
                    assigned_names[nm] = node.lineno
        # With statements (incl. `with f() as (a, b):`)
        if isinstance(node, ast.With):
            for item in node.items:
                if item.optional_vars:
                    for nm in names_in_target(item.optional_vars):
                        if nm not in assigned_names:
                            assigned_names[nm] = node.lineno
        # Locally-bound names (fix for local-binding false positives):
        # function / lambda parameters, comprehension targets, and `except ... as`.
        # These are Load-referenced inside their scope but were never collected,
        # so the flat undefined-name check wrongly flagged them. This does NOT make
        # the check scope-aware (still one flat namespace) - it only stops valid
        # code from failing.
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            a = node.args
            for arg in (a.posonlyargs + a.args + a.kwonlyargs):
                if arg.arg not in assigned_names:
                    assigned_names[arg.arg] = node.lineno
            if a.vararg and a.vararg.arg not in assigned_names:
                assigned_names[a.vararg.arg] = node.lineno
            if a.kwarg and a.kwarg.arg not in assigned_names:
                assigned_names[a.kwarg.arg] = node.lineno
        # Comprehension targets, e.g. `x` (and unpacked forms) in [x for x in items]
        if isinstance(node, ast.comprehension):
            for nm in names_in_target(node.target):
                if nm not in assigned_names:
                    assigned_names[nm] = getattr(node.target, "lineno", node.target.col_offset)
        # Exception binding, e.g. `e` in `except Exception as e`
        if isinstance(node, ast.ExceptHandler):
            if node.name and node.name not in assigned_names:
                assigned_names[node.name] = node.lineno

    all_defined = {**assigned_names, **imported_names}
    builtins = set(dir(__builtins__)) if isinstance(__builtins__, dict) else set(dir(__builtins__))
    builtins.update({"__name__", "__file__", "__doc__", "__package__",
                     "__spec__", "__loader__", "__builtins__", "True", "False", "None"})

    # -- Check: undefined name references --------------------------------------
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            name = node.id
            if name not in all_defined and name not in builtins:
                findings.append({
                    "severity": "CERTAIN_FAILURE",
                    "lines": str(node.lineno),
                    "issue": f"Name '{name}' is used but never defined or imported in this file",
                    "example": f"Referenced at line {node.lineno}: `{lines[node.lineno-1].strip()}`"
                })

    # -- Check: function call argument count mismatches -------------------------
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                fname = node.func.id
                if fname in defined_functions:
                    defn = defined_functions[fname]
                    # A call unpacking *args/**kwargs, or a def accepting *args/**kwargs, is too
                    # dynamic for this simple count to reason about - skip rather than risk a
                    # false positive.
                    has_star_splat = any(isinstance(a, ast.Starred) for a in node.args)
                    has_kwarg_splat = any(kw.arg is None for kw in node.keywords)
                    if has_star_splat or has_kwarg_splat or defn["has_varargs"] or defn["has_varkw"]:
                        continue
                    # A keyword arg matching a named parameter counts toward coverage same as a
                    # positional one - a required param passed by keyword (e.g. `f(1, 2, c=3)`)
                    # is a valid call, not a missing-arg mismatch. A keyword name not among the
                    # def's positional-or-keyword params (kwonly-after-*, or a typo) means this
                    # simple model doesn't understand the call - skip rather than guess.
                    keyword_names = [kw.arg for kw in node.keywords]
                    if any(k not in defn["arg_names"] for k in keyword_names):
                        continue
                    n_passed = len(node.args) + len(keyword_names)
                    n_expected = defn["arg_count"]
                    n_min = defn["min_args"]
                    arity_desc = str(n_expected) if n_min == n_expected else f"{n_min}-{n_expected}"
                    # Skip 'self' for methods defined at module level (rare but possible)
                    if n_passed < n_min or n_passed > n_expected:
                        findings.append({
                            "severity": "CERTAIN_FAILURE",
                            "lines": str(node.lineno),
                            "issue": (
                                f"Function '{fname}' defined with {arity_desc} positional arg(s) "
                                f"({', '.join(defn['arg_names'])}), called with {n_passed} arg(s)"
                            ),
                            "example": f"Call at line {node.lineno}: `{lines[node.lineno-1].strip()}`"
                        })

    # -- Check: string key consistency (column names / dict keys) --------------
    # Normalises separators to flag 'user_id' / 'user-id' / 'userid' as the same key. Excludes
    # CLI-flag literals ('--zip') and dunder sentinels ('__main__') before the fuzzy-match set,
    # since blind normalisation would otherwise collide either against an unrelated bare word.
    #
    # A Constant that is a literal segment of an f-string (ast.JoinedStr) is also excluded - it's
    # prose/template text, not a key - while a Constant used as a subscript key inside an
    # f-string's `{...}` expression is a different AST node and is still checked normally.
    fstring_fragment_ids = {
        id(v) for node in ast.walk(tree) if isinstance(node, ast.JoinedStr)
        for v in node.values if isinstance(v, ast.Constant)
    }

    string_literals = defaultdict(list)
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if id(node) in fstring_fragment_ids:
                continue
            val = node.value.strip()
            if not val or " " in val or len(val) <= 2:
                continue
            if val.startswith("-"):
                continue  # CLI-flag literal, e.g. '--zip' - not a key/column name
            if val.startswith("__") and val.endswith("__"):
                continue  # dunder sentinel, e.g. '__main__' - not a key/column name
            # Normalise: lowercase, remove underscores/hyphens for fuzzy match
            normalised = val.lower().replace("_", "").replace("-", "")
            string_literals[normalised].append((val, node.lineno))

    for normalised, occurrences in string_literals.items():
        unique_forms = list({v for v, _ in occurrences})
        if len(unique_forms) > 1:
            lines_list = sorted({ln for _, ln in occurrences})
            findings.append({
                "severity": "CERTAIN_FAILURE",
                "lines": ", ".join(str(l) for l in lines_list),
                "issue": f"String key/column used under {len(unique_forms)} different spellings: {unique_forms}",
                "example": f"Forms found: {unique_forms} - likely the same column referenced inconsistently"
            })

    return findings


def resolve_target():
    """Direct/test mode: target as argv[1]. Hook mode: read PostToolUse JSON on stdin and pull
    tool_input.file_path. Returns (path, is_hook_mode); path is None when neither yields one (the
    caller then no-ops). is_hook_mode distinguishes an explicit, deliberate invocation (a human or
    check_tower_crane.py's golden-suite runner passing a fixture on purpose - always run it, FAIL
    included) from an automatic live PostToolUse trigger (see the tests\\ skip in main())."""
    if len(sys.argv) > 1 and sys.argv[1].strip():
        return sys.argv[1], False
    # Claude Code delivers PostToolUse context as a JSON object on stdin,
    # e.g. { "tool_input": { "file_path": "..." } }.
    try:
        raw = sys.stdin.read()
    except Exception:
        raw = ""
    if raw and raw.strip():
        try:
            return json.loads(raw).get("tool_input", {}).get("file_path"), True
        except Exception:
            return None, True
    return None, True


def main():
    target, is_hook_mode = resolve_target()
    if not target:
        sys.exit(0)

    # Skip rather than guess a project path - CLAUDE_PROJECT_DIR unset means the target project's
    # logs\ folder can't be determined safely.
    project_root = os.environ.get("CLAUDE_PROJECT_DIR")
    if not project_root:
        print("[WARN] consistency_check.py: CLAUDE_PROJECT_DIR not set - skipping "
              "(cannot determine this project's log folder safely)")
        sys.exit(0)

    # Guard: only process .py files
    if not target.endswith(".py"):
        sys.exit(0)
    if not os.path.exists(target):
        print(f"[WARN] consistency_check.py: target file not found: {target}")
        sys.exit(0)

    # Golden-suite fixtures (tests\<tool>\...) are deliberately valid/invalid code by design - a
    # fail_*.py fixture is SUPPOSED to trip a finding so check_tower_crane.py's golden suite can
    # assert the checker still catches it. Checking one live via the automatic hook would hard-
    # block an editor for touching an intentionally-broken fixture, which is not a real defect.
    # Only skip in hook mode: an explicit direct-mode invocation (a human, or the golden suite
    # itself) is deliberately asking for a real result, FAIL included, and must still get one.
    if is_hook_mode and "tests" in Path(target).resolve().parts:
        print(f"[SKIP] consistency_check.py: {os.path.basename(target)} is under a tests\\ "
              "fixture directory - not checked live (golden-suite fixtures are deliberately "
              "valid/invalid by design; the golden suite exercises them directly).")
        sys.exit(0)

    # Log folder: logs\YYYY-MM\
    now = datetime.now()
    log_root = os.path.join(project_root, "logs")
    month_dir = os.path.join(log_root, now.strftime("%Y-%m"))
    timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")
    basename = os.path.basename(target)
    log_file = os.path.join(month_dir, f"{timestamp}_{basename}.log")
    latest = os.path.join(log_root, "latest_check.txt")
    os.makedirs(month_dir, exist_ok=True)

    # Header to terminal
    print("")
    print("================================================================")
    print("CONSISTENCY CHECK")
    print(f"File   : {basename}")
    print(f"Run at : {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print("================================================================")

    findings = check_file(target)

    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    os.makedirs(os.path.dirname(latest), exist_ok=True)

    with open(log_file, "w", encoding="utf-8") as lf, \
         open(latest, "w", encoding="utf-8") as ltf:

        if not findings:
            emit(f"[PASS]  No certain failures found in {basename}", lf, ltf)
        else:
            # also_stderr=True on every line: exit code 2 below only gets auto-fed back to
            # Claude Code if the report is actually ON stderr, not just stdout/log files.
            emit("", lf, ltf, also_stderr=True)
            emit("=" * 60, lf, ltf, also_stderr=True)
            emit(f"[FAIL]  CONSISTENCY CHECK -- {basename}", lf, ltf, also_stderr=True)
            emit("=" * 60, lf, ltf, also_stderr=True)
            for i, f in enumerate(findings, 1):
                emit("", lf, ltf, also_stderr=True)
                emit(f"[{i}] {f['severity']}", lf, ltf, also_stderr=True)
                emit(f"    Line(s): {f['lines']}", lf, ltf, also_stderr=True)
                emit(f"    Issue:   {f['issue']}", lf, ltf, also_stderr=True)
                emit(f"    Detail:  {f['example']}", lf, ltf, also_stderr=True)
            emit("", lf, ltf, also_stderr=True)
            emit("=" * 60, lf, ltf, also_stderr=True)
            emit(f"  {len(findings)} certain failure(s) found. Claude must resolve before continuing.", lf, ltf, also_stderr=True)
            emit("=" * 60, lf, ltf, also_stderr=True)
            emit("", lf, ltf, also_stderr=True)

    print("")
    if findings:
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
