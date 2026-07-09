# 01 — ML systems architecture

A production ML system is mostly *not* the model. The
[Hidden Technical Debt in ML Systems](https://research.google/pubs/hidden-technical-debt-in-machine-learning-systems/)
paper's famous point: the ML code is a small box in the middle of a large
system of data collection, feature extraction, serving, and monitoring — and
that surrounding system is where debt accumulates. Design the system, not just
the model.

## 1. The model is the small part

- [Rules of ML](https://developers.google.com/machine-learning/guides/rules-of-ml)
  #1–#4: don't be afraid to ship without ML; design and implement **metrics**
  first; a **simple model with a solid pipeline** beats a sophisticated model on
  a fragile one. Get the end-to-end pipeline (data → features → train → eval →
  serve → monitor) working with a trivial model, then improve the model inside
  that frame.
- Decide the prediction architecture up front: **batch** (precompute, store),
  **online/real-time** (serve on request), or **streaming**. This drives the
  feature and serving design (`rules/05`).

## 2. Training vs serving paths

- The training path (offline, large batch, historical data) and the serving
  path (online, low-latency, current data) are different code paths over the
  same logical features. If they compute features differently, you get
  **train/serve skew** (`rules/02`) — the most common silent production failure.
- Eliminate skew structurally: a **feature store** (e.g. Feast-style) or shared
  transformation code/library used by both paths, so a feature is defined once.

## 3. Feature store

- A feature store centralizes feature definitions, computes and **versions**
  features, serves them consistently to training (offline store) and inference
  (online store), and enables reuse across models. Its core value is
  **training-serving consistency** and point-in-time-correct historical lookups
  (no future leakage in the training join).
- Not every project needs a dedicated feature store — but it needs *one*
  definition of each feature shared by both paths. Reimplementing features in
  the serving app is a skew bug waiting to happen.

## 4. Model registry & artifacts

- A **model registry** (MLflow-style) is the source of truth for trained models:
  versioned artifacts with their metrics, data/code/config lineage, deployment
  label (version **aliases** like `@champion`/`@challenger` — MLflow deprecated
  fixed staging/production/archived stages in favor of aliases and tags), and
  approver. Promotion is an explicit, gated transition (`rules/04`, `rules/05`),
  not a file copy.
- Store the model with everything needed to reproduce and explain it: training
  data reference + hash, feature versions, hyperparameters, code commit,
  environment, and eval report.

## 5. Reproducibility is architectural

- Any model in production must be **rebuildable**: pin data (versioned/hashed),
  code (commit), config, environment (container/lockfile), and seeds (`rules/03`).
  "We can't reproduce the prod model" is a HIGH finding — you can't debug,
  audit, or safely retrain it.

## 6. The Hidden-Technical-Debt anti-patterns

Audit for these (Sculley et al.) — each is real ML debt:

- **Entanglement / CACE** ("Changing Anything Changes Everything"): no input is
  truly independent; adding/removing a feature or changing data shifts the whole
  model. Mitigate with isolation, versioning, and monitoring of model behavior.
- **Undeclared consumers**: other systems silently depend on your model's output
  — changing the model breaks them invisibly. Declare and access-control
  consumers.
- **Feedback loops**: the model influences its own future training data (direct)
  or another model's (hidden). Detect and break them; they make offline metrics
  lie.
- **Data dependencies cost more than code dependencies**: unstable/underutilized
  input signals. Version data sources; drop unused features (`rules/02`).
- **Glue code & pipeline jungles**: most of the system becomes plumbing around a
  general-purpose package; scrappy ETL accreting into an unmaintainable jungle.
  Refactor toward clean, tested components.
- **Configuration debt**: ML systems sprawl config (features, thresholds,
  data selection). Treat config as code — reviewed, versioned, validated.

## Audit checklist

```bash
# Reproducibility — HIGH if a prod model can't be rebuilt
#   Is there a versioned link model → (data hash, code commit, config, env)?
grep -rniE 'mlflow|wandb|model.?registry|model.?card|lineage' . | head
ls -R | grep -iE 'requirements|environment.ya?ml|poetry.lock|uv.lock|Dockerfile|conda'   # env pinned?

# Train/serve consistency — CRITICAL if features computed two ways
grep -rniE 'feature.?store|feast|transform' --include='*.py' . | head
#   Compare training feature code vs serving feature code — same source?

# Glue code / pipeline jungle / config sprawl — MEDIUM
grep -rniE 'TODO|FIXME|HACK|temp|quick' --include='*.py' . | grep -iE 'pipeline|feature|etl' | head
find . -name '*.ipynb' | head        # notebook-only training/serving == debt

# Undeclared consumers / feedback loops — MEDIUM/HIGH (manual)
#   Who reads the model's outputs? Does the model's action affect its future training data?

# Unused features kept in infra — LOW (Rules of ML: drop them)
```
