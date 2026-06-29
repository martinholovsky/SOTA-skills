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
  code (`rules/01`).

## 3. Configuration management

- Treat experiment config as code: versioned, reviewed, validated (typed config
  — Hydra/pydantic-style). Avoid magic numbers scattered across scripts
  (configuration debt, `rules/01`).
- Separate config from code so a run is fully described by (code commit +
  config + data version).

## 4. Hyperparameter search

- Use a principled search (grid for small spaces, random/Bayesian/Optuna-style
  for larger) with a fixed validation protocol; never tune on the test set
  (`rules/02`). Budget it — log all trials to the tracker.
- Guard against overfitting the validation set through many trials: keep a final
  held-out test untouched until the end; consider nested CV for small data.

## 5. Distributed & large-scale training

- For multi-GPU/multi-node: checkpoint regularly (resume from failure), make
  data loading deterministic where it matters, and verify the effective batch
  size / LR scaling. Checkpoints are part of the reproducible artifact set.
- Cost-awareness: training is expensive — track GPU-hours; use spot/preemptible
  with checkpointing; don't retrain from scratch when a warm start or incremental
  update suffices (cross-ref `sota-performance`, `sota-cloud-infrastructure`).

## 6. Start simple, iterate inside the pipeline

- First model: simplest thing that beats the baseline, wired through the full
  pipeline with metrics and monitoring (`rules/01`, `rules/04`). Add complexity
  only when the eval (on slices, vs baseline) justifies it. Most gains come from
  better features and data, not fancier models (Rules of ML).

## Audit checklist

```bash
# Experiment tracking present? — MEDIUM if absent
grep -rniE 'mlflow|wandb|neptune|comet|sacred|tensorboard' . | head || echo "no experiment tracking"

# Seeds / determinism — MEDIUM (reproducibility)
grep -rniE 'seed|random_state|set_seed|manual_seed|deterministic' --include='*.py' . | head \
  || echo "no seeds set — runs not reproducible"

# Config as code — MEDIUM
grep -rniE 'hydra|omegaconf|pydantic|argparse|yaml.safe_load|config' --include='*.py' . | head
grep -rnE '= ?(0\.[0-9]+|[0-9]{2,})' --include='*.py' . | grep -iE 'lr|rate|epoch|batch|threshold' | head  # magic numbers

# Hyperparameter search hygiene — MEDIUM
grep -rniE 'GridSearch|RandomizedSearch|optuna|ray.tune|hyperopt' --include='*.py' . | head
#   verify search uses validation set, not test

# Notebook-only training — LOW/MEDIUM (debt)
find . -name '*.ipynb' | head    # is production training a notebook?

# Checkpointing for long/distributed runs — MEDIUM
grep -rniE 'checkpoint|save_model|state_dict|ModelCheckpoint' --include='*.py' . | head
```
