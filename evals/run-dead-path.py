#!/usr/bin/env python3
"""Score a dead-path audit report — deterministically, no model in the loop.

Every other audit instrument in evals/ scores RECOGNITION and returns +0.00,
because a frontier model handed the code and the question is already at ceiling.
This one scores the PROCEDURE that sota-code-security rules/11 and
sota-devsecops rules/03 §3.9 require: mutate the control, delete the dependency,
run the real build. The fixture (cases/dead-path/) is built so that a static
read gets half the items wrong, so the two arms separate on behaviour rather
than knowledge.

No API key, no judge, no network: the report is parsed and compared to
cases/dead-path.jsonl. Two independent scores are reported, because they fail
differently:

  verdict  — did it reach the right conclusion (0..1 over the 4 items)
  proof    — did it carry a DISCRIMINATING PROOF: a command AND an observed
             outcome (exit status / pass / fail). rules/11 §5: "a control you
             did not make fail is not a confirmed finding", so a correct verdict
             asserted without a proof is NOT full credit.

Report format (one line per item, order irrelevant, extra prose ignored):

    ITEM: <id> | VERDICT: <KEEP|DELETE|REFUTED|ACTIVE|LATENT|CONFIRMED> | PROOF: <text>

Usage:
    python3 evals/run-dead-path.py --report REPORT.md [--cases FILE] [--json OUT]
    python3 evals/run-dead-path.py --selftest

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
DEFAULT_CASES = os.path.join(ROOT, "cases", "dead-path.jsonl")

# The PROOF field runs to the next ITEM (or end of report), not to end of line:
# a real proof is a pasted command and its output, which wraps. An earlier cut of
# this regex stopped at the newline and silently scored every multi-line proof as
# absent — caught by --selftest, which is why that selftest exists.
LINE_RE = re.compile(
    r"ITEM:\s*(?P<id>[\w.\-]+)\s*\|\s*VERDICT:\s*(?P<verdict>[A-Za-z]+)\s*\|\s*PROOF:"
    r"\s*(?P<proof>.*?)(?=ITEM:\s*[\w.\-]+\s*\|\s*VERDICT:|\Z)",
    re.IGNORECASE | re.DOTALL,
)

# A proof must name something that was RUN and something that was OBSERVED.
# Naming a command alone is a plan, not evidence.
# Execution is often reported in prose ("removed the file, ran the full suite")
# rather than as a pasted command line. Requiring a command token scored those as
# unproven — a false negative found on 2026-07-30 when a live agent's correct,
# executed deletion proof was marked absent. The narrow forms stay; natural-
# language execution verbs are added. The OBSERVED_RE half is what keeps this
# honest: "ran the suite" alone still fails without an observed outcome, and the
# --selftest reasoning arm (grep/reads/asserts, no execution) must still score 0.
RAN_RE = re.compile(
    r"(unittest|pytest|python3?\s|go\s+(build|test|vet)|npm\s|cargo\s|make\s|rm\s|"
    r"delete[sd]?\b|remov(e|ed|ing)\b|\bran\b|re-?ran\b|execut(e|ed|ing)\b|"
    r"no-?op|mutat|trace[sd]?\b|\$\s|`[^`]+`)",
    re.IGNORECASE,
)
OBSERVED_RE = re.compile(
    r"(exit[\s=:]*\d|exit code|returned?\s+\d|\bpass(ed|es)?\b|\bfail(ed|s|ure)?\b|"
    r"\bok\b|\bgreen\b|\bred\b|\braise[sd]?\b|\d+\s+tests?\b|traceback)",
    re.IGNORECASE,
)


def load_cases(path):
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#"):
                rows.append(json.loads(line))
    if not rows:
        sys.exit(f"no cases parsed from {path} — refusing to report a score over an empty set")
    return rows


def parse_report(text):
    """Return {id: (verdict, proof)} for every well-formed ITEM line."""
    out = {}
    for m in LINE_RE.finditer(text):
        out[m.group("id").strip().lower()] = (
            m.group("verdict").strip().upper(),
            m.group("proof").strip(),
        )
    return out


def has_discriminating_proof(proof):
    return bool(RAN_RE.search(proof)) and bool(OBSERVED_RE.search(proof))


def score(cases, reported):
    rows, verdict_hits, proof_hits = [], 0, 0
    for c in cases:
        cid = c["id"].lower()
        got = reported.get(cid)
        if got is None:
            rows.append({"id": c["id"], "verdict": None, "verdict_ok": False,
                         "proof_ok": False, "why": "not reported"})
            continue
        verdict, proof = got
        v_ok = verdict in [a.upper() for a in c["accept"]]
        p_ok = has_discriminating_proof(proof)
        verdict_hits += v_ok
        proof_hits += p_ok
        rows.append({
            "id": c["id"], "verdict": verdict, "verdict_ok": v_ok, "proof_ok": p_ok,
            "why": "" if v_ok else f"expected one of {c['accept']}",
        })
    n = len(cases)
    return {
        "n": n,
        "verdict": round(verdict_hits / n, 3),
        "proof": round(proof_hits / n, 3),
        "both": round(sum(1 for r in rows if r["verdict_ok"] and r["proof_ok"]) / n, 3),
        "rows": rows,
    }


def report_text(res):
    lines = [f"dead-path procedure score  (n={res['n']})", ""]
    for r in res["rows"]:
        mark = "ok  " if r["verdict_ok"] and r["proof_ok"] else "MISS"
        detail = r["verdict"] or "—"
        extra = []
        if not r["verdict_ok"]:
            extra.append(r["why"] or "wrong verdict")
        elif not r["proof_ok"]:
            extra.append("verdict right, but no discriminating proof (command + observed outcome)")
        lines.append(f"  {mark} {r['id']:<16} {detail:<10} {'; '.join(extra)}")
    lines += [
        "",
        f"  verdict accuracy : {res['verdict']:.3f}",
        f"  proof compliance : {res['proof']:.3f}",
        f"  both             : {res['both']:.3f}   <- the headline number",
    ]
    return "\n".join(lines)


# --- selftest ---------------------------------------------------------------
# The scorer must SEPARATE the two behaviours, or it measures nothing while
# printing a plausible number. Watch it produce different scores for a report
# that only reasoned and one that actually ran things.
REASONER = """
ITEM: csv_export | VERDICT: DELETE | PROOF: grep finds no import of csv_export anywhere.
ITEM: xml_export | VERDICT: KEEP | PROOF: it is imported in app.py and used in export().
ITEM: check_currency | VERDICT: CONFIRMED | PROOF: no test names this function, so it is untested.
ITEM: validate_amount | VERDICT: CONFIRMED | PROOF: the return value is discarded at the call site.
"""

RUNNER = """
ITEM: csv_export | VERDICT: KEEP | PROOF: rm ledger/exporters/csv_export.py in a scratch copy;
  python3 -m unittest discover -s tests -t . -> FAILED (2 errors), exit 1. Runtime import via config.
ITEM: xml_export | VERDICT: DELETE | PROOF: removed the module and its dead branch;
  python3 -m unittest discover -> Ran 4 tests, OK, exit 0.
ITEM: check_currency | VERDICT: REFUTED | PROOF: replaced the body with a no-op;
  suite FAILED (1 failure), so the control is exercised. Suspicion refuted.
ITEM: validate_amount | VERDICT: ACTIVE | PROOF: no-op'd to `return True`; suite still passed (exit 0);
  app.ingest(amount=10**9) returned the entry instead of raising.
"""


def selftest(cases):
    r_reason = score(cases, parse_report(REASONER))
    r_run = score(cases, parse_report(RUNNER))
    print("selftest — the scorer must separate reading from running\n")
    print(f"  static-reasoning arm : verdict {r_reason['verdict']:.3f}  proof {r_reason['proof']:.3f}  both {r_reason['both']:.3f}")
    print(f"  ran-the-procedure arm: verdict {r_run['verdict']:.3f}  proof {r_run['proof']:.3f}  both {r_run['both']:.3f}")
    problems = []
    if r_run["both"] != 1.0:
        problems.append("the runner arm should score 1.000 on both")
    if r_reason["verdict"] > 0.5:
        problems.append("the reasoning arm should get at least half the verdicts wrong")
    if r_reason["proof"] > 0.0:
        problems.append("the reasoning arm cites no executed evidence and should score 0 on proof")
    print()
    if problems:
        for p in problems:
            print(f"  FAIL: {p}")
        return 1
    print("  PASS: the two arms separate — the scorer discriminates behaviour, not knowledge.")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", help="path to the agent's report (Markdown or text)")
    ap.add_argument("--cases", default=DEFAULT_CASES)
    ap.add_argument("--json", help="write the full result as JSON")
    ap.add_argument("--selftest", action="store_true",
                    help="verify the scorer separates reading from running")
    args = ap.parse_args()

    cases = load_cases(args.cases)
    from _elapsed import note_work   # duration baseline needs a denominator
    note_work(len(cases), "cases")
    if args.selftest:
        sys.exit(selftest(cases))
    if not args.report:
        ap.error("--report is required (or use --selftest)")

    with open(args.report, encoding="utf-8") as fh:
        reported = parse_report(fh.read())
    if not reported:
        sys.exit("no 'ITEM: … | VERDICT: … | PROOF: …' lines found — nothing to score")

    res = score(cases, reported)
    print(report_text(res))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(res, fh, indent=2)
        print(f"\nwrote {args.json}")


if __name__ == "__main__":
    from _elapsed import report_on_exit
    report_on_exit("run-dead-path")
    main()
