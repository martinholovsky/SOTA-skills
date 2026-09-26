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
- **Lineage records the recipe, not just the result.** A dataset version names
  its components and every transformation, augmentation, filter and merge that
  produced it, so a bad source can be traced forward to every derived set.
  OWASP: AISVS 12.5.1.
- **Sign what a hash only identifies.** A content hash tells you the bytes
  changed; a signed attestation tells you who vouched for them. Put dataset
  manifests, RAG chunk sets and annotation exports under a signed attestation
  (e.g. an in-toto Statement in a DSSE envelope, `sota-devsecops` rules/02 §2.4).
  In a multi-stage pipeline (pre-processing, SFT, preference tuning,
  distillation) each stage verifies the attestation and digest of the previous
  stage's output before it reads it, and stops on a mismatch. OWASP: AISVS
  1.2.2, 3.5.3; AI-Powered Advertising Systems Security cheat sheet.

## 6. Data governance & PII

- Minimize personal data in features; collect/keep only what has a lawful basis
  and document it (`rules/07`, cross-ref `sota-privacy-compliance`). Don't use
  protected attributes as features unless justified and lawful; beware proxies.
- Track data provenance/consent so you can honor deletion and explain what a
  model was trained on.
- **Every training field earns its place.** Keep a field-to-purpose register:
  each column that enters training is justified by the model's stated purpose,
  and a field with no justification is dropped, not kept "in case". Keep
  financial settlement data (billing, payouts, invoices) in its own store; label
  materialisation reads a derived, minimised signal from it, never the ledger
  itself. OWASP: AISVS 1.1.1; AI-Powered Advertising Systems Security cheat
  sheet.
- **A reason code on every personal-data row.** A training corpus built from
  personal data admits a row only if it carries a consent or lawful-basis code
  an auditor can check (and a withdrawal can find). Treat consent strings
  themselves, such as IAB TCF TC strings, as personal data: the CJEU held in
  C-604/22 (7 March 2024) that a TC string is personal data where it can be
  linked to an identifier such as an IP address. OWASP: AI-Powered Advertising
  Systems Security cheat sheet.

## 7. Training-data admission

- **Labeling platform roles.** Separate who creates, who modifies and who
  approves annotations; no single account does all three on the same item, and
  approvals are logged with the approver. OWASP: AISVS 1.2.1.
- **Auto-generated labels are admitted, not assumed.** Pseudo-labels, weak
  labels and model-generated labels pass a confidence threshold and a
  consistency check (agreement with a second model or rule, or a sampled human
  review) before training uses them; rejected items go to review, not silently
  to training. OWASP: AISVS 1.3.2.
- **Quarantine outcomes that can still be overturned.** Outcome and reward
  events that a later verdict can flip (a click later judged invalid traffic, a
  purchase later charged back, a transaction later marked fraud) wait in
  quarantine for the adjudication window before they reach training. Then
  reconcile them against the verdicts and drop the flagged rows. Online and
  reinforcement learners, which cannot wait, cap how far the policy may move per
  update or epoch (a clipped or trust-region step), so a burst of forged rewards
  cannot drag the model far before the verdicts land (`rules/07` §1). OWASP:
  AI-Powered Advertising Systems Security cheat sheet.

## Audit checklist

- [ ] **Train/serve skew**: is the transformation that produces a training feature the
      *same code path* as the one serving it — a shared library or a feature store — or
      two implementations that must be kept in step by hand? Two implementations is the
      finding, whether or not they currently agree.
- [ ] **Point-in-time correctness**: does every training label join features **as of** the
      label's timestamp? A join that picks up feature values computed after the event
      leaks the future into training and inflates offline metrics — it will not reproduce
      in serving, which is how it is usually discovered.
- [ ] If a **feature store** is in use: are offline and online stores written from one
      pipeline, is freshness monitored per feature, and is a feature's serving default
      (on a store miss) the same value training saw for a missing feature?
- [ ] If one is **not** in use: what enforces the two answers above instead? "We are
      careful" is not a mechanism (`rules/01` §3).

- [ ] **Preprocessing leakage — CRITICAL** —
      `grep -rnE '\.fit(_transform)?\(' --include='*.py' . | grep -vE 'Pipeline|fit\(X_train|fit\(train'`
      (fit on full data?);
      `grep -rnE 'SMOTE|resample|SelectKBest|StandardScaler|fit_transform' --include='*.py' . # before split?`
- [ ] **Split correctness — CRITICAL/HIGH** —
      `grep -rnE 'train_test_split\(' --include='*.py' . | grep -v 'stratify\|TimeSeries\|Group'`
      (temporal/group needed?);
      `grep -rniE 'TimeSeriesSplit|GroupKFold|GroupShuffle' --include='*.py' . || echo "no temporal/group split — verify IID"`
- [ ] **Train/serve skew — CRITICAL Diff training feature code vs serving feature code; are
      served features logged for training?** —
      `grep -rniE 'feature.?store|feast|log.*feature|skew' --include='*.py' . | head`
- [ ] **Data/feature versioning — HIGH** —
      `out=$(grep -rniE 'dvc|lakefs|dataset.*hash|snapshot|data.?version' . 2>&1); rc=$?` ;
      `case $rc in 0) printf '%s\n' "$out" | head ;; 1) echo "no data versioning found" ;; *) echo "SWEEP FAILED, not a finding about their code: $out" ;; esac`
- [ ] **Data validation at entry — HIGH** —
      `grep -rniE 'great_expectations|pandera|tfdv|schema.*valid|expect_' --include='*.py' . || echo "no data validation"`
- [ ] **PII in features — HIGH (cross-ref sota-privacy-compliance)** —
      `grep -rniE 'email|ssn|phone|dob|address|name|ip_addr' --include='*.py' . | grep -i feature | head`
- [ ] **Signed dataset attestations and stage-to-stage verification (§5) — HIGH** —
      `grep -rniE 'in-toto|dsse|attest' . | grep -iE 'dataset|manifest|chunk|annotation|stage' || echo "no signed dataset attestation"`
      ; manual: does each pipeline stage verify the previous stage's output before use?
- [ ] **Purpose-bound fields and settlement data separated (§6) — MEDIUM** —
      `grep -rniE 'settlement|payout|invoice|billing' --include='*.py' --include='*.sql' . | grep -iE 'label|train|feature'`
      (each hit is a label or feature reading the ledger directly)
- [ ] **Per-row consent/lawful-basis code on training rows (§6) — HIGH** —
      `grep -rniE 'lawful_?basis|legal_?basis|consent_?(code|reason|basis)|tc_?string' . || echo "no per-row consent or lawful-basis code"`
- [ ] **Auto-label QA and labeling roles (§7) — MEDIUM** — auto-labels with no threshold on
      the same line:
      `grep -rniE '(pseudo|weak|auto)_?label' --include='*.py' . | grep -viE 'confidence|threshold|min_score'`
      ; manual: create/modify/approve separated on the labeling platform
- [ ] **Adjudication-window quarantine (§7) — HIGH where outcomes can be reversed** —
      `grep -rniE 'quarantine|adjudicat|chargeback|holdback' --include='*.py' --include='*.sql' . || echo "no quarantine before outcome events reach training"`
