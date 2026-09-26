# 02 — IdP Operations

Scope: running and configuring an Identity Provider as production infrastructure —
client/relying-party registration discipline, the client-authentication ladder, token
lifetimes and refresh-token rotation with reuse detection, signing-key (`kid`) rotation,
session management and Single Logout, consent, multi-IdP brokering, and treating the IdP
as a **tier-0 asset** (HA, backup, restricted admin plane).

Applies to self-hosted IdPs — **Kanidm** (Rust, OIDC/OAuth2, WebAuthn), **Keycloak**
(CNCF Incubating, OIDC/SAML), **Authentik** (goauthentik.io, OIDC/SAML/SCIM),
**Zitadel** (Go, OIDC/SAML, multi-tenant) — and the same principles map to **Entra ID**
and **Okta**. Protocol-level token rules are rules/01; this file is operations.

## 1. The IdP is tier-0

Everything that authenticates to anything depends on the IdP. Treat it like the root CA
of your access:

- **Availability**: run HA (≥2 nodes / managed multi-AZ). An IdP outage is a total
  authentication outage. Have a documented degraded-mode (cached sessions, longer token
  lifetimes during incident) and a tested failover.
- **Backup of the identity store**: the user/group/credential database and the signing
  keys are crown jewels. Back them up encrypted, test restore, and store key material
  per **sota-secrets-management**. For Kanidm, back up the database and the
  server's key material; for Keycloak/Zitadel/Authentik, back up the backing Postgres
  *and* the realm/instance config and signing keys.
- **Admin-plane isolation**: the IdP admin console is not a normal app. Restrict it by
  network (admin VPN / identity-aware proxy — **sota-network-security**), require
  phishing-resistant MFA, separate admin accounts (rules/05), and audit-log every admin
  mutation immutably.
- **Patch cadence**: an IdP CVE is critical-by-default. Track the vendor's advisories;
  the federation libraries (SAML, JWT) are exactly where signature-bypass bugs land.
- **Keep the workforce trust domain away from the internet-facing one.** Do not let the
  internal directory or workforce IdP authenticate public, customer or DMZ-hosted apps.
  Give those their own IdP, realm or tenant with no trust path back. Otherwise an
  exposed login form becomes a password-spraying and bind oracle against employee
  accounts, and a compromised DMZ host holds credentials that open the inside. OWASP:
  Authentication cheat sheet.
- **A hosted IdP or MFA service is a tier-0 supplier.** One provider sits in the login
  path of all its customers, so a breach there can bypass MFA for every tenant at once.
  Assess it like your own tier-0: its attestations (SOC 2 / ISO 27001 evidence, see
  **sota-privacy-compliance**), its support staff's access to your tenant, its breach
  notification terms, and your fallback. The break-glass path (rules/05 §3) must not
  depend on it, and you must be able to re-key or cut its federation trust quickly.
  OWASP: Multifactor Authentication, Authentication cheat sheets.

## 2. Client / relying-party registration discipline

Each application is a distinct client with the narrowest config that works:

- **One client per app**, never shared. Exact redirect URIs only (rules/01 §4).
- **Scopes/claims minimal**: grant only the scopes the app needs; do not enable the
  `groups`/`profile`/`email` claims for a client that does not consume them.
- **Public vs confidential**: SPAs and native apps are public clients (no secret) and
  MUST use PKCE; server-side apps are confidential and authenticate per the ladder below.
- **Disable unused grant/response types** per client (no implicit, no ROPC).
- **Dynamic Client Registration** (RFC 7591), if enabled, must be authenticated and
  policy-gated — open DCR lets anyone mint a client. RFC 7591 Sec. 5 says the AS MUST
  treat every metadata value as self-asserted unless a software statement vouches for
  it. So validate on registration: redirect URIs under rules/01 §4, and `logo_uri`,
  `client_uri`, `policy_uri` and `tos_uri` on the same host as the redirect URIs (the
  RFC's SHOULD). Every URL the AS fetches (`jwks_uri`, `logo_uri`, `sector_identifier_uri`)
  is attacker input and goes through the SSRF rules (**sota-code-security** rules/01 §5).
  Mark such clients untrusted: always show consent (§7) with a warning that the app is
  unverified.
- **Client ID Metadata Documents** (`draft-ietf-oauth-client-id-metadata-document`, an
  Internet-Draft as of 2026-09-26; the MCP authorization spec's SHOULD path, rules/01 §5.1)
  replace registration with a URL: the `client_id` is an HTTPS URL the AS fetches. That
  fetch is the AS making an outbound request to an attacker-chosen URL, so the draft's
  rules apply: MUST NOT fetch the document, or any URL inside it, when it resolves to a
  special-use IP (RFC 6890 — no loopback exception in production); MUST NOT follow
  redirects; accept only `200`; cap the bytes read (5 KB recommended); never cache errors
  or invalid documents; require the document's `client_id` to equal the fetched URL by
  simple string comparison. Everything in it is self-asserted, as with DCR above.
- **A client must not be able to pose as a user.** Where client ids and user subjects
  share a namespace (a client-credentials token's `sub` is the client id, RFC 9068), the
  AS SHOULD NOT let a client choose its `client_id` or any claim that could equal a real
  user's `sub` (RFC 9700 Sec. 4.15.1). Generate client ids, or give the RS another way to
  tell the two token kinds apart (rules/01 §5.1).
- **Allow only the `response_mode` each client needs.** Pin it per client (for example
  `query` or `form_post` for a code flow), or carry it inside PAR/JAR so it cannot be
  rewritten. An open choice lets an attacker pick a delivery mode the client never
  secured, such as a fragment that scripts on the callback page can read.
- **The client asks for what it uses.** Each client requests only the scopes and
  authorization parameters its current feature needs, not the whole set it is allowed.
  The AS-side cap above bounds the damage; the client-side request keeps the token small
  and the consent screen honest. OWASP: ASVS 5.0 V10.2.3, V10.4.7, V10.4.12; OAuth2 cheat
  sheet.

```
# Kanidm — register an OIDC RP with an exact redirect; group→scope mapping in rules/03
kanidm system oauth2 create web-app "Web App" https://app.example.com
kanidm system oauth2 add-redirect-url web-app https://app.example.com/auth/callback
kanidm system oauth2 update-scope-map web-app app_users openid email groups
```

## 3. Client-authentication ladder (weakest → strongest)

Pick the strongest the platform supports:

1. `client_secret_basic` / `client_secret_post` — a shared secret in the request. Lowest
   tier; the secret is a long-lived bearer credential that leaks. Acceptable only for
   low-risk confidential clients with the secret in a secret manager and rotated.
2. `client_secret_jwt` — HMAC-signed assertion; still a shared symmetric secret.
3. **`private_key_jwt`** — the client signs an assertion with its *private* key; the IdP
   verifies with the public key. No shared secret to leak. Preferred for confidential
   clients.
4. **`tls_client_auth` / mTLS (RFC 8705)** — client authenticates with a TLS client cert,
   enabling certificate-bound tokens. Strongest where a PKI exists.

Treat `client_secret_basic` as a finding when the client could use `private_key_jwt` or
mTLS. Never embed a client secret in a public client (SPA/mobile) — there is no secret a
public client can keep.

## 4. Token lifetimes, refresh rotation, reuse detection

- **Access tokens short-lived** (minutes, single-digit to ~15). The shorter the lifetime,
  the smaller the stolen-token window and the less you depend on revocation.
- **Refresh tokens rotate**: each use issues a new refresh token and invalidates the
  prior one. Combined with **reuse detection** — if a previously-used (rotated-out)
  refresh token is presented, treat it as theft, revoke the whole token family, and force
  re-auth. This is the RFC 9700 baseline for public clients (rotate **or**
  sender-constrain).
- **Sender-constrain** refresh/access tokens with DPoP (RFC 9449) or mTLS (RFC 8705) for
  high value (rules/01 §5) so a stolen token is unusable.
- **No non-expiring tokens.** "Offline" refresh tokens still get an absolute max lifetime
  and idle expiry; long-lived non-rotating refresh tokens are a High finding.
- **Revocation** (RFC 7009) endpoint available and used on logout/credential-change;
  pair with introspection (RFC 7662) for opaque tokens.
- **Revoking a self-contained token before `exp`.** A short lifetime stays the primary
  control. When a JWT (or another signed credential) must be revocable anyway, the IETF
  Token Status List (`draft-ietf-oauth-status-list` — IESG-approved and in the RFC Editor
  queue, not yet an RFC, as of 2026-09-26; check datatracker.ietf.org for its RFC number)
  gives the issuer a standard design. The
  token carries `status.status_list` with an `idx` and a `uri`; the verifier fetches the
  signed Status List Token from that URI, caches it for the list's `ttl`, and reads the bit
  at `idx`. The URI is attacker-influenced input, so allowlist it (**sota-code-security**
  rules/17 covers the verifier side).
- **Check online for the critical calls.** A cached status list or a local signature check
  cannot see a revocation newer than the cache. Validate online (introspection, or a fresh
  status fetch) for payments, admin actions, privilege and credential changes. Keep
  offline validation for low-risk reads, where a few minutes of staleness is acceptable.
  OWASP: Microservices Security cheat sheet.
- **A revoked token presented again is an incident signal.** Log every use of a revoked
  access token, refresh token or session at critical severity, with the token id and
  subject, and alert on it. Rotated-refresh reuse is only one case: a revoked access
  token turning up after logout or a password change means someone kept a copy. OWASP:
  Logging Vocabulary cheat sheet (`authn_token_reuse`, level CRITICAL); JSON Web Token
  cheat sheet.
- **Authorization codes are one-shot and short-lived.** Expire them within minutes — RFC
  6749 Sec. 4.1.2 recommends a maximum of 10, and a minute is usually enough. Mark a code
  redeemed atomically at the token endpoint (a check-then-mark race lets two concurrent
  redemptions both succeed). A second redemption MUST fail, and the AS SHOULD revoke every
  token already issued from that code: a replayed code means it leaked, and the first
  redeemer may have been the attacker. Test both halves; many custom ASs do the first and
  not the second. OWASP: ASVS 5.0 V10.4.2, V10.4.3.

```
# GOOD (IdP token policy)
access_token_lifetime   = 10m
refresh_token_rotation  = true
refresh_reuse_detection = true       # revoke family on reused token
refresh_absolute_max    = 30d
# BAD
access_token_lifetime   = 24h
refresh_token_rotation  = false
refresh_token_lifetime  = "never"
```

## 5. Signing-key rotation (`kid`)

- The IdP's token-signing keys rotate on a schedule (e.g. quarterly) and immediately on
  suspected compromise. Each key has a `kid`; publish current + previous in the JWKS so
  in-flight tokens verify during the overlap, then retire the old `kid`.
- Prefer asymmetric signing (ES256 as the portable default, RS256, or Ed25519 where supported — RFC 9864 deprecates the JOSE `EdDSA` identifier) so RPs verify with public keys and the
  private key never leaves the IdP. Avoid symmetric (`HS256`) signing across trust
  boundaries.
- This is the IdP-operations side; the credential-rotation mechanics
  (overlap windows, JWKS publication) are also in **sota-secrets-management** rules/05.
- Audit: a signing key that has never rotated, or a JWKS that publishes only one key with
  no rotation history, is a finding (no clean path to recover from key compromise).

## 6. Session management & Single Logout

- **Idle + absolute session timeouts** at the IdP SSO session level: idle (re-auth after
  inactivity) and absolute (hard cap regardless of activity). Privileged sessions get
  shorter caps.
- **Session fixation**: the IdP must issue a fresh session identifier on successful
  authentication and not accept a pre-login session id. (The app-side cookie handling for
  this is **sota-code-security** rules/17.)
- **Single Logout (SLO) / back-channel logout**: SSO means one credential opens many RPs;
  logout or credential-change must propagate. Configure **back-channel logout** (OIDC
  Back-Channel Logout: the IdP POSTs a logout token to each RP) so a sign-out or
  forced revocation actually ends sessions everywhere. Front-channel-only logout is
  unreliable (depends on browser). SAML SLO has the same goal and the same fragility.
- On credential change / account disable, *kill live sessions* — pair with CAEP/SSF
  (rules/06) for near-real-time propagation rather than waiting for token expiry.
- **The RP validates every logout token before it acts on one.** A back-channel endpoint
  that ends sessions on any well-formed POST lets anyone log users out, and one that
  accepts an ID token here has confused two JWT kinds. OIDC Back-Channel Logout 1.0
  requires validating the signature, `iss`, `aud`, `iat` and `exp` (both REQUIRED claims),
  a `sub` or `sid`, an `events` object holding the member
  `http://schemas.openid.net/event/backchannel-logout`, and the absence of `nonce`.
  Also pin `typ` = `logout+jwt` (rules/01 §2), refuse a long `exp` (the spec encourages at
  most two minutes ahead), and optionally drop a repeated `jti`.
- **The OP must not log a user out just because a link says so.** OIDC RP-Initiated
  Logout 1.0: when the request has no `id_token_hint`, or the hint does not match the
  current session, the OP MUST ask the user before logging them out. Otherwise a crafted
  link or image is a forced-logout DoS. Validate `post_logout_redirect_uri` against the
  registered set, as with redirect URIs.
- **Keep an inventory of every session in the SSO chain.** List each component that
  creates or holds a session: the upstream IdP, the broker, the IdP SSO session, every
  RP's local session, any BFF or gateway. For each one record its idle and absolute
  lifetime, what ends it (logout, disable, credential change, risk event), and how that
  end reaches the others. A component missing from the list is the one whose session
  survives logout. OWASP: ASVS 5.0 V7.1.3, V10.5.5, V10.6.2.

## 7. Consent

- For first-party apps, consent may be implicit/skipped. For **third-party** clients,
  show an informative consent screen: which client, which scopes, what data, revocable.
- Consent is auditable and revocable by the user and by an admin; revoking consent
  revokes the associated tokens. For privacy/regulatory consent (purpose, retention) see
  **sota-privacy-compliance**.
- Beware "consent phishing": a malicious OAuth app requesting broad scopes. Gate which
  clients may request sensitive scopes; admin-approve high-scope third-party apps.
- **No silent consent for a client you cannot authenticate.** Skipping the prompt is only
  safe for a confidential first-party client. For a public client, a dynamically
  registered one, or any client whose identity rests on a redirect URI alone, prompt the
  user every time. An impersonator can reuse the real client's `client_id`, and RFC 6749
  Sec. 10.2 says the AS SHOULD NOT process repeat requests automatically without
  authenticating the client or otherwise making sure it is the original. OWASP: ASVS 5.0
  V10.7.1.
- **SaaS you adopt is an identity estate too.** For every SaaS tenant: name its admins
  (few, each on a separate admin identity, rules/05 §1). Inventory the connected apps
  and integrations allowed to read or share its data, with the scope and owner of each.
  Review that list on the access-review cadence (rules/04 §4). Treat tenant
  customisations (scripts, webhooks, custom apps, workflow rules that call out) as code:
  they get a security review and an owner before they run. OWASP: Secure Cloud
  Architecture cheat sheet.

## 8. Multi-IdP & brokering

- An **identity broker** (Keycloak/Authentik/Zitadel brokering an upstream IdP, or
  Kanidm fronting OIDC) federates multiple sources. Each upstream trust is a security
  boundary: validate upstream tokens fully (rules/01 §3), pin the upstream issuer, and
  **map external identities to internal accounts deterministically** — link on a verified
  immutable identifier (verified email + `sub`), never on a mutable display field, to
  avoid account-takeover via attribute collision (account-linking attacks, rules/06).
- Do not blindly trust upstream group/role claims — re-map them through your own
  authorization model (rules/03); an upstream that can assert arbitrary groups must not be
  able to grant your privileged roles.
- **Disabled must mean disabled — test it.** After disabling an upstream IdP, broker
  link, or client, verify its authentication path actually fails closed. Keycloak
  CVE-2026-3047 (CVSS 8.8) and CVE-2026-2603 (both fixed in 26.5.5, March 2026) let a
  *disabled* SAML client or upstream SAML IdP still complete IdP-initiated broker
  logins — a retired or compromised upstream an admin thought was off kept
  authenticating users into the realm. Patch, and restrict or disable IdP-initiated
  broker endpoints you do not use.

## Audit checklist

- [ ] Is the IdP run HA with a tested failover and a documented degraded-mode?
- [ ] Is the identity store (and signing-key material) backed up encrypted, with restore tested?
- [ ] Is the admin console network-restricted, MFA-gated with separate admin accounts, and immutably audit-logged?
- [ ] Is there one client per app with exact redirect URIs and minimal scopes (no shared clients, no unused claims)?
- [ ] Is Dynamic Client Registration disabled or authenticated+policy-gated?
- [ ] Does each confidential client use `private_key_jwt` or mTLS rather than `client_secret_basic` where supported? Grep config for `client_secret_basic`/`token_endpoint_auth_method`.
- [ ] Are no client secrets embedded in public (SPA/mobile) clients?
- [ ] Are access tokens short-lived (≤~15m)?
- [ ] Is refresh-token rotation enabled with reuse detection (family revocation), or are tokens sender-constrained (DPoP/mTLS)?
- [ ] Are there any non-expiring / never-rotating refresh tokens? (High finding)
- [ ] Do signing keys rotate on a schedule with `kid` overlap in the JWKS, using asymmetric algorithms?
- [ ] Are idle and absolute SSO session timeouts set, with shorter caps for privileged sessions?
- [ ] Is back-channel (or reliable) Single Logout configured so sign-out / disable ends sessions across all RPs?
- [ ] Do third-party clients show informative, revocable consent, with high-scope apps admin-gated?
- [ ] For brokered/upstream IdPs: is the issuer pinned, tokens fully validated, identities linked on a verified immutable id, and upstream group claims re-mapped (not trusted) into the local model?
- [ ] When an upstream IdP, broker link, or client is disabled, is it tested that its login path fails closed (Keycloak CVE-2026-3047 / CVE-2026-2603 class), with unused IdP-initiated broker endpoints restricted?
- [ ] **High** — Is an authorization code single-use, expiring within minutes (RFC 6749 recommends at most 10), with a second redemption refused and the tokens already issued from it revoked? Code lifetimes over 10 minutes: `grep -rniE '(auth(orization)?_?)?code_?(lifetime|lifespan|ttl|expir[a-z]*)["'\'']?[[:space:]]*[:=][[:space:]]*["'\'']?([0-9]+[[:space:]]*[hd]|(1[1-9]|[2-9][0-9]|[0-9]{3,})[[:space:]]*m|(60[1-9]|6[1-9][0-9]|[7-9][0-9]{2}|[0-9]{4,})[[:space:]]*s?["'\'']?[[:space:]]*$)' .`
- [ ] **High** — Is the workforce directory/IdP kept out of the authentication path of public and DMZ apps, and is any hosted IdP or MFA provider assessed as a tier-0 supplier, with a break-glass path that does not depend on it?
- [ ] **High** — Does Dynamic Client Registration treat metadata as self-asserted (redirect and `*_uri` host checks, SSRF rules on fetched URLs, unverified-app consent), refuse client-chosen ids that can equal a user `sub`, and pin each client's `response_mode`? Anonymous registration or a wide-open `response_mode`: `grep -rniE '(anonymous|unauthenticated|open)_?(client_?)?registration["'\'']?[[:space:]]*[:=][[:space:]]*["'\'']?(true|on|yes|enabled)|response_modes?["'\'']?[[:space:]]*[:=].*(fragment|["'\''][*]["'\'']|any)' .`
- [ ] **Medium** — Is consent always prompted for public, dynamically registered or otherwise unauthenticated clients, and does each client request only the scopes the feature uses?
- [ ] **High** — Can a signed token be revoked before `exp` where the risk needs it (Token Status List or introspection), are critical operations validated online, and is every use of a revoked token logged at critical severity and alerted? Revocation checks that never log: `grep -rlE '[Ii]s_?[Rr]evoked|[Rr]evoked[A-Za-z_]*\(|deny_?list|status_list' . | xargs -r grep -LE '(log|logger|logging|LOG|Log)\.[A-Za-z]+\(|audit|security_event'`
- [ ] **High** — Does every back-channel logout endpoint validate the logout token (signature, `iss`, `aud`, `iat`, `exp` short, `typ` `logout+jwt`, `events` member, `sub`/`sid`, no `nonce`), does the OP confirm with the user when `id_token_hint` is missing or foreign, and is every session in the SSO chain inventoried with its lifetime and termination path? Logout-token handlers that never check the event member: `grep -rlE 'logout_token|logoutToken' . | xargs -r grep -LE 'schemas\.openid\.net/event/backchannel-logout'`
- [ ] **Medium** — For each adopted SaaS tenant: are admins named and few, connected apps and data-sharing integrations inventoried with scope and owner and reviewed, and are tenant scripts, webhooks and custom apps security-reviewed before they run?
