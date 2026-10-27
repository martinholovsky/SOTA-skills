# 05 — Deployment & serving

Shipping a model is a deployment, with the same discipline as any production
release — plus ML-specific concerns: serving/training parity, reversibility, and
progressive rollout validated on live traffic.

## 1. Serving pattern: batch vs online vs streaming

- **Batch** — precompute predictions on a schedule, store them, serve from a
  store. Simplest and cheapest when freshness tolerates it.
- **Online/real-time** — model behind a low-latency API; needs the online
  feature path and latency budgets.
- **Streaming** — predictions on an event stream.
- Choose by freshness/latency requirement; don't build a real-time service when
  nightly batch suffices. The choice dictates the feature architecture
  ([`rules/01`](01-ml-systems-architecture.md)).

## 2. Packaging & the serving environment

- Package the model with its inference dependencies for a **reproducible serving
  environment** (container; pinned libs). The serving-time framework/version
  must match what the model expects — a silent library mismatch changes outputs.
- Prefer portable, **safe** model formats: ONNX for cross-framework serving,
  `safetensors` over `pickle` ([`rules/07`](07-security-governance.md)). Use a serving runtime (Triton,
  KServe, BentoML, Ray Serve, or a framework server) rather than ad-hoc Flask
  where scale/standardization matters. Do **not** adopt TorchServe — the repo
  was archived Aug 2025 (no updates or security patches); flag it in existing
  systems and migrate.
- The serving path must apply the **same feature transforms** as training
  ([`rules/02`](02-data-and-features.md)) — share code or a feature store, never reimplement.

## 3. Registry-gated promotion

- Deploy from the **model registry** ([`rules/01`](01-ml-systems-architecture.md)): a model is promoted
  staging→production only after the validation gate passes ([`rules/04`](04-evaluation-validation.md)). The
  deployed artifact is immutable and traceable to its lineage.
- Admission and the serving process's load path both verify the model
  signature against the authorised signer, and fail closed ([`rules/07`](07-security-governance.md) §2).
- Keep the **previous production model** available for instant rollback.

## 4. Progressive rollout & rollback

- Don't flip 100% of traffic to a new model. Use:
  - **Shadow** (dark launch): run the new model on real traffic without serving
    its predictions; compare outputs/latency to prod safely.
  - **Canary / A-B**: route a small % to the new model, watch guardrail and
    business metrics, ramp up.
- **Rollback must be fast and tested** — one action to revert to the prior
  model. A deployment with no rollback path is HIGH (ML Test Score requires it).
- **Roll back the whole serving state, not the weights.** A release bundle pins
  the weights together with the tokenizer, preprocessing and serving config,
  feature definitions, prompts and the retrieval index version, and rollback
  restores the bundle; old weights behind a new tokenizer or index is a third,
  untested model. OWASP: AISVS 3.3.2.
- **Versions running side by side share no model runtime state.** During shadow,
  canary or A/B, each version gets its own KV/prefix caches, adapter pool and
  any cached embeddings or results, keyed by model version, so one version
  never serves from state the other produced (tenant-scoped caches:
  [`sota-code-security` rules/08](../../sota-code-security/rules/08-llm-ai-security.md) §4). OWASP: AISVS 3.3.3.

## 5. Operational concerns

- Latency/throughput: meet the budget (batching, hardware/accelerator choice,
  quantization/distillation if needed); load-test before launch (cross-ref
  [`sota-performance`](../../sota-performance/SKILL.md)).
- Versioned, backward-compatible serving API; handle unseen categories/missing
  features gracefully (don't crash or silently mis-encode). Validate inputs at
  the serving boundary.
- Health checks, autoscaling, and resource limits like any service (cross-ref
  [`sota-observability`](../../sota-observability/SKILL.md), [`sota-cloud-infrastructure`](../../sota-cloud-infrastructure/SKILL.md), [`sota-kubernetes`](../../sota-kubernetes/SKILL.md)).

## 6. Decommissioning a model

- Retiring a model is a planned step, not neglect: revoke its serving endpoints
  and credentials first, then delete the weights, checkpoints, caches and
  derived embeddings, and the training data held only for it (subject to the
  retention schedule, [`sota-privacy-compliance`](../../sota-privacy-compliance/SKILL.md)). Record what was erased,
  where, when and by whom; the registry entry stays as a tombstone with that
  record (e.g. MLflow `MlflowClient.delete_model_version` removes the version, so
  write the record first). Storage-level erasure of the underlying buckets and
  volumes: [`sota-cloud-infrastructure` rules/05](../../sota-cloud-infrastructure/rules/05-data-storage.md). OWASP: LLMSVS 2.18.

## Audit checklist

- [ ] **Serving pattern matches the freshness need (§1) — LOW (manual)** — is a real-time service
      built where scheduled batch would meet the freshness requirement, and does the feature
      path match the chosen pattern (batch, online, streaming)?
- [ ] **Serving/training parity (§2) — CRITICAL if features reimplemented in the server** —
      `grep -rniE 'predict|inference|serve' --include='*.py' . | head` — a locator: it lists
      every serving site; each hit is read, not a finding (confirm the server calls the SAME feature transform code/store as training, [rules/02](02-data-and-features.md))
- [ ] **Safe model format & reproducible env (§2) — HIGH** —
      `grep -rniE 'pickle|joblib|torch.load|cloudpickle' --include='*.py' . | head` (unsafe
      load? ([rules/07](07-security-governance.md))); `grep -rqiE 'safetensors|onnx|torchscript' --include='*.py' . || echo "no safe model format"` ;
      `grep -rniE 'torchserve|torch-model-archiver' . | head` (EOL runtime (archived Aug 2025,
      no security patches) — HIGH);
      `find . -maxdepth 3 -not -path '*/node_modules/*' \( -name 'Dockerfile*' -o -name 'requirements*.txt' -o -name poetry.lock -o -name uv.lock -o -name 'conda*.yml' \)` (serving env
      pinned?)
- [ ] **Registry-gated deploy + rollback (§3) — HIGH** —
      `out=$(grep -rniE 'registry|stage|promote|production|rollback|previous.*model|champion|challenger' . 2>&1); rc=$?` ;
      `case $rc in 0) printf '%s\n' "$out" | head ;; 1) echo "no registry/rollback path found" ;; *) echo "SWEEP FAILED, not a finding about their code: $out" ;; esac`
      ; manual: is the deployed artifact immutable and traceable to its lineage, and the previous
      production model kept deployable? Signature at admission and load: the model-signing item
      in [rules/07](07-security-governance.md)
- [ ] **Progressive rollout — MEDIUM/HIGH** (§4) —
      `out=$(grep -rniE 'shadow|canary|a/?b|traffic.*split|gradual|ramp' . 2>&1); rc=$?` ;
      `case $rc in 0) printf '%s\n' "$out" | head ;; 1) echo "no progressive rollout" ;; *) echo "SWEEP FAILED, not a finding about their code: $out" ;; esac`
- [ ] **Serving input validation and operability (§5) — MEDIUM** —
      `grep -rqiE 'validate|schema|pydantic|unseen|unknown.*categor|fillna|missing' --include='*.py' . || echo "no serving input validation"`
      ; manual: load-tested against the latency budget before launch, and a versioned,
      backward-compatible serving API
- [ ] **Full-state rollback and isolated caches (§4) — MEDIUM/HIGH** — cache keys with no
      model version: `grep -rniE 'cache_?key\s*=' --include='*.py' . | grep -viE 'model_?(version|id)'`
      ; manual: does the rollback bundle pin tokenizer, config, features, prompts and index?
- [ ] **Model decommissioning (§6) — MEDIUM** —
      `grep -rqiE 'decommission|retire|delete_model_version|delete_registered_model' . || echo "no model retirement path"`
      ; manual: endpoints revoked before artifacts erased, and the erasure recorded
