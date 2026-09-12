#!/usr/bin/env python3
"""Comment-triage eval — can a reviewer tell a REAL review comment from a wrong one?

WHY. This library's audit-accuracy axis was closed at +0.00 across nine instruments, and
the precision instrument behind that verdict was 30 claims scoring 1.00 in BOTH arms. A
measure that saturates has not shown the treatment does nothing — it has shown it cannot
tell. This runner swaps in an external instrument that does not saturate: AACR-Bench
(Alibaba Aone, Apache-2.0), 2,145 expert-labelled review comments over 200 pull requests,
50 repositories and 10 languages, whose negatives were written by other people's reviewers
and models rather than by us.

METHOD. Two arms over the SAME case, the SAME frozen code context and the SAME scoring:
  bare  — the judging prompt alone.
  with  — the judging prompt plus this library's finding-quality rules.
The only difference is the guidance block, so a gap is attributable to it.

THE GUIDANCE IS EXTRACTED FROM THE LIBRARY AT RUN TIME, never mirrored here. A hand-copied
excerpt is a second copy that drifts, and then the arms stop measuring the shipped rules
(evals/README.md: pin anything hand-mirrored). If the headings move, this aborts.

THE TRAP, PRE-REGISTERED. `rules/03` §4 says *default the verdict to REFUTED when the
evidence is ambiguous*. On a balanced set that can raise accuracy purely by making the
model more skeptical — a bias shift, not better discrimination. So per-class recall is a
PRIMARY output here, not a diagnostic, and a lift is only claimable if the with-arm does
not lose more than 0.05 of label-1 recall. See
evals/results/2026-09-12/PRE-REGISTRATION-COMMENT-TRIAGE.md.

SCORING is objective: the model emits `VERDICT: REAL` or `VERDICT: NOT_REAL`. Anything
else is a parse failure, counted and reported — never silently dropped, because a dropped
case picks the denominator by when the failure happened.

Auth: OPENROUTER_API_KEY (env or ./.env). Never printed or committed.
Usage: python3 evals/run-comment-triage.py [--samples N] [--temp T] [--model M]
                                           [--limit N] [--out FILE]
"""
import argparse
import importlib.util
import json
import os
import re
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CASES = os.path.join(ROOT, "evals/cases/comment-triage.jsonl")
RULES = os.path.join(ROOT, "skills/sota/rules/03-audit-findings.md")

_spec = importlib.util.spec_from_file_location(
    "_dr", os.path.join(ROOT, "evals/run-desc-routing.py"))
_dr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_dr)


def extract(md, start_heading, stop_headings):
    """Pull one section out of the shipped rules file. Aborts if the heading is gone."""
    lines = md.splitlines()
    try:
        i = next(n for n, l in enumerate(lines) if l.startswith(start_heading))
    except StopIteration:
        sys.exit(f"heading {start_heading!r} not found in {RULES} — the guidance this eval "
                 f"pastes has moved. Fix the anchor rather than measuring an empty arm.")
    out = []
    for l in lines[i:]:
        if out and any(l.startswith(h) for h in stop_headings):
            break
        out.append(l)
    return "\n".join(out).strip()


def guidance():
    md = open(RULES, encoding="utf-8").read()
    ev = extract(md, "## 2. Evidence standard", ["## 3.", "## 4.", "## 5."])
    ad = extract(md, "## 4. Adversarial verification", ["## 5."])
    block = f"{ev}\n\n{ad}"
    if len(block) < 2000:
        sys.exit(f"extracted guidance is only {len(block)} chars — an arm that cannot see "
                 f"the treatment scores a structural +0.00 (sota-llm-engineering rules/01).")
    return block


def build_prompt(case, with_rules):
    head = (
        "You are reviewing a code-review comment that someone left on a pull request.\n"
        "Decide whether the comment identifies a REAL problem in the code shown.\n\n"
        "REAL      = the comment is correct and worth acting on.\n"
        "NOT_REAL  = the comment is wrong, does not apply to this code, restates the "
        "obvious, or asserts something the code does not do.\n"
    )
    body = (
        f"\nFile: {case['path']}  (lines {case['from_line']}-{case['to_line']})\n"
        f"Language: {case['lang']}\n\n"
        f"--- CODE (line-numbered, at the reviewed commit) ---\n{case['code']}\n"
        f"--- END CODE ---\n\n"
        f"--- REVIEW COMMENT ---\n{case['note']}\n--- END COMMENT ---\n"
    )
    rules = ""
    if with_rules:
        rules = ("\nApply the following review standards when deciding:\n\n"
                 "<standards>\n" + guidance() + "\n</standards>\n")
    tail = ("\nAnswer with one line of reasoning, then a final line exactly of the form:\n"
            "VERDICT: REAL\nor\nVERDICT: NOT_REAL\n")
    return head + rules + body + tail


VERDICT = re.compile(r"VERDICT:\s*(REAL|NOT_REAL)", re.I)


def parse(text):
    m = VERDICT.findall(text or "")
    if not m:
        return None
    return m[-1].upper() == "REAL"


def call(model, key, prompt, temp, tries=4):
    body = json.dumps({"model": model,
                       "messages": [{"role": "user", "content": prompt}],
                       "temperature": temp}).encode()
    for attempt in range(tries):
        try:
            req = urllib.request.Request(
                "https://openrouter.ai/api/v1/chat/completions", data=body,
                headers={"Authorization": f"Bearer {key}",
                         "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=180) as r:
                d = json.load(r)
            return d["choices"][0]["message"]["content"] or ""
        except Exception as e:
            if attempt == tries - 1:
                sys.exit(f"model call failed after {tries} tries: {e!r}\n"
                         f"Aborting rather than reporting a rate over a denominator chosen "
                         f"by when the failure happened.")
            time.sleep(3 * (attempt + 1))


def load_cases(path, limit=None):
    cases = []
    for ln in open(path, encoding="utf-8"):
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        cases.append(json.loads(ln))
    if not cases:
        sys.exit(f"no cases in {path} — refusing to report a rate over zero cases.")
    if limit:
        # keep the balance when truncating, or the metric stops being chance-0.500
        good = [c for c in cases if c["label"] == 1][: limit // 2]
        bad = [c for c in cases if c["label"] == 0][: limit // 2]
        cases = good + bad
    return cases


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default=CASES)
    ap.add_argument("--model", default="anthropic/claude-sonnet-4.6")
    ap.add_argument("--samples", type=int, default=3)
    ap.add_argument("--temp", type=float, default=0.7)
    ap.add_argument("--limit", type=int, default=None,
                    help="use only N cases, kept label-balanced (pilot runs)")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    key = _dr.load_env_key()
    cases = load_cases(a.cases, a.limit)

    n_good = sum(1 for c in cases if c["label"] == 1)
    n_bad = len(cases) - n_good
    if n_good != n_bad:
        sys.exit(f"set is not balanced ({n_good} real / {n_bad} not-real) — accuracy would "
                 f"no longer have chance at 0.500, which the thresholds assume.")

    # Void condition 3: assert the arms actually differ before spending anything.
    p_bare = build_prompt(cases[0], False)
    p_with = build_prompt(cases[0], True)
    if p_bare == p_with:
        sys.exit("both arms produce an identical prompt — the delta would be a "
                 "manufactured zero.")
    print(f"guidance block: {len(guidance())} chars | cases: {len(cases)} "
          f"({n_good} real / {n_bad} not-real) | {a.samples}x temp {a.temp}", flush=True)

    res = {"model": a.model, "samples": a.samples, "temp": a.temp,
           "n_cases": len(cases), "cases": {}, "parse_failures": {"bare": 0, "with": 0}}

    for arm, with_rules in (("bare", False), ("with", True)):
        for c in cases:
            prompt = build_prompt(c, with_rules)
            verdicts = []
            for _ in range(a.samples):
                out = call(a.model, key, prompt, a.temp)
                v = parse(out)
                if v is None:
                    res["parse_failures"][arm] += 1
                else:
                    verdicts.append(v)
            rec = res["cases"].setdefault(c["id"], {"label": c["label"],
                                                    "lang": c["lang"],
                                                    "is_ai": c["is_ai_comment"],
                                                    "arms": {}})
            want = bool(c["label"])
            acc = (sum(1 for v in verdicts if v == want) / len(verdicts)) if verdicts else None
            rec["arms"][arm] = {"verdicts": verdicts, "correct": acc}
            print(f"  {arm:4} {c['id']:9} label={c['label']} -> {acc}", flush=True)

    summary = {}
    for arm in ("bare", "with"):
        vals = [r["arms"][arm]["correct"] for r in res["cases"].values()
                if r["arms"][arm]["correct"] is not None]
        pos = [r["arms"][arm]["correct"] for r in res["cases"].values()
               if r["label"] == 1 and r["arms"][arm]["correct"] is not None]
        neg = [r["arms"][arm]["correct"] for r in res["cases"].values()
               if r["label"] == 0 and r["arms"][arm]["correct"] is not None]
        summary[arm] = {
            "accuracy": round(sum(vals) / len(vals), 3) if vals else None,
            "recall_real": round(sum(pos) / len(pos), 3) if pos else None,
            "recall_not_real": round(sum(neg) / len(neg), 3) if neg else None,
        }
    delta = round(summary["with"]["accuracy"] - summary["bare"]["accuracy"], 3)
    summary["delta_accuracy"] = delta
    summary["delta_recall_real"] = round(
        summary["with"]["recall_real"] - summary["bare"]["recall_real"], 3)
    res["summary"] = summary

    print("\n" + "=" * 62)
    for arm in ("bare", "with"):
        s = summary[arm]
        print(f"{arm:5} accuracy {s['accuracy']:.3f} | recall REAL {s['recall_real']:.3f} "
              f"| recall NOT_REAL {s['recall_not_real']:.3f}")
    print(f"DELTA accuracy = {delta:+.3f}   (chance = 0.500)")
    print(f"DELTA recall_real = {summary['delta_recall_real']:+.3f}  "
          f"(registered: a lift needs this >= -0.05)")
    print(f"parse failures: {res['parse_failures']}")

    # Registered readings, printed so the run states its own verdict.
    if max(summary['bare']['accuracy'], summary['with']['accuracy']) >= 0.95:
        print("VOID: an arm is >= 0.95 — saturated, no lift claimable.")
    elif summary["delta_recall_real"] < -0.05 and delta >= 0.05:
        print("READING: threshold shift, NOT better discrimination (registered trap).")
    elif delta >= 0.05:
        print("READING: H1 supported.")
    elif abs(delta) < 0.03:
        print("READING: null.")
    elif delta <= -0.05:
        print("READING: H1 refuted.")
    else:
        print("READING: ambiguous / underpowered.")

    out = a.out or os.path.join(ROOT, "evals/results/2026-09-12/comment-triage.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(res, open(out, "w"), indent=2)
    print("wrote", out)


if __name__ == "__main__":
    main()
