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

- **Validation rules that name a table or column are the same sink.** A database-backed rule
  builds a query from its table, column and ignore arguments, e.g. Laravel's
  `Rule::unique('users')->ignore($id, $idColumn)`, `Rule::exists($table, $column)`, or the
  string forms `unique:table,column,except,idColumn` and `exists:table,column`. Request input
  never supplies the table or column: map it through the same hardcoded allowlist. The Laravel
  validation docs say the value passed to `ignore()` must be a system-generated ID (e.g. from the
  loaded model), never request input, or the rule is open to SQL injection. OWASP: Laravel cheat
  sheet.
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

## 2a. Dynamic code evaluation: `eval`, generated templates, expression engines

PHP turns a string into running code in more places than `eval()`. Each is a sink when any part
of the string comes from a request, a database row a user wrote, or an uploaded file:

- `eval($code)`, and `include`/`require` of a file the app just wrote (a generated "cache" or
  "compiled" PHP file whose contents carry input).
- **A template compiled from a string**: Twig `createTemplate($src)` or `template_from_string()`,
  or a Blade string rendered at runtime (`Blade::render($string)`). The template language
  reaches objects and methods, so a user-authored template is server-side template injection.
  Users choose *which* stored template renders, never its source.
- Callables named by input: `call_user_func($name)`, `$obj->$method()`, `new ReflectionMethod($o,
  $name)`. §5 below covers class names.

Two measured traps on 8.5.9: `disable_functions=eval` does not stop `eval()` (a language
construct, not a function; the code still ran), and a string passed to `assert()` is no longer
evaluated (removed in 8.0; `assert("1 === 2")` passed silently), so an old string assertion is a
check that never fires.

The safe shape is a **closed set**: a `match` or array of closures keyed by an allowlisted
name, or an expression library with a fixed grammar and a declared variable set (e.g. Symfony
ExpressionLanguage, whose docs call it *"a very restricted PHP sandbox"* and still say to
sanitize user data). Register no function that reaches the filesystem, the network or
`call_user_func`.

**An in-process sandbox is not a security boundary.** The GitHub Advisory Database lists 14
twig/twig advisories whose title names the sandbox, 11 published in 2026 (queried
2026-09-25, 34 twig/twig entries in all). Untrusted template or expression authors get a
separate process with no credentials (`sota-sandboxing`), or no template authoring at all.
OWASP: Code Review Guide, Proactive Controls 2024 C3; ASVS 5.0 V1.3.

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

## 4a. `header('Location')` does not stop the script (CWE-698)

Sending a `Location` header only queues a header. The script runs on, so everything after the
redirect still executes and its output is sent in the 302 body, which a browser hides and
`curl` shows. Measured on PHP 8.5 under `php -S`: a page that redirected unauthenticated users
with `header('Location: /login');` and no `exit` returned `302` and the admin page's body, and
the privileged write below the redirect ran.

- Follow every `header('Location: …')` on a guard path with `exit;` (or `return` from the only
  entry point), or better, throw an exception the front controller turns into the redirect.
- A framework redirect helper only **builds** a response object: Symfony's `redirectToRoute()`
  and Laravel's `redirect()` return a `RedirectResponse`. A controller that calls one without
  `return` sends nothing and carries on (read in Symfony 7.3 `AbstractController` and
  Laravel 12 `helpers.php`).
- Put authorisation in middleware or a guard that halts the request, not in an `if` that
  redirects and falls through.

OWASP: Unvalidated Redirects and Forwards cheat sheet.

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

## 7. Regular expressions: escape, anchor, bound, and check for `false`

A `preg_*` pattern that validates, allowlists, routes or redacts is a security control. A pattern
assembled from request data is an injection sink. The language-neutral rule is in
`sota-code-security` rules/01 §10 (ReDoS); this is the PHP spelling.

```php
// BAD — term spliced raw; `$` accepts "alice\n"; unbounded; false (error) read as "no match"
if (preg_match("/$term/i", $text)) { flag(); }
if (!preg_match('/^[a-z0-9_]+$/', $user)) { reject(); }

// GOOD
$re = '/' . preg_quote($term, '/') . '/i';        // pass the delimiter you actually use
if (strlen($user) > 32 || preg_match('/\A[a-z0-9_]{1,32}\z/', $user) !== 1) { reject(); }
```

- **Escape with `preg_quote($str, $delimiter)`.** It escapes the regex metacharacters and, only
  when you pass it, the delimiter: `/` is not a metacharacter, so `preg_quote('a/b')` leaves the
  slash raw and the value can close the pattern. `#` is escaped only since **7.3** (php.net
  changelog), which matters to a `#`-delimited pattern on older code. Prefer a literal-string
  function (`str_contains`, `strpos`) when no regex feature is needed.
- **Anchor to the whole input.** PCRE's `$` also matches just before a trailing newline, so
  `'/^[a-z]+$/'` accepts `"abc\n"`. Measured on 8.5: 1 match, but 0 with `\A...\z` or with the `D`
  modifier. The `m` modifier makes `^`/`$` line anchors and PHP ignores `D` under it: `'/^\d+$/m'`
  accepted `"abc\n<script>"`. An unanchored `preg_match` succeeds on any substring. Write
  `\A...\z`, and test the result with `=== 1`.
- **Bound the input and the pattern.** Cap the length (`strlen`/`mb_strlen`) before matching and
  use `{1,N}` rather than `+`/`*` in validators.
- **Engine: PCRE2 backtracks.** `preg_*` runs PCRE2 (10.47 in the measured build), a
  backtracking engine. JIT (`pcre.jit`, on by default) makes it faster, not linear. The guard is
  `pcre.backtrack_limit` (default 1000000) and `pcre.recursion_limit` (100000). They make
  `preg_match` return **`false`** and `preg_replace` return **`null`**, with
  `preg_last_error()` set to `PREG_BACKTRACK_LIMIT_ERROR`. That is **fail-open** wherever `false`
  is read as "no match". Measured: a denylist `if (preg_match('/^(a+)+$/', $in))` let
  `str_repeat('a', 30).'!'` through, and a redaction `preg_replace` returned `null`. Check
  `=== false`/`=== null` or `preg_last_error() !== PREG_NO_ERROR`, and treat an error as a
  rejection. Remove nested quantifiers with an atomic group `(?>...)` or a possessive `++`.
  Measured: `^(?>a+)+$` and `^(a++)+$` finished the same input in microseconds with no error.
  PHP has no built-in linear-time engine. Moving a pattern from an RE2-class engine (Go
  `regexp`, Rust `regex`) into `preg_*` gains backtracking, and so do the lookarounds and
  backreferences it now permits. Re-check such a pattern for nested quantifiers.

Sources: OWASP Input Validation cheat sheet; OWASP Proactive Controls 2024 C3; ASVS 5.0 V1.2.9;
OWASP Go-SCP (regular expressions, validation).

## 8. WordPress: core's escapers, and a capability behind every nonce

WordPress spells §1–§5 through its own API (developer.wordpress.org: Common APIs Handbook,
Security; Code Reference). The rules are the same; these are the names to look for.

- **SQL:** `$wpdb->prepare()` with unquoted `%d`, `%f`, `%s` and `%i` (identifier) placeholders,
  one argument each, and `$wpdb->esc_like()` on a value before wrapping it in `%` for `LIKE`. A
  variable spliced into `$wpdb->query()`, `get_results()`, `get_row()`, `get_var()` or
  `get_col()` is §1's CRITICAL.
- **Output:** escape late, at the `echo` (the handbook: *"escape when you echo, not before"*):
  `esc_html()` in element content, `esc_attr()` in attributes, `esc_url()` in `href`/`src`,
  `esc_js()` inline, `wp_kses()`/`wp_kses_post()` where some HTML is allowed.
- **Input:** `wp_unslash()`, then `sanitize_text_field()`, `sanitize_email()`, `sanitize_key()`
  or `absint()`. Sanitising on the way in never replaces escaping on the way out.
- **A nonce is a CSRF token, not authorization.** The handbook: nonces *"should never be relied
  on for authentication, authorization, or access control"*. Every state-changing admin form,
  `admin_post_*` and `wp_ajax_*` handler checks both a nonce (`check_admin_referer()`,
  `check_ajax_referer()` or `wp_verify_nonce()`) **and** `current_user_can('<capability>')`.
  `is_admin()` only says an admin screen was requested (Code Reference: *"Does not check if the
  user is an administrator"*), and `wp_ajax_nopriv_*` handlers run for logged-out visitors.
- **REST:** every `register_rest_route()` gets a `permission_callback` that calls
  `current_user_can()`. `__return_true` is the handbook's spelling for a *public* route; on one
  that writes, deletes or returns private data it is missing authorization.
- **No `unserialize()` or `maybe_unserialize()` of request, cookie or remote data.**
  `maybe_unserialize()` is `@unserialize(trim($data))` with no `allowed_classes` (Code Reference
  source), so it is `rules/03` §3 under another name. Use JSON across any trust boundary.

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
- [ ] **Request input in a database validation rule (§1) — HIGH, CRITICAL when it names the
      table or column** — request data in `Rule::unique`/`Rule::exists`/`->ignore()`, or a
      variable spliced into a `unique:`/`exists:` string (read each: a model's own ID is fine):
      `grep -rnE '(Rule::(unique|exists)\(|->ignore\()[^;]*(\$request|request\(|input\(|\$_(GET|POST|REQUEST))|["'"'"'][^"'"'"']*(unique|exists):[^"'"'"']*["'"'"'][[:space:]]*\.|"[^"]*(unique|exists):[^"]*\$' --include='*.php' src/`
- [ ] **Shell — CRITICAL with tainted input** —
      `grep -rnE '\b(exec|shell_exec|system|passthru|popen|pcntl_exec)\s*\(' --include='*.php' src/`
      ; `grep -rn 'proc_open' --include='*.php' src/` (array command = good sign);
      ``grep -rn '`' --include='*.php' src/ | grep -vE '(//|\*|#)'`` ;
      `grep -rnE '\b(eval|assert)\s*\(\s*\$' --include='*.php' src/`
- [ ] **Dynamic code evaluation and templates compiled from strings (§2a) — CRITICAL with input
      in the string, HIGH until traced** —
      `grep -rnE '(^|[^A-Za-z0-9_>:$])eval[[:space:]]*\(|createTemplate[[:space:]]*\(|template_from_string|Blade::render[[:space:]]*\(' --include='*.php' --include='*.twig' src/ templates/`
      (a method named `eval`, e.g. a Redis client's, is excluded). Trace each string to a
      literal; `disable_functions` does not cover `eval`
- [ ] **XSS — echo/print of request data, raw template sinks** —
      `grep -rnE '(echo|print|<\?=)[^;]*\$_(GET|POST|REQUEST|COOKIE|SERVER)' --include='*.php' .`
      ; `grep -rnE '<\?=[[:space:]]*\$' --include='*.php' templates/ | grep -vE '<\?=[[:space:]]*\$this'`
      (a `(?!this)` lookahead here exited 2 with its stderr discarded, so it reported nothing) ;
      `grep -rn '{!!' --include='*.blade.php' resources/ 2>/dev/null` ;
      `grep -rn '|raw' --include='*.twig' templates/ 2>/dev/null` ;
      `grep -rn 'strip_tags' --include='*.php' src/` (not an XSS defense)
- [ ] **Header/redirect injection** —
      `grep -rnE 'header\s*\(\s*["'"'"']Location:.*\$' --include='*.php' src/`
- [ ] **Execution after redirect (§4a) — HIGH on an authz path** — each hit is a `Location`
      header whose next non-blank line is not `exit`/`die`/`return`/`throw`:
      `find src/ -name '*.php' -exec awk 'FNR==1 && p {print pf":"pl": "ph} FNR==1 {p=0} p && /[^[:space:]]/ {if ($0 !~ /(exit|die|return|throw)/) print FILENAME":"pl": "ph; p=0} tolower($0) ~ /header[[:space:]]*\([[:space:]]*.location:/ && $0 !~ /(exit|die|return|throw)/ {p=1; pl=FNR; ph=$0; pf=FILENAME} END {if (p) print pf":"pl": "ph}' {} +`
      ; a framework redirect that is built and not returned:
      `grep -rnE '^[[:space:]]*(\$this->)?redirect(ToRoute)?[[:space:]]*\(' --include='*.php' src/ app/ 2>/dev/null`
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
- [ ] **Regex escaping, anchoring and engine limits (§7) — HIGH** — a variable spliced into a
      `preg_*` pattern without `preg_quote($v, $delim)`:
      `grep -rnE 'preg_[a-z_]+[[:space:]]*\([[:space:]]*("[^"]*\$[A-Za-z_{]|'"'"'[^'"'"']*'"'"'[[:space:]]*\.)' --include='*.php' src/ | grep -v 'preg_quote'`
      ; a `$`-anchored `/`-delimited validator without the `D` modifier (or under `m`), which
      accepts a trailing newline:
      `grep -rnE 'preg_match(_all)?[[:space:]]*\([[:space:]]*["'"'"'][^"'"'"']*\$/[a-zA-Z]*["'"'"']' --include='*.php' src/ | grep -vE '\$/[a-ln-zA-Z]*D[a-ln-zA-Z]*["'"'"']'`
      . Patterns held in variables or constants, and other delimiters, need tracing. For each
      security `preg_*` call, check that `false`/`null` (backtrack limit) is treated as a rejection
- [ ] **WordPress SQL outside `prepare()` (§8) — CRITICAL with request data** —
      `grep -rnE '\$wpdb->(query|get_results|get_row|get_var|get_col)[[:space:]]*\([[:space:]]*("[^"]*\$|[^;]*\.[[:space:]]*\$)' --include='*.php' --exclude-dir=vendor . | grep -v 'prepare'`
- [ ] **WordPress handler with no capability or nonce check (§8) — HIGH, CRITICAL when it
      mutates** — prints each file that registers an AJAX, admin-post or REST handler and never
      calls the check (a file not printed still needs its handlers read one by one):
      `grep -rlE "add_action[[:space:]]*\([[:space:]]*['\"](wp_ajax_|admin_post_)|register_rest_route[[:space:]]*\(" --include='*.php' --exclude-dir=vendor . | while IFS= read -r f; do grep -q 'current_user_can' "$f"; case $? in 0) ;; 1) echo "NO current_user_can: $f" ;; *) echo "SWEEP FAILED: $f" ;; esac; grep -qE 'wp_ajax_|admin_post_' "$f" && { grep -qE 'check_(admin|ajax)_referer|wp_verify_nonce' "$f"; case $? in 0) ;; 1) echo "NO NONCE CHECK: $f" ;; *) echo "SWEEP FAILED: $f" ;; esac; }; done`
      ; REST routes open to anyone (read each: a public read-only route is fine):
      `grep -rnE "permission_callback['\"]?[[:space:]]*=>[[:space:]]*['\"]__return_true" --include='*.php' --exclude-dir=vendor .`
- [ ] **WordPress unescaped output and deserialization (§8)** —
      `grep -rnE '(echo|<\?=)[[:space:]]*(\$|get_)' --include='*.php' --exclude-dir=vendor . | grep -vE 'esc_(html|attr|url|js|textarea|xml)|wp_kses|absint|intval'`
      ; `grep -rnE '(maybe_)?unserialize[[:space:]]*\(' --include='*.php' --exclude-dir=vendor . | grep -v 'allowed_classes'`
      (trace each argument: a request, cookie or remote value is CRITICAL)

Severity guide: interpolated SQL or shell with user input CRITICAL; unescaped
output of request data HIGH; raw template sink with untraced source HIGH until
proven benign; missing hex flags on script-embedded JSON MEDIUM; escaping at
input time instead of output MEDIUM (design); a request-chosen class name HIGH (CRITICAL when
the constructor argument is request-chosen too, as in the file read above), a request-chosen
session key HIGH; an `ldap_bind` login that accepts an empty password CRITICAL; an unescaped
request value in a `preg_*` pattern HIGH (CRITICAL on an authz or redaction path), a validator
that accepts a trailing newline or reads a `preg_*` error as "no match" MEDIUM
where the directory permits unauthenticated binds (HIGH until that is checked); code that runs
after a guard's redirect (§4a) HIGH, CRITICAL when it performs the privileged action; a
WordPress handler or REST route that mutates without `current_user_can` HIGH (CRITICAL when
reachable logged-out), and a nonce with no capability check HIGH.