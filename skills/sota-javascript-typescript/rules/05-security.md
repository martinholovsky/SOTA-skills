# JavaScript/TypeScript Security

Severity here maps to exploitability: attacker-controlled input reaching a sink = CRITICAL/HIGH; hardening gaps = MEDIUM; defense-in-depth = LOW.

## 1. XSS: know your sinks

XSS = untrusted data reaching an HTML/JS execution sink. Frameworks escape by default; every escape hatch is a sink.

Sinks to treat as hostile-by-default:
- `element.innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write`
- React `dangerouslySetInnerHTML`, Vue `v-html`, Angular `bypassSecurityTrust*`, Svelte `{@html}`
- `eval`, `new Function`, string args to `setTimeout`/`setInterval`
- `<a href>`/`location` assignment with user data — `javascript:` URLs
- jQuery `$(userInput)`, `.html()`
- Lit `unsafeHTML`/`unsafeSVG`/`unsafeMathML` (`lit/directives/unsafe-*.js`, lit 3.3)
- **DOM APIs that turn a string into code without any "HTML" in their name.** Measured in
  Chrome 151: `el.setAttribute('onclick', str)` ran `str` on click, and setting `innerText` of a
  new `<script>` ran it on insertion (`textContent` did the same in jsdom 29). URL attributes
  (`href`/`src`/`action`/`formaction`) accept `javascript:`, and `srcdoc` takes a whole HTML document.
  Build UI with `createElement` + `textContent` + `append`. Pass untrusted values to
  `setAttribute` only for a fixed allowlist of inert names (`title`, `alt`, `aria-*`,
  `data-*`), and attach handlers as functions (`addEventListener('click', fn)`), never as strings.
  Do not HTML-encode values set this way. `setAttribute('title', '&lt;b&gt;')` stored the
  literal `&lt;b&gt;` (measured), so the user sees the entities. *OWASP: Cross Site Scripting
  Prevention cheat sheet; DOM based XSS Prevention cheat sheet.* DOM clobbering, where injected
  markup with no script overwrites globals, is [rules/09](09-browser-platform-security.md).

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
  - **Dynamic code evaluation has more spellings than `eval(`.** `Function('a', src)` works
    without `new`. `node:vm` compiles code through `vm.Script`, `runInContext`,
    `runInNewContext`, `runInThisContext`, `compileFunction` and `SourceTextModule`. Its docs
    open with "The `node:vm` module is not a security mechanism. Do not use it to run
    untrusted code." Measured on Node 22.22:
    `vm.runInNewContext('this.constructor.constructor("return process")().version', {})`
    returned the host's `process.version`. EJS/Pug template source is code too (§"Server-rendered HTML").
  - **The safe shape is data, not code.** When input names an operation, look it up in a
    dispatch table (`const ops = new Map([['sum', sum], ['avg', avg]])`, unknown key → 400),
    never `obj[input]()`. User-authored formulas or rules need a parser for a fixed grammar
    you own or have vetted, evaluated over an explicit variable map, and never compiled to JS.
    Truly untrusted code runs in a separate process or isolate with its own resource limits
    ([`sota-sandboxing`](../../sota-sandboxing/SKILL.md)). *OWASP: Code Review Guide; Proactive Controls 2024 C3; ASVS 5.0 V1.3.*

## 2. CSP integration

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

## 3. Server-rendered HTML: template engines and hand-built strings

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
  above. The class is [`sota-code-security` rules/01](../../sota-code-security/rules/01-input-injection.md) §7.
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

## 4. Prototype pollution

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
- **Freezing is a security control for objects that other code could swap.** An escaper, a
  sanitizer wrapper or a security config held in a shared module can be overwritten by a
  polluted merge, a third-party script or injected code. Freeze it at creation
  (`Object.freeze`, or `Object.defineProperty` with `writable: false, configurable: false`
  plus `Object.preventExtensions`), or keep it in a closure or module-private binding that
  nothing else can reach. Two traps, measured on Node 22.22: in sloppy-mode code an
  assignment to a frozen property is **silently ignored** (strict mode throws `TypeError`),
  and `freeze` is shallow, so `Object.freeze({ opts: { allow: ['b'] } })` still let
  `opts.allow.push('script')` through. Freeze nested arrays and objects too.
- **Untrusted data never chooses a key on a global.** `window[name] = v` or
  `globalThis[name] = v` with a request- or URL-derived `name` lets the caller replace any
  global the app later calls (`globalThis['fetch'] = …` replaced `fetch`, measured). Keep
  untrusted values on the right-hand side, and store per-key data in a `Map`.
  *OWASP: DOM based XSS Prevention cheat sheet; DOM Clobbering Prevention cheat sheet;
  Nodejs Security cheat sheet.*

## 5. npm supply chain

The dependency tree is your attack surface; install scripts run arbitrary code on `npm install` (developer machines and CI). Worm campaigns like the 2025 Shai-Hulud worm spread exactly this way; the March 2026 axios compromise published malicious versions with a stolen npm token, bypassing the project's trusted-publishing setup — caught within a day, which is exactly what install cooldowns absorb; and the 2026 Miasma campaign (a Shai-Hulud derivative, 32+ `@redhat-cloud-services` packages) came in two shapes: its initial wave ran code from `preinstall` scripts, and a later wave (disclosed June 4) ran it from a phantom `binding.gyp` — the implicit `node-gyp rebuild` needs no declared install script — published through a compromised OIDC trusted-publishing workflow with valid SLSA provenance. A control that inspects only `scripts` in `package.json` misses the second shape.

- **Lockfile committed and exact**: `package-lock.json`/`pnpm-lock.yaml` in git; CI installs with `npm ci` / `pnpm install --frozen-lockfile` — never bare `npm install` in CI. **What unfreezes it without failing:** `npx <pkg>`/`npm exec`, `pnpm dlx` or `yarn dlx` of a package the lockfile does not hold (npm's docs: when stdin is not a TTY or CI is detected, `--yes` is assumed, so it fetches the current release unprompted), and a later `npm install`/`npm i <pkg>` step, often in a sub-directory. Make each CLI tool a devDependency and run it locally only: `npx --no-install <tool>` refused to download a missing package (measured, npm 10.9.4).
- **Disable install scripts by default**: `npm config set ignore-scripts true` (or `.npmrc: ignore-scripts=true`) — this also skips the implicit `binding.gyp`/node-gyp path; pnpm ≥10 blocks them by default with an allowlist — `allowBuilds` since **v11**, which **removed** `onlyBuiltDependencies`/`neverBuiltDependencies`/`ignoreDepScripts`; keep `strictDepBuilds` (setting added in v10.3.0, default `true` since v11.0.0) so an unreviewed build script **exits non-zero** instead of warning; npm ≥12 (July 2026) blocks dependency install scripts including implicit node-gyp rebuilds by default, and refuses git and remote-URL tarball dependencies unless allowed: `allow-git`/`allow-remote` take `all`, `none` (the npm 12 default) or `root` (only those your own `package.json` names), so write `--allow-git=root`, not a bare or abbreviated flag, since npm 12 throws on unknown and abbreviated CLI flags. Build the allowlist before upgrading with `npm approve-scripts` (npm ≥11.16 warns; npm 12's release notes name `npm install-scripts approve`, and 12.1.0 still documents both). Allow per-package only what genuinely needs to build (esbuild, sharp).
- **Know every hook that runs dependency code before your tests do** — the lifecycle scripts above are not the whole list:
  - *Install time*: `prepare` of a git or other non-registry dependency (npm installs that package's dependencies and runs it before packing); Yarn's `exec:` protocol (a generator script); a `.pnpmfile.cjs`/`.mjs` (its `updateConfig`, resolver and fetcher hooks run inside pnpm installs, and since pnpm 12.3.0 also in `pnpm run`/`exec`); `npx`/`npm exec` of a package you have not installed.
  - *Build time*: every plugin that `vite.config.*`, `webpack.config.*`, `babel.config.*`, `postcss.config.*` or `eslint.config.*` imports. These are plain Node modules and run with the build's environment.
- **The switch in each manager** (npm's `ignore-scripts` is above; it still runs a script named in `npm run <x>`, skipping only its `pre`/`post` hooks):
  - *npm 11.x*: an `allowScripts` map in `package.json`, written by `npm approve-scripts`. Entries are pinned to `pkg@version` by default (`allow-scripts-pin=true`), and in 11.19 an unapproved script only prints a warning. `--dangerously-allow-all-scripts` bypasses the whole policy.
  - *Yarn 4*: `enableScripts` in `.yarnrc.yml` defaults to `false` from 4.14.0 (it was `true` up to 4.13). Opt a single package in with `dependenciesMeta: { "<pkg>": { "built": true } }` in `package.json`. A skipped build is a warning, not a failure.
  - *Bun*: dependency scripts run only for names in `trustedDependencies` (`bun pm untrusted` lists the rest, `bun pm trust <pkg>` adds one). It also has a built-in default-trusted list, 366 names in bun 1.3.10 (`bun pm default-trusted`); anything on that list runs without being named in your file.
- **Review what runs, on every bump**: when an allowlisted package changes version, read the diff of the files it executes (`npm diff --diff=pkg@old --diff=pkg@new`, the `install`/`postinstall` target, `binding.gyp`) before re-approving it. Pinned approvals exist to force that stop. Your *own* build-executing files are code too: `package.json` `scripts`/`allowScripts`, `.npmrc`, `.yarnrc.yml`, `pnpm-workspace.yaml`, `.pnpmfile.*` and the build configs above. Give them a `CODEOWNERS` entry and turn on "Require review from Code Owners" in the branch rule or ruleset. That applies unchanged when an AI agent wrote the change.
- **Install without credentials in CI**: run `npm ci`/`pnpm install` in a job whose environment holds no registry, cloud or deploy secrets and no `id-token: write`. Publish or deploy from a separate job that takes only the built artifact. A malicious install script then has nothing to steal. (OWASP: NPM Security cheat sheet; CI/CD Security cheat sheet; Software Supply Chain Security cheat sheet.)
- **Cooldown**: don't install or auto-merge dependency updates the day they publish; most hijacked versions are caught within days. Package managers now enforce this natively: npm CLI ≥11.10 has `min-release-age` (days) in config; Yarn ≥4.10 has `npmMinimalAgeGate` in `.yarnrc.yml` (default `1d` since 4.15.0; `npmPreapprovedPackages` exempts names); plus Renovate `minimumReleaseAge` (e.g. `7 days`) / Dependabot cooldown for update PRs.
  **pnpm 11's built-in default fails open.** `minimumReleaseAge` defaults to 1440 minutes, but `minimumReleaseAgeStrict` is `false` unless you set `minimumReleaseAge` yourself, and non-strict means pnpm "falls back to a version that doesn't meet the `minimumReleaseAge` constraint" when nothing in range is old enough (pnpm settings docs). Measured on pnpm 12.6.0 with an exact pin to a version published that morning: with no config it installed (exit 0); with `minimumReleaseAge: 1440` written in `pnpm-workspace.yaml`, or `minimumReleaseAgeStrict: true`, it exited 1 (`ERR_PNPM_NO_MATURE_MATCHING_VERSION`). And `minimumReleaseAgeIgnoreMissingTime` defaults to `true`, which skips the check for a registry or mirror whose metadata has no `time` field. So write both into `pnpm-workspace.yaml`: `minimumReleaseAge: 1440` (or longer) and, behind a private registry or mirror, `minimumReleaseAgeIgnoreMissingTime: false`.
- **Provenance & audit**: prefer packages publishing npm provenance (Sigstore attestation) — but provenance proves the publish path, not code safety: Miasma shipped malware with valid SLSA attestations from a compromised trusted-publishing workflow. pnpm's `trustPolicy: no-downgrade` (v10.21.0, default `off`) turns provenance into an install gate: it fails when a version carries weaker trust evidence than an earlier-published one — the axios case above, where a stolen token published without the project's trusted publisher. It cannot catch a release that has valid provenance (Miasma), and `trustPolicyExclude`/`trustPolicyIgnoreAfter` loosen it; `npm audit --omit=dev` in CI with a triage policy (fail on high/critical with no fix-path exception file); `osv-scanner` or Socket for behavioral flags (new maintainer, install script added, network in install).
- **Minimal deps**: every dep is trust granted to its maintainers and their deps transitively. Before adding: is it <100 lines you could own? Does the platform do it ([rules/04](04-node-backend.md) table)? Check maintenance, weekly downloads, dependency count.
- **Before adding a dependency, vet it — including every name an AI assistant proposed**: a suggested name may not exist, or may have been registered recently by someone betting that it will be suggested (slopsquatting), and a one-letter slip is a typosquat. `npm view <name> time.created maintainers repository.url dist-tags.latest` fails with E404 on an unknown name; read the creation date, maintainer count and the repository it links, and confirm that repository is the project you meant. Then `https://deps.dev/npm/<name>` (or `api.deps.dev/v3/systems/npm/packages/<name>`) for versions, advisories, deprecations and licence, and OpenSSF Scorecard (`scorecard --npm=<name>`, or `api.securityscorecards.dev/projects/github.com/<owner>/<repo>`) for maintenance signals. Scoped packages (`@org/x`) reduce the squatting risk. Pin GitHub Actions to commit SHAs, not tags.
- **A library's defaults are part of your code**, and README samples are demos: audit every security-relevant option you pass or omit. Verified examples: `cors()` with no options sends `Access-Control-Allow-Origin: *` (cors 2.8.6 `origin: '*'`); axios `timeout` defaults to `0`, meaning no timeout (axios 1.20.0 `lib/defaults`); `marked` does not sanitize its HTML output (its README says so; wrap it in `DOMPurify.sanitize`); express-session leaves the cookie's `Secure` attribute unset unless `cookie.secure` is set, and its README examples use the secret `'keyboard cat'`. A copied sample brings its demo settings with it, such as `rejectUnauthorized: false` ([rules/04](04-node-backend.md)), `origin: true` or a debug flag. (OWASP: Vulnerable Dependency Management cheat sheet; Software Supply Chain Security cheat sheet; Secure Coding with AI cheat sheet; SCVS V1, V6.)
- **Publishing**: trusted publishing (OIDC from CI — `npm trust` since CLI 11.10 configures it across packages in bulk) over long-lived tokens; npm's staged publishing adds a human 2FA approval gate before a version goes live — enable it for high-blast-radius packages (a stolen token alone then can't ship a release). `files` allowlist in package.json so secrets/configs never ship in the tarball.
- **A bundle has no dependency list a scanner can read**: a bundler (esbuild, webpack, Rollup) or a Node single executable application drops every `package.json`, so an image scan of the output reports nothing; generate the SBOM at build time from the lockfile ([`sota-devsecops` rules/14](../../sota-devsecops/rules/14-sbom-component-inventory.md) §14.6). `vercel/pkg` is archived: do not adopt it.

## 6. Invisible and bidirectional characters in source

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
text bound for an LLM or a UI, is [`sota-code-security` rules/09](../../sota-code-security/rules/09-untrusted-data-ingestion.md) §4.

## 7. ReDoS

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

## 8. Tokens and client-side auth

- **Session/refresh tokens never in `localStorage`/`sessionStorage`** — any XSS exfiltrates them (other sensitive data in browser storage: [rules/09](09-browser-platform-security.md)). Use cookies: `HttpOnly; Secure; SameSite=Lax` (or `Strict`), `Path` scoped, `__Host-` prefix.
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
- **Every other cookie the app sets starts from the framework's defaults, and none sets
  `HttpOnly` or `Secure`.** Measured with a bare `('pref', 'dark')` call: Express 5.2.1
  `res.cookie` emits `pref=dark; Path=/`. Hono 4.13 `setCookie` and Next 15.5's
  `ResponseCookies` (the class behind `cookies().set`) emit the same. `@fastify/cookie` 11.1
  `reply.setCookie` emits `pref=dark; SameSite=Lax`. Pass `{ httpOnly: true, secure: true,
  sameSite: 'lax' }` explicitly, or wrap one helper that does, and set `Domain` only when a
  subdomain must read the cookie. Drop `httpOnly` only when page JS must read the value, and
  never for a value that authorizes anything. A cookie written by `document.cookie` can never
  be HttpOnly. **The `__Host-` prefix is not checked by every server:** Hono threw
  "__Host- Cookie must have Secure attributes" without `secure`, while Express sent
  `__Host-pref=dark; Path=/; HttpOnly`, which browsers reject. *OWASP: Session Management
  cheat sheet; Cookie Theft Mitigation cheat sheet; ASVS 5.0 V3.3.*
- Rotate session IDs on every privilege change (session fixation, HIGH — the trigger list is [`sota-code-security` rules/17](../../sota-code-security/rules/17-sessions-and-tokens.md) §2); server-side revocation list or short-lived JWT + refresh rotation with reuse detection.
- CSRF for cookie-authed JSON APIs: require a custom header (e.g. `X-Requested-With`) and strict CORS — preflight enforcement makes cross-origin forgery fail; forms still need synchronizer tokens.
- CORS: never `Access-Control-Allow-Origin: *` with `Allow-Credentials: true` (browsers reject it; reflecting `Origin` unvalidated recreates the hole — allowlist exact origins).

## 9. Secrets in code and client bundles

- Anything in frontend code ships to the attacker: API keys in `VITE_*`/`NEXT_PUBLIC_*` vars are public by definition — only put genuinely-public keys there (analytics write keys, maps keys with referrer locks). Server-only secrets must never appear in client-reachable modules; Next.js server/client boundary violations leak env into the bundle.
- `grep` the built bundle for key prefixes (`sk_live`, `AKIA`, `ghp_`, `AIza`) as a release gate; gitleaks/trufflehog pre-commit and in CI for the repo itself.
- Error responses: never echo stack traces, SQL, or internal paths to clients in production — log them server-side with the request ID, return the ID in the error body for correlation.

## 10. postMessage and cross-origin

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

**Web Workers follow the same rule in both directions.** A worker's script is code: build it
only from files you ship, never from user input through a `Blob`/`data:` URL, a
`new Worker(url)` whose URL varies, or `importScripts()` inside the worker. Messages between
page and worker (`onmessage`, `MessagePort`) are untrusted input on each side: schema-parse
them, map them to a fixed set of actions, and never `eval` them or write them to an HTML sink.
Restrict worker sources with the CSP `worker-src` directive. *OWASP: HTML5 Security cheat sheet.*

Command injection via `child_process` and SSRF moved to
[rules/08](08-process-and-outbound.md) on 2026-09-25, section names unchanged.

## 11. Open redirects and file uploads

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

## 12. Timing and crypto hygiene

- Compare secrets (HMAC signatures, API keys, tokens) with `crypto.timingSafeEqual` (equal-length buffers — hash both sides first if lengths vary), never `===` (timing oracle).
- Randomness for anything security-relevant (tokens, IDs in URLs, reset codes): `crypto.randomUUID()` / `crypto.getRandomValues()` / `crypto.randomBytes` — never `Math.random()` (predictable, seedable state recovery is practical).
- Password hashing: argon2id (or scrypt/bcrypt with sane cost), async variants only ([rules/04](04-node-backend.md)); never SHA-256-of-password, never homegrown (audit: [`sota-code-security` rules/02](../../sota-code-security/rules/02-authentication.md) §1).
- Web Crypto (`crypto.subtle`) for in-app encryption/signing; AES-GCM with unique IVs per encryption (IV reuse with GCM is catastrophic); keys from KMS/secret manager, not constants.

## 13. Native addons and uninitialized buffers

Three ways Node leaves memory safety. **Native addons** (`.node` files, Node-API /
`node-addon-api`, built with `node-gyp`) are C or C++ inside the process: audit them as such.
**`Buffer.allocUnsafe`** needs no native code at all. Node's docs say its memory "is *not
initialized*" and "may contain sensitive data", so a buffer sent before every byte is
overwritten leaks earlier allocations: tokens, keys, other users' data. Use `Buffer.alloc`
unless a benchmark justifies the unsafe form *and* the code provably overwrites the whole
buffer first. **`node:ffi`** (Stability 1 — Experimental; added v26.1.0 behind
`--experimental-ffi`, on by default since v26.9.0) calls native symbols and reads and writes
raw pointers from JavaScript with no compiled addon; its docs call the API "unsafe", able to
"crash the process or corrupt memory". Treat an import of it as native code, and start
production processes with `--permission` without `--allow-ffi` (measured on v26.7.0: `dlopen`
threw `ERR_ACCESS_DENIED`) or with `--no-experimental-ffi`, unless a reviewed feature needs it.
The docs say that flag exists "only in builds with FFI support": on v22 (v22.22.1, v22.23.3) the
command line prints `bad option: --no-experimental-ffi` and `NODE_OPTIONS` prints
`--no-experimental-ffi is not allowed in NODE_OPTIONS`, both exit 9, so the process never starts
on a runtime without FFI. The class is [`sota-code-security` rules/06](../../sota-code-security/rules/06-memory-resource-safety.md) §3.
An addon you build runs its tests in CI against a `-fsanitize=address,undefined` build, with the sanitizer runtime loaded by `LD_PRELOAD`.
Run that job on Linux: on macOS, SIP and the hardened runtime strip `DYLD_INSERT_LIBRARIES`.

## Audit checklist

- [ ] **Uninitialized buffers and native addons — HIGH if the buffer can leave the process** —
      `grep -rnE 'Buffer\.allocUnsafe(Slow)?\(|new Buffer\(' --include='*.js' --include='*.ts' --include='*.mjs' --include='*.cjs' .`
      ; `grep -rnE 'node-addon-api|node-gyp|"gypfile"|\.node([^a-zA-Z0-9]|$)|node:ffi|--allow-ffi' --include='package.json' --include='*.js' --include='*.ts' --include='*.mjs' --include='*.cjs' --include='Dockerfile*' --include='*.yml' --include='*.yaml' .`
      — a `node:ffi` import or `--allow-ffi` grant is native code to audit as C (HIGH if its arguments are request-derived). `grep -rqE 'fsanitize=(address|undefined)' --include='binding.gyp' --include='*.yml' --include='*.yaml' --exclude-dir=node_modules . || grep -rl --include='binding.gyp' --exclude-dir=node_modules . .` lists the repo's own `binding.gyp` files when no sanitizer job exists (MEDIUM, §13).
- [ ] `grep -rn "innerHTML\|outerHTML\|insertAdjacentHTML\|document.write" --exclude-dir=node_modules .` — each with non-constant input is HIGH (§1), CRITICAL where script can read a session token or secret; constant strings LOW.
- [ ] `grep -rn "dangerouslySetInnerHTML\|v-html\|{@html}\|bypassSecurityTrust" --exclude-dir=node_modules . | grep -v "DOMPurify\.sanitize("` — lists sinks with no `DOMPurify.sanitize(` on the line: sanitized upstream? Unsanitized user/db content = HIGH (stored XSS), CRITICAL where script can read a session token or secret. Server-embedded state: `grep -rnE '<script[^>]*>[^<]*\$\{ *JSON\.stringify\(' --include='*.ts' --include='*.js' --include='*.tsx' --exclude-dir=node_modules . | grep -v 'u003c'` — `JSON.stringify` inside a `<script>` without escaping `<` allows `</script>` breakout (HIGH) (§1).
- [ ] ``grep -rn "eval(\|new Function(\|setTimeout(['\"\`]\|setInterval(['\"\`]" --exclude-dir=node_modules .`` — CRITICAL with dynamic input (§1).
- [ ] **Dynamic code evaluation beyond `eval(` (§"XSS", the `node:vm` bullet) (§1) — CRITICAL
      when request data reaches it** —
      `grep -rnE '(^|[^[:alnum:]_.])Function\(|vm\.(Script|runIn(New|This)?Context|compileFunction|SourceTextModule)|new (vm\.)?Script\(|\[[^]]*req\.(body|query|params)[^]]*\] *\(' --include='*.js' --include='*.ts' --include='*.mjs' --include='*.cjs' .`
      — hits are the `Function` constructor without `new`, `node:vm` used as a "sandbox",
      and a method called by a request-chosen name. Replace with a dispatch table, a
      fixed-grammar evaluator, or an out-of-process isolate.
- [ ] **String-to-code DOM APIs (§"XSS", the DOM APIs bullet) (§1) — HIGH with request or stored
      data** —
      ``grep -rnE "setAttribute\( *['\"](on[a-z]+|href|src|action|formaction|srcdoc)['\"] *, *[^'\" ]|unsafe(HTML|SVG|MathML)\(|createElement\( *['\"]script['\"]" --include='*.js' --include='*.ts' --include='*.mjs' --include='*.tsx' .``
      — a variable into an event-handler, URL or `srcdoc` attribute, a Lit `unsafe*` directive,
      or a script element built in code (read what sets its text or `src`).
- [ ] `grep -rn "href={" --include="*.tsx" --exclude-dir=node_modules .` lists every dynamic JSX href; each hit is read, not a finding: user-controlled hrefs without protocol allowlist (§1) (`javascript:`) = HIGH.
- [ ] `grep -rn "localStorage.setItem\|sessionStorage.setItem" --exclude-dir=node_modules . | grep -i "token\|jwt\|session\|auth\|key"` — HIGH (§8).
- [ ] `grep -rnE "postMessage\(.*, *['\"]\*['\"]" --exclude-dir=node_modules .` — `'*'` target with sensitive data (HIGH); then read each `message` listener for an origin check (HIGH). `grep -rnE "target=[\"'{]*_blank" --include='*.tsx' --include='*.jsx' --include='*.html' --include='*.vue' --exclude-dir=node_modules . | grep -v noopener` — external links opened with `target="_blank"` and no `rel="noopener"` hand over `window.opener` (LOW) (§10).
- [ ] **Worker script built from data (§"postMessage", the Web Workers paragraph) (§10) — HIGH with user input** —
      ``grep -rnE "new (Shared)?Worker\( *([^'\"\` ]|['\"\`](data|blob):|\`[^\`]*\\$\{)|importScripts\( *[^'\"\` )]" --include='*.js' --include='*.ts' --include='*.mjs' --include='*.tsx' . | grep -vE "Worker\( *new URL\( *['\"]"``
      — a worker URL from a variable, `Blob`, `data:` or template, or a non-literal `importScripts`. Read each worker's `onmessage` for a schema parse.
- [ ] **Attacker-chosen key written to a global (§4) — HIGH when the key is request- or URL-derived** —
      ``grep -rnE "(window|globalThis|self)\[ *[^]'\"\` ][^]]*\] *=[^=]" --include='*.js' --include='*.ts' --include='*.mjs' --include='*.tsx' .``
      — then read shared escapers and security config for a runtime `Object.freeze` (unfrozen and exported: MEDIUM).
- [ ] Deep-merge of request data (§4): `grep -rnE "(merge|deepmerge|Object\.assign)\([^()]*req\.(body|query)" --exclude-dir=node_modules .` (request data passed straight in; read merges of parsed `json()` too) — prototype pollution exposure (HIGH); `grep -rn "__proto__" --exclude-dir=node_modules .` lists every `__proto__` reference; each hit is read, not a finding (one in tests/guards is good signal of awareness).
- [ ] `grep -rn "jwt.verify\|jwtVerify" --exclude-dir=node_modules . | grep -v "algorithms"` — lists verify calls with no `algorithms` option on the line: algorithm not pinned = HIGH (§8); read a multi-line call before rating it. `aud`/`iss` checked?
- [ ] Regex on user input (§7): `grep -rn "new RegExp(" --exclude-dir=node_modules .` (dynamic patterns = ReDoS + injection risk, HIGH); run `eslint-plugin-regexp`/recheck over static patterns.
- [ ] **Regex escaping, anchoring and engine (§7, the four control failures) — HIGH on a
      validator or allowlist** —
      ``grep -rnE 'new RegExp\( *[[:alpha:]_$`]|/[dgimsuvy]*[gmy][dgimsuvy]*\.test\(|/\^[^(/|]*\|[^/]*\$/' --include='*.js' --include='*.ts' --include='*.mjs' --include='*.cjs' . | grep -v 'RegExp\.escape('``
      — hits are a pattern built from a variable without `RegExp.escape`, a `.test()` on a
      literal carrying `m`/`g`/`y`, and a `/^a|b$/` alternation outside a group. A request value
      in an unescaped pattern is HIGH (pattern injection plus ReDoS). An `m`/`g` validator or an
      ungrouped alternation is HIGH when it guards access. The probe sees inline literals only:
      a flagged regex held in a `const` needs a read, and so do JSON Schema `pattern`s without `^…$`.
      Complex patterns on untrusted input should run on the linear-time `re2` engine, or it is MEDIUM. So is a validator with no `input.length` cap before matching.
- [ ] CSP present? `grep -rq "Content-Security-Policy" --exclude-dir=node_modules . || echo 'no Content-Security-Policy anywhere'; grep -rn "Content-Security-Policy.*unsafe-\(inline\|eval\)" --exclude-dir=node_modules .` — absent on HTML-serving apps (MEDIUM); contains `unsafe-inline`/`unsafe-eval` in script-src (MEDIUM). `grep -rnE "'nonce-[A-Za-z0-9+/=_-]{8,}'" --exclude-dir=node_modules .` — a nonce written into config is reused on every response, which makes the policy as weak as `unsafe-inline` (MEDIUM); missing `object-src 'none'`, `base-uri 'none'` or `frame-ancestors` is LOW (§2).
- [ ] Lockfile in git (§5); CI uses `npm ci`/frozen lockfile; install scripts blocked (`.npmrc` `ignore-scripts`, pnpm allowlist, or npm ≥12 defaults + committed `approve-scripts` allowlist); install cooldown active (each absent: MEDIUM) — npm ≥11.10 `min-release-age`, Yarn `npmMinimalAgeGate`, Renovate/Dependabot, or pnpm with `minimumReleaseAge` **written** in `pnpm-workspace.yaml` or `minimumReleaseAgeStrict: true` (the built-in default alone fails open), plus `minimumReleaseAgeIgnoreMissingTime: false` behind a private registry or mirror: `grep -qE 'minimumReleaseAge(Strict)?:' pnpm-workspace.yaml || echo 'pnpm-workspace.yaml: no minimumReleaseAge written'`, then read it for `minimumReleaseAgeIgnoreMissingTime: false` and `trustPolicy: no-downgrade` (no `trustPolicy` on a pnpm repo: LOW).
- [ ] **Frozen install bypassed (§5, the lockfile bullet) — HIGH in CI, an image build or a deploy, MEDIUM on a developer-only path ([`sota-devsecops` rules/03](../../sota-devsecops/rules/03-dependencies.md) §3.1)** — `grep -rnE '(^|[^[:alnum:]_-])(npx|bunx|npm exec|pnpm dlx|yarn dlx)[[:space:]]+[^-[:space:]]|(^|[^[:alnum:]_-])npm (install|i)([[:space:]]|$)' .github/workflows/ ; grep -rnE '(^|[^[:alnum:]_-])(npx|bunx|npm exec|pnpm dlx|yarn dlx)[[:space:]]+[^-[:space:]]|(^|[^[:alnum:]_-])npm (install|i)([[:space:]]|$)' --include='Dockerfile*' --include='*.sh' --include='Makefile' --exclude-dir=node_modules .`
      — a `npx`/`dlx` of a tool that is not a devDependency runs whatever is current; `npm install` re-resolves the lock.
- [ ] **Bundled or single-executable artifact with no build-time SBOM (§"npm supply chain", the bundle bullet) (§5) — MEDIUM, HIGH for a deployed service ([`sota-devsecops` rules/14](../../sota-devsecops/rules/14-sbom-component-inventory.md) §14.6)** — `grep -nE '"(esbuild|webpack|rollup|postject)"|sea-config' package.json` lists every bundler or SEA config; each hit is read, not a finding: a hit on a shipped artifact needs an SBOM generated from the lockfile in CI; an image scan of the bundle does not stand in for it.
- [ ] **Install-time code execution re-enabled or unreviewed (§"npm supply chain") (§5) — HIGH** —
      `grep -rnE 'dangerously-allow-all-scripts|no-allow-scripts-pin|allow-scripts-pin *= *false|ignore-scripts *= *false|enableScripts: *true|approve-scripts +--all|install-scripts +approve +--all|dangerouslyAllowAllBuilds: *true|allow-(git|remote) *= *all|bun pm trust +--all' --include='package.json' --include='.npmrc' --include='.yarnrc.yml' --include='*.yml' --include='*.yaml' --exclude-dir=node_modules .`
      — each hit turns lifecycle scripts back on wholesale, or approves them unread. Then
      `grep -sqE 'package\.json|\.npmrc|\.yarnrc|pnpmfile|pnpm-workspace' .github/CODEOWNERS CODEOWNERS docs/CODEOWNERS || echo 'CODEOWNERS: no owner for package.json/.npmrc/pnpm config'`
      — no owner for these files is MEDIUM. A workflow whose install step can read a
      registry/cloud secret or `id-token: write` needs a read (HIGH if it can).
- [ ] **New dependency vetted, insecure defaults configured (§"npm supply chain") (§5) — MEDIUM, HIGH on a request path** —
      `grep -rnE 'cors\(\)|keyboard cat|axios\.create\(\)|marked\.parse\(' --include='*.js' --include='*.ts' --include='*.mjs' --include='*.cjs' --exclude-dir=node_modules . | grep -v 'DOMPurify\.sanitize('`
      — each hit is a default or README sample left in place (open CORS, no timeout, unsanitized Markdown, the demo session secret).
      For each name the PR adds to `package.json`, run `npm view <name> time.created maintainers repository.url`: E404 or a days-old package is HIGH until explained.
- [ ] `grep -n "git+\|git://\|github:\|https://.*\.tgz" package.json` — git-URL or remote-tarball dependencies (§5): unauditable, refused by npm ≥12 unless `allow-git`/`allow-remote` is `root` or `all` (MEDIUM).
- [ ] `grep -rnE "Allow-Origin['\"]?, *(['\"]\*['\"]|req\.headers\.origin|req\.get\(['\"]origin)" --exclude-dir=node_modules .` — `*` with credentials or unvalidated Origin reflection (§8) (HIGH).
- [ ] Built client bundle: `grep -rE "sk_live|AKIA|ghp_|-----BEGIN" dist/` — leaked secrets (CRITICAL). Repo: gitleaks in CI (absent = MEDIUM). (§9)
- [ ] `grep -rnE "(NEXT_PUBLIC_|VITE_)[A-Z0-9_]*(SECRET|TOKEN|PASSWORD|PRIVATE)" --exclude-dir=node_modules .` — server secrets under public prefixes (§9) (CRITICAL).
- [ ] Production error handler leaks stacks/SQL to clients (§9) (`grep -rn "err.stack\|error.stack" --exclude-dir=node_modules .` in response paths) — MEDIUM.
- [ ] Cookies: `grep -rn "Set-Cookie\|res.cookie" --exclude-dir=node_modules . | grep -vE 'httpOnly: *true.*secure: *true|secure: *true.*httpOnly: *true|HttpOnly.*Secure|Secure.*HttpOnly'` — missing HttpOnly/Secure/SameSite on session cookies (HIGH). Session IDs not rotated on login or privilege change, and cookie-authed state-changing routes with no CSRF token or custom-header check, are HIGH (§8).
- [ ] **App-set cookie attribute defaults (§"Tokens and client-side auth") (§8) — MEDIUM, HIGH if
      the value authorizes anything** —
      `grep -rnE '(res|reply)\.(cookie|setCookie)\(|setCookie\(|cookies\(\)\.set\(|\.cookies\.set\(|document\.cookie *=' --include='*.js' --include='*.ts' --include='*.mjs' --include='*.cjs' --include='*.tsx' . | grep -vE 'httpOnly: *true.*secure: *true|secure: *true.*httpOnly: *true'`
      — a call without both `httpOnly` and `secure` inline gets Express/Hono/Next's `Path=/` only
      (Fastify adds `SameSite=Lax`). Read calls whose options are a variable.
- [ ] `grep -rnE "res\.redirect\([^)]*req\.|location(\.href)? *=.*(search|hash|params|get\()" --exclude-dir=node_modules .` with request-derived values — open redirect (§11) (MEDIUM, HIGH in a login/OAuth flow or on an SSRF-trusted host: [`sota-code-security` rules/01](../../sota-code-security/rules/01-input-injection.md) §11).
- [ ] Upload handlers: extension/MIME-only validation, client filename used in path (`grep -rn "originalname\|file.name" --exclude-dir=node_modules .`) — HIGH. User uploads served inline without `Content-Disposition: attachment` + `nosniff`, or SVGs served unsanitized from the app origin, are HIGH; images not re-encoded is LOW (§11).
- [ ] **Template raw-output syntax (§3)** — in template files:
      `grep -rnE '<%-|!\{|^[[:space:]]*[[:alnum:]._#-]*!=|&attributes|\{\{\{|\{\{&' --include='*.ejs' --include='*.pug' --include='*.jade' --include='*.hbs' --include='*.handlebars' --include='*.mustache' .`
      — each hit fed user or DB content is stored/reflected XSS (HIGH/CRITICAL).
- [ ] **Template engines misused from code** (§3) —
      ``grep -rnE 'noEscape|Mustache\.escape *=|(ejs|pug|Handlebars|Mustache)\.(render|compile)\([^)]*req\.|res\.render\([^,)]*req\.|res\.(send|write|end)\( *`[^`]*<' --include='*.js' --include='*.ts' --include='*.mjs' --include='*.cjs' .``
      — a request value as EJS/Pug template *source* is CRITICAL (code execution). As a
      view *name* it is HIGH (renders templates outside `views/`). `noEscape`, a reassigned
      `Mustache.escape`, or HTML built in a template literal is XSS (HIGH). So is a hand escaper using `.replace('<', …)` with a string pattern: it replaces only the first match.
- [ ] **CORS via the `cors` middleware** (§8) — `grep -rnE 'origin: *(true|/)' --include='*.js' --include='*.ts' --include='*.mjs' --include='*.cjs' .`
      — `origin: true` reflects every origin: HIGH with `credentials: true`. A regex origin
      must be anchored at both ends with the dot escaped, or it is HIGH.
- [ ] **JWT decoded but never verified** (§8) — `grep -rnE '(jwt|jsonwebtoken)\.decode\(|decodeJwt\(' --include='*.js' --include='*.ts' --include='*.mjs' --include='*.cjs' .`
      — on the server, a decoded claim that gates access is CRITICAL.
- [ ] **Invisible or bidirectional characters in source (§6)** —
      `grep -rnE "$(printf '\342\200\213|\342\200\214|\342\200\215|\342\200\216|\342\200\217|\342\200\252|\342\200\253|\342\200\254|\342\200\255|\342\200\256|\342\201\240|\342\201\241|\342\201\242|\342\201\243|\342\201\244|\342\201\246|\342\201\247|\342\201\250|\342\201\251|\343\205\244|\357\276\240')" --include='*.js' --include='*.ts' --include='*.mjs' --include='*.cjs' .`
      — U+200B–200F, U+202A–202E, U+2060–2064, U+2066–2069, U+3164 and U+FFA0, written as
      UTF-8 bytes so the probe works under BSD grep and ugrep alike. A BOM at the start of a
      file is deliberately excluded. Any hit in code is HIGH until explained.
- [ ] `grep -rn "Math.random" --exclude-dir=node_modules .` near token/id/code generation — HIGH; `grep -rn "=== .*signature\|signature ===" --exclude-dir=node_modules .` — timing-unsafe compare (MEDIUM). `grep -rnE 'subtle\.(encrypt|importKey)\(' --include='*.ts' --include='*.js' --include='*.mjs' --exclude-dir=node_modules .` lists every encrypt/importKey call; each hit is read, not a finding: each AES-GCM call needs a fresh random IV and a key from a KMS or secret manager, not a constant (HIGH) (§12).
- [ ] **Publishing with a long-lived token instead of trusted publishing (npm supply chain) (§5) —
      HIGH for a published package** —
      `grep -rnE 'NODE_AUTH_TOKEN|NPM_TOKEN|_authToken' .github/workflows/ .npmrc` (a token
      where trusted publishing would do) ; `grep -rl 'npm publish' .github/workflows/ | xargs -r grep -L 'id-token: *write'` lists the
      publishing workflows with no `id-token: write` (npm's docs: trusted publishing needs it, and publishing
      that way from GitHub Actions or GitLab CI/CD generates provenance automatically, for a
      public package from a public repository)
