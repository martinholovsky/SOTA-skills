<!-- last-verified: 2026-07 -->
# 02 — NIST 800-53 / 800-171 / CMMC / FedRAMP

The US federal control stack. These four are one lineage: **SP 800-53** is the
master control catalog; **SP 800-171** is its tailored subset for protecting
Controlled Unclassified Information (CUI) on non-federal systems; **CMMC** is the
DoD program that *assesses* 800-171 implementation; **FedRAMP** applies 800-53
baselines to cloud services sold to the government. Learn the catalog once; the
rest are scopes and assessment wrappers over it.

> Statuses verified July 2026 against csrc.nist.gov, fedramp.gov, and the Federal
> Register. Re-verify dates before relying on them; route scoping/level decisions
> to your assessor or sponsor (engineering guidance, not assessment advice).

## 1. SP 800-53 — the control catalog

**Status:** **Rev 5**, finalized 10 Dec 2020 (Rev 5.1.1); the control **baselines**
in **SP 800-53B** reached **Release 5.2.0 on 27 Aug 2025** — the catalog is current
and actively maintained, no Rev 6 (csrc.nist.gov/pubs/sp/800/53/r5/upd1/final).

**20 control families**; Rev 5 added **PT** (PII processing) and **SR** (supply-
chain risk). The families engineers implement directly:

| Family | What it drives in code/infra |
|---|---|
| **AC** Access Control | RBAC/ABAC, least privilege, session control → `sota-identity-access` |
| **AU** Audit & Accountability | auditable events, log content, retention, tamper-evidence → `sota-observability`, `sota-detection-engineering` |
| **SC** System & Comms Protection | TLS, boundary/segmentation, FIPS crypto, key mgmt → `sota-network-security`, `sota-secrets-management` |
| **SI** System & Info Integrity | flaw remediation, malware, input validation, monitoring → `sota-code-security` |
| **CM** Configuration Management | baselines, least functionality, change control → `sota-devsecops`, `sota-kubernetes` |
| **IA** Identification & Authentication | MFA, authenticator mgmt (800-63) → `sota-identity-access` |
| **SA** System & Services Acquisition | secure SDLC, developer testing (SA-11/SA-15/SA-22) → rules/03 SSDF |

**Baselines (800-53B):** **low / moderate / high**, keyed to the system's impact
level (FIPS 199 categorization across confidentiality/integrity/availability),
plus a **privacy baseline** applied regardless of impact. Start from the baseline
and tailor (rules/01 §5) — never a blank catalog.

**Interchange format:** NIST publishes the catalog and baselines in **OSCAL**
(machine-readable JSON/XML/YAML). Consume OSCAL for the control catalog and emit
OSCAL SSP/SAP/SAR from your crosswalk (rules/01 §2) rather than hand-maintaining
Word documents.

## 2. SP 800-171 — protecting CUI on your systems

**Status:** **Rev 3 is FINAL — published 14 May 2024**
(csrc.nist.gov/pubs/sp/800/171/r3/final), superseding Rev 2. Re-derived from
800-53 Rev 5 moderate baseline; introduces **organization-defined parameters
(ODPs)** and reorganizes into **17 families** (Rev 2 had 14 — Rev 3 adds Planning,
System & Services Acquisition, and Supply Chain Risk Management).

> **Version caveat that bites right now:** CMMC Level 2 is currently pinned to
> **800-171 Rev 2** (110 controls) via the DoD rule text, even though Rev 3 is the
> current NIST publication. Which revision your contract requires is a
> **contract-level fact** — verify against the DFARS clause / SSP template before
> building to Rev 3 numbering. Rev 3 also **renumbered** some requirements, so
> confirm exact IDs against the 800-171r3 PDF, not memory.

**What CUI is:** government-created or -owned information that is not classified but
requires safeguarding (contract data, technical drawings, etc.). If you process,
store, or transmit CUI on a non-federal system, 800-171 applies.

**The requirements that drive architecture** (Rev 2 numbering shown; map forward
carefully):
- **Define and isolate the CUI boundary** — boundary protection (3.13.1) and
  subnetworks for publicly accessible components (3.13.5). This is the single
  biggest design decision: a **CUI enclave** (segmented network/accounts/identity)
  keeps scope small; a flat network puts the whole company in scope.
- **FIPS-validated cryptography** to protect CUI confidentiality (3.13.11) — a
  *validated module* (FIPS 140-3, CMVP certificate), not merely "AES somewhere."
  See §4.
- **Audit logging & retention** (3.3.x) — auditable events, protected logs,
  reviewed.
- **Separation of duties + least privilege** (3.1.x) and **MFA** (3.5.3) for
  network/privileged access.
- **SPRS score:** DoD contractors self-assess against 800-171 and post a score to
  the Supplier Performance Risk System; the SSP + POA&M are the assessable
  artifacts. Generate them from the crosswalk (rules/01), don't hand-write.

## 3. CMMC — assessing 800-171 for DoD

**Status:** the **CMMC program rule (32 CFR Part 170)** was published 15 Oct 2024
and became **effective 16 Dec 2024**. The **acquisition rule (48 CFR / DFARS, Case
2019-D041)** that lets DoD put CMMC clauses into contracts was published 10 Sep
2025, **effective 10 Nov 2025** (Federal Register 2024-22905 and 2025-17359). CMMC
is live; contract requirements are phasing in.

**Three levels:**
- **Level 1 (Foundational)** — Federal Contract Information (FCI); 15 requirements
  from FAR 52.204-21; **annual self-assessment**.
- **Level 2 (Advanced)** — CUI; **maps to NIST SP 800-171 (110 controls)**;
  self-assessment *or* third-party assessment by a **C3PAO** depending on the
  contract.
- **Level 3 (Expert)** — adds a subset of **SP 800-172** (enhanced controls for
  advanced persistent threats); government-led assessment.

**Phase-in** (per 32 CFR 170, clock from the 48 CFR effective date 10 Nov 2025):
Phase 1 (self-assessments) now → **Phase 2 (~Nov 2026)** L2 C3PAO certification in
solicitations → Phase 3 (~2027) L3 → Phase 4 (~2028) full inclusion. *Dates are
DoD-planned and can slip — verify against the actual DFARS clause at contract
time.* Engineering consequence: implement the 800-171 controls in §2, maintain an
SSP + POA&M as living, assessable evidence, and re-affirm annually.

## 4. FIPS-validated cryptography — the recurring hard requirement

CUI, FedRAMP, and many OT/federal contexts require **FIPS 140-3 validated
cryptographic modules** — not just "strong encryption." Engineering consequences:

- Use a crypto module holding a current **CMVP certificate** (check the module and
  version on the NIST CMVP list; "FIPS-capable" ≠ "validated" ≠ "operating in FIPS
  mode"). Verify the *module* your runtime actually loads.
- In cloud: use the provider's **FIPS-validated endpoints/KMS** and record the
  module in the crosswalk (`sota-secrets-management`). A non-validated library
  (or a validated one running outside FIPS mode) protecting CUI is a **critical**
  finding.
- Don't roll your own or use a non-validated cipher for in-scope data. This is the
  one place "the crypto works fine" is not the standard — validation is the
  requirement.

## 5. FedRAMP — 800-53 for government cloud

**Status:** the traditional program uses **800-53 Rev 5 baselines** at **Low /
Moderate / High** impact (FIPS 199), via **Agency ATO** or PMO paths. **FedRAMP
20x is a real, active initiative** (fedramp.gov/20x) reframing authorization toward
continuous, **machine-readable evidence** (Key Security Indicators) over
document-heavy SSPs — first 20x pilot authorizations issued **6 Mar 2026**, with
wider submission planned for **FY26 Q4**; consolidated program rules took effect
**4 Jul 2026**, and new Rev 5 certifications stop being accepted **11 Jun 2027**.
*Future-phase dates are FedRAMP estimates — re-verify at fedramp.gov/changelog.*

**Engineering implications (both paths):**
- **Authorization boundary:** a hard, documented edge around the service; every
  component and data flow that touches federal data is inside it and inventoried.
  Scope discipline is the whole game (as with the CUI enclave, §2).
- **Complete asset inventory**, reconciled continuously — a stale inventory is the
  most common ConMon finding.
- **Continuous monitoring (ConMon):** scanning, POA&M management, and change
  control run monthly, not at audit time.
- **20x-shaped work:** emit control evidence as **machine-readable KSIs** straight
  from the enforcing system (rules/01 §6) rather than transcribing into an SSP.
- **Customer Responsibility Matrix:** document which controls the consuming agency
  inherits from you vs. must implement themselves (rules/01 §3).

## Audit checklist

- [ ] System categorized (impact level / FIPS 199) and the correct 800-53 baseline (low/moderate/high) inherited then tailored, with justification as code
- [ ] If CUI is present: a defined, segmented CUI enclave/boundary — verified in network/IAM config, not asserted; publicly accessible components subnetworked
- [ ] FIPS-validated (140-3, CMVP-certificated) crypto module protects CUI/federal data at rest and in transit; the *loaded* module verified, and it runs in FIPS mode
- [ ] 800-171 revision in use matches the **contract** requirement (CMMC L2 may pin Rev 2); exact requirement IDs confirmed against the primary PDF, not memory
- [ ] CMMC level matches the contract; SSP + POA&M generated from the control crosswalk and kept current; SPRS score posted where required; annual affirmation wired
- [ ] AU/audit-logging controls implemented with retention + tamper-evidence; logs reviewed (mechanism, not manual promise)
- [ ] AC/IA controls: least privilege, separation of duties, MFA for privileged/network access — enforced by the IdP, not policy prose (`sota-identity-access`)
- [ ] FedRAMP (if applicable): authorization boundary drawn and enforced; asset inventory reconciled continuously; ConMon (scans/POA&M/change control) operating monthly; CRM published
- [ ] Where FedRAMP 20x applies, control evidence emitted as machine-readable KSIs from the enforcing system; OSCAL used for SSP/SAP/SAR interchange
- [ ] All statuses/dates in this file re-verified against primary sources (CSRC, fedramp.gov, Federal Register) within the last 6 months
