# 17 — Sessions & Tokens

Scope: server-side session management, remember-me tokens, JWT verification and token
lifetimes. Split out of rules/02 on 2026-09-25 with its section numbers kept (2 and 3), so
an older citation of rules/02 section 2 or 3 names the same text here. Maps to OWASP A07:2025, CWE-384/613/345/347.

Core principle: **use the framework's session machinery and a maintained JWT library, and
configure them; never invent a token format.** Authentication itself (passwords, MFA,
OAuth/OIDC, passkeys, recovery) stays in rules/02.

## 2. Session management (CWE-384, CWE-613)

- Use the framework's session implementation. Session IDs: ≥ 128 bits from a
  CSPRNG, opaque (no encoded user data), stored server-side or in a sealed cookie.
- **Regenerate the session ID on every privilege change**: login, logout,
  password change, MFA step-up, role elevation, and a change of connection security
  (HTTP to HTTPS). Reusing the pre-auth ID = session fixation (CWE-384).
- **Strict IDs, from the cookie only.** Run the store in *strict* mode: an ID the server
  never minted is discarded, a fresh one is issued, and the event is logged as suspicious.
  A *permissive* store, which opens a session for any value presented, is fixation by
  design (PHP's: `session.use_strict_mode` is `0` with no ini, measured on 8.5.9;
  `sota-php` rules/04). Accept the ID from
  the session cookie and nowhere else, and establish **by test** which other carriers the
  stack still honours (a `;jsessionid=` path parameter, a query or form field, a custom
  header); frameworks that fall back to URL rewriting do it silently (servlet tracking
  modes, `sota-jvm` rules/04). Never carry one session across an HTTP-to-HTTPS switch:
  set or regenerate the cookie only after the redirect to HTTPS has happened.
  OWASP: Session Management cheat sheet; Secure Coding Practices QRG; Code Review Guide v2.
- **One session key, one meaning** (session puzzling, WSTG-SESS-08). When a reset or
  signup page writes `user`/`email`/`user_id` into the session, and an authenticated page
  treats that key's presence as proof of login, visiting the reset page logs the attacker
  in. Namespace keys per flow (`reset.pending_user`, `signup.email`), write the identity
  key only on a completed login (after regenerating the ID), and drop a flow's keys when
  it ends. The identity key should have exactly one writer: the login success path.
- Cookie flags: `Secure; HttpOnly; SameSite=Lax` (or `Strict`), `__Host-` prefix
  (enforces Secure + no Domain attribute + Path=/). Details in rules/05.
- Expiry: idle timeout (15–30 min sensitive apps, ≤ 24h general) AND absolute
  timeout (e.g. 8–12h) regardless of activity (CWE-613). Logout must invalidate
  **server-side**, not just clear the cookie.
- On password change or "log out everywhere": revoke all of the user's sessions.
  Maintain a session registry to make this possible.
- **Renewal timeout**: regenerate the session ID periodically mid-session (e.g. every
  few hours) even without a privilege change, capping the window a stolen ID is useful.
- On logout/sensitive responses, send `Clear-Site-Data: "cookies", "storage"` and
  `Cache-Control: no-store` so the session artifact isn't left in the browser/proxy cache.
- Bind nothing secret into URLs: session tokens in query strings leak via logs,
  referrers, and browser history (CWE-598).
- "Remember me" done right: a separate long-lived token, never an extended
  session — `selector:validator` pattern (selector indexes the row, validator
  is compared against its **hash** constant-time), single-use rotation on each
  login, revoked with the session family on password change. A long-lived
  token granting full session powers without re-auth for sensitive ops is a
  finding; pair with step-up auth (rules/02 §5).
- Concurrent-session policy is product-specific, but display active sessions
  (device, IP, last seen) and let users revoke them — detection beats
  prevention for stolen sessions.
- **Detect a stolen cookie in use.** At session creation, record the client context on the
  server: IP range or ASN, UA family, `Accept-Language`, `Accept-Encoding`, client hints
  (`Sec-CH-UA*`), creation time. Compare it on each request in middleware, sensitive
  endpoints first. Judge whether the *meaning* changed, not the bytes: a browser update
  changes the UA string and a Wi-Fi switch changes the IP. `Sec-Fetch-*` is not sent by every
  browser, so its absence is no signal. When a session spans several cookies, verify all of
  them and their binding to each other. If the context turns implausible, or a sealed
  cookie fails its integrity check, invalidate the session server-side and issue a new
  cookie after re-authentication. For a weaker signal, step up (or show a CAPTCHA against
  bots) before any side-effecting action; never hard-fail on a bare IP change.
- **Device Bound Session Credentials** (DBSC) make the cookie sender-constrained: the
  browser holds a non-exportable key (TPM-backed in Chrome on Windows) and proves
  possession at a refresh endpoint to renew a short-lived cookie. It is a W3C WebAppSec
  draft that only Chromium is pursuing (chromestatus, read 2026-09-25: Firefox position
  negative, Safari no signal), so it adds to the detection above and does not replace it.
  OWASP: Cookie Theft Mitigation, Session Management cheat sheets; Code Review Guide v2.

```python
# GOOD: remember-me verification (selector/validator, hashed at rest)
row = db.get_remember_token(selector)
if row and not row.expired and hmac.compare_digest(
        hashlib.sha256(validator).digest(), row.validator_hash):
    rotate_remember_token(row)            # single use
    login_user(row.user_id, fresh=False)  # mark non-fresh: step-up for sensitive ops
```

## 3. JWT pitfalls (CWE-345, CWE-347)

JWTs are misconfiguration magnets. If sessions are server-side anyway, prefer
opaque tokens. If you use JWTs:

- **Pin the algorithm at verification.** Pass an explicit allowlist
  (`algorithms=["EdDSA"]` or `["RS256"]`); never trust the header's `alg`.
  Classic breaks: `alg: none` acceptance, and RS256→HS256 confusion where the
  public key is used as an HMAC secret (CWE-347).
- Prefer asymmetric (EdDSA/Ed25519 or ES256) when multiple services verify —
  shared HMAC secrets turn every verifier into a forger. HS256 secrets must be
  ≥ 256 bits random, never a password.
- **Always set and verify `exp`** (short: 5–15 min for access tokens), plus `iss`,
  `aud`, `nbf`. Verifying signature but not claims is a common library default trap.
- Revocation: JWTs can't be revoked, so keep them short-lived and pair with
  rotating refresh tokens (server-side, revocable, **rotation with reuse
  detection** — a replayed old refresh token revokes the whole family).
- **A denylist, if you need one, is keyed on `(iss, jti)`**: every issued token carries a
  unique `jti`, each entry expires at that token's `exp`, and logout, idle timeout and
  password change add the `jti`. Never key it on the raw token string or `SHA-256(token)`,
  because one token can have several spellings that all verify. Lenient parsing is one
  source; ECDSA is another, since `(r, s)` and `(r, n − s)` are both valid signatures.
  Measured 2026-09-25 with PyJWT 2.15.0: an ES256 token with `s` replaced by `n − s` is a
  different string with a different hash, and `jwt.decode` accepts it. For issuer-side
  revocation at scale, the IETF Token Status List draft puts a `status` claim in the token.
  OWASP: JSON Web Token, REST Security cheat sheets.
- **Header-carried key material is attacker input: `kid`, `jku`, `x5u`, `jwk`, `x5c`**
  (RFC 7515 section 4.1). An embedded `jwk` or `x5c` lets a forger ship the public key matching
  their own private key (CVE-2018-0114: node-jose before 0.11.0 trusted the embedded
  `jwk`), and `jku`/`x5u` do the same by URL. Take verification keys only from server-side
  configuration: a pinned key, or the JWKS at the issuer's configured `jwks_uri`. Accept
  `x5c`/`x5u` only when the chain validates to a trust anchor already bound to that
  issuer. Use `kid`/`x5t` only to *select* among keys you already hold, and validate `kid`
  first (SQLi/path traversal via `kid` is a known pattern). Every URL derived from token
  content (`jku`, `x5u`, a status-list `uri`, `iss`-driven discovery) is an outbound fetch
  of attacker-chosen input: allowlist it and apply rules/01 §5 (SSRF).
  OWASP: JSON Web Token cheat sheet; ASVS 5.0 V9.1.3.
- Never put secrets/PII in the payload — it's base64, not encrypted.
- Browser storage: keep tokens out of `localStorage` (XSS-exfiltratable, CWE-922).
  Use `HttpOnly` cookies, or in-memory only with refresh via HttpOnly cookie.

```js
// BAD: library honors header alg, no claim checks
jwt.verify(token, key);
// GOOD
jwt.verify(token, publicKey, { algorithms: ["EdDSA"], issuer: ISS,
                               audience: AUD, maxAge: "15m" });
```

## Audit checklist

- [ ] Is the session ID regenerated at login and every privilege change, and invalidated server-side at logout/password change?
- [ ] Do sessions have both idle and absolute timeouts, with a registry enabling "revoke all"?
- [ ] Does every JWT verification pin an algorithm allowlist and check `exp`, `iss`, `aud`?
- [ ] Are access tokens short-lived with rotating, reuse-detecting refresh tokens?
- [ ] Are tokens kept out of localStorage and URLs?
- [ ] Are "remember me" tokens selector/validator-hashed, single-use, and non-fresh (step-up required for sensitive ops)?
- [ ] **Is the session store strict and cookie-only (§2)? HIGH** — every hit is permissive
      mode, a disabled cookie-only switch, or URL tracking:
      `grep -rniE 'use_(strict_mode|only_cookies).{0,3}[=,][[:space:]]*.?(0|off|false)|use_trans_sid.{0,3}[=,][[:space:]]*.?(1|on|true)|tracking-mode>url|trackingmode\.url|tracking-modes[[:space:]]*[=:].*url' .`
      No hit is not a pass: send a request with a made-up session ID (and the ID as a URL
      parameter) and confirm the server issues a fresh one rather than adopting it.
- [ ] **Does the identity session key have one writer, the login success path (§2,
      session puzzling)? HIGH when a pre-auth flow writes it** — list the writers and read each:
      `grep -rniE '(_session|session)\[.(user|user_id|userid|uid|email|username|account)[^]]*\][[:space:]]*=[^=]|session\.(user|user_id|userid|uid|email|username)[[:space:]]*=[^=]|setattribute\(.(user|userid|user_id|email|username).,' .`
- [ ] Is client context recorded at session creation and compared per request, with a
      suspected hijack ending the session server-side (§2)? MEDIUM where absent on an app
      holding money or personal data.
- [ ] **Is the verification key never taken from the token header (§3)? CRITICAL when a
      header value selects or supplies the key unchecked** — read each hit:
      `grep -rniE 'get_unverified_header|header[^=;]*[^a-z_](jwk|jku|x5u|x5c)([^a-z_s]|$)' .`
- [ ] **Is a JWT denylist keyed on `(iss, jti)`, not the token or its hash (§3)? HIGH** —
      `grep -rniE '(deny|block|black|revok)[a-z_]*[^a-z_].*(sha256|createhash|digest|hash)\(.*(token|jwt)|(deny|block|black|revok)[a-z_]*\.(add|insert|set|sadd|put)\((raw_)?(token|jwt)[,)]|(sadd|add|insert|set|put)\([^)]*(deny|block|black|revok)[^)]*, *(raw_)?(token|jwt)[,)]' .`
