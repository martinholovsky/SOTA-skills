# 08 — Child Processes & Outbound Requests (server-side)

Split out of rules/05 on 2026-09-25, when rules/05 neared the 500-line cap. Section names are
unchanged, so an older citation of rules/05 §"Command injection via child_process" or
§"SSRF and server-side validation" names the same text here.

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

## SSRF and server-side validation

- Every inbound payload schema-parsed at the boundary (rules/01) — including webhooks (verify signatures: Stripe/GitHub HMAC) and headers you act on.
- User-supplied URLs the server fetches (webhooks, importers, avatars): allowlist protocols (`new URL(u).protocol === 'https:'`, checked again on every redirect hop), block private ranges (127/8, 10/8, 172.16/12, 192.168/16, 169.254/16 — cloud metadata `169.254.169.254`), handle redirects (below), pin timeouts and response-size caps. Library: `ssrf-req-filter` or equivalent egress proxy. The generic policy is `sota-code-security` rules/01 §5; the Node idiom:
  - **Best: never relay a caller URL.** Accept a service key or record ID, look the origin up in a server-side map, and build the URL with `new URL(path, base)` plus `encodeURIComponent` on each segment. The rest of this list is for when you genuinely must fetch an arbitrary URL.
  - **Check the address at connect time, not before.** A `dns.lookup()` done before `fetch()` is a separate resolution from the one the socket uses, so a rebinding DNS server answers public to the check and `127.0.0.1` to the connection. Put the check in the resolver the socket calls: `new Agent({ connect: { lookup } })` from the `undici` package (its connector spreads `connect` into `net.connect`/`tls.connect`), or the `lookup` option of `http.request`/`https.request` and of axios. Measured on Node 22.22.1: the hook is called with `{ all: true }` (family autoselection), so it must resolve all addresses, reject if **any** is blocked, and answer in the array form. Test each address with a `net.BlockList` covering 127/8, 10/8, 172.16/12, 192.168/16, 169.254/16, 100.64/10, 0/8, 224/4, `::1`, `fc00::/7`, `fe80::/10`, `ff00::/8`; a v4 subnet also matched `::ffff:127.0.0.1` checked as `ipv6`. Also refuse the metadata host names (`metadata.google.internal` on GCP, whose IPv6 metadata address `fd20:ce::254` falls in `fc00::/7`; check your cloud's docs for its own) by name.
  - **The hook never sees an IP literal.** `fetch('http://127.0.0.1/')` through that Agent returned 200 with zero `lookup` calls (undici 8.11.2; `http.get` skips it too). So check a literal host yourself before dispatch: `new URL(u).hostname`, strip the `[]` around IPv6 (`net.isIP('[::1]')` is 0), then `net.isIP` + the same BlockList.
  - **Parse with WHATWG `URL`, not a regex or the `ip` package.** `new URL()` canonicalises `0x7f.1`, `0177.0.0.1` and `2130706433` to `127.0.0.1` (measured), whereas `net.isIP` returns 0 for those raw strings, so a check on the unparsed string treats them as host names. `ip`'s `isPublic` misclassifies `127.1`, octal forms and `::fFFf:127.0.0.1` in every version through 2.0.1 with no patch (CVE-2024-29415).
  - **Use `undici`'s own `fetch` with its `Agent`.** Passing an `undici@8` `Agent` as `dispatcher` to Node 22's global `fetch` (bundled undici 6.23) failed with `invalid onRequestStart method` — a major mismatch, measured.
  - **Redirects**: `redirect: 'error'` rejects any 3xx; `redirect: 'manual'` returns it so you re-validate `Location` and fetch the next hop yourself (bounded count). The default `'follow'` goes wherever the server says. In axios, `maxRedirects: 0` or a `beforeRedirect` that re-checks. Under the default `follow` the Agent's `lookup` still ran on the hop and blocked a 302 to `localhost` (measured), but that does not cover a literal-IP hop; only scheme and literal-IP checks need repeating per hop.
  - **Credentials on a redirect.** Node's global `fetch`, undici 8.11.2, axios 1.20.0 (through
    follow-redirects 1.16.0) and got 14.6.6 all removed `Authorization` and `Cookie` when a 302
    sent the request to another host or another port (measured). The edges differ, per their
    source. follow-redirects **keeps** both headers on a redirect to a *subdomain* of the current
    host, and drops them on a switch to any protocol other than `https:`. got compares hostname
    and port but not scheme, so an `https:`→`http:` hop on default ports keeps them. undici's
    `fetch` compares the full origin. Two rules follow. **Never put the headers back in a
    redirect hook.** axios/follow-redirects `beforeRedirect` and got `hooks.beforeRedirect` both
    run *after* the strip, and a hook that set `Authorization` again sent it to the other origin
    (measured, axios). For a credentialed call, **turn redirects off** (`redirect: 'error'`,
    `maxRedirects: 0`, got `followRedirect: false`) and handle a 3xx yourself. This is the Node
    form of Go's `CheckRedirect` rule (`sota-golang` rules/04 §4b). *OWASP: NPM Security cheat sheet.*
  - OWASP: SSRF Prevention, .NET Security and GraphQL cheat sheets.
- **The browser counterpart: client-side request URLs.** In page code, a URL from the query
  string, fragment, `postMessage` or stored data that reaches `fetch`, `XMLHttpRequest.open`
  or `new EventSource` sends the request, with any `Authorization` header your wrapper adds,
  to whichever host the attacker chose, and the page then trusts the response. Resolving it
  against your origin does not help: `new URL(input, 'https://app.example/')` returned
  `https://evil.example/x` for `https://evil.example/x`, `//evil.example/x` and
  `\\evil.example/x` (measured, Node 22.22). Take an ID or path segment, not a URL. When a
  URL is unavoidable, parse it and compare `.origin` to an exact allowlist before the call.
  The `EventSource` case is `sota-api-design` rules/05 §3. *OWASP: HTML5 Security cheat sheet.*
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

## Audit checklist

- [ ] `grep -rn "exec(\|execSync(" src/` — template/concat input = CRITICAL; migrate to execFile array form.
- [ ] `grep -rn "child_process" src/ | grep "shell"` — `shell: true` (HIGH).
- [ ] **SSRF: a request value becoming an outbound request's URL (§"SSRF and server-side validation")** —
      ``grep -rnE '(fetch|axios(\.[a-z]+)?|got(\.[a-z]+)?|https?\.(get|request)|goto|new URL)\( *(`\$\{ *)?req\.(body|query|params|headers)' --include='*.js' --include='*.ts' --include='*.mjs' --include='*.cjs' .``
      — each hit must go through a connect-time `lookup` guard plus a literal-IP check, with
      `redirect: 'error'`/`'manual'`, or it is HIGH (internal address / metadata endpoint
      reachable). A pre-fetch `dns.lookup` as the only check is HIGH (DNS rebinding). The probe
      sees single-line calls with the request value first; a URL held in a variable needs a read.
- [ ] **Credentials re-added on a redirect (§"SSRF", the credentials sub-bullet) — HIGH** —
      `grep -rnE 'beforeRedirect.*([Aa]uthorization|[Cc]ookie|headers)' --include='*.js' --include='*.ts' --include='*.mjs' --include='*.cjs' .`
      — a redirect hook that touches headers can send the token to the redirect target. A hook
      whose body spans lines needs a read. A credentialed call that follows redirects through
      follow-redirects (subdomains keep the headers) or got (`https:`→`http:` keeps them) is MEDIUM.
- [ ] **Client-side request to a URL taken from the page (§"SSRF", the browser-counterpart bullet) — HIGH when the
      request carries credentials or its response is rendered** —
      ``grep -rnE "(fetch\(|new EventSource\(|\.open\( *['\"][A-Za-z]+['\"] *,)[^;]*(location\.(search|hash|href)|[sS]earchParams\.get\(|params\.get\(|\.data[.)[]|localStorage\.getItem\()" --include='*.js' --include='*.ts' --include='*.mjs' --include='*.tsx' --include='*.jsx' .``
      — each hit needs an origin allowlist check before the call. Single-line calls only; a URL held in a variable needs a read.
