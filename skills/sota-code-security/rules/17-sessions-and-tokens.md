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
- **An incoming session ID is untrusted input.** Check its length, character set and format
  before it reaches a store lookup, a cache key or a log line: an unchecked value is an
  injection path into whatever holds sessions. A custom ID manager, where one cannot be
  avoided, accepts only a value that round-trips through the exact format it mints (for
  example, parses back into the same 128-bit value and re-serialises byte-identical), and on
  anything else issues a new ID instead of adopting the client's (PHP's
  `session_id($_GET[...])` adopts it). Give the pre-authentication and authenticated
  sessions different cookie names or ID sets, so an anonymous ID is never promoted.
  OWASP: Session Management cheat sheet.
- **Protect the session store like a credential store.** Session files, the Redis keyspace
  or the table is reachable only by the application's own identity: not a shared,
  world-readable temp directory, not an unauthenticated Redis that other tenants or
  processes on the host can reach. Encrypt session objects that carry sensitive data.
  Keep per-session state small and bounded, because any anonymous client can make the
  server allocate one. OWASP: Session Management, Denial of Service cheat sheets.
- **Creating a session takes a user action.** Mint an application session only after the
  user clicked sign-in or consented. A page that silently completes SSO on load (a hidden
  iframe or `prompt=none` round trip, an auto-submitting callback) and creates a local
  session nobody asked for is a finding; silent checks may renew a session the user
  already started, not open one. OWASP: ASVS 5.0 V7.6.2.
- **One session key, one meaning** (session puzzling, WSTG-SESS-08). When a reset or
  signup page writes `user`/`email`/`user_id` into the session, and an authenticated page
  treats that key's presence as proof of login, visiting the reset page logs the attacker
  in. Namespace keys per flow (`reset.pending_user`, `signup.email`), write the identity
  key only on a completed login (after regenerating the ID), and drop a flow's keys when
  it ends. The identity key should have exactly one writer: the login success path.
- Cookie flags: `Secure; HttpOnly; SameSite=Lax` (or `Strict`), `__Host-` prefix
  (enforces Secure + no Domain attribute + Path=/). Details in rules/05.
- Expiry: idle timeout AND absolute timeout (e.g. 8–12h) regardless of activity
  (CWE-613), both computed from **server-side timestamps**, never from a time the client
  sends or a counter the client holds. Pick the idle value by risk: the Session Management
  cheat sheet's common ranges are 2–5 min for high-value applications and 15–30 min for
  low-risk ones. Write both values down with the reason for any deviation from NIST SP
  800-63B's reauthentication requirements (ASVS 5.0 V7.1.1). Warn the user before a forced
  end so they can save work or extend; on a high-confidentiality system, extending asks
  for verification again, and a long-lived remember-me token needs a reason to exist
  there at all. Logout must invalidate **server-side**, not just clear the cookie.
- **Log the session lifecycle** (event names in rules/07 §2.1): renewal or extension,
  expiry with its reason (logout, idle, absolute, revoked), and any request presenting an
  expired or revoked ID, the last at high severity (the Logging Vocabulary rates it
  CRITICAL) because a replayed stolen cookie looks exactly like that. The event needs the
  old record: on revocation, mark the session ended and keep that tombstone until its
  absolute expiry instead of deleting the row, or a hijack attempt reads as an ordinary
  unknown ID. OWASP: Logging Vocabulary, Session Management cheat sheets.
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
- **Concurrent sessions: decide the limit, write it down, enforce it.** Document the
  maximum number of parallel sessions per account and what happens at the limit: end the
  oldest, refuse the new login, or ask the user which one to end (ASVS 5.0 V7.1.2). Log
  each exceedance as a security event, since many live sessions on one account means
  sharing or takeover. Alert the user to a new sign-in while another session is active.
- **Let people see and end sessions.** Users see their active sessions (device,
  approximate location, last seen) and an account activity history, and can end any or
  all of them after re-authenticating with at least one factor (V7.5.2); detection beats
  prevention for stolen sessions. Administrators can end one user's sessions or everyone's
  (V7.4.5). After sign-in, show the date, time and rough location of the previous successful
  login and of failed attempts since. OWASP: Session Management, Credential Stuffing
  Prevention, Logging Vocabulary cheat sheets.
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

JWTs are misconfiguration magnets. **For user sessions, default to server-side state**:
an opaque ID and a session record (§2). A JWT used as the session still needs a
revocation denylist for logout and password change (below), so it is stateful in
practice, with more moving parts. Client-held session state used to skip the server
lookup, signed or not, cannot be revoked before it expires and replays until then: a
finding unless a denylist, or a short lifetime refreshed server-side, covers it.
OWASP: JSON Web Token, REST Security cheat sheets. If you use JWTs:

- **Pin the algorithm at verification.** Pass an explicit allowlist
  (`algorithms=["EdDSA"]` or `["ES256"]`); never trust the header's `alg`.
  Classic breaks: `alg: none` acceptance, and RS256→HS256 confusion where the
  public key is used as an HMAC secret (CWE-347).
- **Algorithm choice**: EdDSA (Ed25519), ES256/384/512 or PS256/384/512. RS256/384/512
  (RSASSA-PKCS1-v1_5) is for interop with a peer that offers nothing else. Prefer
  asymmetric when multiple services verify — shared HMAC secrets turn every verifier
  into a forger. An HMAC secret is random, never a password, and at least as long as the
  hash output: 256, 384 and 512 bits for HS256, HS384 and HS512 (RFC 7518 section 3.2).
  OWASP: JSON Web Token cheat sheet.
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
- Browser storage: keep tokens **and any other sensitive data** out of `localStorage` and
  `sessionStorage` (CWE-922). Every script in the origin reads them, one XSS takes them
  all, and the login guarding the page does not guard them from someone with local
  access to the machine. **Browser apps: prefer a backend-for-frontend.** The server-side
  component is the OAuth client and holds the access and refresh tokens; the browser
  holds only an `HttpOnly` session cookie to it (§2), and tokens reach only the
  components that call the API (ASVS 5.0 V10.1.1). Tokens held in browser memory, renewed
  via an HttpOnly cookie, are the weaker fallback. When frontend code must itself use a
  secret, keep it in a dedicated Web Worker: the code needing it runs there and the secret
  is never posted to the window. XSS can still ask the worker to act, so this protects the
  secret, not its use. OWASP: HTML5 Security, Session Management cheat sheets.

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
- [ ] **Is an incoming session ID validated and never adopted from the request (§2)? HIGH**
      — custom ID managers and client-chosen IDs; read each hit for a strict round-trip parse:
      `grep -rnE 'session_id\([[:space:]]*\$_(GET|POST|REQUEST|COOKIE)|I?SessionIDManager|CreateSessionID' .`
- [ ] **Is the session store private to the application (§2)? MEDIUM** — a shared temp
      directory or a Redis URL with no credentials (confirm the Redis is a session store):
      `grep -rniE 'session\.save_path[[:space:]]*=[[:space:]]*"?/(tmp|var/tmp)|redis://[a-z0-9.-]+(:[0-9]+)?(/[0-9]*)?["'\'' ]*$' .`
- [ ] **Does a session get created only after a user action (§2)? MEDIUM** — silent SSO on
      page load; read whether the hit opens a new session or only renews one:
      `grep -rniE 'prompt[[:space:]]*[=:][[:space:]]*.?none|check-sso|silentCheckSso' .`
- [ ] **Are idle and absolute timeouts documented, risk-tiered and computed from server time
      (§2)? HIGH when a client-sent time decides expiry** —
      `grep -rniE '(req|request)\.(body|query|params|headers|cookies|form|args|json)[^;]{0,40}(last[_-]?(activity|seen)|login[_-]?(time|at)|session[_-]?(start|age)|client[_-]?time)' .`
- [ ] **Does ending a session emit a lifecycle event, and does a revoked or expired ID
      presented again raise one at high severity (§2)? MEDIUM** — files that end sessions
      without naming an event:
      `grep -rliE 'session\.(destroy|invalidate|flush)\(|session_destroy\(|invalidate_session' . | while IFS= read -r f; do grep -qiE 'session_(expired|logout|revoked)|use_after_expire|security_event|audit' "$f" || echo "$f"; done`
- [ ] Is there a documented concurrent-session limit with defined behaviour at the limit and
      a logged exceedance, a user-facing session list with re-authenticated termination, an
      admin "end sessions" control, and a previous-login notice (§2)? MEDIUM.
- [ ] **Is a JWT used as the browser session backed by revocation (§3)? HIGH** — files that
      sign a JWT into a cookie and never mention `jti` or revocation:
      `grep -rlE 'jwt\.(sign|encode)\(' . | while IFS= read -r f; do grep -qiE 'set_cookie|\.cookie\(|cookies\.set|set-cookie' "$f" && ! grep -qiE 'jti|denylist|blocklist|revok' "$f" && echo "$f"; done`
- [ ] **Is RSASSA-PKCS1-v1_5 (`RS*`) used only for interop, and is each HMAC secret at least
      the hash length (§3)? LOW** — `grep -rnE '(^|[^A-Za-z0-9])RS(256|384|512)([^0-9]|$)' .`
- [ ] **Is sensitive data kept out of Web Storage (§3)? HIGH** —
      `grep -rniE '(localStorage|sessionStorage)\.setItem\([^)]*(token|jwt|secret|passw|session|api_?key|ssn|card)' .`
- [ ] **Do browser apps keep OAuth tokens server-side behind a backend-for-frontend (§3)?
      MEDIUM** — refresh tokens handled in frontend components:
      `grep -rniE 'refresh_?token' --include='*.tsx' --include='*.jsx' --include='*.vue' --include='*.svelte' .`
