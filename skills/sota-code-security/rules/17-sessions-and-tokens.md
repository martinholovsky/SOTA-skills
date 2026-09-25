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
  password change, MFA step-up, role elevation. Reusing the pre-auth ID =
  session fixation (CWE-384).
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
  prevention for stolen sessions. Optionally bind sessions to coarse client
  properties (IP range/UA family) and step-up on anomaly rather than hard-fail.

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
- `kid`/`jku`/`x5u` header fields: treat as untrusted input. `kid` → lookup in
  your own keystore only (SQLi/path traversal via `kid` is a known pattern);
  `jku`/`x5u` → allowlist of your own JWKS URLs or reject.
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
