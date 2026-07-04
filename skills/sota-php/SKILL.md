---
name: sota-php
description: >-
  State-of-the-art PHP engineering (2026 baseline, PHP 8.3+ floor, 8.5 current) for both
  writing new PHP and auditing existing PHP code. Covers strict_types and modern idioms
  (enums, readonly, match, fibers, property hooks), OWASP-grade security (SQL injection,
  XSS, file uploads, LFI/RFI, unserialize/Phar object injection, sessions, password
  hashing, sodium, SSRF), framework-neutral web hardening, Composer supply chain and
  static analysis (PHPStan/Psalm levels, baselines), and runtime performance (OPcache,
  preloading, FPM tuning, JIT, N+1). Use whenever the task involves PHP source,
  composer.json, php.ini, FPM config, or a PHP framework — building features,
  scaffolding projects, reviewing PRs, or hunting bugs and vulnerabilities.
  Trigger keywords: PHP, composer, Laravel, Symfony, WordPress, PHPStan, Psalm, PHPUnit,
  Pest, PDO, php-fpm, OPcache, strict_types, phar, unserialize, htmlspecialchars.
---

# SOTA PHP (2026)

## Purpose

This skill encodes the 2026 state of the art for PHP: a supported-version baseline
(PHP 8.3+ floor, 8.5 current stable — see `rules/01`), `strict_types` everywhere, typed
object-oriented design, security-by-default at every trust boundary, a locked and audited
Composer supply chain, and measured runtime performance. It serves two modes:

- **BUILD** — writing new code or modifying existing code to this standard.
- **AUDIT** — reviewing existing code against this standard and reporting findings.

The detailed rules live in `rules/*.md`. Read SKILL.md fully; load rules files on demand
per the index table below.

## BUILD mode

When creating or modifying PHP code:

1. **Establish context first.** Check `composer.json` (`require.php`, `config.platform`),
   `composer.lock`, the framework in use, PHPStan/Psalm config, and CS ruleset. Match the
   project's PHP floor — no enums on a project that still supports 8.0. For a *new*
   project, scaffold per `rules/05`: PHP ≥ 8.3 floor, committed lockfile, PHPStan at max
   level (baseline only for legacy), PER-CS formatting, CI gates from day one.
2. **Default style:** `declare(strict_types=1)` in every file, full parameter/return/
   property types, constructor promotion, `readonly` where state shouldn't mutate, enums
   over class constants, `match` over `switch`, exceptions over error codes, no `@`
   suppression. (`rules/01`)
3. **Security posture is non-optional** even when unrequested: PDO prepared statements,
   context-correct output escaping, upload validation by content, no `unserialize()` on
   external data, `password_hash`/`sodium`/`random_bytes` for anything secret.
   (`rules/02`–`rules/04`)
4. **Framework first.** When a framework is present (e.g. Laravel, Symfony), use its
   escaping, CSRF, auth, and validation mechanisms instead of hand-rolling — but verify
   raw-escape hatches (`DB::raw`, `|raw`, `html()`) aren't fed user input.
5. **Tests accompany code** (PHPUnit or Pest as the project dictates); static analysis
   and CS must pass before code is presented. (`rules/05`)
6. **Performance:** OPcache assumptions belong in deploy config, not code; anything
   beyond correct-by-default (eager loading, streaming, generators) requires a profile
   first. (`rules/06`)

## AUDIT mode

When reviewing existing PHP code:

1. **Sweep mechanically first.** Run the "Audit checklist" blocks at the end of every
   relevant rules file — ordered grep/composer/phpstan commands. Start with
   `composer audit --locked` and a grep sweep for `unserialize(`, `eval(`, `shell_exec`,
   string-interpolated SQL, and `echo $_`.
2. **Then read for design:** trust-boundary placement, escaping strategy (output-time or
   scattered?), session lifecycle, N+1 patterns, lockfile discipline.
3. **Verify every finding** — open the file, trace the data flow. An `unserialize()` of a
   value the same app signed with HMAC is not CRITICAL. Note mitigations already present.
4. **Don't report style noise** a fixer would auto-fix; mention once collectively.

### Severity conventions

| Severity | Meaning | Examples |
|---|---|---|
| CRITICAL | Exploitable now, or data loss | SQL built by interpolation from request data, `unserialize($_GET…)`, `include` of user path, `eval` on input, uploads executed as PHP |
| HIGH | Exploitable with preconditions, or prod-breaking | XSS via unescaped output, `md5()` passwords, missing `use_strict_mode`/fixation, SSRF fetch of user URL, `CURLOPT_SSL_VERIFYPEER => false`, world-readable secrets |
| MEDIUM | Correctness/maintenance risk | no lockfile committed, no `composer audit` in CI, loose `==` on security decisions, `rand()` for tokens in non-auth context, N+1 on hot path, no static analysis |
| LOW | Deviation from SOTA, friction | missing `strict_types`, untyped properties, `switch` where `match` fits, dev deps in prod image |
| INFO | Worth knowing | newer-PHP features available after floor bump, tooling consolidation |

### Finding format

```
file:line | rule violated (rules/NN §S) | severity | effort | fix
```

Effort: trivial · small · medium · large. Group by severity, CRITICAL first. Borderline
severities state the deciding assumption; unconfirmed findings are marked "needs
verification", never asserted. End with counts per severity, the sweep commands run, and
explicit "checked and clean" areas.

## Rules index

| File | Read this when... |
|---|---|
| `rules/01-language-baseline.md` | choosing/verifying PHP version floor (support/EOL table); writing any PHP: strict_types, typed properties, enums, readonly, match, fibers, 8.4/8.5 features, comparison pitfalls, error handling, deprecations |
| `rules/02-injection.md` | code touching SQL, shell, or HTML output: PDO prepared statements, command execution, XSS and context-aware escaping, template engines, eval-family bans |
| `rules/03-files-deserialization-ssrf.md` | file uploads, include/require paths, stream wrappers (LFI/RFI/`phar://`), `unserialize` and Phar object injection, XXE, server-side URL fetching (SSRF) |
| `rules/04-sessions-auth-web-hardening.md` | login/session/auth code: session cookie flags and fixation, password_hash/argon2id, sodium crypto, CSRF, security headers, production php.ini hardening |
| `rules/05-composer-tooling.md` | dependencies and CI: composer.lock discipline, `composer audit`, platform reqs, PHPStan/Psalm levels and baseline ratcheting, PER-CS, PHPUnit/Pest, CI gates |
| `rules/06-performance-runtime.md` | anything slow or deploy-shaped: OPcache and preloading, JIT reality check, PHP-FPM pool sizing, N+1/caching, autoloader optimization, profiling. **Test *strategy* lives in `sota-testing`; DB depth in `sota-databases`.** |

## Top-10 non-negotiables

1. **Run a supported PHP** (≥ 8.2 today, and 8.2 is security-only until 2026-12-31 —
   plan the 8.3+ move now); new code targets 8.3+. (`rules/01`)
2. **`declare(strict_types=1)` in every file; full types on every property, parameter,
   and return.** Untyped is legacy, not a style choice. (`rules/01`)
3. **SQL only via prepared statements with bound parameters** (PDO/mysqli, emulation
   off); identifiers via allowlist. String-built SQL is CRITICAL, no exceptions for
   "internal" values. (`rules/02`)
4. **Escape at output, for the right context** — `htmlspecialchars(…, ENT_QUOTES |
   ENT_SUBSTITUTE, 'UTF-8')` or the template engine's auto-escaping; raw-output escape
   hatches never receive user input. (`rules/02`)
5. **Never `unserialize()`, `eval()`, or `include`/`require` data you don't fully
   control.** External data is JSON. Filter user paths for `phar://` and friends.
   (`rules/03`)
6. **Uploads: validate by content, rename randomly, store non-executable** — never trust
   client filename or MIME; never let the webserver execute uploads. (`rules/03`)
7. **Passwords via `password_hash()` (bcrypt default, or argon2id) + `password_verify`;
   secrets via `random_bytes`/`sodium`; compare with `hash_equals`.** Never md5/sha1/
   `rand()`/`uniqid()` for anything secret. (`rules/04`)
8. **Sessions hardened:** `use_strict_mode=1`, cookies `Secure` + `HttpOnly` +
   `SameSite`, `session_regenerate_id(true)` on privilege change. (`rules/04`)
9. **`composer.lock` committed; CI runs `composer install` (never `update`) and
   `composer audit --locked`; prod installs `--no-dev`.** (`rules/05`)
10. **PHPStan (or Psalm) gates CI at the highest level the project can hold; the
    baseline only shrinks. OPcache on in prod; performance claims require a profile.**
    (`rules/05`, `rules/06`)
