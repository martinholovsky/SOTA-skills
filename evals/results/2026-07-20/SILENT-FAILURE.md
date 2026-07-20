# Silent control failure — eval for `sota-code-security` rules/10

**Date:** 2026-07-20 · **Model:** `anthropic/claude-sonnet-4.6` ·
**Judge:** `anthropic/claude-opus-4.8` (open-ended design, blind to arm) ·
**Cases:** [`evals/cases/silent-failure.jsonl`](../../cases/silent-failure.jsonl) — **49**

> **Correction (same day).** An earlier version of this page reported a
> **+0.07** library lift from a **15-case** version of this set, and that number
> reached `RESULTS.md`. Growing the set to 49 cases **did not reproduce it**:
> the lift is **+0.03 (vocabulary design)** and **−0.01 (open-ended design)**,
> both inside run-to-run spread. **The +0.07 was small-sample noise and is
> retracted.** The scoreboard row has been corrected. This section is kept
> rather than deleted — the retraction is the result.

## What was measured

Whether the library helps a model detect a **silently inert control** — a check,
scanner, policy, or test that appears active but has no effect, so a broken
system and a working one look identical from outside. This is the class
[`rules/10`](../../../skills/sota-code-security/rules/10-silent-control-failure.md)
was added for (PR #119).

**49 cases:** 41 positives, **8 negative controls** (`not-silent` — the control
fails loudly, so flagging it is the error), and **6 of the positives tagged
`novel`** — mechanisms rules/10 does **not** enumerate (a case-sensitive
blocklist regex against lowercased input, an unawaited async authz check,
decorator/route ordering that bypasses an admin guard, inverted config-merge
precedence, a context timeout never attached to the request, a retry loop that
swallows its final failure). The novel subgroup is the **generalization probe**:
it separates "the guidance teaches the lens" from "the guidance recites its own
list". Languages: Python 30, Go 8, JS 4, YAML 3, TS/SQL/Dockerfile/Markdown 1 each.

Two designs, three arms each:

- **Vocabulary** (`run-clean.py`) — both arms get a 25-slug vocabulary naming the
  taxonomy. Measures *classification*.
- **Open-ended** (`run-silent-open.py`) — no vocabulary; free-form mechanism per
  case, graded by a **different** model blind to arm. Measures *discovery*.
- Third arm in both: **ablated** — the full skill *minus rules/10*.

## Results at n=49

| Design | Samples | Without | With (full) | With (ablated) | Library lift | rules/10 |
|---|---|---|---|---|---|---|
| Vocabulary | 3× @0.7 | 0.891 | **0.918** | 0.918 | **+0.03** | **+0.00** |
| Open-ended | 5× @1.0 | 0.935 | 0.927 | 0.910 | **−0.01** | +0.02 |

Per-arm run spread (open-ended): without 0.918–0.959, with 0.878–0.959, ablated
0.898–0.918. **Every difference in the table is smaller than the spread of the
arms producing it.**

Subgroup recall (open-ended, mean of 5):

| Subgroup | Without | With (full) | With (ablated) |
|---|---|---|---|
| **Novel** (6 unenumerated mechanisms) | **1.00** | 0.83 | 0.83 |
| **Negative controls** (8 loud failures) | 1.00 | 1.00 | 1.00 |

What the n=15 → n=49 change did: the added cases are harder, which **broke the
ceiling** (the with-arm was 0.99–1.00 at n=15, leaving no headroom to measure).
With headroom, the lift disappeared.

Reproduce:

```sh
python3 evals/run-clean.py --cases evals/cases/silent-failure.jsonl --samples 3 --temp 0.7
python3 evals/run-clean.py --cases evals/cases/silent-failure.jsonl --samples 3 --temp 0.7 --ablate
python3 evals/run-silent-open.py --samples 5 --temp 1.0
```

Artifacts: `silent-failure-49-3sample.json`, `silent-failure-49-ablated-3sample.json`,
`silent-open-49-5sample.json` (n=15 originals kept alongside for the comparison).

## Findings

**1. No measurable library lift on this dimension at n=49.** +0.03 in one design,
−0.01 in the other, both inside noise. The earlier +0.07 does not replicate.
Silent-control detection joins audit (+0.00), cross-file audit (+0.00) and
description-routing (+0.00) as a dimension where a frontier model, *once told
what to look for*, does not need the library.

**2. rules/10's own contribution is +0.00 / +0.02** — the ablated arm matches or
nearly matches the full arm in both designs. The vocabulary design is now clean
on this point: with and ablated are **identical (0.918, zero spread, same four
missed cases)**. The file adds nothing measurable on this set.

**3. The one signal worth acting on is negative: taxonomy anchoring.** On the six
mechanisms rules/10 does *not* list, the unguided arm scored **1.00** and both
library arms **0.83**. It is a one-case difference at n=6 — **not** statistically
solid — but it points the way the concern runs: a model handed an 11-item list
may pattern-match against the list instead of applying the underlying question.
That is precisely the failure mode the file's own §1 warns about. **Needs more
novel cases before it is a finding.**

**4. Four cases defeat every arm** (`sf18` Go release-build-tag no-op, `sf19`
`*.yaml` glob vs `.yml` files, `sf20` env filter `prod` vs `production`, `sf37`
unawaited `expect().rejects`). rules/10 §2.3 covers "empty ruleset" abstractly,
but neither the guidance nor the base model connects it to a *glob or filter that
silently matches nothing*. Tempting to add those examples to the rule — **that
would be fitting the guidance to the test set**, so it is logged, not done.

## Limitations (read before citing any number)

- **41 of 49 positives were authored from rules/10's own taxonomy.** Only 6 test
  generalization. That ratio should invert as the set grows.
- **n=49 gives 0.020 granularity**, but the *arms* vary by ±0.04, so the real
  resolution is worse than the case count suggests. Differences under ~0.05 are
  not interpretable here.
- **The novel subgroup is 6 cases.** Treat finding 3 as a hypothesis.
- **Single model, single judge pairing.** No cross-model replication.
- **Batched prompts** — all 49 cases in one call per arm, so cases prime each
  other. Matches `run-clean.py`'s existing design for comparability; not how a
  real audit arrives.
- **Both designs must state the task**, and that framing *is* the falsification
  question rules/10 teaches. So the eval hands every arm the lens and measures
  application. What the rule uniquely offers — asking unprompted — remains
  unmeasured by construction.

## What this changes

`RESULTS.md` corrected: the silent-control row now reads **no measurable lift**,
not +0.07.

rules/10 is **not** reverted, but its justification is now explicitly *not*
efficacy: it stands on being a documented gap-analysis result with no measured
harm on the enumerated classes. If the taxonomy-anchoring signal in finding 3
reproduces on a larger novel subgroup, that calculus changes and the file should
be rewritten to lead harder on the question and lighter on the list.

Open follow-ups: (a) grow the **novel** subgroup to 20+ so finding 3 resolves;
(b) the agentic design (large repo, generic "audit this", do silent no-ops appear
unprompted?) — the only design that can measure what this file is for;
(c) cross-model replication.
