# 04 — Sessions, auth, crypto, and web hardening

Framework-neutral: whether sessions come from raw `session_start()` or a
framework layer (e.g. Laravel, Symfony), the same properties must hold — verify
them in *effective* config, not defaults you assume.

## 1. Session hardening

Required ini/effective settings (OWASP Session Management + PHP Configuration
Cheat Sheets; php.net session security manual):

```ini
session.use_strict_mode  = 1       ; reject attacker-supplied (uninitialized) IDs
session.use_only_cookies = 1       ; never accept IDs from URLs
session.cookie_secure    = 1       ; HTTPS-only cookie
session.cookie_httponly  = 1       ; no JS access
session.cookie_samesite  = Lax     ; Strict where UX allows
session.sid_length       = 48      ; entropy of the ID (pre-8.4 tunable)
```

- `use_strict_mode=1` is the **session fixation** kill switch — without it, PHP
  happily adopts any ID the attacker planted. Default is 0; always set it.
- **Regenerate on privilege change:** `session_regenerate_id(true)` immediately
  after login, logout, and role elevation. The `true` deletes the old session
  file; without regeneration, a pre-login ID stays valid post-login (fixation).
- Logout destroys server state: `$_SESSION = []; session_destroy();` plus
  expiring the cookie — not just a client-side redirect.
- Implement **idle timeout and absolute lifetime** in app logic (timestamps in
  the session); `gc_maxlifetime` is garbage collection, not access control.
- Bind sessions loosely to context (IP /24 or UA family) only if your users
  tolerate it; log mismatches either way.
- Never put secrets, roles, or prices in cookies/hidden fields; the session ID
  is the only client-held session artifact. Custom session storage (e.g. Redis)
  keeps the same rules.

## 2. Passwords: password_hash, nothing homemade

```php
$hash = password_hash($password, PASSWORD_DEFAULT);      // bcrypt today
// or, when compiled with Argon2 (or via libsodium):
$hash = password_hash($password, PASSWORD_ARGON2ID);

if (!password_verify($password, $hash)) fail();
if (password_needs_rehash($hash, PASSWORD_DEFAULT)) {
    // transparently upgrade cost/algorithm at successful login
    store(password_hash($password, PASSWORD_DEFAULT));
}
```

Verified against php.net password_hash (2026-07):

- `PASSWORD_DEFAULT` = bcrypt; **default bcrypt cost rose 10 → 12 in PHP 8.4**.
  The constant is designed to change — store hashes in the self-describing
  `$2y$`/`$argon2id$` format (password_hash does) and rely on
  `password_needs_rehash` for migrations.
- `PASSWORD_ARGON2ID` exists since 7.3 and requires Argon2 support compiled in
  (libargon2, or the sodium implementation since 7.4). OWASP Password Storage
  Cheat Sheet ranks argon2id first, bcrypt as the solid default; both are fine —
  `md5`/`sha1`/`sha256(+salt)`/`crypt()` for passwords are HIGH findings.
- bcrypt truncates at 72 bytes; since 8.4 PHP rejects longer inputs with
  `ValueError` rather than silently truncating — cap length in validation.
- Reset/verification tokens: `bin2hex(random_bytes(32))`, stored **hashed**
  (`hash('sha256', $token)`), single-use, short TTL.
- Compare any secret (tokens, HMACs, API keys) with **`hash_equals($known,
  $user)`** — `==`/`===` are timing-unsafe and `==` also has magic-hash
  juggling traps (`rules/01` §4).
- Rate-limit and lock out at the auth boundary; log failures. MFA/passkey and
  IdP architecture → sota-identity-access; app-level flows → sota-code-security.

## 3. General crypto: sodium first, random_bytes always

- **CSPRNG:** `random_bytes()` / `random_int()` only. `rand`, `mt_rand`,
  `array_rand`, `str_shuffle`, `uniqid()` (timestamp-based, even with
  `more_entropy`) are predictable — HIGH wherever the value gates anything.
  8.2+ `Random\Randomizer` with `Random\Engine\Secure` is fine (same source).
- **Authenticated encryption:** libsodium is in core since PHP 7.2 —
  `sodium_crypto_secretbox` (symmetric), `sodium_crypto_aead_xchacha20poly1305_ietf_*`,
  `sodium_crypto_box`/`sign` (asymmetric). New nonce per message
  (`random_bytes(SODIUM_CRYPTO_SECRETBOX_NONCEBYTES)`), keys from a secret
  manager, `sodium_memzero()` after use.
- If constrained to OpenSSL: AEAD only (`openssl_encrypt` with `aes-256-gcm`,
  checking/passing `$tag`); CBC without an HMAC is a padding-oracle finding.
  `mcrypt` was removed in 7.2 — its presence means abandoned code.
- Key derivation from passwords: `sodium_crypto_pwhash` or argon2id — never a
  bare hash of the password as key material.
- JWTs and OAuth flows: use a maintained library (e.g. lcobucci/jwt,
  web-token) — alg allowlist, `none` rejected; details in sota-code-security.

## 4. CSRF

State-changing requests need a CSRF defense; `SameSite` cookies are strong but
not sufficient alone (subdomain and same-site-scripting caveats — OWASP CSRF
Prevention Cheat Sheet recommends token + SameSite).

- Use the framework mechanism where present (e.g. Symfony form tokens, Laravel
  `@csrf`) — audit for routes excluded from verification.
- Hand-rolled: synchronizer token — `bin2hex(random_bytes(32))` in the session,
  embedded per-form, compared with `hash_equals`, rotated on login. Verify on
  every non-GET route, centrally (middleware), not per-handler.
- GET must never mutate state (also a CSRF hole via `<img src>`).

## 5. Production php.ini hardening

Per the OWASP PHP Configuration Cheat Sheet:

```ini
display_errors = Off               ; stack traces/paths leak internals
display_startup_errors = Off
log_errors = On
expose_php = Off                   ; drop X-Powered-By
allow_url_include = Off
allow_url_fopen = Off              ; unless remote fetch is a real requirement
open_basedir = /srv/app            ; coarse containment fence
disable_functions = exec,passthru,shell_exec,system,proc_open,popen,pcntl_exec
                                   ; tailor to what the app truly needs
```

- `disable_functions` is defense in depth against webshells/RCE pivots — build
  the list from what the app *doesn't* use, and keep CLI workers on a separate
  ini if they need more.
- Run PHP-FPM as a dedicated non-root user; app files not writable by that
  user (a writable webroot turns any file-write bug into RCE); secrets in env/
  secret manager, not in webroot files (`.env` must be denied by the webserver
  — better, outside the docroot entirely).
- Uncaught exceptions must map to a generic 500 page; the chain goes to logs
  only (`rules/01` §5).

## 6. Security headers

Set centrally (middleware or webserver), not per-page:

- `Content-Security-Policy` — nonce/hash-based `script-src`, `object-src
  'none'`, `frame-ancestors` (replaces `X-Frame-Options`); start
  `Content-Security-Policy-Report-Only`.
- `Strict-Transport-Security: max-age=31536000; includeSubDomains` once HTTPS
  is universal; cookies also `__Host-` prefixed where possible.
- `X-Content-Type-Options: nosniff`, `Referrer-Policy:
  strict-origin-when-cross-origin`, restrictive `Permissions-Policy`.
- CORS: explicit origin allowlist; `Access-Control-Allow-Origin: *` with
  credentials is invalid anyway — reflecting arbitrary Origins with
  credentials is the real-world HIGH.

## Audit checklist

Run from repo root; verify each hit manually.

```bash
# Session config — effective values, not file greps alone
php -r 'foreach (["use_strict_mode","use_only_cookies","cookie_secure","cookie_httponly","cookie_samesite"] as $k) echo "session.$k=", ini_get("session.$k"), PHP_EOL;'
grep -rn 'session_regenerate_id' --include='*.php' src/   # absent near login = HIGH
grep -rnE 'session_id\s*\(\s*\$' --include='*.php' src/   # attacker-settable ID

# Password handling
grep -rnE '\b(md5|sha1|crypt)\s*\(' --include='*.php' src/ | grep -iE 'pass|pwd'
grep -rn 'password_hash' --include='*.php' src/
grep -rn 'password_needs_rehash' --include='*.php' src/   # absent = MEDIUM (stuck costs)

# Weak randomness / timing-unsafe compares — HIGH where security-relevant
grep -rnE '\b(rand|mt_rand|uniqid|str_shuffle|array_rand)\s*\(' --include='*.php' src/
grep -rnE '(===?)\s*\$.*(token|signature|hmac|hash)' -i --include='*.php' src/
grep -rn 'hash_equals' --include='*.php' src/

# Crypto
grep -rn 'mcrypt' --include='*.php' src/                  # removed 7.2 — abandoned code
grep -rnE "openssl_encrypt\([^)]*(cbc|ecb)" -i --include='*.php' src/
grep -rn 'sodium_crypto' --include='*.php' src/

# CSRF — token verified centrally? exclusions?
grep -rnE '(csrf|_token)' -il --include='*.php' src/ | head
grep -rn 'VerifyCsrfToken' -r app/ 2>/dev/null            # e.g. Laravel: check $except

# ini hardening + headers
php -r 'foreach (["display_errors","expose_php","allow_url_include","allow_url_fopen","open_basedir","disable_functions"] as $k) echo "$k=", ini_get($k), PHP_EOL;'
curl -sI https://target/ | grep -iE 'content-security|strict-transport|x-content-type|x-powered-by'
```

Severity guide: fixation (no strict mode + no regeneration) HIGH; md5/sha1
passwords HIGH; predictable tokens HIGH; missing CSRF on state change HIGH;
`display_errors=On` in prod MEDIUM (HIGH if traces confirmed reaching users);
missing CSP/headers MEDIUM.
