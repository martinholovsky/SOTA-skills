# 03 — Training & experimentation

Training must be **reproducible** and **tracked**, or you can't compare models,
rebuild a production model, or explain a result. The discipline here is the
difference between "we got 0.92 once in a notebook" and a model you can ship and
defend.

## 1. Experiment tracking

- Track every run: code version (commit), data version/hash, feature set,
  hyperparameters, environment, metrics, and artifacts — with a tool (MLflow,
  Weights & Biases, or equivalent), not a spreadsheet. Untracked experiments are
  unreproducible and uncomparable (MEDIUM debt).
- Log enough to answer "why did model B beat model A?" — same eval data, same
  metric definitions, recorded deltas.

## 2. Reproducibility

- Pin and record: random **seeds** (numpy/framework/CUDA where feasible),
  library versions (lockfile), the data snapshot, and config. Containerize the
  training environment.
- Note nondeterminism you can't remove (GPU kernels, parallelism) and bound it —
  report metric variance across seeds rather than a single lucky number.
- A training run should be a parameterized, version-controlled **pipeline**, not
  a hand-run notebook. Notebooks are fine for exploration; production training is
  code ([`rules/01`](01-ml-systems-architecture.md)).

## 3. Configuration management

- Treat experiment config as code: versioned, reviewed, validated (typed config
  — Hydra/pydantic-style). Avoid magic numbers scattered across scripts
  (configuration debt, [`rules/01`](01-ml-systems-architecture.md)).
- Separate config from code so a run is fully described by (code commit +
  config + data version).

## 4. Hyperparameter search

- Use a principled search (grid for small spaces, random/Bayesian/Optuna-style
  for larger) with a fixed validation protocol; never tune on the test set
  ([`rules/02`](02-data-and-features.md)). Budget it — log all trials to the tracker.
- Guard against overfitting the validation set through many trials: keep a final
  held-out test untouched until the end; consider nested CV for small data.

## 5. Distributed & large-scale training

- For multi-GPU/multi-node: checkpoint regularly (resume from failure), make
  data loading deterministic where it matters, and verify the effective batch
  size / LR scaling. Checkpoints are part of the reproducible artifact set.
- Cost-awareness: training is expensive — track GPU-hours; use spot/preemptible
  with checkpointing; don't retrain from scratch when a warm start or incremental
  update suffices (cross-ref [`sota-performance`](../../sota-performance/SKILL.md), [`sota-cloud-infrastructure`](../../sota-cloud-infrastructure/SKILL.md)).

## 6. Start simple, iterate inside the pipeline

- First model: simplest thing that beats the baseline, wired through the full
  pipeline with metrics and monitoring ([`rules/01`](01-ml-systems-architecture.md), [`rules/04`](04-evaluation-validation.md)). Add complexity
  only when the eval (on slices, vs baseline) justifies it. Most gains come from
  better features and data, not fancier models (Rules of ML).

## Audit checklist

- [ ] **Experiment tracking present? — MEDIUM if absent** —
      `out=$(grep -rniE 'mlflow|wandb|neptune|comet|sacred|tensorboard' . 2>&1); rc=$?` ;
      `case $rc in 0) printf '%s\n' "$out" | head ;; 1) echo "no experiment tracking" ;; *) echo "SWEEP FAILED, not a finding about their code: $out" ;; esac`
      ; manual (§1): does each run record commit, data version, feature set, hyperparameters,
      environment and metrics, with compared runs on the same eval data?
- [ ] **Seeds / determinism (§2) — MEDIUM (reproducibility); is metric variance across seeds reported, not one run?** —
      `out=$(grep -rniE 'seed|random_state|set_seed|manual_seed|deterministic' --include='*.py' . 2>&1); rc=$?` ;
      `case $rc in 0) printf '%s\n' "$out" | head ;; 1) echo "no seeds set — runs not reproducible" ;; *) echo "SWEEP FAILED, not a finding about their code: $out" ;; esac`
- [ ] **Config as code (§3) — MEDIUM** —
      `grep -rniE 'hydra|omegaconf|pydantic|argparse|yaml.safe_load|config' --include='*.py' . | head`
      ;
      `grep -rnE '= ?(0\.[0-9]+|[0-9]{2,})' --include='*.py' . | grep -iE 'lr|rate|epoch|batch|threshold' | head`
      (magic numbers)
- [ ] **Hyperparameter search hygiene (§4) — MEDIUM** —
      `grep -rniE 'GridSearch|RandomizedSearch|optuna|ray.tune|hyperopt' --include='*.py' . | head`
      (verify search uses validation set, not test, and every trial is logged to the tracker)
- [ ] **Notebook-only training (§2) — LOW/MEDIUM (debt)** — `find . -name '*.ipynb' | head` (is
      production training a notebook?)
- [ ] **Checkpointing for long/distributed runs (§5) — MEDIUM** —
      `grep -rniE 'checkpoint|save_model|state_dict|ModelCheckpoint' --include='*.py' . | head`
      ; manual: does a failed run resume from its last checkpoint, is the effective batch size / LR
      scaling verified, and are GPU-hours tracked?
- [ ] **Simplest model first (§6) — LOW (manual)** — did a simple model that beats the baseline run
      end-to-end through the full pipeline, with metrics and monitoring, before complexity was
      added, and is each added complexity justified by sliced eval against the baseline?
