# Pre-registration — ROADMAP 12: does one description mis-route the verification job?

**Written 2026-09-09, BEFORE any model call.** The twelve cases in
[`evals/cases/skill-split-code-security.jsonl`](../../cases/skill-split-code-security.jsonl)
were written and committed first, blind; nothing has been run against them.

## Why this exists

ROADMAP 12 has proposed splitting `sota-code-security` since 2026-07. It was parked on
two reasons, both re-tested on 2026-09-07 and one of them still true: a split does not
solve the line cap (invariant 1 is per *file*, and a split moves files without shrinking
one), and it costs router lines (much less than it did — the router is at 410/500 and a
new skill costs one routing-table row plus a library-map entry).

The **trigger** was a file count: "split when the verification half reaches N files." That
trigger fired on 2026-09-06 and the answer was still no, which is the tell that the
trigger was a **proxy**. Same shape as the router's own 500-line cap, which proxied an
unmeasured fear and read flat at 2.6× the length.

The thing a count was proxying for is **routing**. One `description` is the entire
auto-load classifier for two different jobs:

- `rules/01–09` — name a vulnerability **class** in code (SQLi, authz, uploads, crypto).
- `rules/10–15` — verify a **control** does something (inert gates, empty comparands,
  coverage censuses, evidence-producing scripts).

ROADMAP 12's replacement trigger, written 2026-09-07: *split when a routing measurement
shows the combined description mis-classifies verification-shaped tasks.* This is that
measurement.

## Design

`evals/run-desc-routing.py` over the new set: a model picks one skill from the catalogue
of all 41 descriptions, given a task. Six vulnerability-shaped cases and six
verification-shaped ones, paired across comparable surfaces (auth, CI, parsers, crypto,
logging, uploads). `expect` is `sota-code-security` for **all twelve** — the router's
cross-cutting rule 20 already says a "does this control actually do anything?" task
routes there.

- Model: `anthropic/claude-sonnet-5` · samples **3** · temp **0.7** · both arms
  (with-xref and without-xref, the runner's standing ablation, kept as a free control).
- Metric: per-half mean correct-pick rate, and the **gap** between them.
- Cost: 12 × 2 × 3 = **72 calls**, objective scoring, no judge.

## Predictions, with numbers, fixed before the run

**H1 — the description mis-routes the verification job.** Verification half ≤ **0.70**
*and* vulnerability half ≥ **0.90**, i.e. a gap ≥ **0.20**. This is the only result that
constitutes a routing argument for a split.

**H0 — no routing argument exists.** Both halves ≥ **0.85** and the gap ≤ **0.10**. Then
the replacement trigger reads negative, and ROADMAP 12 closes: the count trigger was a
proxy, the routing trigger is the real one, and it says no.

**Anything between** is a dead zone: reported as inconclusive, and **no split**. A
skill-level split is expensive and irreversible-ish; an ambiguous number does not buy it.

### A result in H1's direction does NOT mean "split the skill"

Registered now, because this is where the temptation lands. If the verification half
routes badly, the **cheap fix is tried first**: add verification vocabulary to the
existing description — the exact fix that repaired `r1_token_count` in v1.38.0 with one
keyword — and re-measure on this same set. Only a gap that **survives** that edit is
evidence that one description cannot carry two jobs. A split proposed on the strength of
the first number would be a fix chosen before the cheaper one was tested.

### The falsification condition

H1 is refuted if the verification half reads above 0.70, or the gap is under 0.20. It
will not be rescued by rewriting cases, dropping the ones that route "correctly for the
wrong reason", or re-labelling a `distractor` pick as acceptable.

## What could make this measure nothing

- **A ceiling.** If both halves read 1.00, the set is too easy and the run is
  **uninformative rather than null**. Reported that way, and the honest follow-up is
  harder verification-shaped cases — not a different threshold.
- **`expect` is a judgement.** All twelve expect `sota-code-security`. For the
  verification half a pick of `sota-testing` or `sota-devsecops` is *defensible* in prose
  even though rule 20 says otherwise; that is the whole point of the measurement, but it
  means a low score is evidence about the **description**, not proof the model was wrong.
- **12 cases, one model, one day.** A routing number is a gap between a description and a
  classifier, and the classifier side moves. This number is dated to `sonnet-5`.
- **The distractors are chosen, not sampled.** They are the siblings that share surface
  vocabulary, so distractor-pick rate here is an upper bound on confusability, not a
  population estimate.
- **The two halves are not matched on difficulty**, only on surface. If the verification
  tasks are simply longer or more abstract, that confound is in the number and cannot be
  separated at this design.

## Status

Not yet run. Live spend on the operator's account, authorised 2026-09-09.
