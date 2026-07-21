#!/usr/bin/env python3
"""Golden tests for the eval harness's SCORING functions.

Why this file exists — the honest version. On 2026-07-21 a mutation probe replaced
`run-clean.score()` with `return 1.0, {}` and asked what would notice:

    check-invariants.sh   PASSES
    pre-commit            PASSES
    scoring a deliberately wrong prediction set -> 1.00

Nothing noticed. There was no test suite anywhere in the repo and CI never touched
`evals/`, so the code that produces **every number this project publishes** — the
+0.39 in the README, every +0.00 we report as an honest null — was unverified. A
scorer stuck at 1.00 would have made all of it a lie, silently.

That is the `sota-code-security` rules/10 class at its worst: a control (the score)
that looks like it is working because it always produces a plausible number.

These tests are deliberately **mutation-resistant**: each scorer is checked against a
perfect prediction (1.0), an empty/wrong prediction (0.0), AND a partial one. The 0.0
cases are what kill a `return 1.0` mutation; the partial cases kill a `return 0.0` or
a swapped-metric mutation.

Plain `python3`, no pytest — so CI needs no extra dependency and this always runs.
Usage: `python3 evals/test_scoring.py`  (exit 0 = pass, 1 = fail)
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FAILURES = []


def load(fname, modname):
    spec = importlib.util.spec_from_file_location(modname, os.path.join(HERE, fname))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def check(label, got, want):
    ok = abs(got - want) < 1e-9 if isinstance(want, float) else got == want
    if not ok:
        FAILURES.append(f"{label}: got {got!r}, want {want!r}")
    print(f"  {'ok  ' if ok else 'FAIL'} {label}: {got!r}")


# --------------------------------------------------------------------------
# run-clean.score() — set-intersection recall (routing/audit) + token match
# --------------------------------------------------------------------------
def test_run_clean():
    print("run-clean.score()")
    m = load("run-clean.py", "rc")
    cases = [{"id": "a", "expect": ["x", "y"]}, {"id": "b", "expect": ["z"]}]

    r, miss = m.score(cases, {"a": ["x", "y"], "b": ["z"]}, "routing")
    check("perfect -> 1.0", r, 1.0)
    check("perfect -> no misses", miss, {})

    r, miss = m.score(cases, {}, "routing")
    check("empty predictions -> 0.0", r, 0.0)          # kills `return 1.0`
    check("empty predictions -> both missed", sorted(miss), ["a", "b"])

    r, _ = m.score(cases, {"a": ["x"], "b": []}, "routing")
    check("partial (1 of 2, 0 of 1) -> 0.25", r, 0.25)  # kills constants both ways

    r, _ = m.score(cases, {"a": ["x", "y", "JUNK"], "b": ["z"]}, "routing")
    check("extras don't reduce recall -> 1.0", r, 1.0)

    fresh = [{"id": "f", "expect": ["RFC 9999"]}]
    r, _ = m.score(fresh, {"f": "the answer is rfc 9999 today"}, "freshness")
    check("freshness token present (case-insensitive) -> 1.0", r, 1.0)
    r, _ = m.score(fresh, {"f": "no idea"}, "freshness")
    check("freshness token absent -> 0.0", r, 0.0)


# --------------------------------------------------------------------------
# run-adjudication.score() — accuracy / sensitivity / specificity
# --------------------------------------------------------------------------
def test_run_adjudication():
    print("run-adjudication.score()")
    m = load("run-adjudication.py", "ra")
    cases = [
        {"id": "r1", "expect": ["UPHELD"]}, {"id": "r2", "expect": ["UPHELD"]},
        {"id": "f1", "expect": ["REFUTED"]}, {"id": "f2", "expect": ["REFUTED"]},
    ]
    s = m.score(cases, {"r1": "UPHELD", "r2": "UPHELD", "f1": "REFUTED", "f2": "REFUTED"})
    check("all correct -> accuracy 1.0", s["accuracy"], 1.0)
    check("all correct -> sensitivity 1.0", s["sensitivity"], 1.0)
    check("all correct -> specificity 1.0", s["specificity"], 1.0)

    s = m.score(cases, {"r1": "REFUTED", "r2": "REFUTED", "f1": "UPHELD", "f2": "UPHELD"})
    check("all wrong -> accuracy 0.0", s["accuracy"], 0.0)          # kills `return 1.0`

    # An arm that refutes EVERYTHING: perfect specificity, zero sensitivity. This is
    # the degenerate strategy the two metrics exist to expose — if it ever scores well,
    # the scorer is broken.
    s = m.score(cases, {c["id"]: "REFUTED" for c in cases})
    check("refute-everything -> specificity 1.0", s["specificity"], 1.0)
    check("refute-everything -> sensitivity 0.0", s["sensitivity"], 0.0)
    check("refute-everything -> accuracy 0.5", s["accuracy"], 0.5)

    s = m.score(cases, {"r1": "UPHELD", "r2": "UPHELD", "f1": "REFUTED", "f2": "UPHELD"})
    check("one false-claim upheld -> specificity 0.5", s["specificity"], 0.5)
    check("missing prediction counts as wrong",
          m.score(cases, {"r1": "UPHELD"})["accuracy"], 0.25)


# --------------------------------------------------------------------------
# run-repo-audit.score()
# --------------------------------------------------------------------------
def test_run_repo_audit():
    print("run-repo-audit.score()")
    m = load("run-repo-audit.py", "rra")
    if not hasattr(m, "score"):
        FAILURES.append("run-repo-audit.score() not found — did it get renamed?")
        return
    # findings are dicts {category, file}; cases carry the `primary` files that make
    # a hit "strict". Both recalls are checked — a mutation that collapses them into
    # one number is caught by the row where they legitimately differ.
    cases = [{"id": "d1", "category": "idor", "primary": ["orders.py"]},
             {"id": "d2", "category": "ssrf", "primary": ["http_client.py"]}]
    perfect = [{"category": "idor", "file": "app/orders.py"},
               {"category": "ssrf", "file": "app/http_client.py"}]
    cat, strict, _ = m.score(cases, perfect)
    check("perfect -> category recall 1.0", cat, 1.0)
    check("perfect -> strict recall 1.0", strict, 1.0)

    cat, strict, _ = m.score(cases, [])
    check("no findings -> category 0.0", cat, 0.0)                  # kills `return 1.0`
    check("no findings -> strict 0.0", strict, 0.0)

    cat, strict, _ = m.score(cases, [{"category": "idor", "file": "app/orders.py"}])
    check("half -> category 0.5", cat, 0.5)
    check("half -> strict 0.5", strict, 0.5)

    # right category, WRONG file: category recall credits it, strict does not.
    # This row is the one that fails if the two metrics are ever conflated.
    cat, strict, _ = m.score(cases, [{"category": "idor", "file": "app/unrelated.py"},
                                     {"category": "ssrf", "file": "app/http_client.py"}])
    check("wrong file -> category 1.0", cat, 1.0)
    check("wrong file -> strict 0.5", strict, 0.5)


if __name__ == "__main__":
    for t in (test_run_clean, test_run_adjudication, test_run_repo_audit):
        try:
            t()
        except Exception as e:                       # a scorer that crashes is a failure
            FAILURES.append(f"{t.__name__} raised {type(e).__name__}: {e}")
            print(f"  FAIL {t.__name__} raised {type(e).__name__}: {e}")
    print()
    if FAILURES:
        print(f"FAIL: {len(FAILURES)} scoring check(s) failed")
        for f in FAILURES:
            print(f"  - {f}")
        sys.exit(1)
    print("PASS: eval scoring functions behave correctly")
