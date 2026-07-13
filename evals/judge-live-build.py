#!/usr/bin/env python3
"""Score live-agent BUILD outputs against the completeness rubrics.

run-completeness.py measures the library by PASTING the router's principle 5 +
rules + a self-audit instruction into a single API call (a simulation of what an
agent loads). This script closes the validity gap (roadmap item 2): it scores
artifacts produced by a REAL Claude Code sub-agent that was handed the bare
"build X" task and told to follow the actual sota router BUILD workflow
(load-lean → plan-with-checklist → terminal self-audit) — the live flow, not the
pasted-content sim.

It reuses run-completeness.py's blind judge (opus-4.8 by default): for each case
it concatenates the agent's deliverable files (everything except process.md),
sends them to the judge with the case rubric, and reports present/absent recall.
Compare the mean here to the eval's simulated with-arm (0.99) and base (0.60).

Input: a directory with one subdir per case id, each holding the agent's files.
Auth: OPENROUTER_API_KEY (env or ./.env). Never printed/committed.
Usage: python3 evals/judge-live-build.py --builds DIR [--judge-model M] [--out FILE]
"""
import argparse
import json
import os
import sys

# Reuse the exact judge + case loader from the completeness harness.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib.util

_spec = importlib.util.spec_from_file_location(
    "run_completeness", os.path.join(os.path.dirname(os.path.abspath(__file__)), "run-completeness.py"))
_rc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_rc)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Files that are process logs / notes, not part of the deliverable being judged.
SKIP = {"process.md", "uv.lock", "poetry.lock", "package-lock.json"}
# Judge only the source/tests/config the agent authored — never installed
# dependencies, caches, or VCS internals (agents that ran `uv`/`pip` leave a
# .venv with thousands of files that would swamp the artifact).
SKIP_DIRS = {".venv", "venv", "site-packages", "__pycache__", ".mypy_cache",
             ".ruff_cache", ".pytest_cache", ".git", "node_modules", ".tox",
             "dist", "build", ".eggs"}
CODE_EXT = {".py", ".txt", ".md", ".toml", ".cfg", ".ini", ".env", ".sh", ".yaml", ".yml", ".json"}


def collect_artifact(case_dir):
    parts = []
    for root, dirs, files in os.walk(case_dir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.endswith((".dist-info", ".egg-info"))]
        for fn in sorted(files):
            if fn in SKIP:
                continue
            ext = os.path.splitext(fn)[1].lower()
            if ext and ext not in CODE_EXT:
                continue
            path = os.path.join(root, fn)
            rel = os.path.relpath(path, case_dir)
            try:
                body = open(path, encoding="utf-8").read()
            except (UnicodeDecodeError, OSError):
                continue
            parts.append(f"===== FILE: {rel} =====\n{body}")
    return "\n\n".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--builds", required=True, help="dir with one subdir per case id")
    ap.add_argument("--judge-model", default="anthropic/claude-opus-4.8")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    k = _rc.key()
    cases = _rc.load_cases()
    print(f"judge={a.judge_model}  cases={len(cases)}  builds={a.builds}  (live-agent BUILD, blind judge)\n")
    results, tot = {}, 0.0
    n = 0
    for c in cases:
        case_dir = os.path.join(a.builds, c["id"])
        if not os.path.isdir(case_dir):
            print(f"  {c['id']:16s} SKIP (no build dir)")
            continue
        art = collect_artifact(case_dir)
        if not art.strip():
            print(f"  {c['id']:16s} SKIP (empty build)")
            continue
        verdict = _rc.judge(art, c["rubric"], a.judge_model, k)
        present = [r["id"] for r in c["rubric"] if verdict.get(r["id"]) == "present"]
        missing = [r["id"] for r in c["rubric"] if r["id"] not in present]
        recall = len(present) / len(c["rubric"])
        tot += recall
        n += 1
        results[c["id"]] = {"recall": recall, "present": present, "missing": missing,
                            "artifact_len": len(art)}
        print(f"  {c['id']:16s} recall={recall:.2f}  missing: {', '.join(missing) or '-'}")
    if n:
        print(f"\nMEAN live-agent completeness = {tot/n:.2f}  (n={n})")
        print("compare: base (no library) 0.60 | simulated with-library 0.99 "
              "(results/2026-07-13/completeness-7case-p5.json)")
    if a.out:
        json.dump({"mean": tot / n if n else None, "n": n, "cases": results},
                  open(a.out, "w"), indent=1)
        print(f"saved {a.out}")


if __name__ == "__main__":
    main()
