#!/usr/bin/env python3
"""Cross-file repo-audit eval: does the library lift audit recall when the defect
spans multiple files?

The snippet-audit eval (cases/audit*.jsonl) saturates at 1.00 both arms — a
capable model recognizes an isolated vulnerability whether or not it has the
library. The open question (roadmap item 3) is whether skill-guided auditing
beats bare recognition when the defect is NOT in any single file: an authz check
one layer assumes another enforces, a taint that crosses modules, an invariant
one file documents and another violates, an insecure default trusted elsewhere.

Method (clean, raw OpenRouter API — no sota config anywhere; mirrors run-clean.py):
  - The whole fixture repo (evals/cases/repo-audit/orderdesk/*.py) is pasted with
    per-file headers into BOTH arms. The with-library arm ALSO gets the router
    (skills/sota/SKILL.md) + the sota-code-security rules pasted in. Both are
    asked to report every vulnerability as {category (from the fixed VOCAB),
    file}.
  - Scoring is recall over the planted defects (cases/repo-audit.jsonl):
      * category recall (lenient): did the arm name each planted category anywhere?
      * strict recall: category named AND attributed to a file in that defect's
        `primary` set (so a lucky category guess pinned to the wrong file misses).
  - Lift = with-recall − without-recall, reported for both metrics.

Auth: OPENROUTER_API_KEY (env or ./.env). Never printed/committed.
Usage: python3 evals/run-repo-audit.py [--model M] [--samples N] [--temp T] [--out FILE]
"""
import argparse
import glob
import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_DIR = os.path.join(ROOT, "evals/cases/repo-audit/orderdesk")
CASES = os.path.join(ROOT, "evals/cases/repo-audit.jsonl")

# Same vocabulary as run-clean.py so the two audit evals are directly comparable.
VOCAB = [
    "sql-injection", "command-injection", "weak-password-hashing", "tls-verification-disabled",
    "unsafe-deserialization", "non-constant-time-comparison", "idor", "mass-assignment", "ssrf",
    "redos", "path-traversal", "xxe", "prototype-pollution", "xss", "csrf", "open-redirect",
    "insecure-random", "missing-authentication", "log-injection", "hardcoded-secret",
    "business-logic-flaw",
]


def key():
    k = os.environ.get("OPENROUTER_API_KEY")
    if k:
        return k
    p = os.path.join(ROOT, ".env")
    if os.path.exists(p):
        for ln in open(p, encoding="utf-8"):
            if ln.strip().startswith("OPENROUTER_API_KEY="):
                return ln.split("=", 1)[1].strip().strip("'\"")
    sys.exit("OPENROUTER_API_KEY not found in env or ./.env")


def load_cases():
    return [json.loads(x) for x in open(CASES, encoding="utf-8")
            if x.strip() and not x.startswith("#")]


def repo_text():
    """Concatenate the fixture repo with per-file headers (basenames only)."""
    parts = []
    for f in sorted(glob.glob(os.path.join(REPO_DIR, "*.py"))):
        name = os.path.basename(f)
        if name == "__init__.py":
            continue
        parts.append(f"===== FILE: {name} =====\n{open(f, encoding='utf-8').read()}")
    return "\n\n".join(parts)


def library_context():
    files = sorted(glob.glob(os.path.join(ROOT, "skills/sota-code-security/rules/*.md")))
    if not files:                       # empty corpus => with-arm gets no rules => fake +0.00
        sys.exit(f"library corpus is EMPTY under {ROOT}. Refusing to run a with-library "
                 f"arm that contains no library.")
    rules = "\n\n".join(open(f, encoding="utf-8").read() for f in files)
    router = open(os.path.join(ROOT, "skills/sota/SKILL.md"), encoding="utf-8").read()
    return f"{router}\n\n{rules}"


def build_prompt(repo, with_lib):
    vocab = ", ".join(VOCAB)
    head = (
        "You are auditing a small Python (FastAPI) web application for security "
        "vulnerabilities. The full source is below, file by file. Review it as a "
        "whole: some defects only appear when you connect one file to another (a "
        "route that trusts a service, an insecure default trusted by its caller, "
        "an invariant one module documents and another violates). Report EVERY "
        f"vulnerability you find, using ONLY these category slugs: {vocab}."
    )
    lib = (f"\n\nApply the following engineering standards and router:\n\n{library_context()}\n\n"
           if with_lib else "\n\nUse only your own security knowledge.\n\n")
    return (
        f"{head}{lib}APPLICATION SOURCE:\n\n{repo}\n\n"
        'Output ONLY a JSON array of findings, each {"category": "<slug>", '
        '"file": "<basename.py>", "why": "<one line>"}. No prose, no code fence.')


def call(model, prompt, k, temp=0.0):
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}],
                       "temperature": temp, "max_tokens": 4000}).encode()
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=body,
                                 headers={"Authorization": f"Bearer {k}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=240) as r:
        txt = json.load(r)["choices"][0]["message"]["content"]
    s, e = txt.find("["), txt.rfind("]")
    if s < 0 or e < 0:
        sys.exit(f"model did not return a JSON array:\n{txt[:400]}")
    return json.loads(txt[s:e + 1])


def score(cases, findings):
    """Return (category_recall, strict_recall, per-defect hit detail)."""
    got_cat = {str(f.get("category", "")).strip() for f in findings}
    got_pairs = {(str(f.get("category", "")).strip(), os.path.basename(str(f.get("file", "")).strip()))
                 for f in findings}
    cat_hits, strict_hits, detail = 0, 0, {}
    for c in cases:
        cat = c["category"]
        cat_ok = cat in got_cat
        strict_ok = any(cat == g and fpath in set(c["primary"]) for g, fpath in got_pairs)
        cat_hits += cat_ok
        strict_hits += strict_ok
        detail[c["id"]] = {"category": cat, "category_found": cat_ok, "strict_found": strict_ok}
    n = len(cases)
    return cat_hits / n, strict_hits / n, detail


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="anthropic/claude-sonnet-4.6")
    ap.add_argument("--samples", type=int, default=1,
                    help="runs per arm; mean recall reported. >1 only varies at --temp>0")
    ap.add_argument("--temp", type=float, default=0.0)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    if a.samples > 1 and a.temp == 0.0:
        print("note: --samples>1 at --temp 0 gives identical deterministic runs; "
              "use --temp 0.7 for real variance.\n")
    k = key()
    cases = load_cases()
    repo = repo_text()
    print(f"model={a.model}  planted_defects={len(cases)}  samples={a.samples}  "
          f"temp={a.temp}  (clean API run, no sota config)\n")
    result = {}
    for with_lib in (False, True):
        arm = "with-library" if with_lib else "without-library"
        prompt = build_prompt(repo, with_lib)
        cat_recalls, strict_recalls, last_detail, last_findings = [], [], {}, []
        for s in range(a.samples):
            findings = call(a.model, prompt, k, temp=a.temp)
            cat_r, strict_r, detail = score(cases, findings)
            cat_recalls.append(cat_r)
            strict_recalls.append(strict_r)
            last_detail, last_findings = detail, findings
        cat_mean = sum(cat_recalls) / len(cat_recalls)
        strict_mean = sum(strict_recalls) / len(strict_recalls)
        missed = [d for d, v in last_detail.items() if not v["strict_found"]]
        result[arm] = {"category_recall": cat_mean, "strict_recall": strict_mean,
                       "category_recalls": cat_recalls, "strict_recalls": strict_recalls,
                       "detail": last_detail, "findings": last_findings}
        print(f"{arm:16s} category_recall={cat_mean:.2f}  strict_recall={strict_mean:.2f}"
              + (f"  strict-missed: {missed}" if missed else "  (all found, strict)"))
    cat_lift = result["with-library"]["category_recall"] - result["without-library"]["category_recall"]
    strict_lift = result["with-library"]["strict_recall"] - result["without-library"]["strict_recall"]
    print(f"\nLIFT  category={cat_lift:+.2f}  strict={strict_lift:+.2f}")
    if a.out:
        json.dump(result, open(a.out, "w"), indent=1)
        print(f"saved {a.out}")


if __name__ == "__main__":
    main()
