# 01 — Input Handling & Injection

Scope: SQL/NoSQL injection, command injection, path traversal, SSRF, XXE, template
injection, unsafe deserialization, prototype pollution, ReDoS, canonicalization,
allowlist validation. Maps to OWASP A05:2025 (Injection), A01:2025 (Broken Access
Control — SSRF was folded into it in the 2025 release), A08:2025 (Software or
Data Integrity Failures).

Core principle: **data and code must never share a channel.** Every injection class
below is the same bug — untrusted bytes reaching an interpreter (SQL engine, shell,
filesystem path resolver, XML parser, template engine, object loader, regex engine)
without a structural boundary. Fix the boundary; never "sanitize" your way out.

## 1. Validation strategy (applies to everything below)

- Validate at the **trust boundary** (HTTP handler, queue consumer, file ingester),
  not deep in business logic. Reject early, fail closed.
- **Allowlist, never denylist** (CWE-183). Define what IS valid (type, length, range,
  charset, format) and reject everything else. Denylists always miss an encoding.
- **Canonicalize before validating** (CWE-180): decode URL/percent/unicode encoding
  ONCE, normalize unicode (NFC), resolve paths — then validate the canonical form.
  Validating then decoding reintroduces the bug (`%252e%252e%252f`).
- Validate server-side. Client-side validation is UX, not security.
- Length-limit every string input. Unbounded input is a DoS primitive even when
  syntactically valid.
- **Validate semantics, not just syntax** (OWASP Business Logic): enforce cross-field
  and business invariants the type system can't (`checkout` after `checkin`,
  `quantity ≥ 1`, end-date after start-date, currency matches account). A
  well-formed-but-nonsensical request is still an attack.
- **Anything the client can set is adversary-controlled** — hidden form fields,
  disabled inputs, pre-filled values, and data you returned last response included.
  Re-validate and re-authorize them server-side; never trust them because "the UI
  doesn't allow changing it".

```python
# BAD: denylist, validates pre-decoding
if "../" not in user_path: open(base + urllib.parse.unquote(user_path))

# GOOD: canonicalize, then containment check (allowlist semantics)
p = (BASE_DIR / user_path).resolve()
if not p.is_relative_to(BASE_DIR): raise Forbidden()
```

## 2. SQL injection (CWE-89)

- Use **parameterized queries / prepared statements** for every value. No exceptions
  for "internal" or "already validated" data.
- String concatenation/f-strings/format() into SQL is a finding even if inputs look
  safe today — the call site is one refactor away from exploitable.
- Identifiers (table/column names, ORDER BY direction) **cannot be parameterized**:
  map them through a hardcoded allowlist dict, never interpolate raw input.
- ORMs do not save you: `raw()`, `extra()`, `whereRaw()`, `$where`, string-built
  HQL/JPQL are all injectable. Audit every raw-query escape hatch.
- NoSQL (CWE-943): reject non-scalar values where scalars are expected.
  `{"password": {"$ne": ""}}` bypasses Mongo equality checks — enforce types
  (`typeof password === "string"`) before building queries.
- LIKE clauses: escape `%` and `_` in the *value* (parameterization doesn't), or
  attacker controls match breadth.

```python
# BAD
cur.execute(f"SELECT * FROM users WHERE email = '{email}'")
cur.execute("SELECT * FROM logs ORDER BY " + sort_col)

# GOOD
cur.execute("SELECT * FROM users WHERE email = %s", (email,))
SORT_COLS = {"date": "created_at", "name": "username"}
cur.execute(f"SELECT * FROM logs ORDER BY {SORT_COLS[sort_key]}")  # KeyError = reject
```

## 3. Command injection (CWE-78)

- **Do not invoke a shell.** Use argv-array exec APIs: `subprocess.run([...])` (never
  `shell=True`), `execve`, Go `exec.Command`, Node `execFile`/`spawn` (never `exec`).
- Prefer native libraries over shelling out (`shutil`, `os` ops, language HTTP/zip
  libs) — removes the interpreter entirely.
- Argv arrays stop shell metacharacters but NOT argument injection (CWE-88):
  a filename of `--output=/etc/cron.d/x` or `-oProxyCommand=...` (ssh, git, curl,
  tar, find all have dangerous flags). Insert `--` before positional args and
  validate that user-supplied args don't start with `-`.
- If a shell is truly unavoidable, allowlist-validate every interpolated token
  against `^[A-Za-z0-9._-]+$` and still treat it as a code smell.

```js
// BAD
exec(`convert ${file} out.png`);
// GOOD
execFile("convert", ["--", file, "out.png"]);
```

## 4. Path traversal (CWE-22) & file access

- Resolve to an absolute canonical path (`realpath`, `Path.resolve`,
  `filepath.Clean` + abs) and verify containment within the intended base dir
  with a path-aware check (`is_relative_to`), not `startswith` (`/var/www2`
  passes a `startswith("/var/www")` check).
- Reject NUL bytes, and on Windows also reserved names (`CON`, `NUL`), alternate
  data streams (`:`), and both slash types.
- Treat archive extraction as path traversal (Zip Slip, CWE-22): validate every
  entry name post-join; reject absolute paths and symlink entries; cap total
  decompressed size and entry count (zip bombs).
- Best: don't use user input as a path at all — store files under a server-generated
  UUID, keep the user filename only as display metadata in the DB.

### 4.1 Filesystem adjacents

- Symlinks inside user-controllable trees escape containment even after
  `resolve()`-at-check-time — re-resolve at open time or use `O_NOFOLLOW`,
  `openat2(RESOLVE_BENEATH)` on Linux; see TOCTOU in rules/06 §6.
- User-controlled *target* of file writes (log path, export path, config path
  from input) is arbitrary-file-write → RCE via cron/webroot/`.ssh` drops; same
  containment rules apply to writes, harder.
- `os.path.join(base, user)` discards `base` entirely when `user` is absolute
  (`/etc/passwd`) — join, then resolve, then containment-check; never trust the
  join alone (Python, Node `path.join` with `..`, Java `Paths.resolve`).

## 5. SSRF (CWE-918)

Any feature that fetches a user-supplied URL (webhooks, importers, PDF renderers,
avatar-by-URL, link previews) is an SSRF surface targeting cloud metadata
(`169.254.169.254`), internal admin panels, and localhost services.

- Allowlist schemes (`https` only — block `file:`, `gopher:`, `ftp:`, `dict:`).
- Resolve DNS, then verify **every** resolved IP is public: reject loopback,
  RFC1918, link-local, ULA/IPv6-mapped (`::ffff:127.0.0.1`), `0.0.0.0`.
- **Pin the validated IP for the actual connection** (custom dialer/resolver) —
  validate-then-reconnect is a DNS-rebinding TOCTOU (CWE-367).
- Disable or re-validate redirects (redirect to `http://127.0.0.1/` defeats a
  one-shot check). Cap redirect count, response size, and timeout.
- Defense in depth: run fetchers in an egress-restricted network segment; on cloud,
  enforce IMDSv2 / metadata-server firewalling.
- Parser-confusion URLs (`http://expected.com@evil.com/`, `evil.com#@expected.com`)
  — compare the *host the client will actually connect to*, from the same URL
  parser the HTTP client uses.

```go
// GOOD: validate the resolved IP and pin it for the dial (no rebinding window)
dialer := &net.Dialer{Timeout: 5 * time.Second}
transport := &http.Transport{
    DialContext: func(ctx context.Context, network, addr string) (net.Conn, error) {
        host, port, _ := net.SplitHostPort(addr)
        ips, err := net.DefaultResolver.LookupIPAddr(ctx, host)
        if err != nil { return nil, err }
        for _, ip := range ips {
            if ip.IP.IsLoopback() || ip.IP.IsPrivate() || ip.IP.IsLinkLocalUnicast() ||
               ip.IP.IsMulticast() || ip.IP.IsUnspecified() || isCGNAT(ip.IP) {
                return nil, errors.New("blocked address") // IsMulticast covers 224/4 + ff00::/8;
                // isCGNAT blocks 100.64.0.0/10 (carrier-grade NAT, reaches internal hosts)
            }
        }
        return dialer.DialContext(ctx, network, net.JoinHostPort(ips[0].IP.String(), port))
    },
}
client := &http.Client{Transport: transport, Timeout: 10 * time.Second,
    CheckRedirect: func(req *http.Request, via []*http.Request) error {
        if len(via) >= 3 { return errors.New("too many redirects") }
        return nil // transport re-validates each hop's IP via DialContext
    }}
```

## 6. XXE & XML (CWE-611)

- Disable DTDs and external entities on **every** XML parser, explicitly — many
  parsers (Java DocumentBuilderFactory, libxml2 pre-2.9) are unsafe by default:
  `factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true)`.
- Python: use `defusedxml`; .NET: `XmlResolver = null`; Node: avoid `libxmljs`
  `noent: true`.
- Same family: disable external schema/DTD fetch in SVG processing, DOCX/XLSX
  ingestion (they're zipped XML), SOAP, and SAML libraries.
- Billion-laughs (CWE-776): cap entity expansion even with external entities off.

```java
// GOOD: Java hardened XML factory (apply to DocumentBuilder, SAX, StAX, Transformer)
DocumentBuilderFactory f = DocumentBuilderFactory.newInstance();
f.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
f.setFeature("http://xml.org/sax/features/external-general-entities", false);
f.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
f.setXIncludeAware(false);
f.setExpandEntityReferences(false);
```

## 7. Template injection — SSTI (CWE-1336)

- User input goes into template **context variables**, never into the template
  **string**. `render(template_string + user_input)` is RCE in Jinja2, Freemarker,
  ERB, Twig, etc. (`{{cycler.__init__.__globals__...}}`).
- If users must author templates (email editors, CMS), use a logic-less sandboxed
  engine (Mustache/Liquid in strict mode, Jinja2 `SandboxedEnvironment` — and treat
  even that as a hardened surface, sandbox escapes recur).

```python
# BAD                                    # GOOD
Template("Hi " + name).render()          Template("Hi {{ name }}").render(name=name)
```

## 8. Unsafe deserialization (CWE-502)

- **Never deserialize untrusted data with native object serializers**: Python
  `pickle`/`PyYAML yaml.load`, Java `ObjectInputStream`/XMLDecoder, PHP
  `unserialize`, Ruby `Marshal`, .NET `BinaryFormatter` (deprecated for this
  reason). All are remote code execution by design, regardless of gadget hygiene.
- Use data-only formats: JSON, protobuf, msgpack — then validate against a schema
  and map to explicit DTOs.
- `yaml.safe_load` only. Java: if legacy ObjectInputStream is unavoidable, enforce
  `ObjectInputFilter` allowlists (JEP 290) — and still plan migration.
- Signed/encrypted blobs (session cookies, view state) only defer the problem:
  if the key leaks or signing is misconfigured (Rails `secret_key_base`,
  ASP.NET machineKey), deserialization RCE follows. Keep contents data-only.

## 9. Prototype pollution (CWE-1321, JS/TS)

- Recursive merge/extend/clone of attacker-controlled JSON into objects lets
  `{"__proto__": {"isAdmin": true}}` poison every object. Block keys
  `__proto__`, `constructor`, `prototype` in any deep-merge; or use
  `Object.create(null)` / `Map` for attacker-keyed dictionaries.
- `JSON.parse` itself is safe; the merge utility is the sink. Audit lodash
  `merge`/`set`/`defaultsDeep` call sites fed by request bodies, and query-string
  parsers with bracket syntax (`?a[__proto__][x]=1`).
- Mitigate globally with `node --frozen-intrinsics` or `Object.freeze(Object.prototype)`
  where feasible; treat as defense in depth, not the fix.

## 10. ReDoS (CWE-1333)

- Any regex with nested/overlapping quantifiers (`(a+)+`, `(a|a)*`, `(\w+\s?)*`)
  applied to unbounded input can pin a CPU core with ~40 chars.
- Length-cap input before regex matching. Prefer linear-time engines: RE2, Rust
  `regex`, Go `regexp` (all guaranteed linear); .NET `NonBacktracking`;
  Node ≥20 has no built-in guard — use `re2` package for untrusted input.
- Lint with rules like `eslint-plugin-redos` / `regexploit` in CI for any regex
  whose input crosses a trust boundary.
- Don't validate emails/URLs with elaborate regexes at all — parse with a real
  parser, regex only for coarse shape.

## 11. Other injection surfaces (audit sweep list)

- **LDAP injection (CWE-90)**: escape DN and filter metacharacters per RFC 4515
  (`* ( ) \ NUL`) via the library's escaper, or allowlist
  `^[A-Za-z0-9._@-]+$` for usernames before building filters.
  `(&(uid=USER)(password=PASS))` with `USER = *)(uid=*` is an auth bypass.
- **XPath injection (CWE-643)**: same shape as SQLi; use parameterized XPath
  (XPath 3.1 variables) or allowlist values — quoting alone is fragile.
- **CRLF / header injection (CWE-93/113)**: reject `\r`/`\n` in anything placed
  into HTTP headers (redirect `Location` from input, custom headers, cookies) —
  response splitting and cache poisoning. Modern frameworks reject; hand-built
  responses and raw socket code don't. Same bug in email: user input in
  `Subject`/`To` enables SMTP header injection (`%0aBcc: victims`) — use the
  mail library's structured API, never string-assembled MIME.
- **Open redirect (CWE-601)**: `?next=` targets must be relative-path-only
  (reject `//evil.com`, `https:`, `\\`, scheme-relative) or exact-match against
  an allowlist. Open redirects chain into OAuth token theft and SSRF-filter
  bypass — not "low severity" in those contexts.
- **CSV/formula injection (CWE-1236)**: cells starting `= + - @ \t` execute in
  spreadsheet apps on export; prefix with `'` or space-escape when generating
  CSV/XLSX from user data.
- **Host header attacks**: never build absolute URLs (password-reset links!)
  from the request `Host`/`X-Forwarded-Host` — use a configured canonical
  origin. Poisoned reset links = account takeover (CWE-640 chain).
- **HTTP parameter pollution / parser differentials**: duplicate keys
  (`?id=1&id=2`), JSON duplicate fields, and content-type confusion are
  validated-by-one-parser, consumed-by-another bypasses — validate the same
  representation you consume, normalize once at the boundary.
- **GraphQL**: injection rules apply inside resolvers (resolver args → SQL);
  plus GraphQL-specific limits live in rules/06 §5 and field authz in rules/03.

## Audit checklist

- [ ] Is every SQL/NoSQL query parameterized, with raw/`whereRaw`/`$where` escape hatches audited and identifiers allowlist-mapped?
- [ ] Are all process invocations argv-array based (no `shell=True`/`exec(string)`), with `--` separators and leading-dash rejection for user args?
- [ ] Are file paths canonicalized (`realpath`) then containment-checked with a path-aware comparison before any filesystem access?
- [ ] Does archive extraction validate entry paths, reject symlinks/absolute entries, and cap decompressed size?
- [ ] Do URL fetchers enforce scheme allowlist, block private/link-local/metadata IPs *post-DNS-resolution*, pin the connection IP, and re-check on redirects?
- [ ] Are DTDs/external entities explicitly disabled on every XML/SVG/Office-doc parser?
- [ ] Is user input confined to template variables (never concatenated into template strings)?
- [ ] Is all untrusted deserialization via data-only formats with schema validation (no pickle/ObjectInputStream/unserialize/Marshal/yaml.load)?
- [ ] Do JS deep-merge/set utilities fed by request data block `__proto__`/`constructor`/`prototype` keys?
- [ ] Are regexes on untrusted input linear-time or length-capped, with no nested quantifiers?
- [ ] Is validation allowlist-based, server-side, performed after canonicalization, with length limits on every field?
- [ ] Are CR/LF rejected from header/email-field values, and absolute URLs (reset links) built from configured origins, never the Host header?
- [ ] Are redirect targets allowlisted or relative-only, and CSV exports formula-escaped?
- [ ] Are LDAP/XPath filters built with library escapers or parameterization?
