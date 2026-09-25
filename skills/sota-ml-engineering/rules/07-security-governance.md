# 07 — ML security & governance

ML systems have an attack surface ordinary software doesn't (the data and the
model are attackable), plus regulatory obligations. Map threats with
[MITRE ATLAS](https://atlas.mitre.org/) (adversarial tactics/techniques against
AI systems) and govern with the
[NIST AI RMF](https://www.nist.gov/itl/ai-risk-management-framework). For
prompt-injection/agent threats specific to LLMs, see `sota-code-security`
rules/08 and `sota-llm-engineering`; this file covers classical-ML security.

## 1. Attacks on ML systems (MITRE ATLAS)

- **Training-data poisoning** — adversary corrupts training data (or labels) to
  degrade the model or implant a backdoor/trigger. Control data provenance and
  integrity; validate and monitor training data; restrict who/what can write to
  training sources (`rules/02`).
  A backdoor leaves accuracy on ordinary data untouched, so an aggregate eval
  passes it. Screen training sets before each run: outlier detection on features
  and learned representations, **spectral-signature** screening (the poisoned
  subset shows up in the top singular direction of a class's representation
  covariance, Tran et al. 2018), activation clustering, and influence-based
  tracing of suspicious predictions back to the training points that drove
  them. **Clean-label** (label-consistent) poisons carry correct labels, so
  label audits and human review miss them — only the representation-level
  screens apply. Gate promotion (`rules/04`) on a held-out **trigger corpus**
  built from your own policy taxonomy (the inputs whose flip would matter),
  kept out of every training source. Signing and provenance (§2) prove *who*
  produced a model, never that it is backdoor-free. OWASP: AISVS 1.3.1, 1.3.5;
  AI-Powered Advertising Systems Security cheat sheet.
- **Evasion / adversarial examples** — crafted inputs at inference cause
  misclassification. Validate/bound inputs; consider adversarial training and
  detection for high-stakes models.
- **Model extraction/stealing** — querying the API to clone the model.
  Rate-limit, monitor query patterns, avoid returning raw confidence vectors
  where not needed. Size the limits from the extraction threat model — how many
  queries clone the model to useful fidelity — per principal *and* globally
  (many low-rate accounts add up), not as a generic throttle. Feed per-principal
  query logs into a dedicated extraction detector (e.g. PRADA-style: the
  distribution of distances between a client's successive queries departs from
  benign traffic; also input-space coverage and boundary probing). An alert
  carries the principal, key, time window, query count and sample inputs, and
  the playbook escalates: throttle, block, revoke the credential, open an IR
  case (`sota-detection-engineering`). OWASP: AISVS 11.2.2, 11.3.1, 11.3.4,
  12.2.4.
- **Membership inference / model inversion** — inferring whether a record was in
  training, or reconstructing training data, from outputs/confidences. Minimize
  output granularity; consider differential privacy for sensitive training data.
- ATLAS is a living knowledge base (date-based `v2026.MM` releases since May
  2026; techniques now carry platform designations — Predictive AI, Generative
  AI, Agentic AI, Enterprise — check current); use it to enumerate threats
  during design, like ATT&CK for AI.

## 2. ML supply chain

- **Never load an untrusted model artifact.** `pickle`/`joblib`/`cloudpickle`
  execute arbitrary code on load — a malicious model file is RCE. `torch.load`
  defaults to `weights_only=True` (restricted unpickler) since PyTorch 2.6:
  `weights_only=False` or torch <2.6 is still arbitrary code execution, and even
  `weights_only=True` was bypassed to RCE on ≤2.5.1 (CVE-2025-32434, fixed in
  2.6.0) — treat it as hardening, not a trust boundary. Load models only from
  trusted, integrity-verified sources; prefer **`safetensors`**/ONNX (data, not
  code). `weights_only=False` on untrusted input is CRITICAL on sight (`rules/05`).
- Verify integrity/provenance of models and datasets (hashes, signing); pin and
  scan ML dependencies (the PyData/CUDA stack is large attack surface) — cross-ref
  `sota-devsecops`. Beware pre-trained weights/datasets from unvetted hubs — and
  don't treat a passing pickle scan as a trust boundary: blacklist-based scanners
  (picklescan-style, used by major model hubs) were repeatedly bypassed in 2025
  (multiple CVSS 9.3 CVEs: renamed extensions, corrupted ZIP flags, subclassed
  imports). Only trusted sources + integrity verification + safe formats count.
- **Sign every model artifact, verify twice.** Weights, configs, tokenizers,
  adapters, base models and safety/guard models each need a signature from a
  named, authorised signer. **OpenSSF Model Signing (OMS)** is a concrete
  format: one detached Sigstore-bundle signature over the whole model
  directory (reference CLI `model_signing` from `sigstore/model-transparency`;
  Sigstore verification requires the expected `--identity` and identity
  provider). Verify at deployment admission and again on load, and fail the
  deploy on any mismatch — the same contract as container-image admission
  (`sota-devsecops`). By default a file absent from the signed manifest fails
  verification; the ignore-unsigned-files option turns that off, letting an
  added file ride along unverified — treat it as a finding. OWASP: AISVS
  3.1.2, 3.1.3; AI-Powered Advertising Systems Security cheat sheet.
- **Handle third-party models in disposable workers.** Evaluation,
  fine-tuning and format conversion of an external or untrusted model run in an
  isolated worker (`sota-sandboxing` rules/01) with egress denied or
  allowlisted, no production credentials and no registry write access.
  `trust_remote_code=True` (Hugging Face `transformers`) executes Python shipped
  in the model repo: only inside such a worker, with `revision` pinned to a
  reviewed commit. At job
  teardown, check — not assume — that temp files, checkpoints, prompt/eval logs
  and cached embeddings are gone (list the scratch volume and caches; fail the
  job if anything remains). OWASP: Secure AI Model Ops cheat sheet.
- Protect the model registry and feature store with authn/z; a tampered registry
  ships a tampered model.

## 3. Privacy in ML

- Training data often contains personal data — minimize it, document a lawful
  basis, and honor deletion/retention (cross-ref `sota-privacy-compliance`). A
  model can **memorize** and leak training data; treat models trained on
  sensitive data as sensitive artifacts.
- Consider anonymization/aggregation, and differential privacy where the threat
  model warrants. Don't log raw PII features in monitoring (`rules/06`).

## 4. Governance & documentation

- **Model card** for each production model: intended use, training data summary,
  metrics **including per-slice** (`rules/04`), limitations, ethical
  considerations, owner. It's the artifact auditors and downstream consumers
  read.
- **NIST AI RMF** (Govern / Map / Measure / Manage) for the organizational
  process: identify context and risks, measure them (metrics, fairness,
  robustness), and manage with controls and monitoring. Treat as governance
  scaffolding, not a checkbox.
- **Fairness/bias**: assess disparate performance across protected groups
  (`rules/04`); document findings and mitigations. Bias is both an ethical and,
  increasingly, a legal requirement.

## 5. Regulatory (EU AI Act and beyond)

- The **EU AI Act** imposes obligations by risk tier; **high-risk** systems
  (e.g. employment, credit, biometric, essential services) carry requirements:
  risk management, data governance, technical documentation, logging,
  transparency, human oversight, and accuracy/robustness/cybersecurity. Determine
  your system's tier early — it shapes the whole lifecycle. Verify current
  obligations and timelines against the official text (they phase in over time).
- Sector rules may also apply (credit, health, insurance). Cross-ref
  `sota-privacy-compliance`.

## Audit checklist

- [ ] **Unsafe model deserialization — CRITICAL** —
      `grep -rnE '\b(pickle\.load|joblib\.load|cloudpickle|torch\.load)\b' --include='*.py' .` ;
      `grep -rnE 'weights_only\s*=\s*False' --include='*.py' .` (arbitrary code execution on
      load);
      `grep -rnE 'torch\s*[=<>~!]=+\s*[12]\.[0-5]\b' requirements*.txt pyproject.toml 2>/dev/null`
      (<2.6: CVE-2025-32434 weights_only bypass);
      `grep -rniE 'safetensors|onnx' --include='*.py' . || echo "consider safetensors/ONNX over pickle"`
- [ ] **Model/data provenance & integrity — HIGH** —
      `out=$(grep -rniE 'hash|sha256|sign|verify|provenance|checksum' . | grep -iE 'model|dataset|weight'); rc=$?` ;
      `case $rc in 0) printf '%s\n' "$out" | head ;; *) echo "no model/dataset integrity verification (rc=$rc; if the first grep failed, rerun it alone)" ;; esac`
- [ ] **Training-data write access / poisoning surface — HIGH (manual) Who can write to training
      data sources? Is training data validated (rules/02)?**
- [ ] **Extraction/inference exposure — MEDIUM** —
      `grep -rniE 'predict_proba|confidence|logits|rate.?limit|throttle' --include='*.py' . | head`
      (raw scores exposed? rate-limited?)
- [ ] **Governance docs — MEDIUM/LOW** —
      `out=$(grep -rniE 'model.?card|MODEL_CARD|datasheet|intended.use|limitation' . 2>&1); rc=$?` ;
      `case $rc in 0) printf '%s\n' "$out" | head ;; 1) echo "no model card" ;; *) echo "SWEEP FAILED, not a finding about their code: $out" ;; esac`
      ; `grep -rniE 'nist|ai.?rmf|risk.?assessment|fairness|bias' . | head`
- [ ] **EU AI Act / regulatory tier considered — HIGH for high-risk domains (manual)** —
      `grep -rniE 'ai.?act|high.?risk|gdpr|differential.privacy|anonymiz' . | head`
- [ ] **Model signing verified at admission and load (§2) — HIGH** —
      `grep -rnE 'model_signing[ .](verify|verifying)' . || echo "no model signature verification at admission/load"` ;
      unsigned files waved through:
      `grep -rnE 'ignore[-_]unsigned[-_]files' . | grep -vE 'no-ignore[-_]unsigned|unsigned_files\((False|0)\)'`
      (every hit is a finding). Manual: are tokenizers, adapters and guard models in the signed set?
- [ ] **Untrusted model code / worker isolation (§2) — HIGH** —
      `grep -rnE 'trust_remote_code *= *True' --include='*.py' .` (each hit must run in an
      egress-restricted worker with a pinned `revision`); manual: does job teardown verify
      checkpoints, logs and embedding caches are gone?
- [ ] **Poisoning screen and trigger-corpus gate (§1) — HIGH (manual)** —
      `grep -rniE 'spectral|activation.?cluster|influence|trigger.?(set|corpus)|backdoor' --include='*.py' . || echo "no poisoning screen or trigger-corpus gate"`
      ; a signature or provenance check alone does not satisfy this item
- [ ] **Extraction detection and response (§1) — MEDIUM** —
      `grep -rniE 'extraction|model.?steal|query.?(pattern|distance)' --include='*.py' . || echo "no extraction detector"`
      ; manual: limits sized per principal and globally, alerts carry principal/window/count,
      and a revoke/IR path exists
