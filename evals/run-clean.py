#!/usr/bin/env python3
"""Clean, isolated with-vs-without efficacy run via a direct model API.

Unlike the in-session eval (where the sota CLAUDE.md directive and the skill
registry are ambient in every subagent — see results/2026-07-10/BASELINE.md
§Control validity), this makes RAW API calls: no HOME, no CLAUDE.md, no skill
registry — just model + prompt. So the "without-library" arm is a true
library-vs-nothing control.

- without-library arm: the task only (+ the category vocabulary / the 40 skill
  names, which are needed to score, but NOT the router rules or skill guidance).
- with-library arm: the same task PLUS the actual repo skill content
  (skills/sota/SKILL.md for routing; skills/sota-code-security/rules/*.md for
  audit) pasted into the prompt.

Auth: OPENROUTER_API_KEY (read from env or ./.env). Never printed or committed.

Usage:
  python3 evals/run-clean.py --cases evals/cases/audit-hard.jsonl
  python3 evals/run-clean.py --cases evals/cases/router.jsonl --model anthropic/claude-sonnet-4.6
  # average N samples per arm for a spread (needs temp>0, else runs are identical):
  python3 evals/run-clean.py --cases evals/cases/freshness.jsonl --samples 3 --temp 0.7
Exit 0 always (it reports; scoring is the output, not a gate).
"""
import argparse
import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOCAB = [
    "sql-injection", "command-injection", "weak-password-hashing", "tls-verification-disabled",
    "unsafe-deserialization", "non-constant-time-comparison", "idor", "mass-assignment", "ssrf",
    "redos", "path-traversal", "xxe", "prototype-pollution", "xss", "csrf", "open-redirect",
    "insecure-random", "missing-authentication", "log-injection", "hardcoded-secret",
    "business-logic-flaw",
]
# Silent-control-failure vocabulary (cases/silent-failure.jsonl). The last six are
# distractors drawn from VOCAB so the choice isn't 1-of-13, and "not-silent" is the
# correct answer for the two loud-failure controls. BOTH arms get this list, so the
# without-library arm is not handicapped on naming — only on recognizing.
SILENT_VOCAB = [
    "weak-existence-check", "optional-dependency-degradation", "empty-ruleset-loaded",
    "swallowed-enforcement-exception", "overloaded-flag", "early-return-bypass",
    "truncation-before-inspection", "ignored-config-key", "doc-code-default-drift",
    "hardcoded-report-value", "shipped-artifact-gap", "vacuous-test", "not-silent",
    # mechanisms NOT enumerated in rules/10 — the generalization probe (cases
    # tagged "novel": does the guidance transfer, or only recall its own list?)
    "regex-never-matches", "unawaited-async-check", "decorator-order-bypass",
    "setting-overwritten", "timeout-not-applied", "retry-swallows-failure",
    # distractors from VOCAB so the choice is never 1-of-N-obvious
    "sql-injection", "missing-authentication", "hardcoded-secret", "idor",
    "path-traversal", "insecure-random",
]
# rules/10 is the file under test; --ablate drops it from the with-library arm to
# isolate its contribution from the rest of sota-code-security.
ABLATE_FILE = "10-silent-control-failure.md"


def load_env_key():
    k = os.environ.get("OPENROUTER_API_KEY")
    if k:
        return k
    envp = os.path.join(ROOT, ".env")
    if os.path.exists(envp):
        for line in open(envp, encoding="utf-8"):
            line = line.strip()
            if line.startswith("OPENROUTER_API_KEY="):
                return line.split("=", 1)[1].strip().strip("'\"")
    sys.exit("OPENROUTER_API_KEY not found in env or ./.env")


def load_cases(path):
    out = []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#"):
            out.append(json.loads(line))
    return out


def read(*parts):
    return open(os.path.join(ROOT, *parts), encoding="utf-8").read()


def audit_library_context(ablate=False):
    import glob
    files = sorted(glob.glob(os.path.join(ROOT, "skills/sota-code-security/rules/*.md")))
    if ablate:
        files = [f for f in files if os.path.basename(f) != ABLATE_FILE]
    return "\n\n".join(open(f, encoding="utf-8").read() for f in files)


def build_prompt(cases, kind, with_lib, ablate=False):
    if kind == "freshness":
        tasks = json.dumps([{"id": c["id"], "question": c["question"]} for c in cases], indent=1)
        head = "Answer each question with the CURRENT (mid-2026) fact, in ONE short line each."
        if with_lib:
            files = sorted({f for c in cases for f in c.get("skill", [])})
            ctx = "\n\n".join(open(os.path.join(ROOT, f), encoding="utf-8").read() for f in files)
            lib = f"\n\nUse this current reference material:\n\n{ctx}\n\n"
        else:
            lib = "\n\nUse only your own knowledge.\n\n"
        return (f"{head}{lib}Questions:\n{tasks}\n\n"
                'Output ONLY a JSON object mapping each id to your one-line answer string, '
                'e.g. {"f01": "RFC 9989"}. No prose, no code fence.')
    # WHITELIST, not blacklist: a case carries answer keys ("expect", "reference") and
    # analysis metadata ("novel", "tier"), and a new field must never leak into the
    # prompt just because nobody added it to a strip list. Only these reach the model.
    # Must list the INPUT field of every kind routed here — `prompt` (router),
    # `snippet` (audit/silent). Omitting one silently reduces its cases to bare ids
    # and the run still prints a plausible number (this exact bug shipped in the
    # first draft: router cases lost `prompt`), hence the guard below.
    keep = ("id", "language", "snippet", "prompt", "task")
    stripped = [{k: v for k, v in c.items() if k in keep} for c in cases]
    for s in stripped:
        if len(s) < 2:
            sys.exit(f"case {s.get('id')!r}: no content field survived the prompt "
                     f"whitelist — add this kind's input field to `keep` in "
                     f"build_prompt(). Refusing to run a content-free eval.")
    tasks = json.dumps(stripped, indent=1)
    if kind == "silent":
        vocab = ", ".join(SILENT_VOCAB)
        head = ("You are reviewing code for controls that are SILENTLY INERT — a check, "
                "scanner, policy, or test that appears to be active but has no effect, so a "
                "broken system and a working one look identical from outside. For each "
                "snippet, list the slugs that apply, using ONLY this vocabulary: "
                f"{vocab}. If the control fails LOUDLY (it raises, logs an error, or emits a "
                "metric when it cannot do its job), answer [\"not-silent\"].")
        lib = (f"\n\nApply the following security guidance:\n\n"
               f"{audit_library_context(ablate)}\n\n"
               if with_lib else "\n\nUse only your own security knowledge.\n\n")
    elif kind == "audit":
        vocab = ", ".join(VOCAB)
        head = (f"You are a security code reviewer. For each snippet, list the vulnerability "
                f"category slugs that apply, using ONLY this vocabulary: {vocab}.")
        lib = (f"\n\nApply the following security guidance:\n\n"
               f"{audit_library_context(ablate)}\n\n"
               if with_lib else "\n\nUse only your own security knowledge.\n\n")
    else:
        names = ", ".join(sorted(os.path.basename(d) for d in _skill_dirs()))
        head = ("You are routing an engineering task to skills. For each prompt, list the "
                f"sota-* skill names that should load. Available skills: {names}.")
        lib = (f"\n\nApply this router (its routing table AND cross-cutting rules):\n\n"
               f"{read('skills/sota/SKILL.md')}\n\n" if with_lib
               else "\n\nUse only the skill names above and your own judgment.\n\n")
    return (f"{head}{lib}Cases:\n{tasks}\n\n"
            'Output ONLY a JSON object mapping each case id to a list of slugs/skill-names, '
            'e.g. {"x1": ["sql-injection"]}. No prose, no code fence.')


def _skill_dirs():
    import glob
    return [d for d in glob.glob(os.path.join(ROOT, "skills/sota-*")) if os.path.isdir(d)]


def call(model, key, prompt, temp=0.0):
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}],
                       "temperature": temp}).encode()
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=body,
                                 headers={"Authorization": f"Bearer {key}",
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        txt = json.load(r)["choices"][0]["message"]["content"]
    s, e = txt.find("{"), txt.rfind("}")
    if s < 0 or e < 0:
        sys.exit(f"model did not return JSON:\n{txt[:400]}")
    return json.loads(txt[s:e + 1])


def score(cases, preds, kind):
    tot, misses = 0.0, {}
    for c in cases:
        if kind == "freshness":
            ans = str(preds.get(c["id"], "")).lower()
            hit = any(tok.lower() in ans for tok in c["expect"])
            r = 1.0 if hit else 0.0
            if not hit:
                misses[c["id"]] = f"want {c['expect']}; got: {ans[:70]!r}"
        else:
            exp = set(c["expect"])
            got = set(preds.get(c["id"], []))
            r = len(exp & got) / len(exp)
            if r < 1.0:
                misses[c["id"]] = sorted(exp - got)
        tot += r
    return tot / len(cases), misses


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", required=True)
    ap.add_argument("--model", default="anthropic/claude-sonnet-4.6")
    ap.add_argument("--samples", type=int, default=1,
                    help="runs per arm; mean recall is reported. >1 only varies at --temp>0")
    ap.add_argument("--temp", type=float, default=0.0,
                    help="sampling temperature; keep 0 for a deterministic single run")
    ap.add_argument("--out", default=None)
    ap.add_argument("--ablate", action="store_true",
                    help=f"with-library arm EXCLUDES rules/{ABLATE_FILE} — isolates that "
                         "file's contribution from the rest of the skill")
    a = ap.parse_args()
    if a.samples > 1 and a.temp == 0.0:
        print("note: --samples>1 at --temp 0 gives identical deterministic runs; "
              "use --temp 0.7 for real variance.\n")
    key = load_env_key()
    cases = load_cases(a.cases)
    kind = cases[0].get("kind", "audit")
    abl = f"  ABLATED(-{ABLATE_FILE})" if a.ablate else ""
    print(f"model={a.model}  kind={kind}  cases={len(cases)}  samples={a.samples}  "
          f"temp={a.temp}{abl}  (clean API run, no sota config)\n")
    result = {"_meta": {"model": a.model, "kind": kind, "cases": len(cases),
                        "samples": a.samples, "temp": a.temp, "ablate": a.ablate}}
    for with_lib in (False, True):
        arm = ("with-library-ablated" if a.ablate else "with-library") if with_lib \
            else "without-library"
        prompt = build_prompt(cases, kind, with_lib, a.ablate)
        recalls, last_misses, last_preds = [], {}, {}
        for _ in range(a.samples):
            preds = call(a.model, key, prompt, temp=a.temp)
            rec, last_misses = score(cases, preds, kind)
            recalls.append(rec)
            last_preds = preds
        mean = sum(recalls) / len(recalls)
        result[arm] = {"recall": mean, "recalls": recalls, "misses": last_misses,
                       "predictions": last_preds}
        spread = f"  (min {min(recalls):.2f}, max {max(recalls):.2f}, n={len(recalls)})" if a.samples > 1 else ""
        print(f"{arm:16s} recall={mean:.2f}{spread}"
              + (f"  misses: {last_misses}" if last_misses else "  (no misses)"))
    with_arm = "with-library-ablated" if a.ablate else "with-library"
    lift = result[with_arm]["recall"] - result["without-library"]["recall"]
    print(f"\nLIFT (with − without) = {lift:+.2f}")
    if a.out:
        json.dump(result, open(a.out, "w"), indent=1)
        print(f"saved {a.out}")


if __name__ == "__main__":
    main()
