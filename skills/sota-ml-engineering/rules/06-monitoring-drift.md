# 06 — Monitoring & drift

A model is not "done" at deploy — it decays. The world shifts away from the
training distribution, and offline metrics can't see it. An **unmonitored model
in production is a HIGH finding**: it can degrade silently for months. Monitor
inputs, outputs, and (as labels arrive) live performance, and trigger
retraining.

## 1. What drifts

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
  categoricals. Tools: Evidently, NannyML, WhyLogs, or built-in platform monitors.
- Monitor per-feature and on the prediction distribution; alert on sustained
  shift, not single-batch noise.

## 3. Monitoring performance (the real signal)

- When labels arrive (even delayed), compute the **live metric** and compare to
  the offline expectation and to deployment-time performance. Account for
  **label lag** — design how/when ground truth is collected.
- Where labels are very delayed, use proxy/leading indicators and drift as early
  warning. NannyML-style performance *estimation* can approximate metric decay
  before labels land — treat as estimate, confirm with labels.

## 4. Operational & data-quality monitoring

- Monitor the serving system like any service: latency, throughput, error rate,
  resource use (cross-ref `sota-observability`).
- Monitor **input data quality** at serving: schema conformance, null/NaN spikes,
  range violations, unexpected categories, feature freshness/staleness — a broken
  upstream feature is a common silent failure (ML Test Score monitoring tests).
- Watch for **training/serving skew** continuously by comparing logged served
  features to training (`rules/02`).

## 5. Retraining strategy

- Define the **retraining trigger** explicitly: scheduled (cadence matched to
  drift rate), or **drift/performance-triggered** (retrain when PSI or metric
  crosses a threshold). Don't retrain blindly on a timer if nothing changed, and
  don't wait for a complaint if drift is detected.
- Retraining runs the **same validated pipeline** with gates (`rules/03`,
  `rules/04`) — an automatically-retrained model still passes validation and
  progressive rollout before it serves. Beware feedback loops contaminating new
  training data (`rules/01`).
- Keep model/version history and the ability to roll back a bad retrain
  (`rules/05`).

## 6. Alerting & ownership

- Drift/decay/data-quality alerts route to an owner with a runbook (what to
  check, when to retrain, when to roll back) — cross-ref `sota-observability`
  and `sota-detection-engineering` for alerting discipline. An alert nobody owns
  is noise.

## Audit checklist

```bash
# Any production monitoring at all? — HIGH if none
grep -rniE 'evidently|nannyml|whylogs|drift|psi|kolmogorov|ks_2samp|monitor' --include='*.py' . | head \
  || echo "no drift/perf monitoring found — HIGH"

# Drift detection method present?
grep -rniE 'population_stability|psi|ks_2samp|chi2|js_diverg|wasserstein' --include='*.py' . | head

# Live performance tracking + label lag handling — HIGH
grep -rniE 'ground.?truth|label.*lag|actual|delayed|backfill.*label|live.*metric' --include='*.py' . | head

# Data-quality/freshness monitoring at serving — MEDIUM/HIGH
grep -rniE 'freshness|stale|null.*rate|schema.*serv|nan|range.*check' --include='*.py' . | head

# Retraining trigger defined? — MEDIUM/HIGH
grep -rniE 'retrain|schedule|cron|airflow|trigger|cadence' . | grep -iE 'train|drift|model' | head \
  || echo "no explicit retraining trigger"

# Alerts have an owner/runbook — MEDIUM (manual)
```
