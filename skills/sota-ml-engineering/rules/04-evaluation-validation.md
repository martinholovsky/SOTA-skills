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
  — validate it predicts the online outcome ([`rules/06`](06-monitoring-drift.md)).

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
- Where inputs are attacker-influenced, the suite includes a **robustness
  slice**: adversarially perturbed versions of held-out inputs, with its own
  floor, so the hardening required by [`rules/07`](07-security-governance.md) §1 is measured. Where the
  model sees personal data, a **proxy audit** checks on every refresh that the
  model cannot be used to infer special-category attributes ([`rules/07`](07-security-governance.md) §3).
  OWASP: AISVS 11.1.4, 11.2.1.

## 4. Validation gates before promotion

- Promotion to production is **gated** by automated checks (the ML Test Score
  "model development" + "infra" tests), run in CI/CD for ML:
  - metric ≥ threshold **and** no regression vs current production (within
    tolerance), on a fixed eval set;
  - per-slice floors met;
  - data/schema validation passed ([`rules/02`](02-data-and-features.md));
  - the model is reproducible and registered with lineage ([`rules/01`](01-ml-systems-architecture.md),[`rules/03`](03-training-experimentation.md));
  - a successful **shadow/canary** test where applicable ([`rules/05`](05-deployment-serving.md)).
- A **quantised, pruned or distilled** artifact is a new model. It passes the
  same quality, safety and slice suite, run against the compressed binary
  itself, before it deploys; results measured on the full-precision parent do
  not carry over. OWASP: AISVS 3.2.2.
- A model that can't pass the gate doesn't get promoted — no manual override
  without sign-off. Missing a validation gate is HIGH.
- **Fit an operating threshold on held-out or out-of-fold scores, never on the rows
  the model was fit on.** An in-sample quantile ("flag above the 99th percentile of
  training benign scores") looks right for a weak model and collapses for a strong one,
  whose training scores sit far below anything unseen. So a capacity increase silently
  moves the real false-positive rate. Field-reported 2026-10-20: a nominal ~1% per head
  measured 34.7% on held-out benign rows. scikit-learn's `TunedThresholdClassifierCV`
  tunes on internal cross-validation by default, and its docs warn: "You should never use
  the same data for training the classifier and tuning the decision threshold due to
  the risk of overfitting." The threshold is part of the model, so it is versioned and
  re-derived with it.
- **Every decision rule reports what it evaluated, not only what passed**, for example
  `rule 2: 27 evaluated, 2 pass, 1 hurt, 24 n.s.`. A report of passes alone cannot show a
  comparison that was never run. Select the population by **exact identity**: an explicit
  list of names, or a set difference against one. Never select it by a prefix or suffix
  test, since `name.endswith("_max")` also matches `sfx_max`. Field-reported 2026-10-20: a
  suffix filter dropped 4 of 27 comparisons, among them the strongest result, and the
  passes-only report showed nothing missing. Assert `evaluated == expected` before printing
  any verdict ([`sota-code-security` rules/11](../../sota-code-security/rules/11-dead-path-diagnostics.md): a gate whose silence and whose skip look
  the same is not a gate).

## 5. Test the pipeline, not just the model

- The ML Test Score covers **infrastructure tests**: the training pipeline is
  reproducible, the full pipeline is integration-tested, model specs are
  unit-tested, the model can be rolled back, and serving matches training. Skew
  and serving correctness are tested, not assumed ([`rules/02`](02-data-and-features.md), [`rules/05`](05-deployment-serving.md)).
- Test for NaNs/inf, schema conformance, and that the model gives stable outputs
  on a canonical input (a "golden" prediction regression test).

## 6. Offline → online validation

- Offline wins don't guarantee online wins. Validate with an **online
  experiment** (A/B test / interleaving) measuring the business metric, with
  proper sample size and guardrail metrics, before full rollout ([`rules/05`](05-deployment-serving.md),
  [`rules/06`](06-monitoring-drift.md)). Beware feedback loops contaminating the comparison ([`rules/01`](01-ml-systems-architecture.md)).

## Audit checklist

- [ ] **Single-metric / no-baseline evaluation — MEDIUM/HIGH** —
      `grep -rniE 'accuracy_score|f1_score|roc_auc|rmse|mae' --include='*.py' . | head` (is there
      a baseline + current-prod comparison? A single aggregate number is a finding.)
- [ ] **Sliced / fairness evaluation — HIGH if absent on a high-stakes model** —
      `grep -rniE 'group_?by|slice|segment|subgroup|fairness|by_cohort|disaggregat' --include='*.py' . || echo "no sliced evaluation — aggregate metrics only"`
- [ ] **Validation gate before promotion — HIGH if missing** —
      `err=$(grep -rniE 'threshold|gate|promote|regression|assert.*metric|validate_model' --include='*.yml' --include='*.yaml' . 2>&1 >/dev/null); rc=$?` ;
      `case $rc in 0) ;; 1) echo "no automated promotion gate in CI config" ;; *) echo "SWEEP FAILED, not a finding about their code: $err" ;; esac`
      (the previous form piped through `head`, which exits 0, so its fallback could never fire)
- [ ] **Operating threshold fit in-sample (§4) — HIGH where the threshold gates a decision** —
      `grep -rnE '(quantile|percentile)\(' --include='*.py' .`: for each hit that sets a
      threshold, are the scores held-out or out-of-fold, or the training rows?
- [ ] **Decision report without a denominator (§4) — MEDIUM** — does every rule print its
      evaluated count beside its verdicts, and is the population an explicit list?
      Name-shape filters to read: `grep -rnE '\.(endswith|startswith)\(|rpartition\(' --include='*.py' .`
- [ ] **Pipeline/model tests (ML Test Score infra) — HIGH** —
      `grep -rniE 'def test_|pytest|golden|integration' --include='*.py' . | grep -iE 'model|pipeline|predict|feature' | head`
- [ ] **Online experiment before full rollout — MEDIUM/HIGH** —
      `grep -rniE 'a/?b.?test|experiment|interleav|shadow|canary|holdout' . | head`
- [ ] **Compressed artifact re-validated (§4) — HIGH** — files that quantise, prune or
      distil: `grep -rnliE 'quantiz|quantis|prune|pruning|distil' --include='*.py' --include='*.yml' --include='*.yaml' .`
      ; manual: does the gate run the eval suite on the compressed output, not the parent?
- [ ] **Robustness slice where inputs are attacker-influenced (§3) — HIGH** — see the
      robustness item in [`rules/07`](07-security-governance.md); manual: is there a per-slice floor for it?
