#!/usr/bin/env python3
"""Competitor benchmark: SOTA vs. named competing guidance libraries, same task.

The completeness eval (run-completeness.py) is SOTA vs. an *unguided* model. This
adds competitor arms so we can say — with hard numbers — whether SOTA's guidance
produces more complete code than the most popular competing skill/rules libraries
on the same "build X" tasks. It reuses the SAME cases, rubric, and blind judge.

FAIRNESS — content-only, level playing field (deliberately conservative for SOTA):
  - Every GUIDED arm (SOTA and each competitor) gets the SAME neutral build wrapper
    ("apply this guidance, then review your code for completeness against it, don't
    ship incomplete code"). The wrapper names NO specific concern (naming e.g. rate
    limiting would leak SOTA's non-negotiables to competitors), so the ONLY variable
    is the pasted guidance content.
  - This does NOT give SOTA its self-audit forcing function (which lifts it to ~0.99
    in its own deployment, run-completeness.py). So SOTA's number here is a
    CONTENT-ONLY measure — if SOTA still wins, it is the guidance, not the method.
  - Each competitor's bundle is its best-matching content for "build a secure
    Python/FastAPI backend feature" (evals/cases/competitors.json), at a token
    budget comparable to a SOTA per-case arm. Competitor content is NOT vendored;
    pass --competitors-dir pointing at clones at the pinned SHAs.
  - Judge is opus-4.8, blind to which arm produced each artifact.

Auth: OPENROUTER_API_KEY (env or ./.env). Never printed/committed.
Usage: python3 evals/run-competitors.py --competitors-dir DIR [--build-model M]
       [--judge-model M] [--only ECC,claude-skills] [--out FILE]
"""
import argparse
import json
import os
import sys
import importlib.util

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Reuse the completeness harness (call/judge/load_cases/principle5).
_spec = importlib.util.spec_from_file_location(
    "run_completeness", os.path.join(ROOT, "evals/run-completeness.py"))
_rc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_rc)

MANIFEST = os.path.join(ROOT, "evals/cases/competitors.json")

# Neutral, concern-agnostic build wrapper — identical for every guided arm.
NEUTRAL_BUILD = (
    "\n\n---\nBUILD PROCESS (follow it): apply the guidance above while writing the "
    "code. Before you finish, review your implementation against that guidance and "
    "general production best practice, and ADD anything it implies you are missing — "
    "or state explicitly why it is out of scope. Do not present incomplete code."
    "\n\nTask: ")


def read(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def sota_bundle(case):
    """SOTA's per-case content: router principle 5 + the case's rules files."""
    ctx = "\n\n".join(read(os.path.join(ROOT, s)) for s in case["skills"])
    return f"{_rc.principle5()}\n\n{ctx}"


def competitor_bundle(comp, cdir):
    """Concatenate a competitor's manifest files from the local clone."""
    base = os.path.join(cdir, os.path.basename(comp["repo"]))
    parts = []
    for rel in comp["files"]:
        p = os.path.join(base, rel)
        if not os.path.exists(p):
            sys.exit(f"missing competitor file: {p}\n(clone {comp['repo']} at {comp['sha']} into {cdir})")
        parts.append(f"===== {rel} =====\n{read(p)}")
    return "\n\n".join(parts)


def guided_prompt(bundle, task):
    return (f"Apply the following engineering guidance:\n\n{bundle}{NEUTRAL_BUILD}{task}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--competitors-dir", required=True,
                    help="dir containing clones (ECC/, claude-skills/, awesome-cursorrules/)")
    ap.add_argument("--build-model", default="anthropic/claude-sonnet-4.6")
    ap.add_argument("--judge-model", default="anthropic/claude-opus-4.8")
    ap.add_argument("--only", default=None, help="comma list of competitor keys to run")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    k = _rc.key()
    cases = _rc.load_cases()
    manifest = json.load(open(MANIFEST, encoding="utf-8"))["competitors"]
    comps = list(manifest)
    if a.only:
        comps = [c for c in comps if c in a.only.split(",")]
    arms = ["without", "sota"] + comps
    print(f"build={a.build_model}  judge={a.judge_model}  cases={len(cases)}  "
          f"arms={arms}  (content-only, blind judge)\n")

    results, totals = {}, {arm: 0.0 for arm in arms}
    for c in cases:
        row = {"rubric_n": len(c["rubric"]), "arms": {}}
        for arm in arms:
            if arm == "without":
                prompt = c["task"]
            elif arm == "sota":
                prompt = guided_prompt(sota_bundle(c), c["task"])
            else:
                prompt = guided_prompt(competitor_bundle(manifest[arm], a.competitors_dir), c["task"])
            print(f"  {c['id']:16s} {arm:20s} generating…", flush=True)
            art = _rc.call(a.build_model, prompt, k, max_tokens=32000, temp=0.0)
            verdict = _rc.judge(art, c["rubric"], a.judge_model, k)
            present = [r["id"] for r in c["rubric"] if verdict.get(r["id"]) == "present"]
            recall = len(present) / len(c["rubric"])
            totals[arm] += recall
            row["arms"][arm] = {"recall": recall, "present": present,
                                "missing": [r["id"] for r in c["rubric"] if r["id"] not in present],
                                "artifact_len": len(art)}
            print(f"  {c['id']:16s} {arm:20s} recall={recall:.2f}", flush=True)
        results[c["id"]] = row
        line = "  ".join(f"{arm}={row['arms'][arm]['recall']:.2f}" for arm in arms)
        print(f"{c['id']:16s} {line}")
    n = len(cases)
    print("\nMEAN completeness by arm:")
    for arm in arms:
        m = totals[arm] / n
        delta = f"  (vs sota {m - totals['sota']/n:+.2f}, vs unguided {m - totals['without']/n:+.2f})" if arm not in ("without", "sota") else ""
        print(f"  {arm:20s} {m:.3f}{delta}")
    if a.out:
        json.dump({"arms": arms, "cases": results,
                   "means": {arm: totals[arm]/n for arm in arms}}, open(a.out, "w"), indent=1)
        print(f"saved {a.out}")


if __name__ == "__main__":
    main()
