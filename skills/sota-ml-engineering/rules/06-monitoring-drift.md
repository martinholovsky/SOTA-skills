# 06 — Monitoring & drift

A model is not "done" at deploy — it decays. The world shifts away from the
training distribution, and offline metrics can't see it. An **unmonitored model
in production is a HIGH finding**: it can degrade silently for months. Monitor
inputs, outputs, and (as labels arrive) live performance, and trigger
retraining.

## 1. What drifts

*(advisory: definitions of the four drift kinds; detection is probed under §2, live performance under §3)*

- **Data/feature drift (covariate shift)**: the input distribution P(X) moves
  away from training. Detect *before* performance visibly drops.
- **Concept drift**: the relationship P(y|X) changes — the same inputs now map
  to different outcomes (seasonality, behavior change, an external shock).
- **Label/prediction drift**: the output distribution shifts.
- **Performance decay**: the actual metric falls — the ground truth, but you only
  see it once labels arrive (often delayed).

## 2. Detecting drift

- Compare live feature/prediction distributions to a training/reference window
  with statistical tests: **PSI** (Population Stability Index — common rule of
  thumb: >0.1 moderate, >0.25 significant shift; verify thresholds for your
  data), **KS test** for continuous features, chi-square/JS-divergence for
  categoricals. Tools: Evidently, NannyML, or built-in platform monitors
  (WhyLogs has had no release since 2024-12 — treat an existing use as dormant).
- Monitor per-feature and on the prediction distribution; alert on sustained
  shift, not single-batch noise.
- **Match the test to the input.** PSI/KS/chi-square suit tabular features.
  For text, images and audio, compare **embeddings** instead: distance between
  reference and live embedding distributions, maximum mean discrepancy (MMD),
  or a domain classifier trained to tell reference from live (accuracy near
  0.5 means no drift). Per-token or per-pixel statistics say little there.
- **Abrupt is not gradual.** Slow drift is expected and feeds the retraining
  trigger (§5). A sudden, unexplained step change in inputs, outputs or
  confidence is a different event (a broken upstream, an attack, a poisoned
  retrain) and pages on its own route with an investigate-first runbook, not
  an automatic retrain on the shifted data. OWASP: AISVS 12.3.1, 12.3.4.

## 3. Monitoring performance (the real signal)

- When labels arrive (even delayed), compute the **live metric** and compare to
  the offline expectation and to deployment-time performance. Account for
  **label lag** — design how/when ground truth is collected.
- Where labels are very delayed, use proxy/leading indicators and drift as early
  warning. NannyML-style performance *estimation* can approximate metric decay
  before labels land — treat as estimate, confirm with labels.

## 4. Operational & data-quality monitoring

- Monitor the serving system like any service: latency, throughput, error rate,
  resource use (cross-ref [`sota-observability`](../../sota-observability/SKILL.md)).
- Monitor **input data quality** at serving: schema conformance, null/NaN spikes,
  range violations, unexpected categories, feature freshness/staleness — a broken
  upstream feature is a common silent failure (ML Test Score monitoring tests).
- Watch for **training/serving skew** continuously by comparing logged served
  features to training ([`rules/02`](02-data-and-features.md)). The served-feature log
  carries the same PII minimisation as training data: mask or drop PII fields before
  logging ([`rules/07`](07-security-governance.md) §3, [`rules/02`](02-data-and-features.md) §6).
- Record the out-of-distribution flags raised by the inference-time gate
  ([`rules/07`](07-security-governance.md) §1) and trend their rate; a rising rate is early drift.

## 5. Retraining strategy

- Define the **retraining trigger** explicitly: scheduled (cadence matched to
  drift rate), or **drift/performance-triggered** (retrain when PSI or metric
  crosses a threshold). Don't retrain blindly on a timer if nothing changed, and
  don't wait for a complaint if drift is detected.
- Retraining runs the **same validated pipeline** with gates ([`rules/03`](03-training-experimentation.md),
  [`rules/04`](04-evaluation-validation.md)) — an automatically-retrained model still passes validation and
  progressive rollout before it serves. Beware feedback loops contaminating new
  training data ([`rules/01`](01-ml-systems-architecture.md)).
- Keep model/version history and the ability to roll back a bad retrain
  ([`rules/05`](05-deployment-serving.md)).

## 6. Alerting & ownership

- Drift/decay/data-quality alerts route to an owner with a runbook (what to
  check, when to retrain, when to roll back) — cross-ref [`sota-observability`](../../sota-observability/SKILL.md)
  and [`sota-detection-engineering`](../../sota-detection-engineering/SKILL.md) for alerting discipline. An alert nobody owns
  is noise.

## Audit checklist

- [ ] **Any production monitoring at all? — HIGH if none** (§2, §3) —
      `out=$(grep -rniE 'evidently|nannyml|whylogs|drift|psi|kolmogorov|ks_2samp|monitor' --include='*.py' . 2>&1); rc=$?` ;
      `case $rc in 0) printf '%s\n' "$out" | head ;; 1) echo "no drift/perf monitoring found — HIGH" ;; *) echo "SWEEP FAILED, not a finding about their code: $out" ;; esac`
- [ ] **Drift detection method present?** (§2) —
      `grep -rqiE 'population_stability|psi|ks_2samp|chi2|js_diverg|wasserstein' --include='*.py' . || echo "no drift detection method"`
- [ ] **Live performance tracking + label lag handling (§3) — HIGH** —
      `grep -rqiE 'ground.?truth|label.*lag|actual|delayed|backfill.*label|live.*metric' --include='*.py' . || echo "no live performance tracking"`
      ; manual: is ground-truth collection designed, and are performance estimates confirmed with
      labels once they land?
- [ ] **Data-quality/freshness monitoring at serving (§4) — MEDIUM/HIGH** —
      `grep -rqiE 'freshness|stale|null.*rate|schema.*serv|nan|range.*check' --include='*.py' . || echo "no serving data-quality monitoring"`
      ; manual: served features compared to training continuously, the served-feature log masks or
      drops PII before logging, and the OOD-flag rate is trended
- [ ] **Retraining trigger defined? — MEDIUM/HIGH** —
      `out=$(grep -rniE 'retrain|schedule|cron|airflow|trigger|cadence' . | grep -iE 'train|drift|model'); rc=$?` ;
      `case $rc in 0) printf '%s\n' "$out" | head ;; *) echo "no explicit retraining trigger (rc=$rc; if the first grep failed, rerun it alone)" ;; esac`
      ; manual, for each trigger found: trace the retrain job to promotion — does it pass the
      [rules/04](04-evaluation-validation.md) gate and the [rules/05](05-deployment-serving.md) progressive rollout (this file's §5)? A retrain that deploys
      directly = HIGH
- [ ] **Alerts have an owner/runbook (§6) — MEDIUM (manual)** — do drift, decay and data-quality
      alerts route to an owner whose runbook says what to check, when to retrain and when to roll back?
- [ ] **Drift method fits the data type; abrupt shifts routed apart (§2) — MEDIUM** — for
      text/image models: `grep -rniE 'embedding.?drift|mmd|mean.discrepancy|domain.?classifier' --include='*.py' . || echo "no embedding-level drift test"`
      ; manual: does a step change page separately instead of triggering a retrain?
