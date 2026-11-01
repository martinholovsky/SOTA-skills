# 05 — Privileged Access & Workload Identity

Scope: privileged access management (PAM) — admin-account separation, break-glass
design, just-in-time / just-enough elevation, session recording, vaulting — and machine
/ workload identity — SPIFFE/SPIRE, workload identity federation, service-to-service
auth, mTLS identity, short-lived over static credentials.

Privileged identities and machine identities are where a single compromise becomes total
compromise. The governing principle: **no standing privilege and no standing secret** —
elevate just-in-time, authenticate workloads with short-lived federated credentials, and
make every privileged action loud and auditable.

For the *secret-storage* mechanics (Vault dynamic creds, OIDC-federation token exchange,
`kid` rotation) see **[sota-secrets-management** rules/01](../../sota-secrets-management/rules/01-lifecycle-and-workload-identity.md) and [rules/05](../../sota-secrets-management/rules/05-credential-types.md). For mTLS/ZTNA
transport see **[sota-network-security](../../sota-network-security/SKILL.md)**. For K8s SA tokens / OIDC to the API server see
**[sota-kubernetes](../../sota-kubernetes/SKILL.md)**. This file owns the *access-management design*.

## 1. Admin-account separation

- **Admin work uses a separate identity** from daily work. The same human has a normal
  account (email, chat, browsing) and a distinct privileged account; the privileged
  account never reads email or browses the web (the phishing/drive-by surface that
  compromises admin rights).
- Privileged accounts require **phishing-resistant MFA** (FIDO2/passkey — [rules/06](06-mfa-federation-assurance.md)),
  shorter session caps ([rules/02](02-idp-operations.md) §6), and ideally a dedicated admin workstation / PAW or
  identity-aware-proxy-gated access (**[sota-network-security](../../sota-network-security/SKILL.md)**).
- No shared admin accounts. Every privileged action attributes to a named human (or a
  named workload). A shared `root`/`admin` login is a finding — break-glass excepted (§3).

## 2. Just-in-time / just-enough elevation

- **No standing admin.** Default state: the human holds *no* privileged role. To perform
  privileged work they **request elevation** for a specific role/scope, for a bounded
  window, with approval and a reason; the grant auto-expires.
- **Just-enough**: elevate to the *narrowest* role for the task (read-only break-fix vs
  full admin), not blanket superuser.
- Elevation is logged with who/what/when/why/approved-by, and ideally requires a second
  approver for the highest tiers (pairs with SoD, [rules/03](03-authorization-models.md) §4).
- This is the standing-privilege fix for the access-creep and orphaned-admin problems in
  [rules/04](04-lifecycle-provisioning.md): there is simply far less standing privilege to leak or forget.

## 3. Break-glass (emergency access)

Break-glass is the deliberate exception that must exist (the IdP/SSO is down, or the
normal admin path is unavailable) — and it is precisely what attackers target, so it must
be tightly controlled:

- **Exists, but dormant.** A small number of emergency accounts that are *not* used for
  daily work and are normally disabled or credential-less.
- **Logged, time-bound, alerted.** Any use of break-glass fires a **loud real-time alert**
  (it should be impossible to use one quietly), is time-boxed, and is fully audit-logged.
  An *un-alerted* break-glass account is indistinguishable from a backdoor — High finding.
- **Strong credential, split if shared.** If a break-glass credential is a shared secret,
  vault it, split knowledge (no single person holds it), and rotate after every use.
- **The Kanidm pattern**: Kanidm's `admin` and `idm_admin` are explicitly break-glass /
  disaster-recovery accounts — they exist for initial setup and recovery, *not* daily use,
  and are recovered out-of-band from the server host with
  `kanidmd recover-account admin` (or `idm_admin`), which mints a one-time recovery
  credential. Treat that command as a break-glass event: run it only in an emergency, on
  the server, and alert when it happens. Daily admin uses *separate* named accounts, never
  `admin`/`idm_admin`.

```
# Break-glass usage on the Kanidm server host = an auditable emergency event
kanidmd recover-account idm_admin     # generates a one-time recovery credential
# After use: rotate, confirm the alert fired, log the incident, restore normal admin path.
```

## 4. Session recording & vaulting

- For the highest tiers (production database admin, infra root, jump hosts), broker
  privileged sessions through a **PAM/bastion** that records the session (commands /
  keystrokes / screen) and brokers credentials so the human never holds the raw
  credential.
- **Vault credentials, issue dynamically.** Privileged credentials (DB superuser, cloud
  admin) are not handed out long-lived; they are checked out for a session and revoked
  after — Vault/OpenBao dynamic secrets (**[sota-secrets-management** rules/01](../../sota-secrets-management/rules/01-lifecycle-and-workload-identity.md)/02).
- Recordings and access logs are themselves sensitive and tamper-evident; protect and
  retain them per **[sota-privacy-compliance](../../sota-privacy-compliance/SKILL.md)**.

## 5. Machine / workload identity

Workloads need identity too, and the failure mode is the **long-lived static secret** (an
API key or service-account key file baked into config). Replace it:

- **SPIFFE / SPIRE**: every workload gets a cryptographic identity (a SPIFFE ID like
  `spiffe://trust-domain/ns/app`) materialized as a short-lived SVID (X.509 cert or JWT),
  auto-rotated by the SPIRE agent based on platform attestation. Service-to-service auth
  is then mTLS with SVIDs — no shared secret. Coordinate with **[sota-network-security](../../sota-network-security/SKILL.md)**
  for the mTLS plane.
- **Workload identity federation**: a workload (CI job, cloud function, pod) presents a
  platform-issued OIDC token and exchanges it (RFC 8693 token exchange) for a short-lived
  access token at the IdP/cloud — no stored credential at all. This is the preferred way
  for CI→cloud and service→cloud. The OIDC-federation *mechanics* are
  **[sota-secrets-management** rules/01](../../sota-secrets-management/rules/01-lifecycle-and-workload-identity.md); the *identity design* (one workload identity per
  service, narrowly scoped, attested) is here. Which platform identity each cloud runtime issues
  is [`sota-cloud-infrastructure` rules/02](../../sota-cloud-infrastructure/rules/02-iam-design.md) §2.
- **Short-lived over static, always.** A workload credential should live minutes, be
  scoped to one service's needs, and rotate automatically. A static service-account key
  in a repo/config/env is a defect — push it up the hierarchy to federation or SVIDs.
- **One identity per workload**, scoped least-privilege through the authorization model
  ([rules/03](03-authorization-models.md)). Shared service accounts used by many services destroy attribution and blast-
  radius control. On Kubernetes that means one ServiceAccount per workload, token automount
  off unless it calls the API, and RBAC free of the escalation verbs
  ([`sota-kubernetes` rules/02](../../sota-kubernetes/rules/02-rbac-serviceaccounts.md) §2, §3).
- Workload identities are in the JML/dormancy scope too ([rules/04](04-lifecycle-provisioning.md)): a decommissioned
  service's identity must be retired, and dormant service credentials detected.

```
# BAD: static, long-lived, broadly-scoped machine credential
SVC_API_KEY="sk_live_8f3...permanent"        # in env/config, never rotates, shared

# GOOD: short-lived federated/attested identity
#   pod presents projected SA token -> exchanged for a 15m, single-service token
#   or SPIRE issues an auto-rotating SVID; service-to-service is mTLS with the SVID
```

## Audit checklist

- [ ] Do admins use a separate privileged identity from their daily account, with the privileged account barred from email/browsing? (§1)
- [ ] Do privileged accounts require phishing-resistant MFA and shorter session caps? (§1)
- [ ] Are there shared admin logins (non-break-glass)? Every privileged action should attribute to a named principal. (§1)
- [ ] Is privileged access just-in-time (no standing admin) — requested, approved, reason-logged, auto-expiring? (§2)
- [ ] Is elevation just-enough (narrowest role), with a second approver for the highest tiers? (§2)
- [ ] Do break-glass accounts exist, stay dormant, and fire a loud real-time alert on every use? (§3)
- [ ] Are break-glass uses time-boxed, fully logged, and the credential rotated after use (and split-knowledge if shared)? (§3)
- [ ] For Kanidm: are `admin`/`idm_admin` treated as break-glass only (recovered via `kanidmd recover-account`), with daily admin on separate named accounts? Is `recover-account` use alerted? (§3)
- [ ] Are highest-tier sessions brokered/recorded via a PAM/bastion, with dynamically-issued (not standing) privileged credentials? (§4)
- [ ] Do workloads use short-lived federated/attested identity (SPIFFE/SPIRE SVIDs or workload identity federation) instead of static keys? Hunt config/env for long-lived `*_API_KEY`, `*-key.json`, service-account key files. (§5)
- [ ] Is there one least-privilege identity per workload (no shared service accounts)? (§5)
- [ ] Are decommissioned workload identities retired and dormant service credentials detected (§5) ([rules/04](04-lifecycle-provisioning.md))?
