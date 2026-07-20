# Silent control failure — eval for `sota-code-security` rules/10

**Date:** 2026-07-20 · **Model:** `anthropic/claude-sonnet-4.6` ·
**Judge:** `anthropic/claude-opus-4.8` (open-ended design only, blind to arm) ·
**Cases:** [`evals/cases/silent-failure.jsonl`](../../cases/silent-failure.jsonl) (15)

## What was measured

Whether the library helps a model detect a **silently inert control** — a check,
scanner, policy, or test that appears active but has no effect, where a broken
system and a working one look identical from outside. This is the class
[`rules/10`](../../../skills/sota-code-security/rules/10-silent-control-failure.md)
was added for (PR #119).

The case set is 13 positives (one per hiding place in rules/10 — weak existence
checks, optional-dependency degradation, empty rulesets, swallowed enforcement
exceptions, overloaded flags, early-return and truncation bypasses, ignored
config keys, doc/code default drift, hardcoded report values, shipped-artifact
gaps, two vacuous tests) plus **2 negative controls** (`sf14`, `sf15`) where the
control fails *loudly* and the correct answer is "not silent". The negatives
exist because an arm that cries no-op at everything would otherwise score 1.00.
Languages are mixed (Python, Go, JS, YAML, Dockerfile) — the
[breadth run](../2026-07-13/BREADTH.md) showed domain effects are real.

Two designs were run, because the first cannot answer the question that matters:

- **Vocabulary design** (`run-clean.py`) — both arms get a 19-slug vocabulary
  that already enumerates the taxonomy. Measures *classification* once you know
  the classes exist.
- **Open-ended design** (`run-silent-open.py`) — no vocabulary. Free-form
  one-line mechanism per case, graded by a **different** model, blind to arm,
  against a reference mechanism. Measures *discovery*.

Both designs run a third arm: **ablated** — the full skill *minus rules/10* — to
isolate the new file's contribution from the other nine rules files.

## Results

| Design | Samples | Without | With (full) | With (ablated) | Full lift | **rules/10 contribution** |
|---|---|---|---|---|---|---|
| Vocabulary | 3× @0.7 | 0.87 | **1.00** | 1.00 | +0.13 | **+0.00** |
| Open-ended | 1× @0.0 | 0.87 | 0.93 | 0.93 | +0.07 | **+0.00** |
| Open-ended | 3× @0.7 | 0.93 | **1.00** | 0.93 | +0.07 | **+0.07** |
| Open-ended | 5× @1.0 | 0.92 | 0.99 | 0.95 | +0.07 | **+0.04** |

Reproduce:

```sh
python3 evals/run-clean.py --cases evals/cases/silent-failure.jsonl --samples 3 --temp 0.7
python3 evals/run-clean.py --cases evals/cases/silent-failure.jsonl --samples 3 --temp 0.7 --ablate
python3 evals/run-silent-open.py --samples 5 --temp 1.0
```

Raw artifacts: `silent-failure-3sample.json`, `silent-failure-ablated-3sample.json`,
`silent-open-{1,3,5}sample.json` in this directory.

## Findings

**1. The full library lifts detection: +0.07 to +0.13, consistently and in both
designs.** The with-library arm reaches 0.99–1.00; the unguided arm sits at
0.87–0.93. Unlike the audit evals, this dimension does **not** saturate at the
baseline — an unguided frontier model does miss some of these.

**2. rules/10's own marginal contribution is NOT resolvable at this case-set
size, and no lift is claimed for it.** Across four runs it lands between +0.00
and +0.07 — but one case is worth 0.067 at n=15, and the per-arm spread in the
5-sample run (±0.07) is as large as the effect. The 1-sample and 3-sample runs
disagree about *which* case each arm misses. That is noise, not a signal.
Honest statement: **the new file did not measurably improve detection over the
rest of `sota-code-security` on this set.**

**3. The reason is a ceiling, and the ceiling is partly built into the eval.**
Both designs must *state the task* — "report any control that appears active but
has no effect" — or the unguided arm has nothing to answer. But that framing
**is** the falsification question, which is the core of rules/10. So the eval
hands every arm the lens for free and then measures who applies it best. What
rules/10 actually contributes — knowing to ask the question **at all, unprompted,
during an ordinary audit** — is precisely what this design cannot measure.

This is the same wall the [cross-file audit](../2026-07-13/REPO-AUDIT.md) hit
(+0.00): once the task is posed clearly and the code fits in one context, a
capable model performs well unaided. The measurable frontier is **agentic** —
give an agent a large repo and a generic "audit this", and measure whether silent
no-ops appear in the findings at all. That run is not built yet.

## Limitations (read before citing any number)

- **The case set was authored from rules/10.** It tests the classes that file
  enumerates, not discovery of classes nobody wrote down. It cannot show the
  taxonomy is complete — only that these 13 instances are detectable.
- **n=15 with 1-case granularity (0.067).** Differences below ~0.13 are not
  resolvable. Growing the set is the fix, and is the logged follow-up.
- **Single model, single judge pairing.** No cross-model replication.
- **Batched prompts.** All 15 cases go in one call per arm, so cases can prime
  each other. This matches the existing `run-clean.py` design (comparability),
  but it is not how a real audit arrives one file at a time.
- **The negative controls work but are few.** `sf14`/`sf15` were answered
  correctly in nearly every run; two cases is thin protection against an
  over-flagging arm. `sf15` is the most-missed case in the with-library arm —
  weak evidence that heavy silent-failure guidance nudges toward over-flagging a
  loud, correct control. Worth watching as the set grows.

## What this changes

Nothing in the library is reverted. rules/10 stays on the evidence that (a) the
full library measurably leads on this dimension, (b) the file adds no measurable
*harm* (the with-arm is at or above the ablated arm in three of four runs), and
(c) its content is a documented gap-analysis result, not a guess. But **it is not
backed by a measured lift of its own**, and must not be cited as one.

The honest scoreboard entry is: *silent-control detection — full library
0.99 vs unguided 0.92 (+0.07); rules/10's marginal contribution unresolved.*
