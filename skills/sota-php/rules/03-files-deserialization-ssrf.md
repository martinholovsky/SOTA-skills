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
$mime = (new finfo(FILEINFO_MIME_TYPE))->file($f['tmp_name']);   // parens required on 8.3
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
  `zip://`. Reject any user path containing `://`, or scheme-check it with a URL parser
  (on 8.5+ the `Uri\` classes, §5). Functions beyond include are affected —
  `file_exists('phar://…')` used to be enough pre-8.0 (§3).
- ini: `allow_url_include=Off`. It defaults to Off and has been deprecated since 7.4, but it is
  still honoured: measured on 8.5.9, `-d allow_url_include=1` printed a startup deprecation and
  then `include`d a `data://` URL. Keep it Off, and `allow_url_fopen=Off` unless remote
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

Build the request, do not relay it: take a host key or record ID from the caller and
look the base URL up in your own allowlist. Where a caller URL is unavoidable, the IP
check must run on the address cURL **actually dialled**, at connect time, on every
redirect hop, because anything checked before the request (a `gethostbynamel()` pass,
which is IPv4-only anyway) is a DNS-rebinding window. cURL's hook for that is
`CURLOPT_PREREQFUNCTION` (PHP 8.4+, libcurl 7.80+): it runs after the connection is
made and before the request is sent, receives the destination IP, and aborts on
`CURL_PREREQFUNC_ABORT`. Measured on PHP 8.5.9: a `localhost` URL was aborted with
errno 42, and with `CURLOPT_FOLLOWLOCATION` on, the callback ran again for the second hop.

```php
function isPublicIp(string $ip): bool
{
    if (filter_var($ip, FILTER_VALIDATE_IP, FILTER_FLAG_GLOBAL_RANGE) === false) return false;
    $b = inet_pton($ip);                                 // multicast passes the flag
    return strlen($b) === 4 ? (ord($b[0]) & 0xF0) !== 0xE0 : ord($b[0]) !== 0xFF;
}
$ch = curl_init($base . '/v1/items/' . rawurlencode($id));   // $base from YOUR allowlist
curl_setopt_array($ch, [
    CURLOPT_PROTOCOLS_STR       => 'https',
    CURLOPT_REDIR_PROTOCOLS_STR => 'https',
    CURLOPT_FOLLOWLOCATION      => false,     // or true: the callback below runs per hop
    CURLOPT_PREREQFUNCTION      => fn($h, string $ip, string $lip, int $port, int $lport): int
        => isPublicIp($ip) ? CURL_PREREQFUNC_OK : CURL_PREREQFUNC_ABORT,
    CURLOPT_CONNECTTIMEOUT => 3, CURLOPT_TIMEOUT => 10,
]);
```

- **What the check rejects, measured on PHP 8.5.9.** `FILTER_FLAG_GLOBAL_RANGE` (PHP 8.2+)
  blocked loopback, RFC 1918, `fc00::/7`, link-local incl. `169.254.169.254`, `0.0.0.0/8`,
  `100.64/10` and IPv4-mapped `::ffff:127.0.0.1`; it **passed multicast** (`224/4`,
  `ff00::/8`), hence the extra test, and the NAT64 prefix `64:ff9b::/96` (block it too where
  the network translates). The older `FILTER_FLAG_NO_PRIV_RANGE | FILTER_FLAG_NO_RES_RANGE`
  pair also passed `100.64.0.1`. Reject cloud metadata hostnames (e.g.
  `metadata.google.internal`) by name in the allowlist step as well.
- **Parse IP literals with `filter_var(..., FILTER_VALIDATE_IP)`, never by regex.** It
  rejected `0177.0.0.1`, `0x7f.0.0.1`, `2130706433` and `127.1`, while the system resolver
  behind `gethostbynamel()` turned every one of them into `127.0.0.1`, and `inet_pton()` on
  macOS read `0177.0.0.1` as `177.0.0.1`. A "not an IP, so it is a hostname" branch is the hole.
- **PHP 8.3 (no `PREREQFUNCTION`):** resolve A **and** AAAA (`dns_get_record()`), check every
  address, pin the checked one with `CURLOPT_RESOLVE`, and keep `CURLOPT_FOLLOWLOCATION` off,
  following each `CURLINFO_REDIRECT_URL` yourself through the same function.
- **Clients.** Guzzle follows redirects by default (`allow_redirects` max 5, http/https,
  read in 7.9 source): set `'allow_redirects' => false`, or pass the callback above through
  its `'curl' => [CURLOPT_PREREQFUNCTION => ...]` option (cURL handler only; each hop is a new
  request with the same options). Symfony's `NoPrivateNetworkHttpClient` (read in 7.3 source)
  resolves, pins via `resolve` and re-checks every redirect hop, but its default subnet list
  (`IpUtils::PRIVATE_SUBNETS`) omits multicast, so pass your own list to the constructor.
- Positive allowlist first; IP-range rejection is the fallback. OWASP: SSRF Prevention, .NET Security and GraphQL cheat sheets.
- **The parser that checks a URL must be the one that uses it.** Measured on 8.5.9 for
  `http://example.com\@evil.com/`: `parse_url()` gave host `evil.com`, cURL 8.21 dialled
  `evil.com`, `Uri\WhatWg\Url` (browser rules) gave `example.com`, and `Uri\Rfc3986\Uri::parse()`
  returned `null`. So a WHATWG check in front of a cURL fetch approves one host and fetches
  another. On 8.5+, parse a server-side fetch URL with `Uri\Rfc3986\Uri::parse()`, reject a
  `null`, check the parsed scheme and host, and hand cURL the object's `toString()`, never the
  raw input. Use `Uri\WhatWg\Url` where a browser follows the URL (redirect targets, links).
  On 8.3/8.4 there is no strict parser in core; the connect-time check above is the control.
- cURL hardening: `CURLOPT_PROTOCOLS_STR`/`CURLOPT_REDIR_PROTOCOLS_STR` (PHP 8.3+, libcurl
  7.85+) limited to HTTP(S) — redirects can bounce to `gopher://`/`file://`; a
  `CURLOPT_MAXREDIRS` cap is **not** re-validation; set timeouts; **never**
  `CURLOPT_SSL_VERIFYPEER => false` (HIGH).
- **Every PHP spelling of disabled TLS verification is HIGH, not only that one.** The rule is
  `sota-code-security` rules/04. Measured on PHP 8.5.9 against a local server:
  - cURL: `CURLOPT_SSL_VERIFYPEER` `false`/`0` accepted an untrusted chain, and
    `CURLOPT_SSL_VERIFYHOST` `0`/`false` accepted a certificate issued for another name. The
    value `1` is coerced to `2` with a notice.
  - Stream context (`file_get_contents`, `fopen`, `stream_socket_client`): `'ssl' =>
    ['verify_peer' => false]` accepted an untrusted chain, `'verify_peer_name' => false` any
    name, and `'allow_self_signed' => true` a self-signed certificate.

  Each switch turns off **one** of the two checks. `verify_peer => false` alone still refused
  the wrong-name certificate, so a half-disabled client can pass a smoke test. For an internal
  endpoint, point `cafile`/`CURLOPT_CAINFO` at the private CA.
- **SSH host keys: neither common PHP client checks one unless you do.** The class is
  `sota-code-security` rules/04 §5. Read from source:
  - phpseclib (4.0.1): `SSH2::login()` never compares the server's key with anything. The
    key-exchange signature is verified only inside `getServerPublicHostKey()`, and nothing in
    the library calls that method.
  - `ext-ssh2`: no known-hosts support at all. `ssh2_fingerprint()` returns a hash for *you* to
    compare, MD5 unless `SSH2_FINGERPRINT_SHA1` is passed.

  So every `new SSH2`/`new SFTP`/`ssh2_connect` needs a comparison of
  `getServerPublicHostKey()` or `ssh2_fingerprint()` with a pinned value **before**
  authenticating, failing closed. One with no such comparison in reach is the finding.
- The strongest control is architectural: route egress through a proxy that
  enforces the allowlist (network-level, see sota-network-security), so a
  missed validation isn't fatal.
- `file_get_contents($url)`/`fopen` honor redirects with no protocol pinning (measured:
  the default stream context followed a 302 to a loopback URL; `'http' => ['follow_location'
  => 0]` stopped it) and have no connect-time hook — use cURL for remote fetches. `getimagesize()`, `get_headers()` and
  `get_meta_tags()` fetch URLs through the same stream layer (php.net `getimagesize`: *"a
  remote file using one of the supported streams"*), so they are SSRF sinks too.


## 6. FFI — PHP calling C

The FFI extension lets PHP declare C functions and structures and call them directly, with
none of PHP's memory safety. Its gate is `ffi.enable`: the default `"preload"` restricts the
FFI API to the CLI and preloaded files, and **`"true"` opens it to every request**. So
`ffi.enable=true` in a web SAPI's `php.ini` is the finding, and FFI code, where it is needed,
is loaded from a preload script where its surface is fixed at start-up. Audit the C
signatures and every length crossing them with the C rules. The class is `sota-code-security` rules/06 §3.

## Audit checklist

Run from repo root; verify each hit manually.

- [ ] **FFI — HIGH if enabled for every request** (§6) —
      `grep -rniE 'ffi\.enable[[:space:]]*=[[:space:]]*"?(true|1|on)' --include='*.ini' --include='*.conf' --include='Dockerfile*' .` ;
      `grep -rnE '\\?FFI::(cdef|load|scope|new)' --include='*.php' .`
- [ ] **Uploads — client-trusted name/type, executable destinations** —
      `grep -rnE "\\\$_FILES\[[^]]+\]\['(name|type)'\]" --include='*.php' src/` ;
      `grep -rn 'move_uploaded_file' --include='*.php' src/` (trace dest: webroot? renamed?);
      `grep -rn 'is_uploaded_file' --include='*.php' src/` (absent near move_* = MEDIUM)
- [ ] **LFI/RFI/traversal — user data reaching include/fs functions** —
      `grep -rnE '(include|require)(_once)?\s*[( ][^;]*\$_(GET|POST|REQUEST|COOKIE)' --include='*.php' src/`
      ;
      `grep -rnE '(file_get_contents|fopen|readfile|file_put_contents|copy|unlink)\s*\([^;]*\$_' --include='*.php' src/`
      ; `grep -rnE '(phar|expect|data|zip)://' --include='*.php' src/` ;
      `grep -rn 'php://filter' --include='*.php' src/` ;
      `php -r 'echo ini_get("allow_url_include"), "|", ini_get("allow_url_fopen"), PHP_EOL;'`
- [ ] **Deserialization — CRITICAL on external data** —
      `grep -rn 'unserialize(' --include='*.php' src/ | grep -v 'allowed_classes'` ;
      `grep -rnE 'unserialize\s*\(\s*\$_(GET|POST|COOKIE|REQUEST)' --include='*.php' src/` ;
      `grep -rn 'getMetadata' --include='*.php' src/` ;
      `grep -rnE '__(destruct|wakeup|toString)' --include='*.php' src/` (gadget surface
      inventory)
- [ ] **XML** — `grep -rnE 'LIBXML_(NOENT|DTDLOAD)' --include='*.php' src/` ;
      `grep -rn 'libxml_disable_entity_loader' --include='*.php' src/` (deprecated; check PHP<8
      paths)
- [ ] **SSRF — user URLs fetched server-side** —
      `grep -rnE '(curl_init|file_get_contents|fopen|getimagesize|get_headers|get_meta_tags|->request|->get)[[:space:]]*\([^;]*\$' --include='*.php' src/ | grep -iE 'url|uri|host|endpoint|webhook'`
      ; `grep -rn 'CURLOPT_SSL_VERIFYPEER' --include='*.php' src/` (false = HIGH);
      `grep -rn 'CURLOPT_FOLLOWLOCATION' --include='*.php' src/` (check REDIR_PROTOCOLS nearby)
- [ ] **SSRF — no connect-time check of the dialled address (DNS rebinding) / redirects
      unchecked — HIGH (§5)** — prints each file that makes outbound requests with no
      connect-time IP check, then its redirect-following lines:
      `grep -rlE 'curl_init[[:space:]]*\(|GuzzleHttp\\Client|HttpClient::create' --include='*.php' src/ | while IFS= read -r f; do grep -qE 'CURLOPT_PREREQFUNCTION|CURLOPT_RESOLVE|NoPrivateNetworkHttpClient' "$f"; case $? in 0) ;; 1) echo "NO CONNECT-TIME IP CHECK: $f"; grep -nE "FOLLOWLOCATION[^;]*(true|1)|allow_redirects'?[[:space:]]*=>[[:space:]]*(true|\[)" "$f" | sed "s|^|  REDIRECT FOLLOWED: $f:|" ;; *) echo "SWEEP FAILED: $f" ;; esac; done`
      — a file using Guzzle's default redirects prints only its first line; a file not
      printed still needs reading (`CURLOPT_RESOLVE` alone leaves redirect hops unpinned)
- [ ] **URL checked by one parser, fetched by another (§5) — HIGH on an SSRF path** — prints
      each file that validates with `parse_url` or WHATWG and also fetches with cURL:
      `grep -rlE 'parse_url[[:space:]]*\(|WhatWg\\Url' --include='*.php' src/ | while IFS= read -r f; do grep -qE 'curl_init|GuzzleHttp|HttpClient' "$f"; case $? in 0) echo "CHECK-PARSER vs FETCHER: $f" ;; 1) ;; *) echo "SWEEP FAILED: $f" ;; esac; done`
      (on 8.5+ the fix is `Uri\Rfc3986\Uri::parse()` and fetching its `toString()`)
- [ ] **TLS verification off in any spelling — HIGH (§5)** —
      `grep -rniE '(SSL_VERIFYPEER|SSL_VERIFYHOST|verify_peer(_name)?)["'"'"']?[[:space:]]*(,|=>)[[:space:]]*(false|0)|allow_self_signed["'"'"']?[[:space:]]*=>[[:space:]]*(true|1)' --include='*.php' src/`
- [ ] **SSH host key never compared — HIGH (§5)** — prints each file that opens an SSH session
      and never compares a host key:
      `grep -rlE 'new[[:space:]]+([\\A-Za-z0-9_]*\\)?(SSH2|SFTP)[[:space:]]*\(|ssh2_connect[[:space:]]*\(' --include='*.php' src/ | while IFS= read -r f; do grep -qE 'getServerPublicHostKey|ssh2_fingerprint' "$f"; case $? in 0) ;; 1) echo "NO HOST-KEY CHECK: $f" ;; *) echo "SWEEP FAILED: $f" ;; esac; done`
      — a file the loop does *not* print still needs reading: the comparison must run before
      `login()` and fail closed

Severity guide: `unserialize`/`include` of external data CRITICAL; uploads
executable or client-named HIGH; user-URL fetch with no allowlist/IP validation
HIGH (CRITICAL when cloud metadata is reachable); `LIBXML_NOENT` on untrusted
XML HIGH; missing `is_uploaded_file` MEDIUM; any disabled TLS check or an SSH session with
no host-key comparison HIGH.