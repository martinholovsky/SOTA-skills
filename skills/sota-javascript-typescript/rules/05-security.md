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
- **Disable install scripts by default**: `npm config set ignore-scripts true` (or `.npmrc: ignore-scripts=true`) — this also skips the implicit `binding.gyp`/node-gyp path; pnpm ≥10 blocks them by default with an allowlist (`pnpm.onlyBuiltDependencies`); npm ≥12 (July 2026) blocks dependency install scripts including implicit node-gyp rebuilds by default, and refuses git and remote-URL tarball dependencies unless `--allow-git`/`--allow-remote` — build the allowlist before upgrading with `npm approve-scripts` (npm ≥11.16 warns). Allow per-package only what genuinely needs to build (esbuild, sharp).
- **Cooldown**: don't install or auto-merge dependency updates the day they publish; most hijacked versions are caught within days. Package managers now enforce this natively: pnpm 11 defaults `minimumReleaseAge` to 1440 minutes (1 day — don't opt out without reason); npm CLI ≥11.10 supports `minimumReleaseAge` in config; plus Renovate `minimumReleaseAge` (e.g. `7 days`) / Dependabot cooldown for update PRs.
- **Provenance & audit**: prefer packages publishing npm provenance (Sigstore attestation) — but provenance proves the publish path, not code safety: Miasma shipped malware with valid SLSA attestations from a compromised trusted-publishing workflow; `npm audit --omit=dev` in CI with a triage policy (fail on high/critical with no fix-path exception file); `osv-scanner` or Socket for behavioral flags (new maintainer, install script added, network in install).
- **Minimal deps**: every dep is trust granted to its maintainers and their deps transitively. Before adding: is it <100 lines you could own? Does the platform do it (rules/04 table)? Check maintenance, weekly downloads, dependency count.
- **Typosquatting**: verify exact names on add; scoped packages (`@org/x`) reduce risk. Pin GitHub Actions to commit SHAs, not tags.
- **Publishing**: trusted publishing (OIDC from CI — `npm trust` since CLI 11.10 configures it across packages in bulk) over long-lived tokens; npm's staged publishing adds a human 2FA approval gate before a version goes live — enable it for high-blast-radius packages (a stolen token alone then can't ship a release). `files` allowlist in package.json so secrets/configs never ship in the tarball.

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

## Tokens and client-side auth

- **Session/refresh tokens never in `localStorage`/`sessionStorage`** — any XSS exfiltrates them. Use cookies: `HttpOnly; Secure; SameSite=Lax` (or `Strict`), `Path` scoped, `__Host-` prefix.
- SameSite is CSRF defense-in-depth, not complete: keep CSRF tokens (or strictly enforce custom-header + CORS preflight) for state-changing routes if any non-SameSite path exists.
- If an SPA must hold an access token in JS (third-party API): keep it in memory only, short-lived (≤15min), refresh via httpOnly-cookie refresh token; accept that XSS can use (not just steal) it — XSS prevention remains the real control.
- **Verify JWTs server-side properly**: pin the algorithm (`{ algorithms: ['RS256'] }` — never accept `alg` from the token; `none` and HS/RS confusion attacks), validate `iss`, `aud`, `exp`, clock skew. Use `jose`. Don't put secrets in JWT payloads — they're only base64.
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
- Same family: never interpolate into SQL (parameterized queries only), `Function`, YAML `load` (use `safeLoad` semantics), or `vm`.

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
- User-supplied URLs the server fetches (webhooks, importers, avatars): allowlist protocols (`https:` only), resolve DNS and block private ranges (127/8, 10/8, 172.16/12, 192.168/16, 169.254/16 — cloud metadata `169.254.169.254`), block redirects-to-private (re-check after each redirect, `redirect: 'manual'`), pin timeouts and response-size caps. Library: `ssrf-req-filter` or equivalent egress proxy.
- Mass assignment: never `Model.update(req.body)` — schema-pick the allowed fields (`z.object({...}).strict()`).

## Timing and crypto hygiene

- Compare secrets (HMAC signatures, API keys, tokens) with `crypto.timingSafeEqual` (equal-length buffers — hash both sides first if lengths vary), never `===` (timing oracle).
- Randomness for anything security-relevant (tokens, IDs in URLs, reset codes): `crypto.randomUUID()` / `crypto.getRandomValues()` / `crypto.randomBytes` — never `Math.random()` (predictable, seedable state recovery is practical).
- Password hashing: argon2id (or scrypt/bcrypt with sane cost), async variants only (rules/04); never SHA-256-of-password, never homegrown.
- Web Crypto (`crypto.subtle`) for in-app encryption/signing; AES-GCM with unique IVs per encryption (IV reuse with GCM is catastrophic); keys from KMS/secret manager, not constants.

## Audit checklist

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
- [ ] CSP present? `grep -rn "Content-Security-Policy" src/` — absent on HTML-serving apps (MEDIUM); contains `unsafe-inline`/`unsafe-eval` in script-src (MEDIUM).
- [ ] Lockfile in git; CI uses `npm ci`/frozen lockfile; install scripts blocked (`.npmrc` `ignore-scripts`, pnpm allowlist, or npm ≥12 defaults + committed `approve-scripts` allowlist); install cooldown active (`minimumReleaseAge` — pnpm 11 default, npm ≥11.10, or Renovate/Dependabot) (each absent: MEDIUM).
- [ ] `grep -n "git+\|git://\|github:\|https://.*\.tgz" package.json` — git-URL or remote-tarball dependencies: unauditable, refused by npm ≥12 without `--allow-git`/`--allow-remote` (MEDIUM).
- [ ] Server-side fetch of user-supplied URLs: private-IP/metadata blocking + redirect handling (absent = HIGH, SSRF).
- [ ] Webhook handlers: signature verification before parsing (absent = HIGH).
- [ ] `grep -rn "Allow-Origin" src/` — `*` with credentials or unvalidated Origin reflection (HIGH).
- [ ] Built client bundle: `grep -rE "sk_live|AKIA|ghp_|-----BEGIN" dist/` — leaked secrets (CRITICAL). Repo: gitleaks in CI (absent = MEDIUM).
- [ ] `grep -rn "NEXT_PUBLIC_\|VITE_" src/ .env*` — server secrets under public prefixes (CRITICAL).
- [ ] Production error handler leaks stacks/SQL to clients (`grep -rn "err.stack\|error.stack" src/` in response paths) — MEDIUM.
- [ ] Cookies: `grep -rn "Set-Cookie\|res.cookie" src/` — missing HttpOnly/Secure/SameSite on session cookies (HIGH).
- [ ] `grep -rn "res.redirect\|window.location.*=\|location.href.*=" src/` with request-derived values — open redirect (MEDIUM/HIGH near auth flows).
- [ ] Upload handlers: extension/MIME-only validation, client filename used in path (`grep -rn "originalname\|file.name" src/`) — HIGH.
- [ ] `grep -rn "Math.random" src/` near token/id/code generation — HIGH; `grep -rn "=== .*signature\|signature ===" src/` — timing-unsafe compare (MEDIUM).
