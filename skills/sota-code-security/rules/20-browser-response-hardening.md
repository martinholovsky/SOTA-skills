# 20 — Browser Response Hardening

Scope: how response headers reach the browser (every status code, exactly once), HSTS
rollout and preloading, a Fetch Metadata resource isolation policy against XS-Leaks, and
stripping the diagnostic headers infrastructure adds. The header *baseline* (which headers,
which values), CSP, CSRF, CORS and cookies stay in rules/05; directory listing and the
static-root extension allowlist stay in rules/07 §4. Maps to OWASP A02:2025
(Security Misconfiguration), CWE-319/200/1021.

Core principle: **a browser security feature is a second line that the client may not
have.** It helps only where the header actually arrives on the response that matters and
where the user's browser implements it. Server-side checks remain the primary control;
the headers narrow what an attacker can do when one of those checks is missing.

## 1. Features are opportunistic: know your clients, write down the fallback

- Treat every header-driven defence (HSTS, CSP, Fetch Metadata, COOP/CORP, `SameSite`)
  as defence in depth. None of them replaces authorization, output encoding or a CSRF
  token; an app that is safe only when the browser cooperates is not safe.
- List the features the application relies on and check that the **real client
  population** supports them: browser analytics, the supported-browser policy, embedded
  web views, kiosk and TV clients, and API clients that are not browsers at all.
- For each feature, decide and **document** what happens when it is missing — warn the
  user, fall back to a server-side equivalent (a missing `Sec-Fetch-Site` falls back to
  the `Origin` check, rules/05 §3), degrade the feature, or refuse access. Then test that
  path: a fallback nobody exercises is the one that fails open (rules/10).
- Use the same review to drop **obsolete headers**. `X-XSS-Protection` should be absent
  or `0` (the legacy filter it enables can itself open XSS in an otherwise safe page;
  CSP without inline script is the control); `Expect-CT` and `Public-Key-Pins` /
  `Public-Key-Pins-Report-Only` should not be sent at all; `Feature-Policy` has been
  superseded by `Permissions-Policy`. A stale header is noise that makes the live policy
  harder to read and review.
- OWASP: ASVS 5.0 V3.1.1, ASVS 5.0 V3.7.5, Proactive Controls 2024 C8, HTTP Headers
  cheat sheet.

## 2. Emitting headers: every status code, exactly once

- Security headers belong on **every** response, not just `200`s: redirects, `4xx` and
  `5xx` pages, framework error handlers, the proxy's own error pages and health or
  maintenance pages. An error page without `frame-ancestors`, `nosniff` or CSP is
  framable, sniffable and scriptable, and an attacker can usually provoke one.
- **nginx:** `add_header` applies only to a fixed set of success and redirect codes
  (200, 201, 204, 206, 301, 302, 303, 304, 307, 308) unless the `always` parameter is
  given. It is also inherited from the enclosing level **only when the current level
  defines no `add_header` of its own**, so one `add_header` in a `location` silently drops
  every server-level security header there (newer nginx adds `add_header_inherit` to
  change this; check the version you run). Put the set in one included snippet, add it
  with `always`, and include it in every block that declares any `add_header`.
- **Apache `mod_headers`:** `Header` works on two tables, `onsuccess` (the default) and
  `always`; only `always` reaches locally generated error responses and survives
  internal redirects such as `ErrorDocument`. Setting the same header in both tables
  sends it twice, so clear the success table and set the value once in the other:
  `Header onsuccess unset X-Frame-Options` then `Header always set X-Frame-Options "DENY"`.
- **Exactly once.** When the application and a proxy or CDN both add a header, the
  browser sees two values: every CSP delivered is enforced, so a second policy can only
  tighten (and often breaks) the page, and a duplicated single-value header confuses
  clients about which value applies.
  Pick one owner per header — normally the edge for transport headers, the application
  for CSP — and have the other hide the upstream copy (nginx `proxy_hide_header`, Apache
  `Header unset`).
- Verify on a real error path, not the home page: request a missing URL and a URL that
  redirects, and compare their headers with a `200`.
- OWASP: HTTP Headers cheat sheet.

## 3. HSTS rollout: staged max-age, preload last, HTTPS-only emission

- **Send `Strict-Transport-Security` only on HTTPS responses.** RFC 6797 forbids an HSTS
  host from sending it over plain HTTP and requires browsers to ignore it there. On port
  80, answer every request with a **permanent** redirect (`301` or `308`) to the same host
  and path over HTTPS; a temporary redirect (`302`/`307`, and Apache's bare `Redirect`,
  which defaults to `302`) invites clients and caches to keep using HTTP.
- **Ramp `max-age` in stages.** Start short — minutes (`max-age=300`), then a week, then a
  month — watching for hosts or subdomains that break at each step, and only then move to
  a year or more. A long `max-age` sent too early strands users on any name that is not
  yet HTTPS until the value expires, and you cannot shorten it for browsers that already
  cached it.
- **`includeSubDomains` only once every subdomain serves valid HTTPS**, internal and
  legacy names included; inventory them from DNS, not from memory.
- **Preload is the last step, and nearly permanent.** Add `preload` and submit the
  registrable domain to the browser preload list only after the long `max-age` with
  `includeSubDomains` has run without incident. The list's requirements, verified at
  hstspreload.org: `max-age` of at least 31536000 (one year), `includeSubDomains`, the
  `preload` directive, and an HTTP-to-HTTPS redirect on the same host when port 80 is
  open. Removal takes months to reach users through browser updates and other browsers
  may never pick it up, so treat preloading as a commitment for the whole domain tree.
- The generic rule lives here; the Ruby, PHP and network-security skills carry their
  platform's spelling (framework force-TLS settings, edge TLS posture).
- OWASP: ASVS 5.0 V3.7.4, HTTP Strict Transport Security cheat sheet, DotNet Security
  cheat sheet.

## 4. Fetch Metadata resource isolation policy and XS-Leaks

- **Threat: cross-site leaks (XS-Leaks).** A hostile page cannot read your responses, but
  it can load them and observe side effects: how many frames a framed page contains
  (frame counting), whether a navigation or a load succeeded or raised an error event,
  and whether a resource was already in the cache (cache probing, which reveals what the
  user has viewed). Each observation leaks one bit of per-user state — logged in or not,
  a search matched, a record exists.
- **Resource isolation policy.** rules/05 §3 uses `Sec-Fetch-*` against CSRF on
  state-changing requests. Extend it to a policy applied **application-wide, including
  read-only endpoints and APIs**:
  - allow when `Sec-Fetch-Site` is `same-origin`, `same-site` (only if sibling subdomains
    are trusted) or `none` (typed URL, bookmark);
  - allow a cross-site request only when it is a top-level navigation: `Sec-Fetch-Mode:
    navigate`, method `GET`, and a `Sec-Fetch-Dest` that is not `object` or `embed`;
  - reject any other cross-site request with `403`;
  - on sensitive endpoints, also reject a `Sec-Fetch-Dest` the endpoint never expects —
    a JSON API is fetched with `empty`, so `script`, `image`, `iframe`, `object` or
    `embed` there is an inclusion or probing attempt; a page that must not be framed
    rejects `iframe` and `frame`.
- **Fallback for clients without the headers.** Browsers send `Sec-Fetch-*` only to
  potentially trustworthy URLs (HTTPS or localhost), so plain HTTP, old or embedded
  browsers and non-browser clients arrive without them. Decide per endpoint class and
  write it down (§1): the common choice is to allow absence on reads for compatibility
  while mutating requests fall back to the `Origin` check (rules/05 §3); for the most
  sensitive reads, treat absence as unknown and block.
- **Complements, not substitutes:** `Cross-Origin-Resource-Policy: same-origin` makes the
  browser refuse to hand the response to a cross-site loader even when the request got
  through; `Cross-Origin-Opener-Policy: same-origin` severs the window reference a
  cross-site opener could use to count frames; `frame-ancestors` stops framing; `SameSite`
  cookies make many probes arrive logged out.
- **Cache probing:** give per-user resources a per-user **unguessable** URL component (a
  random token in the path or query, not the user id), so an attacker cannot construct
  the URL to time; or mark them `Cache-Control: no-store`.
- OWASP: Proactive Controls 2024 C8, XS Leaks cheat sheet, ASVS 5.0 V3.5.8.

### 4.1 Rolling out a Fetch Metadata deny policy

- **Log-only first.** Record every request the policy would reject, with route, method,
  the three `Sec-Fetch-*` values, `Origin` and user agent, and review that log for false
  positives before switching to enforcement.
- **Track which user agents omit the headers** and how much traffic they carry, so you
  know the fallback path (§4) is covering real clients, not assumed ones; watch the
  share after enforcement too.
- **Keep one documented, reviewed exemption list** of endpoints that are deliberately
  cross-origin: CORS APIs, webhook receivers, SSO endpoints that receive a cross-site
  `POST` (such as a SAML POST-binding assertion consumer), public assets
  meant to be embedded. Each exemption is protected by other means — its CORS allowlist
  (rules/05 §4), authentication or signature verification, and logging — and is
  re-reviewed when the endpoint changes. Exemptions scattered across handlers as
  one-off decorators are how the policy erodes unnoticed.
- Proxies and CDNs must forward `Sec-Fetch-*` and `Origin` unchanged (rules/05 §3); one
  that strips them sends all traffic down the fallback.
- OWASP: Cross-Site Request Forgery Prevention cheat sheet.

## 5. Infrastructure diagnostic headers: strip at the edge

- Fingerprinting is wider than `Server` and `X-Powered-By` (rules/05 §6). Every layer
  between the client and the code tends to add its own response headers, and each
  discloses topology, timing or internal names. Strip these **families** at the outermost
  edge you control:
  - version and product banners: server, framework, CMS and language-runtime versions,
    generator tags;
  - gateway and proxy internals: upstream and proxy latency, upstream status, retry
    counts, internal or original destination hosts, backend node names;
  - distributed-tracing internals: trace, span and parent IDs, sampling flags;
  - cache internals: cache tags, surrogate and purge keys, backend server names — a purge
    key in a response can let an outsider trigger invalidation;
  - server-side timing breakdowns (`Server-Timing` with per-component durations);
  - framework routing internals: the matched route pattern, page or redirect source;
  - APM and monitoring agent identifiers and injection markers;
  - cluster control-plane details, such as priority-level or flow-schema UIDs.
- Strip at the edge (nginx `proxy_hide_header`, Apache `Header always unset`, the CDN's
  response-header rules) as well as turning banners off at the source, because a new
  component or agent upgrade adds headers the source config never knew about.
- An **opaque** correlation ID that the application deliberately returns for support is
  fine; raw tracing IDs from the infrastructure are not the same thing.
- In an audit, sweep real responses — success, error and redirect, from each hostname
  and each path class — rather than reading config, since agents and platforms inject
  headers that no config file shows. The OWASP Secure Headers Project publishes a
  maintained list of headers to remove; use it to extend the probe below.
- OWASP: Secure Headers Project.

## Audit checklist

- [ ] **Obsolete or harmful headers still sent (§1)?** LOW (MEDIUM for a live `Public-Key-Pins`):
      `grep -rnEi "X-XSS-Protection['\":[:space:]]+1|Expect-CT|Public-Key-Pins|Feature-Policy" .`
      — `X-XSS-Protection: 0` does not match and is fine. Also confirm the documented
      supported-client list and missing-feature behaviour exist (ASVS 3.1.1); no grep finds a
      missing document.
- [ ] **Security headers dropped on error and redirect responses (§2)?** MEDIUM (HIGH when the
      missing header is `frame-ancestors`/CSP on a page an attacker can force an error on):
      `grep -rnEi "add_header[[:space:]]+['\"]?(Strict-Transport-Security|Content-Security-Policy|X-Content-Type-Options|X-Frame-Options|Referrer-Policy|Permissions-Policy|Cross-Origin-[A-Za-z]+-Policy)[^;]*;" . | grep -vE 'always[[:space:]]*;'`
      (nginx without `always`) and
      `grep -rnEi "^[[:space:]]*Header[[:space:]]+(onsuccess[[:space:]]+)?(set|add|append|merge|setifempty)[[:space:]]+['\"]?(Strict-Transport-Security|Content-Security-Policy|X-Content-Type-Options|X-Frame-Options|Referrer-Policy|Permissions-Policy|Cross-Origin-[A-Za-z]+-Policy)" .`
      (Apache success table only). Then check nginx `location` blocks that declare their own
      `add_header` re-include the security set.
- [ ] **Headers duplicated (§2)?** MEDIUM: on a live missing page,
      `curl -s -D - -o /dev/null https://HOST/no-such-page | grep -ioE '^[a-z0-9-]+:' | tr 'A-Z' 'a-z' | sort | uniq -d`
      prints every header name sent more than once; repeat on a redirect and a `200`.
- [ ] **HSTS preloaded before it is safe, or HTTP redirected temporarily (§3)?** MEDIUM:
      `grep -rnEi 'Strict-Transport-Security[^;]*max-age=([0-9]{1,7}|[12][0-9]{7}|30[0-9]{6}|31[0-4][0-9]{5}|315[0-2][0-9]{4}|3153[0-5][0-9]{3})[^0-9][^"]*preload' .`
      (`preload` with `max-age` under one year) and
      `grep -rnEi 'return[[:space:]]+30[27][[:space:]]+https://|^[[:space:]]*Redirect([[:space:]]+(302|307|temp))?[[:space:]]+"?/[^[:space:]]*[[:space:]]+"?https://' .`
      (nginx `302`/`307`, Apache temporary or bare `Redirect` to HTTPS). Also confirm HSTS is not
      emitted by the port-80 server block and that every subdomain serves HTTPS before
      `includeSubDomains`/`preload`.
- [ ] **No resource isolation policy at all (§4)?** MEDIUM (HIGH when per-user state is
      observable cross-site, e.g. search or existence endpoints):
      `grep -rqEi 'sec-fetch-(site|dest)' . || echo 'NO resource isolation policy (no Sec-Fetch-* check anywhere)'`
      — a hit only proves the header is read; confirm the check covers read-only routes, not
      just unsafe methods, and that `Sec-Fetch-Dest` is validated on sensitive APIs.
- [ ] **Fetch Metadata rollout discipline (§4.1)?** MEDIUM: is there a log-only phase with a
      reviewed false-positive log, user-agent tracking for requests without `Sec-Fetch-*`, and
      one reviewed exemption list whose entries each have CORS/auth/signature checks and
      logging? Process, not code — read the policy module and its config; no grep separates a
      reviewed list from an ad hoc one.
- [ ] **Infrastructure diagnostic headers leak (§5)?** LOW (MEDIUM when a purge key, internal
      host name or version with a known CVE is exposed): for each hostname and for a success,
      error and redirect path,
      `curl -s -D - -o /dev/null https://HOST/PATH | grep -iE '^(server:.*[0-9]|server-timing:|x-(powered-by|aspnet|aspnetmvc|generator|runtime|b3-|datadog-|envoy-|kong-|varnish|litespeed|nextjs-|kubernetes-pf-|dt|tyk-)|[a-z-]*(latency|upstream-status|matched-path|purge|cache-tag|trace-id)[a-z-]*:)'`
      — every hit is a header to strip at the edge; extend the prefixes from the OWASP Secure
      Headers Project removal list.
