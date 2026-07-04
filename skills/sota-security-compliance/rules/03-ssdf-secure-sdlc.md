<!-- last-verified: 2026-07 -->
# 03 — Secure SDLC: NIST SSDF (SP 800-218)

The framework that turns "we develop securely" from a claim into an assessable set
of practices. The SSDF is deliberately high-level and tool-agnostic; its value here
is as a **checklist to crosswalk your existing pipeline against** (rules/01), and
as the thing US federal buyers make you **attest to**. Almost none of it is new
engineering if you already apply `sota-devsecops`, `sota-testing`, and
`sota-secrets-management` — the work is mapping and closing gaps.

> **Status (verified July 2026):** the operative version is **SSDF v1.1, SP
> 800-218, published 3 Feb 2022** (csrc.nist.gov/pubs/sp/800/218/final). A **Rev 1
> (SSDF v1.2)** initial public draft appeared **Dec 2025** — *draft, not a
> baseline; do not cite as current.* **SP 800-218A** (AI/model development
> profile) is **final, 26 Jul 2024**. Re-verify before relying on any of these.

## 1. The four practice groups

SSDF organizes practices into four groups. Map each to the sota-* skill and CI
stage that already implements it:

| Group | Intent | Where it lives in your stack |
|---|---|---|
| **PO — Prepare the Organization** | Define security requirements, roles, toolchains, and criteria *before* coding | Governance + `sota-devsecops` (pipeline setup), `sota-docs-workflow` (requirements) |
| **PS — Protect the Software** | Protect code and releases from tampering | Source integrity, branch protection, artifact **signing & provenance (SLSA/Sigstore)**, protected registries → `sota-devsecops`, `sota-secrets-management` |
| **PW — Produce Well-Secured Software** | The design/code core: build security in | **Threat modeling** (`sota-threat-modeling`), secure defaults & secure coding (`sota-code-security` + language skills), **SAST/DAST/secret-scanning**, code review, vetting reused components → `sota-devsecops`, `sota-testing` |
| **RV — Respond to Vulnerabilities** | Find, triage, remediate, and root-cause post-release | VDP/CVD intake, scanning, SLA-tracked remediation → rules/04 (CRA overlaps), `sota-devsecops` |

**PW drives architecture and code most directly**; PS drives the pipeline; RV
drives operations. PO is largely governance with a few engineering hooks (the
toolchain and the security-requirements definition).

## 2. Make each practice a gate, not an intention

The failure mode assessors hunt is a **signed attestation whose practices aren't
enforced**. Encode the machine-checkable practices as CI gates so the attestation
is backed by a mechanism (rules/01 §4):

- **PW.7 / PW.8 (review & testing)** → SAST, DAST, and secret-scanning gates that
  fail the build; test-coverage and security-test suites (`sota-testing`,
  including its security-testing/WSTG rules).
- **PW.4 (reuse secure components)** → dependency scanning + an allowlist/denylist;
  SBOM generation (rules/04); no unvetted transitive pull-through.
- **PS.1 / PS.2 (protect & provide provenance)** → signed commits, SHA-pinned
  actions, **build provenance (SLSA)** and artifact signing (`sota-devsecops`).
- **PS.3 (archive & protect each release)** → immutable, signed release artifacts
  with retained provenance.
- **PW.1 (threat modeling / secure design)** → a design-review gate that references
  the threat model (`sota-threat-modeling` rules/06) for features crossing trust
  boundaries.
- **RV.1 (identify vulns continuously)** → scheduled dependency/container/runtime
  scanning with SLA-tracked tickets; **RV.2** remediation; **RV.3** root-cause.

The crosswalk row for each practice cites the gate and its evidence — the CI log
*is* the operating evidence (rules/01 §6).

## 3. Federal secure-software self-attestation

**Status (needs verification — enforcement scope has shifted across
administrations):** under OMB M-22-18 / M-23-16, software producers selling to the
US government are required to **self-attest** to SSDF-aligned practices via the
**CISA Secure Software Development Attestation Form**, with artifacts submitted
through CISA's repository (cisa.gov/secure-software-attestation-form). *Confirm the
current mandate, covered-software scope, and deadlines before asserting them* —
this is the most politically volatile item in this skill.

**Engineering consequence regardless of the mandate's status:** an attestation is
a **signed claim by a named officer**. Before anyone signs, the PW/PS/RV practices
must be *demonstrably enforced* — because the attestation is only as true as the
gates behind it, and a false attestation carries legal exposure (False Claims Act
risk in the US). Treat "can we sign this honestly?" as "are these practices gates
in CI?" Produce the artifacts (SBOM, provenance, scan results) the form references
straight from the pipeline.

## 4. SP 800-218A — AI / model development

If you develop or fine-tune AI models, **SP 800-218A** (final, Jul 2024) augments
the SSDF with model-specific tasks. The additions that drive engineering:

- **Training-data provenance & integrity** — data lineage, poisoning defenses,
  and the same inventory discipline as `sota-privacy-compliance` rules/01 extended
  to datasets (see `sota-ml-engineering` for leakage/lineage mechanics).
- **Model weights as high-value assets** — protect and sign them like release
  artifacts (PS practices applied to weights); access-control and provenance for
  checkpoints.
- **Dual-use foundation-model considerations** and eval/misuse testing before
  release (`sota-llm-engineering` evals, `sota-code-security` rules/08 for
  prompt-injection/agent surface).

This is the crosswalk target when an SSDF attestation or a customer questionnaire
asks about AI development specifically.

## 5. Don't rebuild — reference

The SSDF is intentionally a *reference framework*; the concrete SOTA practice for
every task it names already lives in this library. This rule's job is to give you
the **mapping** and the **attestation discipline**, not a second copy of the
pipeline guidance. When a PW/PS/RV practice needs implementing, jump to:

- `sota-devsecops` — the pipeline, SLSA/Sigstore provenance, SBOM, dependency & IaC
  scanning, admission control
- `sota-testing` — SAST/DAST placement, security testing (WSTG), fuzzing, mutation
- `sota-code-security` + the language skills — secure coding, the vuln classes
- `sota-secrets-management` — signing keys, protected credentials
- `sota-threat-modeling` — the PW.1 design analysis

## Audit checklist

- [ ] SSDF practices (PO/PS/PW/RV) crosswalked to concrete pipeline stages and sota-* mechanisms (rules/01); gaps tracked, not hand-waved
- [ ] PW machine-checkable practices are CI gates that fail the build: SAST, DAST, secret-scanning, dependency scanning, test suites
- [ ] PS: signed commits, SHA-pinned actions, build provenance (SLSA) and artifact signing; releases immutable, signed, provenance retained
- [ ] PW.1 secure-design/threat-modeling gate for features crossing trust boundaries, referencing the threat model
- [ ] RV: continuous vuln identification (deps/containers/runtime) with SLA-tracked remediation and root-cause analysis
- [ ] If federal self-attestation applies: the attested practices are demonstrably enforced *before* signing; SBOM/provenance/scan artifacts produced from the pipeline; current mandate/scope/deadline verified (not assumed)
- [ ] If developing/fine-tuning AI: SP 800-218A additions applied — training-data provenance/integrity, model weights protected & signed as high-value assets, eval/misuse testing before release
- [ ] Attestation, if any, backed by mechanisms not prose — no signed claim without an enforcing gate (False Claims exposure)
- [ ] SSDF version referenced is the current final (v1.1 / SP 800-218) unless a newer revision has been finalized; drafts not cited as baseline
- [ ] No pipeline guidance duplicated here — implementation deferred to `sota-devsecops` / `sota-testing` / `sota-code-security`
