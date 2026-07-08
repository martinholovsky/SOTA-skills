# 07 — Active Directory Attack Detection

Detective controls for on-premises **Active Directory**: the Kerberos/NTLM
attacks (Kerberoasting, AS-REP roasting, golden/silver tickets, delegation
abuse), the domain-dominance techniques (DCSync, DCShadow), **ADCS** abuse, NTLM
relay, password spraying, and RBCD writes — plus the AD-specific deception that
catches them with near-zero false positives.

The **preventive** side — why these attacks work and how to design them out
(tiering, delegation hygiene, gMSA/dMSA, ADCS template hardening, KB5014754,
LAPS, `krbtgt` rotation) — lives in **sota-identity-access rules/07 (AD
hardening)**. Detect here; harden there. This file assumes the generic detection
discipline of rules/01 (ADS docs, detection-as-code, tuning with expiry) and the
telemetry principle of rules/02: **you cannot detect what you do not collect** —
so telemetry comes first.

## 1. Telemetry prerequisites

Domain-controller Security logs are the primary source; most AD attacks are
invisible unless **Advanced Audit Policy** subcategories are enabled and DC logs
are shipped centrally (local DC logs roll over fast and are the first thing an
attacker clears). Verify each event's meaning at
`learn.microsoft.com/.../auditing/event-<id>`.

| Event ID | Meaning | Why it matters |
|---|---|---|
| **4768** | Kerberos **TGT** requested (AS-REQ) | Ticket encryption type; account/host baselining; AS-REP roasting |
| **4769** | Kerberos **service ticket** requested (TGS-REQ) | **Kerberoasting** — RC4 (etype 0x17) TGS spikes; silver-ticket clues |
| **4770** | Kerberos service ticket **renewed** | Ticket-lifetime anomalies |
| **4662** | Operation performed on an AD **object** | **DCSync** — replication extended-rights GUIDs; sensitive-object access |
| **4624 / 4625** | Successful / **failed** logon | Password spray (4625 fan-out), lateral movement, logon-type anomalies |
| **5136** | A **directory-service object was modified** (with old/new value) | **RBCD** writes to `msDS-AllowedToActOnBehalfOfOtherIdentity`; ACL/attr tamper. Requires **DS Access → Directory Service Changes** auditing + SACLs |
| **8004** | **NTLM authentication** audit (NTLM Operational log, not Security) | NTLM usage/relay; requires *Restrict NTLM: Audit* policies |
| **4886 / 4887** | ADCS: certificate request **received** / **issued** | ADCS abuse (ESC1 requests, on-behalf-of enrollment). Requires CA "issue and manage" auditing |

**Baseline to enable on every DC:** Account Logon (Kerberos Authentication
Service + Service Ticket Operations, Credential Validation), Logon/Logoff, DS
Access (Directory Service Changes, with SACLs on tier-0 objects/OUs), and — where
NTLM/ADCS in scope — the NTLM Restrict-audit policies and CA object-access
auditing. Ship to the SIEM; **don't triage on the DC.** EDR/host telemetry
(LSASS access, `lsass` dumps, tool signatures) corroborates ticket-forgery and
credential-theft detections that the Security log alone can't confirm.

## 2. Detections (vendor-neutral logic sketches)

Sketches are Sigma-style pseudo-logic — compile to your SIEM (KQL/SPL/EQL) via
rules/03. Each carries an ATT&CK mapping (verify IDs at `attack.mitre.org`), the
dominant false positives, and triage/enrichment notes.

### Kerberoasting — T1558.003

```
source: Security 4769
where TicketEncryptionType == 0x17 (RC4)        # AES = 0x11/0x12
  and ServiceName not in (krbtgt, machine-accounts ending in '$')
  and TargetUserName is a real user account
detect: one principal requesting TGS for many distinct SPNs in a short window,
        OR any RC4 TGS for an account that normally negotiates AES
```

- **Signal:** RC4 (0x17) service-ticket requests — an attacker downgrades to the
  crackable etype — especially a **fan-out** of distinct SPNs from one account.
- **FPs:** legacy apps/appliances that genuinely negotiate RC4; scanners. Reduce
  by AES-hardening service accounts (identity rules/07) so RC4 becomes anomalous,
  then alert on RC4 at all.
- **Enrich:** requesting account, source host, count of distinct SPNs; a spike
  from a workstation (not an app server) is high-fidelity.

### AS-REP roasting — T1558.004

```
source: Security 4768
where PreAuthType == 0 (no pre-authentication)
  and TicketEncryptionType == 0x17 (RC4)
detect: AS-REQ for a preauth-disabled account, esp. many accounts from one source
```

- **Signal:** a TGT issued without pre-auth is the roastable AS-REP. In a hardened
  domain **no account should have pre-auth disabled** (identity rules/07), so any
  such 4768 is inherently suspicious. **FPs:** rare legacy accounts — enumerate
  and allowlist them (and fix them).

### DCSync — T1003.006

```
source: Security 4662
where Properties contains a replication extended-right GUID:
      1131f6aa-9c07-11d1-f79f-00c04fc2dcd2  (DS-Replication-Get-Changes)
      1131f6ad-9c07-11d1-f79f-00c04fc2dcd2  (…-Get-Changes-All)
      89e95b76-444d-4c62-991a-0facbeda640c  (…-Get-Changes-In-Filtered-Set)
  and AccountName is NOT a domain controller ('$' machine acct) and not AAD Connect
detect: replication request from any non-DC principal
```

- **Signal:** replication rights are used by **DCs only** — a non-DC principal
  invoking them is DCSync (credential theft, incl. `krbtgt`). **FPs:** DCs
  themselves, Entra Connect / AD sync accounts, some backup/monitoring tools —
  **allowlist the known replicators explicitly** and alert on everything else.
  High severity; pairs with a golden-ticket watch afterward.

### Golden & silver tickets — T1558.001 / T1558.002

- **Golden** (forged TGT with the stolen `krbtgt` key): anomalous **TGS (4769)
  without a preceding TGT request (4768)** for the same user/session; tickets with
  abnormal lifetimes (e.g. default 10-year forgeries) or accounts/RIDs that don't
  exist; RC4 tickets where the domain is AES. **Silver** (forged TGS for one
  service, signed with the service/computer key): **service access with no
  corresponding 4769 at the DC** — because a silver ticket never contacts the KDC.
  That absence is the tell: correlate service logons (4624 on the member server)
  against the DC's 4769 stream; a service session with no matching TGS is
  suspicious. **Enrich** with EDR ticket telemetry; these are forgery techniques
  so log *absence* and lifetime anomalies matter more than a single event.

### DCShadow — T1207 (Rogue Domain Controller)

```
detect: unexpected registration of a new nTDSDSA / server object or SPN
        (GC/E3514235-… replication SPN) on a non-DC computer  (5136/4742),
   then a replication push (4662 GetChanges) from that fake 'DC'
```

- A rogue-DC registration lets an attacker **push** malicious directory changes
  (e.g. SID history, ACLs) that bypass normal write auditing. **Signal:** a host
  that is not a real DC suddenly carrying DC-like objects/SPNs, followed by
  replication. **FPs:** legitimate DC promotion (`dcpromo`) — correlate with
  change tickets. Rare and high-severity.

### ADCS abuse — T1649 (Steal or Forge Authentication Certificates)

```
source: Security 4886/4887 (CA)  + 4768/4769 (subsequent auth)
detect (ESC1-style): certificate request on an auth-EKU template where the
        Requester != the Subject/SAN principal (enrollee-supplied SAN),
   OR a cert issued for a high-privilege principal to a low-priv requester,
   OR PKINIT TGT (4768) using a certificate right after an anomalous issuance
```

- **Signal:** the SAN/UPN in the issued cert **doesn't match the requester** (the
  ESC1 primitive), or a low-privileged account obtaining a cert that authenticates
  as an admin, then a **cert-based TGT (4768, PKINIT)** shortly after. **FPs:**
  enrollment agents legitimately enrolling on behalf of others (allowlist them),
  auto-enrollment. **Enrich** with the template name and EKU. See identity
  rules/07 §3 for which templates are dangerous (ESC1/ESC4/ESC6/ESC8).

### NTLM relay & forced authentication — T1187

```
source: NTLM 8004 + Security 4624
detect: NTLM authentication where the *source* workstation and the account's
        home host disagree (relayed identity), NTLMv1 usage at all,
   OR a DC/computer account authenticating to an unexpected host right after a
      coercion trigger (EFSRPC/PetitPotam-class RPC)
```

- **Signal:** NTLM (esp. v1) where Kerberos was expected; a machine account
  authenticating outbound to an operator-controlled host (relay to LDAP/ADCS).
  **FPs:** legacy apps that only speak NTLM — inventory and allowlist, then treat
  new NTLM as anomalous. Pairs with the SMB/LDAP-signing hardening (identity
  rules/07 §2) that makes relay fail.

### Password spraying — T1110.003

```
source: Security 4625 (and 4768 failures with Kerberos error 0x18)
detect: one source (or few) → many distinct target accounts failing auth
        within a window, low attempts-per-account (below lockout threshold)
note: attackers prefer Kerberos/LDAP pre-auth failures (4768/4771) over SMB 4625
      to stay quieter — watch both surfaces
```

- **Signal:** horizontal fan-out (many accounts, few tries each) rather than
  vertical brute force. **FPs:** a misconfigured service with stale creds hitting
  many accounts; VPN/mobile reconnection storms. **Enrich** with source IP/ASN,
  time-of-day, and whether any attempt succeeded (pivot to 4624).

### RBCD / delegation-attribute writes — T1098 (Account Manipulation)

```
source: Security 5136
where AttributeLDAPDisplayName == 'msDS-AllowedToActOnBehalfOfOtherIdentity'
      (or msDS-AllowedToDelegateTo, servicePrincipalName on a user, userAccountControl
       delegation flags)  and OperationType == Value Added
detect: any write to the RBCD attribute by a non-tier0 principal
```

- **Signal:** writing `msDS-AllowedToActOnBehalfOfOtherIdentity` sets up
  resource-based constrained-delegation abuse; an SPN suddenly added to a *user*
  account enables Kerberoasting/targeted attacks. **FPs:** legitimate delegation
  configuration by admins — allowlist the tier-0 change process and alert on
  everyone else. Requires Directory Service Changes auditing + SACLs (§1).

### dMSA abuse / BadSuccessor — T1098 (where Windows Server 2025 DCs exist)

```
source: Security 5137/5136 + Directory Service 2946
detect: dMSA object (msDS-DelegatedManagedServiceAccount) created (5137) by a
        non-tier0 principal or in an unusual OU,
   OR a write (5136) to migration-link attributes
      msDS-ManagedAccountPrecededByLink / msDS-DelegatedMSAState,
   OR repeated dMSA TGTs / key-package fetches (2946) for one dMSA
```

- **Signal:** BadSuccessor (CVE-2025-53779, patched Aug 2025) links an
  attacker-created dMSA to a privileged account so the KDC merges that account's
  privileges and keys into the dMSA's tickets. The patch closes the direct
  escalation, but dMSA linkage still yields credential acquisition/lateral
  movement in already-compromised domains — the writes stay detection-worthy.
  **FPs:** genuine gMSA→dMSA migrations — allowlist the tier-0 migration
  process. Requires SACLs on dMSA objects/attributes (§1); event 2946 is in the
  Directory Service log, not Security.

Deception in AD yields near-zero-FP signals (identity attackers walk into it):

- **Honeytoken accounts / fake SPNs.** A decoy service account with an SPN (so it
  appears in any Kerberoast enumeration) and a **deliberately crackable-looking
  password**, but no real access. *Any* **4769 (TGS request) for that SPN** = an
  attacker enumerating/roasting — no legitimate service ever requests it. Similarly
  a decoy account with pre-auth disabled catches AS-REP roasters.
- **Canary AD objects.** A tempting-but-unused privileged-looking group or user,
  or an object with a **SACL** so any read/enumeration raises 4662. LDAP recon
  (BloodHound-style collection — neutral example) trips it.
- **Deceptive delegation / ACL bait.** An object that *looks* like a soft
  escalation path but is monitored; interaction is malicious by definition.
- **Wiring.** Every deception asset alerts at **max severity with full context**
  (source host/account) and routes straight to IR (rules/04 routes, rules/06
  responds). Place decoys **in the path attackers must traverse** — the SPN they
  will enumerate, the group they will target — not in an unused corner (see
  rules/05 §4 and **sota-secrets-management rules/04** for credential-honeytoken
  mechanics).

**Cross-reference:** enable/verify the underlying audit policy and log shipping
with rules/02; test every detection here against the real technique (Atomic Red
Team AD atomics, or purpose-built AD emulation) per rules/06 before trusting it —
an untested Kerberoasting rule is a hope, not a detection.

## Audit checklist

- [ ] Are DC **Advanced Audit Policy** subcategories enabled (Kerberos AS + Service Ticket ops, Credential Validation, Logon, **Directory Service Changes with SACLs on tier-0 objects**) and **DC Security logs shipped centrally** (not triaged on the DC)?
- [ ] Is **NTLM audit (event 8004)** and **CA issuance auditing (4886/4887)** enabled where NTLM/ADCS are in scope?
- [ ] Is there a **Kerberoasting** detection on **RC4 (0x17) 4769** with SPN fan-out, and is it meaningful (are service accounts AES-hardened so RC4 is anomalous)?
- [ ] Is there an **AS-REP roasting** detection on **4768 PreAuthType==0 / RC4**, with preauth-disabled accounts enumerated and allowlisted?
- [ ] Does a **DCSync** detection watch **4662 for replication GUIDs** (`…dcd2`, `…dcAll`, filtered-set) from **non-DC, non-sync** principals, with the legitimate replicators explicitly allowlisted?
- [ ] Are **golden/silver ticket** indicators covered — TGS (4769) without a preceding TGT (4768), abnormal ticket lifetimes/RIDs, and **service logons with no matching DC TGS** (silver)?
- [ ] Is **DCShadow** covered (rogue `nTDSDSA`/DC SPN registration on a non-DC, then replication)?
- [ ] Is **ADCS abuse (T1649)** detected — cert request where **requester != SAN principal (ESC1)**, privileged cert to low-priv requester, PKINIT TGT after anomalous issuance — with enrollment agents allowlisted?
- [ ] Is **NTLM relay / forced auth (T1187)** covered (NTLMv1 usage, relayed-identity mismatch, machine-account outbound auth after coercion)?
- [ ] Is **password spraying (T1110.003)** detected across **both 4625 and Kerberos 4768/4771 failures** (horizontal fan-out below lockout threshold)?
- [ ] Is there a **5136 detection on writes to `msDS-AllowedToActOnBehalfOfOtherIdentity`** (RBCD) and SPN-added-to-user, alerting on non-tier-0 writers?
- [ ] Where **Windows Server 2025 DCs** exist, is **dMSA abuse (BadSuccessor, CVE-2025-53779)** covered — dMSA creation (5137) by non-tier-0 principals or in unusual OUs, **5136 writes to `msDS-ManagedAccountPrecededByLink` / `msDS-DelegatedMSAState`**, and repeated dMSA TGTs (2946)?
- [ ] Are **honeytoken SPN accounts / canary objects** deployed (any 4769/4662 against them = high-fidelity alert) and **wired to IR at max severity**?
- [ ] Is each detection **ATT&CK-mapped, FP-documented, and validated against the real technique** (rules/06) before it is trusted?
- [ ] Does each detection carry known **false positives and an owner** (rules/01/04), with suppressions expiring rather than permanent?
