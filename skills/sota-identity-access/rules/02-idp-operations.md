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

## 2. Client / relying-party registration discipline

Each application is a distinct client with the narrowest config that works:

- **One client per app**, never shared. Exact redirect URIs only (rules/01 §4).
- **Scopes/claims minimal**: grant only the scopes the app needs; do not enable the
  `groups`/`profile`/`email` claims for a client that does not consume them.
- **Public vs confidential**: SPAs and native apps are public clients (no secret) and
  MUST use PKCE; server-side apps are confidential and authenticate per the ladder below.
- **Disable unused grant/response types** per client (no implicit, no ROPC).
- **Dynamic Client Registration** (RFC 7591), if enabled, must be authenticated and
  policy-gated — open DCR lets anyone mint a client.

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
- Prefer asymmetric signing (RS256/ES256/EdDSA) so RPs verify with public keys and the
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
  this is **sota-code-security** rules/02.)
- **Single Logout (SLO) / back-channel logout**: SSO means one credential opens many RPs;
  logout or credential-change must propagate. Configure **back-channel logout** (OIDC
  Back-Channel Logout: the IdP POSTs a logout token to each RP) so a sign-out or
  forced revocation actually ends sessions everywhere. Front-channel-only logout is
  unreliable (depends on browser). SAML SLO has the same goal and the same fragility.
- On credential change / account disable, *kill live sessions* — pair with CAEP/SSF
  (rules/06) for near-real-time propagation rather than waiting for token expiry.

## 7. Consent

- For first-party apps, consent may be implicit/skipped. For **third-party** clients,
  show an informative consent screen: which client, which scopes, what data, revocable.
- Consent is auditable and revocable by the user and by an admin; revoking consent
  revokes the associated tokens. For privacy/regulatory consent (purpose, retention) see
  **sota-privacy-compliance**.
- Beware "consent phishing": a malicious OAuth app requesting broad scopes. Gate which
  clients may request sensitive scopes; admin-approve high-scope third-party apps.

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
