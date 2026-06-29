# 02 — Data and features: leakage, skew, versioning

Most ML production failures are data failures, not model failures. The two
deadliest are **data leakage** (offline metrics lie) and **train/serve skew**
(online behavior diverges from offline). Both are silent — the model looks
great and predicts badly.

## 1. Data leakage — the metric-inflating CRITICAL

Leakage is any information in training features that won't legitimately be
available at prediction time (or that encodes the target). It produces
spectacular offline metrics and a model that fails in production.

- **Target/label leakage**: a feature that is a proxy for, or derived after, the
  label (e.g. "account_closed_date" predicting churn; an aggregate computed over
  a window that includes the outcome).
- **Preprocessing leakage**: fitting scalers, encoders, imputers, feature
  selection, or resampling on the **full** dataset before the train/test split —
  the test set leaks into training. Fit transforms on **train only**, inside the
  CV fold (use a `Pipeline` so fit happens per-fold).
- **Temporal leakage**: using future data to predict the past. For time series,
  split **temporally** and ensure every feature is point-in-time correct (only
  data available at the prediction timestamp).
- **Group leakage**: the same entity (user, patient) in both train and test
  inflates metrics — use **grouped** splits.

```python
# BAD — scaler fit on all data before split: test leaks into train
X = StandardScaler().fit_transform(X_all); train, test = split(X)
# GOOD — fit inside the pipeline, per fold
pipe = Pipeline([("scale", StandardScaler()), ("clf", model)])
cross_val_score(pipe, X_train, y_train, cv=TimeSeriesSplit())
```

## 2. Train/serve skew

- Skew = features (or their distribution) differ between training and serving.
  Causes: features computed by different code in the two paths; different data
  sources; time-of-day/freshness differences; a transform applied in training
  but missing in serving.
- Fix structurally (`rules/01`): one feature definition (feature store / shared
  transform) used by both. Then **detect** residual skew by logging served
  feature values and comparing their distribution to training (Rules of ML #29:
  *the best way to make sure you train like you serve is to log features at
  serving time and use them to train*).

## 3. Splits and validation design

- Choose the split to match deployment reality: random for IID; **temporal** for
  anything time-ordered (forecasting, any "predict the future" task); **grouped**
  when rows share an entity. A wrong split silently leaks.
- Keep a held-out test set touched only at the end; use CV on train for model
  selection. Never tune on the test set.

## 4. Feature engineering discipline

- Prefer few, well-understood features; start with directly-observed/reported
  features before learned ones (Rules of ML). Document each feature's source,
  semantics, and freshness.
- **Drop unused/underperforming features** — they're data dependencies that cost
  maintenance and add skew surface (Hidden Technical Debt, `rules/01`).
- Handle missing values and categoricals deliberately and identically in both
  paths; don't let a serving-time unseen category crash or silently mis-encode.

## 5. Data & feature versioning

- Version training **data** (dataset snapshot/hash, DVC/lakeFS-style or a
  warehouse snapshot) and **feature definitions** so a model's inputs are
  reproducible (`rules/01`). "Which data trained this model?" must have an exact
  answer.
- Validate data **schema and distribution** at pipeline entry (types, ranges,
  nullability, expected categories) — catch a broken upstream feed before it
  trains a bad model. (TFX-DV / Great Expectations-style; cross-ref
  `sota-data-engineering` for pipeline contracts.)

## 6. Data governance & PII

- Minimize personal data in features; collect/keep only what has a lawful basis
  and document it (`rules/07`, cross-ref `sota-privacy-compliance`). Don't use
  protected attributes as features unless justified and lawful; beware proxies.
- Track data provenance/consent so you can honor deletion and explain what a
  model was trained on.

## Audit checklist

```bash
# Preprocessing leakage — CRITICAL
grep -rnE '\.fit(_transform)?\(' --include='*.py' . | grep -vE 'Pipeline|fit\(X_train|fit\(train'  # fit on full data?
grep -rnE 'SMOTE|resample|SelectKBest|StandardScaler|fit_transform' --include='*.py' . # before split?

# Split correctness — CRITICAL/HIGH
grep -rnE 'train_test_split\(' --include='*.py' . | grep -v 'stratify\|TimeSeries\|Group'  # temporal/group needed?
grep -rniE 'TimeSeriesSplit|GroupKFold|GroupShuffle' --include='*.py' . || echo "no temporal/group split — verify IID"

# Train/serve skew — CRITICAL
#   Diff training feature code vs serving feature code; are served features logged for training?
grep -rniE 'feature.?store|feast|log.*feature|skew' --include='*.py' . | head

# Data/feature versioning — HIGH
grep -rniE 'dvc|lakefs|dataset.*hash|snapshot|data.?version' . | head || echo "no data versioning found"

# Data validation at entry — HIGH
grep -rniE 'great_expectations|pandera|tfdv|schema.*valid|expect_' --include='*.py' . || echo "no data validation"

# PII in features — HIGH (cross-ref sota-privacy-compliance)
grep -rniE 'email|ssn|phone|dob|address|name|ip_addr' --include='*.py' . | grep -i feature | head
```
