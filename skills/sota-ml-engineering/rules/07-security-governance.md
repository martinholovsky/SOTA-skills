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
  Outcome and reward events that a later verdict can overturn (fraud, chargeback)
  wait out their adjudication window before training uses them (`rules/02` §7).
- **Evasion / adversarial examples** — crafted inputs at inference cause
  misclassification. Validate/bound inputs. Wherever an attacker can shape the
  input (fraud, abuse, content moderation, anything scoring user-submitted
  data), adversarial hardening is **required**, not optional: adversarial
  training or input purification, *and* a robustness slice in the evaluation
  suite (`rules/04` §3) so the hardening is measured rather than assumed.
  Libraries such as the Adversarial Robustness Toolbox (`art.attacks.evasion`)
  generate the attack inputs. OWASP: AISVS 11.1.4; Secure AI Model Ops cheat
  sheet.
- **Out-of-distribution gating at inference** — score each untrusted input for
  novelty before, or alongside, the prediction: an anomaly or OOD detector fitted
  on the training distribution, plus a confidence floor on the model's own
  output. Decide in advance what a flagged input gets: blocked, sent to human
  review, or served a reduced-capability answer (a default, no automated
  action); log the flag for drift monitoring (`rules/06` §4). This is judged on
  *what the input looks like*, which differs from source-based taint gating
  (`sota-code-security` rules/08), which is judged on *where the input came
  from*; an in-distribution input from a hostile source passes this gate and
  an odd input from a trusted source fails it, so neither replaces the other.
  OWASP: AISVS 11.4.1, 11.4.2; Secure AI Model Ops cheat sheet.
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
  output granularity; for sensitive training data see §3 (DP training and a
  membership-inference test).
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
  Where a pickle-format model genuinely cannot be avoided, scan it anyway before
  load (e.g. `picklescan`, `modelscan`, `fickling`) for dangerous imports and
  opcodes, as one *additional* layer on top of the trusted source and a
  restricted unpickler; a clean scan never waives either. OWASP: AISVS 6.1.1;
  LLMSVS 7.5.
- **A machine-readable ML-BOM per model artifact.** Every registered model
  version carries a versioned AI/ML bill of materials, e.g. CycloneDX (1.5
  added the `machine-learning-model` and `data` component types and the
  `modelCard` object). It lists base weights, adapters, datasets with their data
  origin and licences, the training-data lineage and the fine-tuning
  parameters. Tag each dataset entry with its provenance (the contributor or
  source), so a poisoned or withdrawn contribution maps to exactly the models to
  roll back rather than all of them. It complements the software SBOM
  (`sota-devsecops` rules/03), it does not replace it. **Sign the BOM** with the
  same attestation flow as other artifacts, bound to the model digest (e.g.
  `cosign attest --type cyclonedx`, `sota-devsecops` rules/02 §2.4), and
  verify it at deploy and at model load. An adapter with no signature, or whose
  signature does not match its BOM entry, is refused. OWASP: AISVS 6.2.1,
  6.2.2; LLMSVS 2.13; AI-Powered Advertising Systems Security cheat sheet;
  DSOMM.
- **Deployed prompts and guardrail configs drift-checked.** Where a model ships
  with a system prompt or a guardrail/safety config, a scheduled job hashes the
  deployed copy (normalised: line endings, trailing whitespace, key order) and
  compares it with the approved version in the repository; a mismatch is an
  incident, not a redeploy (versioning and review of these files:
  `sota-code-security` rules/23 §1). OWASP: AI-Powered Advertising Systems
  Security cheat sheet; DSOMM.
- **Models shipped on device** (mobile, edge, embedded): sign the model at
  packaging and have the on-device runtime verify the signature before it
  loads the model, on every load, not only after download (`sota-mobile`
  rules/04 §4.9 and its downloaded-content rule). Encrypt sensitive weights at
  rest under a data key wrapped by a hardware-backed, non-exportable key
  (Android Keystore, iOS Keychain/Secure Enclave, a device TEE) and decrypt only
  inside the trusted runtime. State the residual risk plainly in the threat
  model: someone who controls the device can still read the decrypted weights
  from memory, so encryption raises the cost of extraction, it does not
  prevent it. OWASP: AISVS 4.3.2, 4.3.4, 4.3.5.
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
- **A leaked credential on an ML data path is a data-integrity incident.**
  Rotating it (`sota-secrets-management` rules/04) closes the door but not the
  damage: mark every row the credential could write during the exposure window
  as suspect (this needs a writer identity and an ingest timestamp on each row),
  follow lineage (`rules/02` §5) to the datasets, features and models built from
  those rows, and quarantine or retrain them. OWASP: AI-Powered Advertising
  Systems Security cheat sheet.

## 3. Privacy in ML

- Training data often contains personal data — minimize it, document a lawful
  basis, and honor deletion/retention (cross-ref `sota-privacy-compliance`). A
  model can **memorize** and leak training data; treat models trained on
  sensitive data as sensitive artifacts.
- Consider anonymization/aggregation. Don't log raw PII features in
  monitoring (`rules/06`).
- **Sensitive training data gets DP training or a written reason why not.**
  Use differentially private optimisation (DP-SGD, e.g. Opacus `PrivacyEngine`
  or TensorFlow Privacy) and record the spent (ε, δ) budget in the model card;
  if DP is not used, the model card says why. Either way, the evaluation suite
  runs a **membership-inference simulation** (e.g. the Adversarial Robustness
  Toolbox `art.attacks.inference.membership_inference` attacks) and the model
  passes only when the attack does little better than a coin flip (attack
  accuracy or AUC close to 0.5, threshold set in advance). OWASP: AISVS 11.2.4,
  11.2.5.
- **Inferred special-category attributes.** On every model refresh, test whether
  ordinary inputs let the model (or a probe trained on its outputs or embeddings)
  predict special-category attributes such as health, ethnicity or religion —
  a proxy/disparate-impact audit alongside the fairness slices (`rules/04` §3).
  Never return an inferred sensitive attribute in an output or API response;
  inference creates special-category data (`sota-privacy-compliance` rules/01).
  OWASP: AISVS 11.2.1; AI-Powered Advertising Systems Security cheat sheet.

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
- [ ] **ML-BOM, signed, per model (§2) — HIGH** —
      `grep -rniE 'cyclonedx|ml[-_]?bom|ai[-_]?bom|machine-learning-model' . || echo "no ML-BOM for model artifacts"`
      ; adapter load sites, each needing a signature check bound to its BOM entry:
      `grep -rnE 'load_adapter\(|PeftModel\.from_pretrained\(' --include='*.py' .`
      ; manual: is the BOM itself signed and verified at deploy and load?
- [ ] **Pickle scanned before load where pickle is unavoidable (§2) — MEDIUM** — if the
      unsafe-deserialization probe above hits:
      `grep -rniE 'picklescan|modelscan|fickling' . || echo "pickle models loaded with no pre-load scan"`
      (a scan is an extra layer; a hit does not clear the CRITICAL item)
- [ ] **Deployed prompt/guardrail drift check (§2) — MEDIUM** —
      `grep -rniE '(system_?prompt|guardrail).*(sha256|hash|digest)' . || echo "no drift check on deployed prompts or guardrail configs"`
      ; manual: scheduled, normalised, and a mismatch opens an incident
- [ ] **On-device models signed and verified at load (§2) — HIGH** — list bundled models:
      `find . \( -name '*.tflite' -o -name '*.mlmodel' -o -name '*.mlpackage' -o -name '*.onnx' \) -not -path './.git/*'`
      ; manual for each: signature verified by the runtime before load, weights encrypted
      under a hardware-backed key, residual memory-extraction risk written down
- [ ] **Credential leak on a data path handled as data integrity (§2) — HIGH (manual)** — do
      rows carry writer identity and ingest time, and does the IR runbook trace suspect rows
      to the models trained on them?
- [ ] **Adversarial robustness required where inputs are attacker-influenced (§1) — HIGH** —
      `grep -rniE 'art\.attacks|adversarial|robustness|fgsm|projected.?gradient|textattack' --include='*.py' . || echo "no adversarial robustness evaluation"`
- [ ] **OOD/anomaly gate at inference (§1) — MEDIUM/HIGH** —
      `grep -rniE 'out.of.distribution|(^|[^a-z])ood([^a-z]|$)|novelty|anomaly.?(score|detect)|confidence.?(floor|threshold)' --include='*.py' . || echo "no OOD or anomaly gate at inference"`
      ; manual: is the action for a flagged input (block, review, degrade) defined?
- [ ] **DP training and membership-inference test on sensitive data (§3) — HIGH** —
      `grep -rniE 'opacus|PrivacyEngine|tensorflow_privacy|dp.?sgd|membership.?inference' --include='*.py' . || echo "no DP training or membership-inference test"`
      ; manual: ε recorded in the model card, or a written reason for no DP
- [ ] **Inferred special-category attribute returned (§3) — HIGH** —
      `grep -rniE '(predicted|inferred)_?(race|ethnicity|religion|health|sexual|pregnan|political|disabilit)' .`
      (every hit in an output schema or response is a finding); manual: proxy audit on refresh
