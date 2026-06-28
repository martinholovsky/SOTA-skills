# 01 — Federation Protocols & Their Attack Catalog

Scope: the wire protocols of federated identity and how they fail — OIDC/OAuth 2.x
flows and token validation at the relying party (RP), OAuth 2.1 and FAPI 2.0, the
sender-constraining and request-integrity extensions (PKCE, PAR, RAR, JAR, DPoP, mTLS),
SAML 2.0 and its attack classes, and SCIM 2.0 as a provisioning protocol.

This file owns **protocol design and the IdP/RP token contract**. It does NOT own the
app-side JWT *signature-verification code path* or session cookie handling — that is
**sota-code-security** rules/02. When the finding is "this Express middleware does not
pin the alg," route it there; when it is "the IdP allows the implicit flow" or "the RP
never checks `aud`," it is here.

## 1. OIDC / OAuth: only Authorization Code + PKCE for interactive flows

- **Authorization Code + PKCE (RFC 7636) is the only sanctioned interactive flow** — for
  confidential *and* public clients. PKCE binds the authorization request to the token
  request via a `code_verifier`/`code_challenge` (use `S256`, never `plain`).
- **Implicit flow is dead.** It returns tokens in the URL fragment (leak via history,
  referrer, logs) with no client authentication. OAuth 2.1 (`draft-ietf-oauth-v2-1`,
  draft-15, March 2026 — still an Internet-Draft, *not* an RFC) removes it. Disable
  `response_type=token`/`id_token token` at the IdP.
- **ROPC / password grant is dead.** It hands the user's password to the client,
  defeats federation and MFA, and is removed in OAuth 2.1. Disable
  `grant_type=password`.
- **Client credentials** for machine-to-machine only (no end user present).
- **Device Authorization Grant (RFC 8628)** for input-constrained devices.
- The current security baseline is **OAuth 2.0 Security Best Current Practice, RFC 9700
  (January 2025)**: PKCE for all auth-code flows, exact redirect-URI matching, refresh
  rotation or sender-constraining, short-lived access tokens.

```
# GOOD: IdP client config — interactive web app
grant_types         = ["authorization_code", "refresh_token"]
response_types      = ["code"]
require_pkce        = true        # S256
token_endpoint_auth = "private_key_jwt"   # not client_secret_basic
# BAD
grant_types    = ["authorization_code", "implicit", "password"]   # implicit + ROPC live
require_pkce   = false
```

## 2. Token types: ID token vs access token vs userinfo

- **ID token** authenticates the *user to the client*. It is a JWT for the RP to
  consume. Never send it to a resource server as a credential.
- **Access token** authorizes the *client to a resource server*. Opaque or JWT; the RP
  treats it as bearer (or sender-constrained). The client must not parse/depend on its
  contents unless it is the audience.
- **UserInfo endpoint** returns fresh claims for the access token's subject. Use it when
  claims may have changed since token issuance; do not stuff every attribute into the ID
  token.
- A frequent confusion bug: the client validates the *access* token as if it were the ID
  token, or forwards the ID token as the API bearer. Keep the roles distinct.

## 3. Required claim validation at the RP (the highest-yield audit area)

Validate **every** ID token (OpenID Connect Core 1.0):

- `iss` — exact string match to the configured issuer. Mismatched/missing `iss` =
  accept-any-IdP.
- `aud` — must contain *this* client's `client_id`. Missing `aud` check = a token minted
  for client B is accepted by client A. If `aud` is an array or `azp` is present, verify
  `azp` equals your `client_id`.
- `exp` — reject expired; enforce small clock skew (≤60s). Also `nbf`/`iat` sanity.
- `nonce` — the RP sends a `nonce` in the auth request and verifies it echoes in the ID
  token (binds token to *this* login, anti-replay). REQUIRED for implicit/hybrid; send
  and check it for auth-code too.
- Signature — pin allowed `alg` to the IdP's actual signing alg(s) (e.g. `RS256`,
  `ES256`); fetch keys from the IdP `jwks_uri`; **reject `alg:none` and reject
  symmetric `alg` when an asymmetric key is expected** (the RS256→HS256 confusion
  attack: a verifier that trusts the header `alg` can be tricked into HMAC-verifying with
  the public key as the secret).

```
# BAD — accepts any issuer, no audience, trusts header alg
claims = jwt.decode(token, key, verify_aud=False)   # aud unchecked
# GOOD
claims = verify(token,
    issuer="https://idp.example.com",
    audience="web-app",
    algorithms=["ES256"],          # pinned; no 'none', no HS*
    require=["iss","aud","exp","iat","nonce"])
assert claims.get("azp", claims["aud"]) == "web-app"
```

- **Mix-up defense when the RP/broker talks to more than one AS** (Kanidm *plus* any
  upstream/social IdP): validate the `iss` **authorization-response** parameter
  (RFC 9207), not just the ID-token `iss`. Without it, an attacker who can make the
  user start a login at an honest AS can swap in a malicious AS's authorization
  response and have the code/token redeemed at the wrong endpoint. Single-AS
  deployments are unaffected, but wire it in before adding a second IdP.

- **Discovery & JWKS**: configure from `/.well-known/openid-configuration` (OpenID
  Connect Discovery 1.0), cache the `jwks_uri` keys, and honor key rotation by `kid`
  (re-fetch on unknown `kid`; do not pin a single key forever). Cache JWKS with a sane
  TTL; a hammering RP that re-fetches per request is a DoS on the IdP.

## 4. Redirect-URI discipline (Critical when loose)

- Register **exact, absolute** redirect URIs. **No wildcards** (`https://app/*`), no
  scheme downgrade (`http`), no trailing-slash/path looseness, no
  open-host patterns. The IdP must match the requested `redirect_uri` against the
  registered set by **exact string compare**.
- Loose matching is a token-theft primitive: an attacker who can satisfy a wildcard
  (`https://app.example.com.attacker.com/cb`, `https://app/.../@evil`, an open redirect
  on the registered host) receives the code/token.
- Per-client registration: each RP gets its own client with its own narrow redirect set.
  Never share one client across apps.

```
# BAD
redirect_uris = ["https://app.example.com/*", "http://localhost"]
# GOOD
redirect_uris = ["https://app.example.com/auth/callback"]   # exact, https, fixed path
```

## 5. Request integrity & sender-constraining extensions

Adopt these for high-value and high-assurance clients; required by FAPI 2.0.

- **PAR — Pushed Authorization Requests, RFC 9126**: the client POSTs the authorization
  request to the IdP back-channel and receives a `request_uri`; the front-channel URL
  carries only that reference. Removes request-tampering and parameter-injection on the
  redirect.
- **RAR — Rich Authorization Requests, RFC 9396**: `authorization_details` carries
  fine-grained, structured authorization (e.g. "transfer ≤€100 from account X") instead
  of coarse scopes. Use for transactional authorization.
- **JAR — JWT-Secured Authorization Request, RFC 9101**: the request parameters are a
  signed (optionally encrypted) JWT, giving request integrity/authenticity.
- **DPoP — Demonstrating Proof of Possession, RFC 9449**: sender-constrains access and
  refresh tokens by binding them to a client-held key proven per request via a `DPoP`
  header. A stolen DPoP-bound token is useless without the private key. The
  application-layer alternative to mTLS-bound tokens.
- **mTLS client auth & certificate-bound tokens — RFC 8705**: client authenticates with
  a TLS client cert; tokens are bound to the cert thumbprint. Strongest client auth /
  token binding where a PKI exists — coordinate with **sota-network-security** (mTLS).
- **PKCE downgrade**: if the IdP *supports* but does not *require* PKCE, a MITM can strip
  the `code_challenge`. Mitigation: the IdP rejects a token request with a
  `code_verifier` when no challenge was registered, and rejects an auth-code request
  without a challenge for clients configured to require PKCE. Enforce, don't merely
  offer.

## 6. OAuth 2.1 and FAPI 2.0 posture

- **OAuth 2.1**: a consolidation draft (obsoletes 6749/6750/8252, folds in RFC 9700). It
  is not yet an RFC — treat its *mandates* (PKCE everywhere, no implicit, no ROPC, exact
  redirect URIs) as today's baseline regardless, because they are independently in force.
- **FAPI 2.0 Security Profile** is **Final (22 February 2025)**; FAPI 2.0 Message Signing
  finalized later in 2025. For high-assurance (open banking, health, government) profiles
  require: PAR (RFC 9126) and reject non-PAR requests; **sender-constrained tokens via
  DPoP (9449) or mTLS (8705)**; PKCE S256; exact redirect URIs; tight token lifetimes.
  Reach for FAPI 2.0 when the blast radius of a stolen token is financial or regulated.

## 7. SAML 2.0 and its attack classes

SAML 2.0 (OASIS, 2005) remains common for enterprise SSO; new development should prefer
OIDC. When you run or consume SAML, the failure modes are signature-handling bugs:

- **XML Signature Wrapping (XSW)**: the attacker wraps a forged assertion so the
  signature-validation logic and the business logic resolve *different* elements
  ("validate this signed node, but read that injected node"). Defense: validate the
  signature over the element you actually consume; resolve assertions by the same
  reference the signature covers; use a hardened SAML library, schema-validate, and
  reject documents with multiple/extra assertions.
- **Comment-injection / canonicalization truncation** (Duo, 2018): canonicalization
  drops a comment node before signature check, but naive text extraction reads only the
  first text node — `admin@corp.com<!---->.evil.com` authenticates as `admin@corp.com`.
  Defense: extract the *full* node text (concatenate text nodes) or use a library patched
  for this; don't `getFirstChild().getNodeValue()`.
- **Unsigned-assertion / signature-exclusion**: the RP accepts a response/assertion with
  no signature, or validates only the *first* assertion while consuming a second.
  Defense: require a valid signature on the response **or** the assertion you consume,
  fail closed when absent, and reject extra assertions.
- **IdP-initiated SSO risks**: no `InResponseTo` binding → login CSRF and assertion
  replay. Prefer SP-initiated flows; if IdP-initiated is required, enforce single-use
  assertion IDs, tight `NotOnOrAfter`, audience restriction, and RelayState validation.
- Always enforce: `Destination`/`Recipient` checks, `AudienceRestriction`, assertion
  replay cache, signed metadata, and a rotation plan for IdP signing certs.

## 8. SCIM 2.0 as a protocol

- **SCIM 2.0** = RFC 7642 (requirements), RFC 7643 (core schema: User, Group), RFC 7644
  (protocol — REST CRUD + PATCH + bulk + filtering). It is the standard for
  cross-domain user provisioning/deprovisioning; lifecycle *usage* is rules/04.
- Protocol-level hardening: authenticate the SCIM endpoint (bearer/OAuth, not a static
  shared secret in a header), authorize per-tenant, validate filters to avoid injection,
  rate-limit, and treat `active=false` / DELETE as the deprovisioning trigger (don't
  leave a "soft-deleted but still-authenticating" account).
- **Emerging**: `draft-ietf-scim-events` ("SCIM Profile for Security Event Tokens") adds
  asynchronous SCIM events via SETs; in the RFC Editor queue as of late 2025 — track it
  for event-driven provisioning, but it is not yet an RFC.

## 9. Legacy: WS-Federation

WS-Federation is a legacy WS-* protocol; vendors (Microsoft Entra/ADFS) treat OIDC and
SAML 2.0 as the strategic protocols and keep WS-Fed only for backward compatibility.
New integrations: do not adopt WS-Fed; migrate existing ones to OIDC.

## Audit checklist

- [ ] Is the implicit flow (`response_type=token`/`id_token token`) disabled at the IdP for every client?
- [ ] Is ROPC / `grant_type=password` disabled?
- [ ] Is PKCE (S256) required — not merely supported — for all authorization-code clients? `grep -ri "require_pkce\|code_challenge_method"`
- [ ] Are all `redirect_uri`s exact, absolute, HTTPS, with no wildcards? Hunt config for `redirect_uri.*\*` or `://\*`.
- [ ] Does every RP validate `iss`, `aud` (and `azp` when present), `exp`, and `nonce` on the ID token? Grep RP code for `verify_aud`, `audience`, `nonce`.
- [ ] Are token-verification algorithms pinned, with `alg:none` and asymmetric→symmetric confusion rejected?
- [ ] Does the RP fetch keys from `jwks_uri` and rotate by `kid` (re-fetch on unknown kid), with a sane JWKS cache TTL?
- [ ] Are high-value/regulated clients on PAR + DPoP/mTLS (FAPI 2.0) rather than bare bearer tokens?
- [ ] For SAML RPs: is a signature required and validated over the consumed assertion, with XSW and comment-injection defenses, audience restriction, replay cache, and extra-assertion rejection?
- [ ] Is IdP-initiated SAML avoided or hardened (single-use IDs, tight NotOnOrAfter, RelayState validation)?
- [ ] Is the SCIM endpoint authenticated/authorized per-tenant, with DELETE/`active=false` actually terminating authentication?
- [ ] Is any WS-Federation usage documented as legacy with a migration plan to OIDC?
