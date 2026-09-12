#!/usr/bin/env python3
"""Routing-shift eval — ROADMAP 48. Does a session that has settled into one task shape
still route correctly when the work changes shape?

WHY. Four independent observations, none of them a trigger defect: the description matched,
the rule existed, and it was simply not loaded once the work moved. A session typing zsh
one-liners while auditing with three shell rules unloaded; a documentation session that
became campaign execution; a shell-work session that never opened `sota-devsecops/rules/09`
and filed a duplicate-rule proposal as a result; and the review of that proposal, which
checked the gap inside the file the report named and never asked which skill owned the topic.

METHOD. Two arms over the SAME shape-B prompt and the SAME catalogue:
  fresh    — the prompt alone. This is what `run-desc-routing.py` already measures, and it
             is the ceiling.
  shifted  — the prompt preceded by real turns of shape-A work.
The only difference is the conversation in front of the question, so a gap is attributable
to it. ROUTING-SHIFT = fresh − shifted.

WHAT IT MEASURES, STATED PLAINLY. An eval has no Skill tool, so this measures **which skill
the model says applies**, not whether it loaded one. That is a proxy. It is the same proxy
`run-desc-routing.py` already publishes on, and it is labelled here rather than left to be
read as behaviour.

THE CEILING IS THE RISK. `run-desc-routing`'s fresh arm scores ~0.90, so the detectable range
is narrow: a null could be a real null or a floor effect. **Read the fresh arm before reading
the delta** — if fresh is not clearly above the shifted arm's floor there is nothing to see.

Scoring is objective: exact skill-name match, no judge.

Auth: OPENROUTER_API_KEY (env or ./.env). Never printed or committed.
Usage: python3 evals/run-routing-shift.py [--samples N] [--temp T] [--model M] [--out FILE]
"""
import argparse
import importlib.util
import json
import os
import statistics
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CASES = os.path.join(ROOT, "evals/cases/routing-shift.jsonl")

# Reuse run-desc-routing's catalogue, prompt and scoring rather than copying them: two
# implementations of "what does the catalogue look like" is how the arms of two evals
# silently stop being comparable.
_spec = importlib.util.spec_from_file_location(
    "_dr", os.path.join(ROOT, "evals/run-desc-routing.py"))
_dr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_dr)


def load_cases(path):
    cases = []
    for ln in open(path, encoding="utf-8"):
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        cases.append(json.loads(ln))
    if not cases:
        sys.exit(f"no cases in {path} — refusing to report a rate over zero cases.")
    return cases


def messages(case, items, shifted):
    """The shape-B question, optionally preceded by shape-A work."""
    msgs = []
    if shifted:
        for user, assistant in case["prior"]:
            msgs.append({"role": "user", "content": user})
            msgs.append({"role": "assistant", "content": assistant})
    msgs.append({"role": "user", "content": _dr.build_prompt(items, case["task"])})
    return msgs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default=CASES)
    ap.add_argument("--model", default="anthropic/claude-sonnet-4.6")
    ap.add_argument("--samples", type=int, default=3)
    ap.add_argument("--temp", type=float, default=0.7)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    key = _dr.load_env_key()
    cases = load_cases(a.cases)
    items = _dr.catalogue(False)
    names = [n for n, _ in items]

    # Assert the arms actually differ, the way every ablation here must (rules/12 §1).
    probe = cases[0]
    if messages(probe, items, False) == messages(probe, items, True):
        sys.exit("fresh and shifted arms are identical — every case would score the same "
                 "and the delta would be a manufactured zero. Check `prior` is populated.")
    extra = len(messages(probe, items, True)) - len(messages(probe, items, False))
    print(f"model={a.model}  cases={len(cases)}  samples={a.samples}  temp={a.temp}  "
          f"catalogue={len(items)} skills")
    print(f"  ablation: the shifted arm carries {extra} extra message(s) of prior work\n")

    from _elapsed import note_work
    note_work(len(cases) * 2, "case-arms")

    result = {"model": a.model, "samples": a.samples, "temp": a.temp, "cases": {}}
    agg = {"fresh": [], "shifted": []}
    for c in cases:
        result["cases"][c["id"]] = {"task": c["task"], "expect": c["expect"], "arms": {}}
        for arm, shifted in (("fresh", False), ("shifted", True)):
            picks = []
            for _ in range(a.samples):
                txt = _dr.call(a.model, key, messages(c, items, shifted), a.temp)
                picks.append(_dr.pick_from(txt, names))
            hit = statistics.mean(1.0 if p == c["expect"] else 0.0 for p in picks)
            agg[arm].append(hit)
            result["cases"][c["id"]]["arms"][arm] = {"picks": picks, "correct": hit}
            print(f"  {c['id']:<22} {arm:<8} correct={hit:.2f}  picks={picks}")

    fresh, shifted = statistics.mean(agg["fresh"]), statistics.mean(agg["shifted"])
    result["summary"] = {"fresh": fresh, "shifted": shifted, "routing_shift": fresh - shifted}
    print("\nSUMMARY")
    print(f"  fresh    correct={fresh:.3f}")
    print(f"  shifted  correct={shifted:.3f}")
    print(f"\n  ROUTING-SHIFT (fresh − shifted) = {fresh - shifted:+.3f}")
    print("  Read the FRESH arm first: if it is not clearly above the floor, a small delta "
          "is a ceiling artefact, not a null.")
    print("  This measures which skill the model SAYS applies — a proxy for loading one.")
    if a.out:
        json.dump(result, open(a.out, "w"), indent=1)
        print("saved", a.out)


if __name__ == "__main__":
    main()
