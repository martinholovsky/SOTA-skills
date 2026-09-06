#!/usr/bin/env python3
"""Routing RECALL/PRECISION over a gold SET — does the description catalogue deliver
the *composition* the router promises?

`run-desc-routing.py` measures a pick-ONE decision: one `expect`, one distractor. That
cannot see the two failure modes that matter for a multi-domain task:

  under-selected — some necessary skills chosen, others silently missing
  over-selected  — extra skills loaded, costing context and inviting conflicting rules

Both are invisible to a top-1 metric, and both are what an agent actually does wrong on
a task like "audit my MCP server", where the knowledge lives in three skills at once.

METHOD. The model sees the same catalogue an auto-loader sees — every `skills/sota-*`
SKILL.md frontmatter *description*, nothing else, because the description is the entire
trigger classifier and the body is inert until a skill is loaded. It is asked for ALL
skills a competent engineer would load. Scoring is objective (exact name match against a
gold set), no judge:

  recall    = |picked ∩ gold| / |gold|          (did it get what it needed?)
  precision = |picked ∩ gold| / |picked|        (did it get much else?)

WHERE THE GOLD SETS COME FROM — the selection rule, declared so the metric is not
circular. Wherever the router's own "Cross-cutting routing rules" state a composition
("a K8s cluster audit loads sota-kubernetes + sota-network-security + sota-sandboxing"),
that IS the gold set, transcribed. The eval then asks a sharp question: **do the
descriptions deliver what the router body promises?** Those two surfaces are written by
different hands at different times and nothing checks they agree. Cases with no stated
composition carry their reasoning inline and are marked `derived`.

WHAT THIS DOES NOT MEASURE. Conflict rate — whether two loaded skills give contradictory
prescriptions — needs a judge and is deliberately out of v1. It has a real seed incident
(a liveness-probe rule against a no-`await` async rule, which is why the router carries a
conflict-resolution clause) and is the natural v2.

Auth: OPENROUTER_API_KEY (env or ./.env). Never printed or committed.
Usage: python3 evals/run-routing-recall.py [--selftest] [--samples N] [--temp T]
                                           [--model M] [--cases F] [--out FILE]
"""
import argparse
import glob
import json
import os
import re
import statistics
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CASES = os.path.join(ROOT, "evals/cases/routing-recall.jsonl")


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


def parse_desc(path):
    """(name, description) from SKILL.md frontmatter — inline or block scalar."""
    fm = open(path, encoding="utf-8").read().split("\n---", 1)[0]
    name = re.search(r"(?m)^name:\s*(.+)$", fm).group(1).strip()
    rest = re.search(r"(?m)^description:(.*)$", fm).group(1).strip()
    if rest and rest not in (">-", ">", "|", "|-", "|+", ">+"):
        return name, rest.strip("'\"")
    grab, out = False, []
    for ln in fm.splitlines():
        if ln.startswith("description:"):
            grab = True
            continue
        if grab:
            if re.match(r"^\S", ln):
                break
            out.append(ln.strip())
    return name, " ".join(x for x in out if x)


def catalogue():
    items = []
    for d in sorted(glob.glob(os.path.join(ROOT, "skills/sota-*"))):
        if os.path.isdir(d):
            items.append(parse_desc(os.path.join(d, "SKILL.md")))
    if not items:
        sys.exit("skill catalogue is EMPTY (globbed skills/sota-* under %s). "
                 "Every case would score recall 0 and it would look like a routing "
                 "failure. Refusing to run." % ROOT)
    return items


def load_cases(path):
    cases = [json.loads(x) for x in open(path, encoding="utf-8")
             if x.strip() and not x.lstrip().startswith("#")]
    if not cases:
        sys.exit("no cases in %s — an empty case set scores nothing and prints a "
                 "mean over zero. Refusing to run." % path)
    return cases


def score(picked, gold):
    """Objective set scoring. Returns (recall, precision, missing, extra)."""
    p, g = set(picked), set(gold)
    hit = p & g
    recall = len(hit) / len(g) if g else 0.0
    precision = len(hit) / len(p) if p else 0.0
    return recall, precision, sorted(g - p), sorted(p - g)


def build_prompt(items, task):
    cat = "\n".join("- %s: %s" % (n, d) for n, d in items)
    return ("You are selecting which skills to load before starting an engineering task. "
            "Below is the full catalogue, each with the description its author wrote.\n\n"
            "Select EVERY skill a competent engineer would want loaded for the task — no "
            "more and no fewer. Loading an irrelevant skill costs context and can surface "
            "guidance that conflicts with the task; omitting a needed one means its rules "
            "are never applied.\n\n"
            "CATALOGUE:\n%s\n\nTASK: %s\n\n"
            "Output ONLY a JSON array of skill names, e.g. [\"sota-golang\",\"sota-testing\"]. "
            "No prose." % (cat, task))


def call(model, key, prompt, temp, tries=4):
    body = json.dumps({"model": model, "temperature": temp,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions", data=body,
        headers={"Authorization": "Bearer %s" % key, "Content-Type": "application/json"})
    last = None
    for _ in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                d = json.loads(r.read())
            txt = d["choices"][0]["message"]["content"]
            # An HTTP 200 with empty content is not a successful call (evals/README).
            if txt and txt.strip():
                return txt
            last = "empty completion (finish_reason=%s)" % d["choices"][0].get("finish_reason")
        except Exception as e:                                  # noqa: BLE001
            last = repr(e)
    sys.exit("model call failed after %d tries: %s" % (tries, last))


def parse_picks(txt, valid):
    """Extract the JSON array; keep only names that are real skills."""
    m = re.search(r"\[.*?\]", txt, re.S)
    if not m:
        return []
    try:
        arr = json.loads(m.group(0))
    except json.JSONDecodeError:
        return []
    return [x for x in arr if isinstance(x, str) and x in valid]


def selftest():
    """The scorer is a control: watch it produce a WRONG answer on purpose.

    Three references that must separate. If they do not, no number this runner
    prints means anything (`sota-code-security` rules/15 §2.2).
    """
    gold = ["sota-a", "sota-b", "sota-c"]
    checks = [
        ("perfect",        gold,                      1.0, 1.0),
        ("pick-everything", gold + ["sota-x", "sota-y"], 1.0, 0.6),
        ("half",           ["sota-a", "sota-b"],      2 / 3, 1.0),
        ("empty",          [],                        0.0, 0.0),
        ("all-wrong",      ["sota-x"],                0.0, 0.0),
    ]
    bad = 0
    for label, picked, want_r, want_p in checks:
        r, p, _, _ = score(picked, gold)
        ok = abs(r - want_r) < 1e-9 and abs(p - want_p) < 1e-9
        print("  %-16s recall=%.3f precision=%.3f  %s" % (label, r, p, "ok" if ok else "MISMATCH"))
        bad += 0 if ok else 1
    # The discriminating assertion: a detector that picks everything must score
    # perfect recall and POOR precision. If precision does not fall, over-selection
    # is invisible and this whole runner measures nothing new over top-1.
    r_all, p_all, _, _ = score(gold + ["sota-x", "sota-y"], gold)
    if not (r_all == 1.0 and p_all < 1.0):
        print("  FAIL: pick-everything does not lose precision — over-selection is "
              "unmeasurable and this runner adds nothing to run-desc-routing.py")
        bad += 1
    if bad:
        sys.exit("FAIL: %d scorer check(s) wrong — no number from this runner is usable." % bad)
    print("PASS: scorer separates perfect / over-selected / under-selected / empty.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true",
                    help="check the scorer separates the four outcomes, then exit")
    ap.add_argument("--model", default="anthropic/claude-sonnet-4.6")
    ap.add_argument("--samples", type=int, default=1)
    ap.add_argument("--temp", type=float, default=0.0)
    ap.add_argument("--cases", default=CASES)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    if a.selftest:
        selftest()
        return 0

    items = catalogue()
    names = {n for n, _ in items}
    cases = load_cases(a.cases)

    # GOLD SETS MUST RESOLVE. A case naming a skill that does not exist caps recall
    # below 1.0 forever, and the shortfall reads as a routing failure when it is a
    # case-authoring bug. Same family as an empty comparand (rules/11 §2.2a).
    unknown = {s for c in cases for s in c["expect"] if s not in names}
    if unknown:
        sys.exit("gold sets name skills that do not exist: %s\n"
                 "Recall could never reach 1.0 and the gap would look like a routing "
                 "failure. Fix the cases (or the skill names)." % ", ".join(sorted(unknown)))

    key = load_env_key()
    print("model=%s  cases=%d  catalogue=%d skills  samples=%d  temp=%s\n"
          % (a.model, len(cases), len(items), a.samples, a.temp))

    rows, R, P = {}, [], []
    n_over = n_under = 0
    for c in cases:
        rr, pp, miss, extra = [], [], [], []
        for _ in range(a.samples):
            picks = parse_picks(call(a.model, key, build_prompt(items, c["task"]), a.temp), names)
            r, p, m, x = score(picks, c["expect"])
            rr.append(r); pp.append(p); miss, extra = m, x
        r, p = statistics.mean(rr), statistics.mean(pp)
        R.append(r); P.append(p)
        n_under += 1 if miss else 0
        n_over += 1 if extra else 0
        rows[c["id"]] = {"task": c["task"], "expect": c["expect"], "gold_source": c.get("gold_source"),
                         "recall": r, "precision": p, "missing": miss, "extra": extra}
        print("  %-26s recall=%.2f precision=%.2f  missing=%s  extra=%s"
              % (c["id"], r, p, ",".join(miss) or "-", ",".join(extra) or "-"))

    n = len(cases)
    print("\nMEAN recall=%.3f  precision=%.3f   under-selected %d/%d cases   "
          "over-selected %d/%d cases" % (statistics.mean(R), statistics.mean(P),
                                         n_under, n, n_over, n))
    if a.out:
        os.makedirs(os.path.dirname(a.out), exist_ok=True)
        json.dump({"_meta": {"model": a.model, "samples": a.samples, "temp": a.temp,
                             "catalogue_size": len(items), "cases": n},
                   "summary": {"recall": statistics.mean(R), "precision": statistics.mean(P),
                               "under_selected_cases": n_under, "over_selected_cases": n_over},
                   "cases": rows}, open(a.out, "w", encoding="utf-8"), indent=1)
        print("wrote %s" % a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
