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
CHECKS = 0
# Floor for the number of assertions that must actually execute. Raise it when
# you add checks; a drop means a test stopped running, not that nothing broke.
MIN_CHECKS = 65


def load(fname, modname):
    spec = importlib.util.spec_from_file_location(modname, os.path.join(HERE, fname))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def check(label, got, want):
    global CHECKS
    CHECKS += 1
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


# --------------------------------------------------------------------------
# run-reimplement.score() — decision + reason, where the reason axis is scored
# over a SUBSET (the KEEP cases). The subset is the mutation-bait here: a
# scorer that scores reason over all cases, or that conflates it with decision,
# dies on the "one KEEP justified generically" row below.
# --------------------------------------------------------------------------
def test_run_reimplement():
    print("run-reimplement.score()")
    m = load("run-reimplement.py", "rri")
    cases = [
        {"id": "k1", "decision": "KEEP", "accept": ["KEEP"], "reason_must_match": "persist|stored"},
        {"id": "k2", "decision": "KEEP", "accept": ["KEEP"], "reason_must_match": "persist|stored"},
        {"id": "r1", "decision": "REPLACE", "accept": ["REPLACE"], "reason_must_match": ""},
        {"id": "r2", "decision": "REPLACE", "accept": ["REPLACE"], "reason_must_match": ""},
    ]
    perfect = {"k1": ("KEEP", "the digest is persisted and compared"),
               "k2": ("KEEP", "stored values would be invalidated"),
               "r1": ("REPLACE", "nothing stored"), "r2": ("REPLACE", "mechanical")}
    s = m.score(cases, perfect)
    check("perfect -> decision 1.0", s["decision"], 1.0)
    check("perfect -> reason 1.0", s["reason"], 1.0)
    check("perfect -> both 1.0", s["both"], 1.0)
    check("reason denominator is the KEEP subset", s["reason_n"], 2)

    # Degenerate strategy A: apply the leverage ratio and replace everything.
    s = m.score(cases, {c["id"]: ("REPLACE", "few symbols, many modules") for c in cases})
    check("replace-everything -> decision 0.5", s["decision"], 0.5)   # kills `return 1.0`
    check("replace-everything -> reason 0.0", s["reason"], 0.0)

    # Degenerate strategy B: refuse everything, with no mechanism named.
    s = m.score(cases, {c["id"]: ("KEEP", "risky to reimplement") for c in cases})
    check("refuse-everything -> decision 0.5", s["decision"], 0.5)
    check("refuse-everything -> reason 0.0", s["reason"], 0.0)

    # The discriminating row: every decision right, but one KEEP justified with a
    # generic reason. decision and reason MUST diverge here — a mutation that
    # conflates the two metrics, or scores reason over all 4 cases, dies on this.
    mixed = dict(perfect); mixed["k2"] = ("KEEP", "it seems risky to reimplement")
    s = m.score(cases, mixed)
    check("right calls, one generic reason -> decision 1.0", s["decision"], 1.0)
    check("right calls, one generic reason -> reason 0.5", s["reason"], 0.5)
    check("right calls, one generic reason -> both 0.75", s["both"], 0.75)

    # Naming the mechanism while voting the wrong way earns nothing.
    s = m.score(cases, {**perfect, "k1": ("REPLACE", "the digest is persisted and compared")})
    check("mechanism named but decision wrong -> reason 0.5", s["reason"], 0.5)

    check("missing predictions -> decision 0.0", m.score(cases, {})["decision"], 0.0)


# --------------------------------------------------------------------------
# _stats — the intervals printed beside headline deltas. Two known-bads from the
# proposal that asked for them: an arm against itself, and a scrambled pairing.
# --------------------------------------------------------------------------
def test_stats():
    print("_stats")
    m = load("_stats.py", "evals_stats")
    a = [0.1, 0.3, 0.5, 0.7, 0.9, 0.2, 0.6]

    r = m.paired_bootstrap(a, a)
    check("arm vs itself -> delta 0.0", r["point"], 0.0)
    check("arm vs itself -> CI contains 0", r["lo"] <= 0.0 <= r["hi"], True)

    # A constant per-case shift: every resample has the same mean difference, so a
    # PAIRED interval collapses to the point. An unpaired resampler does not.
    b = [x + 0.1 for x in a]
    paired = m.paired_bootstrap(a, b)
    check("constant shift -> delta +0.1", round(paired["point"], 9), 0.1)
    check("constant shift -> paired CI width 0", round(paired["hi"] - paired["lo"], 9), 0.0)
    scrambled = m.paired_bootstrap(a, list(reversed(b)))
    check("scrambled pairing widens the interval",
          (scrambled["hi"] - scrambled["lo"]) > (paired["hi"] - paired["lo"]) + 0.05, True)
    check("seed is reported", paired["seed"], m.DEFAULT_SEED)
    check("same seed -> same interval", m.paired_bootstrap(a, list(reversed(b)))["lo"], scrambled["lo"])

    check("McNemar: 0 vs 6 discordant -> p 2/64",
          m.mcnemar_exact([False] * 6, [True] * 6)["p"], 2 / 64)
    check("McNemar: balanced discordance -> p 1.0",
          m.mcnemar_exact([True, False, True, False], [False, True, False, True])["p"], 1.0)
    check("McNemar: no discordant pairs -> p 1.0",
          m.mcnemar_exact([True, True], [True, True])["p"], 1.0)

    const = m.bootstrap_mean([0.5] * 5)
    check("constant arm -> CI is the point", (const["lo"], const["hi"]), (0.5, 0.5))
    line = m.format_interval(paired)
    check("printed line carries n and seed", "n=7 cases" in line and "seed=0" in line, True)
    check("few cases -> the line says the interval is a floor", "floor" in line, True)
    many = m.format_interval(m.paired_bootstrap(a * 2, b * 2))
    check("enough cases -> no few-cases warning", "floor" in many, False)

    for label, fn in (("empty arms raise", lambda: m.paired_bootstrap([], [])),
                      ("mismatched arms raise", lambda: m.paired_bootstrap([1.0], [1.0, 0.0]))):
        try:
            fn()
            check(label, "no exception", "ValueError")
        except ValueError:
            check(label, "ValueError", "ValueError")


# --------------------------------------------------------------------------
# _rawlog — every model response is kept beside the results (added 2026-10-16,
# after a scorer fix could not re-score a run whose builds had lived in /tmp).
# --------------------------------------------------------------------------
def test_rawlog():
    print("_rawlog")
    import ast, glob, io, json as _json, tempfile, urllib.request
    m = load("_rawlog.py", "evals_rawlog")
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["EVALS_RAWLOG_DIR"] = tmp
        try:
            req = urllib.request.Request(
                "https://openrouter.ai/api/v1/chat/completions",
                data=_json.dumps({"model": "x/y", "messages": []}).encode(),
                headers={"Authorization": "Bearer KEY-MUST-NOT-BE-LOGGED"})
            # Built at runtime so no secret-shaped literal sits in this file (gitleaks).
            fake = "sk" + "_live_" + "abcdefgh1234"
            resp = {"id": "gen-123", "choices": [{"message": {"content": "key " + fake}}]}
            path = m.record("/x/run-demo.py", req, resp)
            rows = [_json.loads(l) for l in open(path, encoding="utf-8")]
            check("one row per call", len(rows), 1)
            check("generation id kept", rows[0]["generation_id"], "gen-123")
            check("model read from the body", rows[0]["model"], "x/y")
            check("file named after the runner", os.path.basename(path), "run-demo.jsonl")
            text = open(path, encoding="utf-8").read()
            check("API key never written", "KEY-MUST-NOT-BE-LOGGED" in text, False)
            check("secret-shaped string scrubbed", fake in text, False)
            check("scrub is counted", rows[0]["scrubbed_strings"], 1)
            m.record("/x/run-demo.py", req, resp)
            check("calls append, never overwrite", sum(1 for _ in open(path)), 2)
            blocker = os.path.join(tmp, "a-file")
            open(blocker, "w").close()
            os.environ["EVALS_RAWLOG_DIR"] = blocker      # a file where a dir must go
            try:
                m.record("/x/run-demo.py", req, resp)
                check("unwritable log stops the run", "returned", "SystemExit")
            except SystemExit:
                check("unwritable log stops the run", "SystemExit", "SystemExit")
        finally:
            os.environ.pop("EVALS_RAWLOG_DIR", None)

    # Census: a function that calls the API must also keep the response. Adding a
    # runner with its own call() and no record() fails here, not after a lost run.
    sites, missing = 0, []
    for f in sorted(glob.glob(os.path.join(HERE, "run-*.py")) + glob.glob(os.path.join(HERE, "judge-*.py"))):
        tree = ast.parse(open(f, encoding="utf-8").read())
        for fn in ast.walk(tree):
            if not isinstance(fn, ast.FunctionDef):
                continue
            calls = [c for c in ast.walk(fn) if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)]
            if any(c.func.attr == "urlopen" for c in calls):
                sites += 1
                if not any(c.func.attr == "record" and getattr(c.func.value, "id", "") == "_rawlog" for c in calls):
                    missing.append(f"{os.path.basename(f)}:{fn.name}")
    check("API call sites found (denominator)", sites >= 12, True)
    check("every API call site keeps its raw response", missing, [])


if __name__ == "__main__":
    for t in (test_run_clean, test_run_adjudication, test_run_repo_audit,
              test_run_reimplement, test_stats, test_rawlog):
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
    # Report the denominator and fail closed on an empty scope: "0 checked, 0
    # failed, exit 0" is indistinguishable from a real pass, and an early return
    # or an emptied test tuple would have printed PASS here forever
    # (sota-code-security rules/11 §2.2).
    if CHECKS < MIN_CHECKS:
        print(f"FAIL: only {CHECKS} scoring check(s) ran, expected at least "
              f"{MIN_CHECKS} — did a test return early?")
        sys.exit(1)
    print(f"PASS: eval scoring functions behave correctly ({CHECKS} checks)")
