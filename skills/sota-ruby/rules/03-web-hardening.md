# 03 — Web hardening (framework-neutral)

Rules for any Ruby web surface — Rack app, Rails, Sinatra, Hanami, Grape,
Roda all appear only as neutral examples; never assume which one a codebase
uses. Establish the stack first (`Gemfile`, `config.ru`), then map each rule
to that stack's mechanism. References:
[OWASP Ruby on Rails Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Ruby_on_Rails_Cheat_Sheet.html),
[Rails Securing guide](https://guides.rubyonrails.org/security.html),
[Rack::Protection](https://github.com/sinatra/sinatra/tree/main/rack-protection).

## 1. XSS and output escaping

Escaping behavior **differs by framework** — verify, don't assume:

- **Rails ERB auto-escapes** by default. The escape hatches are the audit
  surface: every `raw(...)`, `.html_safe`, `<%== ... %>`, and
  `content_tag`/`tag` with interpolated attributes gets reviewed. `html_safe`
  on anything user-influenced is CRITICAL.
- **Plain ERB / Sinatra do NOT auto-escape by default.** Enable it:
  Sinatra `set :erb, escape_html: true` (Erubi), or escape explicitly with
  `Rack::Utils.escape_html(x)` / `ERB::Util.html_escape(x)` at every
  interpolation. An unescaped-by-default template layer is a standing HIGH.
- Hanami templates escape by default; the `raw` helper is the audit point.
- Rich text/user HTML: sanitize with an allowlist sanitizer
  (`Rails::HTML5::Sanitizer` / `sanitize` helper, or the `sanitize` gem as
  neutral examples) — never regex-strip tags yourself.
- Context matters: HTML-escaping does not make data safe inside
  `<script>`, inline event handlers, CSS, or URLs. JSON into script:
  `json_escape`/`.to_json` with escaping enabled; URLs: validate scheme
  (`http`/`https` allowlist — `javascript:` URLs pass naive checks).
- Ship a Content-Security-Policy (framework DSL or a Rack middleware) —
  defense in depth, not a substitute for escaping.

## 2. Mass assignment

Any endpoint that feeds a params hash into model creation/update must go
through an **attribute allowlist**:

```ruby
# Rails strong parameters (neutral example)
params.require(:user).permit(:name, :email)
params.expect(user: [:name, :email])   # Rails 8.0+, raises 400 on bad shape
```

- `params.expect` (added in
  [Rails 8.0](https://guides.rubyonrails.org/8_0_release_notes.html)) also
  hardens against type-confusion (array-vs-hash) parameter attacks — prefer
  it on 8.0+.
- **`permit!` (permit everything) is HIGH**, as is passing raw
  `params`/parsed JSON into `new`/`update`/`create`/`assign_attributes`.
- Privilege fields (`role`, `admin`, `account_id`, `state`) never come from
  the request — set them server-side from the authenticated context; a
  separate admin flow has its own explicit permit list.
- Non-Rails stacks: same rule, manual mechanism — `payload.slice(:name,
  :email)` (plus type validation via dry-validation/dry-schema or a contract
  object as neutral examples) before it touches the model. Sequel:
  `set_fields(params, [:name, :email])` over mass `set`.

## 3. CSRF

- Every **cookie/session-authenticated, state-changing** endpoint needs CSRF
  protection. Rails: `protect_from_forgery with: :exception` (on by default
  in generated apps) — audit every `skip_before_action
  :verify_authenticity_token` and every `protect_from_forgery with:
  :null_session` on non-API controllers. **Sinatra** enables
  `Rack::Protection` itself (`set :protection, true` is the default, read from
  sinatra 4.2.1), with the Origin check (`HttpOrigin`) and `RemoteToken` on
  and a `:drop_session` reaction: a cookie-bearing cross-Origin POST reaches
  the handler with an empty session (measured). What is **off** by default is
  the token check, `AuthenticityToken`, and a request with no `Origin` header
  passes the Origin check. Turn it on for defence in depth:
  `use Rack::Protection::AuthenticityToken` (or `set :protection, use:
  [:authenticity_token]`; in a plain Rack app, `use Rack::Protection, use:
  [:authenticity_token]`). Through `set :protection` a missing token empties
  the session (Sinatra's reaction); the explicit `use` form answers 403 (both
  measured). The findings are `disable :protection`, `set :protection,
  false`, and an `except:` list naming `:http_origin` or `:remote_token`. Do not write `use Rack::Protection, :authenticity_token`:
  the second argument must be an options hash, and it raises `TypeError` at
  boot (measured, rack-protection 4.2.1). A bare Rack app that never adds
  `Rack::Protection` has no CSRF defence at all.
- Token-authenticated APIs (Authorization header, no cookies) don't need
  CSRF tokens — but an "API" that also accepts session cookies does; that
  hybrid is the classic gap.
- `SameSite=Lax` (or `Strict`) on session cookies is the second layer, not a
  replacement — older clients and subdomain issues remain.
- GET routes must be side-effect free; CSRF middleware only guards
  non-idempotent verbs.
- **HEAD reaches GET actions, and `request.get?` is false inside them.**
  Rails' router matches a HEAD request with no HEAD route against the GET
  routes, then restores the method to `HEAD` (read from
  `journey/router.rb`), and Rack's `get?` compares against `"GET"`. So
  `if request.get? then show else update end` runs the **write** branch on
  a HEAD request, which is not CSRF-checked. Branch on `request.post?` (the
  verb you mean), never on "not GET".
- **Routes that widen the verb or the action set.** `match ... via: :all` or
  `via: [:get, :post]` lets a GET reach a state-changing action; the Rails
  routing guide warns that the GET "won't check for CSRF token". A route with
  dynamic `:controller`/`:action` segments (the old
  `:controller(/:action(/:id))` default) makes every public controller method
  an endpoint, which is still supported on Rails main. Declare routes
  explicitly.

## 4. Sessions and cookies

- Session cookies: `secure: true`, `httponly: true`, `same_site: :lax`
  minimum. Rack example (rack-session 2.x):
  `use Rack::Session::Cookie, secure: true, httponly: true, same_site: :lax,
  secrets: [ENV.fetch("SESSION_SECRET")], serialize_json: true`.
  - **`secrets:`, not `secret:`.** `secrets:` encrypts and authenticates the
    cookie, takes an array so a new key can be prepended for rotation, and
    rejects a key shorter than 64 bytes (`ArgumentError`, measured). The
    singular `secret:` (and `legacy_hmac_secret:`) also turns on the legacy
    path: HMAC-SHA1 verification with a `Marshal` decoder, kept for migrating
    old cookies (read from rack-session 2.1.2 `cookie.rb`).
  - **`serialize_json: true` as well.** Without it the encrypted payload is
    still `Marshal`-serialized (`serialize_json: false` is the encryptor's
    default; measured). Anyone holding the key can then forge a cookie that
    the server passes to `Marshal.load` — a leaked session secret becomes
    remote code execution, not just session forgery (`rules/02` §3). With
    JSON, store only strings, numbers, arrays and hashes in the session.
  - **Sinatra's `enable :sessions` always takes the legacy path**: it passes
    `session_secret` as `secret:` (read from sinatra 4.2.1 `setup_sessions`),
    so HMAC-SHA1 + `Marshal` stays live even with `set :sessions,
    serialize_json: true` (measured). For a new app, `disable :sessions` and
    `use Rack::Session::Cookie, secrets: [...], serialize_json: true` directly;
    the `session` helper works unchanged (measured).
  - A custom `coder:` replaces this machinery; review it as a deserializer.
- **Cookies the app sets itself do not inherit the session cookie's flags.**
  Rails `cookies[:k] = v` (and `.signed`/`.encrypted`/`.permanent`) defaults to
  `path: "/"`, no `HttpOnly`, and `SameSite` from
  `config.action_dispatch.cookies_same_site_protection` (`:lax` from
  `load_defaults 6.1`). It adds `Secure` only when `config.force_ssl` is on,
  because `ActionDispatch::SSL` appends it (read from actionpack 8.1.4).
  Rack's `response.set_cookie` (which Sinatra uses) adds **no** attribute at all:
  `set_cookie("a", "1")` emits `a=1` (measured, rack 3.2.7). Pass a hash:
  `{ value:, httponly: true, secure: true, same_site: :lax, path: "/" }`, and
  leave out `domain:` unless subdomains must read the cookie. Name a
  host-bound cookie `__Host-name`: browsers accept it only with `secure`,
  `path=/` and no `domain`. OWASP: Session Management and Cookie Theft
  Mitigation cheat sheets; ASVS 5.0 V3.3.
- **Rotate the session on privilege change** (`reset_session` at login /
  logout / role elevation) — session fixation otherwise.
- The cookie-signing/encryption secret (`secret_key_base` in Rails; the Rack
  session secret elsewhere) is a production secret: ≥64 random bytes, never
  committed, rotated via the framework's rotation mechanism, distinct per
  environment.
- Don't store authorization-deciding state client-side (even signed) if it
  must be revocable — server-side session or short-lived tokens.
- Cookie size and content: no PII dumps in cookies; they traverse every
  request and end up in logs/CDNs.

## 5. Headers and transport

- Force TLS: HSTS + redirect (Rails `config.force_ssl = true`; elsewhere the
  proxy/middleware). Behind a proxy, trust `X-Forwarded-Proto` only from the
  proxy you control.
- Baseline headers (framework defaults or `Rack::Protection` /
  secure_headers-style middleware as neutral examples):
  `X-Content-Type-Options: nosniff`, `frame-ancestors` via CSP (or
  `X-Frame-Options: DENY`), `Referrer-Policy`, a real
  `Content-Security-Policy`.
- **Outbound TLS is verified.** `verify_mode = OpenSSL::SSL::VERIFY_NONE`
  on `Net::HTTP`, or any HTTP client option that sets it, is a finding. The
  class and its rationale live in `sota-code-security` rules/04; this is
  Ruby's spelling of it. Internal services get a private CA, not disabled
  verification.
- **SSH host keys are verified too, and `net-ssh` does not do it by
  default.** Read from the gem's `select_host_key_verifier`:
  - Leaving `verify_host_key` **unset** selects `:accept_new_or_local_tunnel`,
    which the gem's own docs rank as insecure.
  - `:never` and `false` (the deprecated form, also reached through
    `paranoid: false`) accept any server.
  - Set `verify_host_key: :always` with a pinned `known_hosts`, and treat any
    `Net::SSH.start` (or `net-scp`/`net-sftp` on top of it) that does not set
    it as a finding.

  The class lives in `sota-code-security` rules/04 §5.
- Match `Host`/origin checking to deployment: Rails
  `config.hosts`; elsewhere validate `Host` against an allowlist — DNS
  rebinding and cache-poisoning use wildcard hosts.
- **Debug mode is the default, not an opt-in.** If the environment variables
  are unset, every layer starts in development. `Rails.env` falls back
  through `RAILS_ENV`, then `RACK_ENV`, to `"development"` (railties 8.1.4).
  Sinatra reads `APP_ENV`, then `RACK_ENV`, falls back to `:development`, and
  sets `show_exceptions` to `development?`. `rackup` defaults `RACK_ENV` to
  development and then adds `Rack::ShowExceptions`, the page that prints
  backtraces (rackup 2.3.1). Puma's own `environment` also defaults to
  `"development"` (puma 8.0.2). In a deployed image, set `RAILS_ENV` /
  `RACK_ENV` / `APP_ENV=production` explicitly and fail at boot if it is
  missing: `abort "RACK_ENV unset" if ENV["RACK_ENV"].to_s.empty?`.
  Production keeps `config.consider_all_requests_local = false`, the
  generated value. Put `web-console` in the Gemfile's `:development` group;
  it aborts boot outside development unless `config.web_console.development_only
  = false`, and that override is itself a finding. A `rails server`/`rackup`
  started with the development env is a development server whatever the
  handler. OWASP: Error Handling cheat sheet; Secure Headers Project;
  ASVS 5.0 V13.4.

## 6. Redirects and SSRF

- **Open redirects**: `redirect_to params[:return_to]` is HIGH. Rails 7.0+
  raises on cross-host redirects unless `allow_other_host: true` — audit
  every `allow_other_host: true`. Neutral fix: allowlist paths
  (`redirect_to URI(raw).path`) or map named targets.
- **SSRF**: any server-side fetch of a user-supplied URL
  (`Net::HTTP`, `URI.open`, Faraday/HTTParty as neutral examples) must:
  allowlist schemes (`https`), resolve and reject private/link-local/
  metadata ranges (127.0.0.0/8, 10/8, 172.16/12, 192.168/16, 169.254/16 —
  cloud metadata 169.254.169.254), cap redirects and re-validate each hop,
  and set open/read timeouts. `URI.open` on user input additionally risks
  `|command` execution on Ruby ≤ 3.4 and an arbitrary local-file read on
  every version (see `rules/02` §2). The policy is `sota-code-security`
  rules/01 §5; the Ruby spelling of each step:
  - **Build the URL, don't relay it.** Where the feature allows, accept a
    key or record ID and look the base URL up in a server-side allowlist.
  - **Scheme first**: `uri = URI(raw)` then require `uri.is_a?(URI::HTTPS)`.
    Never hand caller input to `URI.open` — a string without `scheme://`
    falls through to `Kernel#open`, and its redirects may go http→ftp.
  - **Vet the address that is dialled, not an earlier lookup.** `Net::HTTP`
    resolves the name again inside `connect`, so `Resolv.getaddresses` then
    `Net::HTTP.get(uri)` leaves a DNS-rebinding window. Resolve once
    (`Addrinfo.getaddrinfo(host, port, nil, :STREAM)`), vet **every**
    result, then pin one:
    `Net::HTTP.start(host, port, nil, ipaddr: vetted, use_ssl: true)` (or
    `http.ipaddr = vetted` before `start`). The socket goes to `vetted`
    while SNI and certificate hostname checks still use `host`. The third
    argument must be `nil`: its default `:ENV` honours `http_proxy`, and
    then the proxy picks the address, not your pin. The `ssrf_filter` gem
    is a neutral example built on this same `ipaddr:` pin.
  - **What to reject** — `ip = IPAddr.new(addr).native` first (unwraps
    `::ffff:a.b.c.d`; measured on IPAddr 1.2.8, `link_local?` is false for
    the mapped form of 169.254.169.254 until `.native`), then `loopback?`,
    `private?` (RFC 1918 and fc00::/7), `link_local?` (169.254/16, fe80::/10),
    and by `IPAddr#include?` the ranges with no predicate: `0.0.0.0/8`, `::`,
    `100.64.0.0/10`, `224.0.0.0/4`, `ff00::/8`. Refuse metadata hostnames by
    name as well (GCP: `metadata.google.internal`).
  - **Strict parsing**: `IPAddr.new` rejects `0x7f.0.0.1`, `2130706433`,
    `127.1` and `0177.0.0.1`, but the OS resolver behind `Addrinfo` and
    `TCPSocket.open` accepts shorthand forms (measured on macOS: the first
    three all reach 127.0.0.1). Check the resolver's output, never the
    input string.
  - **Redirects**: `Net::HTTP` never follows them — your loop re-runs every
    check per hop and caps the count. `URI.open` follows unless
    `redirect: false`. HTTParty follows by default (`follow_redirects:
    false` turns it off). Faraday core does not, but the
    `faraday-follow_redirects` middleware does (`limit:` default 3); its
    `callback:` can raise to re-validate the next URL, a name check only —
    the connect-time pin still needs `Net::HTTP` with `ipaddr:`.
  - `Net::HTTP` `open_timeout`/`read_timeout` default to 60 s — set them
    lower, and cap the body you read.

  OWASP: SSRF Prevention, .NET Security and GraphQL cheat sheets.
- Webhook/callback URL registration is SSRF-by-design — same checks plus
  egress via a dedicated proxy where available.

## 7. File uploads and downloads

- Validate **server-side**: size cap, extension allowlist, and content
  sniffing (e.g. Marcel as a neutral example) — never trust the client
  `Content-Type` or filename (`File.basename` it, then generate your own
  name).
- Store outside the served docroot (or object storage); serve with an
  explicit `Content-Type` and `Content-Disposition: attachment` for
  user-supplied files; never `send_file params[:path]` (traversal — see
  `rules/02` §7). **`render file:` is the same sink**: Rails serves any
  existing path given to it raw (`Template::RawFile`), so
  `render file: params[:page]` discloses arbitrary files. Map a user choice
  to a fixed template name instead.
- Image processing on untrusted files is an RCE-history hotspot
  (ImageTragick class) — keep processors current, restrict formats, consider
  sandboxing the worker (see `sota-sandboxing`).

## 8. Auth-adjacent essentials

Deep authn/authz design lives in `sota-code-security`; the Ruby-shaped
minimums:

- Passwords via bcrypt/argon2 (`has_secure_password` as a neutral example);
  no home-rolled digests. Constant-time comparison for tokens (`rules/02` §6).
- Rate-limit login/signup/reset (Rack::Attack middleware or Rails 7.2+
  `rate_limit` as neutral examples).
- Authorization checked **per record**, not per route: loading
  `Model.find(params[:id])` without scoping to the authenticated
  tenant/owner (`current_user.things.find(...)`) is the standard IDOR.
- Don't leak stack traces or framework error pages in production; error
  handlers return generic bodies and log the detail server-side.
- **Secrets stay out of logs, including through `inspect`.** `Data` and `Struct` print every
  member: measured on Ruby 4.0, `Data.define(:user, :password)` inspects as
  `#<data Creds user="bob", password="hunter2">`, and interpolating one into a `Logger` line
  writes it out. Override `inspect` on a value object that carries a credential. In Rails (a
  neutral example), `config.filter_parameters` filters *"the parameters that you don't want
  shown in the logs"* and also masks those columns in Active Record `#inspect` (Rails
  configuring guide). The generated `config/initializers/filter_parameter_logging.rb` starts
  it with `:passw, :email, :secret, :token, :_key, :crypt, :salt, :certificate, :otp, :ssn,
  :cvv, :cvc`, matched partially. Redaction at the logger is `sota-observability` rules/01 §4.

## Audit checklist

Run from repo root; verify each hit manually. Rails apps: run `brakeman -q`
first — it covers XSS/mass-assignment/redirect sinks mechanically.

- [ ] **Escaping bypasses — CRITICAL if user-influenced** —
      `grep -rnE '\.html_safe\b|raw\s*\(|<%==' --include='*.erb' --include='*.rb' app/ lib/ views/ 2>/dev/null`
- [ ] **Sinatra/plain-ERB apps: is auto-escape on? absent = HIGH** —
      `grep -rn "escape_html" --include='*.rb' . | head -3`
- [ ] **Mass assignment** — `grep -rn "permit!" --include='*.rb' .` ;
      `grep -rnE '(new|create|update|assign_attributes)\s*\(\s*params\b' --include='*.rb' . | grep -v permit`
      ; `grep -rnE 'permit\([^)]*(:role|:admin|:account_id|:state)' --include='*.rb' .`
- [ ] **CSRF** — `grep -rn "skip_before_action :verify_authenticity_token" --include='*.rb' .` ;
      `grep -rn "protect_from_forgery" --include='*.rb' . | head` ;
      Sinatra/Rack protection switched off (§3) — HIGH on a cookie-session app:
      `grep -rnE 'disable[[:space:]]+:protection|set[[:space:]]+:protection,[[:space:]]*false|except:[^#]*:(http_origin|remote_token)' --include='*.rb' --include='config.ru' .` ;
      token check wired? (absent in a Sinatra app = LOW/MEDIUM, defence in depth; absent in a
      bare Rack app that also lacks `Rack::Protection` = HIGH) —
      `grep -rnE 'AuthenticityToken|:authenticity_token' --include='*.rb' --include='config.ru' .` ;
      the boot-time `TypeError` form — `grep -rnE 'use[[:space:]]+Rack::Protection,[[:space:]]*:' --include='*.rb' --include='config.ru' .`
- [ ] **Verb confusion and widened routes — HIGH on a state-changing action** —
      `grep -rnE 'if\s+request\.get\?|unless\s+request\.get\?|request\.get\?\s*\?' --include='*.rb' app/ lib/ 2>/dev/null`
      (the else branch runs on HEAD, unchecked by CSRF) ;
      `grep -rnE 'via:\s*(:all|\[[^]]*:get[^]]*:(post|put|patch|delete))|:controller\(|/:action' config/routes.rb config/routes/ 2>/dev/null`
- [ ] **Sessions / cookies** —
      `grep -rnE 'Rack::Session::Cookie' --include='*.rb' --include='config.ru' . | grep -v 'secure: true'`
      (options split across lines are a false hit — read the call) ;
      legacy or Marshal-backed session cookie (§4) — HIGH, CRITICAL if the secret may have leaked —
      `grep -rnE '(^|[^_[:alnum:]])(secret|legacy_hmac_secret|coder):[[:space:]]|enable[[:space:]]+:sessions' --include='*.rb' --include='config.ru' .`
      (`secret:` on an unrelated client is a false hit; then confirm each `Rack::Session::Cookie`
      call sets `serialize_json: true`) ;
      `grep -rn "reset_session" --include='*.rb' . | head -1` (absent around login = MEDIUM);
      `grep -rn "secret_key_base\|SESSION_SECRET" --include='*.rb' --include='*.yml' . | grep -vE "ENV|credentials"`
- [ ] **App-set cookie without HttpOnly (§4) — MEDIUM; HIGH when it carries a token or
      identity** — `grep -rnE 'cookies(\.[a-z]+)*\[[^]]+\]\s*=[^=~]|set_cookie\(' --include='*.rb' . | grep -v 'httponly'`
      (a hash split across lines is a false hit; then confirm `secure:`/`same_site:` are
      set, or `force_ssl` is on)
- [ ] **Redirects / SSRF** — `grep -rnE 'redirect(_to)?\s*\(?\s*params' --include='*.rb' .` ;
      `grep -rn "allow_other_host: true" --include='*.rb' .` ;
      `grep -rnE '(Net::HTTP|URI\.open|Faraday|HTTParty)[^#]*params' --include='*.rb' .`
- [ ] **SSRF: outbound request not pinned to a vetted address (§6) — HIGH when the
      destination is caller-influenced** —
      `grep -rnE 'URI\.open|Net::HTTP\.(get|get_response|post|post_form|start|new)|HTTParty\.|Faraday\.(new|get|post)|RestClient\.' --include='*.rb' . | grep -v 'ipaddr'`
      (every hit connects to whatever the name resolves to at connect time — a
      check done earlier is a DNS-rebinding window; confirm the destination is
      fixed, or that the call pins with `ipaddr:` and a `nil` proxy argument)
- [ ] **Uploads / downloads** —
      `grep -rnE 'send_file\s*\(?\s*params|send_file[^,]*#\{' --include='*.rb' .` ;
      `grep -rn "original_filename" --include='*.rb' . | grep -v basename` ;
      `grep -rnE 'render\s*\(?\s*file:' --include='*.rb' .` (user-influenced path = file
      disclosure)
- [ ] **Secrets reaching logs (§8) — HIGH** —
      `grep -rniE 'logger\.(debug|info|warn|error|fatal|unknown).*#\{[^}]*(passw|secret|token|api_?key|credential)' --include='*.rb' .`
      (a credential interpolated into a log line) ;
      `grep -rniE '(Data\.define|Struct\.new)\([^)]*:[a-z_]*(passw|secret|token|api_?key)' --include='*.rb' .`
      (a value object whose `inspect` prints the credential unless overridden) ;
      Rails apps: `grep -rn 'filter_parameters' config/` — exit 1 means no parameter is
      filtered from the logs (HIGH); exit 2 means there is no `config/` to read. A list
      narrower than the generated default needs a reason
- [ ] **Debug mode / development server settings reaching production (§5) — HIGH** —
      `grep -rnE 'consider_all_requests_local\s*=\s*true|development_only\s*=\s*false|:show_exceptions,\s*true|(RAILS|RACK|APP)_ENV[=: ]+"?development' --include='*.rb' --include='*.ru' --include='*.yml' --include='Dockerfile*' --include='Procfile*' . | grep -vE 'environments/(development|test)\.rb'`
      (and confirm the deploy manifest sets the env at all — unset means development)
- [ ] **Transport** — `grep -rn "force_ssl" --include='*.rb' config/ 2>/dev/null | head -1` ;
      `grep -rn "VERIFY_NONE" --include='*.rb' .` (outbound TLS verification disabled — HIGH) ;
      `grep -rnE 'verify_host_key:\s*(:never|:accept_new|false|true)|paranoid:\s*(false|true)' --include='*.rb' .`
      (SSH host key not verified — HIGH) ;
      `grep -rnE 'Net::(SSH|SCP|SFTP)\.start' --include='*.rb' . | grep -v 'verify_host_key'`
      (the default is not `:always` — confirm the options hash sets it)

Severity guide: `html_safe`/`raw` on user input, `send_file params` —
CRITICAL. `permit!`, missing CSRF on cookie-auth state changes, unescaped
template layer, open redirect, unguarded SSRF fetch — HIGH. Missing
`reset_session` on login, absent CSP/HSTS, client-trusted content type —
MEDIUM.