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

## 5. Attacker-chosen names: classes, session keys, properties

§2's ban list covers a *function* name taken from input. The same flaw has more PHP
spellings, and in each the attacker supplies a **name**, not a value:

```php
// BAD — the attacker names the class, the session key, or the property
$obj = new $_GET['type']($_GET['arg']);           // any autoloadable class's constructor runs
$row = $stmt->fetchObject($_GET['model']);        // fetchObject / PDO::FETCH_CLASS instantiate it
$_SESSION[$_POST['key']] = $_POST['value'];       // key "is_admin" overwrites the flag
foreach ($_POST as $k => $v) { $user->$k = $v; }  // mass assignment onto any property

// GOOD — input selects from a closed set; fields are named in code
$class = ['csv' => CsvExport::class, 'pdf' => PdfExport::class][$type]
    ?? throw new InvalidArgumentException('unknown export type');
$key = in_array($key, ['theme', 'locale'], true) ? $key : throw new InvalidArgumentException();
$_SESSION['prefs'][$key] = $value;
$user->email = $input['email'];
```

Measured on PHP 8.5.9:

- `new $class($path)` with `$class = 'SplFileObject'` read a file's first line, so the
  built-in classes alone make the name dangerous. The constructor runs before your code sees
  the object, so an `instanceof` check afterwards is too late.
- `PDOStatement::fetchObject('Probe')` ran `Probe::__construct`. A class name passed to
  `fetchObject()` or `PDO::FETCH_CLASS` is an instantiation sink.
- `$_SESSION[$k] = $v` with `$k = 'is_admin'` flipped the flag. Every later authorization check
  trusts the session, so a request-chosen key is **session poisoning**.
- Mass assignment is the same class through properties. Loops of `$obj->$k = $v` or
  `$obj->{$k} = $v` over request data, and framework guards switched off (e.g. Eloquent's
  `protected $guarded = [];`, which its docs describe as making every attribute mass
  assignable), are findings. The language-neutral rule is `sota-code-security` rules/07 §3.
- For local variables the same flaw is `extract()` and `$$name` (`rules/01` §7).

## 6. LDAP and XPath: PHP's escapers, and the empty password

The injection class is `sota-code-security` rules/01 (LDAP and XPath). This is PHP's spelling of it.

```php
// BAD — spliced filter/DN; an empty password turns the bind into an unauthenticated bind
if (ldap_bind($conn, "uid=$user,ou=people,dc=example,dc=org", $password)) { login($user); }

// GOOD
if ($password === '') { fail(); }   // before every ldap_bind() used as an auth check
$dn = 'uid=' . ldap_escape($user, '', LDAP_ESCAPE_DN) . ',ou=people,dc=example,dc=org';
$filter = '(uid=' . ldap_escape($user, '', LDAP_ESCAPE_FILTER) . ')';
```

- **An empty password does not fail the bind.** php.net `ldap_bind`: *"If password is not
  specified or is empty, an anonymous bind is attempted"*, and php-src passes the zero-length
  credential through unchecked. RFC 4513 section 5.1.2 calls this an *unauthenticated* bind. It says
  clients SHOULD refuse an empty password and servers SHOULD refuse the bind by default. Both are
  only SHOULD, so on a directory that accepts it, `if (ldap_bind(...))` logs in **any existing
  username with no password**. Reject `''` in code, before the bind.
- `ldap_escape()` takes its context as a flag: `LDAP_ESCAPE_FILTER` for `ldap_search()` filters
  and `LDAP_ESCAPE_DN` for DN components (php.net). Measured: `ldap_escape('*)(uid=*', '',
  LDAP_ESCAPE_FILTER)` gives `\2a\29\28uid=\2a`.
- **XPath has no bound parameters.** `DOMXPath::query()`/`evaluate()` take only an expression
  string (php.net class synopsis). Since **8.4**, `DOMXPath::quote()` returns a correctly quoted
  literal. Measured: the value `x' or '1'='1` matched 2 nodes spliced raw and 0 nodes through
  `DOMXPath::quote()`. On older floors, allowlist the value.

## Audit checklist

Run from repo root; verify each hit manually (greps are recall-oriented).

- [ ] **SQL built from strings — CRITICAL if user data reaches it** —
      `grep -rnE '(->query|->exec|_query)\s*\(\s*["'"'"'].*(\$|\bsprintf|\. )' --include='*.php' src/`
      ;
      `grep -rnE '(SELECT|INSERT|UPDATE|DELETE)[^;]*(\{\$|"\s*\.\s*\$|\'\s*\.\s*\$)' --include='*.php' -i src/`
      ;
      `grep -rnE '(whereRaw|selectRaw|orderByRaw|havingRaw|DB::raw|->raw\()' --include='*.php' src/`
      ; `grep -rn 'EMULATE_PREPARES' --include='*.php' src/` (want: false);
      `grep -rn 'real_escape_string' --include='*.php' src/` (HIGH if primary defense)
- [ ] **Shell — CRITICAL with tainted input** —
      `grep -rnE '\b(exec|shell_exec|system|passthru|popen|pcntl_exec)\s*\(' --include='*.php' src/`
      ; `grep -rn 'proc_open' --include='*.php' src/` (array command = good sign);
      ``grep -rn '`' --include='*.php' src/ | grep -vE '(//|\*|#)'`` ;
      `grep -rnE '\b(eval|assert)\s*\(\s*\$' --include='*.php' src/`
- [ ] **XSS — echo/print of request data, raw template sinks** —
      `grep -rnE '(echo|print|<\?=)[^;]*\$_(GET|POST|REQUEST|COOKIE|SERVER)' --include='*.php' .`
      ; `grep -rnE '<\?=[[:space:]]*\$' --include='*.php' templates/ | grep -vE '<\?=[[:space:]]*\$this'`
      (a `(?!this)` lookahead here exited 2 with its stderr discarded, so it reported nothing) ;
      `grep -rn '{!!' --include='*.blade.php' resources/ 2>/dev/null` ;
      `grep -rn '|raw' --include='*.twig' templates/ 2>/dev/null` ;
      `grep -rn 'strip_tags' --include='*.php' src/` (not an XSS defense)
- [ ] **Header/redirect injection** —
      `grep -rnE 'header\s*\(\s*["'"'"']Location:.*\$' --include='*.php' src/`
- [ ] **Log injection (§4) — MEDIUM** —
      `grep -rnE '(error_log|syslog|->(emergency|alert|critical|error|warning|notice|info|debug|log))[[:space:]]*\([^;]*\$_(GET|POST|REQUEST|COOKIE|SERVER)' --include='*.php' src/`
      (request data written straight into a log line; measured on PHP 8.5, `error_log()` to a
      file wrote an embedded `\n` through, so one call produced two log lines). Strip CR/LF or
      log it as a structured field. Values that reach the call via a variable need tracing
- [ ] **json_encode into <script> without hex flags** —
      `grep -rn 'json_encode' --include='*.php' src/ | grep -v 'JSON_HEX'`
- [ ] **Attacker-chosen class, session key or property (§5)** — trace each name to a literal or
      an allowlist:
      `grep -rnE 'new[[:space:]]+\$|fetchObject[[:space:]]*\([[:space:]]*\$|FETCH_CLASS' --include='*.php' src/`
      ; `grep -rnE '\$_SESSION[[:space:]]*\[[[:space:]]*\$' --include='*.php' src/` ;
      `grep -rnE -e '->\{?\$[A-Za-z_]+\}?[[:space:]]*=[^=]' -e 'guarded[[:space:]]*=[[:space:]]*\[[[:space:]]*\]' --include='*.php' src/`
- [ ] **LDAP and XPath (§6)** — is the password checked non-empty before every `ldap_bind` used
      as a login, and is every filter/DN value escaped with the right flag?
      `grep -rnE 'ldap_(bind|search|list|read)[[:space:]]*\(' --include='*.php' src/` ;
      `grep -rn 'ldap_escape' --include='*.php' src/ | grep -v 'LDAP_ESCAPE_'` ;
      `grep -rnE '(->query|->evaluate|->xpath)[[:space:]]*\([[:space:]]*["'"'"'](/|\.)[^;]*\$' --include='*.php' src/ | grep -v 'DOMXPath::quote'`

Severity guide: interpolated SQL or shell with user input CRITICAL; unescaped
output of request data HIGH; raw template sink with untraced source HIGH until
proven benign; missing hex flags on script-embedded JSON MEDIUM; escaping at
input time instead of output MEDIUM (design); a request-chosen class name HIGH (CRITICAL when
the constructor argument is request-chosen too, as in the file read above), a request-chosen
session key HIGH; an `ldap_bind` login that accepts an empty password CRITICAL
where the directory permits unauthenticated binds (HIGH until that is checked).