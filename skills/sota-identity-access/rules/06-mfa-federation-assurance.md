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
  challenge-response, no shared secret to phish or replay. WebAuthn **Level 3** became a
  **W3C Recommendation on 25 August 2026** (w3.org/TR/webauthn-3).
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
- **If SMS or voice OTP stays, run it as an accepted risk.** NIST SP 800-63B-4 classes
  PSTN delivery as its one *restricted* authenticator (Sec. 3.2.9). Accepting it obliges
  you to offer an unrestricted alternative at the same AAL, tell users the risk, and keep
  a written migration plan to TOTP or WebAuthn. Record that acceptance with an owner and
  a review date. Before sending a code, check SIM-swap, number-port and device-change
  signals where the carrier or an aggregator exposes them (Sec. 3.1.3.3). Changing the
  registered number is binding a new authenticator, under the same checks as
  enrolment. Where you can, do not deliver the code to the device running the session,
  and let the user choose SMS or voice. For high-risk populations (banking, admin
  recovery), register the number in person or through an already-verified channel.
  Generate and check codes in a separate verifier service that stores the secrets and
  answers only accept or reject. The web tier then never holds a code it could log or
  leak. OWASP: Multifactor Authentication cheat sheet; Code Review Guide v2.
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
- **Name the risk triggers.** At minimum, raise risk for: a source on an anonymiser, Tor
  exit or threat-intel denylist; one IP or ASN trying many accounts, with few attempts
  each (credential stuffing, **sota-detection-engineering**); traffic with an automation
  fingerprint (headless client, no JS execution, request timing no person produces); a
  new device or country for this user; impossible travel. OWASP: Credential Stuffing
  Prevention, Authentication cheat sheets.
- **Write the risk model down.** Document every attribute the decision reads (IP,
  geolocation, device, time, behaviour), where it comes from, how often it is refreshed
  during a live session, the thresholds, and the action each risk tier maps to (allow,
  challenge, step up, deny, revoke). An undocumented threshold cannot be reviewed,
  tested, or explained to the user it blocks. OWASP: ASVS 5.0 V8.1.3, V8.1.4.
- **A trusted IP range is only as narrow as its narrowest use.** When a corporate range
  or allowlist counts as a factor or skips step-up, make sure it covers only managed
  egress. Guest Wi-Fi, shared VPN pools and cloud NAT often leave through the same
  addresses. It never replaces a second factor for privileged access.
- **Respond with more than allow or block.** Graduated responses keep work moving while
  capping the damage: a constrained session (short lifetime, read-only, no export),
  more detailed logging for that session, re-verification before bulk or destructive
  actions, and for an unusual but plausible access pattern a JIT grant gated on the
  resource owner's approval, time-boxed (rules/05 §2) with a summary to the security
  team. OWASP: Zero Trust Architecture, Multifactor Authentication cheat sheets.

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

**Wallet-held credentials (SD-JWT, RFC 9901, Nov 2025).** When users present a verifiable
credential from a wallet instead of signing in at an IdP, the verifier plays the RP's role
and owns the same checks (RFC 9901 Sec. 7.1, 7.3): reject `alg: none` and pin algorithms, verify
the issuer signature with a key that belongs to *that* issuer, accept only a known and secure
`_sd_alg`, and reject malformed disclosures, a digest seen twice, and any disclosure no
digest references. **Decide per use case whether
Key Binding is required *before* looking at the presentation** — never infer it from
whether the holder sent a KB-JWT (Sec. 9.5). When it is required, check the KB-JWT's `typ`
`kb+jwt`, holder-key signature, a short `iat` window, `nonce` and `aud` for this
transaction and this verifier, and `sd_hash`. Without Key Binding, a leaked credential can
be replayed by anyone. Revocation of such credentials is the Token Status List (rules/02 §4).

Match the assurance level to the risk of the resource (don't demand IAL3 in-person
proofing to read a blog; do demand AAL3 for production infra). What 800-63-4 changed vs
Rev 3, reflect these:
- **Syncable authenticators (passkeys) are explicitly recognized** as an authenticator
  type.
- **No periodic password rotation** and no arbitrary composition rules — rotate passwords
  only on evidence of compromise (the app-side storage of those passwords is
  **sota-code-security** rules/02).
- Stronger emphasis on **phishing-resistant authenticators** for higher AAL / high-risk.

**Authenticator lifecycle** — binding is one event of several, and the others are where
assurance leaks (800-63B-4's lifecycle section: loss, theft, expiration, invalidation):
- **Any factor can be revoked, by the user and by an admin.** A user must be able to
  report a lost or stolen key, phone or passkey provider and have it invalidated at once,
  authenticating with another bound factor to do so. An admin or help desk must be able
  to do the same on the user's behalf. NIST requires the CSP to invalidate promptly on
  notice of loss, theft or compromise, and it treats a lost authenticator as a stolen
  one. Revoking the factor also ends the sessions and tokens it established (rules/02 §6).
- **Replacing a lost factor re-proves identity at the level of enrolment.** If the
  account was proofed at IAL2, the replacement goes through the IAL2 checks again (or a
  retained-evidence re-verification), not an email link. Otherwise the recovery desk is
  the cheapest path to the account. The recovery mechanics are **sota-code-security**
  rules/02 §5.
- **Authenticators that expire get renewed before they do.** For certificates, smart
  cards, hardware tokens with a validity date, and time-limited enrolments, send renewal
  instructions early enough that the user can finish renewing before the old one
  lapses, with automated reminders. An expired authenticator must not authenticate, and
  the failure should say it expired. Binding the replacement follows the
  add-an-authenticator process.
- **Biometrics are never a factor on their own.** A biometric match only unlocks a
  possession factor (a device-bound key, a smart card) or pairs with a knowledge factor.
  800-63B-4 allows biometrics only as part of MFA with a physical authenticator,
  requires a non-biometric alternative, and rules out voice comparison entirely. An IdP
  policy that accepts "face ID" as the whole login is a finding. OWASP: ASVS 5.0 V6.4.4,
  V6.4.5, V6.5.6, V6.5.7.

## 7. Certificate-based authentication of users and devices

- **Where client certificates fit.** Use TLS client certificates (or a smart card) for
  users in a managed estate, where IT enrols the certificate on a known device, and for
  intranet or admin surfaces. Avoid them for a broad public audience, where installation
  and recovery fail. The certificate is phishing-resistant, but it is only as strong as
  its key storage. Put the key in hardware (TPM, secure enclave, smart card), mark it
  non-exportable, and bind each certificate to exactly one account. Pair it with a
  second factor wherever the device is not itself strongly protected.
- **Issue and revoke like a PKI, because it is one.** Run a dedicated issuing CA whose
  trust is scoped to client authentication at your endpoints. Enrol over an
  authenticated channel, with the key generated on the device, never emailed as a
  `.p12`. Keep lifetimes short with automated renewal (§6 lifecycle). The verifier checks
  revocation (OCSP or a fresh CRL) and maps the certificate to the account with a strong
  identifier, not a spoofable name field (rules/07 §3 for the AD equivalent, KB5014754).
  Leavers and lost devices revoke immediately (rules/04).
- **TLS-inspecting proxies break it.** A proxy that terminates TLS cannot present the
  client's certificate to the server, because it does not hold the private key that
  signs the handshake (TLS 1.3 CertificateVerify, RFC 8446 Sec. 4.4.3). So client-cert sign-in fails behind a decrypting corporate proxy
  unless the site is exempted from inspection. Plan that exemption. Never "fix" it by
  having the proxy forward the certificate in a header the backend trusts from anyone
  (rules/01 §5.1: take the certificate from the connection).
- **Edge and IoT devices authenticate as devices.** Each device carries its own
  identity, ideally a key in a secure element or TPM with a per-device certificate
  issued at manufacture or first enrolment. It authenticates to central infrastructure
  with mTLS or a signed-assertion grant, never a fleet-wide shared API key or password.
  Revoke a device individually when it is lost or decommissioned, and scope what one
  device identity may reach so a cloned device cannot speak for the fleet. The workload
  side is rules/05 §5; transport is **sota-network-security**. OWASP: Authentication,
  Multifactor Authentication cheat sheets; Code Review Guide v2; AISVS 4.3.1.

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
- [ ] **High** — Where wallet credentials (SD-JWT) are accepted, does the verifier pin algorithms and `_sd_alg`, check the issuer key, reject malformed, duplicate-digest or unreferenced disclosures, fix Key Binding per use case in advance (never from whether a KB-JWT arrived), and check `kb+jwt`, `iat`, `nonce`, `aud` and `sd_hash`?
- [ ] **High** — Is MFA (AAL2) required for every workforce, contractor and partner account and for every app that exposes personal data, with AAL1 limited to low-risk apps holding none? MFA switched off or optional in policy-as-code: `grep -rniE '(require[sd]?_?mfa|mfa_?(required|enforce[a-z]*)|mfa)["'\'']?[[:space:]]*[:=][[:space:]]*["'\'']?(false|optional|off|disabled|none|no)' .`
- [ ] **High** — Do the factors come from different categories, is there no sign-in or recovery fallback from a phishing-resistant authenticator to a weaker method, and are adaptive-access signals taken from sources the client cannot set? Fallbacks to weaker methods: `grep -rniE 'fallback[A-Za-z_]*["'\'']?[[:space:]]*[:=].*(sms|voice|email|otp|password|question)' .`
- [ ] **Medium** — Where SMS/voice OTP is enabled, is there a recorded risk acceptance with an owner, an unrestricted alternative, a migration plan, SIM-swap/number-port checks, number changes treated as new bindings, and code generation isolated in a verifier service? SMS or voice factors switched on (each hit needs that record): `grep -rniE '(sms|voice|phone)_?(otp|mfa|factor|authenticator|2fa)[a-z_]*["'\'']?[[:space:]]*[:=][[:space:]]*["'\'']?(true|on|yes|enabled|allowed)' .`
- [ ] **High** — Are adaptive-access triggers named (anonymiser/denylisted IPs, one source against many accounts, automation), the attributes, refresh cadence, thresholds and actions documented, trusted IP ranges limited to managed egress, and graduated responses (constrained session, extra logging, re-verification, approval-gated JIT) available? Trusted or MFA-skipping ranges wider than a /16: `grep -rniE '(trusted|allow(ed)?|skip_?mfa|bypass_?mfa|mfa_?exempt)_?(ips?|ip_?ranges?|networks?|cidrs?|locations?)["'\'']?[[:space:]]*[:=].*(0\.0\.0\.0/0|::/0|/[0-9]([^0-9]|$)|/1[0-5]([^0-9]|$))' .`
- [ ] **High** — Can the user and an admin revoke any lost or stolen factor at once (ending its sessions), does replacing a lost factor re-proof at the enrolment IAL, do expiring authenticators get automated renewal reminders, and are biometrics accepted only to unlock a possession factor or alongside a knowledge one? Biometrics configured as a whole factor: `grep -rniE '(biometric|face_?id|touch_?id|fingerprint)[a-z_]*_?(only|sole|single_?factor|as_?mfa|satisfies_?mfa|as_?second_?factor)["'\'']?[[:space:]]*[:=][[:space:]]*["'\'']?(true|on|yes|enabled)' .`
- [ ] **High** — Are client certificates used only in managed estates, with hardware-held non-exportable keys, a dedicated client-auth CA, revocation checking and strong account mapping, and do edge/IoT devices each authenticate with their own identity (no fleet-wide shared key)? A certificate taken from a request header rather than the TLS connection (confirm the proxy strips inbound copies): `grep -rniE 'x-(ssl-)?client-cert|ssl[_-]client[_-]cert|x-forwarded-client-cert|x-client-certificate' .`
