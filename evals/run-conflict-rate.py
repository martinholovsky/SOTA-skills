#!/usr/bin/env python3
"""Conflict rate between SIMULTANEOUSLY-LOADED skills — ROADMAP 39, and v2 of
`run-routing-recall.py`.

v1 asked whether the descriptions deliver the composition the router promises (recall
and precision over a gold set, objective scoring, no judge). It said so in its own
docstring: conflict rate — whether two loaded skills give CONTRADICTORY prescriptions —
needs a judge and was deliberately out of scope. This is that.

WHY IT IS THE ONE FAILURE MODE WITH A REAL INCIDENT. Two rules in this library
contradicted each other in a live build: a liveness-probe rule against a no-`await`
`async def` rule. That incident is why the router carries a conflict-resolution clause at
all, and nothing has ever measured how often it happens.

METHOD.
  - The gold set of `routing-recall.jsonl` supplies WHICH skills are loaded together. No
    routing call: the composition is the router's own stated one, so a routing error
    cannot contaminate a conflict number.
  - A conflict is inherently PAIRWISE, so each case is expanded into every unordered pair
    of its gold skills. Single-skill cases contribute no pairs and are excluded, which is
    stated in the output rather than silently dropped.
  - For each pair the judge sees the FULL corpus of both skills — `SKILL.md` plus every
    `rules/*.md` — and the task, and is asked for contradictory prescription pairs with a
    quote from each side.

THIS MEASURES A CEILING, NOT THE LIVED RATE. BUILD step 2 says load lean: a real session
opens a skill's `SKILL.md` and only the rules files matching the work. Handing the judge
every rules file of both skills maximises the chance a contradiction EXISTS somewhere in
what was loaded. So a low number here is strong (the lean rate is lower still) and a high
number is not yet a claim about practice. Narrowing to lean loading is v3.

THE JUDGE IS A CONTROL (`sota-code-security` rules/15 section 7). Two synthetic pairs run in
the SAME batch, before any real pair is scored: one with a planted head-on contradiction
that must yield at least one conflict, one benign pair that must yield zero. If they do
not separate, the run is VOID and no rate is printed — a judge that says "no conflicts"
about everything is indistinguishable from a library with no conflicts.

Auth: OPENROUTER_API_KEY (env or ./.env). Never printed or committed.
Usage: python3 evals/run-conflict-rate.py [--selftest] [--judge-model M] [--samples N]
                                          [--temp T] [--cases F] [--max-chars N]
                                          [--out FILE]
"""
import argparse
import glob
import itertools
import json
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CASES = os.path.join(ROOT, "evals/cases/routing-recall.jsonl")

# A pair whose corpus does not fit the judge's window would be SILENTLY TRUNCATED by the
# provider or rejected — and a truncated corpus cannot be searched for a contradiction it
# no longer contains. The cap is on characters because that is what we can count locally;
# it is deliberately conservative, and exceeding it ABORTS rather than warns.
DEFAULT_MAX_CHARS = 620_000


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


def skill_corpus(skill):
    """Everything an agent could have loaded for this skill, labelled by file.

    Labelled because an unattributed quote cannot be verified by hand afterwards, and
    every conflict this prints is meant to be checked against the file before it counts.
    """
    files = [os.path.join(ROOT, "skills", skill, "SKILL.md")]
    files += sorted(glob.glob(os.path.join(ROOT, "skills", skill, "rules", "*.md")))
    files = [f for f in files if os.path.exists(f)]
    if not files:
        sys.exit(f"skill {skill!r} has no SKILL.md or rules/*.md under {ROOT}/skills — "
                 f"its side of every pair would be EMPTY, and an empty side can contain "
                 f"no contradiction, so every pair with it would score 0. Refusing to run.")
    out = []
    for f in files:
        rel = os.path.relpath(f, ROOT)
        out.append(f"===== {rel} =====\n" + open(f, encoding="utf-8").read())
    return "\n\n".join(out)


def load_cases(path):
    cases = [json.loads(x) for x in open(path, encoding="utf-8")
             if x.strip() and not x.lstrip().startswith("#")]
    if not cases:
        sys.exit(f"no cases in {path} — an empty case set yields an empty pair list and a "
                 f"conflict rate over zero pairs, which prints as 0.00 and means nothing.")
    return cases


def build_prompt(task, a, corpus_a, b, corpus_b):
    return (
        "Two skill files from an engineering guidance library are loaded at the same time "
        "for one task. Your job is to find CONTRADICTIONS between them.\n\n"
        "A contradiction means: following the prescription in one would VIOLATE the "
        "prescription in the other, for this task. Both must be prescriptions (a rule, a "
        "requirement, a 'always/never/must') — not merely different emphasis, different "
        "topics, or one being more specific than the other. A general default plus a "
        "narrower rule that overrides it in its own domain is NOT a contradiction unless "
        "the narrower one fails to say it is narrower.\n\n"
        f"TASK THE ENGINEER IS DOING: {task}\n\n"
        f"--- SKILL A: {a} ---\n{corpus_a}\n\n"
        f"--- SKILL B: {b} ---\n{corpus_b}\n\n"
        "Respond with ONLY a JSON object, no prose:\n"
        '{"conflicts": [{"file_a": "<path from the ===== header>", "quote_a": "<exact '
        'sentence from A>", "file_b": "<path>", "quote_b": "<exact sentence from B>", '
        '"why": "<one sentence: what following both at once would require>"}]}\n'
        'If there are none, respond with exactly {"conflicts": []}.')


def call(model, key, prompt, temp, tries=4):
    body = json.dumps({"model": model, "temperature": temp,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    last = None
    for _ in range(tries):
        try:
            req = urllib.request.Request(
                "https://openrouter.ai/api/v1/chat/completions", data=body,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=600) as r:
                d = json.loads(r.read())
            ch = d["choices"][0]
            txt = ch["message"]["content"]
            # An HTTP 200 with empty content is not a successful call (evals/README).
            if txt and txt.strip():
                return txt
            last = f"empty completion (finish_reason={ch.get('finish_reason')})"
        except Exception as e:  # noqa: BLE001
            last = repr(e)
    sys.exit(f"judge call failed after {tries} tries: {last}\n"
             "A run that silently skipped a pair would under-report the conflict rate, "
             "so this aborts rather than continuing.")


def parse_conflicts(txt):
    """The judge's verdict, or None if it could not be parsed.

    None is NOT zero. A parse failure counted as 'no conflicts' would make a broken
    judge look like a clean library — the exact shape `sota-code-security` rules/11
    section 2.2a warns about, so callers must abort on None rather than coerce it.
    """
    m = re.search(r'\{.*\}', txt, re.S)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict) or not isinstance(obj.get("conflicts"), list):
        return None
    return [c for c in obj["conflicts"] if isinstance(c, dict)]


# --- the judge's own controls ------------------------------------------------
# Run in the SAME batch as the real pairs, with the same model, temperature and prompt.
# POSITIVE is a head-on contradiction of the shape the seed incident had: one file
# requires an endpoint to do work, the other forbids exactly that construct.
CTRL_POSITIVE_A = """===== control/a-liveness.md =====
## Liveness endpoints
Every service MUST expose `GET /healthz` as an `async def` handler that performs a real
dependency check — it must `await` a round-trip to the database before returning 200. A
handler that returns a constant is a liveness probe that cannot fail, which is no probe.
"""
CTRL_POSITIVE_B = """===== control/b-async.md =====
## Async handlers
An `async def` handler MUST NOT contain any `await`. Declaring a coroutine that awaits
anything inside a request path blocks the event loop for the duration of the round-trip.
Handlers that need I/O must be written as ordinary synchronous functions instead.
"""
CTRL_NEGATIVE_A = """===== control/c-naming.md =====
## Naming
Exported identifiers use `snake_case`. Abbreviations are spelled out. A name that needs a
comment to be understood should be renamed instead of commented.
"""
CTRL_NEGATIVE_B = """===== control/d-logging.md =====
## Logging
Emit structured logs as JSON with a stable `event` key. Never log credentials, session
tokens or full request bodies. Sample high-volume debug logs rather than dropping them.
"""
CTRL_TASK = "Add a health-check endpoint to an existing HTTP service and log its results."


def calibrate(model, key, temp):
    """Watch the judge separate a planted contradiction from a benign pair.

    If it does not, nothing below is readable and the run must not print a rate: a judge
    that answers 'no conflicts' to everything produces exactly the number this project
    would most like to see.
    """
    print("calibration (the judge is a control — watch it separate before trusting it):")
    pos = parse_conflicts(call(model, key, build_prompt(
        CTRL_TASK, "control-a", CTRL_POSITIVE_A, "control-b", CTRL_POSITIVE_B), temp))
    neg = parse_conflicts(call(model, key, build_prompt(
        CTRL_TASK, "control-c", CTRL_NEGATIVE_A, "control-d", CTRL_NEGATIVE_B), temp))
    if pos is None or neg is None:
        sys.exit("  VOID: a control verdict did not parse. A parse failure is not a zero.")
    print(f"  planted contradiction -> {len(pos)} conflict(s)   (needs >= 1)")
    print(f"  benign pair           -> {len(neg)} conflict(s)   (needs == 0)")
    if len(pos) < 1 or len(neg) != 0:
        sys.exit("  VOID: the judge does not separate a planted contradiction from a benign\n"
                 "  pair, so every verdict below is uninterpretable. No rate is printed —\n"
                 "  reporting one anyway is how a broken instrument becomes a published\n"
                 "  number (`sota-code-security` rules/15 section 7).")
    print("  ok — separated.\n")
    return {"positive": len(pos), "negative": len(neg)}


def selftest():
    """The parser and the pair expansion are controls too: watch them get it WRONG."""
    bad = 0
    checks = [
        ('{"conflicts": []}', []),
        ('here you go: {"conflicts": [{"why": "x"}]} ok', [{"why": "x"}]),
        ('no json at all', None),
        ('{"conflicts": "not a list"}', None),
        ('{"nope": []}', None),
    ]
    for txt, want in checks:
        got = parse_conflicts(txt)
        ok = got == want
        print(f"  parse {txt[:34]!r:38s} -> {got if got is None else len(got)}  "
              f"{'ok' if ok else 'MISMATCH'}")
        bad += 0 if ok else 1
    # The discriminating assertion: an unparseable verdict must NOT read as zero
    # conflicts. If it does, a broken judge and a clean library are the same number.
    if parse_conflicts("garbage") == []:
        print("  FAIL: an unparseable verdict reads as 'no conflicts' — a broken judge "
              "would be published as a clean library")
        bad += 1
    # Pair expansion: n skills must yield n*(n-1)/2 pairs, and a single-skill case zero.
    for expect, want in ([["a", "b", "c"], 3], [["a", "b"], 1], [["a"], 0]):
        got = len(list(itertools.combinations(expect, 2)))
        ok = got == want
        print(f"  pairs {expect} -> {got}  {'ok' if ok else 'MISMATCH'}")
        bad += 0 if ok else 1
    if bad:
        sys.exit(f"FAIL: {bad} check(s) wrong — no number from this runner is usable.")
    print("PASS: parser separates none / some / unparseable, and pairs expand correctly.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true",
                    help="check the verdict parser and pair expansion, then exit")
    ap.add_argument("--judge-model", default="anthropic/claude-sonnet-5",
                    help="the conflict judge; needs a large context (pairs reach ~150k tokens)")
    ap.add_argument("--samples", type=int, default=3,
                    help="judge calls per pair; a conflict rate at n=1 is not a rate")
    ap.add_argument("--temp", type=float, default=0.0)
    ap.add_argument("--cases", default=CASES,
                    help="gold-set case file; its `expect` list is the loaded composition")
    ap.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS,
                    help="abort if a pair's corpus exceeds this, rather than let the "
                         "provider truncate it silently")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    if a.selftest:
        selftest()
        return 0

    cases = load_cases(a.cases)
    pairs = []
    skipped = []
    for c in cases:
        if len(c["expect"]) < 2:
            skipped.append(c["id"])
            continue
        for x, y in itertools.combinations(sorted(c["expect"]), 2):
            pairs.append((c["id"], c["task"], x, y))
    if not pairs:
        sys.exit("no multi-skill cases — a conflict rate needs at least one pair, and a "
                 "rate over zero pairs prints as 0.00 while measuring nothing.")

    key = load_env_key()
    corpora = {}
    for _, _, x, y in pairs:
        for s in (x, y):
            corpora.setdefault(s, skill_corpus(s))

    oversize = []
    for cid, _, x, y in pairs:
        n = len(corpora[x]) + len(corpora[y])
        if n > a.max_chars:
            oversize.append(f"{cid}: {x} + {y} = {n:,} chars")
    if oversize:
        sys.exit("these pairs exceed --max-chars (%d) and would be truncated:\n  %s\n"
                 "A truncated corpus cannot contain the contradiction it was truncated "
                 "past, so the rate would be an under-count with no signal that it was.\n"
                 "Raise --max-chars only if you have checked the model's real window."
                 % (a.max_chars, "\n  ".join(oversize)))

    print(f"judge={a.judge_model}  pairs={len(pairs)}  samples={a.samples}  temp={a.temp}")
    print(f"corpus: {len(corpora)} skills, {sum(len(v) for v in corpora.values()):,} chars")
    if skipped:
        print(f"excluded (single-skill, no pair to conflict): {', '.join(skipped)}")
    print()

    controls = calibrate(a.judge_model, key, a.temp)

    rows = []
    n_conflicted = 0
    for cid, task, x, y in pairs:
        per_sample = []
        found = []
        for s in range(a.samples):
            v = parse_conflicts(call(a.judge_model, key,
                                     build_prompt(task, x, corpora[x], y, corpora[y]), a.temp))
            if v is None:
                sys.exit(f"unparseable verdict on {cid} {x}+{y} sample {s + 1}. Aborting "
                         f"rather than counting it as zero.")
            per_sample.append(len(v))
            found.extend(v)
        hit = any(n > 0 for n in per_sample)
        n_conflicted += 1 if hit else 0
        rows.append({"case": cid, "a": x, "b": y, "per_sample": per_sample,
                     "any": hit, "conflicts": found})
        print(f"  {cid:26s} {x:24s} {y:24s} per-sample={per_sample}"
              f"{'  <-- CONFLICT REPORTED' if hit else ''}")

    rate = n_conflicted / len(pairs)
    print(f"\nCONFLICT RATE (judge-reported, ANY sample) = {n_conflicted}/{len(pairs)} "
          f"= {rate:.3f}   over {len(pairs)} pairs, {a.samples} samples each")
    print("This is a CEILING: the judge saw every rules file of both skills, while a real")
    print("session loads lean. It is also UNVERIFIED — every reported conflict must be")
    print("read against the two files by hand before it counts (router principle 7).")

    if a.out:
        json.dump({"_meta": {"judge_model": a.judge_model, "samples": a.samples,
                             "temp": a.temp, "cases": os.path.relpath(a.cases, ROOT),
                             "pairs": len(pairs), "excluded_single_skill": skipped,
                             "calibration": controls},
                   "rate_judge_reported": rate, "pairs_with_conflict": n_conflicted,
                   "rows": rows}, open(a.out, "w"), indent=1)
        print(f"saved {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
