#!/usr/bin/env python3
"""Audit PRECISION eval — does the auditor uphold a plausible-but-wrong finding?

Every other audit eval here measures RECALL (find the real vulnerability) and
saturates at +0.00 both arms. This one measures the opposite failure, which is
what an adversarial refutation pass is for: given a claimed finding, decide
whether it actually holds.

Cases (`cases/finding-adjudication.jsonl`): 30 code+claim pairs, 15 genuine and
15 plausible-but-wrong. The wrong half fails for six distinct reasons (upstream
guard, unreachable code, inflated severity, misread mechanism, already
mitigated, behaviour that is actually correct), so an arm cannot win by
pattern-matching a single refutation shape.

Arms:
  without-library       — the task only
  with-library          — + sota/rules/01-audit-methodology.md (which contains
                          §6 "Adversarial verification") + the router principles
  with-library-ablated  — the same MINUS §6, isolating the refutation section

Reported metrics: overall accuracy, plus SPECIFICITY (share of the 15 false
claims correctly refuted) and SENSITIVITY (share of the 15 real ones upheld).
Specificity is the load-bearing number — refutation should raise it without
costing sensitivity. An arm that refutes everything scores 1.00 specificity and
0.00 sensitivity, which is why both are printed.

Usage:
  python3 evals/run-adjudication.py --samples 3 --temp 0.7
"""
import argparse
import importlib.util
import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("run_clean", os.path.join(_HERE, "run-clean.py"))
run_clean = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(run_clean)
ROOT = run_clean.ROOT

# Match the section by its TITLE, not its number. The first version hardcoded
# "## 6. Adversarial verification" / "## 7. Report structure"; inserting the
# decision-ledger section renumbered both and the ablation stopped matching. The
# guard in library_context() caught it (it aborts rather than silently returning
# an unablated corpus) — keep that guard, and stop depending on the numbering.
SEC_ABLATE_TITLE = "Adversarial verification"
SEC_NEXT_TITLE = "Report structure"


def _section_bounds(text, title, next_title):
    """Byte offsets of a '## N. <title>' section, whatever N happens to be."""
    import re
    a = re.search(rf"^## \d+\. {re.escape(title)}", text, re.M)
    b = re.search(rf"^## \d+\. {re.escape(next_title)}", text, re.M)
    return (a.start() if a else -1), (b.start() if b else -1)

# NEUTRAL by design. An earlier draft listed the ways a claim can fail (misread
# mechanism, upstream guard, unreachable, already mitigated, inflated severity) —
# which is §6's content, handed to every arm for free. That version saturated at
# 1.00 on all three arms. The framing must state the task and nothing more, or the
# eval measures the prompt rather than the library.
FRAMING = (
    "You are the second reviewer on a security audit. For each case you are given a "
    "code snippet and a CLAIMED finding written by the first reviewer.\n"
    "Answer UPHELD if you would ship the claim as written, or REFUTED if you would not."
)


def library_context(ablate=False):
    meth = open(os.path.join(ROOT, "skills/sota/rules/01-audit-methodology.md"),
                encoding="utf-8").read()
    if ablate:
        i, j = _section_bounds(meth, SEC_ABLATE_TITLE, SEC_NEXT_TITLE)
        if i < 0 or j < 0 or j <= i:
            raise SystemExit(
                f"ablation target section not found (looked for '## N. {SEC_ABLATE_TITLE}' "
                f"through '## N. {SEC_NEXT_TITLE}'). Refusing to run: a silent no-op "
                f"ablation would report a fake +0.00 contribution.")
        removed = meth[i:j]
        meth = meth[:i] + meth[j:]
        if SEC_ABLATE_TITLE in meth or len(removed) < 500:
            raise SystemExit(f"ablation removed only {len(removed)} chars or left the "
                             f"section behind — refusing to run.")
    router = open(os.path.join(ROOT, "skills/sota/SKILL.md"), encoding="utf-8").read()
    i, j = router.find("## Operating principles"), router.find("## Routing table")
    return f"{router[i:j].strip()}\n\n---\n\n{meth}"


def build_prompt(cases, with_lib, ablate):
    keep = ("id", "language", "snippet", "claim")
    tasks = json.dumps([{k: v for k, v in c.items() if k in keep} for c in cases], indent=1)
    for c in cases:  # structural guard (see run-clean.build_prompt)
        assert "snippet" in c and "claim" in c, f"{c['id']}: missing input field"
    lib = (f"\n\nApply the following audit methodology:\n\n{library_context(ablate)}\n\n"
           if with_lib else "\n\nUse only your own security judgement.\n\n")
    return (f"{FRAMING}{lib}Cases:\n{tasks}\n\n"
            'Output ONLY a JSON object mapping each case id to exactly "UPHELD" or '
            '"REFUTED". No prose, no code fence.')


def score(cases, preds):
    tp = fp = 0.0
    real = [c for c in cases if c["expect"] == ["UPHELD"]]
    fake = [c for c in cases if c["expect"] == ["REFUTED"]]
    wrong = []
    for c in cases:
        got = str(preds.get(c["id"], "")).strip().upper()
        ok = got == c["expect"][0]
        if not ok:
            wrong.append(f"{c['id']}({c['expect'][0][:3]}→{got[:3] or '??'})")
        if c in real and ok:
            tp += 1
        if c in fake and ok:
            fp += 1
    return {"accuracy": (tp + fp) / len(cases),
            "sensitivity": tp / len(real), "specificity": fp / len(fake),
            "wrong": wrong}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default=os.path.join(ROOT, "evals/cases/finding-adjudication.jsonl"))
    ap.add_argument("--model", default="anthropic/claude-sonnet-4.6")
    ap.add_argument("--samples", type=int, default=1)
    ap.add_argument("--temp", type=float, default=0.0)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    key = run_clean.load_env_key()
    cases = run_clean.load_cases(a.cases)
    n_real = sum(1 for c in cases if c["expect"] == ["UPHELD"])
    print(f"model={a.model}  cases={len(cases)} ({n_real} real / {len(cases)-n_real} false)  "
          f"samples={a.samples}  temp={a.temp}\n")

    result = {"_meta": {"model": a.model, "cases": len(cases), "samples": a.samples,
                        "temp": a.temp, "metric": "audit precision"}}
    for name, with_lib, ablate in [("without-library", False, False),
                                   ("with-library", True, False),
                                   ("with-library-ablated", True, True)]:
        prompt = build_prompt(cases, with_lib, ablate)
        runs, last = [], {}
        for _ in range(a.samples):
            preds = run_clean.call(a.model, key, prompt, temp=a.temp)
            s = score(cases, preds)
            runs.append(s)
            last = {"predictions": preds, **s}
        mean = {k: sum(r[k] for r in runs) / len(runs)
                for k in ("accuracy", "sensitivity", "specificity")}
        result[name] = {**mean, "runs": [{k: r[k] for k in mean} for r in runs],
                        "wrong": last["wrong"], "predictions": last["predictions"]}
        print(f"{name:22s} acc={mean['accuracy']:.2f}  "
              f"specificity(refute the false)={mean['specificity']:.2f}  "
              f"sensitivity(keep the real)={mean['sensitivity']:.2f}")
        print(f"{'':22s} wrong: {last['wrong'] or '(none)'}")

    base = result["without-library"]
    print(f"\nSPECIFICITY lift, full library = "
          f"{result['with-library']['specificity'] - base['specificity']:+.2f}")
    print(f"SPECIFICITY lift, ablated (-§6) = "
          f"{result['with-library-ablated']['specificity'] - base['specificity']:+.2f}")
    print(f"§6 CONTRIBUTION = "
          f"{result['with-library']['specificity'] - result['with-library-ablated']['specificity']:+.2f}")
    if a.out:
        json.dump(result, open(a.out, "w"), indent=1)
        print(f"saved {a.out}")


if __name__ == "__main__":
    main()
