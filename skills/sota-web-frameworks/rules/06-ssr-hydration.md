<!-- last-verified: 2026-07 -->

# 06 — SSR & hydration: mismatches, serialization, caching, CSP

Cross-cutting concerns of server rendering, shared by Next and Nuxt. Framework
specifics are in `rules/03`/`rules/05`; the consolidated security boundary in
`rules/07`.

## 1. Hydration mismatches — cause and correct fix

Hydration is the client attaching event handlers to server-rendered HTML, assuming the
two render trees are identical. When they diverge:

- **React** may recover from some mismatches but gives *no guarantee* attribute
  differences are patched, and if a mismatch forces it, React **discards the server
  HTML and re-renders the whole root on the client** — losing the SSR benefit and
  flashing. Treat every mismatch as a bug.
- **Vue/Nuxt** logs a mismatch warning and patches the DOM toward the client render;
  invalid HTML nesting silently corrupts the tree.

**Common causes** (per react.dev and vuejs.org):

- Non-deterministic values in render: `Date.now()`/`new Date()`, `Math.random()`,
  locale/timezone-dependent formatting, `crypto.randomUUID()`.
- Branching on `typeof window`, `matchMedia`, `localStorage`, `navigator` during
  render (server and client take different branches).
- **Invalid HTML nesting** (`<p><div>`, `<a><a>`, a `<div>` inside `<table>` without
  `<tbody>`): the browser's parser auto-corrects, so the client tree no longer matches
  the server string.
- Browser extensions mutating the DOM before hydration (can't fully control; don't let
  it mask real mismatches).

**Correct fixes:**

- Make render **deterministic**. Move browser-only reads into `useEffect`
  (React) / `onMounted` (Vue) so they run after hydration, or gate with a mounted
  flag / `<ClientOnly>` (Nuxt) / dynamic import with `ssr: false`.
- **Stable IDs:** React `useId` (with `identifierPrefix` on `hydrateRoot` for multiple
  roots) and Vue 3.5 `useId()` — never random IDs across the boundary.
- For genuinely unavoidable divergence (a live timestamp), scope the suppression as
  narrowly as possible: React `suppressHydrationWarning` (one level deep, intended for
  exactly this), Vue 3.5 `data-allow-mismatch`. These silence the warning for *that
  node only* — never blanket them, and never use them to paper over a real bug.
- **Security:** never "resolve" a mismatch by injecting server-side user-controlled
  HTML into the tree. Browser parser normalization of malformed markup is the same
  parser-differential class that drives mutation-XSS — escape/sanitize instead of
  hand-patching the DOM to match. (Sanitizer guidance: `rules/02`/`rules/04`.)

## 2. SSR state serialization — an XSS sink

To avoid double-fetching, SSR frameworks embed fetched state in the HTML as an inline
`<script>`. Done naively this is a script-injection hole.

- **Naked `JSON.stringify` into a `<script>` is XSS.** JSON does not escape `<`, so a
  value containing `</script>` closes the tag early and injects markup; `<!--` and
  `<script` can also break parsing, and `U+2028`/`U+2029` break older JS string
  parsers. The fix is to escape `<`, `>`, `&`, and the line separators to `\uXXXX`
  before embedding (or set the data via `<script type="application/json">` + `textContent`,
  parsed with `JSON.parse`).

```js
// BAD — HIGH: state contains user data → </script> breakout
html += `<script>window.__DATA__=${JSON.stringify(state)}</script>`;
// GOOD — escape the HTML-significant characters first
const safe = JSON.stringify(state).replace(/</g,'\\u003c').replace(/>/g,'\\u003e')
  .replace(/&/g,'\\u0026').replace(/\u2028/g,'\\u2028').replace(/\u2029/g,'\\u2029');
```

- **Prefer the framework serializer** — you rarely hand-roll this:
  - **Nuxt** serializes the payload with **devalue** (handles `Date`/`Map`/`Set`/refs
    and escapes `</script>` + line separators). But devalue's *parse* side has had
    prototype-pollution CVEs (CVE-2025-57820, CVE-2026-30226) and DoS advisories — keep
    it patched (`rules/05`).
  - **Next** embeds the RSC/flight payload via `self.__next_f.push([...])`.
  - **`serialize-javascript`** (used to embed functions/regex): CVE-2020-7660 (RCE,
    fixed 3.1.0) and CVE-2024-11831 (XSS via unescaped URL objects, fixed **6.0.2**) —
    if it's in the tree, verify the version.
- **Only serializable data belongs in the payload**, and *everything* in it is public
  — never let a secret, token, or full DB row reach `useState`/a client prop
  (`rules/07`).

## 3. Cross-request state pollution

On the server the module graph is loaded **once per process** and reused for every
request. Module-level mutable state is therefore shared across all users.

- **The bug:** `let currentUser` / `const cart = reactive([])` / a singleton client
  holding per-request data at module scope. Under load, one user sees another's data,
  and memory grows unbounded. This is a confidentiality breach, not just a leak.
- **React/Next:** don't hold request data in module globals; use request-scoped APIs
  (`cookies()`/`headers()`, React `cache()` for per-request memoization, the DAL).
- **Vue/Nuxt:** create fresh app/router/store instances per request (Nuxt does this
  for you); use `useState`/Pinia, never a module-level `ref` (`rules/05`). Share
  request-scoped values via app-level `provide`/`inject`, not module scope.
- Audit any module-level `let`/mutable singleton in server-reachable code.

## 4. Caching personalized SSR safely

Caching is where SSR bugs become cross-user data leaks.

- **Personalized (auth/cookie-dependent) responses must be `Cache-Control: private`**
  (browser only) or uncached — never `public`/`s-maxage` at a shared CDN.
- **`Vary` is not a reliable isolation mechanism at CDNs.** Cloudflare ignores `Vary`
  values; CloudFront strips `Vary` before returning. If correctness depends on the
  cache keying by a header, verify your CDN actually honors it — prefer explicit
  per-user cache keys or no shared caching.
- **Web cache deception / poisoning** (PortSwigger "Gotta cache 'em all", 2024) exploit
  URL-parsing differences between CDN and origin so a crafted path is cached as a
  static asset while the origin served a private page. Both Next
  (CVE-2024-46982, CVE-2025-49005, CVE-2025-32421) and Nuxt (CVE-2025-27415) have
  shipped cache-poisoning CVEs — keep patched and don't hand a CDN an ambiguous
  cache key. Next's RSC payload uses a `Rsc:`/`_rsc=` scheme that has been a poisoning
  vector; a request missing the buster but carrying the header can poison HTML with an
  RSC payload.
- **ISR/SWR** trade freshness for speed — only for non-personalized content, and think
  through the stale window (`rules/01`, `rules/05`).

## 5. CSP with streaming SSR

A strict, nonce/hash-based CSP is the highest-leverage defense-in-depth for these apps
— but it interacts with rendering.

- **Next (official guide):** generate a per-request nonce in `proxy.ts`, set it on the
  CSP header and an `x-nonce` request header; Next applies it to its own scripts. Use
  `script-src 'self' 'nonce-<n>' 'strict-dynamic'`. **Nonces force dynamic rendering**
  — they're incompatible with static generation, ISR, and PPR (there's no request at
  build time). Opt a page into dynamic with `await connection()`. The static-friendly
  alternative is experimental hash-based CSP via SRI (App Router). Dev needs
  `'unsafe-eval'` (not prod).
- **Nuxt:** the `nuxt-security` module supplies CSP — runtime nonces for SSR (Nitro
  sets the header), build-time SHA hashes for SSG (`<meta>`, no server) — both with
  `'strict-dynamic'` and no `'unsafe-inline'`.
- Without nonces/hashes, framework output typically requires `'unsafe-inline'`, which
  neuters CSP against injected inline scripts. If you're going to have a CSP, wire the
  nonce/hash — a CSP with `'unsafe-inline'` on `script-src` is close to no CSP.
- CSP is defense-in-depth over escaping/sanitization (`rules/02`/`rules/04`), never a
  replacement. General CSP/headers depth: `sota-code-security` rules/05,
  `sota-network-security`.

## Audit checklist

```bash
# Non-determinism in render (hydration bugs)
grep -rnE '(Date\.now|new Date|Math\.random|crypto\.randomUUID)\(' --include='*.tsx' --include='*.vue' src app components pages | grep -v useEffect
grep -rnE 'typeof window|localStorage|matchMedia|navigator\.' --include='*.tsx' --include='*.vue' src app pages

# Blanket mismatch suppression (smell if widespread)
grep -rn 'suppressHydrationWarning\|data-allow-mismatch' --include='*.tsx' --include='*.vue' src app pages

# Hand-rolled state serialization into <script>
grep -rnE 'JSON\.stringify' --include='*.ts' --include='*.tsx' server app | grep -i 'script\|__DATA__\|innerHTML'
grep -E '"serialize-javascript"' package.json   # verify >=6.0.2

# Cross-request state pollution: module-level mutable state in server code
grep -rnE '^(export )?(let|const) \w+\s*=\s*(reactive|ref|new |\[\]|\{\})' --include='*.ts' server lib composables utils 2>/dev/null

# Caching / CSP
grep -rn 'Cache-Control\|s-maxage\|Vary' --include='*.ts' server app middleware.* proxy.*
grep -rn "Content-Security-Policy\|nonce\|strict-dynamic\|nuxt-security" --include='*.ts' app proxy.* middleware.* nuxt.config.*
```

- [ ] Render deterministic — no `Date`/random/`window`/locale branching outside effects/`onMounted`; stable `useId`?
- [ ] Mismatch suppression scoped to individual unavoidable nodes, never blanket, never patched with injected user HTML?
- [ ] SSR state serialized via the framework serializer or `<`-escaped JSON (no naked `JSON.stringify` into `<script>`); `serialize-javascript` ≥ 6.0.2; devalue patched?
- [ ] No secret/token/full row in the serialized payload (`useState`/client props)?
- [ ] No module-level mutable state in server-reachable code (cross-request leak)?
- [ ] Personalized responses `Cache-Control: private`/uncached; not relying on `Vary` at the CDN; framework patched against cache-poisoning CVEs?
- [ ] CSP present and nonce/hash-based (not `'unsafe-inline'` on `script-src`), with the dynamic-rendering trade-off understood?
