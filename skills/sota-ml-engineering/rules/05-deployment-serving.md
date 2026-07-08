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
  (`rules/01`).

## 2. Packaging & the serving environment

- Package the model with its inference dependencies for a **reproducible serving
  environment** (container; pinned libs). The serving-time framework/version
  must match what the model expects — a silent library mismatch changes outputs.
- Prefer portable, **safe** model formats: ONNX for cross-framework serving,
  `safetensors` over `pickle` (`rules/07`). Use a serving runtime (Triton,
  KServe, BentoML, Ray Serve, or a framework server) rather than ad-hoc Flask
  where scale/standardization matters. Do **not** adopt TorchServe — the repo
  was archived Aug 2025 (no updates or security patches); flag it in existing
  systems and migrate.
- The serving path must apply the **same feature transforms** as training
  (`rules/02`) — share code or a feature store, never reimplement.

## 3. Registry-gated promotion

- Deploy from the **model registry** (`rules/01`): a model is promoted
  staging→production only after the validation gate passes (`rules/04`). The
  deployed artifact is immutable and traceable to its lineage.
- Keep the **previous production model** available for instant rollback.

## 4. Progressive rollout & rollback

- Don't flip 100% of traffic to a new model. Use:
  - **Shadow** (dark launch): run the new model on real traffic without serving
    its predictions; compare outputs/latency to prod safely.
  - **Canary / A-B**: route a small % to the new model, watch guardrail and
    business metrics, ramp up.
- **Rollback must be fast and tested** — one action to revert to the prior
  model. A deployment with no rollback path is HIGH (ML Test Score requires it).

## 5. Operational concerns

- Latency/throughput: meet the budget (batching, hardware/accelerator choice,
  quantization/distillation if needed); load-test before launch (cross-ref
  `sota-performance`).
- Versioned, backward-compatible serving API; handle unseen categories/missing
  features gracefully (don't crash or silently mis-encode). Validate inputs at
  the serving boundary.
- Health checks, autoscaling, and resource limits like any service (cross-ref
  `sota-observability`, `sota-cloud-infrastructure`, `sota-kubernetes`).

## Audit checklist

```bash
# Serving/training parity — CRITICAL if features reimplemented in the server
grep -rniE 'predict|inference|serve' --include='*.py' . | head
#   Confirm the server calls the SAME feature transform code/store as training (rules/02)

# Safe model format & reproducible env — HIGH
grep -rniE 'pickle|joblib|torch.load|cloudpickle' --include='*.py' . | head    # unsafe load? (rules/07)
grep -rniE 'safetensors|onnx|torchscript' --include='*.py' . | head
grep -rniE 'torchserve|torch-model-archiver' . | head    # EOL runtime (archived Aug 2025, no security patches) — HIGH
ls Dockerfile* requirements*.txt poetry.lock uv.lock conda*.yml 2>/dev/null     # serving env pinned?

# Registry-gated deploy + rollback — HIGH
grep -rniE 'registry|stage|promote|production|rollback|previous.*model|champion|challenger' . | head \
  || echo "no registry/rollback path found"

# Progressive rollout — MEDIUM/HIGH
grep -rniE 'shadow|canary|a/?b|traffic.*split|gradual|ramp' . | head || echo "no progressive rollout"

# Serving input validation — MEDIUM
grep -rniE 'validate|schema|pydantic|unseen|unknown.*categor|fillna|missing' --include='*.py' . | head
```
