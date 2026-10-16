#!/usr/bin/env python3
"""Intervals for the numbers this harness prints: paired bootstrap, exact McNemar.

Why this exists. Most headline deltas in evals/results/ are points: "LIFT=+0.39" over
seven cases says nothing about how far it could move on a different seven. Only
GATE-ABSORPTION-N3 carried an interval. `sota-llm-engineering` rules/07 section 11
says a delta without an interval is an opinion; this is that rule applied here.

What an interval here means — read before quoting one (evals/README, "Intervals"):
it is a bootstrap over CASES, which are few. It says how much the delta depends on
which cases were in the set. It is not an interval over model samples unless the
runner sampled (--samples > 1), and it never covers judge error.

Stdlib only, deterministic for a given seed. The seed is printed with every interval so
the interval can be re-derived from the saved JSON.

CLI (reads a recorded result, writes nothing):
  python3 evals/_stats.py RESULT.json [--a without] [--b with] [--seed 0]
"""
import argparse
import json
import math
import random
import sys

DEFAULT_SEED = 0
DEFAULT_BOOT = 10000
# Below this many cases a percentile bootstrap is too narrow: n cases admit only
# C(2n-1, n) distinct resamples (10 at n=3), so the interval understates the spread a
# fresh set of cases would show. The printed line says so rather than leaving it to
# the reader. 10 is a convention, not a derived threshold.
FEW_CASES = 10


def _percentile(sorted_xs, q):
    """Linear-interpolated percentile of an already sorted list, q in [0, 1]."""
    if not sorted_xs:
        raise ValueError("percentile of an empty list")
    pos = q * (len(sorted_xs) - 1)
    lo = math.floor(pos)
    hi = math.ceil(pos)
    return sorted_xs[lo] + (sorted_xs[hi] - sorted_xs[lo]) * (pos - lo)


def paired_bootstrap(a, b, n_boot=DEFAULT_BOOT, seed=DEFAULT_SEED, level=0.95):
    """Delta mean(b) - mean(a) over the same cases, with a case-level paired interval.

    a[i] and b[i] must be the SAME case. Resampling draws case indices, so each draw
    keeps a case's two arms together — that pairing is what makes the interval narrow
    when the arms move together, and scrambling it is a known-bad in test_scoring.py.
    """
    if len(a) != len(b):
        raise ValueError(f"paired arms differ in length: {len(a)} vs {len(b)}")
    n = len(a)
    if n == 0:
        raise ValueError("no cases: refusing to report an interval over nothing")
    diffs = [y - x for x, y in zip(a, b)]
    rng = random.Random(seed)
    boots = sorted(sum(diffs[rng.randrange(n)] for _ in range(n)) / n
                   for _ in range(n_boot))
    alpha = (1 - level) / 2
    return {"point": sum(diffs) / n, "lo": _percentile(boots, alpha),
            "hi": _percentile(boots, 1 - alpha), "n": n, "seed": seed,
            "n_boot": n_boot, "level": level, "paired": True}


def bootstrap_mean(xs, n_boot=DEFAULT_BOOT, seed=DEFAULT_SEED, level=0.95):
    """One arm's mean with a case-level bootstrap interval (for unpaired reporting)."""
    n = len(xs)
    if n == 0:
        raise ValueError("no cases: refusing to report an interval over nothing")
    rng = random.Random(seed)
    boots = sorted(sum(xs[rng.randrange(n)] for _ in range(n)) / n for _ in range(n_boot))
    alpha = (1 - level) / 2
    return {"point": sum(xs) / n, "lo": _percentile(boots, alpha),
            "hi": _percentile(boots, 1 - alpha), "n": n, "seed": seed,
            "n_boot": n_boot, "level": level, "paired": False}


def mcnemar_exact(a_pass, b_pass):
    """Exact two-sided McNemar test on paired pass/fail outcomes.

    Only discordant cases carry information: b01 = a passed and b failed, b10 = a failed
    and b passed. Under H0 they are Binomial(b01 + b10, 0.5).
    """
    if len(a_pass) != len(b_pass):
        raise ValueError(f"paired arms differ in length: {len(a_pass)} vs {len(b_pass)}")
    b01 = sum(1 for x, y in zip(a_pass, b_pass) if x and not y)
    b10 = sum(1 for x, y in zip(a_pass, b_pass) if y and not x)
    m = b01 + b10
    if m == 0:
        return {"a_only": 0, "b_only": 0, "p": 1.0, "n": len(a_pass)}
    tail = sum(math.comb(m, i) for i in range(min(b01, b10) + 1)) / 2 ** m
    return {"a_only": b01, "b_only": b10, "p": min(1.0, 2 * tail), "n": len(a_pass)}


def format_interval(r, unit="cases"):
    """One line, the shape the runners print beside a headline number."""
    pct = round(r["level"] * 100)
    kind = "paired bootstrap" if r["paired"] else "unpaired bootstrap"
    label, f = ("delta", "+.3f") if r["paired"] else ("mean", ".3f")
    warn = (f"  (n<{FEW_CASES}: too few {unit} for a bootstrap — read the interval as a "
            "floor on the uncertainty)") if r["n"] < FEW_CASES else ""
    return (f"{label} {r['point']:{f}}  {pct}% CI [{r['lo']:{f}}, {r['hi']:{f}}]  "
            f"n={r['n']} {unit}  {kind} seed={r['seed']}{warn}")


def _arm_values(obj, arm):
    """Per-case recall for one arm, from either recorded result shape.

    run-completeness writes {case_id: {"arms": {...}}, "_meta": {...}};
    run-competitors writes {"cases": {case_id: {"arms": {...}}}, ...}.
    """
    cases = obj["cases"] if isinstance(obj.get("cases"), dict) else {
        k: v for k, v in obj.items() if not k.startswith("_") and isinstance(v, dict)}
    out = {}
    for cid, row in cases.items():
        arms = row.get("arms", {})
        if arm in arms and "recall" in arms[arm]:
            out[cid] = arms[arm]["recall"]
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("result", help="a recorded run-completeness or run-competitors JSON")
    ap.add_argument("--a", default="without", help="baseline arm (default: without)")
    ap.add_argument("--b", default="with", help="treated arm (default: with)")
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--boot", type=int, default=DEFAULT_BOOT)
    a = ap.parse_args()
    obj = json.load(open(a.result, encoding="utf-8"))
    if obj.get("complete") is False:
        sys.exit(f"REFUSING: {a.result} says complete=false "
                 f"({obj.get('cases_done')}/{obj.get('cases_total')} cases)")
    va, vb = _arm_values(obj, a.a), _arm_values(obj, a.b)
    shared = sorted(set(va) & set(vb))
    # Denominator first: a pairing over fewer cases than either arm holds is a
    # different measurement, and the reader has to see that before the interval.
    print(f"cases: {a.a}={len(va)}  {a.b}={len(vb)}  paired={len(shared)}")
    if not shared:
        sys.exit("FAIL: no case carries both arms — nothing to pair")
    r = paired_bootstrap([va[c] for c in shared], [vb[c] for c in shared],
                         n_boot=a.boot, seed=a.seed)
    print(f"{a.b} - {a.a}: " + format_interval(r))
    for arm, v in ((a.a, va), (a.b, vb)):
        print(f"  {arm}: " + format_interval(bootstrap_mean([v[c] for c in shared],
                                                            n_boot=a.boot, seed=a.seed)))


if __name__ == "__main__":
    main()
