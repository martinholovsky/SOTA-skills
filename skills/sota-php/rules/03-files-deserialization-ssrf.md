<!-- last-verified: 2026-07 -->

# 03 — Files, deserialization, and SSRF

PHP's include system, stream wrappers, and native serialization form one
connected attack surface: a "harmless" file path becomes code execution via
`include`, `phar://`, or `unserialize`. Treat every user-influenced path, file,
and URL as hostile.

## 1. File uploads: validate content, own the name, deny execution

Never trust anything the client sent: `$_FILES[...]['name']` and `['type']` are
attacker-chosen. (OWASP File Upload Cheat Sheet.)

```php
$f = $_FILES['avatar'] ?? null;
if ($f === null || $f['error'] !== UPLOAD_ERR_OK) { /* reject */ }
if (!is_uploaded_file($f['tmp_name'])) { /* reject */ }
if ($f['size'] > 2 * 1024 * 1024) { /* reject */ }

// 1. Content-derived type, allowlist only
$mime = new finfo(FILEINFO_MIME_TYPE)->file($f['tmp_name']);
$ext  = ['image/jpeg' => 'jpg', 'image/png' => 'png', 'image/webp' => 'webp'][$mime]
    ?? throw new RuntimeException('unsupported type');

// 2. Server-generated name — client filename is display metadata at most
$name = bin2hex(random_bytes(16)) . '.' . $ext;

// 3. Non-executable destination, outside the webroot
move_uploaded_file($f['tmp_name'], '/srv/app/storage/uploads/' . $name);
```

- **Storage:** outside the document root, served via a controlled handler
  (with `Content-Type` you set, `Content-Disposition`, `X-Content-Type-Options:
  nosniff`) or from object storage/a separate cookieless domain. If files must
  live under the webroot, the directory gets *no PHP execution* (webserver
  config: no handler/`php_admin_flag engine off` equivalent) — double
  extensions (`x.php.jpg`), trailing-dot and case tricks defeat blocklists.
- Extension **allowlist** derived from sniffed content, never the client name;
  reject polyglot-prone types you don't need (SVG = XSS vector unless
  sanitized). For images, re-encoding (GD/Imagick) strips embedded payloads —
  but keep Imagick patched (historic RCEs) and consider it a trade-off, not
  free.
- Archives: extraction is a traversal vector ("zip slip") — validate each entry
  name against the target dir before writing; cap entry count/size ratios
  (zip bombs).
- ini caps (`upload_max_filesize`, `post_max_size`, `max_file_uploads`) are the
  outer DoS guard (OWASP PHP Configuration Cheat Sheet), not validation.

## 2. Path traversal, LFI/RFI, and stream wrappers

Any `include`/`require`/`fopen`/`file_get_contents`/`readfile` whose path is
user-influenced is a code-execution candidate, not "just" file disclosure.

```php
// BAD — CRITICAL: LFI, and with allow_url_include, RFI
include $_GET['page'] . '.php';
readfile('/var/reports/' . $_GET['name']);

// GOOD — closed set: map input to known files
$page = ['home' => 'home.php', 'about' => 'about.php'][$_GET['page']] ?? 'home.php';
include __DIR__ . '/pages/' . $page;

// GOOD — dynamic filenames: canonicalize, then prove containment
$base = '/var/reports/';
$real = realpath($base . basename($_GET['name']));
if ($real === false || !str_starts_with($real, $base)) {
    throw new RuntimeException('invalid path');
}
readfile($real);
```

- Prefer allowlist maps over sanitizing. When sanitizing: `basename()` to drop
  directories, `realpath()` to resolve `..` and symlinks, then a prefix check
  against the canonical base (with trailing separator).
- **Stream wrappers escalate LFI:** `php://filter` (source disclosure via
  base64 chains), `phar://` (deserialization, §3), `data://`, `expect://`,
  `zip://`. Reject any user path containing `://`, or `parse_url` scheme-check
  it. Functions beyond include are affected — `file_exists('phar://…')` used
  to be enough pre-8.0 (§3).
- ini: `allow_url_include=Off` (default off since 7.4 deprecation; removed as a
  real option risk — keep it off), and `allow_url_fopen=Off` unless remote
  fetching is genuinely needed (OWASP PHP Configuration Cheat Sheet);
  `open_basedir` as a coarse second fence.

## 3. Deserialization: unserialize() is code execution; JSON is data

`unserialize()` on attacker data = **PHP object injection**: instantiated
objects fire `__destruct`/`__wakeup`/`__toString`, and public gadget-chain
catalogs (e.g. the phpggc project) cover major frameworks and libraries. Assume
a chain exists for your dependency graph.

```php
// BAD — CRITICAL on any external data (cookies, hidden fields, cache, queues)
$prefs = unserialize($_COOKIE['prefs']);

// GOOD — external data is JSON
$prefs = json_decode($cookie, associative: true, flags: JSON_THROW_ON_ERROR);

// If a legacy format forces unserialize: cap the damage AND authenticate first
$data = unserialize($raw, ['allowed_classes' => false]);          // scalars/arrays only
$data = unserialize($raw, ['allowed_classes' => [Point::class]]); // tight allowlist
```

- `allowed_classes => false` (7.0+) blocks object instantiation but not all
  DoS shapes; it is the floor, not the fix. The fix is JSON (or a schema-ed
  format) plus validation.
- Data that must round-trip internally (cache, queues) still transits
  attacker-reachable systems — sign it: `hash_hmac('sha256', $payload, $key)`
  verified with `hash_equals()` *before* deserializing.
- **Phar:** a `.phar`'s metadata is a serialized blob. Since **PHP 8.0**, the
  `phar://` wrapper no longer auto-unserializes metadata on file operations —
  only `Phar->getMetadata()` does (PHP RFC: phar_stop_autoloading_metadata,
  accepted 25-0). Pre-8.0, `file_exists('phar://upload.jpg')` was an RCE
  primitive. Still: never call `getMetadata()` on untrusted archives (8.0+
  accepts an `unserializeOptions` allowlist argument), and keep §2's wrapper
  filtering so uploads are never addressed as `phar://`.
- Same family: `wddx` (removed 7.4), reading `serialize()`d session/cache blobs
  populated by less-trusted code.

## 4. XML: XXE and entity expansion

- Since **PHP 8.0**, libxml external entity loading is disabled by default
  (requires libxml ≥ 2.9; `libxml_disable_entity_loader()` is deprecated
  because it became unnecessary — php.net migration80). Do not re-enable.
- Never parse untrusted XML with `LIBXML_NOENT` (entity substitution) or
  `LIBXML_DTDLOAD`. Audit any occurrence as HIGH.
- Billion-laughs/entity expansion: reject DTDs outright on untrusted input
  (`$dom->loadXML($xml, LIBXML_NONET)` and check `$dom->doctype === null`).

## 5. SSRF: server-side fetching of user-influenced URLs

A URL fetched by the server reaches things the user can't: cloud metadata
(`169.254.169.254`), localhost admin ports, internal services. (OWASP Server
Side Request Forgery Prevention Cheat Sheet.)

```php
function assertSafeUrl(string $url): void
{
    $p = parse_url($url);
    if (!in_array($p['scheme'] ?? '', ['http', 'https'], true)) fail();
    $ips = gethostbynamel($p['host'] ?? '') ?: [];
    foreach ($ips as $ip) {
        if (filter_var($ip, FILTER_VALIDATE_IP,
            FILTER_FLAG_NO_PRIV_RANGE | FILTER_FLAG_NO_RES_RANGE) === false) fail();
    }
}
```

- Prefer a **positive allowlist** of hosts/URL prefixes; IP-range blocklists
  are the fallback and must run on the *resolved* address, cover IPv6
  (`::1`, `fe80::`, mapped IPv4), and beware DNS rebinding (resolve once, pin
  via `CURLOPT_RESOLVE`).
- cURL hardening: `CURLOPT_PROTOCOLS`/`CURLOPT_REDIR_PROTOCOLS` limited to
  HTTP(S) — redirects can bounce to `gopher://`/`file://`; cap
  `CURLOPT_MAXREDIRS` or re-validate each hop; set timeouts; **never**
  `CURLOPT_SSL_VERIFYPEER => false` (HIGH).
- The strongest control is architectural: route egress through a proxy that
  enforces the allowlist (network-level, see sota-network-security), so a
  missed validation isn't fatal.
- `file_get_contents($url)`/`fopen` honor redirects with no protocol pinning —
  use a real HTTP client for remote fetches.

## Audit checklist

Run from repo root; verify each hit manually.

```bash
# Uploads — client-trusted name/type, executable destinations
grep -rnE "\\\$_FILES\[[^]]+\]\['(name|type)'\]" --include='*.php' src/
grep -rn 'move_uploaded_file' --include='*.php' src/   # trace dest: webroot? renamed?
grep -rn 'is_uploaded_file' --include='*.php' src/     # absent near move_* = MEDIUM

# LFI/RFI/traversal — user data reaching include/fs functions
grep -rnE '(include|require)(_once)?\s*[( ][^;]*\$_(GET|POST|REQUEST|COOKIE)' --include='*.php' src/
grep -rnE '(file_get_contents|fopen|readfile|file_put_contents|copy|unlink)\s*\([^;]*\$_' --include='*.php' src/
grep -rnE '(phar|expect|data|zip)://' --include='*.php' src/
grep -rn 'php://filter' --include='*.php' src/
php -r 'echo ini_get("allow_url_include"), "|", ini_get("allow_url_fopen"), PHP_EOL;'

# Deserialization — CRITICAL on external data
grep -rn 'unserialize(' --include='*.php' src/ | grep -v 'allowed_classes'
grep -rnE 'unserialize\s*\(\s*\$_(GET|POST|COOKIE|REQUEST)' --include='*.php' src/
grep -rn 'getMetadata' --include='*.php' src/
grep -rnE '__(destruct|wakeup|toString)' --include='*.php' src/  # gadget surface inventory

# XML
grep -rnE 'LIBXML_(NOENT|DTDLOAD)' --include='*.php' src/
grep -rn 'libxml_disable_entity_loader' --include='*.php' src/   # deprecated; check PHP<8 paths

# SSRF — user URLs fetched server-side
grep -rnE '(curl_init|file_get_contents|fopen|->request|->get)\s*\([^;]*\$' --include='*.php' src/ | grep -iE 'url|uri|host|endpoint|webhook'
grep -rn 'CURLOPT_SSL_VERIFYPEER' --include='*.php' src/          # false = HIGH
grep -rn 'CURLOPT_FOLLOWLOCATION' --include='*.php' src/          # check REDIR_PROTOCOLS nearby
```

Severity guide: `unserialize`/`include` of external data CRITICAL; uploads
executable or client-named HIGH; user-URL fetch with no allowlist/IP validation
HIGH (CRITICAL when cloud metadata is reachable); `LIBXML_NOENT` on untrusted
XML HIGH; missing `is_uploaded_file` MEDIUM.
