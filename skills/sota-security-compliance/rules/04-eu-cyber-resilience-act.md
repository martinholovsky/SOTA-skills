# 04 — EU Cyber Resilience Act (CRA)

The first horizontal EU law that makes **product cybersecurity** a legal
requirement for placing a "product with digital elements" on the EU market. Unlike
the framework crosswalks elsewhere in this skill, the CRA is binding regulation
with CE-marking, penalties, and hard reporting clocks — and its obligations are
overwhelmingly *engineering* obligations (SBOM, vulnerability handling, secure-by-
default, a maintained update channel). Retrofitting them is brutal; design them in.

> **Status (verified July 2026 against EUR-Lex and the European Commission):**
> Regulation **(EU) 2024/2847**, in force **10 Dec 2024**. Phased application:
> **conformity-assessment/notified-body provisions from 11 Jun 2026**;
> **reporting obligations (Art. 14) from 11 Sep 2026**; **main/essential
> requirements from 11 Dec 2027**. Article sub-numbering below should be confirmed
> against EUR-Lex before quoting verbatim; the dates and Art. 14 clocks are
> corroborated by the Commission's summary page. Re-verify — and route
> product-class/conformity-route decisions to counsel or a notified body.

## 1. Does it apply? Scope

- **Product with digital elements (PDE):** any software or hardware product (plus
  its remote data-processing solutions) whose intended or reasonably foreseeable
  use includes a direct or indirect logical/physical data connection to a device or
  network. Components placed on the market separately are covered.
- **Risk tiers → conformity route:** **default** (self-assessment, Module A) →
  **"important" products (Annex III), Class I and Class II** → **"critical"
  products (Annex IV)**. Higher tiers require stricter routes — third-party
  (notified-body) assessment or an EU cybersecurity certification scheme.
- **Open-source nuance:** non-commercial OSS is out of scope. The **open-source
  software steward** role (Art. 24) carries a lighter, tailored regime (a
  cybersecurity policy, vulnerability handling, cooperation) and stewards are **not
  subject to the penalty regime**. Commercial productization of OSS pulls you back
  into full manufacturer obligations.

If you sell software/hardware into the EU and it talks to a network or device,
assume in-scope and confirm the tier — the tier decides how heavy the conformity
route is, not whether the essential requirements apply.

## 2. Essential requirements → engineering work (Annex I)

Annex I has two parts: **Part I = product security properties**; **Part II =
vulnerability-handling process**. Both are engineering.

**Part I — secure by design & default:**
- Ship **without known exploitable vulnerabilities** → a **release gate** that
  blocks known-exploitable findings; a mechanism to know your components' CVE
  status (ties to the SBOM below and to `sota-devsecops` scanning).
- **Secure default configuration** — hardened out of the box, no default
  credentials, minimal attack surface, secure-by-default TLS/auth
  (`sota-code-security`, `sota-network-security`).
- Protect **confidentiality/integrity** of data and commands (encryption,
  authenticated updates), **minimize attack surface**, and provide
  **security-relevant logging** (`sota-observability`).

**Part II — vulnerability handling (for the whole support period):**
- **SBOM** covering at least the top-level dependencies → **generate in CI/CD**
  (SPDX or CycloneDX), keep it current per release, and be able to produce it
  (`sota-devsecops`). Pair with **VEX** to communicate which listed components are
  actually exploitable.
- **Coordinated Vulnerability Disclosure (CVD) policy** → a published intake
  (`security.txt`, a disclosure address/portal) and a documented handling process.
- **Timely security updates** over the **support period — by default at least 5
  years** (or the product's expected use time if shorter; confirm the exact Article
  reference in EUR-Lex): a **signed update channel** and a maintained
  long-lived branch. Updates must be **without delay** and **free** for security
  fixes; separable from feature updates.

## 3. The reporting clocks (Article 14) — wire them into on-call

For an **actively exploited vulnerability** in your product **or** a **severe
incident** affecting its security, report to the designated coordinating **CSIRT**
*and* **ENISA** via the single reporting platform:

| Stage | Deadline |
|---|---|
| **Early warning** | **≤ 24 hours** of awareness |
| **Notification** | **≤ 72 hours** of awareness |
| **Vulnerability final report** | ≤ 14 days after a corrective/mitigating measure is available |
| **Severe-incident final report** | ≤ 1 month after the incident notification |

Engineering consequence: this is a **detection + telemetry + workflow** problem,
not a legal one. You need to *know* within hours that a vuln in your product is
being exploited (threat intel, telemetry, disclosure intake — `sota-detection-
engineering`, `sota-observability`) and a rehearsed reporting runbook. A clock that
depends on someone happening to notice is already blown. These clocks sit alongside
NIS2 (24h/72h) and DORA (4h/24h/72h) covered in `sota-privacy-compliance` rules/04
§6 — build one incident pipeline that satisfies the strictest applicable clock.

## 4. Conformity & the harmonized-standards route

- **CE marking** signals CRA conformity. **Presumption of conformity** flows from
  **harmonized standards** being drafted by CEN/CENELEC under a Commission
  standardization request (a horizontal **EN 40000** series for all digital
  products, plus vertical/OT tracks).
- **Conformity routes:** internal control (Module A self-assessment) for default
  products; **third-party assessment via a notified body** or an **EU cybersecurity
  certification scheme** for important/critical classes.
- **ISA/IEC 62443 and NIST frameworks** are widely expected to *inform* the
  harmonized standards and are common industry mappings — CEN/CENELEC is adapting
  **EN IEC 62443-4-1 / 4-2** as the OT/industrial route (rules/05). **But being a
  formally-recognized presumption-of-conformity route depends on the harmonized
  standards actually cited in the Official Journal**, which are still being
  finalized (target dates around late 2026). *Flag: evolving — confirm the
  published hEN list at use time before claiming conformity via a standard.*

**Practical stance:** build to Annex I now (SBOM, CVD, signed updates, secure-by-
default, no-known-exploitable-vulns, the reporting pipeline). Those are true
regardless of which harmonized standard you later certify against, and they are the
expensive-to-retrofit parts. Track the hEN list; don't wait for it to start.

## 5. What this shares with the rest of the library

The CRA is mostly a **repackaging of good product-security engineering** with legal
teeth and deadlines. Reuse, don't rebuild:
- SBOM/provenance/signing → `sota-devsecops`; secure-by-default & vuln classes →
  `sota-code-security` + language skills; update-channel signing keys →
  `sota-secrets-management`; the incident/reporting pipeline → `sota-detection-
  engineering` + `sota-observability`; OT products → rules/05 (62443).

## Audit checklist

- [ ] CRA applicability determined: is it a PDE placed on the EU market? tier (default / important Class I–II / critical) identified; OSS-steward status if relevant
- [ ] Release gate blocks **known exploitable vulnerabilities** at ship; component CVE status known via SBOM + scanning
- [ ] **SBOM generated in CI/CD** (SPDX/CycloneDX), current per release, producible on request; VEX used to scope exploitability
- [ ] Secure-by-default config verified: no default credentials, hardened defaults, minimal attack surface, authenticated/encrypted comms and updates
- [ ] **Coordinated Vulnerability Disclosure** intake published (security.txt / portal) with a documented handling process
- [ ] **Signed update channel** and a maintained branch covering the support period (default ≥ 5 years / expected use time); security updates delivered without delay, free, separable
- [ ] Article 14 reporting pipeline built and rehearsed: detection → 24h early warning / 72h notification to CSIRT + ENISA; final reports (14 days / 1 month) covered; unified with NIS2/DORA clocks where applicable
- [ ] Conformity route chosen for the tier (self-assessment vs notified body / certification scheme); CE-marking obligations understood
- [ ] Harmonized-standard reliance (incl. 62443 for OT) confirmed against the current OJ-published hEN list, not assumed
- [ ] All CRA dates/Article references re-verified against EUR-Lex / the Commission within the last 6 months (timeline is live: reporting from 11 Sep 2026, main obligations from 11 Dec 2027)
