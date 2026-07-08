# 02 — Injection: SQL, shell, and XSS

Trust-boundary thinking: `$_GET`/`$_POST`/`$_COOKIE`/headers, uploaded files, DB
content, queue payloads, and LLM output are attacker-controlled until proven
otherwise. PHP's history is a catalog of interpolation bugs — the fix is always
the same: **keep data out of the code/query/markup channel.**

## 1. SQL: prepared statements with bound parameters, nothing else

String-interpolated SQL is CRITICAL regardless of the value's origin — "it comes
from our own table" is how second-order injection happens. (OWASP SQL Injection
Prevention Cheat Sheet: parameterized queries are defense #1.)

```php
// BAD — CRITICAL, even with (worse: because of) manual quoting/escaping
$rows = $pdo->query("SELECT * FROM users WHERE email = '" . $email . "'");
$rows = $pdo->query(sprintf("SELECT * FROM users WHERE id = %s", $id));

// GOOD — PDO named parameters
$stmt = $pdo->prepare('SELECT * FROM users WHERE email = :email');
$stmt->execute(['email' => $email]);
$user = $stmt->fetch();
```

PDO setup that makes the safe path the real path:

```php
$pdo = new PDO($dsn, $user, $password, [
    PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION, // default since 8.0
    PDO::ATTR_EMULATE_PREPARES   => false, // real server-side prepares
    PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
]);
```

- `ATTR_EMULATE_PREPARES => false` sends the statement and data separately
  (true separation, and typed results on mysqlnd). Emulated prepares are
  client-side string splicing — safe when used correctly, but one charset or
  driver quirk away from not being safe.
- **Identifiers can't be bound.** Table/column names and `ORDER BY ... ASC|DESC`
  from user input go through a hardcoded allowlist, never quoting:

```php
$col = ['name', 'created_at'][$idx] ?? 'created_at';
$dir = $desc ? 'DESC' : 'ASC';
$stmt = $pdo->prepare("SELECT * FROM users ORDER BY $col $dir LIMIT :n");
```

- `LIKE`: bind the parameter *and* escape wildcards in it —
  `addcslashes($term, '%_\\')` — or user input `%` scans the table.
- `IN (...)`: build exactly as many `?` placeholders as values; never implode
  values into the string.
- ORMs/query builders (e.g. Doctrine, Eloquent) parameterize by default, but
  their raw escape hatches don't: audit `->raw(`, `DB::raw(`, `whereRaw(`,
  `createNativeQuery`, string-concatenated DQL. Same rule applies inside them.
- `mysqli`: same discipline (`prepare`/`bind_param`). Any use of
  `mysqli_real_escape_string` as the *primary* defense is a finding (HIGH):
  it's charset-sensitive and doesn't help outside quoted string context.

## 2. Command execution: no shell between you and the binary

Prefer no process at all (native functions, extensions). When you must run one:

```php
// BAD — CRITICAL with any user-influenced part
shell_exec("convert $input out.png");
system('ping -c1 ' . $host);
$out = `ls $dir`;               // backticks = shell_exec; deprecated in 8.5

// GOOD — argv array, no shell involved (proc_open array mode, 7.4+)
$p = proc_open(['convert', $input, 'out.png'], $spec, $pipes);

// Acceptable when a shell string is unavoidable: escape EVERY argument
$cmd = 'ping -c1 ' . escapeshellarg($host);
```

- `proc_open` with an **array** command bypasses the shell entirely — the
  strongest option (php.net proc_open). Symfony Process (array syntax) is a
  neutral-example wrapper doing the same.
- `escapeshellarg()` escapes one argument; `escapeshellcmd()` escapes a whole
  command *but leaves argument splitting possible* — it is not a substitute.
- Watch argument injection even with perfect quoting: a value starting with `-`
  becomes an option. Prepend `--` where the tool supports it, or validate shape.
- `mail()`: the 4th/5th parameters historically enabled header/argument
  injection — validate/drop user input there; prefer a mailer library (e.g.
  Symfony Mailer) as a neutral example.
- Ban list for user-reachable paths: `eval()`, `assert()` with dynamic input,
  `preg_replace_callback` with attacker-chosen callables, `call_user_func`/
  variable functions `$fn()` where `$fn` derives from input, `unserialize`
  (see `rules/03`).

## 3. XSS: escape at output, for the exact context

Escaping at *input* time is the classic mistake — data gets double-escaped,
mis-escaped for the context, or bypassed by a second write path. Store raw,
escape at the sink. (OWASP Cross Site Scripting Prevention Cheat Sheet.)

**HTML body and attribute context:**

```php
// BAD — HIGH
echo "<p>Hello {$_GET['name']}</p>";

// GOOD — the one true incantation; wrap it in a helper e()
echo '<p>Hello ', htmlspecialchars($name, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8'), '</p>';
```

- `ENT_QUOTES` covers single-quoted attributes; `ENT_SUBSTITUTE` prevents
  invalid-UTF-8 from truncating output; the explicit `'UTF-8'` pins the charset
  (default since 5.4, pin it anyway). Attribute values must also be *quoted* in
  the markup — escaping alone doesn't save `<img src=x onerror=...>` in an
  unquoted attribute.
- `htmlentities` is not more secure, just noisier; `strip_tags` is not an XSS
  defense (attributes survive, and it destroys data).

**JavaScript context:** never splice into script; pass via JSON with hex flags:

```php
<script>
const cfg = <?= json_encode($cfg, JSON_HEX_TAG | JSON_HEX_APOS | JSON_HEX_QUOT
    | JSON_HEX_AMP | JSON_THROW_ON_ERROR) ?>;
</script>
```

**URL context:** `rawurlencode()` for components; validate whole user-supplied
URLs — scheme allowlist (`https?`) — before emitting in `href` (blocks
`javascript:`). Redirect targets: allowlist or same-origin check (open
redirect, and see SSRF in `rules/03`).

**Templates:** use an auto-escaping engine — e.g. Twig (`autoescape` on by
default) or Blade `{{ }}` — and treat the raw syntaxes (`|raw`, `{!! !!}`,
`<?= $x ?>` in plain PHP templates) as audit targets: every one needs a proven
non-user-controlled source. Plain-PHP templates escape via a project-wide `e()`
helper; naked `<?=` of a variable is a finding until traced.

**Rich text** (user HTML): sanitize with a real allowlist sanitizer — e.g.
`Symfony\Component\HtmlSanitizer` or HTML Purifier as neutral examples — never
regex/`strip_tags`.

**Defense in depth:** a strict `Content-Security-Policy` (see `rules/04` §6)
and `X-Content-Type-Options: nosniff` cap the blast radius; they don't replace
escaping.

## 4. Header and log injection

- `header()` rejects CR/LF since PHP 5.1.2 (response splitting), but building
  headers from input still enables open redirects (`Location: $_GET['next']`)
  and cache poisoning — validate/allowlist values.
- Strip `\r`/`\n` from user data before writing to line-oriented logs, or log
  structured JSON; otherwise attackers forge log entries.

## Audit checklist

Run from repo root; verify each hit manually (greps are recall-oriented).

```bash
# SQL built from strings — CRITICAL if user data reaches it
grep -rnE '(->query|->exec|_query)\s*\(\s*["'"'"'].*(\$|\bsprintf|\. )' --include='*.php' src/
grep -rnE '(SELECT|INSERT|UPDATE|DELETE)[^;]*(\{\$|"\s*\.\s*\$|\'\s*\.\s*\$)' --include='*.php' -i src/
grep -rnE '(whereRaw|selectRaw|orderByRaw|havingRaw|DB::raw|->raw\()' --include='*.php' src/
grep -rn 'EMULATE_PREPARES' --include='*.php' src/    # want: false
grep -rn 'real_escape_string' --include='*.php' src/  # HIGH if primary defense

# Shell — CRITICAL with tainted input
grep -rnE '\b(exec|shell_exec|system|passthru|popen|pcntl_exec)\s*\(' --include='*.php' src/
grep -rn 'proc_open' --include='*.php' src/           # array command = good sign
grep -rn '`' --include='*.php' src/ | grep -vE '(//|\*|#)'
grep -rnE '\b(eval|assert)\s*\(\s*\$' --include='*.php' src/

# XSS — echo/print of request data, raw template sinks
grep -rnE '(echo|print|<\?=)[^;]*\$_(GET|POST|REQUEST|COOKIE|SERVER)' --include='*.php' .
grep -rnE '<\?=\s*\$(?!this)' --include='*.php' templates/ 2>/dev/null
grep -rn '{!!' --include='*.blade.php' resources/ 2>/dev/null
grep -rn '|raw' --include='*.twig' templates/ 2>/dev/null
grep -rn 'strip_tags' --include='*.php' src/          # not an XSS defense

# Header/redirect injection
grep -rnE 'header\s*\(\s*["'"'"']Location:.*\$' --include='*.php' src/

# json_encode into <script> without hex flags
grep -rn 'json_encode' --include='*.php' src/ | grep -v 'JSON_HEX'
```

Severity guide: interpolated SQL or shell with user input CRITICAL; unescaped
output of request data HIGH; raw template sink with untraced source HIGH until
proven benign; missing hex flags on script-embedded JSON MEDIUM; escaping at
input time instead of output MEDIUM (design).
