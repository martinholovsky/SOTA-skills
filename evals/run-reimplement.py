#!/usr/bin/env python3
"""Score a reimplementation-risk report — deterministically, no model in the loop.

STATUS — DOCUMENTATION, NOT A MEASURED INSTRUMENT (decided 2026-07-31).
This has never been run against a live agent and no number from it may be cited.
It is kept because building it did the useful work: it exposed a genuine ambiguity
in the rule it tests (a request signer is a "protocol" under §3.9.6, so the clause
forbade something reasonable), which is now fixed in §3.9.6. Seven audit
instruments already read +0.00 and docs/ROADMAP.md records "do not build another
audit-recall instrument"; running an eighth was declined. The scorer stays so the
case set is checkable and cannot rot, and its --selftest runs in CI.

What this measures. `sota-devsecops` rules/03 §3.9.4 tells an auditor to flag a
poor LEVERAGE RATIO (few symbols called, many modules inherited) as a
replace-in-house candidate. §3.9.6 bucket C then OVERRIDES that for two families:
the enumerated list (crypto/TLS/JWT/CORS/session cookies/WebAuthn/password
hashing/YAML|XML|PDF|archive parsing), and anything whose output is persisted and
must stay comparable with stored data. The second family is the dangerous one:
an equivalent-but-not-identical reimplementation keeps returning answers, just
wrong ones, against every value already stored.

So the fixture is built as a conflict: every disqualified case has a leverage
ratio that screams REPLACE. An arm that applies §3.9.4 and stops gets all five
wrong. An arm that refuses everything gets the five legitimate ones wrong. Both
degenerate strategies land at 0.500 on decision — verified by --selftest.

No API key, no judge, no network: the report is parsed and compared to
cases/reimplement.jsonl. Two scores, because they fail differently:

  decision — KEEP vs REPLACE, over all cases (0..1)
  reason   — over the KEEP cases only: did the justification name the actual
             disqualifying mechanism (stored-value comparability, the enumerated
             list, migrate-to-a-successor) rather than a generic "it's risky"?
             A right answer for the wrong reason gets the NEXT case wrong, which
             is exactly what the legitimate cases are there to catch. Credit
             requires the decision to be right AND the mechanism named.

Report format (one line per item, order irrelevant, extra prose ignored):

    ITEM: <id> | DECISION: <KEEP|REPLACE> | WHY: <text>

Usage:
    python3 evals/run-reimplement.py --report REPORT.md [--cases FILE] [--json OUT]
    python3 evals/run-reimplement.py --selftest
    python3 evals/run-reimplement.py --print-prompt        # what the agent is given
"""
import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CASES = os.path.join(ROOT, "cases", "reimplement.jsonl")

# Only these fields ever reach the model. The answer keys (decision/accept/
# reason_must_match/truth/trap/looks) live in the same file, so a runner that
# serialised the whole case would hand over the answer — the failure mode
# evals/README.md records under "a new field cannot silently leak the answer".
PROMPT_FIELDS = ("id", "dossier")

# WHY runs to the next ITEM (or end of report), not to end of line: a real
# justification wraps. Same lesson as run-dead-path.py's PROOF field, whose
# first cut stopped at the newline and scored every multi-line proof as absent.
LINE_RE = re.compile(
    r"ITEM:\s*(?P<id>[\w.\-]+)\s*\|\s*DECISION:\s*(?P<decision>[A-Za-z]+)\s*\|\s*WHY:"
    r"\s*(?P<why>.*?)(?=ITEM:\s*[\w.\-]+\s*\|\s*DECISION:|\Z)",
    re.IGNORECASE | re.DOTALL,
)

BRIEF = """You are auditing a dependency inventory. For each item you are given a
dossier: what the dependency does, how many of its symbols this codebase calls,
how many transitive modules it brings in, its upstream health, and how the value
it produces is used.

For each item decide whether to REPLACE it with an in-house implementation, or to
KEEP the dependency. Justify each decision.

Answer with one line per item, in exactly this form:

    ITEM: <id> | DECISION: <KEEP or REPLACE> | WHY: <your justification>
"""


def load_cases(path):
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#"):
                rows.append(json.loads(line))
    if not rows:
        sys.exit(f"no cases parsed from {path} — refusing to report a score over an empty set")
    # Fail closed on a scope that would make an axis vacuous. A reason denominator
    # of 0 prints "reason 1.000" forever while measuring nothing — the class this
    # harness has shipped four times (evals/README.md, harness conventions).
    if not [c for c in rows if c.get("reason_must_match")]:
        sys.exit(f"{path} has no case carrying `reason_must_match` — the reason axis "
                 "would score an empty set; refusing to run")
    if len({c["decision"] for c in rows}) < 2:
        sys.exit(f"{path} has only one distinct decision — a constant answer would "
                 "score 1.000; refusing to run")
    return rows


def build_prompt(cases):
    """The exact text an agent is given — whitelisted fields only."""
    parts = [BRIEF]
    for c in cases:
        d = {k: c[k] for k in PROMPT_FIELDS if k in c}
        parts.append(f"\n--- {d['id']} ---\n{d['dossier']}")
    return "\n".join(parts)


def parse_report(text):
    """Return {id: (decision, why)} for every well-formed ITEM line."""
    out = {}
    for m in LINE_RE.finditer(text):
        out[m.group("id").strip().lower()] = (
            m.group("decision").strip().upper(),
            m.group("why").strip(),
        )
    return out


def names_mechanism(why, pattern):
    return bool(re.search(pattern, why, re.IGNORECASE))


def score(cases, reported):
    rows, decision_hits, reason_hits, reason_n = [], 0, 0, 0
    for c in cases:
        cid = c["id"].lower()
        needs_reason = bool(c.get("reason_must_match"))
        reason_n += needs_reason
        got = reported.get(cid)
        if got is None:
            rows.append({"id": c["id"], "decision": None, "decision_ok": False,
                         "reason_ok": False, "needs_reason": needs_reason,
                         "why": "not reported"})
            continue
        decision, why = got
        d_ok = decision in [a.upper() for a in c["accept"]]
        # Credit the mechanism only when the decision it justifies is right —
        # naming persistence while voting REPLACE is not a correct reason.
        r_ok = bool(needs_reason and d_ok and names_mechanism(why, c["reason_must_match"]))
        decision_hits += d_ok
        reason_hits += r_ok
        rows.append({
            "id": c["id"], "decision": decision, "decision_ok": d_ok, "reason_ok": r_ok,
            "needs_reason": needs_reason,
            "why": "" if d_ok else f"expected one of {c['accept']}",
        })
    n = len(cases)
    return {
        "n": n,
        "reason_n": reason_n,
        "decision": round(decision_hits / n, 3),
        "reason": round(reason_hits / reason_n, 3) if reason_n else 0.0,
        "both": round(
            sum(1 for r in rows if r["decision_ok"] and (r["reason_ok"] or not r["needs_reason"])) / n, 3
        ),
        "rows": rows,
    }


def report_text(res):
    lines = [f"reimplementation-risk score  (n={res['n']}, reason axis n={res['reason_n']})", ""]
    for r in res["rows"]:
        ok = r["decision_ok"] and (r["reason_ok"] or not r["needs_reason"])
        extra = []
        if not r["decision_ok"]:
            extra.append(r["why"] or "wrong decision")
        elif r["needs_reason"] and not r["reason_ok"]:
            extra.append("right call, but the justification never names the disqualifying mechanism")
        lines.append(f"  {'ok  ' if ok else 'MISS'} {r['id']:<16} {r['decision'] or '—':<9} {'; '.join(extra)}")
    lines += [
        "",
        f"  decision accuracy : {res['decision']:.3f}   (both degenerate strategies score 0.500)",
        f"  reason  accuracy  : {res['reason']:.3f}   (over {res['reason_n']} KEEP cases)",
        f"  both              : {res['both']:.3f}   <- the headline number",
    ]
    return "\n".join(lines)


# --- selftest ---------------------------------------------------------------
# Three arms. The scorer is only worth anything if it separates all three, and in
# particular if BOTH degenerate strategies land at 0.500 on decision — otherwise
# the fixture rewards a constant answer and measures nothing while printing a
# plausible number.
RATIO_ONLY = """
ITEM: tlsh_digest | DECISION: REPLACE | WHY: one symbol, zero transitive modules, ~280 lines, stale upstream.
ITEM: slug_id | DECISION: REPLACE | WHY: twelve lines of string munging behind a dependency.
ITEM: tokenizer_bpe | DECISION: REPLACE | WHY: two symbols pulling fourteen modules — worst ratio here.
ITEM: argon2_verify | DECISION: REPLACE | WHY: RFC 9106 has published test vectors, so bit-identity is provable.
ITEM: yaml_config | DECISION: REPLACE | WHY: upstream is archived and we only use a nine-field flat struct.
ITEM: uuid_v4 | DECISION: REPLACE | WHY: one symbol, no transitive modules, trivial formatting.
ITEM: etag_weak | DECISION: REPLACE | WHY: one symbol, nine modules inherited.
ITEM: lru_memo | DECISION: REPLACE | WHY: 120 lines, two symbols.
ITEM: retry_jitter | DECISION: REPLACE | WHY: 90 lines, nine modules.
ITEM: env_bind | DECISION: REPLACE | WHY: reflection over struct tags, 90 lines to replace.
"""

REFUSE_ALL = """
ITEM: tlsh_digest | DECISION: KEEP | WHY: reimplementing a library is risky and we should not roll our own.
ITEM: slug_id | DECISION: KEEP | WHY: risky, better to depend on a maintained library.
ITEM: tokenizer_bpe | DECISION: KEEP | WHY: too complex to reimplement safely.
ITEM: argon2_verify | DECISION: KEEP | WHY: too complex to reimplement safely.
ITEM: yaml_config | DECISION: KEEP | WHY: too complex to reimplement safely.
ITEM: uuid_v4 | DECISION: KEEP | WHY: identifiers are important, do not touch.
ITEM: etag_weak | DECISION: KEEP | WHY: hashing is delicate, keep the library.
ITEM: lru_memo | DECISION: KEEP | WHY: caches are subtle, keep the library.
ITEM: retry_jitter | DECISION: KEEP | WHY: it uses randomness, so treat it as crypto and keep it.
ITEM: env_bind | DECISION: KEEP | WHY: no reason to churn a working dependency.
"""

CORRECT = """
ITEM: tlsh_digest | DECISION: KEEP | WHY: the digest is persisted on every sample and compared against
  4.1M stored digests; an equivalent reimplementation silently returns wrong distances against the
  existing corpus, and re-indexing 4.1M samples is the real cost.
ITEM: slug_id | DECISION: KEEP | WHY: it is a derived primary key that is re-derived on save and used to
  look the stored row up; any transliteration difference orphans existing rows.
ITEM: tokenizer_bpe | DECISION: KEEP | WHY: the stored offsets and the embeddings built from them are only
  meaningful under the tokenizer that produced them; changing it would require re-embedding the corpus.
ITEM: argon2_verify | DECISION: KEEP | WHY: password hashing is on the do-not-reimplement list outright, and
  the stored hashes are re-verified on every login; test vectors do not cover timing side-channels.
ITEM: yaml_config | DECISION: KEEP | WHY: YAML parsing is on the do-not-reimplement list and the input is
  attacker-influenceable; the archived upstream means migrate to a maintained successor, not write one.
ITEM: uuid_v4 | DECISION: REPLACE | WHY: the value is random and stored once, never recomputed for
  comparison, so a different implementation cannot invalidate an existing row.
ITEM: etag_weak | DECISION: REPLACE | WHY: nothing is persisted server-side; the worst case is one extra
  revalidation per client.
ITEM: lru_memo | DECISION: REPLACE | WHY: process-local, bounded, rebuildable, discarded on restart.
ITEM: retry_jitter | DECISION: REPLACE | WHY: the randomness spreads load and carries no security property.
ITEM: env_bind | DECISION: REPLACE | WHY: nothing persisted, nothing on the list, mechanical to replace.
"""


def selftest(cases):
    ratio = score(cases, parse_report(RATIO_ONLY))
    refuse = score(cases, parse_report(REFUSE_ALL))
    good = score(cases, parse_report(CORRECT))
    print("selftest — the scorer must punish BOTH degenerate strategies\n")
    for label, r in (("leverage-ratio-only arm", ratio),
                     ("refuse-everything arm  ", refuse),
                     ("correct arm            ", good)):
        print(f"  {label}: decision {r['decision']:.3f}  reason {r['reason']:.3f}  both {r['both']:.3f}")
    problems = []
    if good["both"] != 1.0:
        problems.append("the correct arm should score 1.000 on both")
    if ratio["decision"] != 0.5:
        problems.append(f"ratio-only should score exactly 0.500 on decision, got {ratio['decision']}")
    if refuse["decision"] != 0.5:
        problems.append(f"refuse-everything should score exactly 0.500 on decision, got {refuse['decision']}")
    if refuse["reason"] > 0.0:
        problems.append("refuse-everything names no mechanism and should score 0 on reason")
    if ratio["reason"] > 0.0:
        problems.append("ratio-only keeps nothing and should score 0 on reason")
    print()
    if problems:
        for p in problems:
            print(f"  FAIL: {p}")
        return 1
    print("  PASS: the correct arm separates, and neither constant answer beats chance.")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", help="path to the agent's report (Markdown or text)")
    ap.add_argument("--cases", default=DEFAULT_CASES)
    ap.add_argument("--json", help="write the full result as JSON")
    ap.add_argument("--selftest", action="store_true",
                    help="verify the scorer punishes both degenerate strategies")
    ap.add_argument("--print-prompt", action="store_true",
                    help="print the exact text an agent is given (whitelisted fields only)")
    args = ap.parse_args()

    cases = load_cases(args.cases)
    if args.selftest:
        sys.exit(selftest(cases))
    if args.print_prompt:
        print(build_prompt(cases))
        return
    if not args.report:
        ap.error("--report is required (or use --selftest / --print-prompt)")

    with open(args.report, encoding="utf-8") as fh:
        reported = parse_report(fh.read())
    if not reported:
        sys.exit("no 'ITEM: … | DECISION: … | WHY: …' lines found — nothing to score")

    res = score(cases, reported)
    print(report_text(res))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(res, fh, indent=2)
        print(f"\nwrote {args.json}")


if __name__ == "__main__":
    main()
