<!-- last-verified: 2026-07 -->

# 01 — Language baseline & idioms

Modern PHP is a strictly-typed language. Most legacy-PHP pain (type juggling,
register-globals folklore, `@` suppression) is opt-out today — these rules make
opting out the default.

## 1. Version baseline: know the support windows

Verified against php.net/supported-versions.php and php.net/releases (2026-07):

| Branch | Status | Active support until | Security fixes until |
|---|---|---|---|
| 8.2 | security-only | ended 2024-12-31 | **2026-12-31** |
| 8.3 | security-only | ended 2025-12-31 | 2027-12-31 |
| 8.4 | active | 2026-12-31 | 2028-12-31 |
| 8.5 | active (current stable, released 2025-11-20) | 2027-12-31 | 2029-12-31 |

- 8.1 and older are **EOL** (8.1's final release was 8.1.34, 2025-12; PHP 7 ended
  2022-11). Running them is a HIGH finding on internet-facing systems.
- Each branch gets 2 years active + 2 years security-only (php.net policy).
- **BUILD:** target 8.3+ as the floor for new projects (8.2 exits security support
  2026-12-31 — months away); use 8.4/8.5 features when the floor allows.
- **AUDIT:** check `composer.json` `require.php` and `config.platform.php` against
  the table; flag EOL floors and floors about to lapse.

Feature timeline for floor decisions: enums, `readonly` properties, fibers,
first-class callable syntax (8.1); `readonly` classes, DNF types (8.2); typed class
constants, `#[\Override]`, `json_validate()` (8.3); property hooks, asymmetric
visibility, `new X()->method()` without parens, bcrypt default cost 10→12 (8.4);
pipe operator `|>`, `clone with`, `#[\NoDiscard]`, `array_first`/`array_last`,
closures in constant expressions, URI extension (8.5, per php.net/releases/8.5).

## 2. strict_types and real types, everywhere

Without `declare(strict_types=1)`, scalar type declarations *coerce* ("42abc" may
pass an `int` parameter with a notice, `"1"` passes `bool`). With it, mismatches
throw `TypeError`.

```php
<?php

declare(strict_types=1);   // first statement, every file — no exceptions
```

- Every property, parameter, and return gets a type. `mixed` is a documented
  last resort, not a default; `?Type` over implicit-nullable (implicit nullable
  parameters are deprecated since 8.4).
- Use union/intersection/DNF types where they model reality
  (`(Countable&Traversable)|null`), not to paper over unclear design.
- `array` hides shape: for structured data prefer a small typed class (or at
  least a PHPDoc `array{id: int, name: string}` shape that PHPStan/Psalm check).
- Value objects: constructor promotion + `readonly`:

```php
final class Money
{
    public function __construct(
        public readonly int $amountMinor,
        public readonly Currency $currency,
    ) {}

    public function withAmount(int $amountMinor): self
    {
        return clone($this, ['amountMinor' => $amountMinor]); // 8.5 clone-with
        // pre-8.5: return new self($amountMinor, $this->currency);
    }
}
```

- 8.4+ property hooks replace getter/setter boilerplate; asymmetric visibility
  (`public private(set)`) replaces "public getter, private setter" pairs.

## 3. Enums over constants; match over switch

```php
enum OrderStatus: string          // backed enum when it's persisted/serialized
{
    case Pending = 'pending';
    case Shipped = 'shipped';
    case Cancelled = 'cancelled';
}

$status = OrderStatus::tryFrom($raw) ?? throw new InvalidArgumentException(
    sprintf('unknown status "%s"', $raw),
);
```

- `::from()` throws `ValueError` on unknown input; `::tryFrom()` returns null —
  choose deliberately at trust boundaries.
- Enums can carry methods and interfaces; use them instead of parallel
  `match`/lookup tables scattered around the codebase.

`match` beats `switch`: strict (`===`) comparison, no fallthrough, it's an
expression, and an unhandled value throws `\UnhandledMatchError` instead of
silently doing nothing:

```php
$label = match ($status) {
    OrderStatus::Pending   => 'In progress',
    OrderStatus::Shipped   => 'Done',
    OrderStatus::Cancelled => 'Cancelled',
};  // adding a case to the enum makes this throw until handled — good
```

Audit `switch` on security-relevant values as MEDIUM (loose comparison +
fallthrough hazards).

## 4. Comparison and juggling discipline

- `==` compares after juggling; **always `===`/`!==`** unless a comment justifies
  otherwise. Classic traps: `0 == "a"` was true before 8.0 (string-to-number
  comparison changed in PHP 8.0 — saner, but `"1" == "01"` is still true),
  `null == false == 0 == ""` are all true.
- `in_array($needle, $arr)` and `array_search` juggle by default — pass
  `strict: true`. `switch` juggles and cannot be fixed — prefer `match`.
- `strcmp()`-style return values and `0` are falsy: `if (strpos($s, $p))` is a
  bug when the needle is at offset 0 — use `str_contains`/`str_starts_with`
  (8.0+) or `!== false`.
- Never use `==` on anything security-relevant (tokens, hashes, MACs): juggling
  plus magic-hash pitfalls (`"0e123..." == "0e456..."`). Use `hash_equals()`
  (see `rules/04`).

## 5. Errors and exceptions, not silence

- Production ini: `display_errors=Off`, `log_errors=On`; development:
  `error_reporting(E_ALL)` and fail on warnings in tests. (OWASP PHP
  Configuration Cheat Sheet.)
- **No `@` suppression** — it hides the error *and* costs a handler round-trip.
  The only near-acceptable uses are APIs with no error-free variant; wrap those
  once and document.
- Throw exceptions; don't return `false|string` unions from new APIs. Define a
  small package-level exception hierarchy (`DomainException` subclasses), chain
  with `previous:`.
- `json_decode(..., flags: JSON_THROW_ON_ERROR)` — silent `null` returns are a
  classic injection/logic hazard. 8.3+ `json_validate()` for validate-only.
- Since 8.5, uncaught fatal errors include backtraces (php.net/releases/8.5) —
  make sure stack traces still never reach responses (`rules/04` §6).
- `DateTimeImmutable` over `DateTime`; pass an explicit `DateTimeZone`; never
  parse dates with juggling (`strtotime` on user input needs validation).

## 6. Fibers and concurrency (8.1+)

`Fiber` is a *low-level* cooperative-concurrency primitive: full-stack
interruptible functions (`Fiber::suspend()`/`resume()`). It does **not** make
code parallel and does not schedule anything by itself.

- Application code should not hand-roll fiber schedulers. Use an event-loop
  runtime built on fibers (e.g. Revolt/AMPHP v3, ReactPHP) where async I/O
  concurrency is genuinely needed.
- Classic FPM request/response code gains nothing from fibers — concurrency
  there is process-level (see `rules/06` FPM sizing). Long-running runtimes
  (CLI workers, e.g. FrankenPHP/Swoole-style servers as neutral examples) are
  where async PHP pays off; in those, blocking calls (`PDO`, `file_get_contents`)
  stall the whole loop — same discipline as any event loop.
- AUDIT: raw `new Fiber(` in application (non-library) code is a MEDIUM design
  smell; blocking I/O inside an event-loop callback is HIGH in async runtimes.

## 7. Deprecations and legacy constructs to remove on sight

- **Removed** (fail on modern PHP): `create_function` (8.0), string-argument
  `assert()` (8.0), `preg_replace` `/e` modifier (7.0), `mcrypt_*` (7.2),
  `each()` (8.0), curly-brace string offsets `$s{0}` (8.0).
- **Deprecated** (fix now): backtick operator `` `cmd` `` and `__sleep`/
  `__wakeup` (both deprecated in 8.5 — use `__serialize`/`__unserialize`),
  implicit nullable params (8.4), dynamic properties without
  `#[\AllowDynamicProperties]` (8.2).
- **Legacy smells:** `extract()` on request data (variable injection),
  variable-variables `$$name` from input, `global` keyword in new code,
  `array_merge` in loops (quadratic — use spreads/`array_push`),
  `register_shutdown_function` as error handling.

## Audit checklist

Run from repo root; verify each hit manually.

```bash
# Missing strict_types — LOW per file, MEDIUM if project-wide
grep -rL --include='*.php' 'declare(strict_types=1)' src/ | head -50

# EOL / lapsing PHP floor — check require.php against the table in §1
grep -n '"php"' composer.json
php -v

# Loose comparison on suspicious values — MEDIUM+, verify context
grep -rnE '[^=!<>]==[^=]' --include='*.php' src/ | grep -iE 'token|password|hash|hmac|secret|sig'
grep -rnE 'in_array\([^)]*\)' --include='*.php' src/ | grep -v 'true'

# strpos truthiness bug
grep -rnE 'if\s*\(\s*!?\s*strpos\(' --include='*.php' src/

# Error suppression and silent JSON
grep -rn '@' --include='*.php' src/ | grep -E '@\s*[a-z_]+\(' | grep -v '//'
grep -rn 'json_decode' --include='*.php' src/ | grep -v 'JSON_THROW_ON_ERROR'

# Removed/deprecated constructs
grep -rnE '(create_function|each\(|__sleep|__wakeup|\$\$[a-zA-Z]|extract\s*\(\s*\$_)' --include='*.php' src/
grep -rn '`' --include='*.php' src/ | grep -vE '(//|\*|#)'   # backtick exec

# Untyped properties (heuristic; rely on PHPStan level 6+ for the real sweep)
grep -rnE '^\s*(public|protected|private)\s+\$' --include='*.php' src/

# switch on request-derived values — prefer match
grep -rn 'switch\s*(' --include='*.php' src/
```

Severity guide: EOL PHP in production HIGH; missing strict_types project-wide
MEDIUM; loose `==` on security decisions HIGH; `@`-suppressed security function
HIGH; style-level items LOW/INFO.
