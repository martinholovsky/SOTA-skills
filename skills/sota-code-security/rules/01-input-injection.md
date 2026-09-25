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
- **NoSQL operators from the client are denied by default.** Reject any `$`-prefixed key that
  arrives in input unless a named feature needs that one operator. `$where`, `$function` and
  `$accumulator` run server-side JavaScript (deprecated from MongoDB 8.0, per its docs). `$regex`
  is two bugs at once: `.*` matches every document, and MongoDB 6.1+ evaluates it with PCRE2, a
  backtracking engine, so it is also a ReDoS vector (§10). Escape and length-cap user text that
  goes into one, or use the driver's text search (`$text` with the string as a plain value).
  Never pass a request object as the filter (`find(req.body)`); build it from typed fields
  through the driver's or ODM's builder (`eq("email", email)`, Mongoose, Spring Data). A string
  that still reaches a JavaScript-evaluated query must not contain `' " \ ; { } $`.
  OWASP: NoSQL Security cheat sheet, Java Security cheat sheet.
- **Optional filters: choose a whole statement, never assemble a WHERE.** `WHERE 1=1` plus
  appended `" AND ..."` fragments is concatenation with extra steps, and a branch that drops its
  condition turns a scoped read, UPDATE or DELETE into one over the whole table. Select among
  fixed, complete parameterized statements keyed by which filters are present (or compose
  predicate objects in a query builder), and raise when no required criterion was supplied.
- **Stored procedures** go through the driver's parameterized call API (JDBC `prepareCall` /
  `CallableStatement`, ADO.NET `CommandType.StoredProcedure` with parameters). Dynamic SQL
  inside the procedure binds too (`EXECUTE IMMEDIATE ... USING` in PL/SQL, `EXECUTE ... USING`
  in PL/pgSQL, `sp_executesql` with a parameter list in T-SQL); a procedure that concatenates is
  the same injection moved into the database.
- **Know where your driver binds.** Some send statement and values separately (PDO with
  `ATTR_EMULATE_PREPARES => false`, psycopg 3 by default); others merge values into the SQL text
  on the client (PDO emulation, psycopg2), which leaves the driver's quoting as the only barrier.
  Use the server-side mode wherever the driver offers one, and review any switch to emulation.
  OWASP: SQL Injection Prevention, Query Parameterization cheat sheets; Code Review Guide v2.
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

- **Prefer allowlist mode, and take a host, not a URL.** First ask whether the fetch needs to
  exist. Where it does and the destinations are known, accept a destination key, IP or domain,
  match it exactly against an explicit allowlist, and build the request yourself from the
  matched entry: your scheme, port and path, plus only fields you validated one by one. Never
  carry the path or query of a user URL across, do not follow redirects, and hand the caller
  the fields you extracted rather than the upstream body or error text. The resolve-and-pin
  controls below are for the open case (webhooks, link previews) where no allowlist can exist.
- **Parse hosts strictly.** IPv4 has hex, octal, dword and short forms (`0x7f.0.0.1`,
  `0177.0.0.1`, `2130706433`, `127.1`) that parsers disagree on; use a parser that rejects or
  normalises them and compare its *output*, never the raw string (per-language results are in
  each language skill's security rules). Keep IP allowlists dual-stack (every v4 and v6 address
  of each destination) and exact-match. In allowlist mode validate domain *syntax* with a
  validator that does not resolve: resolving to validate leaks the name to resolvers and still
  rebinds at connect time. Instead have your own domains answered by the internal resolver
  first, and monitor each allowlisted name's A/AAAA records for private or internal addresses.
  In the open case, check names against a central internal-domain list or an internal-only
  resolver, then resolve and pin as below. **Reject a URL whose host two parsers in the path
  read differently**: `http://example.com\@evil.com` is `example.com` to WHATWG `new URL`
  (Node 22) and `evil.com` to CPython `urlsplit` (3.14), both measured 2026-09-25.
- Allowlist schemes (`https` only — block `file:`, `gopher:`, `ftp:`, `dict:`).
- Resolve DNS, then verify **every** resolved IP is public. The block list is the IANA IPv4 and
  IPv6 Special-Purpose Address Registries plus multicast, not a few remembered ranges: at least
  `0.0.0.0/8`, `127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `100.64.0.0/10`,
  `169.254.0.0/16`, `224.0.0.0/4`, `240.0.0.0/4`, `::/128`, `::1/128`, `fc00::/7`, `fe80::/10`,
  `ff00::/8`, and `::ffff:0:0/96` judged by its embedded IPv4 (`::ffff:127.0.0.1`). Prefer a
  library predicate that tracks the registry over a hand list, and never a string-prefix test
  (`startswith("10.")`). Multicast is a separate registry: Python 3.14 `is_global` is `True`
  for `224.0.0.1` and `ff02::1` (measured), so test `not ip.is_global or ip.is_multicast`.
  Metadata endpoints go beyond `169.254.169.254`: refuse host *names* such as
  `metadata.google.internal` (GCP), and note AWS's IPv6 `fd00:ec2::254` (inside `fc00::/7`).
  OWASP: SSRF Prevention, DotNet Security, GraphQL cheat sheets.
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
- **A validating regex matches the whole input.** Use the full-match API (`re.fullmatch`)
  or absolute anchors, and know that `$` is not one: `re.match(r"^[a-z]+$",
  "abc\n")` matches in Python 3.14 and Perl's `$` does the same, while Ruby's `^`/`$` are line
  anchors (use `\A`…`\z`; Python spells the end `\Z`). Go and JavaScript `$` without the
  multiline flag rejected the newline (all measured 2026-09-25). Put the length bound inside
  the pattern (`{1,32}`, not `+`), avoid `.`/`.*` where a character class says what is allowed,
  and prefer a vetted pattern to a home-grown one. User text placed *inside* a pattern goes
  through the language's escaper (`re.escape`, `regexp.QuoteMeta`, `Regexp.escape`,
  `quotemeta`). Swapping a linear-time engine (RE2, Go `regexp`, Rust `regex`) for a
  backtracking one to get lookaround or backreferences (`regexp2`, `fancy-regex`, PCRE) gives
  up the ReDoS guarantee; bound it with a match timeout or limit. Per-language detail lives in
  each language skill's security rules. OWASP: Input Validation cheat sheet, Go-SCP
  (validation, regular expressions), Proactive Controls 2024 C3, ASVS 5.0 V1.2.9.

## 11. Other injection surfaces (audit sweep list)

- **LDAP injection (CWE-90)**: two contexts, two encoders, chosen by where the value lands.
  A **search-filter** value is escaped per RFC 4515 (`*`, `(`, `)`, `\`, NUL become `\XX`).
  A **DN component** is escaped per RFC 4514, a different set: `"`, `+`, `,`, `;`, `<`, `>`,
  `\` and NUL anywhere, plus a leading space or `#` and a trailing space; `=` may be escaped
  and common encoders do. DN escaping is positional, so an encoder's "skip the leading/trailing
  rules" mode is only for a fragment spliced into the middle of a DN. Use a maintained encoder
  per context (python-ldap `ldap.filter.escape_filter_chars` / `ldap.dn.escape_dn_chars`, go-ldap
  `EscapeFilter` / `EscapeDN`, PHP `ldap_escape` with `LDAP_ESCAPE_FILTER` / `LDAP_ESCAPE_DN`)
  or allowlist `^[A-Za-z0-9._@-]+$` for usernames first.
  `(&(uid=USER)(password=PASS))` with `USER = *)(uid=*` is an auth bypass. OWASP: LDAP
  Injection Prevention, Injection Prevention, DotNet Security cheat sheets.
- **XPath injection (CWE-643)**: same shape as SQLi; use parameterized XPath
  (XPath 3.1 variables) or allowlist values — quoting alone is fragile.
- **XML built from strings (XML injection, CWE-91)**: untrusted data concatenated or
  interpolated into XML text can close the element and add its own. A name of
  `x</name><role>admin</role><name>` inside `<user><name>…</name><role>user</role></user>`
  parses to **two** `<role>` elements, and a first-match lookup returns `admin`. Measured
  2026-09-24 in Python, Java, .NET, Go, PHP, Node and Ruby: the same result in all seven. An
  attribute value `x" admin="true` adds an attribute the same way, and **wrapping the value in
  CDATA does not help**, because `]]>` ends the section (measured). The fix is an API that
  escapes, never a template: DOM `setTextContent`/`createTextNode`, ElementTree `.text`,
  `XElement`, Go `xml.Marshal`, PHP `XMLWriter`, Node `xmlbuilder2`, REXML `add_text`. Each
  one kept the payload as text (measured). **Trap:** PHP `DOMDocument::createElement($name,
  $value)` does *not* escape `$value` (php.net), so an `&` in it starts an entity reference.
  SOAP envelopes and XML request bodies built from templates are the usual sites (find-sec-bugs
  `POTENTIAL_XML_INJECTION`). Detectors, each run against a known-bad and a known-good fixture
  under ugrep and BSD grep. They are line-based, so a template split across lines is missed,
  and HTML templates match too; keep the hits whose output is parsed as XML or sent as XML:

  ```text
  Java    grep -rnE '"<[A-Za-z/][^"]*"[[:space:]]*\+|\+[[:space:]]*"</' --include='*.java' --include='*.kt' .
  Python  grep -rnE "f[\"'][^\"']*<[A-Za-z/][^\"']*\{" --include='*.py' .
  .NET    grep -rnE 'LoadXml[[:space:]]*\([[:space:]]*\$|\$"[^"]*<[A-Za-z/][^"]*\{' --include='*.cs' .
  Go      grep -rnE 'Sprintf[[:space:]]*\([[:space:]]*"[^"]*<[A-Za-z/]' --include='*.go' .
  PHP     grep -rnE '(simplexml_load_string|loadXML)[[:space:]]*\([^;]*(\.[[:space:]]*\$|"[^"]*\$)|createElement[[:space:]]*\([^,)]*,[[:space:]]*\$' --include='*.php' .
  Node    grep -rnE '`[^`]*<[A-Za-z/][^`]*\$\{' --include='*.js' --include='*.ts' --include='*.mjs' --include='*.cjs' .
  Ruby    grep -rnE '"[^"]*<[A-Za-z/][^"]*#\{' --include='*.rb' .
  ```
- **CRLF / header injection (CWE-93/113)**: reject `\r`/`\n` in anything placed
  into HTTP headers (redirect `Location` from input, custom headers, cookies) —
  response splitting and cache poisoning. Modern frameworks reject; hand-built
  responses and raw socket code don't. Same bug in email: user input in
  `Subject`/`To` enables SMTP header injection (`%0aBcc: victims`) — use the
  mail library's structured API, never string-assembled MIME.
  Broader than CR/LF: header names and values you emit carry printable ASCII only (RFC 9110
  steers new fields to visible US-ASCII, SP and HTAB; encode anything else, e.g. RFC 8187 for
  filenames). A server or proxy accepting HTTP/2 or HTTP/3 must treat a header field containing
  CR, LF or NUL as malformed (RFC 9113 section 8.2.1, RFC 9114 section 10.3): those bytes survive the binary
  framing and become header injection or request smuggling when the request is downgraded to
  HTTP/1.1. OWASP: ASVS 5.0 V4.2.4, Go-SCP (validation), Secure Coding Practices QRG.
- **Open redirect (CWE-601)**: `?next=` targets must be relative-path-only
  (reject `//evil.com`, `https:`, `\\`, scheme-relative) or exact-match against
  an allowlist. Open redirects chain into OAuth token theft and SSRF-filter
  bypass — not "low severity" in those contexts. The same rule covers **every** redirect
  sink, not only a 30x `Location`: the `Refresh` response header, `<meta http-equiv="refresh">`,
  client-side `location`/`location.href` assignment and `location.assign`/`replace`, and
  server-side forwards whose target comes from input (servlet `getRequestDispatcher(...)
  .forward`, ASP.NET `Server.Transfer`/`Execute`), which can land the caller on a function
  nobody checked them for. The best form takes a short ID the server maps to a URL; make the IDs non-enumerable so the
  map cannot be walked. OWASP: Unvalidated Redirects and Forwards cheat sheet, Code Review
  Guide v2.
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
- [ ] Is every XML document or SOAP/XML body that carries untrusted data built through an escaping API, with no string concatenation, interpolation or CDATA wrapping (§11, XML built from strings)? Run the §11 detector row for the language, and read each hit. HIGH when an injected element or attribute changes a security decision (role, price, recipient).
- [ ] **SSRF allowlist mode (§5)**: does each fetch with known destinations take a host or key, match it against an allowlist and rebuild the request with its own scheme, port and path, relaying extracted fields rather than the upstream body? HIGH when a request field is the URL; read each hit of `grep -rnE "(requests\.(get|post|head)|urlopen|fetch|axios\.(get|post)|http\.(Get|Post|Head)|GetAsync|getForObject)\([[:space:]]*(req(uest)?\.(args|form|query|body|params|json|GET|POST)|r\.URL\.Query|params\[)" --include='*.py' --include='*.js' --include='*.ts' --include='*.go' --include='*.cs' --include='*.java' .`
- [ ] **SSRF host parsing (§5)**: are IP literals parsed strictly and the parser's output compared (never `inet_aton`/`inet_addr` or the raw string), domain syntax validated without DNS in allowlist mode, and URLs rejected when two parsers read different hosts? HIGH where the check guards an internal destination; read each hit of `grep -rnE 'inet_aton|inet_addr[[:space:]]*\(|IPAddress\.(Try)?Parse|gethostbyname|InetAddress\.getByName' --include='*.c' --include='*.cpp' --include='*.py' --include='*.cs' --include='*.java' --include='*.kt' .`
- [ ] **SSRF block list (§5)**: does the open-case block list cover the IANA special-purpose registries plus multicast for both families (including `0.0.0.0/8`, `100.64.0.0/10`, `::ffff:0:0/96`) and metadata host names, with no string-prefix IP tests? HIGH for any prefix test hit by `grep -rnE "(startswith|startsWith|HasPrefix|start_with\?)\([^)]*[\"'](10\.|127\.|169\.254|192\.168|172\.(1[6-9]|2[0-9]|3[01])|0\.|fc|fd|fe80)" --include='*.py' --include='*.js' --include='*.ts' --include='*.go' --include='*.rb' --include='*.java' --include='*.cs' .`
- [ ] **LDAP DN vs filter (§11)**: is each LDAP value escaped with the encoder for where it lands (RFC 4514 for DN components, RFC 4515 for filter values)? HIGH on an authentication or authorization bind; every hit of `grep -rnE "(uid|cn|ou|sAMAccountName|mail)=[\"'][[:space:]]*[+.]|(uid|cn|ou|mail)=(\{|%s|\\$\{|#\{)" --include='*.py' --include='*.java' --include='*.php' --include='*.js' --include='*.ts' --include='*.go' --include='*.cs' --include='*.rb' . | grep -vE 'escape|Escape|[Ee]ncode'` is a DN or filter built from an unescaped value
- [ ] **Validation regexes (§10)**: are validators full-match with an absolute end anchor, bounded inside the pattern, and is user text escaped before it enters a pattern? HIGH where the regex is a security control (allowlist, redirect or host check); read each hit of `grep -rnE "(re\.(match|search|compile)\([[:space:]]*r?[\"']\^[^\"']*\\\$[\"']|=~[[:space:]]*/\^[^/]*\\\$/|re\.(compile|match|search)\([[:space:]]*(r?f|fr)[\"']|new RegExp\([^\"'/)]|Regexp\.new\([^\"'/)])" --include='*.py' --include='*.rb' --include='*.js' --include='*.ts' . | grep -vE 'escape|QuoteMeta|quotemeta'`
- [ ] **Header contents (§11)**: are emitted header names and values printable ASCII with CR/LF rejected, and does every HTTP/2 or HTTP/3 front end reject CR, LF or NUL in inbound fields before any HTTP/1.1 hop? HIGH when input reaches a header unencoded; read each hit of `grep -rnE "(setHeader|res\.set|headers\[[^]]*\][[:space:]]*=|header\().*(req\.(query|body|params|headers)|request\.(args|form|GET|POST|headers)|\\\$_(GET|POST|REQUEST|SERVER))" --include='*.js' --include='*.ts' --include='*.py' --include='*.php' .`
- [ ] **SQL construction (§2)**: are optional filters served by fixed complete statements (raising when no required criterion is present), stored procedures called through parameterized call APIs with bound dynamic SQL inside, and drivers set to server-side binding where they offer it? HIGH for a concatenated WHERE on an UPDATE/DELETE, MEDIUM for emulated prepares; `grep -rniE "where 1 ?= ?1|[\"'] (and|or) [\"']\.join|\+= *[\"'] (and|or|where) |EMULATE_PREPARES[^;]*(true|1)[[:space:]]*[]);]" --include='*.py' --include='*.php' --include='*.java' --include='*.js' --include='*.ts' --include='*.go' --include='*.cs' --include='*.rb' .`
- [ ] **NoSQL operators (§2)**: are client-supplied `$`-operators rejected by default, request objects never passed as filters, and user text in `$regex` escaped and length-capped? HIGH when a request body reaches a filter or `$where`; read each hit of `grep -rnE "[\"']?\\\$(where|regex|expr|function|accumulator)[\"']?[[:space:]]*:|\.(find|findOne|find_one|aggregate|update_?[Oo]ne|delete_?[Mm]any)\([[:space:]]*(req\.(body|query)|request\.(get_json|json|args))" --include='*.js' --include='*.ts' --include='*.py' --include='*.java' --include='*.php' .`
- [ ] **Redirect sinks (§11)**: is every redirect sink (30x, `Refresh` header, meta refresh, client-side `location`, server-side forward/transfer) fed only a relative path, an allowlisted URL or a non-enumerable server-mapped ID? MEDIUM, HIGH on an OAuth or login flow; every hit of `grep -rniE "http-equiv=[\"']?refresh[^>]*url=[^>]*(\{\{|<\?|\\\$\{|<%)|[\"']Refresh[\"'][[:space:]]*,.*(req|request|params|query)|location(\.href)?[[:space:]]*=[^=].*(searchParams|URLSearchParams|params\.get|location\.(search|hash))|location\.(assign|replace)\(.*(searchParams|params\.get|location\.(search|hash))|getRequestDispatcher\([^)]*getParameter|Server\.(Transfer|Execute)\([^)]*Request" --include='*.html' --include='*.htm' --include='*.jsp' --include='*.php' --include='*.erb' --include='*.js' --include='*.ts' --include='*.java' --include='*.cs' --include='*.aspx' .` needs its source traced
