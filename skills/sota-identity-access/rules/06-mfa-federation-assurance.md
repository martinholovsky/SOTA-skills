# 06 — MFA, Passwordless, Federation Risk & Assurance

Scope: phishing-resistant MFA (FIDO2/passkeys/WebAuthn at the IdP), step-up / adaptive /
conditional access, Continuous Access Evaluation (CAEP / Shared Signals Framework),
push-bombing / MFA-fatigue defenses, B2B/B2C/social-login and account-linking risks, and
identity proofing / assurance levels (NIST SP 800-63-4 IAL/AAL/FAL).

This file owns the **IdP-side authentication strength and federation-risk posture**. The
*WebAuthn ceremony implementation* at one RP (challenge generation, attestation handling,
credential storage) is **sota-code-security** rules/02 — reference it for the wire-level
ceremony; here we own the policy and the assurance model.

## 1. Phishing-resistant MFA at the IdP

- **FIDO2 / WebAuthn / passkeys are the target state.** They are phishing-resistant:
  origin-bound (the credential only works for the registered relying-party origin),
  challenge-response, no shared secret to phish or replay. WebAuthn is at **Level 3**
  (W3C Candidate Recommendation as of early 2026 — current spec level, not yet a finished
  Recommendation).
- **Passkeys** = FIDO credentials, either device-bound (hardware security key, platform
  authenticator) or **synced** multi-device (synced through a provider's keychain). Synced
  passkeys trade some assurance for huge usability/recovery wins — for the highest
  assurance prefer device-bound/hardware authenticators.
- **MFA factor ranking** (use the strongest the population supports):
  1. FIDO2 hardware security key / device-bound passkey (phishing-resistant) — best.
  2. Synced passkey / platform authenticator (phishing-resistant).
  3. App-based push with number-matching (phishable but resists fatigue — §3).
  4. TOTP / authenticator-app codes (phishable via real-time relay).
  5. SMS / voice OTP — **not phishing-resistant** (SIM-swap, interception, relay). Treat
     as a Medium finding where phishing-resistant options are feasible; never the only
     factor for privileged accounts.
- **Require phishing-resistant MFA for all privileged accounts** (rules/05) and drive all
  users toward passkeys. Enroll passkeys at the IdP and let them satisfy MFA across all
  federated RPs via SSO.
- **MFA is the baseline for everyone, not a privileged-account perk.** Require AAL2 (two
  distinct factors) for every employee, contractor and partner account and for any
  application that exposes personal data; reserve single-factor AAL1 for low-risk apps
  that hold none. NIST SP 800-63B-4 sets the same floor for US federal agencies (a minimum
  of AAL2 whenever personal information is made available online). Enforce it at the IdP
  so an RP cannot opt out, and report the accounts still exempt.
- **Two factors means two categories.** Knowledge, possession and inherence must be
  independent — a password plus a security question is one factor twice, and a code sent
  to a mailbox unlocked by the same password is not independent either.
- **No downgrade path.** A user enrolled with a phishing-resistant authenticator must not
  be able to choose SMS, email OTP or a password-only path at sign-in ("try another
  way") or in recovery; the weakest reachable method is the real assurance level.
  Recovery re-binds a strong authenticator through a process at least as strong
  (sota-code-security rules/02 §5). OWASP: Multifactor Authentication cheat sheet;
  Proactive Controls 2024 C7; Zero Trust Architecture cheat sheet.

## 2. Step-up, adaptive & conditional access

- **Step-up authentication**: low-risk actions ride the existing session; sensitive
  actions (change MFA, move money, export data, admin operations) demand a *fresh*
  strong authentication. Express the requirement as an assurance level (AAL) or ACR the
  RP requests and the IdP enforces (`acr_values` / `max_age` in the OIDC request).
- **Adaptive / conditional access**: gate authentication on context — device posture,
  network/location, impossible-travel, risk score. High risk → step-up or block; low risk
  → allow. Feed the risk signals from and to **sota-detection-engineering** (auth anomaly,
  impossible-travel detections).
- **A risk signal the client can set is not a signal.** Take the source IP from the
  connection or from a proxy header only when the peer is a known proxy
  (sota-network-security rules/05 R6) — a raw `X-Forwarded-For` lets an attacker claim a
  trusted network and skip step-up. Device posture must come from attested or managed-device
  evidence, not a user-agent string or a client-sent flag. OWASP: Multifactor
  Authentication cheat sheet.
- Conditional access is policy-as-code too: version it, test it, and fail closed (an
  unevaluated condition denies or steps up, never silently allows).

## 3. Push-bombing / MFA-fatigue defenses

The attacker has the password and spams push prompts until the user taps "approve":

- **Number matching** — the user types a number shown on the login screen into the app,
  so a blind "approve" cannot succeed.
- **Rate-limit and lock out** repeated push prompts; alert on push storms.
- **Show context** in the prompt (app, location, IP) so the user can spot the anomaly.
- The real fix is **phishing-resistant MFA** (§1), which has no "approve" to spam.

## 4. B2B / B2C / social-login & account-linking risk

- **Social / external login** delegates authentication to an upstream IdP. Validate its
  tokens fully (rules/01 §3), pin the issuer, and **only trust verified claims** (e.g.
  `email_verified=true`) — never link on an unverified email.
- **Account-linking attacks**: linking a federated identity to a local account on a
  *mutable* or *unverified* attribute lets an attacker pre-register or collide and take
  over. Link deterministically on a **verified, immutable** identifier (provider `sub` +
  verified email); require re-verification to link a second IdP to an existing account.
- **B2B federation**: each partner/tenant trust is a boundary (rules/02 §8). Re-map their
  group/role claims through your own authorization model (rules/03) — a partner IdP must
  not be able to assert your privileged roles.

## 5. Continuous Access Evaluation (CAEP / Shared Signals Framework)

Bearer tokens are valid until they expire, so a revocation/disable does not take effect
until the token times out — the gap that lets a just-fired employee keep working for the
token lifetime. CAEP/SSF closes it:

- **Shared Signals Framework (SSF) 1.0** is **final (29 August 2025)** at the OpenID
  Foundation — a transport framework for asynchronously delivering Security Event Tokens
  (SETs) between an IdP and RPs/receivers.
- **CAEP 1.0** is **final (29 August 2025)** — defines the event types carried over SSF,
  including **session-revoked, credential-change, assurance-level-change** (plus
  token-claims-change, device-compliance-change, session-established/presented,
  risk-level-change).
- Use it so that disabling an account, a credential change, or a risk-level rise **pushes
  a revocation event** to relying parties in near-real-time instead of waiting for token
  expiry. This is the propagation mechanism behind the leaver SLA (rules/04) and Single
  Logout (rules/02 §6). **RISC** is the parallel SSF profile for account-takeover/fraud
  signals.

## 6. Identity proofing & assurance levels (NIST SP 800-63-4)

**NIST SP 800-63-4 "Digital Identity Guidelines" is final (July 2025)**, superseding
Rev 3, across three volumes: 800-63A-4 (proofing), 800-63B-4 (authentication), 800-63C-4
(federation). The assurance model:

- **IAL — Identity Assurance Level**: confidence that the person is who they claim
  (identity proofing). IAL1→IAL2→IAL3 rising rigor.
- **AAL — Authenticator Assurance Level**: confidence in the authentication
  (authenticator strength + binding). AAL2 needs MFA; **AAL3 requires a hardware-based,
  phishing-resistant authenticator**.
- **FAL — Federation Assurance Level**: strength of the federated assertion (signing,
  encryption, holder-of-key binding). FAL rises with assertion protection.

Match the assurance level to the risk of the resource (don't demand IAL3 in-person
proofing to read a blog; do demand AAL3 for production infra). What 800-63-4 changed vs
Rev 3, reflect these:
- **Syncable authenticators (passkeys) are explicitly recognized** as an authenticator
  type.
- **No periodic password rotation** and no arbitrary composition rules — rotate passwords
  only on evidence of compromise (the app-side storage of those passwords is
  **sota-code-security** rules/02).
- Stronger emphasis on **phishing-resistant authenticators** for higher AAL / high-risk.

## Audit checklist

- [ ] Is phishing-resistant MFA (FIDO2/passkey) available at the IdP and **required for all privileged accounts**?
- [ ] Is SMS/voice OTP relied on as a sole or primary factor anywhere it could be phishing-resistant instead?
- [ ] Are users actively driven toward passkeys, with enrollment at the IdP satisfying MFA across federated RPs?
- [ ] Do sensitive operations require step-up (fresh strong auth via `acr_values`/`max_age`), not just an existing session?
- [ ] Is conditional/adaptive access policy versioned, tested, and fail-closed?
- [ ] Are push-MFA prompts protected with number-matching, rate limiting, context display, and storm alerting?
- [ ] Does social/external login trust only verified immutable claims, with the upstream issuer pinned and tokens fully validated?
- [ ] Is account linking done on a verified immutable id, with re-verification to add a second IdP (no linking on mutable/unverified email)?
- [ ] Are B2B partner group/role claims re-mapped through the local authorization model, never trusted to grant privileged roles?
- [ ] Is CAEP/SSF (or an equivalent) wired so disable/credential-change/risk events propagate revocation to RPs in near-real-time, not at token expiry?
- [ ] Are IAL/AAL/FAL levels chosen to match resource risk, with AAL3 (hardware phishing-resistant) for the highest-risk access?
- [ ] Is password policy 800-63-4-aligned (no forced periodic rotation, no composition rules; rotate on compromise only)?
- [ ] **High** — Is MFA (AAL2) required for every workforce, contractor and partner account and for every app that exposes personal data, with AAL1 limited to low-risk apps holding none? MFA switched off or optional in policy-as-code: `grep -rniE '(require[sd]?_?mfa|mfa_?(required|enforce[a-z]*)|mfa)["'\'']?[[:space:]]*[:=][[:space:]]*["'\'']?(false|optional|off|disabled|none|no)' .`
- [ ] **High** — Do the factors come from different categories, is there no sign-in or recovery fallback from a phishing-resistant authenticator to a weaker method, and are adaptive-access signals taken from sources the client cannot set? Fallbacks to weaker methods: `grep -rniE 'fallback[A-Za-z_]*["'\'']?[[:space:]]*[:=].*(sms|voice|email|otp|password|question)' .`
