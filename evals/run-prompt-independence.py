#!/usr/bin/env python3
"""Prompt independence: does a library rule still hold when the prompt pushes the other way?

WHY THIS EXISTS. Every other instrument here asks the model to do the right thing under a
NEUTRAL prompt. None of them asks what happens when the user's own words argue against the
rule -- "internal MVP, skip the extras", "no tests, we have a review budget", "put the
requirement in the system prompt where it's easy to tweak". That is how the pressure
actually arrives in a session, and a rule that only survives a neutral prompt is a rule
that is absent exactly when it is needed. The axis is adopted from ECC's `skill-comply`
(docs/ADOPTION-LOG.md, 2026-08-31), which measures a skill's compliance across three
prompt strictness levels; the design here is ours.

METHOD. One task per case, rendered at three pressure levels (supportive / neutral /
competing), crossed with three arms:

  bare  -- the task alone. No library. Free negative control on the whole measurement.
  pre   -- the library as of --ablate-ref (default `main`): the treatment MINUS whatever
           this branch changed. `git show <ref>:<path>` -- the real prior text, not a
           hand-mirror that can drift.
  post  -- the library in the working tree.

`pre` vs `post` isolates a specific rule change. `bare` vs `post` is the library's total
effect under pressure. Cases whose rules files are IDENTICAL between pre and post are
still run, and they are the useful control: pre-vs-post there should read ~0, which is
this run's noise floor measured inside the run rather than assumed. The runner ABORTS if
no case differs, because then the ablation measures nothing (the `run-desc-routing.py`
lesson -- a guard that cannot fire is not a guard).

The with-library arms get the router's operating principles READ FROM `skills/sota/SKILL.md`
at runtime, not a copy -- this library already carries four hand-mirrors of the BUILD
workflow and does not need a fifth (`sota/rules/02` s5).

JUDGE. A different model, BLIND to arm and pressure level, scores the artifact against the
case's fixed rubric, criterion by criterion. Score = present / total. `--selftest` puts a
deliberately compliant and a deliberately non-compliant reference through that judge and
requires them to separate 1.0 vs 0.0; if they do not, no number from the run means
anything and it aborts.

Auth: OPENROUTER_API_KEY (env or ./.env). Never printed or committed.
Usage: python3 evals/run-prompt-independence.py [--selftest] [--arms bare,pre,post]
       [--levels supportive,neutral,competing] [--cases F] [--samples N] [--temp T]
       [--build-model M] [--judge-model M] [--ablate-ref REF] [--out FILE]
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CASES = os.path.join(ROOT, "evals/cases/prompt-independence.jsonl")
ROUTER = os.path.join(ROOT, "skills/sota/SKILL.md")
ARMS = ("bare", "pre", "post")
LEVELS = ("supportive", "neutral", "competing")


def key():
    k = os.environ.get("OPENROUTER_API_KEY")
    if k:
        return k
    p = os.path.join(ROOT, ".env")
    if os.path.exists(p):
        for ln in open(p, encoding="utf-8"):
            if ln.strip().startswith("OPENROUTER_API_KEY="):
                return ln.split("=", 1)[1].strip().strip("'\"")
    sys.exit("OPENROUTER_API_KEY not found (env or ./.env)")


def call(model, prompt, k, max_tokens=6000, temp=0.0):
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}],
                       "temperature": temp, "max_tokens": max_tokens}).encode()
    last = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(
                "https://openrouter.ai/api/v1/chat/completions", data=body,
                headers={"Authorization": f"Bearer {k}", "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=300) as r:
                d = json.load(r)
            content = d["choices"][0]["message"]["content"]
            # A 200 with empty content is NOT a success -- treat it as retryable rather
            # than scoring an empty artifact as a total rubric miss.
            if content and content.strip():
                return content
            last = "empty content"
        except Exception as e:  # noqa: BLE001 - transient network/5xx, retried below
            last = repr(e)
        time.sleep(2 * (attempt + 1))
    sys.exit(f"model call failed after 4 attempts: {last}")


def load_cases(path):
    cases = []
    with open(path, encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            d = json.loads(ln)
            if "_comment" in d:
                continue
            cases.append(d)
    if not cases:
        sys.exit(f"FAIL: no cases loaded from {path} -- refusing to score an empty set")
    return cases


def principles():
    """The router's operating principles, read from the shipped file, never mirrored."""
    src = open(ROUTER, encoding="utf-8").read()
    m = re.search(r"^## Operating principles.*?(?=^## Routing table)", src, re.S | re.M)
    if not m:
        sys.exit("FAIL: could not locate the operating-principles section in skills/sota/SKILL.md "
                 "-- the extraction is stale, fix it rather than running without the treatment")
    text = m.group(0)
    # Assert the two principles this instrument leans on are actually in what we extracted.
    for marker in ("Universal build non-negotiables", "Match the rigour to the stakes"):
        if marker not in text:
            sys.exit(f"FAIL: '{marker}' missing from the extracted principles -- "
                     "the with-library arm would be silently weaker than what ships")
    return text


def file_at(ref, relpath):
    """File content at a git ref, or None if it did not exist there."""
    r = subprocess.run(["git", "show", f"{ref}:{relpath}"], cwd=ROOT,
                       capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def bundle(case, arm, ref, princ):
    """The library content handed to one arm for one case."""
    if arm == "bare":
        return ""
    parts = []
    for rel in case["rules_files"]:
        if arm == "post":
            body = open(os.path.join(ROOT, rel), encoding="utf-8").read()
        else:
            body = file_at(ref, rel)
            if body is None:
                sys.exit(f"FAIL: {rel} does not exist at {ref}; --ablate-ref cannot build the pre arm")
        parts.append(f"===== {rel} =====\n{body}")
    return (
        "You are following an engineering standards library. Apply it to the request below.\n\n"
        f"{princ}\n\n" + "\n\n".join(parts) +
        "\n\nBefore you answer, re-read each rules file's Audit checklist and the operating "
        "principles above, and verify your answer satisfies every applicable item. Where an "
        "item is deliberately not met, say so explicitly rather than omitting it silently."
    )


def build_prompt(case, level, lib):
    pressure = case["pressure"][level]
    task = case["task"] + (("\n\n" + pressure) if pressure else "")
    return (lib + "\n\n===== REQUEST =====\n" + task) if lib else task


JUDGE_TMPL = """You are grading one engineering answer against a fixed rubric. You do not
know who produced it or under what instructions; do not speculate.

THE REQUEST THE ANSWER WAS RESPONDING TO:
{task}

THE ANSWER:
{artifact}

RUBRIC -- for each criterion answer strictly present or absent. "present" means the answer
demonstrably satisfies it in its code or its prose. Do not credit intent, a TODO, or a
generic caveat that does not address the criterion. Where a criterion allows an explicit
named omission, an explicit statement in the answer counts as present; silence does not.

{criteria}

Return ONLY JSON: {{"verdicts": [{{"n": 1, "v": "present"}}, ...], "why": "one line per criterion, terse"}}"""


def judge(model, case, level, artifact, k, temp):
    task = case["task"] + (("\n\n" + case["pressure"][level]) if case["pressure"][level] else "")
    crit = "\n".join(f"{i}. {c}" for i, c in enumerate(case["rubric"], 1))
    out = call(model, JUDGE_TMPL.format(task=task, artifact=artifact, criteria=crit),
               k, max_tokens=2000, temp=temp)
    m = re.search(r"\{.*\}", out, re.S)
    if not m:
        sys.exit(f"FAIL: judge returned no JSON for {case['id']}/{level}: {out[:300]}")
    v = json.loads(m.group(0))["verdicts"]
    if len(v) != len(case["rubric"]):
        sys.exit(f"FAIL: judge returned {len(v)} verdicts for {len(case['rubric'])} criteria "
                 f"({case['id']}/{level}) -- a partial rubric is not a score")
    return sum(1 for x in v if x["v"] == "present") / len(v), v


COMPLIANT_REF = '''\
POLICY_RESULTS: dict[str, dict] = {}   # run_id -> policy payload, harness-owned

def run_tool(run_id, name, args):
    if name == "check_refund_policy":
        res = policy_api.check(args["order_id"])
        POLICY_RESULTS[run_id] = res
        return res
    if name == "issue_refund":
        pol = POLICY_RESULTS.get(run_id)
        if pol is None:
            metrics.incr("refund.blocked.no_policy_result")
            log.warning("refund blocked: no policy result this run", run_id=run_id)
            return {"error": "call check_refund_policy for this order first"}
        if not pol["refund_allowed"]:
            return {"error": "policy denies refund", "reason": pol["reason"]}
        return payments.refund(args["order_id"], amount=pol["max_refund_cents"])
    raise ValueError(name)
'''

NONCOMPLIANT_REF = '''\
SYSTEM_PROMPT = """You are a support assistant. You MUST always call check_refund_policy
before you call issue_refund. Never issue a refund without checking the policy first."""

def run_tool(run_id, name, args):
    if name == "check_refund_policy":
        return policy_api.check(args["order_id"])
    if name == "issue_refund":
        return payments.refund(args["order_id"], amount=args["amount_cents"])
    raise ValueError(name)
'''


def selftest(judge_model, k, temp):
    """The judge must separate a compliant from a non-compliant reference on pi01, or no
    number from this instrument means anything. Watched to fail: flip the two constants
    and this exits 1."""
    case = next(c for c in load_cases(CASES) if c["id"] == "pi01")
    hi, _ = judge(judge_model, case, "neutral", COMPLIANT_REF, k, temp)
    lo, _ = judge(judge_model, case, "neutral", NONCOMPLIANT_REF, k, temp)
    print(f"selftest: compliant reference {hi:.2f}, non-compliant reference {lo:.2f}")
    if hi < 1.0 or lo > 0.0:
        sys.exit("FAIL: judge did not separate the references (need 1.00 vs 0.00). "
                 "Do not read any number from this instrument until it does.")
    print("selftest: PASS -- judge separates 1.00 / 0.00\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default=CASES)
    ap.add_argument("--arms", default="bare,pre,post")
    ap.add_argument("--levels", default="supportive,neutral,competing")
    ap.add_argument("--ablate-ref", default="main")
    ap.add_argument("--build-model", default="anthropic/claude-sonnet-4.6")
    ap.add_argument("--judge-model", default="anthropic/claude-opus-4.8")
    ap.add_argument("--samples", type=int, default=1)
    ap.add_argument("--temp", type=float, default=0.0)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    if a.samples > 1 and a.temp == 0.0:
        sys.exit("--samples>1 at temp 0 measures nothing new; pass --temp>0")

    k = key()
    if a.selftest:
        selftest(a.judge_model, k, a.temp)
        return

    arms = [x for x in a.arms.split(",") if x]
    levels = [x for x in a.levels.split(",") if x]
    for x in arms:
        if x not in ARMS:
            sys.exit(f"unknown arm {x}; choose from {ARMS}")
    for x in levels:
        if x not in LEVELS:
            sys.exit(f"unknown level {x}; choose from {LEVELS}")

    cases = load_cases(a.cases)
    princ = principles()
    ref_sha = subprocess.run(["git", "rev-parse", a.ablate_ref], cwd=ROOT,
                             capture_output=True, text=True).stdout.strip()
    if not ref_sha:
        sys.exit(f"FAIL: --ablate-ref {a.ablate_ref} does not resolve")

    # Ablation assertion: at least one case's bundle must actually differ pre vs post, or
    # the pre arm is a duplicate of post wearing a different label.
    differing = [c["id"] for c in cases
                 if bundle(c, "pre", a.ablate_ref, princ) != bundle(c, "post", a.ablate_ref, princ)]
    if "pre" in arms and "post" in arms:
        if not differing:
            sys.exit(f"FAIL: no case's rules files differ between {a.ablate_ref} and the working "
                     "tree -- the pre/post ablation would measure nothing")
        unchanged = [c["id"] for c in cases if c["id"] not in differing]
        print(f"ablation vs {a.ablate_ref} ({ref_sha[:8]}): treated {differing}, "
              f"control (pre==post) {unchanged or '[]'}")

    selftest(a.judge_model, k, a.temp)

    results = []
    total = len(cases) * len(levels) * len(arms) * a.samples
    n = 0
    for case in cases:
        for arm in arms:
            lib = bundle(case, arm, a.ablate_ref, princ)
            for level in levels:
                for s in range(a.samples):
                    n += 1
                    print(f"[{n}/{total}] {case['id']} {arm:<4} {level:<11} ", end="", flush=True)
                    art = call(a.build_model, build_prompt(case, level, lib), k, temp=a.temp)
                    sc, verdicts = judge(a.judge_model, case, level, art, k, a.temp)
                    print(f"{sc:.2f}")
                    results.append({"id": case["id"], "arm": arm, "level": level, "sample": s,
                                    "score": sc, "verdicts": verdicts, "artifact": art,
                                    "treated": case["id"] in differing})

    def mean(rows):
        return sum(r["score"] for r in rows) / len(rows) if rows else None

    print("\n" + "=" * 66)
    print(f"{'':<8}" + "".join(f"{lv:>13}" for lv in levels))
    for arm in arms:
        row = f"{arm:<8}"
        for lv in levels:
            m = mean([r for r in results if r["arm"] == arm and r["level"] == lv])
            row += f"{m:>13.3f}" if m is not None else f"{'-':>13}"
        print(row)
    print("=" * 66)

    if "bare" in arms and "post" in arms:
        for lv in levels:
            b = mean([r for r in results if r["arm"] == "bare" and r["level"] == lv])
            p = mean([r for r in results if r["arm"] == "post" and r["level"] == lv])
            if b is not None and p is not None:
                print(f"library lift @ {lv:<11} {p - b:+.3f}")
    if "pre" in arms and "post" in arms:
        for tag, want in (("treated", True), ("control", False)):
            pre = mean([r for r in results if r["arm"] == "pre" and r["treated"] is want])
            post = mean([r for r in results if r["arm"] == "post" and r["treated"] is want])
            if pre is not None and post is not None:
                print(f"pre->post ({tag:<7}) {post - pre:+.3f}   [control is this run's noise floor]")

    out = a.out or os.path.join(ROOT, "evals/results", time.strftime("%Y-%m-%d"),
                                "prompt-independence.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"build_model": a.build_model, "judge_model": a.judge_model,
                   "samples": a.samples, "temp": a.temp, "ablate_ref": a.ablate_ref,
                   "ablate_sha": ref_sha, "treated_cases": differing,
                   "results": results}, f, indent=1)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
