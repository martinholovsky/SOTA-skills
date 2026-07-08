# 05 — ISA/IEC 62443 for OT / ICS / Embedded

The cybersecurity standard for **operational technology**: industrial control
systems (ICS), industrial automation and control systems (IACS), IIoT, and embedded
industrial products. Its models — **zones and conduits**, **Security Levels**, the
**7 Foundational Requirements** — assume a control-system, availability-first,
physical-process context that general IT frameworks don't. If your code runs a
turbine, a PLC, a medical device, or a factory line, this is your frame.

> **Scope honestly.** 62443 is **not** the right frame for general IT / SaaS / web
> apps — those fit ISO 27001, OWASP/ASVS, and NIST CSF/SSDF (rules/01–03). Reach
> for 62443 when the system is OT/ICS/IACS/embedded/industrial. Statuses below
> verified July 2026 against ISA, IEC, ISAGCA, and ISASecure; certification-scheme
> and CRA-harmonization details are evolving — re-verify at use time.

## 1. Family structure — the parts engineers touch

The series has four groups: **General (1-x)**, **Policies & Procedures (2-x)**,
**System (3-x)**, **Component (4-x)**. The engineering-facing parts:

| Part | What it governs |
|---|---|
| **62443-4-1** (2018) | **Secure product development lifecycle** — requirements on the *supplier's development process*: security requirements definition, secure-by-design, secure implementation, verification/validation testing, defect & patch management, product end-of-life. Prescriptive enough to certify against. |
| **62443-4-2** (2019) | **Technical security requirements for components** — four component types: software application, embedded device, host device, network device. |
| **62443-3-3** (2013) | **System security requirements + Security Levels** — system-level SRs mapped to the 7 FRs and the four SLs. |
| **62443-3-2** | Risk assessment & system design for zones/conduits — sets target SLs. |
| **62443-2-1 / 2-4** | The security *program* (CSMS) for asset owners / service providers — largely organizational (route out per the SKILL boundary). |

## 2. 62443-4-1 vs NIST SSDF — companions, not competitors

Both cover secure development. The difference is prescription:
- **SSDF (rules/03)** is broad, tool-agnostic, and **non-certifiable** — a
  reference framework.
- **62443-4-1** is **narrower and certification-oriented** (measurable process
  requirements, supports the ISASecure **SDLA** certification). It gives
  prescriptive, auditable detail for the same practices SSDF names at a higher
  level.

**Practical stance:** if you already run an SSDF-aligned SDLC (rules/03), you have
most of 62443-4-1; the gap is the *measurable process artifacts* and end-of-
life/patch-management rigor that a 4-1 audit expects. Crosswalk them (rules/01) —
one secure-SDLC, two framings.

## 3. Zones and conduits — the segmentation model

The architecture-driving core. Partition the IACS into **zones** (groupings of
assets by risk, function, and required security) and force all inter-zone
communication through controlled **conduits**:

- A zone groups assets with a common security requirement (e.g., the control zone
  vs. a DMZ vs. the enterprise/IT zone). Assign each zone a **target Security
  Level** from a risk assessment (62443-3-2).
- A conduit is the *only* sanctioned path between zones — a controlled channel
  (firewall, data diode, gateway) where you enforce and monitor traffic. No
  side-channels, no flat OT network.
- This is the OT expression of segmentation and blast-radius control that
  `sota-network-security` covers for IT — apply that skill's depth (default-deny,
  egress control) at the conduit, respecting OT constraints (availability first,
  legacy protocols, no casual patching).

A flat OT network with no zone/conduit model is the equivalent of the flat-network
finding in rules/02 — it makes everything one blast radius and defeats SL
assignment.

## 4. Security Levels (SL 0–4) and the 7 Foundational Requirements

**Security Levels** express resistance to escalating attacker capability:
- **SL 0** none · **SL 1** casual/accidental · **SL 2** intentional, low resources/
  skill · **SL 3** sophisticated, moderate resources (sector specialists) · **SL 4**
  nation-state, high resources.

Each zone carries an **SL vector** — one value per Foundational Requirement — in
three forms you must keep straight:
- **SL-T (Target):** required level, from the risk assessment.
- **SL-C (Capability):** what a properly-configured component/system *can* deliver.
- **SL-A (Achieved):** the actual level after deployment.

**Design obligation: ensure SL-C and SL-A ≥ SL-T for every zone.** Asserting an
SL-T with no risk assessment behind it, or deploying components whose SL-C can't
meet the target, is the core 62443 finding.

**The 7 Foundational Requirements** (all SRs in 3-3 and component requirements in
4-2 map to these):

1. **Identification & Authentication Control (IAC)** — who/what is acting.
2. **Use Control (UC)** — least privilege / authorized actions only.
3. **System Integrity (SI)** — code/config/data not tampered.
4. **Data Confidentiality (DC)** — protect data at rest/in transit.
5. **Restricted Data Flow (RDF)** — zones & conduits enforcement.
6. **Timely Response to Events (TRE)** — detection, logging, response.
7. **Resource Availability (RA)** — availability against DoS/degradation (the
   FR that most distinguishes OT: availability is the top priority, not
   confidentiality).

The mechanisms behind FR1–FR4, FR6 live in `sota-identity-access`,
`sota-code-security`, `sota-secrets-management`, `sota-detection-engineering`;
FR5 in the zone/conduit design (§3); FR7 in resilience/DR
(`sota-cloud-infrastructure`, `sota-architecture`) adapted to OT.

## 5. Certification and the CRA link

- **Certification exists.** **ISASecure** (an ISO/IEC 17065 scheme) certifies:
  **SDLA** → against 62443-4-1 (the dev process); **CSA** (Component Security
  Assurance) → 4-2 (a component); **SSA** (System Security Assurance) → 3-3 (a
  system). *A separate IECEE CB scheme also covers 62443 — confirm scope from a
  primary IECEE source before relying on it.*
- **CRA route (rules/04 §4):** CEN/CENELEC (TC65X WG3) is **adapting EN IEC
  62443-4-1 / 4-2 into CRA harmonized standards** for OT/industrial "important
  products" (CRA Annex III), which would grant presumption of conformity. Target
  dates cluster around **late 2026**, with a compressed runway before CRA
  obligations apply (Dec 2027). *Flag: EN designations and dates are reported
  inconsistently and are moving — verify against the OJ-published hEN list.*

**So for an OT/industrial product sold into the EU:** 62443-4-1/4-2 is likely your
*most direct* path to both a recognized OT security posture and (once harmonized)
CRA conformity. Build to it now; certify when the hENs land.

## Audit checklist

- [ ] 62443 is the *appropriate* frame — system is OT/ICS/IACS/embedded/industrial (not general IT/SaaS, which routes to ISO 27001 / CSF / SSDF)
- [ ] Zones and conduits defined: assets grouped into zones by risk/function; all inter-zone traffic forced through controlled, monitored conduits; no flat OT network
- [ ] Each zone has a **target Security Level (SL-T)** derived from a documented risk assessment (62443-3-2), not asserted
- [ ] Components/systems meet the target: **SL-C and SL-A ≥ SL-T** per zone, per FR; components selected/configured to their required capability level
- [ ] The 7 Foundational Requirements addressed with named mechanisms (IAC, UC, SI, DC, RDF, TRE, RA) — availability (FR7) treated as top priority per OT context
- [ ] Secure development per **62443-4-1** crosswalked to the SSDF SDLC (rules/03); measurable process artifacts, defect/patch management, and product end-of-life defined
- [ ] Component technical requirements (**4-2**) and system requirements (**3-3**) met for the relevant component types
- [ ] Patch/update strategy fits OT constraints (availability, maintenance windows, legacy) while still delivering security fixes over the support period
- [ ] If EU-market: 62443 harmonization path to CRA conformity tracked against the current OJ hEN list (rules/04); certification (ISASecure SDLA/CSA/SSA) pursued where required
- [ ] 62443 part versions, certification-scheme scope, and CRA-harmonization status re-verified against primary sources within the last 6 months
