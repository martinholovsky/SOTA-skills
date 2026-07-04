<!-- last-verified: 2026-07 -->
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
  :null_session` on non-API controllers. Sinatra/Rack: `Rack::Protection`
  (`use Rack::Protection, :authenticity_token`) — plain Sinatra without it
  has **no CSRF protection**.
- Token-authenticated APIs (Authorization header, no cookies) don't need
  CSRF tokens — but an "API" that also accepts session cookies does; that
  hybrid is the classic gap.
- `SameSite=Lax` (or `Strict`) on session cookies is the second layer, not a
  replacement — older clients and subdomain issues remain.
- GET routes must be side-effect free; CSRF middleware only guards
  non-idempotent verbs.

## 4. Sessions and cookies

- Session cookies: `secure: true`, `httponly: true`, `same_site: :lax`
  minimum. Rack example:
  `use Rack::Session::Cookie, secure: true, httponly: true, same_site: :lax,
  secret: ENV.fetch("SESSION_SECRET")`.
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
- Match `Host`/origin checking to deployment: Rails
  `config.hosts`; elsewhere validate `Host` against an allowlist — DNS
  rebinding and cache-poisoning use wildcard hosts.

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
  `|command` execution (see `rules/02` §2).
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
  `rules/02` §7).
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

## Audit checklist

Run from repo root; verify each hit manually. Rails apps: run `brakeman -q`
first — it covers XSS/mass-assignment/redirect sinks mechanically.

```bash
# Escaping bypasses — CRITICAL if user-influenced
grep -rnE '\.html_safe\b|raw\s*\(|<%==' --include='*.erb' --include='*.rb' app/ lib/ views/ 2>/dev/null
# Sinatra/plain-ERB apps: is auto-escape on? absent = HIGH
grep -rn "escape_html" --include='*.rb' . | head -3

# Mass assignment
grep -rn "permit!" --include='*.rb' .
grep -rnE '(new|create|update|assign_attributes)\s*\(\s*params\b' --include='*.rb' . | grep -v permit
grep -rnE 'permit\([^)]*(:role|:admin|:account_id|:state)' --include='*.rb' .

# CSRF
grep -rn "skip_before_action :verify_authenticity_token" --include='*.rb' .
grep -rn "protect_from_forgery" --include='*.rb' . | head
grep -rn "Rack::Protection" --include='*.rb' config.ru 2>/dev/null | head -1  # Sinatra: absent = HIGH

# Sessions / cookies
grep -rnE "Rack::Session::Cookie" --include='*.rb' config.ru 2>/dev/null | grep -v "secure: true"
grep -rn "reset_session" --include='*.rb' . | head -1   # absent around login = MEDIUM
grep -rn "secret_key_base\|SESSION_SECRET" --include='*.rb' --include='*.yml' . | grep -vE "ENV|credentials"

# Redirects / SSRF
grep -rnE 'redirect(_to)?\s*\(?\s*params' --include='*.rb' .
grep -rn "allow_other_host: true" --include='*.rb' .
grep -rnE '(Net::HTTP|URI\.open|Faraday|HTTParty)[^#]*params' --include='*.rb' .

# Uploads / downloads
grep -rnE 'send_file\s*\(?\s*params|send_file[^,]*#\{' --include='*.rb' .
grep -rn "original_filename" --include='*.rb' . | grep -v basename

# Transport
grep -rn "force_ssl" --include='*.rb' config/ 2>/dev/null | head -1
```

Severity guide: `html_safe`/`raw` on user input, `send_file params` —
CRITICAL. `permit!`, missing CSRF on cookie-auth state changes, unescaped
template layer, open redirect, unguarded SSRF fetch — HIGH. Missing
`reset_session` on login, absent CSP/HSTS, client-trusted content type —
MEDIUM.
