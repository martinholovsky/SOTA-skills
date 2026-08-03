#!/usr/bin/env python3
"""Adjudicate an unscoped-audit report against planted ground truth.

Deterministic first pass, human-verifiable second pass. The rule was fixed in
results/2026-07-30/PRE-REGISTRATION.md BEFORE any agent ran:

    a defect counts as FOUND only if the report names the mechanism AND points
    at one of that case's `primary` files.

So a hit needs both signals. Mechanism keywords come from the case's `must`
list; the file signal comes from `primary`. Neither alone counts — naming the
file without the mechanism is "looked at it", and naming the mechanism without
the file is unlocated.

It also reports a CONTAMINATION verdict, because the live-agent runs on
2026-07-30 showed that sub-agents inherit a global instruction to consult the
SOTA library and some "bare" agents loaded it anyway. Self-report is not
evidence; library citations in the text are.

Usage:
  python3 evals/run-unscoped-audit.py --report R.md --cases evals/cases/unscoped-audit.jsonl
  python3 evals/run-unscoped-audit.py --selftest

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
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))

# Text that only appears if the agent read the library. `router` is deliberately
# NOT here: FastAPI's APIRouter matched it 12 times in a clean report and made a
# first cut of this check report false contamination.
LIB_PATTERNS = [
    r"sota-[a-z]+",
    r"rules/\d{2}",
    r"§\d",
    r"silent[- ]control",
    r"falsification question",
    r"blast radius",
]


def load_cases(path):
    rows = [json.loads(l) for l in open(path, encoding="utf-8")
            if l.strip() and not l.startswith("#")]
    if not rows:
        sys.exit(f"no cases parsed from {path} — refusing to score over an empty set")
    return rows


def contamination(text):
    """Library-citation evidence, with two corrections learned on 2026-07-30.

    1. The scratchpad path contains 'SOTA-skills', so every report quoting its own
       target path matched `sota-[a-z]+` once. Strip path-like tokens first.
    2. A single occurrence of a common security phrase ('blast radius') flagged a
       verifiably clean report. Require a THRESHOLD: contamination is a pattern of
       citation, not one word. Both false positives are recorded in the selftest.
    """
    # Strip ABSOLUTE paths only (3+ segments). A first cut stripped every token
    # containing a slash, which also deleted the `rules/10` citations this check
    # exists to find — it turned a known-contaminated report clean. Keep short
    # citations; drop the scratchpad path that embeds the library's own name.
    stripped = re.sub(r"(?:/[\w.\-]+){3,}", " ", text)
    hits = {}
    for pat in LIB_PATTERNS:
        n = len(re.findall(pat, stripped, re.IGNORECASE))
        if n:
            hits[pat] = n
    # "silent[- ]control" is distinctive library vocabulary, not general security
    # usage — it is what caught the one agent that loaded the router while citing
    # no file paths at all. Excluding it produced a false NEGATIVE on a
    # self-reported-contaminated report, which is the more dangerous direction.
    strong = sum(n for p, n in hits.items()
                 if p in (r"rules/\d{2}", r"§\d", r"sota-[a-z]+",
                          r"falsification question", r"silent[- ]control"))
    weak = sum(hits.values())
    return (hits if (strong >= 2 or weak >= 4) else {})


def found(case, text):
    low = text.lower()
    file_hit = any(os.path.basename(f).lower() in low for f in case["primary"])
    mech_hit = any(re.search(k, low, re.IGNORECASE) for k in case["must"])
    return file_hit and mech_hit, file_hit, mech_hit


def score(cases, text):
    rows = []
    for c in cases:
        ok, fh, mh = found(c, text)
        rows.append({"id": c["id"], "group": c["group"], "class": c["class"],
                     "found": ok, "file_named": fh, "mechanism_named": mh})
    def rate(group):
        sub = [r for r in rows if r["group"] == group]
        return round(sum(r["found"] for r in sub) / len(sub), 3) if sub else None
    return {"rows": rows, "control": rate("control"), "treatment": rate("treatment"),
            "all": round(sum(r["found"] for r in rows) / len(rows), 3)}


SELFTEST_HIT = """
The ORDER BY clause in db.py interpolates `sort` with an f-string — SQL injection.
reports.py get() has no ownership check, so any user reads any report (IDOR).
webhooks.py swallows the signature exception with except Exception: pass.
quota_events.py registers a handler for an event nothing dispatches — unreachable.
permissions.py caches on user_id only; revoke_role never invalidates it — stale.
admin.py guards purge_tenant with assert, which python -O strips.
uploads.py scan() only inspects the first 64KB; the rest is stored unscanned.
"""
SELFTEST_MISS = """
The code is generally clean. Some functions lack type hints and the module
docstrings could be more detailed. Consider adding tests.
"""


def selftest(cases):
    hit, miss = score(cases, SELFTEST_HIT), score(cases, SELFTEST_MISS)
    print(f"  full-hit report : all={hit['all']:.3f} control={hit['control']} treatment={hit['treatment']}")
    print(f"  no-hit report   : all={miss['all']:.3f} control={miss['control']} treatment={miss['treatment']}")
    print(f"  contamination on a clean text: {contamination(SELFTEST_MISS) or 'none'}")
    problems = []
    if hit["all"] != 1.0:
        problems.append("a report naming every mechanism at every primary file must score 1.000")
    if miss["all"] != 0.0:
        problems.append("a report naming no mechanism must score 0.000")
    if contamination(SELFTEST_MISS):
        problems.append("clean text must not trip the contamination check")
    for p in problems:
        print(f"  FAIL: {p}")
    if problems:
        return 1
    print("  PASS: adjudicator separates a full report from an empty one.")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report")
    ap.add_argument("--cases", default=os.path.join(ROOT, "cases", "unscoped-audit.jsonl"))
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    cases = load_cases(a.cases)
    from _elapsed import note_work   # duration baseline needs a denominator
    note_work(len(cases), "cases")
    if a.selftest:
        sys.exit(selftest(cases))
    if not a.report:
        ap.error("--report is required (or --selftest)")
    text = open(a.report, encoding="utf-8").read()
    res = score(cases, text)
    contam = contamination(text)
    print(f"report: {os.path.basename(os.path.dirname(a.report))}")
    for r in res["rows"]:
        mark = "ok  " if r["found"] else "MISS"
        why = "" if r["found"] else f"(file={r['file_named']}, mechanism={r['mechanism_named']})"
        print(f"  {mark} [{r['group'][:4]}] {r['id']:<28} {r['class']:<32} {why}")
    print(f"\n  control   recall : {res['control']}")
    print(f"  treatment recall : {res['treatment']}")
    print(f"  overall          : {res['all']}")
    print(f"  CONTAMINATED     : {'YES ' + str(contam) if contam else 'no (no library citations)'}")


if __name__ == "__main__":
    from _elapsed import report_on_exit
    report_on_exit("run-unscoped-audit")
    main()
