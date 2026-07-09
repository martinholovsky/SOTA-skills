# 05 — Web Platform Security

Scope: XSS, CSP, CSRF, CORS, clickjacking, security headers, cookies, file uploads.
Maps to OWASP A05/A02/A07:2025, CWE-79/352/942/1021/434/1004.

Core principle: the browser enforces your security policy — but only the policy you
actually declare. Output encoding, headers, cookie attributes, and CORS are
**declarative contracts**; an unset header is a vulnerability you chose by default.

## 1. XSS — context-aware output encoding (CWE-79)

- Encoding must match the **output context**; one HTML-escape pass is not enough:
  - HTML body → HTML-entity encode (`&<>"'`).
  - HTML attribute → quote the attribute AND entity-encode; unquoted attributes
    are injectable via whitespace.
  - JavaScript context → don't put data in script blocks; pass via
    `<script type="application/json" id="data">` + `JSON.parse`, or data
    attributes. If unavoidable: JSON-encode with `<`, `>`, `&`, U+2028/2029
    escaped.
  - URL context → `encodeURIComponent` for components AND validate scheme —
    `javascript:`/`data:` URLs survive entity encoding (allowlist
    `https?:`/relative).
  - CSS context → don't interpolate untrusted data into styles at all.
- Use your framework's auto-escaping templates and audit every bypass:
  `dangerouslySetInnerHTML`, `v-html`, `innerHTML`/`outerHTML`/
  `insertAdjacentHTML`, `bypassSecurityTrustHtml`, Jinja `|safe`, `{!! !!}`,
  `html/template` → `template.HTML(...)` casts. Each one needs sanitization or
  removal.
- DOM XSS: sources (`location.*`, `document.referrer`, `postMessage` data,
  `window.name`) flowing to sinks (`innerHTML`, `eval`, `setTimeout(string)`,
  `document.write`, `location.href=`). Use Trusted Types
  (`require-trusted-types-for 'script'`) to make sink misuse fail loudly.
- Sanitizing rich HTML (user-authored content): DOMPurify (or server-side
  equivalent) with an explicit tag/attribute allowlist; never regex-strip tags.
- `postMessage`: always verify `event.origin` against an allowlist on receive,
  and set explicit `targetOrigin` (never `*`) on send when payload is sensitive.

```jsx
// BAD
<div dangerouslySetInnerHTML={{__html: user.bio}} />
// GOOD
<div>{user.bio}</div>                       // framework escapes
<div dangerouslySetInnerHTML={{__html: DOMPurify.sanitize(user.bio)}} />  // rich text only
```

## 2. Content Security Policy

- CSP is the XSS backstop, not the fix. SOTA policy is **nonce- or hash-based,
  with strict-dynamic** — allowlist-of-domains CSPs are routinely bypassed via
  JSONP/open redirects on allowed CDNs:

```
Content-Security-Policy:
  default-src 'self';
  script-src 'nonce-{random-per-response}' 'strict-dynamic';
  object-src 'none'; base-uri 'none'; frame-ancestors 'none';
  form-action 'self'; upgrade-insecure-requests
```

- Nonce: CSPRNG, per **response** (never static/cached — a cached nonce is no
  nonce). No `unsafe-inline`/`unsafe-eval` in script-src; if a dependency
  demands them, that's a dependency finding.
- `base-uri 'none'` (blocks `<base>` hijack of relative scripts), `object-src
  'none'`, `form-action` (limits credential-phishing form posts even post-XSS).
- Roll out with `Content-Security-Policy-Report-Only` + `report-to` first; then
  enforce. A report-only policy left in place for a year is a finding.

## 3. CSRF (CWE-352)

- Defense stack (use the first two together):
  1. **SameSite=Lax** (or Strict) on session cookies — default in modern
     browsers, set it explicitly anyway.
  2. **Anti-CSRF token** (synchronizer pattern via framework, or signed
     double-submit) on every state-changing request. SameSite alone fails for:
     subdomain-hosted attacker pages, OAuth/POST flows needing `None`, and
     old clients.
  3. Verify `Origin`/`Sec-Fetch-Site` header as cheap defense in depth
     (`Sec-Fetch-Site: cross-site` on a state change → reject).
- State changes only via POST/PUT/PATCH/DELETE — a state-changing GET bypasses
  every CSRF defense (CWE-352 + CWE-650).
- CSRF applies to cookie-authenticated APIs even "JSON-only" ones: verify
  Content-Type server-side, but don't rely on it alone (form-based
  `text/plain` smuggling, Flash-era lessons). Bearer-token-in-header APIs are
  inherently CSRF-immune — one reason to prefer them for SPAs.
- Login CSRF is real (attacker logs victim into attacker's account to harvest
  data): protect the login form too.

```python
# GOOD: layered CSRF check (framework token + fetch-metadata backstop)
@app.before_request
def csrf_guard():
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return                                    # and GETs never mutate state
    if request.headers.get("Sec-Fetch-Site") not in (None, "same-origin", "same-site"):
        abort(403)                                # cheap, header is browser-enforced
    validate_csrf_token(request)                  # framework synchronizer token
```

```text
# Signed double-submit (when server-side token storage is impractical):
cookie:  __Host-csrf = HMAC(key, session_id) ‖ session_id-binding
request: X-CSRF-Token header must equal the cookie value, verified server-side
# naive double-submit (random cookie == param, unsigned, unbound) is bypassable
# via cookie injection from subdomains/MITM — bind to the session and sign.
```

## 4. CORS (CWE-942)

- CORS **relaxes** the same-origin policy; it never adds protection. Misconfig
  checklist:
  - `Access-Control-Allow-Origin: *` with `Allow-Credentials: true` — invalid
    combo, but reflecting the request `Origin` header to simulate it is the
    classic critical: any site reads authenticated responses.
  - Origin validation by substring/regex: `origin.includes("trusted.com")`
    matches `evil-trusted.com.attacker.io`. **Exact-match against an
    allowlist**, scheme included (`https://app.example.com`).
  - `null` origin allowed (sandboxed iframes/file:// can send it) — never
    allowlist `null`.
- Keep `Allow-Methods`/`Allow-Headers` minimal; don't blanket-allow `*` on a
  credentialed API. Cache poisoning: include `Vary: Origin`.
- CORS preflights don't protect WebSockets — validate `Origin` on the WS
  handshake yourself (cross-site WebSocket hijacking).
- **XSSI (cross-site script inclusion, CWE-829):** a foreign page can `<script
  src>`-include a GET endpoint that returns sensitive data as JS/JSONP/array
  literal and read it. Serve data as `application/json` (never executable JS),
  require auth + anti-CSRF on data endpoints, don't expose JSONP, and where the
  legacy risk exists prefix JSON with an unparseable guard (`)]}',\n`). `nosniff`
  (§6) backs this up.

## 5. Clickjacking & framing (CWE-1021)

- `frame-ancestors 'none'` in CSP (authoritative) plus `X-Frame-Options: DENY`
  for legacy. If embedding is a feature, allowlist exact embedding origins via
  `frame-ancestors`.
- For OAuth consent screens, payment confirmations, and account-change pages,
  framing protection is mandatory, not optional.
- **Double-clickjacking** (2024-class) bypasses `frame-ancestors`/XFO entirely —
  it uses a timed window swap during a double-click rather than a persistent
  frame, so framing headers never fire. Defend sensitive one-click actions
  (OAuth "Authorize", account/payment/permission changes) with an
  interaction-gated confirmation step (re-auth, an explicit second action, or a
  short delay before the control is live), not framing headers alone. Disabling
  unintended same-window opener access (`SameSite` cookies, `noopener`) helps.

## 6. Security headers (baseline set)

```
Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
Content-Security-Policy: (see §2)
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Resource-Policy: same-origin   (relax deliberately per-resource)
Cache-Control: no-store                      (on authenticated/personal responses)
```

- HSTS without `includeSubDomains` leaves cookie-injection via insecure
  subdomains; preload only when all subdomains are HTTPS-ready.
- `nosniff` is what makes your upload Content-Type discipline (§10) stick.
- Remove fingerprint headers (`Server`, `X-Powered-By`) — low value but free.
- COOP/COEP additionally gate cross-origin isolation (Spectre-class leaks) for
  apps using SharedArrayBuffer.

## 7. Cookies (CWE-1004/614/565)

- Session/auth cookies: `__Host-` prefix + `Secure` + `HttpOnly` +
  `SameSite=Lax|Strict` + `Path=/`, no `Domain` attribute. The `__Host-` prefix
  makes the browser enforce Secure/no-Domain/Path=/ — subdomain takeover can't
  plant or override the cookie.
- `HttpOnly` on anything a script doesn't need; CSRF tokens are the usual
  legitimate non-HttpOnly exception (double-submit reads).
- Broad `Domain=.example.com` cookies are readable/settable by every subdomain —
  one XSS'd or taken-over subdomain compromises all (CWE-565 trust issues).
  Scope to the host unless sharing is a designed requirement.
- Never store authorization-relevant state client-side unsigned (e.g.
  `is_admin=1` cookie); signed cookies must also be encrypted if contents are
  sensitive, and validated server-side per request.
- Size/count discipline: cookies ride every request — keep tokens, not data.

## 8. Third-party scripts & embeds in the browser

- Every third-party `<script src>` runs with your origin's full authority —
  analytics/tag-manager compromise = Magecart. Minimize; self-host pinned
  copies where possible; **Subresource Integrity** (`integrity=sha384-...`,
  `crossorigin=anonymous`) for anything static from a CDN; nonce-based CSP
  (§2) limits what an injected/compromised script can load next.
- Tag managers are remote-code-execution-as-a-service for marketing — gate
  container changes with review, exclude payment/auth pages from them
  entirely (also a PCI DSS 4.0.1 §6.4.3/11.6.1 requirement, mandatory since
  March 2025: script inventory + integrity monitoring on payment pages).
- Embedding untrusted content: `<iframe sandbox>` (no `allow-same-origin` +
  `allow-scripts` together on same-site content — that nullifies the sandbox),
  minimal `allow=` permissions; untrusted HTML never via `srcdoc` without
  sanitization.
- OAuth popups/postMessage bridges: see §1 `postMessage` rules; verify opener
  relationships, use COOP to sever unwanted window handles.

## 9. Caching attacks

- **Web cache deception**: `/account.php/style.css` cached by path-suffix rules
  → attacker fetches victim's cached account page. Only cache responses the
  origin explicitly marks cacheable; `Cache-Control: no-store, private` on all
  authenticated/personalized responses; CDN cache keys must match the origin's
  notion of the resource.
- **Cache poisoning**: any request input that affects the response but isn't
  in the cache key (headers like `X-Forwarded-Host`, `X-Original-URL`,
  unkeyed query params) lets an attacker poison the shared cache. Don't
  reflect unkeyed inputs; `Vary` on what you use; strip override headers at
  the edge (rules/01 §11 Host-header rules apply).
- Browser-side: `Cache-Control: no-store` for sensitive pages also defends
  shared-computer history attacks; pair with `Clear-Site-Data: "*"` on logout
  for high-sensitivity apps.

## 10. File upload handling (CWE-434)

- Validate by **content**, not trust: check magic bytes/parse the file with a
  real decoder; the client `Content-Type` and filename extension are
  attacker-controlled.
- Allowlist extensions AND served content types. Reject double extensions
  (`shell.php.jpg`), trailing dots/spaces, NUL tricks; **generate the stored
  filename yourself** (UUID), keep the original only as metadata (also kills
  path traversal, rules/01 §4).
- Store outside the web root, or in object storage with no execute semantics.
  Never in a directory where the app server executes code (the classic
  webshell: upload `x.php` into `/uploads` served by PHP).
- Serve with: `Content-Type` you determined, `X-Content-Type-Options: nosniff`,
  `Content-Disposition: attachment` for anything not explicitly displayable,
  and ideally from a **separate origin/sandbox domain** (usercontent.example) so
  HTML/SVG payloads can't script against your app origin. SVG is XSS-capable —
  sanitize or serve as attachment.
- Limits: max size (enforced streaming, before buffering whole body), max
  files/request, rate limits; image processing in a sandboxed/least-privilege
  worker (decoder CVEs: ImageTragick lineage) with decompression-bomb caps
  (pixel-count limit before decode).
- Scan where threat model warrants (AV/CDR for shared-file features); strip
  metadata (EXIF GPS) from re-served images (privacy, rules/07).

## Audit checklist

- [ ] Is all output encoded for its exact context, with every auto-escape bypass (`innerHTML`, `|safe`, `dangerouslySetInnerHTML`) justified and sanitized?
- [ ] Is rich-text HTML sanitized with an allowlist sanitizer (DOMPurify-class), never regex?
- [ ] Is CSP nonce/hash-based with `strict-dynamic`, no `unsafe-inline`/`unsafe-eval`, per-response nonces, and actually enforcing (not report-only)?
- [ ] Do all state-changing endpoints require non-GET methods plus CSRF tokens, with SameSite cookies as the second layer?
- [ ] Does `postMessage` handling verify `event.origin`, and WS handshakes verify `Origin`?
- [ ] Is CORS exact-match allowlisted (no reflection, no `null`, no substring matching), with `Vary: Origin`?
- [ ] Are `frame-ancestors`/XFO set, especially on auth and confirmation pages?
- [ ] Is the full header baseline present (HSTS w/ includeSubDomains, nosniff, Referrer-Policy, COOP) and `Cache-Control: no-store` on personal data?
- [ ] Do session cookies use `__Host-` prefix, Secure, HttpOnly, SameSite, host-scoped?
- [ ] Are uploads content-validated, renamed server-side, stored non-executable (ideally separate origin), size-capped pre-buffer, and served with nosniff + attachment disposition?
- [ ] Are SVGs sanitized or never served inline from the app origin?
- [ ] Do third-party scripts carry SRI or self-hosted pins, with tag managers excluded from auth/payment pages?
- [ ] Are authenticated responses `no-store`/`private` with cache keys covering every response-affecting input (no unkeyed header reflection)?
- [ ] Are sandboxed iframes used for untrusted embeds without `allow-scripts`+`allow-same-origin` together?
