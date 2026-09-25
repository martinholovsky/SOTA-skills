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
session.use_cookies      = 1       ; the cookie is the only carrier (built-in default)
session.use_trans_sid    = 0       ; no ID rewritten into URLs/forms (default)
session.auto_start       = 0       ; the app, or its framework, starts the session
session.name             = app_sid ; not PHPSESSID, which names the stack
session.save_path        = /var/lib/app-sessions  ; this pool's own dir, mode 0700
```

- `use_cookies`, `use_trans_sid` and `auto_start` already default to `1`, `0`, `0` (read with
  `php -n` on 8.5.9; `php.ini-production` sets the same); pin them anyway, because a hosting
  profile or a per-directory override can flip them. `use_trans_sid=1` puts the ID in URLs,
  where logs and `Referer` headers carry it. `auto_start=1` starts a session at request startup,
  before any application code runs, so a framework that manages sessions itself (e.g. Symfony)
  no longer controls how, or whether, that session is created.
- The default name `PHPSESSID` tells a scanner the stack; rename it. A cheap hardening step,
  not a control.
- `save_path` defaults to empty, so the files handler falls back to the system temp directory,
  shared with every other process on the host. Give each application its own directory, owned by
  its FPM user and closed to everyone else; a store shared between applications lets one read or
  plant another's sessions (`sota-code-security` rules/17 §2).
- `session.referer_check` (empty by default) only rejects a request whose `Referer` lacks a
  substring. Clients omit or strip that header, so treat it as an optional extra and never as a
  fixation defence.
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
- OWASP (the directives after `sid_length`): PHP Configuration cheat sheet, Symfony cheat sheet.

## 1a. Cookies the app sets itself: `setcookie()` has none of §1's defaults

The `session.cookie_*` directives govern **the session cookie only**. Every `setcookie()` or
`setrawcookie()` call carries its own attributes. The positional form defaults to
`secure = false` and `httponly = false`, and has **no SameSite parameter at all** (read by
reflection on PHP 8.5.9).

```php
// BAD — measured: sent `Set-Cookie: remember=tok123`, with no Secure, HttpOnly or SameSite,
// in a request that had session.cookie_secure/httponly/samesite all set
setcookie('remember', $token);

// GOOD — the options array (7.3+); host-only, so no 'domain'; __Host- prefix
setcookie('__Host-remember', $token, [
    'expires'  => time() + 60 * 60 * 24 * 30,
    'path'     => '/',
    'secure'   => true,
    'httponly' => true,
    'samesite' => 'Lax',
]);
```

- Leave `domain` unset unless subdomains must read the cookie. Setting it widens the cookie
  from this host to every subdomain (RFC 6265 section 5.3: no Domain attribute means a host-only
  cookie).
- Request data never chooses a cookie's **name**. A request value copied into an auth-bearing
  cookie is session fixation (§1). This is Psalm's `TaintedCookie`.
- Framework cookie settings (e.g. a session config's `secure` / `http_only` / `same_site`) are
  the same attributes. Check the effective values, as for §1.

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
- **Never re-encode a token with `base_convert()`.** It converts through a float (php.net
  warns it *"may lose precision on large numbers"*), so only the leading ~53 bits survive.
  Measured on 8.5.9: 1,000 `random_bytes`-derived tokens that shared their top 64 bits gave
  **one** distinct base-36 output. Use `bin2hex()` or `sodium_bin2base64()`, or GMP
  (`gmp_strval(gmp_init($hex, 16), 36)`) when you need a particular alphabet.
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
- **The framework application key is a production secret.** One value keys most of the
  framework's integrity checks, so whoever holds it can forge or decrypt most of them. Read in
  source: Laravel 12's `APP_KEY` builds the encrypter behind encrypted cookies, keys signed URLs,
  and is the HMAC key that mints password-reset tokens; Symfony 7.3's `APP_SECRET`
  (`kernel.secret`) keys the URI signer, remember-me cookies and login links. Generate it per
  environment from a CSPRNG (Laravel: `php artisan key:generate`), inject it from a secret
  store, never commit it or share it between environments, and rotate through the framework's
  mechanism (Laravel: `APP_PREVIOUS_KEYS`). Neither framework refuses to boot without
  it: the skeletons ship it empty (`.env.example` `APP_KEY=`; the Symfony recipe's `.env`
  `APP_SECRET=`), and the error (`MissingAppKeyException`, or Symfony's non-empty-parameter
  check) fires only when something first uses it. Assert it at boot beside the debug check in §5b.
  See sota-secrets-management `rules/03` §2 and §6. OWASP: Laravel cheat sheet.

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
error_reporting = E_ALL            ; report everything, display nothing
html_errors = Off                  ; no HTML-formatted messages or doc links
error_log = /var/log/app/php_error.log  ; outside the docroot; or syslog/stderr
ignore_repeated_errors = Off       ; a repeating error is a signal, keep each
expose_php = Off                   ; drop X-Powered-By
allow_url_include = Off
allow_url_fopen = Off              ; unless remote fetch is a real requirement
open_basedir = /srv/app            ; coarse containment fence
doc_root = /srv/app/public
include_path = "/srv/app/lib"
extension_dir = /usr/lib/php/modules  ; root-owned, not writable by the FPM user
enable_dl = Off                    ; or add dl to disable_functions
variables_order = "GPCS"           ; no $_ENV superglobal
file_uploads = Off                 ; only when the app accepts no uploads
upload_tmp_dir = /var/lib/app/upload-tmp  ; when it does: private, not the docroot
disable_functions = exec,passthru,shell_exec,system,proc_open,popen,pcntl_exec,phpinfo
                                   ; tailor to what the app truly needs
```

- **Errors: keep reporting, stop displaying, and read the log.** The built-in `error_reporting`
  default is `E_ALL`, but `php.ini-production` ships `E_ALL & ~E_DEPRECATED`; set `E_ALL` so
  deprecations reach the log before an upgrade turns them into breakage. `html_errors` is On
  by default outside the CLI (read on 8.5.9 under `php-cgi -n`). With `error_log` unset,
  messages go to the SAPI error logger (php.net: e.g. Apache's error log, or stderr in
  the CLI), which is often nobody's dashboard. Name a destination, then
  ship it to the log pipeline and alert on it (sota-observability). A log that is written and
  never read is not a control. `ignore_repeated_errors` defaults to Off; leave it Off, because
  deduplicating hides the rate of an attack that repeats one error.
- **The rest of the surface.** `enable_dl` defaults to On (read on 8.5.9); `dl()` only works in
  the CLI, embed and command-line CGI SAPIs (php.net `dl`), so this closes the CLI and worker
  side. `variables_order` defaults to `EGPCS`; `GPCS` stops populating `$_ENV` (checked on 8.5.9), so environment
  secrets do not sit in a superglobal that a debug dump prints (`getenv()` still works).
  `include_path`, `extension_dir` and `doc_root` belong beside `open_basedir`: set them to
  explicit, root-owned paths so an include or extension load cannot resolve somewhere the app
  user can write. `file_uploads = Off` removes multipart parsing from an app that takes no
  files; one that does gets its own `upload_tmp_dir` (`rules/03` §1).
- `allow_webdav_methods` is not a PHP directive now: `ini_get()` returns `false` for it on
  8.5.9. Older checklists still list it. Do not set it, and do not count its absence as a gap.
- OWASP: PHP Configuration cheat sheet.

- `disable_functions` is defense in depth against webshells/RCE pivots — build
  the list from what the app *doesn't* use, and keep CLI workers on a separate
  ini if they need more.
- Run PHP-FPM as a dedicated non-root user; app files not writable by that
  user (a writable webroot turns any file-write bug into RCE); secrets in env/
  secret manager, not in webroot files (`.env` must be denied by the webserver
  — better, outside the docroot entirely).
- Uncaught exceptions must map to a generic 500 page; the chain goes to logs
  only (`rules/01` §5).
- **Per-request resource caps** are the outer DoS guard: `memory_limit`,
  `max_execution_time`, `max_input_vars`, `post_max_size`, `upload_max_filesize`. **The CPU
  limit is not a wall-clock limit.** php.net `set_time_limit`: time spent outside the script,
  such as system calls, stream operations and database queries, is not counted, except on
  Windows. Measured on 8.5.9, macOS and Linux: `sleep(3)` completed under
  `max_execution_time=1`, while a 3-second busy loop was killed. So a request-controlled
  `sleep()`/`usleep()` duration (Psalm's `TaintedSleep`) or a slow upstream holds an FPM
  worker for as long as it likes. The wall-clock bound is the pool's
  `request_terminate_timeout`, which defaults to `0` (off) (php.net FPM configuration). Set it,
  and clamp any duration taken from input.

## 5a. Secrets that reach output: stack-trace arguments and `phpinfo()`

A stack trace records **every argument** of every frame, and logs keep it.

```php
function connect(string $dsn, string $user, #[\SensitiveParameter] string $password): PDO
```

- Measured on 8.5.9 with `zend.exception_ignore_args=0`: `getTraceAsString()` printed
  `login2('bob', 'hunter2')`. With `#[\SensitiveParameter]` (8.2+) the same frame printed
  `Object(SensitiveParameterValue)`. Mark every password, key and token parameter.
- `zend.exception_ignore_args = On` drops arguments from traces entirely. Its **built-in default
  is Off** and only `php.ini-production` sets it On, along with
  `zend.exception_string_param_max_len = 0`.
- **The official PHP container image loads no `php.ini`.** Measured: `php --ini` reports
  `Loaded Configuration File: (none)`, and there `zend.exception_ignore_args` and
  `display_errors` read `0` and `1`. So neither §5's settings nor these apply until a deploy
  step copies `php.ini-production` or sets them. Check the effective values, never the file.
- `phpinfo()` prints the whole environment. Measured: a value set only in an environment
  variable appeared in its output, and the environment is where §5 tells you to keep secrets. It
  belongs on no reachable route: add it to `disable_functions` in production. A framework debug
  page is the same class (`sota-code-security` rules/07 §6).

## 5b. Debug mode and the development server

The framework's debug switch outranks `display_errors`: its error page renders the trace and the
configuration itself. The defaults point the wrong way for anyone who copies the dev setup.

- **Laravel:** `config/app.php` reads `'debug' => (bool) env('APP_DEBUG', false)`, but the
  skeleton's `.env.example`, which the installer copies to `.env`, ships `APP_ENV=local` and
  `APP_DEBUG=true`. The docs: *"If the variable is set to `true` in production, you risk exposing
  sensitive configuration values to your application's end users."*
- **Symfony:** with no `APP_ENV`, the Runtime component assumes `dev`, and `APP_DEBUG` defaults
  to on for every environment not listed in `prod_envs` (default `['prod']`) (read in
  `SymfonyRuntime.php`, 8.0 branch). So `APP_ENV=staging` runs with debug on. The docs: *"the web
  profiler must **never** be enabled in production"*; keep `symfony/web-profiler-bundle` and
  similar debug bundles in `require-dev`, so `composer install --no-dev` removes them.
- **The built-in server is not a production server.** `php -S`, and `php artisan serve`, which
  runs it, is single-threaded, and php.net says it *"should not be used on a public network"*.
  A container `CMD` that runs either is a finding. Serve through PHP-FPM or an application server.
- **Assert it at boot.** Fail startup when the environment says production and debug is on (e.g.
  `if ($env === 'prod' && $debug) { throw new LogicException('debug in production'); }` in the
  front controller or a service provider), and check the running app with a request that
  forces an error: the body must be the generic page, never a trace.

OWASP: Error Handling cheat sheet, Secure Headers Project; ASVS 5.0 V13.4.

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

- [ ] **Session config — effective values, not file greps alone** —
      `php -r 'foreach (["use_strict_mode","use_only_cookies","cookie_secure","cookie_httponly","cookie_samesite"] as $k) echo "session.$k=", ini_get("session.$k"), PHP_EOL;'`
      ; `grep -rn 'session_regenerate_id' --include='*.php' src/` (absent near login = HIGH);
      `grep -rnE 'session_id\s*\(\s*\$' --include='*.php' src/` (attacker-settable ID)
- [ ] **Session ini overrides (§1) — MEDIUM (HIGH for `use_trans_sid` on)** — each hit sets
      URL IDs, auto-start, the default name or a shared temp dir:
      `grep -rniE 'session\.(use_trans_sid[]"]?[[:space:]]*[[:space:]=][[:space:]]*"?(1|on)|use_cookies[]"]?[[:space:]]*[[:space:]=][[:space:]]*"?(0|off)|auto_start[]"]?[[:space:]]*[[:space:]=][[:space:]]*"?(1|on)|name[]"]?[[:space:]]*[[:space:]=][[:space:]]*"?PHPSESSID|save_path[]"]?[[:space:]]*[[:space:]=][[:space:]]*"?(/tmp|/var/tmp))' --include='*.ini' --include='*.conf' --include='.htaccess' --include='.user.ini' .`
      ; no hit is not a pass — read the effective values: `php -r 'foreach (["use_cookies","use_trans_sid","auto_start","name","save_path"] as $k) echo "session.$k=", ini_get("session.$k"), PHP_EOL;'`
- [ ] **App-set cookies (§1a)** — each hit lacks SameSite; the positional form cannot set it, so
      rewrite it to the options array with `secure`, `httponly` and `samesite` (a multi-line
      options array also shows up here: read it):
      `grep -rnE 'set(raw)?cookie[[:space:]]*\(' --include='*.php' src/ | grep -vi 'samesite'`
- [ ] **Password handling** —
      `grep -rnE '\b(md5|sha1|crypt)\s*\(' --include='*.php' src/ | grep -iE 'pass|pwd'` ;
      `grep -rn 'password_hash' --include='*.php' src/` ;
      `grep -rn 'password_needs_rehash' --include='*.php' src/` (absent = MEDIUM (stuck costs))
- [ ] **Weak randomness / timing-unsafe compares — HIGH where security-relevant** —
      `grep -rnE '\b(rand|mt_rand|uniqid|str_shuffle|array_rand)\s*\(' --include='*.php' src/` ;
      `grep -rnE '(===?)\s*\$.*(token|signature|hmac|hash)' -i --include='*.php' src/` ;
      `grep -rn 'hash_equals' --include='*.php' src/` ;
      `grep -rn 'base_convert' --include='*.php' src/` (on a token, key or ID = HIGH, §3)
- [ ] **Crypto** — `grep -rn 'mcrypt' --include='*.php' src/` (removed 7.2 — abandoned code);
      `grep -rnE "openssl_encrypt\([^)]*(cbc|ecb)" -i --include='*.php' src/` ;
      `grep -rn 'sodium_crypto' --include='*.php' src/`
- [ ] **Framework application key committed or hard-coded (§3) — CRITICAL for a production
      value** — a key in a tracked env file (`.example`, `.dist`, `.dev` and `.test` skipped):
      `git ls-files | grep -E '(^|/)\.env(\.[^/]*)?$' | grep -vE '\.(example|dist|dev|test)$' | while IFS= read -r f; do grep -nHE '^[[:space:]]*(APP_KEY|APP_SECRET)[[:space:]]*=[[:space:]]*[^[:space:]#]' "$f"; done`
      ; a literal in config or an image:
      `grep -rnE ''"'"'key'"'"'[[:space:]]*=>[[:space:]]*'"'"'base64:|^[[:space:]]*secret:[[:space:]]*["'"'"']?[^%"'"'"'[:space:]]|(ENV|ARG)[[:space:]]+APP_(KEY|SECRET)[[:space:]=]+[^[:space:]$]' --include='*.php' --include='*.yaml' --include='*.yml' --include='Dockerfile*' .`
      . A hit that was ever pushed is a leaked key: rotate it, do not just delete the line. Then
      check that boot fails when the key is empty in the deployed environment
- [ ] **CSRF — token verified centrally? exclusions?** —
      `grep -rnE '(csrf|_token)' -il --include='*.php' src/ | head` ;
      `grep -rn 'VerifyCsrfToken' -r app/ 2>/dev/null` (e.g. Laravel: check $except)
- [ ] **ini hardening + headers** —
      `php -r 'foreach (["display_errors","expose_php","allow_url_include","allow_url_fopen","open_basedir","disable_functions"] as $k) echo "$k=", ini_get($k), PHP_EOL;'`
      ;
      `curl -sI https://target/ | grep -iE 'content-security|strict-transport|x-content-type|x-powered-by'`
- [ ] **Error and attack-surface directives (§5) — MEDIUM (`display_errors` on in production
      per the severity guide)** — each hit turns on HTML errors, `dl()`, repeat suppression or
      error display, or keeps `E` in `variables_order`:
      `grep -rniE '^[^;#]*(html_errors|enable_dl|ignore_repeated_errors|display_errors)[]"]?[[:space:]]*[[:space:]=][[:space:]]*"?(1|on)|^[^;#]*variables_order[]"]?[[:space:]]*[[:space:]=][[:space:]]*"?[GPCS]*E' --include='*.ini' --include='*.conf' --include='.htaccess' --include='.user.ini' .`
      ; then the effective values, on the production image and SAPI (the CLI forces
      `html_errors` off): `php -r 'foreach (["error_reporting","html_errors","error_log","ignore_repeated_errors","enable_dl","variables_order","file_uploads","upload_tmp_dir","include_path","extension_dir","doc_root"] as $k) echo "$k=", ini_get($k), PHP_EOL;'`
      . An empty `error_log`, or one nothing ships and alerts on = MEDIUM
- [ ] **Resource caps, and a wall-clock bound (§5)** — `request_terminate_timeout` unset or `0`
      on a web pool = MEDIUM; a request-derived sleep duration = MEDIUM:
      `php -r 'foreach (["memory_limit","max_execution_time","max_input_vars","post_max_size","upload_max_filesize"] as $k) echo "$k=", ini_get($k), PHP_EOL;'`
      ; `php-fpm -tt 2>&1 | grep 'request_terminate_timeout ='` (the effective value per pool;
      the binary may carry a version suffix; measured default `0s`) ;
      `grep -rnE '(u|time_nano)?sleep[[:space:]]*\([^;]*\$' --include='*.php' src/`
- [ ] **Secrets reaching traces or `phpinfo()` (§5a)** — run on the production image, not a dev
      box: `php --ini | grep 'Loaded Configuration'` ;
      `php -r 'foreach (["zend.exception_ignore_args","zend.exception_string_param_max_len","display_errors"] as $k) echo "$k=", ini_get($k), PHP_EOL;'`
      ; `grep -rnE 'phpinfo[[:space:]]*\(' --include='*.php' .` ;
      `grep -rniE 'function[^(]*\([^)]*\$(pass(word)?|secret|token|api_?key|credentials?)' --include='*.php' src/ | grep -v 'SensitiveParameter'`
      (one-line signatures only: a signature split across lines, as PER-CS formats long ones,
      needs reading)

- [ ] **Debug mode or the development server in production (§5b) — HIGH** — `APP_DEBUG` on,
      a dev `APP_ENV`, or `php -S` / `artisan serve` in a deploy file:
      `grep -rnE 'APP_DEBUG.?[=:][[:space:]]*.?(true|1)([^0-9A-Za-z]|$)|APP_ENV.?[=:][[:space:]]*.?(dev|local)([^A-Za-z]|$)|php[0-9.]*.?,?[[:space:]]*.?-S[[:space:]"]|artisan.?,?[[:space:]]*.?serve' --include='.env*' --include='Dockerfile*' --include='*.yml' --include='*.yaml' --include='Procfile' .`
      . Values injected by the platform are not in the repo: read the running process's
      environment, and force an error on the live app to confirm the generic page

Severity guide: fixation (no strict mode + no regeneration) HIGH; md5/sha1
passwords HIGH; predictable tokens HIGH; missing CSRF on state change HIGH;
`display_errors=On` in prod MEDIUM (HIGH if traces confirmed reaching users);
missing CSP/headers MEDIUM; an auth-bearing `setcookie()` without `secure`/`httponly` HIGH;
`base_convert` on a token HIGH; reachable `phpinfo()` HIGH; `zend.exception_ignore_args` off
with unmarked secret parameters MEDIUM; a committed or hard-coded production application key
CRITICAL, an empty key with no boot-time check MEDIUM.