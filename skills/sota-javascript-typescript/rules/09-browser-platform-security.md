# 09 — Browser Platform Security (service workers, DOM clobbering, extensions)

rules/05 covers the XSS sinks and CSP that every page needs. This file covers three browser
features that give script more reach than a page normally has, or that let markup act like
script: a service worker (it keeps running between visits), named elements (markup that
overwrites globals) and browser extensions (script with privileges inside someone else's page).
Added 2026-09-25.

## Service workers: origin, scope and a kill switch

A service worker sits between the page and the network for every URL in its scope, and it
survives reloads and deploys. One attacker-controlled worker is therefore persistent XSS for the
whole scope until the browser drops it.

- **Only a same-origin script, from a trustworthy origin.** `navigator.serviceWorker.register()`
  is available only in secure contexts. It throws `SecurityError` when the script URL or the
  scope is not same-origin with the registering page (MDN, `register()`). Keep the script URL a
  string literal. A URL built from query data, a CDN host or a user setting is a finding even
  where the browser would reject it, because it shows the author expected it to vary.
- **Narrow the scope.** The default scope is the directory the script lives in. Pass
  `{ scope: '/app/' }` for the part of the site that needs offline support. A scope wider than
  the script's own directory works only when the script is served with a `Service-Worker-Allowed`
  header. Setting that header to `/` hands the worker every path on the origin, including
  `/admin` and any user-uploaded content served there. Set it only where you mean it.
- **Keep the script URL stable. Do not hash it.** This corrects a common suggestion, a
  content-hashed filename like the rest of the bundle. web.dev's service worker lifecycle
  article says not to give each version a unique URL ("Don't do this!"): the old worker keeps
  serving the old HTML, which references the old URL, so the new worker never installs. The
  browser detects a new version by a byte-by-byte comparison of the script at the same URL. Per
  that article, Chrome 68 and later ignore HTTP cache headers for that update check, but still
  honour them for files the worker loads through `importScripts()`. Hash those files instead.
- **Ship a tested kill switch before you need it.** A no-op release at the **same** script URL
  that calls `self.registration.unregister()` in its `activate` handler (and does not intercept
  `fetch`) is the recovery path for a broken or compromised worker. The browser installs it on its
  next update check. Also document a `Clear-Site-Data: "storage"` response. MDN lists
  "Service worker registrations" among what `"storage"` clears (it runs `unregister()` on each).
  Rehearse both in staging, because a worker that caches its own shell can keep a bad deploy
  alive.
- **AppCache is gone.** The `manifest` attribute and `window.applicationCache` were removed
  (web.dev's "AppCache removal" dates Chrome's from version 85, complete by October 2021; Firefox
  removed it first, and Safari deprecated it in 2018). `applicationCache` was absent from
  Chrome 151 (measured). Offline support means a service worker plus the Cache API. A leftover
  `manifest=` attribute or `.appcache` file is dead code (LOW).
- *OWASP: HTML5 Security cheat sheet.*

## DOM clobbering: markup that overwrites globals

The browser exposes named elements as properties. An element with `id="x"` becomes `window.x`,
and `<img name=...>` or `<form name=...>` becomes a property of `document`. That holds even when
`document` already has a built-in of that name. So injected HTML that carries **no script at
all** can still change what your code reads. Measured in Chrome 151 after inserting
`<a id="appConfig" href="https://evil.example/x.js">` and `<img name="getElementById">`:
`window.appConfig` was the attacker's element, and `String()` of it was the attacker's URL.
`document.getElementById` was no longer a function. A `document.cookie` read was not replaced.

- **Never read configuration from a global with a fallback.**
  `const cfg = window.appConfig || { src: '/default.js' }` loads the attacker's script once a
  sanitizer lets through an element with that id. Import configuration as a module, or read it
  once from a `<script type="application/json">` you render yourself and then `JSON.parse` it.
  Where you must read a `window`/`document` property in a sensitive path, check its type first
  (`typeof x === 'function'`, `x instanceof HTMLScriptElement`, or a schema parse) and fail
  closed.
- **DOMPurify: know what `SANITIZE_DOM` does not cover.** `SANITIZE_DOM` is on by default. It
  drops an `id`/`name` only when the value collides with an existing `document` or form
  property. Measured on DOMPurify 3.4.16: the default config **kept**
  `<a id="appConfig" …>` (your own global is not a built-in) and removed `name="cookie"`.
  Set `SANITIZE_NAMED_PROPS: true` for any HTML that goes into your page. It rewrites every
  `id` and `name` to `user-content-<value>` (measured). Never set `SANITIZE_DOM: false`.
- **The HTML Sanitizer API (`setHTML`): the old key names do nothing.** In Chrome 151 the
  default `setHTML()` removed `id` and `name` (measured). A config that lists `id`/`name` in
  `attributes` puts them back. `removeAttributes: ['id', 'name']` works. `blockAttributes`, a
  key from an older draft, was **silently ignored**: the `id` was kept (measured). A typo or a
  stale config key is not an error. Test your config's output, and do not assume that a key
  you passed took effect. `setHTMLUnsafe` keeps everything.
- *OWASP: DOM Clobbering Prevention cheat sheet; ASVS 5.0 V3.2.3.*

## Browser extensions

An extension's code runs with privileges the page does not have (cross-origin requests, tabs,
storage, sometimes cookies) while its content scripts read DOM the page controls. Treat every
edge between the two as a trust boundary.

- **No remotely hosted code.** Chrome's Manifest V3 docs define it as anything executed "loaded
  from someplace other than the extension's own files", JavaScript and WASM included, and require
  all code to be bundled. Do not `fetch()` a script and `eval` it, `import()` an `https:` URL,
  or add `<script src="https://…">` to an extension page. Updates go through the store, where
  they are reviewed and signed. Chrome names three narrow exceptions (the User Scripts API,
  `chrome.debugger`, sandboxed iframes). Treat each one as a finding to justify.
- **Keep secrets and sensitive UI out of the host page.** Anything a content script renders
  into the page lives in the page's DOM and event path. A closed shadow root hides the node from
  `element.shadowRoot`, but it is not a security boundary. Measured in Chrome 151: a page-level
  `keydown` listener on `document` received every key typed into an `<input>` inside a
  **closed** shadow root. The event target was retargeted to the host element, but the key was
  intact. Put login, token and settings UI in the extension's own popup, options or side-panel
  page, which the web page cannot reach.
- **Privileged logic stays in the isolated world.** Content scripts default to `ISOLATED`, whose
  variables the page cannot see. `world: "MAIN"` (manifest or `scripting.executeScript`) runs the
  script as page code: the page can redefine the built-ins it calls, and Chrome's docs note that
  the page's CSP then applies. Use `MAIN` only for code that must touch page globals, and give it
  nothing the page should not have.
- **Check the sender in every message handler.** Chrome's messaging docs say content scripts are
  "less trustworthy than the extension service worker", because a malicious page may compromise
  the renderer that runs them. In `runtime.onMessage`/`onConnect`:
  - check `sender.id === chrome.runtime.id`;
  - check `sender.origin` (Chrome 80+) or `sender.url` against the sites the feature is for;
  - parse the payload with a schema;
  - map it to a fixed set of actions. Never map it to a URL to fetch, a tab to script, or code
    to run.
  `onMessageExternal` and `externally_connectable` accept other extensions and web pages, so
  allowlist their ids and origins. Build DOM from message data with `textContent`, never
  `innerHTML` (the same docs warn against `eval` and `innerHTML` on message data).
- *OWASP: Browser Extension Vulnerabilities cheat sheet.*

## Audit checklist

- [ ] **Service worker script or scope wider than intended (§"Service workers") — HIGH for a
      non-literal or cross-origin URL, MEDIUM for a root `Service-Worker-Allowed`** —
      ``grep -rnE "serviceWorker\.register\( *([^'\"\` ]|['\"\`](https?:|//|[^'\"\`]*\\$\{))|Service-Worker-Allowed['\"]? *[,:=] *['\"]/['\"]" --include='*.js' --include='*.ts' --include='*.mjs' --include='*.cjs' --include='*.tsx' --include='*.conf' .``
      — a script URL taken from a variable, an absolute or templated URL, or the header set to `/`.
      A scope wider than the feature needs is MEDIUM.
- [ ] **No kill switch for a service worker (§"Service workers") — MEDIUM** —
      `grep -rlE 'serviceWorker\.register\(' --include='*.js' --include='*.ts' --include='*.tsx' . ; grep -rnE 'registration\.unregister\(|Clear-Site-Data' --include='*.js' --include='*.ts' --include='*.conf' .`
      — the first command lists apps with a worker, the second the recovery paths. A worker with no
      tested `unregister()` release or `Clear-Site-Data: "storage"` route is MEDIUM.
- [ ] **DOM clobbering exposure (§"DOM clobbering") — HIGH when the global selects a script URL
      or an auth decision** —
      `grep -rnE '(window|document|globalThis|self)\.[[:alnum:]_$]+ *(\|\||\?\?)|SANITIZE_DOM: *false|blockAttributes|dropAttributes' --include='*.js' --include='*.ts' --include='*.mjs' --include='*.tsx' .`
      — a global read with a fallback, DOMPurify's clobbering check turned off, or a Sanitizer
      config key that is silently ignored. Then read each `DOMPurify.sanitize(` whose output goes
      into the page: it needs `SANITIZE_NAMED_PROPS: true` (absent = MEDIUM).
- [ ] **Extension: remote code, main-world scripts and message handlers (§"Browser extensions")
      — CRITICAL for remote code, HIGH for a handler that acts without a sender check** —
      `grep -rnE "\"world\": *\"MAIN\"|world: *['\"]MAIN|import\( *['\"\`]https?:|<script[^>]*src=['\"]https?:|onMessage(External)?\.addListener|onConnect(External)?\.addListener|externally_connectable" --include='*.js' --include='*.ts' --include='*.json' --include='*.html' .`
      — each listener hit must check `sender.id` and `sender.origin`/`sender.url` before any
      privileged call. Each `MAIN` hit needs a reason, and remote script loading is CRITICAL.
      Secret-bearing UI injected into the page (read the content scripts) is HIGH.
