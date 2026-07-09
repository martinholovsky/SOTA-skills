# 04 — Regulatory Landscape: Engineering Obligations

What each major regime actually demands from the codebase and infrastructure.
Statuses verified against primary/secondary sources as of **June 2026** — laws
move; re-verify any date you are about to rely on, and route interpretation to
counsel (this is engineering guidance, not legal advice).

## 0. Applicability triage (run this first)

Determine regimes from three axes — the answers shape architecture before any
control work starts:

| Axis | Question | Triggers |
|---|---|---|
| Data subjects | Where are the people whose data you process? | EU/UK → GDPR/UK GDPR; US states → state patchwork; minors → COPPA/state minor laws (stricter everywhere) |
| Data types | What categories? | Payment cards → PCI DSS; US health data as covered entity/BA → HIPAA; health-adjacent outside HIPAA → state health-data laws (e.g., Washington My Health My Data); special-category → GDPR Art. 9 |
| Sector/role | What are you? | EU financial entity → DORA; EU essential/important entity → NIS2; AI system provider/deployer in EU → AI Act; processor for enterprises → SOC 2/ISO 27001 expectations (rules/05) |

## 1. GDPR / UK GDPR — the mechanics that hit engineering

**Lawful basis (Art. 6).** Every processing purpose in the catalog (rules/01)
carries exactly one lawful basis. Engineering consequences:
- **Consent** → build the consent machinery of rules/03 §1; withdrawal stops
  processing, so every consumer must check state.
- **Contract** → scope limited to what the service actually requires; doesn't
  cover marketing or analytics bolted onto a contract basis.
- **Legitimate interest** → requires a documented balancing test (LIA) AND an
  objection (opt-out) path users can actually exercise — that's a feature to build.
Basis choice is a counsel/DPO call; representing it in the catalog and enforcing
its consequences in code is yours.

**International transfers (Ch. V).** Personal data leaving the EU/EEA requires a
transfer mechanism: adequacy decision (e.g., EU–US Data Privacy Framework for
certified US companies — verify the receiving entity's certification and the
framework's current validity before relying on it: a CJEU appeal against the
adequacy decision is pending (C-703/25 P), and the June 2026 US Supreme Court
ruling ending FTC commissioners' removal protections has raised fresh
independent-oversight questions), Standard Contractual Clauses
(SCCs) + transfer impact assessment, or BCRs. Engineering consequences:
- Know region per processor (rules/01 §4) — including support access and admin
  consoles, not just storage ("data at rest in EU, support in US" is a transfer).
- Be ready to region-pin (§7) if a mechanism collapses (it has happened twice —
  Safe Harbor, Privacy Shield).

**DPIA triggers (Art. 35).** A Data Protection Impact Assessment is required for
likely-high-risk processing: systematic large-scale monitoring, large-scale
special-category processing, automated decisions with legal/significant effects,
new tracking tech, matching/combining datasets. Engineering hook: make "needs
DPIA?" a checkbox on design docs for features touching PII; the DPIA references
the data map and threat model (LINDDUN via sota-threat-modeling) — don't write it
from scratch.

**Breach notification (Art. 33/34).** Current law: notify the supervisory
authority **within 72 hours** of becoming aware, unless the breach is unlikely to
result in risk; notify affected individuals without undue delay when high risk.
*Pending change (NOT yet law as of June 2026):* the EU **Digital Omnibus**
proposal (published 19 Nov 2025, still in Parliament/Council) would extend the
deadline to 96 hours and raise the threshold to high-risk breaches, with a single
EU entry point across GDPR/NIS2/DORA. **Build to 72h until the amendment is
adopted and applicable.** Mechanics: rules/06.

**Other engineering-facing articles:** Art. 25 (privacy by design/default —
rules/02), Art. 30 (RoPA — rules/01), Art. 32 (security of processing — encryption,
resilience, testing), Arts. 15–22 (user rights — rules/03), Art. 28 (processor
DPAs — rules/05 §5).

## 2. US state privacy laws — the patchwork

As of 2026, **twenty states** have comprehensive consumer privacy laws in effect;
Indiana, Kentucky, and Rhode Island took effect 1 Jan 2026 (verified via IAPP/
MultiState trackers — re-check the tracker for new states before scoping).
Applicability thresholds vary (typically 100k consumers, or 25k + revenue share
from data sales; Rhode Island as low as 35k).

**Engineer to the strictest common denominator instead of per-state logic:**
- Rights: access, deletion, correction, portability, opt-out of sale/share/
  targeted advertising — one rights pipeline (rules/03) serving all states.
- **Honor Global Privacy Control** as a binding opt-out signal (required under
  CCPA/CPRA regulations and several other states).
- Sensitive data: opt-in consent before processing (most states) — same consent
  machinery as GDPR Art. 9.
- CCPA/CPRA specifics: "sale/share" is defined broadly enough to cover ad-tech
  data flows; "Do Not Sell or Share" link; service-provider contracts restricting
  use (the DPA analog); California also enforces data-broker registration and
  (effective 2026) location/health-adjacent restrictions.
- CPPA's finalized regulations (effective 1 Jan 2026): **risk assessments**
  (DPIA analog) for high-risk processing — pre-2026 processing assessed by
  31 Dec 2027, first submissions to the CPPA by 1 Apr 2028; **ADMT**
  significant-decision obligations (pre-use notice, opt-out, access right) from
  **1 Jan 2027** — same profiling opt-out machinery as rules/03 §7; annual
  **cybersecurity audits** phase in with certifications due 1 Apr 2028–2030 by
  revenue tier.
- Universal quirk to encode: deletion/access SLAs cluster at 45 days; cure
  periods vary and are disappearing — don't architect around "we'll fix it if
  warned."

No federal comprehensive law as of June 2026; FTC Act §5 (unfair/deceptive)
still applies everywhere — your privacy policy is a promise your code must keep.

## 2b. Children's & minors' data — strictest tier everywhere

If your service is child-directed or you have actual knowledge of users under 13
(US COPPA) — or under 16/18 for various state minor laws and GDPR Art. 8
(member-state ages 13–16) — obligations jump sharply: verifiable parental
consent, hard minimization, no targeted advertising to minors (several state
laws ban it outright for under-18s), default-private settings mandated, age
assurance proportional to risk. Engineering consequences: an age signal in the
data model that gates features/processing (not a birthday collected for fun —
rules/02 §1), separate consent flows, and treating "we don't know users' ages"
as a risk position to document, not an exemption. UK Age Appropriate Design Code
and similar codes apply the same defaults-private logic. This area is enforcement-
heavy and fast-moving — counsel review is non-optional.

## 2c. One capability set serves all regimes

Most regimes demand the same engineering machinery; build once, map many:

| Capability (built per this skill) | GDPR | US states | HIPAA | PCI | AI Act | DORA/NIS2 |
|---|---|---|---|---|---|---|
| Data inventory / RoPA (rules/01) | Art. 30 | scoping | risk analysis | scope def. | data governance | asset mgmt |
| Rights pipeline (rules/03) | Arts. 15–22 | all rights | access/amend | — | — | — |
| Retention automation (rules/03 §6) | Art. 5(1)(e) | required | required | log windows | log retention | — |
| Breach clocks (rules/06) | 72h | state matrix | 60d | brand rules | serious-incident | 24h/4h |
| Access control + audit logs | Art. 32 | safeguards | §164.312 | req. 7/8/10 | logging | ICT risk |
| Vendor/DPA management (rules/05 §5) | Art. 28 | service-provider K | BAAs | TPSP | value chain | third-party register |

## 3. HIPAA — technical safeguards (when you're a covered entity or business associate)

Security Rule technical safeguards (45 CFR §164.312), engineering summary:
access control (unique user IDs, emergency access, auto-logoff, encryption),
audit controls (record and examine activity in systems with ePHI), integrity
controls, person/entity authentication, transmission security.

**Status note (verified June 2026):** HHS published a proposed Security Rule
overhaul (NPRM, Jan 2025) that would make **encryption at rest/in transit and MFA
mandatory** (removing "addressable" flexibility), require asset inventories,
network segmentation, and tighter BA verification. It is **not final as of June
2026** — but build to it anyway: it codifies what competent engineering already
does, and the compliance window after finalization is short (~180–240 days).
Breach notification: HHS + individuals within **60 days** of discovery (media for
500+ records); BAs notify the covered entity. BAAs (business associate
agreements) are the DPA analog — required before PHI flows to any vendor.

## 4. PCI DSS 4.x — scope is the whole game

**Status (verified June 2026):** PCI DSS **v4.0.1** is the only active version
(v4.0 retired 31 Dec 2024). All future-dated v4 requirements became **mandatory
31 March 2025** — including authenticated internal vulnerability scans, expanded
MFA, automated log review, payment-page script integrity and tamper-detection
(requirements 6.4.3/11.6.1 targeting e-skimming), and phishing controls.

**The engineering strategy is descoping, not compliance-spreading:**
1. **Never touch PANs if possible:** hosted payment fields/redirect (PSP-hosted
   iframe) keep card data out of your servers entirely → SAQ-A-class scope.
2. **If you must touch, tokenize at the edge** (rules/02 §3) and segment: the CDE
   (cardholder data environment) is an isolated network/account with its own
   access control; everything that can reach it is in scope — flat networks make
   the whole company in scope.
3. **Never store:** CVV (prohibited post-auth, full stop), track data; PAN only
   if a documented business need survives challenge, then encrypted with PCI-grade
   key management.
4. E-commerce pages: inventory and integrity-check all scripts on payment pages
   (CSP + SRI + tamper monitoring) — mandatory since the 2025 date, and the top
   gap found in 2025–26 assessments.

## 5. EU AI Act — engineering obligations & current timeline

**Timeline (verified June 2026 — moving target, re-verify):**
- In force 1 Aug 2024. Prohibited practices + AI literacy: applicable since
  **2 Feb 2025**. GPAI (general-purpose model) obligations: since **2 Aug 2025**.
- General applicability: **2 Aug 2026**.
- **Digital Omnibus on AI (adopted: Parliament 16 Jun 2026, Council 29 Jun 2026;
  OJ publication pending as of early Jul 2026):** postpones high-risk
  obligations — Annex III (use-case high-risk: employment, credit, education,
  essential services...) from Aug 2026 to **2 Dec 2027**; Annex I (AI in
  regulated products) to **2 Aug 2028**. These are now the operative dates; do
  not treat the delay as a reason to defer architecture — the obligations are
  data/logging/docs-shaped and cheap at design time, brutal at retrofit time.
  The omnibus also adds a prohibited practice (AI generation of CSAM /
  non-consensual intimate content) and postpones Art. 50 synthetic-content
  marking to **2 Dec 2026** for systems on the market before 2 Aug 2026.

**Engineering obligations if your system is high-risk (provider side):** risk
management system across lifecycle; data governance (training-data relevance,
representativeness, error/bias examination — your data catalog extends to
training datasets); technical documentation; **automatic event logging** through
the system's life; human-oversight affordances; accuracy/robustness/cybersecurity
testing; post-market monitoring. Deployers: use per instructions, human
oversight, input-data quality, log retention (≥ 6 months), worker notification.
GPAI providers: training-content summary, copyright policy, downstream
documentation (systemic-risk tier adds evals and incident reporting).
Transparency (Art. 50): disclose AI interaction (chatbots), machine-readable
marking of synthetic content / deepfakes — applicability aligned with the 2026–27
dates above.

## 6. DORA & NIS2 — sector awareness

- **DORA** (EU financial entities + their critical ICT providers): applicable
  since **17 Jan 2025**, first enforcement cycle underway in 2026. Engineering
  surface: ICT risk management, **major-incident reporting (initial notification
  within 4h of classifying as major / max 24h from awareness; intermediate 72h;
  final ≤ 1 month)**, digital operational resilience testing (TLPT for
  significant entities), ICT third-party register and contract clauses. If you
  sell to EU banks/insurers, expect DORA clauses in contracts even as a vendor.
- **NIS2** (EU essential/important entities — energy, transport, health, digital
  infra, cloud/DNS, managed services...): transposition deadline was Oct 2024;
  many member states transposed late (infringement procedures ran through
  2025–26) — check the national law that applies to you. Incident reporting:
  **early warning 24h, incident notification 72h, final report ≤ 1 month**.
  Management liability and supply-chain security requirements flow down to
  vendors.

## 7. Data residency & sovereignty patterns

When law or contract requires data to stay in-region (GDPR transfers, sector
rules, public-sector procurement, China/Russia-style localization, customer
contractual residency):

- **Region pinning:** per-tenant home region decided at onboarding; all primary
  storage, backups, and replicas constrained by IaC policy (deny-by-default on
  cross-region replication; policy-as-code checks — rules/05 §4). Tenant→region
  routing at the edge.
- **In-region processing, not just storage:** compute, queues, caches, telemetry,
  and supportability paths stay in-region; centralized logging that ships EU user
  data to a US SIEM defeats the design — keep regional sinks with cross-region
  access to aggregates/metadata only.
- **Key residency / hold-your-own-key:** keys in in-region KMS (or
  customer-controlled external KMS) so out-of-region copies are useless without
  in-region keys; combine with crypto-shredding (rules/03 §4). This is the
  strongest mitigation against extraterritorial-access concerns, though residual
  legal exposure of a foreign-controlled provider remains a counsel question.
- **The hard parts to design for explicitly:** global uniqueness (email→tenant
  lookup) needs a minimized global directory (identifier + region only); support
  staff access becomes a transfer — gate cross-region admin reads; analytics
  prefer per-region aggregation with only anonymous/aggregate roll-up to global.

```rego
# GOOD: residency enforced as policy-as-code in CI (rules/05 §4) —
# an EU-pinned dataset physically cannot be declared outside allowed regions
deny[msg] {
  r := input.resource_changes[_]
  r.type == "aws_s3_bucket"
  r.change.after.tags.data_residency == "eu"
  not startswith(r.change.after.region, "eu-")
  msg := sprintf("%s: residency=eu but region=%s", [r.address, r.change.after.region])
}
# BAD: residency promised in the enterprise contract, enforced by "the team
# knows"; a replication rule added for latency quietly mirrors the bucket
# to us-east-1 for eight months.
```

## Audit checklist

- [ ] Applicability triage documented: regimes per data type × subject location × sector; reviewed on entering new markets
- [ ] Every cataloged purpose has a recorded lawful basis; legitimate-interest purposes have an LIA and a working objection path
- [ ] Cross-border flows enumerated with transfer mechanism per processor (incl. support/admin access paths); DPF certifications verified where relied on
- [ ] DPIA trigger checklist embedded in design-review process; existing high-risk processing has DPIAs on file
- [ ] Breach capability meets 72h GDPR clock today (rules/06); pending Digital Omnibus changes tracked, not assumed
- [ ] US: single rights pipeline covers strictest state requirements; GPC honored; sensitive-data opt-in implemented; state-tracker re-checked this quarter; California risk-assessment/ADMT/cyber-audit deadlines (2026–2030 phase-in) tracked
- [ ] Minors: age signal modeled and gating where service could reach under-18s; no targeted ads to known minors; parental-consent flow where required
- [ ] HIPAA (if applicable): §164.312 safeguards mapped to controls; encryption + MFA universal (NPRM-proof); BAAs precede every PHI vendor flow
- [ ] PCI: scope minimized (hosted fields/tokenization); no CVV at rest anywhere (grep + scanner); CDE segmented; payment-page script integrity controls live
- [ ] AI Act: systems classified (prohibited/high-risk/transparency/GPAI); for high-risk candidates, logging + data-governance + documentation designed now against the post-omnibus dates
- [ ] DORA/NIS2 (if in sector/supply chain): incident-reporting clocks wired into IR runbooks; third-party register current
- [ ] Residency requirements per tenant/market recorded; region pinning enforced by policy-as-code; key residency where required
- [ ] All dates/statuses in this file re-verified within the last 6 months against primary sources
