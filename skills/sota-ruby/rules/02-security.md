# 02 — Security: injection, deserialization, ReDoS, secrets

Ruby-specific rules for input crossing a trust boundary. Primary references:
[OWASP Ruby on Rails Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Ruby_on_Rails_Cheat_Sheet.html)
and the framework security guides (e.g.
[Rails Securing guide](https://guides.rubyonrails.org/security.html)) — the
patterns below apply to any Ruby codebase, framework or not. Web-surface
issues (XSS, CSRF, mass assignment) live in `rules/03`; generic secure-coding
depth in `sota-code-security`.

## 1. SQL injection — parameterize everywhere

String interpolation into SQL is CRITICAL regardless of where the value
"comes from" — trust levels change over refactors.

**ActiveRecord** (neutral example):

```ruby
# BAD — injectable
User.where("name = '#{params[:name]}'")
User.order(params[:sort])                       # column-name injection
User.pluck(Arel.sql(params[:col]))              # attacker-chosen SQL

# GOOD
User.where(name: params[:name])                  # hash conditions
User.where("email = ?", params[:email])          # positional placeholder
User.where("created_at > :since", since: since)  # named placeholder
User.order(Arel.sql(SORTS.fetch(params[:sort]))) # allowlist -> literal
```

- `order`, `group`, `select`, `pluck`, `joins`, `having` with raw strings are
  injection sinks too — anything user-influenced goes through an **allowlist
  lookup**, never straight in. Rails raises on unrecognized raw SQL in some
  of these unless wrapped in `Arel.sql` — treat every `Arel.sql` as an audit
  point.
- `LIKE` patterns: escape with `sanitize_sql_like(term)` before binding,
  or `%` / `_` become wildcards (data disclosure, DoS-y scans).

**Sequel** (neutral example): use placeholders (`where("name = ?", n)`) or
virtual rows (`where { created_at > since }`); every `Sequel.lit`
with interpolation is the same CRITICAL as raw string SQL.

Raw drivers (`pg`, `mysql2`, `sqlite3`): use `exec_params`/prepared
statements; never `exec("... #{v}")`.

## 2. Command injection — argv form, never shell strings

The shell-string forms of `system`, backticks/`%x`, `exec`, `spawn`,
`IO.popen`, and `Open3.*` all pass through `/bin/sh` when given a single
string with metacharacters.

```ruby
# BAD — all CRITICAL with external input
system("convert #{upload_path} out.png")
`git clone #{repo_url}`
IO.popen("grep #{pattern} log.txt")

# GOOD — argv form, no shell involved
system("convert", upload_path, "out.png")
out, status = Open3.capture2("git", "clone", "--", repo_url)
IO.popen(["grep", "--", pattern, "log.txt"])
```

- Prefer `Open3.capture2/capture3` (argv form) when you need output + status;
  backticks give no status separation and invite interpolation.
- `--` before positional user args stops option injection (`-oProxyCommand=`
  class attacks).
- `Shellwords.escape` is a last resort for legacy shell-string call sites —
  argv form is strictly safer.
- **`Kernel#open` / `URI.open` (open-uri) execute a subprocess when the
  argument starts with `|`** — never call them with an external filename;
  use `File.open` for files and `Net::HTTP`/an HTTP client for URLs.

## 3. Insecure deserialization

- **`Marshal.load` on external data is CRITICAL** — arbitrary object
  instantiation leading to RCE gadgets. That includes data from cookies,
  caches (e.g. a shared Redis/Memcached a less-trusted system can write to),
  message queues, and files users can influence. Use JSON or MessagePack for
  interchange. Rails note: cache/cookie serializers default to safer JSON
  formats in recent versions — flag any explicit `serializer: :marshal`
  fed by semi-trusted writers.
- **YAML/Psych**: since Psych 4 (bundled from Ruby 3.1),
  [`YAML.load` has `safe_load` semantics](https://docs.ruby-lang.org/en/master/Psych.html)
  — only basic types, **aliases disabled** by default. Rules:
  - `YAML.unsafe_load` / `YAML.load_stream(..., unsafe: ...)` on external
    data is CRITICAL (same gadget class as Marshal).
  - Extra classes go through `permitted_classes: [Date, Symbol, ...]`, never
    a switch to `unsafe_load`.
  - Alias-using config files: `YAML.safe_load(s, aliases: true)` — note
    aliases enable billion-laughs-style expansion, so only for trusted files.
  - Code still on Ruby ≤3.0/Psych 3 (EOL anyway): `YAML.load` there is
    unsafe-by-default — treat every call as `unsafe_load`.
- **JSON**: `JSON.parse` is safe; `JSON.load` / `create_additions: true`
  enables object revival via `json_class` — don't use it on external input.
- **CSV**: `CSV` with `converters: :all` can build unexpected types; also
  remember spreadsheet formula injection (`=cmd|...`) when *emitting* CSV
  from user data — prefix `'` on `=`, `+`, `-`, `@` cells.

## 4. eval, send, and reflection sinks

- `eval`, `instance_eval`/`class_eval` **with string arguments**, and
  `Binding#eval` on anything user-influenced is CRITICAL. Block forms
  (`instance_eval { ... }`) don't interpolate input and are fine.
- `send`/`public_send` with a user-controlled method name lets callers reach
  any method (`send(params[:action])` → `send(:destroy_all)`). Allowlist:
  `ACTIONS.fetch(params[:action])`, and prefer `public_send` always.
- `constantize`/`safe_constantize` (or `Object.const_get`) on user input is
  unsafe reflection — instantiating an attacker-chosen class is a gadget
  entry point. Allowlist class names explicitly.
- The same reach comes through **method objects**, not just `send`:
  `method(params[:m]).call`, `instance_method(name).bind_call(obj)`, and
  `items.map(&params[:attr].to_sym)` all let the caller name the method. The
  fix is the same allowlist, applied before the name becomes a symbol.
- ERB/template injection: `ERB.new(user_supplied_template).result(binding)`
  is code execution by design. User-editable templates need a sandboxed
  engine (e.g. Liquid as a neutral example), never ERB/Haml/Slim. Rails'
  `render inline: str` is the same sink: the renderer compiles `str` as a
  template with a handler (`Template::Inline`), so user input there is RCE.
  `render file:` is the file-read twin, in `rules/03` §7.

## 5. ReDoS and regex correctness

- **Anchor validations with `\A` and `\z` — never `^`/`$`.** In Ruby, `^`/`$`
  match *line* boundaries, so `/^https?:\/\/\S+$/` accepts
  `"javascript:x\nhttp://ok"` — a validation bypass, HIGH. (`\Z` allows a
  trailing newline; almost always you want `\z`.)
- ReDoS: nested quantifiers / overlapping alternations
  (`/(a+)+$/`, `/(\w+\s?)*$/`) explode on crafted input. Since Ruby 3.2 most
  patterns are memoized to linear time, and two guards exist
  ([3.2 release](https://www.ruby-lang.org/en/news/2022/12/25/ruby-3-2-0-released/)):
  - Set a **global budget**: `Regexp.timeout = 1.0` (seconds) at boot;
    per-regex override `Regexp.new(src, timeout: 0.1)`.
  - Check hot, input-facing patterns with `Regexp.linear_time?(re)`.
- Don't build regexes by interpolating user input; if unavoidable,
  `Regexp.escape(input)` first.
- **Escaping, precisely.** `#{}` inside `/.../`, `%r{...}` or
  `Regexp.new("...#{x}")` splices `x` in as *pattern syntax*: a search
  term `a.c` matches `abc`, and `.*` or `(a+)+` turns a lookup into a
  wildcard or a ReDoS. Wrap every untrusted piece: `/\A#{Regexp.escape(x)}\z/`.
  For an allowlist of literal strings, `Regexp.union(list)` escapes each
  String element itself (Regexp elements are embedded as-is).
- **Bounds.** Cap the input length *before* matching (`s.bytesize <= 256`
  or a model-level length validation), and give quantifiers an upper limit
  inside the pattern (`\A[a-z0-9_]{3,32}\z`, not `+`). The cap bounds the
  worst case even for a pattern that is not linear-time.
- **Engine choice.** Ruby's engine (Onigmo) backtracks; the 3.2+ memoization
  makes most patterns linear but not all — a **backreference** (`\1`,
  `\k<name>`) makes `Regexp.linear_time?` return `false`, so that pattern has
  no linear guarantee and relies on `Regexp.timeout`. `Regexp.timeout` is
  `nil` (unlimited) until you set it; on expiry the match raises
  `Regexp::TimeoutError` (a `RegexpError`) — rescue it as *reject*, never as
  *accept*. Atomic groups `(?>...)` and possessive quantifiers (`a++`) cut
  backtracking inside a pattern. Where untrusted users supply the *pattern*
  itself, use a linear-time RE2-class engine (e.g. the `re2` gem:
  `RE2::Regexp#full_match?`, `RE2.escape`); it has no backreferences or
  lookaround, which is the price of the guarantee. `linear_time?` is a
  property of the interpreter binary, not the pattern — re-check after a
  Ruby upgrade.
  (OWASP: Input Validation cheat sheet; OWASP Proactive Controls 2024 C3;
  ASVS 5.0 V1.2.9; OWASP Go-SCP, validation and regular expressions.)

## 6. Secrets, randomness, comparison

- **`SecureRandom`** (`hex`, `uuid`, `urlsafe_base64`, `alphanumeric`) for
  tokens, nonces, password-reset codes, API keys. `rand`, `Random`,
  `Array#sample`, `shuffle` are predictable (Mersenne Twister) — HIGH when
  used for anything security-relevant.
- Compare secrets in constant time:
  `OpenSSL.fixed_length_secure_compare(a, b)` (or Rack/ActiveSupport
  `secure_compare` as neutral examples). `==` on HMACs/tokens is a timing
  oracle.
- Passwords: bcrypt/argon2 via a maintained gem (`has_secure_password` uses
  bcrypt as a neutral example) — never `Digest::SHA256` of a password.
- No secrets in code or `ENV`-committed files; load via the deployment
  platform or an encrypted store (see `sota-secrets-management`). Grep
  targets: `_key = "`, `password = "`, `Aws.config`.

## 7. Files and paths

- Path traversal: anything joining user input into a path needs
  canonicalize-then-check:

```ruby
base = File.expand_path("uploads")
path = File.expand_path(name, base)
raise SecurityError unless path.start_with?(base + File::SEPARATOR)
```

- `File.basename(user_name)` before storing uploads; never trust
  client-supplied filenames or content types (see `rules/03` §uploads).
- Archive extraction (zip/tar gems): validate each entry name against the
  same expand-and-prefix check — zip-slip.
- Temp files: `Tempfile`/`Dir.mktmpdir`, not hand-built `/tmp/#{name}`.
- **`Pathname#+` and `Pathname#join` discard the base when the argument is
  absolute.** Measured on Ruby 3.4.10:
  `Pathname.new("/srv/uploads") + "/etc/passwd"` is `/etc/passwd`, whereas
  `File.join("/srv/uploads", "/etc/passwd")` is `/srv/uploads/etc/passwd`.
  Code that treats `base + name` as "inside base" is a traversal. The
  expand-then-prefix check above catches both.


## 8. Fiddle, the `ffi` gem and C extensions

Ruby is memory-safe until it calls C. Fiddle (a libffi wrapper), the `ffi` gem
(`extend FFI::Library`, `attach_function`) and C extensions all reach raw memory: a pointer
read past its length, or a struct layout declared wrong, crashes the process or leaks memory
with no C file in the repository to review. Confine foreign calls to one module, declare
every signature precisely, and validate lengths before they cross. Native gems count as well:
a C extension a gem ships is C you are running. The class is `sota-code-security` rules/06 §3.

## Audit checklist

Run from repo root; verify each hit manually. `brakeman -q` (Rails) and
`bundle exec rubocop --only Security` cover several of these mechanically.

- [ ] **Fiddle / `ffi` / C extensions — HIGH where a length or pointer comes from input** (§8) —
      `grep -rnE "require[[:space:]]+['\"](fiddle|ffi)['\"]|Fiddle::|extend[[:space:]]+FFI::Library|attach_function" --include='*.rb' .`
      ; `grep -rnE 'ext/.*extconf\.rb|extensions' --include='*.gemspec' .`
- [ ] **SQL injection — CRITICAL on any hit with non-literal interpolation** —
      `grep -rnE '\.(where|order|group|having|select|joins|pluck|find_by_sql|update_all)\s*\(\s*["'"'"'][^)]*#\{' --include='*.rb' .`
      ; `grep -rn "Arel.sql" --include='*.rb' .` ;
      `grep -rn "Sequel.lit" --include='*.rb' . | grep '#{'` ;
      `grep -rnE '\.(exec|query)\s*\(\s*["'"'"'][^)]*#\{' --include='*.rb' .`
- [ ] **Command injection — CRITICAL with external input** —
      `grep -rnE '(system|exec|spawn)\s*\(\s*["'"'"'][^,)]*#\{' --include='*.rb' .` ;
      ``grep -rnE '`[^`]*#\{|%x[({\[][^)}\]]*#\{' --include='*.rb' .`` ;
      `grep -rnE 'IO\.popen\s*\(\s*["'"'"']' --include='*.rb' .` ;
      `grep -rnE '(Kernel#?open|URI\.open|[^.]open)\s*\(\s*(params|.*user|.*input)' --include='*.rb' . | head`
- [ ] **Deserialization — CRITICAL on external data** —
      `grep -rn "Marshal.load\|Marshal.restore" --include='*.rb' .` ;
      `grep -rn "unsafe_load\|YAML.load_documents" --include='*.rb' .` ;
      `grep -rn "create_additions" --include='*.rb' .` ;
      `grep -rnE "YAML\.(safe_)?load[^_]" --include='*.rb' . | grep "aliases: true"`
- [ ] **eval / reflection sinks** —
      `grep -rnE '\beval\s*\(|instance_eval\s*\(\s*["'"'"']|class_eval\s*\(\s*["'"'"']' --include='*.rb' .`
      ; `grep -rnE '\b(public_)?send\s*\(\s*params' --include='*.rb' .` ;
      `grep -rn "constantize\|const_get" --include='*.rb' . | grep -iE "params|input|name"` ;
      `grep -rn "ERB.new" --include='*.rb' . | grep -vE "erb\"|template_file|File.read\(\s*Rails"`
      ; `grep -rnE '\b(method|instance_method)\(\s*params|&params\[[^]]*\]\.to_sym' --include='*.rb' .`
      (method-object reflection) ;
      `grep -rnE 'render\s*\(?\s*inline:' --include='*.rb' .` (template RCE if the string is
      user-influenced)
- [ ] **Regex: ^/$ anchors in validations — HIGH; ReDoS candidates** —
      `grep -rnE 'format:.*(\^|\$)|match\?\(/\^' --include='*.rb' . | grep -v '\\\\A'` ;
      `grep -rn "Regexp.timeout" --include='*.rb' config/ . 2>/dev/null | head -1` (absent =
      note it); `grep -rnE '\((\.\*|\\w\+|\[[^]]+\]\+)\)[+*]' --include='*.rb' . | head` (nested
      quantifiers)
- [ ] **Regex built from data without `Regexp.escape` — HIGH with external input
      (pattern injection / ReDoS)** — every hit is a dynamic pattern; confirm each
      interpolated piece is escaped, the input is length-capped, and a
      `Regexp::TimeoutError` rejects —
      `grep -rnE 'Regexp\.(new|compile)\( *([^"'"'"'/ ]|"[^"]*#\{)|%r.*#\{|(=~|match\??\(|scan\(|sub!?\(|split\() */[^/]*#\{' --include='*.rb' . | grep -v 'Regexp\.escape\|Regexp\.union'`
- [ ] **Randomness / comparison — HIGH for security uses** —
      `grep -rnE '\brand\(|Random\.(rand|new)|\.sample\b' --include='*.rb' . | grep -viE "spec|test|seed"`
      ; `grep -rnE '(token|hmac|signature|digest)\s*==' --include='*.rb' .`
- [ ] **Path traversal** —
      `grep -rnE 'File\.(open|read|write|join)\([^)]*params' --include='*.rb' .` ;
      `grep -rnE 'Pathname.*(\+|\.join\()[^)]*params' --include='*.rb' .` (an absolute argument
      replaces the base; confirm an expand-then-prefix check follows)

Severity guide: interpolated SQL / shell string with external input,
`Marshal.load`/`unsafe_load` on external data, string `eval` — CRITICAL.
`^$` validation anchors, `rand` tokens, `send(params[...])`,
non-constant-time secret compare — HIGH. Missing `Regexp.timeout` on an
input-facing regex service, `aliases: true` on semi-trusted YAML — MEDIUM.