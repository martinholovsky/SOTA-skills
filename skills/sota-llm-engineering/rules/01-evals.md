# Rules 01 — Evals: the centerpiece of LLM engineering

Evals are to LLM features what tests are to deterministic code — except the
system under test is probabilistic, the dependency changes underneath you, and
"correct" is often graded, not boolean. Every other rules file in this skill
assumes the discipline defined here. If a codebase has LLM calls and no evals,
that is the first and most important finding of any audit.

## 1. Eval-first development

**Write the eval before the feature.** The eval *is* the spec: it forces you
to define what "good" means before you burn days prompt-twiddling against
vibes. The loop is:

1. Collect 20+ representative inputs (real ones where possible — support
   tickets, actual documents, real queries), including hard cases, edge
   cases, and cases where the correct behavior is *refusal or "I don't know"*.
2. Define graded criteria per case (expected output, rubric, or assertions).
3. Build the simplest pipeline that could work; run the eval.
4. Do error analysis (§6); fix the biggest failure class; re-run. Repeat.
5. Gate the merge on the eval (§5). Ship. Sample production into the eval
   set continuously (§7).

```yaml
# GOOD — eval case checked into repo next to the feature (promptfoo-style;
# any harness works: promptfoo, Braintrust, LangSmith, DeepEval, in-house)
- vars:
    ticket: "I was charged twice for my March invoice, order #4521"
  assert:
    - type: is-json
    - type: javascript
      value: output.category === 'billing' && output.priority === 'high'
    - type: llm-rubric
      value: "Summary mentions duplicate charge AND order number 4521"
```

```python
# BAD — "tested" by running it once in a notebook
resp = llm(f"Categorize this ticket: {ticket}")
print(resp)  # "looks right" → shipped
```

**Sizing:** 20–50 cases to start; 100–500 for a mature production feature.
Below 20, scores are noise (one flipped case = 5 points). Weight the set
toward observed failure modes, not what was easy to generate.

**Synthetic data is a bootstrap, not a destination.** LLM-generated cases are
fine to reach v1 coverage; replace them with sampled production data as it
arrives. Mark provenance (`source: synthetic|production|incident`) so you can
track the ratio — an eval set that is still >50% synthetic after months in
production is a Medium finding.

## 2. Eval types — pick the cheapest grader that captures the criterion

Order of preference (cheapest/most reliable first):

| Type | Use for | Notes |
|---|---|---|
| **Code assertions** | Format, schema validity, length, required/forbidden strings, citations resolve, latency/cost ceilings, classification vs gold label | Deterministic, free, zero judge bias. Always start here — a surprising fraction of "quality" is assertable. |
| **Golden-set exact/fuzzy match** | Extraction, classification, SQL/code with executable check | Execute generated code/SQL against fixtures and compare *results*, not strings. |
| **Rubric scoring (LLM-judge)** | Graded qualities: faithfulness, completeness, tone, helpfulness | Decompose into binary sub-criteria (see below). |
| **Pairwise comparison (LLM-judge)** | A/B between prompts/models when absolute scores are unstable | Judges are far more reliable at "which is better" than "score 1–10". Use for regression decisions; randomize order (position bias). |
| **Human review** | Calibrating judges, high-stakes spot checks, novel failure discovery | Too expensive as the routine grader; indispensable as ground truth. |

**Decompose rubrics into binary checks.** "Rate quality 1–10" produces
incoherent, drift-prone scores. Ask N yes/no questions and aggregate:

```text
# GOOD judge prompt (one binary criterion per call or per structured field)
Does the answer make any claim not supported by the provided context?
Answer with JSON: {"unsupported_claim": true|false, "quote": "<the claim or empty>"}

# BAD judge prompt
Rate this answer's quality from 1 to 10.
```

Force the judge to **quote evidence** — it grounds the verdict and makes
judge errors auditable. Use structured output for the verdict (rules/02).

## 3. LLM-as-judge: validate the judge or don't trust it

An unvalidated judge is a random-ish number generator with a convincing tone.
Before judge scores gate anything:

1. **Label 50–100 outputs by hand** (or with domain experts).
2. **Measure agreement** (raw % and Cohen's κ for class imbalance) between
   judge and humans. Target ≥85–90% agreement on binary criteria; below
   ~75%, fix the judge prompt or drop the criterion.
3. **Inspect disagreements** — they reveal either a bad rubric (humans
   disagree with each other too) or a judge failure mode.
4. **Re-validate when the judge model or judge prompt changes.** A judge
   model upgrade is a metric change; treat it like one.

Known judge biases — design around them:

- **Position bias** (pairwise): judges favor the first answer. Run both
  orderings; a result that flips with order is a tie.
- **Verbosity/style bias**: longer, confident, well-formatted answers score
  higher regardless of correctness. Add explicit rubric language ("length
  and formatting are irrelevant") and assert it during validation.
- **Self-preference**: a model grades its own family's outputs higher. Use a
  different model (or at least a different family) as judge than generator
  where the eval compares providers.
- **Sycophancy to the reference**: if you show the judge a reference answer,
  it anchors; if you don't, it hallucinates a standard. Decide deliberately
  per criterion (faithfulness → show context; format → no reference needed).

Judge calls are LLM calls: pin the judge model version, trace them, and keep
the judge prompt versioned in the repo. A silent judge-model auto-upgrade
invalidates every historical score (High finding).

## 4. Offline vs online evals

**Offline (pre-merge/pre-deploy):** golden sets + assertions + judges, run on
demand and in CI. Deterministic harness: pinned model versions, fixed
seeds/params where supported, retries for transient errors but never silent
re-grading until pass.

**Online (production):** sampled judging of live traffic, user signals
(thumbs, edits, regenerations, abandonment, task completion), canary
comparisons. Online tells you about real distribution; offline tells you
*why* and gates changes. You need both; conflating them ("we monitor thumbs,
that's our eval") is a High finding — thumbs are sparse, biased toward anger,
and arrive too late to gate anything.

Run online judges on a sample (1–10% of traffic, 100% of flagged/escalated
interactions), asynchronously, never in the request path.

## 5. Regression gates in CI

The eval suite must run automatically on every change to prompts, templates,
retrieval config, model IDs, or pipeline code — and block the merge.

```yaml
# GOOD — CI job (provider-agnostic shape)
llm-evals:
  if: changed(prompts/**, src/llm/**, evals/**)
  run: evals run --suite core --output results.json
  gate:
    - pass_rate >= baseline.pass_rate - 0.02   # tolerance for grader noise
    - no_regression_on: [tagged:incident, tagged:safety]   # hard cases never regress
    - p50_cost_per_case <= baseline * 1.2
```

Gate rules that work in practice:

- **Compare to a stored baseline, not an absolute number** — absolute
  thresholds rot as the set grows.
- **A small tolerance band** absorbs judge noise; pair it with a hard zero-
  regression rule on incident-derived and safety-tagged cases.
- **Gate cost and latency too** — a prompt change that doubles tokens "passes"
  quality and fails the budget.
- **Run the suite against model-deprecation candidates** ahead of forced
  migrations, and against any model you intend to switch to (rules/05).
- Keep a `fast` suite (assertions only, minutes) for every PR and a `full`
  suite (judges, larger set) for merge-to-main/nightly if judge cost bites.

Eval results are artifacts: persist run ID, git SHA, model versions, scores
per case. "We can't reproduce last month's score" means you don't have evals,
you have anecdotes.

**A replay harness is not an eval.** Recorded-trace or cassette replay —
re-ingesting captured requests and responses instead of calling the model — is
worth having, but it re-executes nothing, so it tests your pipeline's
determinism (parsing, schema drift, orchestration, tool wiring), not the
system's behavior. Wired into the gate as if it were the suite above, it yields
a CI job that stays green through a prompt rewrite, a model swap, or a
retrieval change, because none of those are on the replayed path — and the
greenness is indistinguishable from the real thing. Declare per suite what is
**live** and what is **replayed**, and apply the falsification question
(`sota/SKILL.md` BUILD step 4): if your quality gate would still pass with the
model endpoint unreachable, it is measuring the harness (`sota-code-security`
rules/10).

## 6. Error analysis discipline

Scores tell you *that* something is wrong; error analysis tells you *what to
do*. This is the highest-leverage activity in LLM engineering and the most
commonly skipped.

- **Read the failures.** Every eval run, open the transcripts of failed
  cases. No dashboard substitutes for reading model output.
- **Open coding → axial coding:** annotate each failure with a free-text
  note, then cluster notes into a failure taxonomy (e.g. `missed-table-data`,
  `wrong-date-format`, `over-refusal`, `retrieval-miss`). Fix the biggest
  cluster first; one targeted fix to the top cluster beats five speculative
  prompt tweaks.
- **Attribute the failure to a pipeline stage** before touching the prompt:
  for RAG, was the right chunk even retrieved (rules/03)? For agents, which
  tool call diverged (rules/04)? Most "prompt problems" are upstream
  data/retrieval problems.
- **Each fixed failure becomes a permanent eval case** tagged with its
  taxonomy label and `source: incident`. The eval set is the institutional
  memory of every bug.

## 7. Production sampling into eval sets

Production is the only honest distribution. Build the loop:

- Sample N traces/day (random + stratified by route/intent) into a review
  queue; promote reviewed cases (with corrected expected output) into the
  golden set.
- Auto-promote every trace behind a user complaint, regeneration, support
  escalation, or incident.
- **De-duplicate and decay**: cap near-duplicate cases, retire cases that no
  longer reflect the product. Date-stamp every case.
- Respect privacy: redact PII before a trace enters the eval repo
  (rules/06, sota-privacy-compliance).

## 8. Metric pitfalls

- **Contamination:** never tune prompts against the eval set you gate on.
  Maintain a dev set for iteration and a held-out set for gating; refresh
  the held-out set periodically from production. Public benchmark numbers
  (MMLU-style) are marketing, not product evals — frontier models have seen
  them; never select a model for your task on public benchmarks alone.
- **Goodharting the judge:** once a judge gates merges, prompts evolve to
  please the judge (longer, more confident, rubric-keyword-stuffed). Counter
  with periodic human calibration (§3) and pairwise checks against older
  baselines.
- **Aggregate masking:** a flat overall score can hide a new failure class
  offset by an improvement elsewhere. Always report per-tag/per-cluster
  scores alongside the aggregate.
- **Non-determinism denial:** run flaky-graded cases k times and report
  pass^k or mean — a criterion that flips run-to-run at temperature 0-ish
  settings is telling you the behavior is unstable, which is itself a
  finding about the feature, not the eval.
- **Eval-set overfit via retries:** harnesses that auto-retry until pass
  inflate scores. Retries are for transport errors only.

## Audit checklist

- [ ] Every shipped LLM feature has an eval suite in the repo, runnable by one
      documented command. (Absent → High; absent on consequential output with
      no human gate → Critical.)
- [ ] Golden set ≥20 cases, includes hard/edge/refusal cases, provenance
      tagged, not majority-synthetic after months in production.
- [ ] Cheapest-grader rule followed: assertions where assertable; judges only
      for genuinely graded qualities; rubrics decomposed into binary checks
      with quoted evidence.
- [ ] Any LLM-as-judge validated against ≥50 human labels with measured
      agreement; re-validated on judge model/prompt change; judge model
      pinned and traced.
- [ ] Pairwise comparisons run in both orders; verbosity/position bias
      addressed.
- [ ] Evals run automatically in CI on prompt/model/pipeline changes and
      block merge; baselines stored; zero-regression rule on incident/safety
      tags; cost/latency gated alongside quality.
- [ ] Eval runs persisted as artifacts (run ID, SHA, model versions,
      per-case results) and reproducible.
- [ ] Each suite declares what is **live** vs **replayed**, and the quality
      gate fails with the model endpoint unreachable — a replay-only gate
      measures the harness, not the model.
- [ ] Online signal exists (sampled judging and/or user feedback) and is
      distinct from — not a substitute for — offline gates.
- [ ] Error-analysis loop visible in history: failure taxonomy, incident
      cases promoted into the set.
- [ ] Dev set ≠ gating set; no prompt tuning against the held-out set; no
      model selection justified by public benchmarks alone.
