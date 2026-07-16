#!/usr/bin/env python3
"""Description-based skill-routing eval — does the negative cross-reference in a
skill description ("Not for X — use sota-Y") reduce mis-routing when a model picks
a skill purely from the description catalogue (the path a skill *auto-loader* uses,
as opposed to the router table that `run-clean.py --cases router.jsonl` measures)?

Two arms over the SAME adversarially-confusable tasks, same catalogue except:
  with-xref     — descriptions exactly as committed (carry the "Not for … — use …")
  without-xref  — the same descriptions with only that one sentence stripped

Each case names the correct skill (`expect`) and the tempting wrong sibling
(`distractor`) that shares surface keywords. Metric: **distractor-pick rate** (what
the cross-ref is designed to cut) and primary-correct rate. Scoring is objective —
exact skill-name match on the model's answer, no LLM judge.

Auth: OPENROUTER_API_KEY (env or ./.env). Never printed or committed.
Run: python3 evals/run-desc-routing.py --samples 3 --temp 0.7 \
        --out evals/results/2026-07-13/desc-routing.json
"""
import argparse, glob, json, os, re, statistics, sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CASES = os.path.join(ROOT, "evals/cases/desc-routing.jsonl")
# Strips exactly the added cross-ref sentence(s): each starts "Not for " and, by
# construction, contains no internal period, so this removes one sentence cleanly.
XREF_RE = re.compile(r"\s*Not for [^.]*\.")


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
    """(name, description) from a SKILL.md frontmatter — handles both an inline
    scalar (`description: text…`) and a folded/literal block (`description: >-`)."""
    fm = open(path, encoding="utf-8").read().split("\n---", 1)[0]
    name = re.search(r"(?m)^name:\s*(.+)$", fm).group(1).strip()
    rest = re.search(r"(?m)^description:(.*)$", fm).group(1).strip()
    if rest and rest not in (">-", ">", "|", "|-", "|+", ">+"):
        return name, rest.strip("'\"")  # inline (single-line) description
    grab, out = False, []             # block scalar: gather indented lines
    for ln in fm.splitlines():
        if ln.startswith("description:"):
            grab = True
            continue
        if grab:
            if re.match(r"^\S", ln):  # next top-level key
                break
            out.append(ln.strip())
    return name, " ".join(x for x in out if x)


def catalogue(strip_xref):
    items = []
    for d in sorted(glob.glob(os.path.join(ROOT, "skills/sota-*"))):
        if not os.path.isdir(d):
            continue
        name, desc = parse_desc(os.path.join(d, "SKILL.md"))
        if strip_xref:
            desc = XREF_RE.sub("", desc).strip()
        items.append((name, desc))
    return items


def build_prompt(items, task):
    cat = "\n".join(f"- {n}: {d}" for n, d in items)
    return ("You are selecting the single most relevant skill for a task from a "
            "library. Here is the catalogue (skill name: description).\n\n"
            f"{cat}\n\nTASK: {task}\n\n"
            "Respond with ONLY the exact name of the single most relevant skill "
            "(for example: sota-python). No explanation — just the name.")


def call(model, key, prompt, temp, tries=4):
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}],
                       "temperature": temp}).encode()
    for attempt in range(tries):
        try:
            req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=body,
                                         headers={"Authorization": f"Bearer {key}",
                                                  "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.load(r)["choices"][0]["message"]["content"]
        except Exception as e:  # transient network/5xx — retry with linear backoff
            if attempt == tries - 1:
                raise
            import time
            time.sleep(3 * (attempt + 1))


def pick_from(txt, names):
    """First sota-* token in the reply that is a real skill name."""
    for tok in re.findall(r"sota-[a-z0-9-]+", txt):
        if tok in names:
            return tok
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="anthropic/claude-sonnet-4.6")
    ap.add_argument("--samples", type=int, default=1)
    ap.add_argument("--temp", type=float, default=0.0)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    key = load_env_key()
    cases = [json.loads(l) for l in open(CASES, encoding="utf-8")
             if l.strip() and not l.startswith("#")]
    names = [os.path.basename(d) for d in glob.glob(os.path.join(ROOT, "skills/sota-*"))
             if os.path.isdir(d)]
    arms = {"with-xref": catalogue(False), "without-xref": catalogue(True)}
    print(f"model={a.model}  cases={len(cases)}  samples={a.samples}  temp={a.temp}  "
          f"arms={list(arms)}  (clean API, objective name-match scoring)\n")
    result = {"model": a.model, "samples": a.samples, "temp": a.temp, "cases": {}}
    agg = {arm: {"correct": [], "distractor": []} for arm in arms}
    for c in cases:
        result["cases"][c["id"]] = {"task": c["task"], "expect": c["expect"],
                                    "distractor": c["distractor"], "arms": {}}
        for arm, items in arms.items():
            picks = [pick_from(call(a.model, key, build_prompt(items, c["task"]), a.temp), names)
                     for _ in range(a.samples)]
            corr = statistics.mean(1.0 if p == c["expect"] else 0.0 for p in picks)
            dist = statistics.mean(1.0 if p == c["distractor"] else 0.0 for p in picks)
            agg[arm]["correct"].append(corr)
            agg[arm]["distractor"].append(dist)
            result["cases"][c["id"]]["arms"][arm] = {"picks": picks, "correct": corr, "distractor": dist}
            print(f"  {c['id']:<20} {arm:<14} correct={corr:.2f} distractor={dist:.2f} picks={picks}")
    result["summary"] = {arm: {"correct": statistics.mean(agg[arm]["correct"]),
                               "distractor": statistics.mean(agg[arm]["distractor"])} for arm in arms}
    print("\nSUMMARY")
    for arm in arms:
        s = result["summary"][arm]
        print(f"  {arm:<14} correct={s['correct']:.3f}  distractor-pick={s['distractor']:.3f}")
    wx, wo = result["summary"]["with-xref"], result["summary"]["without-xref"]
    print(f"\n  Δ correct           (with − without) = {wx['correct'] - wo['correct']:+.3f}")
    print(f"  Δ distractor-pick   (with − without) = {wx['distractor'] - wo['distractor']:+.3f}"
          "   (negative = cross-refs help)")
    if a.out:
        json.dump(result, open(a.out, "w"), indent=1)
        print("saved", a.out)


if __name__ == "__main__":
    main()
