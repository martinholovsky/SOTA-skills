# 05 — Web Platform Security

Scope: XSS, CSP, CSRF, CORS, clickjacking, security headers, cookies (file uploads: rules/21).
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
    `javascript:`/`vbscript:`/`data:` URLs survive entity encoding (allowlist
    `https?:`/relative) — after decoding character references (decimal, hex,
    zero-padded, unterminated) and rejecting NUL, on every URL-bearing attribute
    (`href`, `src`, `action`, `formaction`, `xlink:href`, `background`, object
    `data`, CSS `url()`). Decode CSS escapes and comments before vetting CSS.
  - CSS context → don't interpolate untrusted data into styles at all.
  - **Contexts no encoding makes safe**: untrusted data never becomes a tag
    name, an attribute *name*, HTML-comment content, or the value of an
    event-handler (`on*`) or other script-taking attribute — the browser
    compiles an `on*` value as a JS function body, entity-encoded or not.
    `setAttribute(name, v)` only with a hard-coded, harmless `name`; write
    text with `textContent` and styles with `el.style.prop = v`, not
    `innerHTML`/`setAttribute("style", …)`. Validate ambiguous attributes
    (`id`/`name` — DOM clobbering — `href`, `src`, `background`) against a
    strict pattern. OWASP: XSS Prevention, DOM based XSS Prevention cheat sheets.
  - **Encoding mechanics** (where no auto-escaper applies): allowlist encoders
    that escape every non-alphanumeric — `&#xHH;` in attributes, `\xHH`/`\uHHHH`
    in JS strings (backslash-quoting alone breaks out), `\HH ` in CSS. Nested
    contexts encode innermost-first: a URL in an attribute is component- then
    attribute-encoded; data a script writes to an HTML sink is HTML- then
    JS-encoded. Encode in code you trust, server-side or at the sink; XHTML
    pages decode entities inside `<script>`. OWASP: XSS Filter Evasion cheat
    sheet; Code Review Guide v2; Secure Coding Practices QRG.
- Use your framework's auto-escaping templates and audit every bypass:
  `dangerouslySetInnerHTML`, `v-html`, `innerHTML`/`outerHTML`/
  `insertAdjacentHTML`, `bypassSecurityTrustHtml`, Jinja `|safe`, `{!! !!}`,
  `html/template` → `template.HTML(...)` casts. Each one needs sanitization or
  removal.
- DOM XSS: sources (`location.*`, `document.referrer`, `postMessage` data,
  `window.name`, `EventSource`/WebSocket message data) flowing to sinks
  (`innerHTML`, `eval`, `setTimeout(string)`, `document.write`,
  `location.href=`). Use Trusted Types (`require-trusted-types-for 'script'`)
  to make sink misuse fail loudly; for legacy code, a strict, temporary
  `trustedTypes.createPolicy('default', …)` sanitizes or rejects leftover
  strings — a pass-through one cancels the enforcement (Trusted Types spec).
- **DOM-sourced request targets (client-side CSRF)**: the same sources must
  not choose the URL, method or body of `fetch`/XHR, nor the `src` of a
  `<script>`/`<iframe>`. The request carries the victim's cookies and passes
  every same-origin check (`Sec-Fetch-Site: same-origin`) because *your* page
  sent it. If input must steer a request, use it as a key into a hard-coded
  table of endpoints and parameters (never string-build the URL), under a
  fixed path prefix, for non-state-changing calls only. OWASP: CSRF
  Prevention cheat sheet, WSTG-CLNT-06.
- Sanitizing rich HTML (user-authored content): DOMPurify (or server-side
  equivalent) with an explicit tag/attribute allowlist; never regex-strip tags.
  - **Every user markup format goes through it.** Markdown, BBCode, wiki
    markup and user CSS are not inert: render, then sanitize the *output
    HTML*, with the renderer's raw-HTML passthrough off and link/image
    schemes allowlisted. markdown-it's default preset has `html: false`, but
    its `commonmark` preset turns raw HTML on; unified's
    `rehype-stringify` `allowDangerousHtml` emits it. User CSS gets a
    property allowlist, or is refused.
  - **Sanitize last.** Nothing — your code or a later library (template
    post-processing, link rewriting, minifying) — may change the markup
    between sanitizing and insertion; re-parsing altered markup is how
    mutation XSS returns (DOMPurify's README warns of exactly this). For new
    rich-text features prefer a restricted markup language with raw HTML off
    over accepting sanitized HTML. OWASP: ASVS 5.0 V1.3.5; XSS Prevention,
    Ruby on Rails cheat sheets.
- `postMessage`: always verify `event.origin` against an allowlist on receive,
  and always send with an exact `targetOrigin`, never `*`, whatever the payload.
  `window.open` to a URL you don't control passes `noopener,noreferrer`.
  OWASP: HTML5 Security, XS Leaks cheat sheets.

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
- Roll out with `Content-Security-Policy-Report-Only` first; then enforce, and
  keep reporting on the enforced policy (`Reporting-Endpoints` + `report-to`,
  `report-uri` as the deprecated fallback). A report-only policy left in place
  for a year is a finding. The collector keeps `effective-directive`,
  `blocked-uri` and `disposition` and strips query strings from URL fields —
  browsers remove only fragments and credentials (CSP3). OWASP: ASVS 5.0
  V3.4.7; CSP, Logging Vocabulary cheat sheets.
- Tighten past scripts where feasible: `default-src 'none'` plus a source per
  type, `frame-src`/`child-src` for what may be embedded, no `'unsafe-inline'`
  in `style-src`; move inline `on*=` handlers to `addEventListener` (a nonce
  cannot cover an attribute). Check each policy with a CSP evaluator. CSP does
  not stop DOM clobbering or reuse of script gadgets that are allowed to run.
  OWASP: CSP, DOM Clobbering Prevention cheat sheets; Proactive Controls 2024 C8.
- User files and API responses a browser may open directly get the header
  `Content-Security-Policy: sandbox` (opaque origin, no scripts; ignored in
  `<meta>` and report-only). The iframe `sandbox` attribute is a second layer
  only: untrusted content still gets its own origin (rules/21 §1) and is not rendered
  where sandboxing is unavailable. OWASP: ASVS 5.0 V3.2.1; HTML5 Security cheat sheet.
- Deployment pitfalls: a `<meta http-equiv>` policy ignores `frame-ancestors`,
  `sandbox` and `report-uri`, cannot be report-only, and covers only markup
  after it (CSP3) — deliver by header wherever you control one. Never nonce
  with middleware that stamps every `<script>` in the output: it nonces
  injected scripts too; add the nonce in the template at each trusted tag.
  Write a policy per app, not one blanket org-wide CSP that accumulates every
  app's sources. `*.example.com` in *any* directive (img, connect, frame, not
  just script) trusts every subdomain, a taken-over one included. OWASP: CSP,
  XSS Prevention, Subdomain Takeover Prevention cheat sheets.

## 3. CSRF (CWE-352)

- Defense stack (use the first two together):
  1. **SameSite=Lax** (or Strict) on session cookies — default in modern
     browsers, set it explicitly anyway.
  2. **Anti-CSRF token** (synchronizer pattern via framework, or signed
     double-submit) on every state-changing request. SameSite alone fails for:
     subdomain-hosted attacker pages, OAuth/POST flows needing `None`, and
     old clients.
  3. Fetch Metadata + source-origin check as defense in depth (policy in the
     code below). Source origin = `Origin`, else the origin of `Referer`,
     compared **exactly** (scheme+host+port) with the configured target
     origin(s), never by prefix or substring. `Origin: null` is untrusted;
     a state change with neither header is blocked on sensitive endpoints
     (log-then-block while rolling out). A page served with
     `Referrer-Policy: no-referrer` makes the browser send `Origin: null` on
     its own non-CORS POSTs (Fetch spec) — rely on `Sec-Fetch-Site` + token
     there. A Referer check alone is weak: policies and privacy tools strip
     it. OWASP: CSRF Prevention cheat sheet, Code Review Guide v2.
- State changes only via POST/PUT/PATCH/DELETE — a state-changing GET bypasses
  every CSRF defense (CWE-352 + CWE-650).
- CSRF applies to cookie-authenticated APIs even "JSON-only" ones: verify
  Content-Type server-side, but don't rely on it alone (form-based
  `text/plain` smuggling, Flash-era lessons). Bearer-token-in-header APIs are
  inherently CSRF-immune — one reason to prefer them for SPAs.
- Login CSRF is real (attacker logs victim into attacker's account to harvest
  data). No session exists yet, so issue a pre-session carrying its own token
  on the login form (or require a custom header on a same-origin `fetch`), then
  regenerate the session ID on login (rules/17 §2).
- **Not defenses** on their own: a secret cookie, POST-only, multi-step flows,
  URL rewriting, HTTPS, CAPTCHA. For `fetch`/XHR send the token in a custom
  header; a script-readable token never contains the raw session ID.
- **SPA client half**: token in a `<meta>` tag or JS variable, not Web Storage,
  added on unsafe methods by one HTTP-client interceptor — Angular `HttpClient`
  (`withXsrfConfiguration`; skips GET/HEAD and cross-origin URLs) or axios
  (`XSRF-TOKEN` cookie → `X-XSRF-TOKEN`, same-origin only; `withXSRFToken:
  true` sends it to every origin). OWASP: CSRF Prevention cheat sheet.

```python
# GOOD: Fetch Metadata policy -> Origin/Referer fallback -> token, failing closed
@app.before_request
def csrf_guard():
    h = request.headers
    site = h.get("Sec-Fetch-Site")
    if site not in ("same-origin", "same-site", "cross-site", "none"):
        site = None          # absent (plain HTTP, old client) or undefined value: ignore
    if request.method in ("GET", "HEAD", "OPTIONS"):   # GETs never mutate state
        if site == "cross-site" and NOT_EMBEDDABLE and not (  # resource isolation
                h.get("Sec-Fetch-Mode") == "navigate" and h.get("Sec-Fetch-Dest") == "document"):
            abort(403)       # cross-site only as a top-level navigation
        return
    if site == "same-origin" or (site == "same-site" and TRUST_SIBLING_SUBDOMAINS):
        pass
    elif site is not None:   # cross-site, untrusted same-site, "none" (typed URL/bookmark
        abort(403)           # is a user navigation, never a legitimate POST)
    elif not source_origin_matches(request, settings.EXPECTED_ORIGINS):  # item 3
        abort(403)           # no metadata: do NOT fall straight through to the token
    validate_csrf_token(request)                  # framework synchronizer token
```

`Sec-Fetch-User: ?1` arrives only on navigations with user activation — require
it where a sensitive flow must start from a real click. (OWASP: CSRF Prevention
cheat sheet; values per the W3C Fetch Metadata spec.)

```text
# Signed double-submit (when server-side token storage is impractical):
issue:  nonce = CSPRNG(>=128 bit); mac = HMAC(key, len(sid) ‖ sid ‖ nonce)
        token = nonce ‖ mac  -> cookie __Host-csrf AND page/form field
verify: take the token from the header/form field, split it, recompute the HMAC
        over the CURRENT session id + that nonce, constant-time compare;
        also require it to equal the cookie
# header == cookie alone proves nothing: a subdomain or MITM that can plant a
# cookie plants a matching pair. The MAC bound to the current session is the check.
```

- Token lifecycle: a CSRF token lives as long as its session (rotate it with
  the session id at login and privilege change) and carries no timestamp
  expiry of its own — the scoped exception to rules/04 §7 "verify expiry".
  Per-request tokens are stricter but break Back and multi-tab use; keep
  them for high-value forms. On failure return `403`, log a suspected-CSRF
  security event (user, route, `Origin`), optionally rotate the token. A
  Fetch Metadata/Origin reject and a disallowed CORS origin log the same way,
  with the reason (`malicious_csrf`, `malicious_cors`; rules/07 §2.1).
  OWASP: CSRF Prevention, Logging Vocabulary cheat sheets; Code Review Guide v2.
- **Behind reverse proxies**: the *expected* origin (scheme+host+port) comes
  from server config, never from `Host`/`X-Forwarded-Host`. Trust
  `X-Forwarded-Proto`/`-Host` only when your own proxy sets them and strips
  client copies (sota-network-security rules/05 R6) — e.g. Django
  `SECURE_PROXY_SSL_HEADER`/`USE_X_FORWARDED_HOST`, Express `trust proxy`.
  Proxies, gateways and load balancers must pass `Origin` and `Sec-Fetch-*`
  through unchanged; one that strips them sends every request down the
  fallback path. OWASP: CSRF Prevention, Django Security cheat sheets.

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
  credentialed API. Cache poisoning: include `Vary: Origin`. Emit CORS headers
  only on routes that must be read cross-origin, never domain-wide; refuse
  plain-HTTP requests carrying an `https://` `Origin`. OWASP: Code Review Guide v2.
- CORS preflights don't protect WebSockets — validate `Origin` on the WS
  handshake yourself (cross-site WebSocket hijacking).
- **Host allowlist (DNS rebinding)**: the same-origin policy keys on the
  *name*, so an attacker's domain that re-resolves to `127.0.0.1` or an
  internal IP is same-origin with your service — and the request still
  carries the attacker's name in `Host`. Every web app, above all one bound
  to localhost or an internal network (dev servers, admin UIs, local agents,
  MCP servers — sota-llm-engineering rules/04), rejects a `Host` that is
  not an expected name: e.g. Django `ALLOWED_HOSTS` (never `'*'`), Vite
  `server.allowedHosts` (never `true`), webpack-dev-server `allowedHosts`
  (never `'all'`). Authenticate the local listener as well. OWASP:
  Proactive Controls 2024 C8.
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
- Pitfalls (CSP3, HTML spec): `frame-ancestors` does **not** fall back to
  `default-src`, and is ignored in a `<meta>` CSP — a static/SSG site sets it
  as a response header at the host or CDN. Keywords are quoted (`'none'`,
  `'self'`; bare `none` is read as a host name); allowed framers are full
  `https://` origins. An enforced `frame-ancestors` makes browsers ignore
  XFO. Send XFO once, as `DENY` or `SAMEORIGIN`: `ALLOW-FROM` and unknown
  values count as no header, and with several values the result depends on
  the mix (all-invalid = framing allowed) — check that app and proxy don't
  both add it.
- JS frame-busting (`if (top !== self) top.location = …`) is not a control:
  an `<iframe sandbox>` without `allow-top-navigation` simply blocks it. A
  page that must stay frameable puts sensitive actions behind a step the
  framer cannot drive (re-auth, or a new top-level window). OWASP:
  Clickjacking Defense, CSP cheat sheets; Proactive Controls 2024 C8.
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
Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=(), usb=()  (every unused feature)
Content-Type: text/html; charset=utf-8       (explicit on every response)
X-XSS-Protection: 0                          (or omit; never "1; mode=block")
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Resource-Policy: same-origin   (relax deliberately per-resource)
Cache-Control: no-store                      (on authenticated/personal responses)
```

- HSTS without `includeSubDomains` leaves cookie-injection via insecure
  subdomains; preload only when all subdomains are HTTPS-ready.
- Pages whose URL carries a secret (password reset, magic link, OAuth
  callback) send `Referrer-Policy: no-referrer`: the baseline still sends the
  full URL on same-origin requests, and a `referrerpolicy` attribute on an
  element can widen it. Load no third-party resources there, and redirect to
  a token-free URL once the token is consumed (rules/02 §5). Forms on such a
  page POST with `Origin: null` (§3). OWASP: Forgot Password cheat sheet,
  Secure Headers Project.
- `nosniff` is what makes your upload Content-Type discipline (rules/21 §1) stick.
- Remove fingerprint headers (`Server`, `X-Powered-By`) — low value but free.
- Cross-origin isolation (Spectre-class leaks; needed for SharedArrayBuffer):
  COOP plus COEP `require-corp` (or `credentialless`); each allowed cross-origin
  subresource then needs a `crossorigin` attribute (CORS) or a CORP header.
- Text types carry `charset=utf-8` (a guessed charset lets UTF-7-class input
  pass the escaper); unknown/binary user files go out as `application/octet-stream`.
  The retired XSS auditor could itself leak, hence `0`. Unused features stay
  denied (`fullscreen`, `serial`, `hid`, sensors…), re-enabled one at a time.
  **No mixed content**: no `http://` script, style, frame, image, form or link on
  an HTTPS page — `upgrade-insecure-requests` is a safety net, not the fix;
  plain-HTTP content lives on another host. OWASP: HTTP Headers, HSTS, TLS
  cheat sheets; Secure Headers Project.

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
- **One app per hostname.** The origin (scheme+host+port) is the only browser
  boundary between apps: Web Storage, script-readable cookies and DOM access
  are shared by everything on it. Separate apps, and apps of different trust
  (admin vs user, user content vs app), get distinct hostnames. Cookie `Path`
  is **not** a boundary — script on `/app-b` can reach `/app-a`'s cookies —
  and cookies don't isolate by port either (RFC 6265, section 8.5), so path-prefixed
  apps or two ports on one host are one trust zone. OWASP: ASVS 5.0 V3.5.4;
  Session Management, HTML5 Security cheat sheets; Proactive Controls 2024
  C7; Code Review Guide v2.
- Never store authorization-relevant state client-side unsigned (e.g.
  `is_admin=1` cookie); signed cookies must also be encrypted if contents are
  sensitive, and validated server-side per request.
- Size/count discipline: cookies ride every request — keep tokens, not data;
  name + value over 4096 bytes is dropped silently (RFC 6265bis). **Every**
  cookie is `Secure` (`__Secure-` where `__Host-` can't apply; `__Host-` forces
  `Path=/`). Session cookies carry no `Expires`/`Max-Age` (remember-me: rules/17
  §2), reach the client only via `Set-Cookie` (never a response body), one header
  per cookie, under a non-default name (not `JSESSIONID`/`PHPSESSID`), one name
  per cookie across paths/domains; inventory them. OWASP: ASVS 5.0 V3.3.1/4/5.

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
  Narrow what a tag may touch: the host page builds a data layer holding just
  the values vendors need, validating any user-controlled input (URL params,
  form fields) on the way in, and tags read that — never the DOM, cookies or
  URL directly. Switch off tag types that run arbitrary code (e.g. Google Tag
  Manager: `gtm.blocklist` with `customScripts`, which covers Custom HTML
  tags). The console is a production deploy path: named accounts with MFA
  (GTM can demand 2-step verification before Custom HTML/JS or user settings
  change), publish rights for a few, changes reviewed like a release. OWASP:
  Third Party Javascript Management cheat sheet.
- **Vet before adding, watch after.** Before including a vendor script, review
  what it reads, where it sends data and what it writes to the DOM, and who
  controls its serving domain: a domain that is sold, or lapses and is
  re-registered, hands the new owner script execution on every including site
  (polyfill.io, bought in 2024, then served malware to 100k+ sites — Sansec).
  Afterwards monitor every third-party script's content for change as
  routine, not only on PCI pages: an SRI-pinned file then fails visibly when
  the vendor updates it, and an unpinned one cannot drift unseen. OWASP:
  Third Party Javascript Management cheat sheet.
- Embedding untrusted content: `<iframe sandbox>` (no `allow-same-origin` +
  `allow-scripts` together on same-site content — that nullifies the sandbox),
  minimal `allow=` permissions; untrusted HTML never via `srcdoc` without
  sanitization.
- **Contain a vendor script you cannot vet** in a sandboxed iframe served from
  a separate registrable domain (a sibling subdomain can still receive
  parent-domain cookies): it cannot reach the host DOM, cookies or storage, and
  talks to the page only by `postMessage`, the receiver checking `event.origin`
  exactly and each message against a fixed schema (§1). Worker offloading
  (Partytown-class) is a speed tool, not a boundary: a worker script must be
  same-origin, so it keeps your `fetch` (cookies sent by default) and
  IndexedDB, and the proxy forwards DOM calls unless configured to refuse
  them. OWASP: Third Party Javascript Management cheat sheet.
- OAuth popups/postMessage bridges: see §1 `postMessage` rules; verify opener
  relationships, use COOP to sever unwanted window handles.

## 9. Caching attacks

- **Web cache deception**: `/account.php/style.css` cached by path-suffix rules
  → attacker fetches victim's cached account page. Only cache responses the
  origin explicitly marks cacheable; `Cache-Control: no-store, private` on all
  authenticated/personalized responses; CDN cache keys must match the origin's
  notion of the resource. Origin half: a path that does not exist —
  `/account/x.css`, `/account;x.css`, `/account%2Fx.css` — gets `404` (or a
  redirect), never the `/account` page; routing that ignores trailing
  segments is what lets a static-extension CDN rule store private content.
  OWASP: ASVS 5.0 V14.2.5.
- **One path, one meaning**: every component that decides on a path (authz
  rules, router, cache key, WAF, proxy) normalises trailing slashes, case,
  percent-encoding (double encoding too), `;` parameters and dot-segments
  identically — or the edge normalises once and rejects non-canonical paths.
  Test it: send variants of a protected path through the whole chain and
  assert every component reaches the same decision (rules/01 §4, §11 parser
  differentials). OWASP: WSTG-CONF-13.
- **Cache poisoning**: any request input that affects the response but isn't
  in the cache key (headers like `X-Forwarded-Host`, `X-Original-URL`,
  unkeyed query params) lets an attacker poison the shared cache. Don't
  reflect unkeyed inputs; `Vary` on what you use; strip override headers at
  the edge (rules/01 §11 Host-header rules apply).
- Browser-side: `Cache-Control: no-store` for sensitive pages also defends
  shared-computer history attacks (`no-cache` still permits storing, RFC 9111
  section 5.2.2.4); pair with `Clear-Site-Data: "*"` on logout for high-sensitivity
  apps, and also clear Web Storage, IndexedDB and sensitive DOM from client code
  (works offline). No PII/financial data there. OWASP: ASVS 5.0 V14.3.1, V14.3.3.

File upload handling (formerly section 10) moved to [rules/21](21-file-uploads.md) §1 on 2026-09-25.

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
- [ ] Do third-party scripts carry SRI or self-hosted pins, with tag managers excluded from auth/payment pages?
- [ ] Are authenticated responses `no-store`/`private` with cache keys covering every response-affecting input (no unkeyed header reflection)?
- [ ] Are sandboxed iframes used for untrusted embeds without `allow-scripts`+`allow-same-origin` together?
- [ ] **Unencodable DOM contexts — HIGH**: no untrusted attribute/tag names or `on*`/`style` values via `setAttribute`: `grep -rnEi -- "setAttribute\([[:space:]]*([A-Za-z_][A-Za-z0-9_.]*|['\"](on[a-z]+|style|href|src|srcdoc|formaction)['\"])[[:space:]]*," .` — each hit needs a literal harmless name or a validated value.
- [ ] **DOM-sourced request target — HIGH**: `grep -rnEi -- "(fetch|\.open|axios[.a-z]*)\(.*(location\.|document\.referrer|window\.name|event\.data)|\.src[[:space:]]*=[^=].*(location\.|document\.referrer|window\.name|event\.data)" .` — a hit that builds the URL rather than looking it up in a fixed table is a client-side CSRF/script-injection finding.
- [ ] **Raw HTML through a markup renderer, or post-sanitize edits — HIGH**: `grep -rnEi -- "html:[[:space:]]*true|['\"]commonmark['\"]|allowDangerousHtml|sanitize\(.*\)\.(replace|concat)\(" .` — every user-markup path renders then sanitizes the output, and nothing alters it after.
- [ ] **CSP delivery — MEDIUM**: `grep -rnEi -- "http-equiv=['\"]?Content-Security-Policy|-src[^;]*[[:space:]](https?://)?\*\.|replace\(.*<script" .` — meta-delivered policy where a header is possible, `*.` host wildcards in any directive, or nonce-stamping by rewrite.
- [ ] **Fetch Metadata fails open — HIGH**: `grep -rnEi -- "sec-fetch-site[^#]*[(,[:space:]](none|null|undefined)[,)]|sec-fetch-site['\"][[:space:]]*,[[:space:]]*['\"]same-|sec-fetch-site['\"]\)[[:space:]]*&&" .` — an absent header passes, or defaults to same-origin, instead of falling back to the Origin check.
- [ ] **Origin/Referer prefix match — HIGH**: `grep -rnEi -- "(origin|referer|referrer)[^;]*\.(startswith|includes|indexof|contains|endswith)\(|['\"][[:space:]]+in[[:space:]]+[^;]*(referer|origin)" .` — source origin must equal a configured origin exactly.
- [ ] **Double-submit compares header to cookie only — HIGH**: `grep -rnEi -- "(csrf|xsrf)[^;]*(!==?|===?)[^;]*cookie|cookie[^;]*(!==?|===?)[^;]*(csrf|xsrf)|(compare_digest|equals|timingSafeEqual)\([^;]*cookie" .` — acceptable only if a session-bound HMAC is also recomputed.
- [ ] **Forwarded headers trusted wholesale — HIGH**: `grep -rnEi -- "USE_X_FORWARDED_HOST[[:space:]]*=[[:space:]]*True|trust proxy['\"][[:space:]]*,[[:space:]]*true|://[^;]*X-Forwarded-Host" .` — each hit needs a proxy that strips client copies; expected origins come from config.
- [ ] **Any Host accepted (DNS rebinding) — HIGH on localhost/internal apps**: `grep -rnEi -- "ALLOWED_HOSTS[[:space:]]*=[[:space:]]*\[[[:space:]]*['\"]\*['\"]|allowedHosts['\"]?[[:space:]]*:[[:space:]]*(true|['\"]all['\"])" .`; a server with no Host check at all is the same finding.
- [ ] **Framing-control defects — MEDIUM (HIGH on auth/consent pages)**: `grep -rnEi -- "http-equiv=[^>]*frame-ancestors|frame-ancestors[[:space:]]+(none|self)|ALLOW-FROM|top\.location[^=]*=[^=]|top[[:space:]]*!==?[[:space:]]*(window\.)?self" .` — meta or unquoted `frame-ancestors`, `ALLOW-FROM`, or JS frame-busting relied on.
- [ ] **Referrer widened, or token pages leak — MEDIUM**: `grep -rnEi -- "referrerpolicy=['\"]?(unsafe-url|origin-when-cross-origin|no-referrer-when-downgrade)|Referrer-Policy:[[:space:]]*(unsafe-url|no-referrer-when-downgrade|origin-when-cross-origin)" .`; and do reset/magic-link/callback pages send `no-referrer`?
- [ ] **Path used as an app boundary — MEDIUM**: `grep -rnEi -- "cookie.*path['\"]?[[:space:]]*[:=][[:space:]]*['\"]?/[A-Za-z0-9_-]" .` — a path-scoped session cookie usually means several apps share one origin; they need separate hostnames.
- [ ] **Unpinned or unvetted vendor script — MEDIUM**: `grep -rnEi -- "<script[^>]*src=['\"]?https?://" . | grep -vi 'integrity='` — each remaining hit has a vetted owner/domain and content-change monitoring.
- [ ] **Tag manager runs arbitrary code — HIGH**: `grep -rlEi -- "googletagmanager\.com/gtm\.js" . | xargs -r grep -LEi -- "gtm\.blocklist[^]]*(customScripts|['\"]html['\"])"` — each file loads a container with no custom-code block; also confirm console MFA and a data-layer-only tag design.
- [ ] **Vendor script "sandboxed" in a worker — MEDIUM**: `grep -rnEi -- "type=['\"]?text/partytown|<Partytown" .` — a vendor that must be contained runs in a separate-domain iframe instead; the worker keeps your origin.
- [ ] **Retired subdomain still trusted — HIGH** (sota-network-security rules/06 R4, sota-identity-access rules/01): `grep -rnEi -- "(redirect_?uris?|allowed_?origins|cors_?origins|-src[[:space:]])[^#]*[a-z0-9-]\.[a-z]{2,}" .` — every host listed resolves to a live, owned service; a name gone from DNS is purged from redirect-URI, CSP and CORS lists in the same change.
- [ ] **Web cache deception, origin half — HIGH**: `curl -s -o /dev/null -w '%{http_code}\n' -b "$SESSION" https://HOST/account/x.css` (and `/account;x.css`) returns `404`/redirect, not `200` with the account page.
- [ ] **Path-normalisation disagreement — HIGH**: a test sends variants of a protected path (`/admin/`, `/ADMIN`, `/%61dmin`, `/x/../admin`, `/admin;x`) through CDN, proxy, WAF and app and asserts the same allow/deny at each — sent raw (`curl --path-as-is`), or the client itself collapses `/x/../admin` to `/admin` and the variant is never tested.
- [ ] **CSRF token leaves the origin or sits in storage — HIGH**: `grep -rnEi -- "withXSRFToken[[:space:]]*:[[:space:]]*true|(localStorage|sessionStorage)\.setItem\([^)]*(csrf|xsrf)" .` — the token rides only same-origin requests, from a meta tag or memory.
- [ ] **Cross-window leaks — MEDIUM**: `grep -rnEi -- "postMessage\(.*,[[:space:]]*['\"]\*['\"]|window\.open\(" . | grep -vi noopener` — every send names an exact `targetOrigin`; every `window.open` to a foreign URL passes `noopener`.
- [ ] **Mixed content — MEDIUM**: `grep -rnEi -- "(src|href|action)[[:space:]]*=[[:space:]]*['\"]?http://" .` — no plain-HTTP subresource, form target or link on an HTTPS page.
- [ ] **Header value defects — MEDIUM**: `grep -rnEi -- "x-xss-protection['\"]?[[:space:]]*[:,=]?[[:space:]]*['\"]?1|text/html(['\"]|[[:space:]]*$)|cache-control[^;]*no-cache" . | grep -vi no-store` — auditor enabled, HTML without `charset=utf-8`, or `no-cache` where `no-store` was meant.
- [ ] **Sensitive data in browser storage — MEDIUM**: `grep -rnEi -- "(localStorage|sessionStorage)\.setItem|indexedDB\.open" .` — each hit holds no PII/financial data and is cleared client-side at logout.
- [ ] **CSP gaps — MEDIUM**: `grep -rnEi -- "style-src[^;]*unsafe-inline|<[a-z][^>]*[[:space:]]on[a-z]+=|report-uri" . | grep -vi report-to` — inline styles/handlers to refactor; `report-uri` without `report-to`; enforced policy reports somewhere.
