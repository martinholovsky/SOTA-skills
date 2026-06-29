# 04 — Evaluation & validation

A single offline accuracy number is not evidence a model is ready. Evaluate
against the **business objective**, on **slices**, versus a **baseline**, and
gate promotion on automated **validation**. The
[ML Test Score](https://research.google/pubs/the-ml-test-score-a-rubric-for-ml-production-readiness-and-technical-debt-reduction/)
rubric (data / model / infra / monitoring tests) is the backbone.

## 1. Metrics that match the objective

- Pick metrics that reflect the real goal, not convenience. Accuracy is
  misleading on imbalanced data — use precision/recall/F1, PR-AUC, calibration,
  or a cost-weighted metric tied to the decision. For ranking: NDCG/MAP; for
  regression: MAE/RMSE/MAPE chosen for the loss that matters.
- Distinguish the **model metric** (offline) from the **business metric**
  (online) and state how they relate. Rules of ML: the offline metric is a proxy
  — validate it predicts the online outcome (`rules/06`).

## 2. Baselines and ablations

- Always compare to a baseline: a trivial predictor (majority class, last value,
  simple heuristic) and the **current production model**. "0.91 F1" is meaningless
  without "baseline 0.88, prod 0.90". A model that doesn't beat the baseline
  shouldn't ship.
- Ablate: does the new feature/complexity actually help on held-out data, or just
  fit noise?

## 3. Sliced evaluation and fairness

- Report metrics **per slice**, not just aggregate: by segment, geography,
  device, time, and protected/ sensitive groups where relevant. A model that
  wins on average can fail badly on a subgroup — aggregate metrics hide it
  (this is a core ML Test Score / fairness requirement). Set **minimum
  per-slice floors** for high-stakes models.
- Check calibration and error distribution, not just central tendency. Document
  known failure modes.

## 4. Validation gates before promotion

- Promotion to production is **gated** by automated checks (the ML Test Score
  "model development" + "infra" tests), run in CI/CD for ML:
  - metric ≥ threshold **and** no regression vs current production (within
    tolerance), on a fixed eval set;
  - per-slice floors met;
  - data/schema validation passed (`rules/02`);
  - the model is reproducible and registered with lineage (`rules/01`,`rules/03`);
  - a successful **shadow/canary** test where applicable (`rules/05`).
- A model that can't pass the gate doesn't get promoted — no manual override
  without sign-off. Missing a validation gate is HIGH.

## 5. Test the pipeline, not just the model

- The ML Test Score covers **infrastructure tests**: the training pipeline is
  reproducible, the full pipeline is integration-tested, model specs are
  unit-tested, the model can be rolled back, and serving matches training. Skew
  and serving correctness are tested, not assumed (`rules/02`, `rules/05`).
- Test for NaNs/inf, schema conformance, and that the model gives stable outputs
  on a canonical input (a "golden" prediction regression test).

## 6. Offline → online validation

- Offline wins don't guarantee online wins. Validate with an **online
  experiment** (A/B test / interleaving) measuring the business metric, with
  proper sample size and guardrail metrics, before full rollout (`rules/05`,
  `rules/06`). Beware feedback loops contaminating the comparison (`rules/01`).

## Audit checklist

```bash
# Single-metric / no-baseline evaluation — MEDIUM/HIGH
grep -rniE 'accuracy_score|f1_score|roc_auc|rmse|mae' --include='*.py' . | head
#   Is there a baseline + current-prod comparison? A single aggregate number is a finding.

# Sliced / fairness evaluation — HIGH if absent on a high-stakes model
grep -rniE 'group_?by|slice|segment|subgroup|fairness|by_cohort|disaggregat' --include='*.py' . \
  || echo "no sliced evaluation — aggregate metrics only"

# Validation gate before promotion — HIGH if missing
grep -rniE 'threshold|gate|promote|regression|assert.*metric|validate_model' --include='*.py' .ci* .github/ 2>/dev/null | head \
  || echo "no automated promotion gate found"

# Pipeline/model tests (ML Test Score infra) — HIGH
grep -rniE 'def test_|pytest|golden|integration' --include='*.py' . | grep -iE 'model|pipeline|predict|feature' | head

# Online experiment before full rollout — MEDIUM/HIGH
grep -rniE 'a/?b.?test|experiment|interleav|shadow|canary|holdout' . | head
```
