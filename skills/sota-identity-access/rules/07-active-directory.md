# 07 — Active Directory, Kerberos & ADCS Hardening

Scope: hardening and secure design of on-premises **Active Directory Domain
Services (AD DS)**, the **Kerberos** and **NTLM** authentication planes, **Active
Directory Certificate Services (ADCS)**, and the credential-protection controls
that blunt lateral movement and domain-dominance attacks — plus the boundary
where AD meets **Entra ID** in a hybrid estate.

This file owns the **preventive** posture (build it so the attack can't land).
The **detective** posture — which events to collect, and the Sigma-style logic
that catches Kerberoasting, DCSync, golden tickets, ADCS abuse, and RBCD writes
— lives in **sota-detection-engineering rules/07 (AD attack detection)**. Harden
here; detect there. For app-level login/session mechanics see
**sota-code-security**; for the identity *model* (JML, least privilege, MFA) see
rules/03–06 of this skill.

AD is the classic **tier-0 asset**: a single Domain Admin or `krbtgt` compromise
is total, durable, and hard to evict. Design assuming an attacker already holds a
low-privileged domain account — that is the realistic starting position.

## 1. Enterprise Access Model & tiering

- The legacy **ESAE / "red forest"** (a dedicated hardened administrative forest)
  was **retired as Microsoft's default recommendation in December 2020** and
  replaced by the **modern privileged-access strategy** and the **Enterprise
  Access Model (EAM)** (verify: `learn.microsoft.com/security/privileged-access-workstations/esae-retirement`).
  Do not stand up a new red forest as a first move; existing ones can remain but
  are no longer the recommended pattern.
- The EAM generalizes the old three-tier model (Tier 0/1/2) into **access
  planes** — control, management, and data/workload — and folds in cloud/Entra
  and user/app access. **Tier 0 = anything that can control AD identity**: DCs,
  `krbtgt`, Domain/Enterprise Admins, ADCS CAs, AD-integrated DNS, sync servers,
  and any account or host that can gain those. The core rule survives the
  rename: **a higher tier never authenticates to (or exposes its credential on) a
  lower-tier host.**
- **Clean source / no credential exposure downhill.** A Tier-0 admin never logs
  on interactively to a workstation or member server (that credential can be
  harvested from LSASS). Administer tier-0 from **Privileged Access Workstations
  (PAWs)** and enforce logon isolation with **authentication policies and silos**
  (§4) plus `Deny log on` User-Rights restrictions per tier.
- **Separate admin identities per plane** (rules/05): a human has a normal
  account and distinct privileged account(s); privileged accounts never read
  email or browse. Enforce **just-in-time** elevation, not standing membership in
  Domain Admins.
- Adopt a **least-privilege delegation model** (OU-scoped delegated rights)
  instead of dumping helpdesk/staff into built-in privileged groups. Tools such
  as BloodHound or PingCastle (neutral examples) surface the *attack paths* — the
  transitive edges from a low-priv account to Tier 0 — that this model must cut.

## 2. Kerberos & NTLM hardening

### Delegation (the highest-value misconfig class)

- **Unconstrained delegation** caches the *TGT* of any principal that
  authenticates to the host, so a compromise of that host (or coercing a DC to
  authenticate to it) yields a DC TGT → domain compromise. **Eliminate it.** No
  account should carry `TRUSTED_FOR_DELEGATION` except, unavoidably, DCs. Audit
  `userAccountControl` for the flag across users and computers.
- **Constrained delegation** (`msDS-AllowedToDelegateTo`) limits which SPNs a
  host may impersonate to — better, but **protocol transition**
  (`TRUSTED_TO_AUTH_FOR_DELEGATION`, "any authentication") lets the host mint
  tickets for arbitrary users to those services; scope it tightly and prefer
  Kerberos-only (`use-any-protocol` off).
- **Resource-based constrained delegation (RBCD)** moves the trust to the
  *target* (`msDS-AllowedToActOnBehalfOfOtherIdentity`). It is the cleanest model
  *and* a favourite escalation primitive: an attacker who can **write that
  attribute** on a computer object (often combined with a controlled machine
  account) impersonates any user to it. Restrict who can write it; the write
  itself is a key detection signal (detection rules/07, event 5136).
- Mark truly sensitive accounts **`Account is sensitive and cannot be
  delegated`** (or add them to **Protected Users**, §4) so no delegation can
  impersonate them.

### Service accounts, Kerberoasting & AS-REP roasting

- **Kerberoasting** (ATT&CK **T1558.003**): any domain user can request a TGS for
  any SPN; if it is encrypted with **RC4 (etype 23)** the reply is offline-
  crackable to the service account's password. Mitigations, in order:
  - **Managed service accounts.** **gMSA** (group Managed Service Account) and,
    in **Windows Server 2025, dMSA** (delegated Managed Service Account) give
    accounts **fully randomized, auto-rotated 120-character keys** that are not
    crackable, and dMSA additionally **binds authentication to device identity**
    and disables the migrated account's old password (verify:
    `learn.microsoft.com/windows-server/identity/ad-ds/manage/delegated-managed-service-accounts/delegated-managed-service-accounts-overview`).
    Prefer these over human-set service passwords wherever the service supports
    them. *Caveat:* dMSA is new and has published abuse research — **BadSuccessor**
    (privilege escalation via dMSA migration) and **Golden dMSA** (key
    derivation) — so restrict who can create/migrate dMSAs and monitor it
    (detection rules/07); treat these as "needs ongoing verification" as patches
    land.
  - **AES-only service accounts.** Set `msDS-SupportedEncryptionTypes` to
    AES128/256 (etype 17/18) and disable RC4 so the roast target is far more
    expensive; do this estate-wide only after confirming no RC4 dependency.
  - For any remaining human-managed service account: a **long random password
    (25+ chars)** and rotation, and **minimum SPNs** (SPN hygiene — remove stale/
    duplicate SPNs; never put an SPN on a high-privilege user, which turns a
    Domain Admin into a roastable target).
- **AS-REP roasting** (ATT&CK **T1558.004**): accounts with **Kerberos
  pre-authentication disabled** (`DONT_REQ_PREAUTH`) hand out an offline-crackable
  AS-REP to any unauthenticated requester. **Require pre-auth on every account**;
  the flag should appear nowhere.

### NTLM, relay & machine-account quota

- **Prefer Kerberos; retire NTLM.** Audit NTLM use (NTLM Operational log,
  event 8004 — detection rules/07) then restrict it with the **Network Security:
  Restrict NTLM** policies; NTLMv1 must be disabled outright.
- **Relay mitigations.** Enforce **SMB signing** and **LDAP signing + channel
  binding (EPA)** so coerced authentications can't be relayed. Windows Server 2025
  hardens the defaults: **SMB signing is required by default** (also on Windows 11
  24H2), and new DCs default to **requiring LDAP signing** (new "LDAP server
  signing requirements Enforcement" policy); **LDAP channel binding still defaults
  to *When supported*, not *Required***, so set it to Always where clients allow
  (verify: `techcommunity.microsoft.com` LDAP-signing Server-2025 post and
  `learn.microsoft.com/windows-server/identity/ad-ds/ldap-signing`). Disable/patch
  coercion surfaces (PetitPotam-class RPC).
- **Machine-account quota.** `ms-DS-MachineAccountQuota` **defaults to 10**,
  letting *any* authenticated user join up to ten computer accounts — the fuel for
  RBCD and several escalation chains. **Set it to 0** and grant machine-join via a
  delegated right instead.

## 3. Active Directory Certificate Services (ADCS)

ADCS is a tier-0 system: a CA that issues an authentication certificate for an
arbitrary principal is a domain-compromise primitive. The escalation classes were
catalogued by **SpecterOps ("Certified Pre-Owned", Schroeder & Christensen,
2021)** — originally **ESC1–ESC8** — and **community-extended through ~ESC16 as
of 2025** (Certipy/Oliver Lyak, TrustedSec; verify the current set against
SpecterOps' publications and the Certify/Certipy docs before citing a specific
number).

- **Template hardening (ESC1–ESC4).** For any template with an authentication EKU
  (Client Auth / Smart Card Logon / PKINIT / *Any Purpose*):
  - **Never allow enrollee-supplied subject** (`CT_FLAG_ENROLLEE_SUPPLIES_SUBJECT`)
    on an auth template — that is **ESC1** (attacker names an arbitrary SAN/UPN).
  - Require **manager approval** and/or **authorized-signature (enrollment agent)**
    for sensitive templates; don't grant broad **Enroll**/**AutoEnroll** to
    `Domain Users`/`Authenticated Users`.
  - Lock down **template and CA ACLs** — write access to a template is **ESC4**
    (rewrite it into ESC1); dangerous CA flags (`EDITF_ATTRIBUTESUBJECTALTNAME2`)
    are **ESC6**.
- **Web enrollment / relay (ESC8, ESC11).** The HTTP enrollment endpoints accept
  relayed NTLM → cert for a DC. Disable web enrollment if unused; otherwise
  enforce **HTTPS + EPA** and the NTLM-relay controls in §2.
- **Enrollment-agent restrictions.** Enrollment-agent certificates let the holder
  enroll *on behalf of* others — restrict which agents, templates, and target
  principals are permitted (CA "Enrollment Agents" tab), or the agent becomes a
  domain-wide impersonation tool.
- **Strong certificate mapping (KB5014754).** The May 2022 update **KB5014754**
  adds a **SID extension** to issued certs and makes DCs enforce **strong
  certificate mapping**, closing the weak implicit-mapping (UPN/SAN) abuse.
  Enforcement timeline (verify at `support.microsoft.com` KB5014754): DCs moved to
  **Full Enforcement with the February 11, 2025 update**, and the ability to fall
  back to Compatibility mode was **removed after the September 9, 2025 update**.
  Ensure CAs embed the SID extension and that no weak `altSecurityIdentities`
  mappings remain.
- **Protect the CA private key** (HSM), restrict CA administration to tier-0, and
  monitor issuance (detection rules/07, events 4886/4887).

## 4. Credential protection

- **Windows LAPS** randomizes and rotates the **local administrator password**
  per machine, killing pass-the-hash lateral movement across identical local
  creds. **Legacy Microsoft LAPS (the MSI) is deprecated as of Windows 11 23H2**;
  use the **built-in Windows LAPS** (Windows Server 2019+ / Win10+), which adds
  **password encryption, history, DSRM-password management, and Entra ID support**
  (verify: `learn.microsoft.com/windows-server/identity/laps/laps-overview`).
- **Protected Users** group: members get hardened Kerberos (no RC4/DES, no NTLM,
  no unconstrained/constrained delegation, no long-lived TGT caching). Put
  **high-value human admins** in it — but not service accounts or accounts that
  legitimately need NTLM, and never the break-glass accounts you might need when
  Kerberos is broken (rules/05).
- **Credential Guard** (VBS-isolated LSA) stops LSASS secret theft
  (pass-the-hash/ticket harvesting) on supported hosts; enable on admin
  workstations and, where compatible, member servers.
- **Authentication policies & silos** bind privileged accounts so their TGTs are
  only usable from designated (PAW/tier-0) hosts and cap TGT lifetime — enforcing
  the clean-source rule of §1 in Kerberos itself.
- **`krbtgt` rotation.** The `krbtgt` hash signs every TGT; its theft enables
  **golden tickets** (durable forgery of any identity). Rotate the `krbtgt`
  password **twice** (to also invalidate the *previous* key, which stays valid one
  cycle), **spaced by more than the maximum ticket lifetime** to avoid breakage —
  on a regular cadence (commonly ~every 6–12 months) and **immediately, twice, on
  any suspected DC/tier-0 compromise**. A never-rotated `krbtgt` is a finding.
  (Same twice-rotation logic applies to a compromised DSRM or trust key.)

## 5. Hybrid / Entra ID boundary

Neutral trade-off notes — the goal is to keep an on-prem compromise from becoming
a cloud compromise (and vice-versa):

- **The sync engine is tier-0.** The directory-sync connector server and its
  **sync/connector account** hold broad read (and, with password-writeback or
  hybrid-join, write) over AD and Entra. Treat that host and account as tier-0;
  compromise of it bridges both directories. Do not let cloud-only admins reduce
  on-prem tiering, or vice-versa.
- **PHS vs PTA (neutral).** **Password Hash Sync (PHS)** syncs a hash-of-a-hash to
  Entra — authentication survives on-prem outages and enables leaked-credential
  detection, at the cost of a derived secret residing in the cloud.
  **Pass-Through Authentication (PTA)** validates against on-prem DCs (no synced
  secret) but introduces the **PTA agent** as an on-prem authentication component
  whose compromise can intercept validations. **Federation (ADFS)** hands the
  entire token-issuance trust to an on-prem STS — a golden-SAML target — and is
  generally the heaviest to secure. Pick per outage-tolerance and threat model;
  document the choice.
- **Cloud Kerberos / hybrid join**: where AD and Entra co-issue, the tier-0
  boundary now spans both control planes — apply the higher bar of the two, and
  keep privileged cloud roles (Global Admin) on separate phishing-resistant
  accounts (rules/06).

## Audit checklist

- [ ] Is a **tier-0 / Enterprise Access Model** boundary defined and enforced (DCs, `krbtgt`, Domain/Enterprise Admins, ADCS CAs, sync servers), with **no higher-tier credential exposed on a lower-tier host** (PAWs + `Deny log on` + auth silos)?
- [ ] Any **unconstrained delegation** outside DCs? (Hunt `userAccountControl` for `TRUSTED_FOR_DELEGATION` — should be DCs only.)
- [ ] Is **constrained delegation** tightly scoped, protocol-transition avoided, and **who can write `msDS-AllowedToActOnBehalfOfOtherIdentity` (RBCD)** restricted?
- [ ] Are sensitive/admin accounts marked **`Account is sensitive and cannot be delegated`** or in **Protected Users**?
- [ ] Do service accounts use **gMSA/dMSA** (randomized keys) or, failing that, **AES-only** encryption and 25+ char rotated passwords? Are there **SPNs on privileged user accounts** (Kerberoast bait) or stale/duplicate SPNs?
- [ ] Any account with **Kerberos pre-auth disabled** (`DONT_REQ_PREAUTH`, AS-REP roastable)? Any **RC4 (etype 23)** still permitted where AES is feasible?
- [ ] Is **NTLM audited and restricted** (NTLMv1 disabled), and are **SMB signing** and **LDAP signing + channel binding (EPA)** enforced (Server 2025 defaults confirmed, channel binding set beyond *When supported* where possible)?
- [ ] Is **`ms-DS-MachineAccountQuota` set to 0** (default 10)?
- [ ] ADCS: any **auth template allowing enrollee-supplied subject** (ESC1), broad **Enroll** to Domain/Authenticated Users, weak **template/CA ACLs** (ESC4), `EDITF_ATTRIBUTESUBJECTALTNAME2` (ESC6), or exposed **web enrollment without HTTPS+EPA** (ESC8)?
- [ ] Are **enrollment agents restricted** by template/target, and is the **CA key HSM-protected** and CA admin tier-0?
- [ ] Is **strong certificate mapping (KB5014754)** enforced — SID extension embedded, Full Enforcement in effect (post-Feb/Sep-2025 timeline), no weak `altSecurityIdentities` mappings?
- [ ] Is **Windows LAPS** (not the deprecated legacy MSI) deployed to randomize/rotate local admin passwords, with encryption + history?
- [ ] Are **Credential Guard** and **authentication policies/silos** enabled for privileged accounts/hosts?
- [ ] Is **`krbtgt` rotated on a cadence and twice on suspected compromise** (rotations spaced beyond max ticket lifetime)? A never-rotated `krbtgt` is a finding.
- [ ] Is the **directory-sync host + connector account treated as tier-0**, and is the **PHS/PTA/federation** choice deliberate, documented, and consistent with the tiering model?
