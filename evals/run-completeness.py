#!/usr/bin/env python3
"""Completeness eval: does the library make the model embed best practices UNPROMPTED?

The routing/audit/freshness evals measure the library's weakest dimensions. This
measures its thesis: given a minimal "build X for my app" prompt (no security /
logging / transport cues), does a with-library model produce a SOTA-complete
implementation from v1 — vs a without-library model that builds "some X"?

Method (clean, raw OpenRouter API — no sota config anywhere):
  - Generate: both arms get the SAME minimal task. The with-library arm ALSO
    gets the relevant skill rules pasted in AND runs the router's BUILD workflow
    — apply the non-negotiables, then self-audit the diff against each rules
    file's Audit checklist and fill every gap (simulating an agent that loaded
    the skills and followed the BUILD process, not just read the rules). Pasting
    rules without the self-audit under-measures the library: the model reads the
    guidance but silently drops peripheral concerns (rate limiting, transport,
    tests); the self-audit step is what closed 0.89 → 0.98. The without arm gets
    nothing.
  - Judge: a DIFFERENT model, BLIND to which arm produced the artifact, scores
    each artifact against the case's fixed rubric of universal best practices
    (present/absent per criterion). Completeness = present / total.
  - Lift = with-recall − without-recall.

Rubric criteria are universal, expert-agreed best practices (authz, validation,
transport, structured logging, error hygiene, tests, ...) — not sota-invented —
so a base model that "just knew" to do them would score high too.

Auth: OPENROUTER_API_KEY (env or ./.env). Never printed/committed.
Usage: python3 evals/run-completeness.py [--build-model M] [--judge-model M] [--out FILE]
"""
import argparse
import json
import os
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CASES = os.path.join(ROOT, "evals/cases/completeness.jsonl")


def key():
    k = os.environ.get("OPENROUTER_API_KEY")
    if k:
        return k
    p = os.path.join(ROOT, ".env")
    if os.path.exists(p):
        for ln in open(p, encoding="utf-8"):
            if ln.strip().startswith("OPENROUTER_API_KEY="):
                return ln.split("=", 1)[1].strip().strip("'\"")
    sys.exit("OPENROUTER_API_KEY not found")


def call(model, prompt, k, max_tokens=8000):
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}],
                       "temperature": 0, "max_tokens": max_tokens}).encode()
    last = None
    for attempt in range(4):  # retry transient network/5xx; large gens can trickle
        try:
            req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=body,
                                         headers={"Authorization": f"Bearer {k}", "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.load(r)["choices"][0]["message"]["content"]
        except Exception as e:  # noqa: BLE001 — retry any transient failure
            last = e
            time.sleep(3 * (attempt + 1))
    raise last


def load_cases():
    return [json.loads(x) for x in open(CASES, encoding="utf-8")
            if x.strip() and not x.startswith("#")]


# Mirrors the router's BUILD workflow (skills/sota/SKILL.md steps 3-4): apply the
# non-negotiables, then self-audit the diff against each Audit checklist and fill
# every gap. This is the forcing function the plain "paste rules" arm omitted.
BUILD_WORKFLOW = (
    "\n\n---\nBUILD PROCESS (follow it): (1) apply the NON-NEGOTIABLES of the "
    "standards above unconditionally. (2) CRITICAL — before finishing, go through "
    "EVERY '## Audit checklist' at the end of the standards above and verify your "
    "code satisfies each item; for any gap (rate limiting, transport/TLS "
    "enforcement, tests, structured logging, idempotency, etc.) ADD it, or state "
    "explicitly why it is out of scope. Do not present incomplete code.\n\nTask: ")


def gen_prompt(case, with_lib):
    if with_lib:
        ctx = "\n\n".join(open(os.path.join(ROOT, s), encoding="utf-8").read() for s in case["skills"])
        return f"Apply the following engineering standards:\n\n{ctx}{BUILD_WORKFLOW}{case['task']}"
    return case["task"]


def judge(artifact, rubric, model, k):
    items = "\n".join(f"- {r['id']}: {r['c']}" for r in rubric)
    prompt = (
        "You are a STRICT, impartial code reviewer. Below is a code artifact and a checklist. "
        "For EACH checklist item, decide whether the artifact GENUINELY addresses it — mark "
        "\"present\" only if it is actually implemented or explicitly handled in the artifact, "
        "not merely a TODO/comment/aspiration, and \"absent\" otherwise. Judge only what is in the "
        f"artifact.\n\nCHECKLIST:\n{items}\n\nARTIFACT:\n```\n{artifact[:100000]}\n```\n\n"
        'Output ONLY a JSON object mapping each item id to "present" or "absent". No prose.')
    txt = call(model, prompt, k, max_tokens=1500)
    s, e = txt.find("{"), txt.rfind("}")
    return json.loads(txt[s:e + 1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build-model", default="anthropic/claude-sonnet-4.6")
    ap.add_argument("--judge-model", default="anthropic/claude-opus-4.8")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    k = key()
    cases = load_cases()
    print(f"build={a.build_model}  judge={a.judge_model}  cases={len(cases)}  "
          f"(clean API, blind judge)\n")
    results, tot_wo, tot_wl = {}, 0.0, 0.0
    for c in cases:
        row = {"rubric_n": len(c["rubric"]), "arms": {}}
        for with_lib in (False, True):
            arm = "with" if with_lib else "without"
            print(f"  {c['id']:16s} {arm:8s} generating…", flush=True)
            # 32k: the self-audit with-arm emits substantially longer output;
            # 16k truncated tests/logging off the end and scored them absent.
            art = call(a.build_model, gen_prompt(c, with_lib), k, max_tokens=32000)
            verdict = judge(art, c["rubric"], a.judge_model, k)
            present = [r["id"] for r in c["rubric"] if verdict.get(r["id"]) == "present"]
            recall = len(present) / len(c["rubric"])
            print(f"  {c['id']:16s} {arm:8s} recall={recall:.2f}  len={len(art)}", flush=True)
            row["arms"][arm] = {"recall": recall, "present": present,
                                "missing": [r["id"] for r in c["rubric"] if r["id"] not in present],
                                "artifact": art}
        wo = row["arms"]["without"]["recall"]
        wl = row["arms"]["with"]["recall"]
        tot_wo += wo
        tot_wl += wl
        results[c["id"]] = row
        print(f"{c['id']:16s} without={wo:.2f}  with={wl:.2f}  lift={wl-wo:+.2f}   "
              f"without-missing: {', '.join(row['arms']['without']['missing']) or '-'}")
    n = len(cases)
    print(f"\nMEAN completeness  without={tot_wo/n:.2f}  with={tot_wl/n:.2f}  "
          f"LIFT={((tot_wl-tot_wo)/n):+.2f}")
    if a.out:
        json.dump(results, open(a.out, "w"), indent=1)
        print(f"saved {a.out}")


if __name__ == "__main__":
    main()
