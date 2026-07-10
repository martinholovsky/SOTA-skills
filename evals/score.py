#!/usr/bin/env python3
"""Score an agent's predictions against a golden-set eval case file.

This is a PROTOTYPE regression harness (2026-07-10 audit STRAT-HIGH-2). It does
NOT run an agent — an LLM eval can't run deterministically in CI. You run an
agent (Claude Code, or the API) over the cases yourself, record what it did in a
predictions JSON, and this script scores it. See evals/README.md.

Case files (JSONL, one object per line):
  {"id": "r1", "kind": "routing", "prompt": "...", "expect": ["sota-api-design", ...]}
  {"id": "a1", "kind": "audit", "language": "python", "snippet": "...",
   "expect": ["sql-injection"]}

Predictions file (JSON): { "<case id>": ["<predicted item>", ...], ... }
  routing → the skills the agent actually loaded for that prompt.
  audit   → the finding categories the agent flagged in that snippet.

Metric: per-case recall of the expected set (did the agent load/flag what it
must?), plus precision as an FYI (extras aren't necessarily wrong for routing).
Recall is the load-bearing number: a miss is a real gap.

Usage:  python3 evals/score.py evals/cases/router.jsonl predictions.json
        python3 evals/score.py evals/cases/audit.jsonl  predictions.json
Exit 0 if every case has recall == 1.0 (no misses), else 1.
"""
import json
import sys


def load_cases(path):
    cases = []
    with open(path, encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                cases.append(json.loads(line))
            except json.JSONDecodeError as e:
                sys.exit(f"{path}:{n}: invalid JSON: {e}")
    return cases


def main(argv):
    if len(argv) != 3:
        sys.exit(__doc__)
    cases = load_cases(argv[1])
    preds = json.load(open(argv[2], encoding="utf-8"))

    total_recall = 0.0
    total_prec = 0.0
    any_miss = False
    print(f"{'case':<6} {'recall':>7} {'prec':>6}  misses")
    print("-" * 60)
    for c in cases:
        cid = c["id"]
        expect = set(c.get("expect", []))
        pred = set(preds.get(cid, []))
        if not expect:
            continue
        hit = expect & pred
        recall = len(hit) / len(expect)
        prec = (len(hit) / len(pred)) if pred else 0.0
        total_recall += recall
        total_prec += prec
        misses = sorted(expect - pred)
        if misses:
            any_miss = True
        flag = "" if recall == 1.0 else "  <-- MISS"
        print(f"{cid:<6} {recall:>7.2f} {prec:>6.2f}  {', '.join(misses) or '-'}{flag}")

    n = sum(1 for c in cases if c.get("expect"))
    if n:
        print("-" * 60)
        print(f"mean recall {total_recall / n:.2f}   mean precision {total_prec / n:.2f}"
              f"   ({n} cases)")
    return 1 if any_miss else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
