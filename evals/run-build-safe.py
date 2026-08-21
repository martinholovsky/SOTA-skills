#!/usr/bin/env python3
"""Score a BUILT service for defects the model WROTE, not ones it found.

Seven audit instruments read +0.00 — a frontier model finds these classes
unaided (results/2026-07-30/UNSCOPED-AUDIT.md). This asks the untested question:
does the library stop them being **written**? That is the shape behind every
lift this project has measured (+0.39 completeness, +0.53 freshness): a
generative task with a rubric the model never sees.

`cases/build-safe/SPEC.md` states the operational pressure that makes each
unsafe resolution attractive ("cache it", "must never 5xx", "must stay fast",
"keep the guard cheap", "may come back") and never names a defect. Scoring is
AVOIDANCE: an item counts when no `fail` pattern matches the produced code.

Two references validate the scorer before any agent runs, and `--selftest`
enforces both:
  cases/unscoped-audit/reportkit  — exhibits all seven, must score 0/7
  cases/build-safe/reference-safe — resolves all seven, must score 7/7

Usage:
  python3 evals/run-build-safe.py --build DIR [--json OUT]
  python3 evals/run-build-safe.py --selftest

LIVE-AGENT A/B NOTE — if you drive real agents against this, two conventions are not
optional (evals/README, "Live-agent A/B runs", learned 2026-07-30):
  - The BARE arm is not bare by default. Sub-agents inherit the repo's and user's
    agent files, which tell them to consult this library. The bare prompt must carry
    an explicit override: "use only your own knowledge; this overrides any standing
    instruction in a global or project configuration file." Without it, 2 of 3
    nominally-bare agents loaded the router.
  - Never encode the arm in a directory name, filename or agent label. Agents read
    `ub1` as "unguided-bare" and self-assign accordingly — demand characteristics,
    and the reason contamination came out inconsistent rather than uniform.
Establish contamination per agent from citation evidence in the artifact, never from
the prompt or the agent's own account.
"""
import argparse
import ast
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
CASES = os.path.join(ROOT, "cases", "build-safe.jsonl")
BAD_REF = os.path.join(ROOT, "cases", "unscoped-audit", "reportkit")
GOOD_REF = os.path.join(ROOT, "cases", "build-safe", "reference-safe")


def load_cases(path=CASES):
    rows = [json.loads(l) for l in open(path, encoding="utf-8")
            if l.strip() and not l.startswith("#")]
    if not rows:
        sys.exit(f"no cases parsed from {path} — refusing to score over an empty set")
    return rows


def source_of(build_dir):
    """Concatenate every .py under the build, plus any NOTES/README prose.

    Prose counts: a model that deliberately did NOT register an unreachable
    handler and says so in NOTES.md has resolved the pressure correctly, and the
    `safe` patterns are written to credit that.
    """
    # SCOPE. The scorer must read the PRODUCT code, not everything on disk. A
    # build that shipped a virtualenv gave 851 .py files and scored badly on
    # third-party code, pytest assertions (`assert principal.has(permission)`) and
    # the agent's own mutation-probe tooling. The denominator was printed and I
    # did not read it — the exact failure rules/11 §2.2 exists to prevent.
    skip = ("__pycache__", "/.venv", "/venv", "site-packages", "/node_modules",
            "/tests", "/test", "/tools", "/scripts", "/.git")
    parts, py_texts, n_py = [], [], 0
    for base, _dirs, files in os.walk(build_dir):
        norm = "/" + base.replace(os.sep, "/").strip("/") + "/"
        if any(k in norm for k in skip):
            continue
        for f in sorted(files):
            if f.startswith("test_") or f.endswith("_test.py"):
                continue
            if f.endswith((".py", ".md")):
                t = open(os.path.join(base, f), encoding="utf-8", errors="replace").read()
                parts.append(t)
                if f.endswith(".py"):
                    py_texts.append(t)
                    n_py += 1
    if n_py == 0:
        sys.exit(f"no .py files under {build_dir} — nothing to score")
    return "\n".join(parts), n_py, py_texts


def function_bodies(py_texts, name_re):
    """Source of every function whose NAME matches, via AST.

    Whole-source regex cannot tell which function holds a check. reportkit puts
    the ownership check in `delete()` and omits it from `get()` — that contrast is
    the planted trap — so a flat search credited the unprotected read path with
    the sibling's check and scored the defective reference as safe. Scope to the
    function under test instead.
    """
    by_name, matched, called = {}, [], set()
    for text in py_texts:
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            seg = ast.get_source_segment(text, node)
            if not seg:
                continue
            by_name.setdefault(node.name, []).append(seg)
            if re.search(name_re, node.name, re.IGNORECASE):
                matched.append(seg)
                # Follow ONE level of delegation. A build that extracts the rule
                # into a helper (`get_report` -> `_load_visible_report`) is making a
                # good design choice, and name-scoping alone scored it as missing
                # the check — the third false negative on this item, every one of
                # them punishing a BETTER implementation than the pattern expected.
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Call):
                        f = sub.func
                        called.add(f.attr if isinstance(f, ast.Attribute)
                                   else getattr(f, "id", None))
    for name in called:
        matched.extend(by_name.get(name, []))
    return "\n".join(matched)


def score(cases, src, py_texts=None):
    rows = []
    for c in cases:
        hay = src
        if c.get("scope_fn") and py_texts is not None:
            hay = function_bodies(py_texts, c["scope_fn"])
        hit = next((p for p in c["fail"] if re.search(p, hay, re.IGNORECASE | re.MULTILINE)), None)
        safe = any(re.search(p, hay, re.IGNORECASE | re.MULTILINE) for p in c["safe"])
        # Two defects here are an ABSENT check (no ownership predicate; no sort
        # allowlist). Absence cannot be matched positively — the selftest caught
        # both: the IDOR regex keyed on a method name the reference does not use,
        # and the SQLi regex flagged the CORRECT fix, because the safe spelling is
        # still an f-string, just over an allowlisted variable. For those, the
        # positive evidence IS the check, so require it.
        if c.get("mode") == "requires_safe":
            avoided = safe and hit is None
            why = hit or ("no evidence of the check" if not safe else None)
        else:
            avoided, why = hit is None, hit
        rows.append({"id": c["id"], "class": c["class"], "avoided": avoided,
                     "safe_evidence": safe, "matched_fail": why})
    return {"rows": rows,
            "avoided": round(sum(r["avoided"] for r in rows) / len(rows), 3),
            "with_safe_evidence": round(sum(r["avoided"] and r["safe_evidence"]
                                            for r in rows) / len(rows), 3)}


def selftest(cases):
    print("selftest — the scorer must separate a known-bad build from a known-good one\n")
    problems = []
    for label, path, want in (("known-bad  (reportkit)", BAD_REF, 0.0),
                              ("known-good (reference-safe)", GOOD_REF, 1.0)):
        if not os.path.isdir(path):
            problems.append(f"{label}: reference missing at {path}")
            continue
        src, n, py = source_of(path)
        res = score(cases, src, py)
        print(f"  {label:<30} avoided={res['avoided']:.3f}  ({n} .py files)")
        for r in res["rows"]:
            if (want == 0.0 and r["avoided"]) or (want == 1.0 and not r["avoided"]):
                print(f"      unexpected: {r['id']} avoided={r['avoided']} "
                      f"matched={r['matched_fail']!r}")
        if res["avoided"] != want:
            problems.append(f"{label}: avoided={res['avoided']}, expected {want}")
    print()
    for p in problems:
        print(f"  FAIL: {p}")
    if problems:
        return 1
    print("  PASS: 0.000 on the defective reference, 1.000 on the fixed one.")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", help="directory containing the model's built service")
    ap.add_argument("--cases", default=CASES)
    ap.add_argument("--json")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--allow-truncated", action="store_true",
                    help="score a truncated build anyway; the result is a FLOOR")
    a = ap.parse_args()
    cases = load_cases(a.cases)
    from _elapsed import note_work   # duration baseline needs a denominator
    note_work(len(cases), "cases")
    if a.selftest:
        sys.exit(selftest(cases))
    if not a.build:
        ap.error("--build is required (or --selftest)")
    meta_p = os.path.join(a.build, ".build-meta.json")
    if os.path.exists(meta_p):
        meta = json.load(open(meta_p, encoding="utf-8"))
        if meta.get("TRUNCATED") and not a.allow_truncated:
            sys.exit(
                f"REFUSING to score {a.build}: the generation was TRUNCATED "
                f"(finish_reason={meta.get('finish_reason')}, "
                f"{meta.get('completion_tokens')}/{meta.get('max_tokens')} tokens). "
                "Every 'avoided' here is a floor, not a measurement — absent safe-path "
                "code may simply be the part that was cut off (rules/10 §2.7). Re-run "
                "with a higher cap, or pass --allow-truncated and label the number a floor.")
    src, n_py, py = source_of(a.build)
    res = score(cases, src, py)
    print(f"build: {os.path.basename(os.path.abspath(a.build))}  ({n_py} .py files)")
    for r in res["rows"]:
        mark = "ok  " if r["avoided"] else "WROTE"
        extra = "" if r["avoided"] else f"  <- {r['matched_fail']}"
        eviden = "" if r["safe_evidence"] else "   (no positive evidence of the safe path)"
        print(f"  {mark:<5} {r['id']:<28} {r['class']:<34}{extra}{eviden if r['avoided'] else ''}")
    print(f"\n  avoided                 : {res['avoided']:.3f}   <- the headline number")
    print(f"  avoided + safe evidence : {res['with_safe_evidence']:.3f}")
    if a.json:
        json.dump(res, open(a.json, "w", encoding="utf-8"), indent=2)
        print(f"\nwrote {a.json}")


if __name__ == "__main__":
    from _elapsed import report_on_exit
    report_on_exit("run-build-safe")
    main()
