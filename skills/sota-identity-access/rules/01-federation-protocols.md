# 01 — Federation Protocols & Their Attack Catalog

Scope: the wire protocols of federated identity and how they fail — OIDC/OAuth 2.x
flows and token validation at the relying party (RP), OAuth 2.1 and FAPI 2.0, the
sender-constraining and request-integrity extensions (PKCE, PAR, RAR, JAR, DPoP, mTLS),
SAML 2.0 and its attack classes, and SCIM 2.0 as a provisioning protocol.

This file owns **protocol design and the IdP/RP token contract**. It does NOT own the
app-side JWT *signature-verification code path* or session cookie handling — that is
**sota-code-security** rules/17. When the finding is "this Express middleware does not
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
- **Make the kind of token machine-checkable, and check it.** When one issuer signs several
  kinds of JWT with the same keys (ID token, access token, logout token, SET), a verifier
  that checks only signature and claims will accept one kind where another was meant.
  Explicit typing (RFC 8725 Sec. 3.11) closes this: an RS consuming RFC 9068 JWT access tokens
  MUST reject any `typ` other than `at+jwt`/`application/at+jwt`; an RP consuming OIDC
  Back-Channel Logout tokens should require `logout+jwt` (the spec RECOMMENDS the issuer set
  it). Pin the expected `typ` per endpoint, the same way you pin `alg`.
- **Issuer side: one audience per token.** If one issuer mints JWTs for more than one
  recipient, each token MUST carry an `aud` naming its recipient (RFC 8725 Sec. 3.9) — never a
  shared or empty audience that every service accepts. When audiences arrive dynamically
  (the RFC 8707 `resource` parameter, dynamically registered clients), check the requested
  value against the registered set and refuse unknown ones (`invalid_target`) instead of
  minting a token for whatever string was asked for.
  OWASP: ASVS 5.0 V9.2.2, V9.2.4.

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
- `acr` / `amr` / `auth_time` — **asking for a level is not getting it.** `acr_values` is a
  *voluntary* claim request (OIDC Core Sec. 3.1.2.1): the OP may authenticate at a lower level
  and say so in `acr`. When the RP sent `acr_values`, compare the returned `acr` (and `amr`,
  if policy names methods) with what it required and refuse or re-prompt on a shortfall.
  When it sent `max_age`, the ID token MUST carry `auth_time`; compute `now - auth_time`
  yourself and re-authenticate if it exceeds the limit. A missing claim is a failure, not a
  pass. The same applies to a **resource server** that gates an operation on
  authentication strength: read `acr`/`auth_time` from the access token (RFC 9068 Sec. 2.2.1)
  or introspection, and answer a shortfall with the RFC 9470 challenge
  (`error="insufficient_user_authentication"` plus `acr_values`/`max_age`).
- **The RP session must not outlive the authentication it rests on.** Derive the local
  session's absolute lifetime from `auth_time` and the IdP's re-authentication policy (and
  `SessionNotOnOrAfter` in SAML), not from a local default that silently extends it.
  OWASP: ASVS 5.0 V10.3.4, V6.8.4, V7.6.1; OWASP JSON Web Token cheat sheet.
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
  deployments are unaffected, but wire it in before adding a second IdP. Store, per
  authorization request, which issuer it was sent to and compare on return. If an AS
  cannot send `iss`, the fallback (RFC 9700 Sec. 4.4.2.2) is a **distinct redirect URI per
  issuer**, checked against the URI the response actually arrived on — weaker, since an
  attacker who can register a client at the honest AS may reuse that URI, so use it only
  when issuer identification is unavailable.

- **Metadata issuer must equal the configured issuer.** The `issuer` in fetched discovery
  metadata MUST be identical to the issuer URL it was fetched from (OIDC Discovery Sec. 4.3,
  RFC 8414 Sec. 3.3) and to the ID-token `iss`; on mismatch discard the whole document. A
  client that reads `authorization_endpoint`/`token_endpoint`/`jwks_uri` from whatever
  metadata it received lets a mix-up attacker supply their own endpoints.
  OWASP: ASVS 5.0 V10.5.3; OWASP OAuth2 cheat sheet.

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
- **AS side: never redirect a credential POST with 307 (or 308).** Both are
  method-preserving (RFC 9110 Sec. 15.4), so the browser re-POSTs the login form — password
  included — to the client's redirect URI. RFC 9700 Sec. 4.12: an AS MUST NOT use 307 there and
  SHOULD use **303 See Other**, the only code that unambiguously turns POST into GET. Check
  custom login pages and any framework helper whose default status you did not choose.

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

### 5.1 At the resource server: verify the binding, then authorize from the token

Sender-constraining protects nothing unless the **resource server** checks the proof; an RS
that accepts a DPoP-bound token as a plain bearer token has turned it back into one.

- **DPoP (RFC 9449 Sec. 4.3 and 7)** — on every request: exactly one `DPoP` header holding one
  JWT; `typ` = `dpop+jwt`; an asymmetric, allowlisted `alg` (never `none`); signature
  valid under the header `jwk`, which must hold no private key; `htm` = this request's
  method and `htu` = this request's URI (query and fragment ignored); `iat` (or a
  server-issued `nonce`) inside a short window; **`ath` = the hash of the presented access
  token**; and the proof key's thumbprint = the token's `cnf.jkt`. Track `jti` per target
  URI for the acceptance window and refuse repeats (RFC 9449 Sec. 11.1) — the one check that needs
  shared state, so multi-instance RSs drop it first.
- **mTLS-bound tokens (RFC 8705 Sec. 3)** — take the client certificate from the TLS layer of
  *this* connection (not a header an upstream proxy could let a client set), hash it, and
  compare with the token's `cnf` `x5t#S256`; on mismatch reject with 401 `invalid_token`.
- **MCP servers are resource servers.** The MCP authorization spec (2025-11-25 revision)
  requires tokens audience-bound to the MCP server (RFC 8707 `resource`), and forbids
  passing a client's token through to upstream APIs; it does not itself require
  sender-constraining. Treat MCP client→server tokens as FAPI-grade anyway when they grant
  tool access to sensitive systems: DPoP- or mTLS-bind them and verify as above.
- **Authorize each request from what the token grants, not from the token being valid.**
  After validation (rules/03 for the model), decide on the token's `scope`, its RFC 9396
  `authorization_details` (type, actions, locations, amounts), and its subject — every
  request, not once per session. A structurally valid token for another operation is a
  deny.
- **Key the user on `iss` + `sub`, never `sub` alone.** `sub` is only unique within one
  issuer (OIDC Core Sec. 5.7); an RS that trusts two issuers and looks users up by `sub` lets
  one issuer's subject act as another's. Also keep resource-owner tokens apart from
  client-credentials tokens whose `sub` is a client id (RFC 9700 Sec. 4.15).
  OWASP: ASVS 5.0 V10.3.2, V10.3.3; AISVS 10.3.5; OWASP OAuth2 cheat sheet.

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
- **Golden SAML — forging tokens with a stolen signing key (ATT&CK T1606.002)**: every
  defense above protects the *assertion*; this defeats all of them at once. An attacker
  holding the IdP's **token-signing private key** mints valid assertions for any user, with
  any claims and any lifetime, so **MFA, password policy and account lockout are all
  bypassed** — the federation server never authenticates anyone and logs nothing, while the
  SP receives a correctly signed token. Seen in the SolarWinds compromise (APT29) and
  automated by public tooling (AADInternals). Defenses: keep the signing key
  **non-exportable in an HSM/TPM**; treat the federation server as **Tier 0** and administer
  it only from privileged access workstations; minimise which SPs trust the IdP; and on
  suspected compromise **rotate the token-signing certificate twice in succession** — a
  single rotation leaves the previous certificate valid and every forged token still working.
  Detecting it is a *join between two logs* and lives in `sota-detection-engineering`
  rules/07; the hybrid/Entra blast radius is rules/07 §5 here.
- Always enforce: `Destination`/`Recipient` checks, `AudienceRestriction`, assertion
  replay cache, signed metadata, and a rotation plan for IdP signing certs.
- **Verify with the IdP's pinned key, never the document's own.** SAML Core Sec. 5.4.5 puts no
  restriction on `<ds:KeyInfo>`, so a certificate inside the response proves only that
  *someone* signed it. Load the IdP's signing certificate(s) from its metadata at
  onboarding, keyed by entity ID, and verify against those; ignore embedded `KeyInfo` /
  `X509Certificate` except to select among already-trusted keys. Check the response and
  assertion `<Issuer>` equal the expected IdP entity ID *before* choosing the key.
- **Run the profile's processing rules and the binding's rules.** Walk Web SSO Profile
  Sec. 4.1.4.3 in full (verify signatures, `Recipient` = your ACS URL, bearer
  `NotOnOrAfter`, `InResponseTo` = your request ID or absent for unsolicited, discard any
  invalid assertion). HTTP-POST (Profile Sec. 4.1.4.5): assertions MUST be signed and bearer
  assertion IDs kept in a replay cache until `NotOnOrAfter`. HTTP-Redirect carries its
  signature in the `Signature`/`SigAlg` query parameters over the URL-encoded
  `SAMLRequest`/`SAMLResponse`, `RelayState` and `SigAlg` (Bindings Sec. 3.4.4.1) — verify
  that octet string as received, and never accept an SSO `<Response>` on Redirect (the
  profile forbids it). Use the OASIS *Security and Privacy Considerations* document as the
  audit walk-through. OWASP: OWASP SAML Security cheat sheet.

## 8. SCIM 2.0 as a protocol

- **SCIM 2.0** = RFC 7642 (requirements), RFC 7643 (core schema: User, Group), RFC 7644
  (protocol — REST CRUD + PATCH + bulk + filtering). It is the standard for
  cross-domain user provisioning/deprovisioning; lifecycle *usage* is rules/04.
- Protocol-level hardening: authenticate the SCIM endpoint (bearer/OAuth, not a static
  shared secret in a header), authorize per-tenant, validate filters to avoid injection,
  rate-limit, and treat `active=false` / DELETE as the deprovisioning trigger (don't
  leave a "soft-deleted but still-authenticating" account).
- **SCIM Security Events — RFC 9967 (May 2026)**: the SCIM Profile for Security Event
  Tokens (SETs; updates RFC 7643/7644) is now the standard mechanism for asynchronous,
  event-driven provisioning signals — prefer it over ad-hoc webhooks or polling for
  propagating lifecycle changes across domains.

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
- [ ] Does the RP send a `state` parameter, bind it to the session, and verify it on the callback **before** exchanging the code? CSRF on the authorization response is not covered by PKCE; the rule lives in `sota-code-security` rules/02 §4, and this checklist is where an SSO audit looks for it.
- [ ] Is the IdP's token-signing key non-exportable (HSM/TPM), the federation server Tier 0, and is there a **rotate-twice** runbook for suspected key compromise (Golden SAML, T1606.002)?
- [ ] Is IdP-initiated SAML avoided or hardened (single-use IDs, tight NotOnOrAfter, RelayState validation)?
- [ ] Is the SCIM endpoint authenticated/authorized per-tenant, with DELETE/`active=false` actually terminating authentication?
- [ ] Is any WS-Federation usage documented as legacy with a migration plan to OIDC?
- [ ] **High** — When the RP sends `acr_values`/`max_age`, does it check the returned `acr`/`amr`/`auth_time` and fail on a shortfall or a missing claim (and does an RS gating on strength do the same)? Files that request a level but never read it: `grep -rlE 'acr_values|max_age' . | xargs grep -LE 'auth_time|["'\'']acr["'\'']|\.acr([^A-Za-z_]|$)'`
- [ ] **Medium** — Does every JWT consumer pin the expected `typ` (`at+jwt` at an RS, `logout+jwt` for back-channel logout), and does the issuer give each recipient its own `aud` and refuse unknown `resource` values? Verifiers with no `typ` check: `grep -rlE 'jwtVerify|jwt\.(decode|verify)|JwtDecoder|ValidateToken' . | xargs grep -LE '[+]jwt|["'\'']typ["'\'']'`
- [ ] **High** — Does the RS authorize every request from the token's `scope`/`authorization_details`/subject, and key users on `iss`+`sub`? User lookups on `sub` alone: `grep -rnE '[Uu]ser[A-Za-z_]*\(.*sub|WHERE[[:space:]]+sub[[:space:]]*=' . | grep -v iss`
- [ ] **High** — Does the RS verify DPoP proofs fully (`typ`, `alg`, signature, `htm`, `htu`, `iat`/`nonce`, `ath`, `cnf.jkt`, `jti` replay) and match mTLS-bound tokens' `cnf` `x5t#S256` against the connection's client certificate — including MCP servers? DPoP handlers that never check `ath`: `grep -rlE 'dpop\+jwt|DPoP' . | xargs grep -LE '["'\'']ath["'\'']|\.ath([^A-Za-z_]|$)'`
- [ ] **Medium** — With more than one AS: is the issuer stored per request and compared on return (`iss` parameter, or a distinct redirect URI per issuer as fallback), and is fetched metadata discarded when its `issuer` differs from the configured one? Discovery fetches with no issuer comparison: `grep -rlE 'well-known/(openid-configuration|oauth-authorization-server)' . | xargs grep -LE '\[["'\'']issuer["'\'']\][[:space:]]*(!=|==)|\.issuer[[:space:]]*(!=|==|!==|===)'`
- [ ] **High** — Does the AS redirect after a credential POST with 303, never 307/308? `grep -rnE 'code=30[78]|redirect\(30[78]|StatusTemporaryRedirect|StatusPermanentRedirect|TEMPORARY_REDIRECT|PERMANENT_REDIRECT' .`
- [ ] **Critical** — Does the SAML SP verify only against IdP keys pinned from metadata (never a certificate taken from the message's `KeyInfo`), check `<Issuer>`, and apply the Web SSO profile and binding rules (signed assertions + replay cache on POST, query-string signature on Redirect, no `<Response>` on Redirect)? Keys read out of the document: `grep -rnE '(find|findtext|xpath|select|getElementsByTagName[A-Za-z]*)\(.*(KeyInfo|X509Certificate)' .`
