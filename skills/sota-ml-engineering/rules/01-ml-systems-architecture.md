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
- Every change to a model (registration, alias move, promotion, rollback,
  deletion) writes an append-only audit record: who, what, when, the approval
  reference. A registry whose history can be edited in place cannot answer
  "what served on the 3rd". Fine-tuning checkpoints that may ever be evaluated
  or served are registered as their own artifacts, with their own lineage, not
  kept as loose files beside the final model (dataset lineage: `rules/02` §5).
  OWASP: AISVS 3.5.4, 12.5.3.

## 5. Reproducibility is architectural

- Any model in production must be **rebuildable**: pin data (versioned/hashed),
  code (commit), config, environment (container/lockfile), and seeds (`rules/03`).
  "We can't reproduce the prod model" is a HIGH finding — you can't debug,
  audit, or safely retrain it.

## 6. Trust domains: training, evaluation, serving

- Training, evaluation and production inference are **separate trust domains**:
  separate credentials, separate network reach, and no path by which a training
  job can write to what serving reads except through the gated registry
  promotion (`rules/04`, `rules/05`).
- Training logs, checkpoints, intermediate outputs and the experiment tracker
  hold data and near-final weights; restrict them like production data. An
  experiment tracker started with no authentication (for example `mlflow
  server` without `--app-name basic-auth`, which runs the unauthenticated
  default app) exposes every run's artifacts to anyone who can reach it.
- Compute control planes are remote code execution by design: a Ray dashboard /
  job-submission API, a notebook server or a pipeline UI (e.g. Kubeflow) that
  accepts a job runs it. None is ever reachable unauthenticated or from outside
  its trust domain. Ray's jobs API is the worked case (CVE-2023-48022: remote
  code execution; the vendor's position is "keep Ray on a controlled network");
  token auth exists only since Ray 2.52.0 and is off by default — set
  `RAY_AUTH_MODE=token` *and* keep network isolation. HIGH on sight when exposed.
- Scope feature-store namespaces by purpose, so one model's pipeline cannot read
  or overwrite another's features, and rotate the credentials that write
  materialised features on the same cadence as other production credentials
  (`sota-secrets-management`). OWASP: AI-Powered Advertising Systems Security
  cheat sheet; Secure AI Model Ops cheat sheet.

## 7. The Hidden-Technical-Debt anti-patterns

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

- [ ] **Reproducibility — HIGH if a prod model can't be rebuilt Is there a versioned link model
      → (data hash, code commit, config, env)?** —
      `grep -rniE 'mlflow|wandb|model.?registry|model.?card|lineage' . | head` ;
      `ls -R | grep -iE 'requirements|environment.ya?ml|poetry.lock|uv.lock|Dockerfile|conda'`
      (env pinned?)
- [ ] **Train/serve consistency — CRITICAL if features computed two ways** —
      `grep -rniE 'feature.?store|feast|transform' --include='*.py' . | head` (compare training
      feature code vs serving feature code — same source?)
- [ ] **Glue code / pipeline jungle / config sprawl — MEDIUM** —
      `grep -rniE 'TODO|FIXME|HACK|temp|quick' --include='*.py' . | grep -iE 'pipeline|feature|etl' | head`
      ; `find . -name '*.ipynb' | head` (notebook-only training/serving == debt)
- [ ] **Undeclared consumers / feedback loops — MEDIUM/HIGH (manual) Who reads the model's
      outputs? Does the model's action affect its future training data?**
- [ ] **Unused features kept in infra — LOW (Rules of ML: drop them)**
- [ ] **Trust-domain separation (§6) — HIGH** — trackers started without auth:
      `grep -rnE 'mlflow (server|ui)' . | grep -v 'app-name'`
      (each hit is a tracker with no authentication); manual: do training jobs hold
      credentials that can write serving or feature-store namespaces they don't own?
- [ ] **Append-only model audit trail and registered checkpoints (§4) — MEDIUM (manual)** —
      can the registry's history be edited or deleted by the same role that promotes? Are
      evaluated checkpoints registered with lineage, or loose files?
