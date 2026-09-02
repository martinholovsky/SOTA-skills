#!/usr/bin/env python3
"""Completeness eval: does the library make the model embed best practices UNPROMPTED?

The routing/audit/freshness evals measure the library's weakest dimensions. This
measures its thesis: given a minimal "build X for my app" prompt (no security /
logging / transport cues), does a with-library model produce a SOTA-complete
implementation from v1 — vs a without-library model that builds "some X"?

Method (clean, raw OpenRouter API — no sota config anywhere):
  - Generate: both arms get the SAME minimal task. The with-library arm ALSO
    gets (a) the router's universal non-negotiables (operating principle 5),
    (b) the relevant skill rules pasted in, and (c) the BUILD self-audit — apply
    the non-negotiables, then check the diff against each rules file's Audit
    checklist and fill every gap (simulating an agent that loaded the router +
    skills and followed the BUILD process, not just read the rules). Both are
    load-bearing: without the self-audit the model silently drops peripheral
    concerns; and cross-cutting ones (rate limiting, transport) fade in a long
    rules context unless principle 5 re-surfaces them — a salience/context-rot
    effect (docs/WHY-IT-WORKS.md), not a coverage gap. The without arm gets
    nothing.
  - Judge: a DIFFERENT model, BLIND to which arm produced the artifact, scores
    each artifact against the case's fixed rubric of universal best practices
    (present/absent per criterion). Completeness = present / total.
  - Lift = with-recall − without-recall.

Rubric criteria are universal, expert-agreed best practices (authz, validation,
transport, structured logging, error hygiene, tests, ...) — not sota-invented —
so a base model that "just knew" to do them would score high too.

Auth: OPENROUTER_API_KEY (env or ./.env). Never printed/committed.
Usage: python3 evals/run-completeness.py [--build-model M] [--judge-model M]
       [--samples N] [--temp T] [--out FILE]
       (--samples>1 needs --temp>0 for real variance; default 1 sample at temp 0.)
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


def call(model, prompt, k, max_tokens=8000, temp=0.0):
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}],
                       "temperature": temp, "max_tokens": max_tokens}).encode()
    last = None
    for attempt in range(4):  # retry transient network/5xx; large gens can trickle
        try:
            req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=body,
                                         headers={"Authorization": f"Bearer {k}", "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=300) as r:
                d = json.load(r)
            ch = d["choices"][0]
            content = ch["message"]["content"]
            # A 200 with null/empty content is NOT success. Reasoning models can spend
            # the whole max_tokens budget on reasoning and return nothing: on
            # 2026-08-14 gemini-3.1-pro returned content=None mid-run and the crash
            # surfaced 80 lines later as `'NoneType' object is not subscriptable` in
            # judge(). Retry it, then fail LOUDLY with the finish reason — an empty
            # artifact that reaches the judge scores ~0 and silently depresses an arm.
            if not content:
                raise RuntimeError(
                    f"empty completion from {model}: finish_reason="
                    f"{ch.get('finish_reason')} native={ch.get('native_finish_reason')} "
                    f"usage={d.get('usage', {}).get('completion_tokens_details', {})}")
            if ch.get("finish_reason") == "length":
                print(f"      WARNING: {model} hit max_tokens ({max_tokens}) — artifact "
                      f"is TRUNCATED, the score for it is a floor, not a measurement")
            return content
        except Exception as e:  # noqa: BLE001 — retry any transient failure
            last = e
            time.sleep(3 * (attempt + 1))
    raise last


def load_cases():
    return [json.loads(x) for x in open(CASES, encoding="utf-8")
            if x.strip() and not x.startswith("#")]


# DRIFT GUARD. BUILD_WORKFLOW below is a hand-compressed MIRROR of the router's
# BUILD section, not a live read — it is kept compressed so results stay comparable
# with every historical run. A mirror silently rots: on 2026-07-20 the falsification
# clause added to router step 4 (PR #119) was missing here for four days, so the
# project's most-cited number (+0.39) was being measured against a workflow that no
# longer shipped. Nothing failed; the eval just quietly measured the wrong thing.
# So: pin the router section's hash. If the router changes, this aborts and forces a
# decision — re-sync the mirror and update the hash, or consciously accept the drift.
ROUTER_BUILD_SHA = "a92b0177acadec05"


def _assert_mirror_fresh():
    """Abort if the router's BUILD section moved without this mirror being re-synced."""
    import hashlib
    t = open(os.path.join(ROOT, "skills/sota/SKILL.md"), encoding="utf-8").read()
    i, j = t.find("## BUILD mode — workflow"), t.find("## AUDIT mode — workflow")
    if i < 0 or j < 0 or j <= i:
        sys.exit("router BUILD section not found — cannot verify the mirror is fresh.")
    got = hashlib.sha256(t[i:j].strip().encode()).hexdigest()[:16]
    if got != ROUTER_BUILD_SHA:
        sys.exit(
            f"MIRROR DRIFT: router BUILD section is {got}, mirror pinned to "
            f"{ROUTER_BUILD_SHA}.\nBUILD_WORKFLOW in this file no longer reflects the "
            f"router. Re-sync it and set ROUTER_BUILD_SHA={got}, or the eval will "
            f"measure a workflow that is not shipped. Refusing to run.")


# Mirrors the router's BUILD workflow (skills/sota/SKILL.md steps 3-4): plan the
# task as concrete checkable items, apply the non-negotiables, then self-audit the
# diff against each Audit checklist and fill every gap. The self-audit is the
# forcing function the plain "paste rules" arm omitted; the concrete-plan step
# mirrors step 3's plan-first discipline.
BUILD_WORKFLOW = (
    "\n\n---\nBUILD PROCESS (follow it): (1) apply the NON-NEGOTIABLES of the "
    "standards above unconditionally. (2) plan first — before writing code, list "
    "the task's requirements as concrete, checkable items (each a specific outcome "
    "you can mark done/not-done, e.g. 'rate-limit login to N/min per IP', not a "
    "vague 'add rate limiting'), then implement against that list. (3) CRITICAL — "
    "before finishing, go through EVERY '## Audit checklist' at the end of the "
    "standards above and verify your code satisfies each item; for any gap (rate "
    "limiting, transport/TLS enforcement, tests, structured logging, idempotency, "
    "etc.) ADD it, or state explicitly why it is out of scope. For every control, "
    "safeguard, or check you added, also ask: if this were silently a no-op, would "
    "anything observable differ? If nothing would — no log, no metric, no failing "
    "test — it is not done. If a control you added emits an artifact (a record, "
    "ledger line, signature), read back the one this run produced rather than "
    "re-reading the code that writes it. Do not present incomplete code.\n\nTask: ")


def principle5():
    """The router's universal build non-negotiables (operating principle 5), read
    live so the eval reflects what a real agent loads (the router first). Omitting
    it under-measures the library: it's the short, salient reminder that recovers
    the cross-cutting concerns a long rules context makes the model drop."""
    t = open(os.path.join(ROOT, "skills/sota/SKILL.md"), encoding="utf-8").read()
    i = t.find("5. **Universal build non-negotiables")
    j = t.find("\n## Routing table")
    if i < 0 or j < 0 or j <= i:
        # 2026-08-16: this used to `return ""` on a moved marker. Principle 5 is the
        # component this project credits with the bulk of the +0.39, so an empty
        # return silently WEAKENS the treatment arm and under-reports the lift — the
        # direction nobody investigates because it reads as conservative. It is not
        # covered by ROUTER_BUILD_SHA either: that hash spans BUILD→AUDIT (~24k-27k),
        # principle 5 lives at ~4k. Abort instead.
        sys.exit("principle 5 markers not found in skills/sota/SKILL.md — the "
                 "with-library arm would silently lose the universal non-negotiables. "
                 "Fix the marker or update principle5(). Refusing to run.")
    p5 = t[i:j].strip()
    if len(p5) < 500:                       # floor: the real block is ~2.3k chars
        sys.exit(f"principle 5 extracted only {len(p5)} chars — markers moved or the "
                 f"section shrank; refusing to run on a truncated treatment arm.")
    return p5


def rules_padding(n, exclude):
    """N lines of GENUINE rules prose from skills the case does NOT load.

    ROADMAP item 25, completeness half. The routing half asked whether real competing
    guidance degrades *retrieval* and read null (0.992 vs 1.000, 2026-08-27). This asks
    the question that actually matters: does it degrade **rule application** in a long
    build? `sota/rules/02` s1 asserts that loading unrelated rules files "measurably
    reduces how many rules the model applies" -- an assertion this project has never put
    a number on. Padding is drawn from OTHER skills so it is genuinely irrelevant to the
    task, and every routing signal is stripped so the arm cannot differ by retrieval.
    """
    import glob, re
    out, used = [], []
    excl = {os.path.abspath(os.path.join(ROOT, e)) for e in exclude}
    for f in sorted(glob.glob(os.path.join(ROOT, "skills/sota-*/rules/*.md"))):
        if os.path.abspath(f) in excl:
            continue
        used.append(os.path.relpath(f, ROOT))
        for line in open(f, encoding="utf-8"):
            line = re.sub(r"`?sota-[a-z-]+`?", "the relevant skill", line)
            line = re.sub(r"rules/\d+", "the rules file", line)
            if line.strip():
                out.append(line.rstrip("\n"))
            if len(out) >= n:
                break
        if len(out) >= n:
            break
    if len(out) < n:
        sys.exit(f"rules_padding: only {len(out)} lines available for n={n} -- refusing to "
                 f"run a short padding arm, which would under-state any effect.")
    body = "\n".join(out[:n])
    # A leaked skill name would let the padded arm differ by ROUTING rather than by
    # attention, which is the confound this whole arm exists to avoid.
    if "sota-" in body:
        sys.exit("rules_padding: padding leaked a skill name -- it would confound the arm.")
    for e in exclude:
        if os.path.relpath(os.path.join(ROOT, e), ROOT) in used:
            sys.exit(f"rules_padding: padding included the case's own file {e}.")
    return "\n\n---\nAdditional engineering standards (also loaded):\n\n" + body


def gen_prompt(case, with_lib, pad=0):
    if with_lib:
        ctx = "\n\n".join(open(os.path.join(ROOT, s), encoding="utf-8").read() for s in case["skills"])
        if pad:
            ctx += rules_padding(pad, case["skills"])
        p5 = principle5()
        return (f"ALWAYS-APPLY OPERATING PRINCIPLE (from the router):\n\n{p5}\n\n"
                f"---\nApply the following engineering standards:\n\n{ctx}{BUILD_WORKFLOW}{case['task']}")
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
    if s < 0 or e < 0:
        sys.exit(f"judge returned no JSON object:\n{txt[:400]}")
    verdict = json.loads(txt[s:e + 1])
    # VALIDATE THE SHAPE, do not just parse it (found 2026-08-16). Scoring reads
    # `verdict.get(id) == "present"`, so a *well-formed* reply of the wrong shape
    # scores 0.00 in silence: {"results": {...}} nests the ids away, and "Present"
    # with a capital P is not "present". Demonstrated at 0.00/12 for both. Missing
    # or extra ids mean the judge answered a different question than we asked.
    want = {r["id"] for r in rubric}
    if not isinstance(verdict, dict):
        sys.exit(f"judge returned {type(verdict).__name__}, expected an object:\n{txt[:300]}")
    verdict = {kk: (vv.lower() if isinstance(vv, str) else vv) for kk, vv in verdict.items()}
    missing, extra = want - set(verdict), set(verdict) - want
    if missing or extra:
        sys.exit(f"judge verdict does not match the rubric — missing {sorted(missing)}, "
                 f"unexpected {sorted(extra)}. Scoring this would silently under-count. "
                 f"Raw:\n{txt[:400]}")
    badv = {kk: vv for kk, vv in verdict.items() if vv not in ("present", "absent")}
    if badv:
        sys.exit(f"judge returned values outside present/absent: {badv}. Raw:\n{txt[:300]}")
    return verdict


# Eval artifacts store MODEL-GENERATED code verbatim, and a model asked to build a
# payments endpoint will happily write `sk_live_...` into an example. That is not a
# real credential, but a secret-SHAPED string in a public repo is still wrong: it
# trips push protection, trains readers on a bad example, and buries any genuine leak
# in noise. On 2026-07-20 exactly this blocked a push. So scrub at write time — the
# class, not the instance — and leave a visible marker so the artifact stays honest.
_SECRET_PATTERNS = [
    r"sk_(?:live|test)_[A-Za-z0-9]{6,}",       # Stripe
    r"AKIA[0-9A-Z]{16}",                        # AWS access key id
    r"gh[pousr]_[A-Za-z0-9]{20,}",              # GitHub tokens
    r"xox[baprs]-[A-Za-z0-9-]{10,}",            # Slack
    r"AIza[0-9A-Za-z_\-]{20,}",                 # Google API key
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----",      # PEM private keys
    r"eyJ[A-Za-z0-9_-]{5,}\.eyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}",   # JWTs
]
# The list above is INCOMPLETE by construction — it enumerates shapes, and a model
# writing example code invents new ones. It missed a fake JWT on 2026-07-21 and
# gitleaks (a second, independent method) caught it. Treat gitleaks as the backstop,
# not this list, and add a pattern whenever it fires. Never bypass push protection.
_UNUSED = [
]


def scrub_secrets(obj):
    """Replace secret-shaped strings anywhere in a nested structure, visibly."""
    import re
    if isinstance(obj, str):
        out = obj
        for pat in _SECRET_PATTERNS:
            out = re.sub(pat, "[SCRUBBED-SECRET-SHAPED-STRING]", out)
        return out
    if isinstance(obj, dict):
        return {k: scrub_secrets(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [scrub_secrets(v) for v in obj]
    return obj


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build-model", default="anthropic/claude-sonnet-4.6")
    ap.add_argument("--judge-model", default="anthropic/claude-opus-4.8")
    ap.add_argument("--samples", type=int, default=1,
                    help="generations per arm; mean recall reported. >1 only varies at --temp>0")
    ap.add_argument("--temp", type=float, default=0.0,
                    help="build-model temperature; keep 0 for a deterministic single run")
    ap.add_argument("--max-tokens", type=int, default=32000,
                    help="build-model output cap. A cap only matters if it BINDS: "
                         "32000 never bound claude-sonnet-4.6, but newer models are far "
                         "more verbose, and a truncated artifact scores as a FLOOR rather "
                         "than a measurement (sota-code-security rules/10 §2.7).")
    ap.add_argument("--pad-rules", type=int, default=0,
                    help="ROADMAP 25: add a third arm whose rules context carries N extra "
                         "lines of genuine rules prose from skills the case does NOT load "
                         "(routing signal stripped). Tests whether competing guidance "
                         "degrades rule APPLICATION, which the routing half could not.")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    _assert_mirror_fresh()   # never measure a workflow that isn't shipped
    if a.samples > 1 and a.temp == 0.0:
        print("note: --samples>1 at --temp 0 gives identical deterministic runs; "
              "use --temp 0.7 for real variance.\n")
    k = key()
    cases = load_cases()
    from _elapsed import note_work   # duration baseline needs a denominator
    note_work(len(cases), "cases")
    print(f"build={a.build_model}  judge={a.judge_model}  cases={len(cases)}  "
          f"samples={a.samples}  temp={a.temp}  (clean API, blind judge)\n")
    results, tot_wo, tot_wl, tot_wp = {}, 0.0, 0.0, 0.0
    for c in cases:
        row = {"rubric_n": len(c["rubric"]), "arms": {}}
        arms = [(False, 0), (True, 0)] + ([(True, a.pad_rules)] if a.pad_rules else [])
        for with_lib, pad in arms:
            arm = ("with+pad" if pad else "with") if with_lib else "without"
            recalls, last_present, last_art = [], [], ""
            for s in range(a.samples):
                print(f"  {c['id']:16s} {arm:8s} generating… (sample {s+1}/{a.samples})", flush=True)
                # 32k: the self-audit with-arm emits substantially longer output;
                # 16k truncated tests/logging off the end and scored them absent.
                art = call(a.build_model, gen_prompt(c, with_lib, pad), k,
                           max_tokens=a.max_tokens, temp=a.temp)
                verdict = judge(art, c["rubric"], a.judge_model, k)
                last_present = [r["id"] for r in c["rubric"] if verdict.get(r["id"]) == "present"]
                recalls.append(len(last_present) / len(c["rubric"]))
                last_art = art
            recall = sum(recalls) / len(recalls)
            spread = f"  (min {min(recalls):.2f} max {max(recalls):.2f} n={len(recalls)})" if a.samples > 1 else ""
            print(f"  {c['id']:16s} {arm:8s} recall={recall:.2f}{spread}  len={len(last_art)}", flush=True)
            row["arms"][arm] = {"recall": recall, "recalls": recalls, "present": last_present,
                                "missing": [r["id"] for r in c["rubric"] if r["id"] not in last_present],
                                "artifact": last_art}
        wo = row["arms"]["without"]["recall"]
        wl = row["arms"]["with"]["recall"]
        tot_wo += wo
        tot_wl += wl
        results[c["id"]] = row
        pad_txt = ""
        if "with+pad" in row["arms"]:
            wp = row["arms"]["with+pad"]["recall"]
            tot_wp += wp
            pad_txt = f"  with+pad={wp:.2f}  pad-delta={wp-wl:+.2f}"
        print(f"{c['id']:16s} without={wo:.2f}  with={wl:.2f}  lift={wl-wo:+.2f}{pad_txt}   "
              f"without-missing: {', '.join(row['arms']['without']['missing']) or '-'}")
    n = len(cases)
    print(f"\nMEAN completeness  without={tot_wo/n:.2f}  with={tot_wl/n:.2f}  "
          f"LIFT={((tot_wl-tot_wo)/n):+.2f}")
    if a.pad_rules:
        # The question ROADMAP 25 asks: does competing guidance cost rule APPLICATION?
        # A negative pad-delta is the load-lean thesis showing up as a number; ~0.00 says
        # the thesis is unsupported at this padding size, which is equally publishable.
        print(f"MEAN with+pad={tot_wp/n:.2f}  PAD-DELTA={((tot_wp-tot_wl)/n):+.2f}  "
              f"({a.pad_rules} lines of unrelated real rules prose added to the with-arm)")
    if a.out:
        # Provenance (found missing 2026-08-16): the flagship artifact stored only case
        # results — no build/judge model, samples, temp, or the router SHA the whole
        # comparison is pinned to. A number nobody can attribute is not evidence.
        out_obj = {"_meta": {"build_model": a.build_model, "judge_model": a.judge_model,
                             "samples": a.samples, "temp": a.temp,
                             "pad_rules": a.pad_rules,
                             "router_build_sha": ROUTER_BUILD_SHA},
                   **scrub_secrets(results)}
        json.dump(out_obj, open(a.out, "w"), indent=1)
        print(f"saved {a.out}")


if __name__ == "__main__":
    from _elapsed import note_complete, report_on_exit
    report_on_exit("run-completeness")
    main()
    note_complete()   # main() returned: a measurement, not an abort
