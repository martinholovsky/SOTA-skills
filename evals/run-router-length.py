#!/usr/bin/env python3
"""Router length sweep — does routing survive a longer SKILL.md?

The 500-line cap on `skills/sota/SKILL.md` is OUR invariant mirroring the platform's
advisory "keep SKILL.md under 500 lines". It is not a loader limit — nothing truncates a
skill at load. So the question the cap is really standing in for is whether ROUTING
DEGRADES as the file grows, and that had never been measured.

Arms vary only the router text; the real file is never mutated (no invariant-1 churn, no
ROUTER_BUILD_SHA trip):

  base          the router as it stands
  +N after      N filler lines AFTER the cross-cutting rules — length without depth
  +N before     N filler lines BEFORE the routing table — the table pushed deeper
  no-router     the without-library arm; it cannot see the treatment, so it is a free
                negative control on the measurement itself

FILLER IS SIGNAL-FREE BY CONSTRUCTION — deterministic prose containing no skill name and
no "sota" string, so it can neither help nor hurt routing. Check it before trusting a run.

Result 2026-08-26 (claude-sonnet-5, 3 samples, temp 0.7): recall FLAT AT 1.000 at 501,
902 and 1,302 lines (~40k prompt tokens), while no-router reproduced 0.867 — exactly the
figure from the 2026-08-25 routing run. Two caveats published with it: the metric is AT
CEILING so it can only detect a drop, and inert filler tests length/depth but NOT
competition between real rules. Write-up: results/2026-08-26/ROUTER-LENGTH.md

Usage: python3 evals/run-router-length.py
"""
import glob, json, os, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL = "anthropic/claude-sonnet-5"
SAMPLES, TEMP = 3, 0.7

def key():
    for l in open(os.path.join(ROOT, ".env"), encoding="utf-8"):
        if l.startswith("OPENROUTER_API_KEY="):
            return l.split("=", 1)[1].strip().strip("'\"")
    sys.exit("no key")
K = key()

def load_cases():
    out = []
    for l in open(os.path.join(ROOT, "evals/cases/router.jsonl"), encoding="utf-8"):
        l = l.strip()
        if l and not l.startswith("#"):
            out.append(json.loads(l))
    return out

ROUTER = open(os.path.join(ROOT, "skills/sota/SKILL.md"), encoding="utf-8").read()
NAMES = ", ".join(sorted(os.path.basename(d) for d in glob.glob(os.path.join(ROOT, "skills/sota-*")) if os.path.isdir(d)))

# --- deterministic, signal-free filler -------------------------------------------
TOPICS = ["cache invalidation", "queue depth", "retry jitter", "clock skew",
          "connection reuse", "buffer sizing", "log sampling", "index bloat",
          "batch windows", "warm standby", "partial writes", "back-pressure"]
def filler(n):
    ls = ["", "## Appendix — operational notes", ""]
    i = 0
    while len(ls) < n:
        t = TOPICS[i % len(TOPICS)]
        ls += [f"- **Note {i+1} — {t}.** Record the observed baseline for {t} before",
               f"  changing it, and re-measure after; an unmeasured change to {t} is a",
               f"  guess that reads as a decision. Keep the note beside the setting."]
        i += 1
    return "\n".join(ls[:n])

TABLE = "## Routing table"
XCUT_END = "## Day zero"
def variant(name):
    if name == "base": return ROUTER
    n = 400 if "400" in name else 800
    f = filler(n)
    if "before" in name:
        i = ROUTER.index(TABLE); return ROUTER[:i] + f + "\n\n" + ROUTER[i:]
    i = ROUTER.index(XCUT_END);  return ROUTER[:i] + f + "\n\n" + ROUTER[i:]

def build_prompt(cases, router):
    keep = ("id", "prompt")
    tasks = json.dumps([{k: v for k, v in c.items() if k in keep} for c in cases], indent=1)
    head = ("You are routing an engineering task to skills. For each prompt, list the "
            f"sota-* skill names that should load. Available skills: {NAMES}.")
    lib = (f"\n\nApply this router (its routing table AND cross-cutting rules):\n\n{router}\n\n"
           if router else "\n\nUse only the skill names above and your own judgment.\n\n")
    return (f"{head}{lib}Cases:\n{tasks}\n\n"
            'Output ONLY a JSON object mapping each case id to a list of skill-names, '
            'e.g. {"x1": ["sota-testing"]}. No prose, no code fence.')

def call(prompt):
    body = json.dumps({"model": MODEL, "messages": [{"role": "user", "content": prompt}],
                       "temperature": TEMP}).encode()
    r = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=body,
        headers={"Authorization": f"Bearer {K}", "Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=300) as f: d = json.load(f)
    txt = d["choices"][0]["message"]["content"]
    if not txt: sys.exit("empty completion")
    s, e = txt.find("{"), txt.rfind("}")
    return json.loads(txt[s:e+1]), (d.get("usage") or {}).get("prompt_tokens")

def score(cases, preds):
    tot, miss = 0.0, {}
    for c in cases:
        exp, got = set(c["expect"]), set(preds.get(c["id"], []))
        r = len(exp & got) / len(exp)
        if r < 1.0: miss[c["id"]] = sorted(exp - got)
        tot += r
    return tot / len(cases), miss

cases = load_cases()
print(f"cases={len(cases)}  model={MODEL}  samples={SAMPLES}  temp={TEMP}\n")
results = {}
for arm in ("no-router", "base", "+400 after", "+400 before", "+800 before"):
    router = "" if arm == "no-router" else variant(arm)
    lines = 0 if not router else router.count("\n") + 1
    prompt = build_prompt(cases, router)
    recs, last = [], {}
    ptok = None
    for _ in range(SAMPLES):
        preds, ptok = call(prompt)
        r, last = score(cases, preds); recs.append(r)
    m = sum(recs) / len(recs)
    results[arm] = {"recall": m, "recalls": recs, "lines": lines, "prompt_tokens": ptok, "misses": last}
    print(f"{arm:14s} lines={lines:5d} ptok={ptok:7,}  recall={m:.3f}  "
          f"[{'/'.join(f'{x:.2f}' for x in recs)}]  misses={sorted(last)}")
json.dump(results, open(os.path.join(ROOT, "evals/results/2026-08-26/router-length.json"), "w"), indent=1)
b = results["base"]["recall"]
print("\nvs base:")
for a, v in results.items():
    if a in ("base", "no-router"): continue
    print(f"  {a:14s} {v['recall']-b:+.3f}")
