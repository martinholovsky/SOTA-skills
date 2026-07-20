#!/usr/bin/env python3
"""Open-ended (no-vocabulary) silent-control-failure eval, LLM-judged.

Why this exists alongside `run-clean.py --cases cases/silent-failure.jsonl`:
that run hands both arms a 19-slug VOCABULARY that already enumerates the
taxonomy, which primes the task heavily — it measures CLASSIFICATION once you
know the classes exist. Both arms scored 1.00 with the library, so the
vocabulary run cannot tell whether rules/10 adds anything.

This run removes the taxonomy. Each arm gets the same neutral audit framing
("report any control that appears active but has no effect") and must produce a
free-form one-line mechanism per case. A separate blind judge scores each answer
against the case's `reference` mechanism. That measures DISCOVERY, which is what
a real audit does.

Three arms (each a single batched call, so the library context is paid once):
  without-library            — task only
  with-library               — + all sota-code-security/rules/*.md
  with-library-ablated       — + the same MINUS rules/10 (isolates the new file)

Judging is blind: the judge sees snippet + reference + answer, never the arm.

Usage:
  python3 evals/run-silent-open.py
  python3 evals/run-silent-open.py --samples 3 --temp 0.7 --out results.json
Exit 0 always (it reports; scoring is the output, not a gate).
"""
import argparse
import json
import os
import sys

import importlib.util

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("run_clean", os.path.join(_HERE, "run-clean.py"))
run_clean = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(run_clean)

ROOT = run_clean.ROOT

FRAMING = (
    "You are auditing code. For each snippet, report whether it contains a control, "
    "safeguard, check, or test that APPEARS to be active but in fact has no effect — "
    "so that a broken system and a working system would look identical from outside.\n"
    "Answer for every case with ONE line: the specific mechanism by which the control "
    "is inert (what looks enabled, and why nothing happens). If the control instead "
    "fails loudly and observably (it raises, logs an error, or emits a metric when it "
    "cannot do its job), answer exactly NOT-SILENT. If there is no issue, answer NONE."
)

JUDGE = (
    "You are grading a code-audit answer. You are given a code snippet, the REFERENCE "
    "mechanism (ground truth), and a CANDIDATE answer.\n\n"
    "Score HIT only if the candidate identifies the SAME mechanism as the reference — "
    "the same reason the control is inert (or, when the reference says NOT a silent "
    "failure, the candidate agrees the failure is loud/observable). Naming a different "
    "real problem in the snippet is a MISS. Vague gestures ('this looks unsafe') are a "
    "MISS. Different wording for the same mechanism is a HIT.\n\n"
    "Output ONLY a JSON object mapping each case id to \"HIT\" or \"MISS\". No prose."
)


def build_task_prompt(cases, with_lib, ablate):
    strip = ("expect", "skill", "reference", "kind")
    tasks = json.dumps([{k: v for k, v in c.items() if k not in strip} for c in cases], indent=1)
    if with_lib:
        lib = (f"\n\nApply the following security guidance:\n\n"
               f"{run_clean.audit_library_context(ablate)}\n\n")
    else:
        lib = "\n\nUse only your own security knowledge.\n\n"
    return (f"{FRAMING}{lib}Cases:\n{tasks}\n\n"
            'Output ONLY a JSON object mapping each case id to your one-line answer '
            'string. No prose, no code fence.')


def build_judge_prompt(cases, answers):
    items = [{"id": c["id"], "snippet": c["snippet"], "reference": c["reference"],
              "candidate": str(answers.get(c["id"], ""))} for c in cases]
    return f"{JUDGE}\n\nItems:\n{json.dumps(items, indent=1)}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default=os.path.join(ROOT, "evals/cases/silent-failure.jsonl"))
    ap.add_argument("--model", default="anthropic/claude-sonnet-4.6")
    ap.add_argument("--judge-model", default="anthropic/claude-opus-4.8",
                    help="a DIFFERENT model from --model keeps the judge independent")
    ap.add_argument("--samples", type=int, default=1)
    ap.add_argument("--temp", type=float, default=0.0)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    key = run_clean.load_env_key()
    cases = run_clean.load_cases(a.cases)
    print(f"model={a.model}  judge={a.judge_model}  cases={len(cases)}  "
          f"samples={a.samples}  temp={a.temp}  (open-ended, no vocabulary)\n")

    arms = [("without-library", False, False),
            ("with-library", True, False),
            ("with-library-ablated", True, True)]
    result = {"_meta": {"model": a.model, "judge": a.judge_model, "cases": len(cases),
                        "samples": a.samples, "temp": a.temp, "design": "open-ended"}}
    for name, with_lib, ablate in arms:
        prompt = build_task_prompt(cases, with_lib, ablate)
        scores, last = [], {}
        for _ in range(a.samples):
            answers = run_clean.call(a.model, key, prompt, temp=a.temp)
            verdicts = run_clean.call(a.judge_model, key,
                                      build_judge_prompt(cases, answers), temp=0.0)
            hits = sum(1 for c in cases if str(verdicts.get(c["id"], "")).upper() == "HIT")
            scores.append(hits / len(cases))
            last = {"answers": answers, "verdicts": verdicts,
                    "misses": [c["id"] for c in cases
                               if str(verdicts.get(c["id"], "")).upper() != "HIT"]}
        mean = sum(scores) / len(scores)
        result[name] = {"recall": mean, "recalls": scores, **last}
        spread = (f"  (min {min(scores):.2f}, max {max(scores):.2f}, n={len(scores)})"
                  if a.samples > 1 else "")
        print(f"{name:22s} recall={mean:.2f}{spread}  misses: {last['misses'] or '(none)'}")

    base = result["without-library"]["recall"]
    print(f"\nLIFT full library      = {result['with-library']['recall'] - base:+.2f}")
    print(f"LIFT ablated (-rules/10) = {result['with-library-ablated']['recall'] - base:+.2f}")
    print(f"rules/10 CONTRIBUTION    = "
          f"{result['with-library']['recall'] - result['with-library-ablated']['recall']:+.2f}")
    if a.out:
        json.dump(result, open(a.out, "w"), indent=1)
        print(f"saved {a.out}")


if __name__ == "__main__":
    main()
