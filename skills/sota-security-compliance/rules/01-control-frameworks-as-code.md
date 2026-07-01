# 01 — Control Frameworks as Code (NIST CSF 2.0 spine)

The reusable engine under every regime in this skill: pick an organizing spine,
crosswalk each outcome to a mechanism that already exists in your stack, and make
that mechanism emit its own evidence. Do this once and most of NIST CSF, 800-53,
800-171, SOC 2, ISO 27001, and the CRA fall out as views over the same controls.

## 1. Use NIST CSF 2.0 as the spine, not the control catalog

**Status (verified July 2026):** NIST Cybersecurity Framework **2.0** (CSWP 29)
was published **26 Feb 2024** and is current, superseding 1.1
(csrc.nist.gov/pubs/cswp/29). CSF is an **outcome map**, not a control list — it
says *what* good looks like and defers *how* to "Informative References"
(SP 800-53, etc.). That makes it the right top-level structure for a skill or a
control program; the concrete requirements come from rules/02–05.

**The six Functions** (2.0 added **Govern**, which wraps the other five):

| Function | Engineering meaning | Where the mechanism lives |
|---|---|---|
| **GOVERN** (GV) | Risk strategy, roles, policy, supply-chain oversight | Mostly organizational — note & route out (see SKILL boundary); the engineering hook is policy-as-code + the crosswalk itself |
| **IDENTIFY** (ID) | Asset & data inventory, risk assessment | `sota-privacy-compliance` rules/01 (data), `sota-cloud-infrastructure` (asset inventory), `sota-threat-modeling` |
| **PROTECT** (PR) | Access control, data security, platform hardening | `sota-identity-access`, `sota-secrets-management`, `sota-network-security`, `sota-sandboxing`, `sota-kubernetes` |
| **DETECT** (DE) | Continuous monitoring, anomaly detection | `sota-detection-engineering`, `sota-observability` |
| **RESPOND** (RS) | Incident handling, reporting | `sota-detection-engineering` (NIST 800-61), rules/04 clocks |
| **RECOVER** (RC) | Restoration, backups, continuity | `sota-cloud-infrastructure` (DR/backups), `sota-databases` |

The lesson: this skill's job is **binding and evidence**, not re-implementing
PROTECT/DETECT. If you find yourself writing an encryption or RBAC section here,
stop — reference the skill that owns it.

## 2. The crosswalk is the deliverable

**Rule:** For every control in scope, record three things as code in-repo — the
framework control ID, the *mechanism* that enforces it, and the *evidence source*
that proves it — with an owner. This single artifact serves every framework at
once and is the thing an assessor, a customer, or a future engineer actually uses.

```yaml
# GOOD: controls/sc-8.yaml — one control, many frameworks, a real mechanism
control: "Transmission confidentiality & integrity"
maps:
  nist_800_53: [SC-8, SC-8(1)]
  nist_800_171: ["3.13.8"]         # verify exact Rev 3 req ID against the 800-171r3 PDF
  csf_2_0: [PR.DS-02]
  cra: ["Annex I §1(2)(e)"]         # secure by default in transit
mechanism: >
  TLS 1.3 terminated at the mesh; mTLS between services (sota-network-security
  rules/04); FIPS-validated module in the moderate/CUI boundary (rules/02 §4).
evidence:
  - source: ci_policy
    query: "opa gate: deny plaintext listeners / TLS<1.2 — see policy/tls.rego"
  - source: mesh_config
    query: "istio PeerAuthentication STRICT, exported nightly"
owner: platform-team
inherited_from: ~   # or the CSP/PaaS control the customer inherits (FedRAMP CRM)
```

```text
BAD: a spreadsheet cell "SC-8 — Encryption in transit — Compliant" with no link
to a mechanism or a query. On sampling, two of five services listen plaintext
inside the cluster and nobody can produce proof either way.
```

**Build the crosswalk from the mechanism up, not the framework down.** Enumerate
what your systems already enforce (from the sota-* skills you apply), then attach
control IDs. You will find you already satisfy 70–90% of any framework — the work
is *mapping and recording*, the same insight `sota-privacy-compliance` rules/05
makes for SOC 2/ISO. Only the genuine gaps become new engineering.

## 3. Inheritance and shared responsibility

Most controls in a cloud system are **inherited** from the platform, not built by
you. Record the split explicitly or you will either re-build inherited controls or
claim controls you don't own:

- **Fully inherited** (e.g., physical security of a hyperscaler region) → reference
  the provider's attestation; you implement nothing.
- **Shared** (e.g., encryption at rest: provider offers KMS, *you* must enable it
  and manage keys) → your mechanism is "enabled + enforced by policy-as-code."
- **Customer** (e.g., your app's authz logic) → wholly yours.

FedRAMP calls this the Customer Responsibility Matrix (rules/02); the concept is
universal. A control marked "inherited" with no named provider control is a
finding.

## 4. Encode controls as gates, not prose

**Rule:** Every control that *can* be machine-enforced is a policy-as-code check at
CI and at the platform boundary (admission controllers, org policies/SCPs), not a
sentence in a PDF. Two products fall out of one policy: the **prevention** (the
control) and the **evaluation log** (the evidence).

```rego
# GOOD: a CUI/moderate data store cannot ship without validated crypto & boundary
# tags — one policy keeps the rules/02 boundary and FIPS requirement honest
deny[msg] {
  r := input.resource_changes[_]
  r.type in {"aws_s3_bucket", "aws_rds_cluster", "aws_dynamodb_table"}
  r.change.after.tags.data_category == "cui"
  not r.change.after.tags.boundary == "authorized"
  msg := sprintf("%s: CUI resource outside the authorization boundary", [r.address])
}
deny[msg] {
  r := input.resource_changes[_]
  r.change.after.tags.data_category == "cui"
  not r.change.after.kms_key_fips_validated   # your module verifies the KMS key's module
  msg := sprintf("%s: CUI at rest without FIPS-validated crypto (rules/02 §4)", [r.address])
}
```

Exceptions live in a register with `policy, resource, justification, compensating
control, owner, approved-by, expires` — CI re-fails the build the day an exception
expires. An exception that cannot expire is a policy change; argue it as one. (Same
discipline as `sota-privacy-compliance` rules/05 §4 and `sota-devsecops`.)

## 5. Baselines and tailoring

Frameworks ship **baselines** — predefined control sets keyed to system impact
(rules/02). Do not start from a blank catalog:

1. **Categorize the system** (impact: low/moderate/high, per data sensitivity —
   FIPS 199 in the US context).
2. **Inherit the matching baseline** as your starting control set.
3. **Tailor:** mark inherited controls, scope out non-applicable ones *with
   justification*, and add compensating controls where you deviate. Record the
   tailoring — an unjustified scope-out is the first thing an assessor pulls.

The tailoring record is the US-framework analog of ISO 27001's Statement of
Applicability (`sota-privacy-compliance` rules/05 §2): justify every inclusion and
exclusion, as code, reviewed like code.

## 6. Continuous, not point-in-time

A control that passed once and is never re-checked is a point-in-time artifact;
assessments increasingly want **operating effectiveness over time** (SOC 2 Type II,
FedRAMP ConMon, CMMC affirmation). The engineering consequence is the same one
that makes automation non-optional: you cannot retro-create a year of operating
evidence. So:

- Gates run on **every** change, and their logs are retained as the evidence
  population (`sota-devsecops`).
- Drift detection re-checks live infra against policy continuously.
- The crosswalk is reviewed at defined cadence; control owners get diffs, not
  a 300-row spreadsheet to rubber-stamp (the anti-pattern from
  `sota-privacy-compliance` rules/05 §2b).

Where a framework moves toward **machine-readable evidence** (FedRAMP 20x Key
Security Indicators, OSCAL control catalogs/SSPs), emit that format directly from
the enforcing system rather than transcribing into it — OSCAL SSP/SAP/SAR and
component definitions are the interchange target (rules/02).

## Audit checklist

- [ ] A control crosswalk exists **as code** in-repo: control ID → enforcing mechanism → evidence source → owner; covers the applicable framework(s), not one silo per framework
- [ ] CSF 2.0 (or the mandated framework) used as the organizing spine; controls reference the sota-* skill that owns the mechanism rather than re-implementing it
- [ ] Every control maps to a *running mechanism*, not a policy document; spot-check three controls by executing the gate / sampling the log
- [ ] Inherited vs shared vs customer responsibility recorded per control; no control claimed as inherited without a named provider control
- [ ] Machine-enforceable controls are policy-as-code gates at CI and the platform boundary; exception register with owner + expiry; CI re-fails on expiry
- [ ] System categorized (impact level) and the matching baseline inherited then tailored; tailoring (scope-outs, compensating controls) justified as code
- [ ] Evidence is generated by the enforcing system (CI log, IaC history, signed attestation, KSI/OSCAL feed) and producible in minutes — no screenshot evidence
- [ ] Controls re-evaluated continuously (gates on every change, drift detection), not point-in-time; evidence population generated by reproducible query
- [ ] Organizational controls (GOVERN, training, physical) explicitly marked as GRC/org-owned with the engineering hook noted — not silently skipped nor faked in code
- [ ] Framework versions/dates in the crosswalk re-verified against primary sources within the last 6 months
