# JavaScript/TypeScript Security

Severity here maps to exploitability: attacker-controlled input reaching a sink = CRITICAL/HIGH; hardening gaps = MEDIUM; defense-in-depth = LOW.

## XSS: know your sinks

XSS = untrusted data reaching an HTML/JS execution sink. Frameworks escape by default; every escape hatch is a sink.

Sinks to treat as hostile-by-default:
- `element.innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write`
- React `dangerouslySetInnerHTML`, Vue `v-html`, Angular `bypassSecurityTrust*`, Svelte `{@html}`
- `eval`, `new Function`, string args to `setTimeout`/`setInterval`
- `<a href>`/`location` assignment with user data — `javascript:` URLs
- jQuery `$(userInput)`, `.html()`

```tsx
// BAD — stored XSS
<div dangerouslySetInnerHTML={{ __html: user.bio }} />
el.innerHTML = `<b>${query}</b>`;

// GOOD — default escaping; textContent for DOM
<div>{user.bio}</div>
el.textContent = query;

// HTML genuinely required (rich text/markdown)? Sanitize with DOMPurify at render time
import DOMPurify from 'dompurify';
<div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(html, { USE_PROFILES: { html: true } }) }} />

// BAD — javascript: URL slips through React's escaping
<a href={user.website}>site</a>
// GOOD — allowlist protocols
const safeUrl = (u: string) => { try { const p = new URL(u); return ['https:', 'http:', 'mailto:'].includes(p.protocol) ? u : '#'; } catch { return '#'; } };
```

- Sanitize at output/render, not at input (input-sanitized data gets corrupted and re-encoded wrongly across contexts).
- Server-rendered HTML embedding JSON state: `JSON.stringify(state).replaceAll('<', '\\u003c')` to block `</script>` breakout.
- Adopt Trusted Types where targets allow (`require-trusted-types-for 'script'` CSP) — it turns DOM-sink misuse into runtime errors.
- `eval`/`new Function` on anything dynamic is CRITICAL. There is no safe "sandboxed eval" in-process (Node `vm` is NOT a security boundary — escapes are trivial; use isolated processes/`isolated-vm`/WASM).

## CSP integration

Ship a Content-Security-Policy on every HTML response; it converts many XSS bugs from CRITICAL to mitigated.

```
Content-Security-Policy:
  default-src 'self';
  script-src 'self' 'nonce-{random}' 'strict-dynamic';
  object-src 'none'; base-uri 'none'; frame-ancestors 'none';
```

- Nonce-based `strict-dynamic` beats allowlist CSP (allowlists are bypassable via JSONP/open redirects on allowed hosts). Generate a fresh nonce per response; templating/framework injects it on `<script>` tags.
- `'unsafe-inline'` in `script-src` makes CSP decorative (finding: MEDIUM). `'unsafe-eval'` enables the eval family — required only by legacy libs; eliminate.
- Roll out with `Content-Security-Policy-Report-Only` + a report endpoint, then enforce.
- `frame-ancestors` replaces `X-Frame-Options`; `base-uri 'none'` blocks `<base>` hijack of relative script URLs.

## Server-rendered HTML: template engines and hand-built strings

The sink list above is the browser's. A Node server that renders HTML itself (Express
views, email templates, HTML-to-PDF input) has its own, and each engine spells "raw" in a
different way. Measured on ejs 6, pug 3, handlebars 4.7 and mustache 4.2 with the payload
`<img src=x onerror=alert(1)>`. Each form below emitted it **unescaped**:

| engine | escaped (default) | raw output — each one is a sink |
|---|---|---|
| EJS | `<%= x %>` | `<%- x %>`; an `escape` option that returns its input |
| Pug | `#{x}`, `p= x` | `!{x}`, `p!= x`; `&attributes(obj)` (emitted `onclick="…"` from data) |
| Handlebars | `{{x}}` | `{{{x}}}`, `{{&x}}`; `compile(src, { noEscape: true })` |
| Mustache | `{{x}}` | `{{{x}}}`, `{{&x}}`; reassigning `Mustache.escape` (global, every render) |

- **User input goes into the template's data, never into its source.** Measured:
  `ejs.render('<%= process.version %>')` and `pug.render('- var v = process.version…')`
  both returned the Node version, because EJS and Pug templates *are* JavaScript. A
  user-controlled template string is **code execution** (CRITICAL). Handlebars and
  Mustache are logic-less: the same probe for `constructor` returned nothing useful from
  Handlebars (prototype access is blocked). They still render raw HTML via the table
  above. The class is `sota-code-security` rules/01 §7.
- **The view name is a path.** `res.render(req.query.view)` is an injection sink. Measured
  on Express 5.2.1: `app.render('../upload')` and `app.render('/abs/path/upload.ejs')` both
  rendered a template **outside** `views/`, executing its `<%= %>` code. That is code
  execution once an attacker can put a file on disk. Map the request to a fixed allowlist
  of view names.
- **Hand-built HTML has no escaping at all.** `` res.send(`<p>Hello ${name}</p>`) `` is
  reflected XSS. Do not repair it with `.replace('<', '&lt;')`: a **string** pattern
  replaces only the **first** match. Measured: `'<b><i>'.replace('<','&lt;')` gives
  `&lt;b><i>`. Render through an engine's escaped form. If you must escape by hand, use
  one function that handles `& < > " '` with `replaceAll` or a `/g` regex.

## Prototype pollution

Writing to `__proto__`/`constructor.prototype` via attacker-controlled keys poisons every object — leading to auth bypass (`{}.isAdmin === true`), DoS, sometimes RCE via gadget chains.

Vulnerable patterns: recursive merge/extend/clone of untrusted JSON, `obj[a][b] = v` with attacker-controlled `a`, lodash `set`/`merge` with untrusted paths, query-string parsers building nested objects.

```ts
// BAD — classic vulnerable deep merge
function merge(target: any, src: any) {
  for (const k in src) {
    if (typeof src[k] === 'object') merge(target[k] ??= {}, src[k]);  // k = "__proto__" pollutes
    else target[k] = src[k];
  }
}

// GOOD — defenses, in order of preference:
// 1. Don't deep-merge untrusted input. Parse with zod (strips unknown keys, fixed shape).
const body = BodySchema.parse(await req.json());
// 2. If you must merge dynamic keys: block the dangerous ones and use null-prototype targets
const DANGEROUS = new Set(['__proto__', 'constructor', 'prototype']);
if (DANGEROUS.has(key)) continue;
const map = Object.create(null);          // no prototype to pollute
// 3. Maps for dynamic keyed storage (rules/02). 4. node --disable-proto=delete as hardening.
```

- `JSON.parse` itself is safe (`__proto__` becomes an own property) — the pollution happens in subsequent merge/assign logic.
- Check dependencies: historic offenders are deep-merge utilities, config loaders, and qs-style parsers. `Object.freeze(Object.prototype)` is a blunt last-resort hardening some services use.

## npm supply chain

The dependency tree is your attack surface; install scripts run arbitrary code on `npm install` (developer machines and CI). Worm campaigns like the 2025 Shai-Hulud worm spread exactly this way; the March 2026 axios compromise published malicious versions with a stolen npm token, bypassing the project's trusted-publishing setup — caught within a day, which is exactly what install cooldowns absorb; and the June 2026 Miasma wave (a Shai-Hulud derivative, 32+ `@redhat-cloud-services` packages) ran code at install via a phantom `binding.gyp` — the implicit `node-gyp rebuild` needs no declared install script — published through a compromised OIDC trusted-publishing workflow with valid SLSA provenance.

- **Lockfile committed and exact**: `package-lock.json`/`pnpm-lock.yaml` in git; CI installs with `npm ci` / `pnpm install --frozen-lockfile` — never bare `npm install` in CI.
- **Disable install scripts by default**: `npm config set ignore-scripts true` (or `.npmrc: ignore-scripts=true`) — this also skips the implicit `binding.gyp`/node-gyp path; pnpm ≥10 blocks them by default with an allowlist — `allowBuilds` since **v11**, which **removed** `onlyBuiltDependencies`/`neverBuiltDependencies`/`ignoreDepScripts`; keep `strictDepBuilds` (default `true` since v10.3.0) so an unreviewed build script **exits non-zero** instead of warning; npm ≥12 (July 2026) blocks dependency install scripts including implicit node-gyp rebuilds by default, and refuses git and remote-URL tarball dependencies unless `--allow-git`/`--allow-remote` — build the allowlist before upgrading with `npm approve-scripts` (npm ≥11.16 warns). Allow per-package only what genuinely needs to build (esbuild, sharp).
- **Cooldown**: don't install or auto-merge dependency updates the day they publish; most hijacked versions are caught within days. Package managers now enforce this natively: pnpm 11 defaults `minimumReleaseAge` to 1440 minutes (1 day — don't opt out without reason); npm CLI ≥11.10 has `min-release-age` (days) in config; plus Renovate `minimumReleaseAge` (e.g. `7 days`) / Dependabot cooldown for update PRs.
- **Provenance & audit**: prefer packages publishing npm provenance (Sigstore attestation) — but provenance proves the publish path, not code safety: Miasma shipped malware with valid SLSA attestations from a compromised trusted-publishing workflow; `npm audit --omit=dev` in CI with a triage policy (fail on high/critical with no fix-path exception file); `osv-scanner` or Socket for behavioral flags (new maintainer, install script added, network in install).
- **Minimal deps**: every dep is trust granted to its maintainers and their deps transitively. Before adding: is it <100 lines you could own? Does the platform do it (rules/04 table)? Check maintenance, weekly downloads, dependency count.
- **Typosquatting**: verify exact names on add; scoped packages (`@org/x`) reduce risk. Pin GitHub Actions to commit SHAs, not tags.
- **Publishing**: trusted publishing (OIDC from CI — `npm trust` since CLI 11.10 configures it across packages in bulk) over long-lived tokens; npm's staged publishing adds a human 2FA approval gate before a version goes live — enable it for high-blast-radius packages (a stolen token alone then can't ship a release). `files` allowlist in package.json so secrets/configs never ship in the tarball.

## Invisible and bidirectional characters in source

Code review assumes the diff shows what the parser sees. Two JS facts break that
assumption, both measured on Node 22:

- **An identifier can be invisible.** An identifier consisting only of U+3164 HANGUL
  FILLER is valid: `new Function('const ㅤ = "hidden"; return ㅤ;')()` returned
  `"hidden"`. The parser treats it as a letter, and it renders as blank space. So
  `const { timeout, <U+3164> } = req.query`, followed by a later use of that name in an
  `exec` call, reads in review like a stray comma. (The escapes are written out here so
  this file itself stays clean.) (U+200B, zero-width space, is
  **not** accepted inside an identifier: that was a SyntaxError.)
- **Bidirectional controls inside comments and strings are legal** (U+202A–202E,
  U+2066–2069, the Trojan Source class, CVE-2021-42574). A comment containing U+202E
  parsed and ran unchanged. The characters reorder how the line *displays*, not how it
  *executes*.

Gate on it rather than trusting review: `eslint-plugin-security` ships
`detect-bidi-characters` in its recommended set. Its `detect-invisible-characters` (U+3164,
U+FFA0) is on the project's main branch but was **not in a published release** when checked on
2026-09-24 (latest was 4.0.1). Until your installed version exports it, use the byte probe
in the checklist. The ingest-side version of the same class, for
text bound for an LLM or a UI, is `sota-code-security` rules/09 §4.

## ReDoS

Backtracking regexes with nested/overlapping quantifiers go exponential on crafted input — one request pins a CPU (and on Node, the whole event loop: total DoS).

```ts
// BAD — (a+)+ catastrophic backtracking; 30 chars of 'aaaa...!' hangs the process
const valid = /^(\w+\s?)*$/.test(userInput);
// BAD — overlapping alternation
/^(.*,)*.*$/

// GOOD options:
// 1. Linear-time by construction: no nested quantifiers over overlapping sets
const valid = /^[\w\s]*$/.test(userInput);
// 2. Length-cap input BEFORE regexing
if (input.length > 256) reject();
// 3. Non-backtracking engine for complex patterns: RE2 (node-re2)
// 4. Don't regex what a parser should parse (emails: maxlength + one '@' + send a verification mail)
```

- Lint: `eslint-plugin-regexp` (includes ReDoS detection) or `recheck`/`redos-detector` in CI on any regex touching user input.
- The `v`/`u` flags don't fix backtracking. Regexes in hot paths compiled once (top-level `const`), not per call.

**A regex used as a control (validator, allowlist, route guard, redactor) has four more ways to fail:**

- **Escaping.** Request data placed inside a pattern is pattern syntax until escaped: `.` or
  `.*` in a username turns a match into a wildcard. Use `RegExp.escape(s)` (ES2025; a function
  from Node 24.0.0, `undefined` on Node 22, measured). On older runtimes use one audited
  helper — `s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')` — never ad-hoc escaping. If only a
  literal comparison is needed, skip the regex (`===`, `startsWith`, `includes`).
- **Anchoring.** Validate the whole string: `/^(?:…)$/`. Group an alternation, because
  `/^admin|root$/` means "starts with admin OR ends with root" (it accepts `admin-evil`).
  In JS, without the `m` flag `$` matches only at the true end of input
  (`/^[a-z]+$/.test('abc\n')` is `false`, unlike Python/PCRE). The trap is the reverse: **with `m`,
  `^`/`$` are line anchors**, so `/^[a-z]+$/m` passes `'evil\nabc'`. Never put `m` on a
  validator. Never put `g` or `y` on one either: they make `.test()` stateful through
  `lastIndex`, so one shared `/…/g` validator returns `true` then `false` for the same input
  (measured). `str.match(re)` and `str.search(re)` are unanchored searches, not validation.
  JSON Schema `pattern` is unanchored too: Ajv 8 accepted `'<script>abc'` against
  `"[a-z]+"` (measured), so write `"^[a-z]+$"`.
- **Bounds.** Bound every repetition inside the pattern (`{1,64}` rather than `+`) *and*
  cap `input.length` before matching (above).
- **Engine.** V8's default engine backtracks, and `RegExp` takes only a pattern and flags,
  with no match-timeout option. For a pattern built from, or run on, untrusted input where
  the linear-time shape above cannot be guaranteed, use the `re2` npm package. It is
  linear-time, and it throws `SyntaxError` on backreferences and lookahead. That is the cost:
  a pattern that needs them must be rewritten, or it stays on the backtracking engine with its
  length cap and lint. V8's own linear engine (the `l` flag behind
  `--enable-experimental-regexp-engine`, which rejects backreferences and lookaround with
  "Cannot be executed in linear time") is experimental and off by default. It is not a
  production control. The last resort for an unavoidable backtracking pattern is running it in a
  `worker_threads` Worker that you `terminate()` on a deadline.
- *Sources, by name:* OWASP Input Validation cheat sheet; OWASP Proactive Controls 2024 C3;
  ASVS 5.0 V1.2.9; OWASP Go-SCP (validation, regular expressions).

## Tokens and client-side auth

- **Session/refresh tokens never in `localStorage`/`sessionStorage`** — any XSS exfiltrates them. Use cookies: `HttpOnly; Secure; SameSite=Lax` (or `Strict`), `Path` scoped, `__Host-` prefix.
- SameSite is CSRF defense-in-depth, not complete: keep CSRF tokens (or strictly enforce custom-header + CORS preflight) for state-changing routes if any non-SameSite path exists.
- If an SPA must hold an access token in JS (third-party API): keep it in memory only, short-lived (≤15min), refresh via httpOnly-cookie refresh token; accept that XSS can use (not just steal) it — XSS prevention remains the real control.
- **Verify JWTs server-side properly**: pin the algorithm (`{ algorithms: ['RS256'] }` — never accept `alg` from the token; `none` and HS/RS confusion attacks), validate `iss`, `aud`, `exp`, clock skew. Use `jose`. Don't put secrets in JWT payloads — they're only base64.
- **`decode` is not `verify`.** jsonwebtoken's `jwt.decode` "Returns the decoded payload
  without verifying if the signature is valid", and its README says not to use it on
  untrusted messages. jose's `decodeJwt` decodes "without checking its signature or
  validating claim types and values". Server code that authorizes on either one accepts a
  token the caller wrote themselves (CRITICAL). On the client, decoding for display is
  fine. Decoding in order to gate anything is the "client guards are UX" mistake below.
- Authorization on every request server-side; client-side route guards are UX, not security.

```ts
// Setting the session cookie — the full attribute set, not a subset
res.setHeader('Set-Cookie',
  `__Host-session=${token}; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=900`);
```

- `__Host-` prefix forces Secure + no Domain attribute + Path=/ — blocks subdomain cookie-tossing.
- Rotate session IDs on login/privilege change (session fixation); server-side revocation list or short-lived JWT + refresh rotation with reuse detection.
- CSRF for cookie-authed JSON APIs: require a custom header (e.g. `X-Requested-With`) and strict CORS — preflight enforcement makes cross-origin forgery fail; forms still need synchronizer tokens.
- CORS: never `Access-Control-Allow-Origin: *` with `Allow-Credentials: true` (browsers reject it; reflecting `Origin` unvalidated recreates the hole — allowlist exact origins).

## Secrets in code and client bundles

- Anything in frontend code ships to the attacker: API keys in `VITE_*`/`NEXT_PUBLIC_*` vars are public by definition — only put genuinely-public keys there (analytics write keys, maps keys with referrer locks). Server-only secrets must never appear in client-reachable modules; Next.js server/client boundary violations leak env into the bundle.
- `grep` the built bundle for key prefixes (`sk_live`, `AKIA`, `ghp_`, `AIza`) as a release gate; gitleaks/trufflehog pre-commit and in CI for the repo itself.
- Error responses: never echo stack traces, SQL, or internal paths to clients in production — log them server-side with the request ID, return the ID in the error body for correlation.

## postMessage and cross-origin

```ts
// BAD — any window can send this; acting on it = universal XSS/state tampering
window.addEventListener('message', (e) => applySettings(e.data));
// BAD — broadcasting secrets to whoever holds the window
otherWindow.postMessage(token, '*');

// GOOD — verify origin on receive, target origin on send, validate payload
window.addEventListener('message', (e) => {
  if (e.origin !== 'https://trusted.example.com') return;
  const msg = MessageSchema.safeParse(e.data);
  if (msg.success) handle(msg.data);
});
iframe.contentWindow?.postMessage(payload, 'https://child.example.com');
```

Treat `e.data` as untrusted input even from trusted origins (the trusted page may itself be compromised). Same discipline for `BroadcastChannel` and `window.opener` (use `rel="noopener"` on external links).

## Command injection via child_process

```ts
// BAD — exec runs through a shell; filename = "x; rm -rf /" executes
exec(`convert ${filename} out.png`);
// BAD — shell:true reintroduces the hole in spawn
spawn('convert', [filename], { shell: true });

// GOOD — execFile/spawn with array args, no shell: arguments are never parsed
import { execFile } from 'node:child_process';
const { stdout } = await promisify(execFile)('convert', [filename, 'out.png'], { timeout: 10_000 });
```

- `exec`/`execSync` with any interpolated value is CRITICAL. `execFile`/`spawn` (no `shell`) pass args directly to the binary.
- Still validate the arg itself: allowlist characters/paths (argument injection — `--flag`-shaped filenames — can still subvert tools; prepend `--` where supported).
- Path traversal cousin: joining user input into paths — `const p = path.resolve(base, name); if (!p.startsWith(base + path.sep)) reject();`
- Same family: never interpolate into SQL (parameterized queries only), `Function`, or `vm`.
  **YAML:** in js-yaml **4.0.0 and later**, `load` is safe by default. The `!!js/function`
  family moved to a separate package, and `safeLoad` was removed; calling it now throws.
  Measured on js-yaml 5: `load('f: !!js/function …')` threw "unknown scalar tag". The
  finding is js-yaml **below 4** calling `load` on untrusted input, or a schema that
  re-adds the JS types. "Use `safeLoad`" is stale advice, because that call no longer exists.
- **A shell passed as argv is still a shell.** `spawn('sh', ['-c', cmd])` (or `bash -c`)
  has no `shell: true` for the probe below to find, and it parses `cmd` exactly
  like `exec`. The same holds for `shelljs`: its own docs say `shell.exec()` "executes an
  arbitrary string in the system shell". Measured on shelljs 0.10: `shell.exec('echo
  $HOME')` printed the expanded home directory.
- **A module specifier is code.** `require(x)` and `import(x)` execute whatever `x` names.
  Measured on Node 22: `await import('data:text/javascript,…')` ran the inline source, so an
  ESM `import()` of a user string executes code with **no file on disk**. `require` of a
  user-chosen path runs an uploaded `.js`. Load plugins from a fixed map
  (`const plugins = { csv: () => import('./csv.js') }`), never from a request value.
- **Node deprecated the dangerous spelling itself.** `DEP0190` — "Passing `args` to
  the `node:child_process` module's `execFile()` and `spawn()` methods with the
  `shell` option enabled is deprecated … the arguments are not properly escaped when
  passed to the shell". Measured on Node 22: `spawnSync('/bin/echo', ['$HOME'],
  {shell:true})` prints the expanded home directory **and emits the DEP0190 runtime
  warning**, while the same call without `shell` prints the literal `$HOME`. Treat a
  DEP0190 warning in logs or CI as a finding, not noise — it marks a live injection
  sink.
- **`timeout:` bounds your wait, not the process tree, and may report no error.**
  Measured on Node 22 with a child that exits immediately after spawning a grandchild
  holding stdout: `execFile(..., {timeout: 300})` called back at **305 ms** — the
  deadline works — but the **grandchild was still running**, and `err` was **`null`**,
  because the direct child had exited 0. So the caller cannot tell from the callback
  that the deadline fired at all. If the child may fork, spawn it with
  `detached: true` and kill the process **group** (`process.kill(-child.pid)`), and
  decide explicitly what a timeout means for your caller rather than inferring it from
  `err`.

## Open redirects and file uploads

Open redirect (`/login?next=https://evil.example`) launders phishing through your domain and chains into OAuth token theft.

```ts
// BAD
res.redirect(req.query.next as string);
// GOOD — relative-path allowlist; reject absolute/protocol-relative
const next = String(req.query.next ?? '/');
res.redirect(next.startsWith('/') && !next.startsWith('//') && !next.includes('\\') ? next : '/');
```

File uploads:
- Validate by magic bytes (`file-type` package), not extension or client `Content-Type`; both are attacker-controlled.
- Generate server-side filenames (`crypto.randomUUID()` + validated extension); never use the client filename in paths (traversal) or HTML (XSS).
- Size-cap at the parser (multipart limits), store outside the web root / in object storage, serve with `Content-Disposition: attachment` + `X-Content-Type-Options: nosniff` for user content; SVGs are XSS vectors — sanitize or serve from a sandboxed origin.
- Images: re-encode (sharp) to strip embedded payloads/EXIF.

## SSRF and server-side validation

- Every inbound payload schema-parsed at the boundary (rules/01) — including webhooks (verify signatures: Stripe/GitHub HMAC) and headers you act on.
- User-supplied URLs the server fetches (webhooks, importers, avatars): allowlist protocols (`new URL(u).protocol === 'https:'`, checked again on every redirect hop), block private ranges (127/8, 10/8, 172.16/12, 192.168/16, 169.254/16 — cloud metadata `169.254.169.254`), handle redirects (below), pin timeouts and response-size caps. Library: `ssrf-req-filter` or equivalent egress proxy. The generic policy is `sota-code-security` rules/01 §5; the Node idiom:
  - **Best: never relay a caller URL.** Accept a service key or record ID, look the origin up in a server-side map, and build the URL with `new URL(path, base)` plus `encodeURIComponent` on each segment. The rest of this list is for when you genuinely must fetch an arbitrary URL.
  - **Check the address at connect time, not before.** A `dns.lookup()` done before `fetch()` is a separate resolution from the one the socket uses, so a rebinding DNS server answers public to the check and `127.0.0.1` to the connection. Put the check in the resolver the socket calls: `new Agent({ connect: { lookup } })` from the `undici` package (its connector spreads `connect` into `net.connect`/`tls.connect`), or the `lookup` option of `http.request`/`https.request` and of axios. Measured on Node 22.22.1: the hook is called with `{ all: true }` (family autoselection), so it must resolve all addresses, reject if **any** is blocked, and answer in the array form. Test each address with a `net.BlockList` covering 127/8, 10/8, 172.16/12, 192.168/16, 169.254/16, 100.64/10, 0/8, 224/4, `::1`, `fc00::/7`, `fe80::/10`, `ff00::/8`; a v4 subnet also matched `::ffff:127.0.0.1` checked as `ipv6`. Also refuse the metadata host names (`metadata.google.internal` on GCP, whose IPv6 metadata address `fd20:ce::254` falls in `fc00::/7`; check your cloud's docs for its own) by name.
  - **The hook never sees an IP literal.** `fetch('http://127.0.0.1/')` through that Agent returned 200 with zero `lookup` calls (undici 8.11.2; `http.get` skips it too). So check a literal host yourself before dispatch: `new URL(u).hostname`, strip the `[]` around IPv6 (`net.isIP('[::1]')` is 0), then `net.isIP` + the same BlockList.
  - **Parse with WHATWG `URL`, not a regex or the `ip` package.** `new URL()` canonicalises `0x7f.1`, `0177.0.0.1` and `2130706433` to `127.0.0.1` (measured), whereas `net.isIP` returns 0 for those raw strings, so a check on the unparsed string treats them as host names. `ip`'s `isPublic` misclassifies `127.1`, octal forms and `::fFFf:127.0.0.1` in every version through 2.0.1 with no patch (CVE-2024-29415).
  - **Use `undici`'s own `fetch` with its `Agent`.** Passing an `undici@8` `Agent` as `dispatcher` to Node 22's global `fetch` (bundled undici 6.23) failed with `invalid onRequestStart method` — a major mismatch, measured.
  - **Redirects**: `redirect: 'error'` rejects any 3xx; `redirect: 'manual'` returns it so you re-validate `Location` and fetch the next hop yourself (bounded count). The default `'follow'` goes wherever the server says. In axios, `maxRedirects: 0` or a `beforeRedirect` that re-checks. Under the default `follow` the Agent's `lookup` still ran on the hop and blocked a 302 to `localhost` (measured), but that does not cover a literal-IP hop; only scheme and literal-IP checks need repeating per hop.
  - OWASP: SSRF Prevention, .NET Security and GraphQL cheat sheets.
- Mass assignment: never `Model.update(req.body)` — schema-pick the allowed fields (`z.object({...}).strict()`).
- **NoSQL operator injection is the same bug arriving as a type.** In
  `User.findOne({ name: req.body.name, pass: req.body.pass })`, a body of
  `{"pass": {"$ne": null}}` becomes a MongoDB operator, not a string. JSON bodies can always
  carry it. Query strings depend on the parser, measured: `qs` turns `user[$ne]=x` into
  `{"user":{"$ne":"x"}}`, which is **Express 4's default** (`'extended'`). **Express 5's
  default** (`'simple'`, `node:querystring`) leaves it a flat key. An Express 4→5 upgrade
  therefore changes the exposure, and so does setting `'query parser'` back to
  `'extended'`. The fix is the boundary rule: parse every field to a scalar (`z.string()`)
  before it reaches a filter. Mongoose's `sanitizeFilter` option is the backstop. Measured:
  its helper rewrote `{user:{$ne:null}}` to `{user:{$eq:{$ne:null}}}`. It also throws on
  `$where`, `$expr`, `$jsonSchema` and `$text`. The class is `sota-code-security` rules/01 §2.
- **Ajv:** its security page says **"Do NOT use allErrors in production"**. With
  `allErrors: true`, validation keeps running after the first failure, so the
  slow-keyword mitigations (`maxLength` before `pattern`, `maxItems` before
  `uniqueItems`) stop working. It also says Ajv "treats JSON schemas as trusted as your
  application code". So never compile a schema that came from a request. For
  `pattern`/`format` on untrusted strings, Ajv supports a linear-time engine:
  `new Ajv({ code: { regExp: RE2 } })`.
  Source: <https://github.com/ajv-validator/ajv/blob/master/docs/security.md>.
- **CORS through the `cors` middleware.** The `Allow-Origin` probe below never sees this
  config. Measured on cors 2.8: `cors({ origin: true, credentials: true })` answered
  `Origin: https://evil.example` with that origin **and** `Allow-Credentials: true`, which
  is the reflection hole above written as one option. `origin: /example\.com$/` accepted
  `https://evilexample.com`. Use an exact-string array, or a regex anchored at both ends
  with the scheme and a dot before the domain (`/^https:\/\/([a-z0-9-]+\.)?example\.com$/`).

## Timing and crypto hygiene

- Compare secrets (HMAC signatures, API keys, tokens) with `crypto.timingSafeEqual` (equal-length buffers — hash both sides first if lengths vary), never `===` (timing oracle).
- Randomness for anything security-relevant (tokens, IDs in URLs, reset codes): `crypto.randomUUID()` / `crypto.getRandomValues()` / `crypto.randomBytes` — never `Math.random()` (predictable, seedable state recovery is practical).
- Password hashing: argon2id (or scrypt/bcrypt with sane cost), async variants only (rules/04); never SHA-256-of-password, never homegrown.
- Web Crypto (`crypto.subtle`) for in-app encryption/signing; AES-GCM with unique IVs per encryption (IV reuse with GCM is catastrophic); keys from KMS/secret manager, not constants.

## Native addons and uninitialized buffers

Two ways Node leaves memory safety. **Native addons** (`.node` files, Node-API /
`node-addon-api`, built with `node-gyp`) are C or C++ inside the process: audit them as such.
**`Buffer.allocUnsafe`** needs no native code at all. Node's docs say its memory "is *not
initialized*" and "may contain sensitive data", so a buffer sent before every byte is
overwritten leaks earlier allocations: tokens, keys, other users' data. Use `Buffer.alloc`
unless a benchmark justifies the unsafe form *and* the code provably overwrites the whole
buffer first. The class is `sota-code-security` rules/06 §3.

## Audit checklist

- [ ] **Uninitialized buffers and native addons — HIGH if the buffer can leave the process** —
      `grep -rnE 'Buffer\.allocUnsafe(Slow)?\(|new Buffer\(' --include='*.js' --include='*.ts' --include='*.mjs' --include='*.cjs' .`
      ; `grep -rnE 'node-addon-api|node-gyp|"gypfile"|\.node([^a-zA-Z0-9]|$)' --include='package.json' --include='*.js' --include='*.ts' .`
- [ ] `grep -rn "innerHTML\|outerHTML\|insertAdjacentHTML\|document.write" src/` — each with non-constant input is HIGH/CRITICAL; constant strings LOW.
- [ ] `grep -rn "dangerouslySetInnerHTML\|v-html\|{@html}\|bypassSecurityTrust" src/` — sanitized with DOMPurify at render? Unsanitized user/db content = CRITICAL (stored XSS).
- [ ] `grep -rn "eval(\|new Function(\|setTimeout(['\"\`]\|setInterval(['\"\`]" src/` — CRITICAL with dynamic input.
- [ ] `grep -rn "href={" src/ --include="*.tsx"` — user-controlled hrefs without protocol allowlist (`javascript:`) = HIGH.
- [ ] `grep -rn "localStorage.setItem\|sessionStorage.setItem" src/ | grep -i "token\|jwt\|session\|auth\|key"` — HIGH.
- [ ] `grep -rn "postMessage" src/` — `'*'` target with sensitive data (HIGH); message listener without origin check (HIGH).
- [ ] `grep -rn "exec(\|execSync(" src/` — template/concat input = CRITICAL; migrate to execFile array form.
- [ ] `grep -rn "child_process" src/ | grep "shell"` — `shell: true` (HIGH).
- [ ] Deep-merge of request data: `grep -rn "merge(\|deepmerge\|Object.assign" src/` near `req.body`/`json()` — prototype pollution exposure (HIGH); `grep -rn "__proto__" src/` in tests/guards is good signal of awareness.
- [ ] `grep -rn "jwt.verify\|jwtVerify" src/` — algorithm pinned? `aud`/`iss` checked? `grep -rn "algorithms" src/` absent = HIGH.
- [ ] Regex on user input: `grep -rn "new RegExp(" src/` (dynamic patterns = ReDoS + injection risk, HIGH); run `eslint-plugin-regexp`/recheck over static patterns.
- [ ] **Regex escaping, anchoring and engine (§"ReDoS", the four control failures) — HIGH on a
      validator or allowlist** —
      ``grep -rnE 'new RegExp\( *[[:alpha:]_$`]|/[dgimsuvy]*[gmy][dgimsuvy]*\.test\(|/\^[^(/|]*\|[^/]*\$/' --include='*.js' --include='*.ts' --include='*.mjs' --include='*.cjs' . | grep -v 'RegExp\.escape('``
      — hits are a pattern built from a variable without `RegExp.escape`, a `.test()` on a
      literal carrying `m`/`g`/`y`, and a `/^a|b$/` alternation outside a group. A request value
      in an unescaped pattern is HIGH (pattern injection plus ReDoS). An `m`/`g` validator or an
      ungrouped alternation is HIGH when it guards access. The probe sees inline literals only:
      a flagged regex held in a `const` needs a read, and so do JSON Schema `pattern`s without `^…$`.
      Complex patterns on untrusted input should run on the linear-time `re2` engine, or it is MEDIUM.
- [ ] CSP present? `grep -rn "Content-Security-Policy" src/` — absent on HTML-serving apps (MEDIUM); contains `unsafe-inline`/`unsafe-eval` in script-src (MEDIUM).
- [ ] Lockfile in git; CI uses `npm ci`/frozen lockfile; install scripts blocked (`.npmrc` `ignore-scripts`, pnpm allowlist, or npm ≥12 defaults + committed `approve-scripts` allowlist); install cooldown active (pnpm 11 `minimumReleaseAge` default, npm ≥11.10 `min-release-age`, or Renovate/Dependabot) (each absent: MEDIUM).
- [ ] `grep -n "git+\|git://\|github:\|https://.*\.tgz" package.json` — git-URL or remote-tarball dependencies: unauditable, refused by npm ≥12 without `--allow-git`/`--allow-remote` (MEDIUM).
- [ ] SQL built by interpolation (the rule is stated in §"Same family" above; this is its
      probe, absent until 2026-09-22): `grep -rnE '(query|execute|raw)\\(\\s*`' src/` — a
      template literal reaching a driver is CRITICAL. Also `grep -rn "knex.raw\\|sequelize.query\\|\\$queryRawUnsafe\\|createQueryBuilder" src/`
      — Prisma's `$queryRaw` tagged template is parameterized while `$queryRawUnsafe` is not,
      and the two differ by one word. Parameterized/bound form everywhere, or HIGH.
- [ ] **SSRF: a request value becoming an outbound request's URL (§"SSRF and server-side validation")** —
      ``grep -rnE '(fetch|axios(\.[a-z]+)?|got(\.[a-z]+)?|https?\.(get|request)|goto|new URL)\( *(`\$\{ *)?req\.(body|query|params|headers)' --include='*.js' --include='*.ts' --include='*.mjs' --include='*.cjs' .``
      — each hit must go through a connect-time `lookup` guard plus a literal-IP check, with
      `redirect: 'error'`/`'manual'`, or it is HIGH (internal address / metadata endpoint
      reachable). A pre-fetch `dns.lookup` as the only check is HIGH (DNS rebinding). The probe
      sees single-line calls with the request value first; a URL held in a variable needs a read.
- [ ] Webhook handlers: signature verification before parsing (absent = HIGH).
- [ ] `grep -rn "Allow-Origin" src/` — `*` with credentials or unvalidated Origin reflection (HIGH).
- [ ] Built client bundle: `grep -rE "sk_live|AKIA|ghp_|-----BEGIN" dist/` — leaked secrets (CRITICAL). Repo: gitleaks in CI (absent = MEDIUM).
- [ ] `grep -rn "NEXT_PUBLIC_\|VITE_" src/ .env*` — server secrets under public prefixes (CRITICAL).
- [ ] Production error handler leaks stacks/SQL to clients (`grep -rn "err.stack\|error.stack" src/` in response paths) — MEDIUM.
- [ ] Cookies: `grep -rn "Set-Cookie\|res.cookie" src/` — missing HttpOnly/Secure/SameSite on session cookies (HIGH).
- [ ] `grep -rn "res.redirect\|window.location.*=\|location.href.*=" src/` with request-derived values — open redirect (MEDIUM/HIGH near auth flows).
- [ ] Upload handlers: extension/MIME-only validation, client filename used in path (`grep -rn "originalname\|file.name" src/`) — HIGH.
- [ ] **Template raw-output syntax (§"Server-rendered HTML")** — in template files:
      `grep -rnE '<%-|!\{|^[[:space:]]*[[:alnum:]._#-]*!=|&attributes|\{\{\{|\{\{&' --include='*.ejs' --include='*.pug' --include='*.jade' --include='*.hbs' --include='*.handlebars' --include='*.mustache' .`
      — each hit fed user or DB content is stored/reflected XSS (HIGH/CRITICAL).
- [ ] **Template engines misused from code** —
      ``grep -rnE 'noEscape|Mustache\.escape *=|(ejs|pug|Handlebars|Mustache)\.(render|compile)\([^)]*req\.|res\.render\([^,)]*req\.|res\.(send|write|end)\( *`[^`]*<' --include='*.js' --include='*.ts' --include='*.mjs' --include='*.cjs' .``
      — a request value as EJS/Pug template *source* is CRITICAL (code execution). As a
      view *name* it is HIGH (renders templates outside `views/`). `noEscape`, a reassigned
      `Mustache.escape`, or HTML built in a template literal is XSS (HIGH).
- [ ] **Code chosen by the request, or a shell hidden in argv** —
      ``grep -rnE '(require|import)\( *([[:alpha:]_$]|`[^`]*\$\{)|[^[:alnum:]_](/bin/)?(ba|z|da)?sh[^[:alnum:]_] *, *\[ *[^[:alnum:]]-c[^[:alnum:]]|shelljs|shell\.exec\(' --include='*.js' --include='*.ts' --include='*.mjs' --include='*.cjs' .``
      — `require`/`import()` of a non-literal reached by request data is CRITICAL. So is
      `spawn('sh', ['-c', …])` or `shell.exec` with interpolated input. The `shell: true`
      probe above misses both.
- [ ] **YAML loader version** — `grep -rnE '"js-yaml": *"[~^]?[0-3]\.|safeLoad' --include='package.json' --include='*.js' --include='*.ts' --include='*.mjs' --include='*.cjs' .`
      — js-yaml below 4 with `load` on untrusted input is HIGH. A `safeLoad` call on js-yaml
      4 or later throws, so those hits are dead code.
- [ ] **NoSQL operator injection** —
      `grep -rnE '\.(find|findOne|findOneAndUpdate|findOneAndDelete|updateOne|updateMany|deleteOne|deleteMany|countDocuments|aggregate)\([^)]*req\.(body|query|params)|query parser.*extended' --include='*.js' --include='*.ts' --include='*.mjs' --include='*.cjs' .`
      — a request field in a filter without a scalar schema parse is HIGH (auth bypass via
      `{"$ne": null}`). The probe sees single-line calls only. Also check the Express major,
      because v4 defaults to the nesting `qs` parser.
- [ ] **Ajv configuration** — `grep -rnE 'allErrors: *true|\.compile\([^)]*req\.' --include='*.js' --include='*.ts' --include='*.mjs' --include='*.cjs' .`
      — `allErrors: true` on a request-validation path is MEDIUM (DoS). Compiling a
      request-supplied schema is HIGH.
- [ ] **CORS via the `cors` middleware** — `grep -rnE 'origin: *(true|/)' --include='*.js' --include='*.ts' --include='*.mjs' --include='*.cjs' .`
      — `origin: true` reflects every origin: HIGH with `credentials: true`. A regex origin
      must be anchored at both ends with the dot escaped, or it is HIGH.
- [ ] **JWT decoded but never verified** — `grep -rnE '(jwt|jsonwebtoken)\.decode\(|decodeJwt\(' --include='*.js' --include='*.ts' --include='*.mjs' --include='*.cjs' .`
      — on the server, a decoded claim that gates access is CRITICAL.
- [ ] **Path traversal: request data reaching the filesystem** (the rule is in §"Same family";
      this is its probe) —
      `grep -rnE '(readFile|readFileSync|createReadStream|writeFile|writeFileSync|createWriteStream|unlink|rm|readdir|sendFile|download|join|resolve)\([^)]*req\.(params|query|body)' --include='*.js' --include='*.ts' --include='*.mjs' --include='*.cjs' .`
      — each hit needs the resolve + containment check (HIGH without it). The probe sees
      single-line calls only.
- [ ] **Invisible or bidirectional characters in source (§"Invisible and bidirectional")** —
      `grep -rnE "$(printf '\342\200\213|\342\200\214|\342\200\215|\342\200\216|\342\200\217|\342\200\252|\342\200\253|\342\200\254|\342\200\255|\342\200\256|\342\201\240|\342\201\241|\342\201\242|\342\201\243|\342\201\244|\342\201\246|\342\201\247|\342\201\250|\342\201\251|\343\205\244|\357\276\240')" --include='*.js' --include='*.ts' --include='*.mjs' --include='*.cjs' .`
      — U+200B–200F, U+202A–202E, U+2060–2064, U+2066–2069, U+3164 and U+FFA0, written as
      UTF-8 bytes so the probe works under BSD grep and ugrep alike. A BOM at the start of a
      file is deliberately excluded. Any hit in code is HIGH until explained.
- [ ] `grep -rn "Math.random" src/` near token/id/code generation — HIGH; `grep -rn "=== .*signature\|signature ===" src/` — timing-unsafe compare (MEDIUM).
- [ ] **Publishing with a long-lived token instead of trusted publishing (npm supply chain) —
      HIGH for a published package** —
      `grep -rnE 'NODE_AUTH_TOKEN|NPM_TOKEN|_authToken' .github/workflows/ .npmrc` (a token
      where trusted publishing would do) ; `grep -rl 'npm publish' .github/workflows/` then read
      that job for `id-token: write` (npm's docs: trusted publishing needs it, and publishing
      that way from GitHub Actions or GitLab CI/CD generates provenance automatically, for a
      public package from a public repository)
