# 01 — Language baseline & idioms

Modern Ruby (2026 baseline): a supported interpreter, frozen string literals
declared everywhere, pattern matching for structured data, `Data` for value
objects, exceptions designed as an API, and (optionally but increasingly)
gradual typing via RBS-based tooling or Sorbet.

## 1. Version baseline and support policy

Per the official [maintenance branches page](https://www.ruby-lang.org/en/downloads/branches/)
(checked 2026-07):

| Line | Status | Notes |
|---|---|---|
| **4.0** | normal maintenance | current stable; released 2025-12-25 |
| **3.4** | normal maintenance | released 2024-12-25 |
| **3.3** | security maintenance only | expected EOL 2027-03 |
| **≤ 3.2** | **EOL** | 3.2 reached EOL 2026-04-01 |

Rules:

- **Target 3.4+ for new code; 4.0 for new projects.** An app in production on
  an EOL line (≤3.2) is a HIGH finding on its own — no CVE fixes.
- Pin the version in `.ruby-version` and reference it from CI; the `Gemfile`
  states a compatible `ruby` requirement (`ruby file: ".ruby-version"`).
- Feature floor map (use only what the project's floor allows):
  - **3.2**: `Data.define`, `Regexp.timeout=`/`Regexp.linear_time?`
    ([3.2 release](https://www.ruby-lang.org/en/news/2022/12/25/ruby-3-2-0-released/))
  - **3.3**: Prism parser available; per-line GC/perf work
  - **3.4**: `it` implicit block parameter, chilled-string deprecation
    warnings, Prism as default parser
    ([3.4 release](https://www.ruby-lang.org/en/news/2024/12/25/ruby-3-4-0-released/))
  - **4.0**: `Ractor::Port`, experimental ZJIT, `Set` as a core class,
    reserved `Ruby` namespace module
    ([4.0 release](https://www.ruby-lang.org/en/news/2025/12/25/ruby-4-0-0-released/))

## 2. Frozen string literals

String literals are **still not frozen by default, even in Ruby 4.0** (the
[4.0 release notes](https://www.ruby-lang.org/en/news/2025/12/25/ruby-4-0-0-released/)
contain no change; the multi-release migration plan is
[Feature #20205](https://bugs.ruby-lang.org/issues/20205)). Since 3.4,
literals in files *without* the magic comment are "chilled": mutation works
but emits a deprecation warning when `Warning[:deprecated] = true`.

Rules:

- **Every file starts with `# frozen_string_literal: true`** (after the
  shebang, before code). Enforce with RuboCop
  `Style/FrozenStringLiteralComment` (StandardRB includes an equivalent).
- Need a mutable string? Be explicit: `+"literal"`, `String.new`, or `dup`.
- Build strings with interpolation or `<<` on an explicitly-unfrozen buffer,
  never `+=` in a loop (allocates a new string per iteration).
- In BUILD mode, run test suites with `RUBYOPT="-W:deprecated"` periodically
  so chilled-string mutations surface before the eventual frozen default.

## 3. Pattern matching

`case/in` (stable since 3.1) is the idiomatic way to destructure nested
Hash/Array/JSON-shaped data — prefer it over chained `dig`/`is_a?`/`key?`.

```ruby
case parsed_event
in { type: "payment", amount: Integer => cents, currency: String => cur }
  record_payment(cents, cur)
in { type: "refund", **rest }
  handle_refund(rest)
else
  raise UnknownEventError, parsed_event.inspect
end
```

Rules:

- **Always handle the fall-through**: a bare `case/in` raises `NoMatchingPatternKeyError`/
  `NoMatchingPatternError` on no match — that's often *desired* (fail fast on
  unexpected shapes); otherwise write an `else`.
- Use the **pin operator** `^` to match against an existing variable
  (`in { user_id: ^current_id }`); without it you *bind*, not compare —
  a classic logic bug.
- Rightward assignment + destructure for one-shot extraction:
  `response => { data: { id: } }` (raises if the shape is wrong — a free
  schema assert at trust boundaries).
- Custom classes participate via `deconstruct` (array patterns) and
  `deconstruct_keys` (hash patterns) — implement them on domain value objects.
- Keep patterns shallow; three-plus levels of nesting means the parsing
  belongs in a dedicated mapper object.

## 4. Data vs Struct

- **`Data.define` (3.2+) is the default for value objects**: immutable
  (members can't be reassigned), keyword-initialized, value equality,
  `#with` for updated copies, `deconstruct_keys` for pattern matching.

```ruby
Money = Data.define(:cents, :currency) do
  def +(other) = with(cents: cents + other.cents)
end
```

- `Struct` remains for legacy code and when you genuinely need mutability or
  positional construction. Pitfalls: `Struct.new(...)` without
  `keyword_init: true` takes positional args (silent nil members if you pass
  too few), and members are mutable by default.
- Neither replaces a real class once behavior dominates data.
- Don't use `OpenStruct` in new code — slow, defeats typing and method
  resolution; a `Data`, `Hash`, or class is always better.

## 5. Exception design

- **Library/base exceptions inherit from `StandardError`**, never `Exception`
  directly. Define one root per gem/app (`class MyApp::Error < StandardError`)
  and subclass from it so callers can `rescue MyApp::Error`.
- **Never `rescue Exception`** — it swallows `SignalException`,
  `SystemExit`, and `NoMemoryError`. Bare `rescue` catches `StandardError`
  (acceptable but be explicit).
- **No `rescue nil`** or `rescue => e; nil` around logic that matters —
  silenced failure is the number-one source of "impossible" production state.
- Re-raise with context: `raise MyApp::FetchError, "user #{id}: #{e.message}"`
  inside a `rescue e` keeps the `#cause` chain automatically — never
  `raise e.message` (loses class and cause).
- `retry` only with a bounded counter and backoff; unbounded `retry` is a
  spin loop.
- `ensure` blocks must not `return` or `raise` new errors casually — both
  swallow the in-flight exception.
- **Exceptions are for exceptional flow**, not control flow: `Hash#fetch`
  with a default, `find` vs `find!`-style APIs — pick the non-raising variant
  when absence is normal.

## 5a. In-band sentinels — the stdlib is clean, the converters are not

Ruby's search methods return `nil`, not `-1`: `"abc".index("z")` and
`[1,2].index(3)` are both `nil` (verified, Ruby 4.0.6). So the class in
`sota-architecture` rules/02 §8a rarely arrives from the stdlib's search API — it
arrives from **conversion** and from hand-rolled returns.

- `"x".to_i` is `0` and `"12abc".to_i` is `12` (verified) — garbage and a partial
  parse both succeed silently, and `0` is indistinguishable from `"0".to_i`. Use
  `Integer(str)`, which raises `ArgumentError` (verified), or
  `Integer(str, exception: false)` which returns `nil`. Same for `to_f`/`Float()`.
- `nil` is falsy and `0`/`-1` are **truthy** in Ruby, so `if n` is a correct presence
  check against `nil` and a broken one against a numeric sentinel. That asymmetry is
  the argument for keeping absence as `nil` all the way down.
- Returning `-1`/`0`/`false` from your own method where `nil` fits: don't. `nil` +
  `&.`/`then`/pattern matching (§3) is the idiom; a sentinel opts out of all three.
- RBS/Sorbet: type it `Integer?`, and the checker will make callers handle it. A
  magic `-1` inside `Integer` is invisible to Steep and Sorbet alike.
- Audit: `grep -rnE '\.to_i\b|\.to_f\b' --include='*.rb' app/ lib/ | grep -v 'to_i\.to_s'`
  and `grep -rnE 'return (-1|0)$' --include='*.rb' app/ lib/`.

## 6. Typing: RBS, Sorbet, Steep

Gradual typing is optional but SOTA for libraries and large apps. Two
ecosystems (neutral examples — match what the project already uses):

- **RBS** — the standard signature format, bundled with Ruby; signatures live
  in `sig/*.rbs` next to code. Checked by **Steep**; **TypeProf** can
  generate draft signatures.
- **Sorbet** — inline `sig { params(x: Integer).returns(String) }`
  annotations, fast whole-program checker (`srb tc`), optional runtime
  checks; `# typed:` sigil per file (`false`/`true`/`strict`).

Rules:

- Pick **one** checker and gate CI with it; mixed half-adopted setups rot.
- Type the public API first (boundaries where wrong shapes enter); internals
  can stay untyped longer.
- Don't fight the checker with casts (`T.unsafe`, `T.untyped` everywhere, or
  `untyped` in RBS) — an escape-hatch density above a few per file means the
  design, not the checker, is wrong.
- No checker? Then at minimum: keyword arguments for 3+-arg methods, `fetch`
  over `[]` at boundaries, and pattern-matching shape asserts on parsed input.

## 7. General idioms and pitfalls

- **Keyword arguments** for any method where call-site meaning isn't obvious;
  required keywords (`def pay(amount:, currency:)`) over option hashes.
- **`&.` (safe navigation) only when nil is a valid domain state** — chains of
  `&.` hide broken invariants; prefer failing fast.
- **Predicate methods end in `?` and return booleans**; bang methods `!` are
  the *more dangerous* variant of an existing method (mutates, raises), not
  a naming decoration.
- **Enumerable over manual loops**: `map`/`select`/`sum`/`each_slice`;
  `each_with_object` over `inject` for building collections; lazy
  (`.lazy`) for large/infinite chains.
- **Comparable**: implement `<=>` + `include Comparable` instead of six
  operators.
- **Monkey patching core classes is forbidden in app code**; if unavoidable
  in a gem, use a `Refinement` or a clearly-namespaced module prepend, and
  document it.
- **`require_relative` within a project, `require` for gems**; no code
  execution at require time beyond definitions (side-effectful requires break
  autoloading and testing).
- **Block form for anything that must be closed.** `File.open(path) { |f| ... }` closes on
  every exit, exceptions included; the bare form keeps the descriptor until someone calls
  `close`. Measured on Ruby 4.0.6: the block form's handle was `closed?` after a `raise`
  inside the block, and a bare `File.open` stayed open. Prefer the block form wherever an API
  offers one; otherwise `ensure` the `close`.
- Time: **`Time.now.utc` / monotonic clocks for durations**
  (`Process.clock_gettime(Process::CLOCK_MONOTONIC)`); never subtract two
  `Time.now` calls for measuring elapsed time in production code.
- Equality: `==` for values, `equal?` only for identity, `eql?`+`hash` pair
  when used as Hash keys.
- `method_missing` requires a matching `respond_to_missing?`; prefer
  `define_method` metaprogramming that produces real, introspectable methods.

## 8. Designing a public surface — everything is public until you say otherwise

Shared design rules: `sota-architecture` rules/02 and `sota-api-design`; semver honesty is
already in `rules/04`. **This is the Ruby mechanism**, and Ruby's default is the opposite of
every other language in this tier: a gem's surface is everything it defines, and narrowing it
later is the breaking change.

**`private` does not do what its name suggests — twice over.**

- **It does not apply to `def self.` class methods.** Measured on Ruby 4.0.6 as a
  differential: with a bare `private` above both, the instance method raised `NoMethodError`
  and the class method was **still callable**. Use `private_class_method :name`, or
  `class << self` with `private` inside it. A `private` that silently applies to nothing is
  indistinguishable from one that works, until a consumer depends on the method.
- **It does not apply to constants.** A bare `INTERNAL = 3` inside a class is reachable as
  `C::INTERNAL` with no declaration at all, and is therefore API. `private_constant :SECRET`
  is the mechanism — measured: referencing it afterwards raises
  `NameError: private constant B::SECRET referenced`.

**So the audit question for a gem is inverted**: not *"what did we export?"* but *"what did we
fail to hide?"* Every public instance method, every class method, every constant and every
module you reopen is a promise a consumer may already rely on.

- **Monkey-patching a core class is public API for the whole process**, not just your gem. If
  it must happen, a `Refinement` scopes it to the files that `using` it (§7) — otherwise
  namespace it and let callers opt in.
- `method_missing` widens the surface to things you never wrote; pair it with
  `respond_to_missing?` (§7) or `respond_to?` lies about what your object accepts.
- **Deprecate before removing**: keep the old name delegating to the new one for a major
  cycle, and emit a `warn` naming the replacement. Removing a public method is a major bump,
  and Ruby gives the consumer no compile step that would have caught it.

## Audit checklist

Run from repo root; verify each hit manually.

**Public surface** (§8) — Ruby hides nothing by default, so the question is what you
failed to hide, not what you exported:

- [ ] ** `private` does NOT apply to `def self.` -- measured on 4.0.6, the class method stayed
      callable while the instance method raised NoMethodError. A private that applies to nothing
      looks identical to one that works.** —
      `grep -rn -B3 'def self\.' lib/ | grep -A3 '^\s*private\s*$'` ;
      `grep -rn 'private_class_method\|class << self' lib/` (the forms that actually work)
- [ ] ** `private` does NOT apply to constants either: a bare CONST is reachable as Mod::CONST A
      LOCATOR, NOT A VERDICT: `grep -v` is line-scoped, so a constant privatised on the NEXT
      line still appears here (verified against a fixture that does exactly that). Compare the
      two counts below instead of trusting the filtered list.** —
      `grep -rnE '^\s*[A-Z][A-Z0-9_]+ *=' lib/ | grep -v 'private_constant'` ;
      `grep -rncE '^\s*[A-Z][A-Z0-9_]+ *=' lib/ ; grep -rnc 'private_constant' lib/` ;
      `grep -rn 'private_constant' lib/` (the mechanism, if used at all)
- [ ] **Handles opened without the block form (§7) — MEDIUM, HIGH in a long-lived process** —
      `grep -rnE '=[[:space:]]*(File|Tempfile|Zlib::GzipReader|TCPSocket)\.(open|new)\(' --include='*.rb' app/ lib/`
      (an assigned handle: find its `ensure ... close`, or convert it to a block)
- [ ] **Load-path hacks instead of `require_relative` (§7) — LOW, MEDIUM in a gem** —
      `grep -rnE 'require[[:space:]]+.\.\.?/|\$LOAD_PATH|\$:[[:space:]]*(<<|\.unshift)' --include='*.rb' app/ lib/`
      (`require './x'` resolves against the process's working directory, not the file:
      measured on 4.0.6, it raised `LoadError` when run from another directory, where
      `require_relative` loaded)
- [ ] **Monkey-patching a core class is API for the whole process, not just this gem** —
      `grep -rnE '^\s*class (String|Array|Hash|Integer|Object|Kernel)\b' lib/` ;
      `grep -rn 'refine \|using ' lib/` (the scoped alternative (§7))

**In-band sentinels** (§5a) — Ruby's search API returns `nil`, so these arrive from
conversion and from hand-rolled returns:

- [ ] `grep -rnE '\.to_i\b|\.to_f\b' --include='*.rb' app/ lib/` (0 on garbage, 12 on "12abc" —
      use Integer(s)); `grep -rnE 'return (-1|0)$' --include='*.rb' app/ lib/` (prefer nil,
      which is falsy and pattern-matchable)

- [ ] **Interpreter floor — EOL Ruby is HIGH** —
      `cat .ruby-version 2>/dev/null; grep -n "^ruby" Gemfile 2>/dev/null`
- [ ] **(compare against the branches page table above)**
- [ ] **Missing frozen_string_literal comments — LOW (bulk-fix with rubocop -a)** —
      `grep -rL "frozen_string_literal: true" --include='*.rb' app/ lib/ 2>/dev/null | head`
- [ ] **rescue Exception — MEDIUM (HIGH if it wraps a main loop)** —
      `grep -rn "rescue Exception" --include='*.rb' .`
- [ ] **Silenced errors — MEDIUM+** — `grep -rn "rescue nil" --include='*.rb' .` ;
      `grep -rnE "rescue(\s+StandardError)?\s*(=>\s*_?e?)?\s*$" --include='*.rb' . | head`
- [ ] **raise losing the original class/cause** —
      `grep -rnE "raise\s+e\.message" --include='*.rb' .`
- [ ] **OpenStruct in new code — LOW** — `grep -rn "OpenStruct" --include='*.rb' .`
- [ ] **Struct without keyword_init (positional-arg hazard) — INFO/LOW** —
      `grep -rn "Struct.new" --include='*.rb' . | grep -v keyword_init`
- [ ] **Pattern matching without pin where comparison was intended (manual review)** —
      `grep -rnE "in \{[^}]*: [a-z_]+ *\}" --include='*.rb' . | head`
- [ ] **Monkey patches on core classes — MEDIUM in app code** —
      `grep -rnE "^\s*class (String|Array|Hash|Integer|Symbol|Object)\b" --include='*.rb' app/ lib/ 2>/dev/null`
- [ ] **method_missing without respond_to_missing?** —
      `grep -rln "def method_missing" --include='*.rb' . | xargs grep -L "respond_to_missing?" 2>/dev/null`
- [ ] **Wall-clock durations — LOW** —
      `grep -rnE "Time\.now.*-.*Time\.now|=\s*Time\.now\b.*# .*(elapsed|duration)" --include='*.rb' . | head`
- [ ] **Typing posture — INFO** —
      `ls sig/ sorbet/ 2>/dev/null; grep -rn "# typed:" --include='*.rb' . | head -3`

Severity guide: EOL interpreter HIGH; `rescue Exception`/`rescue nil` around
critical logic MEDIUM–HIGH; missing frozen-string comments LOW (bulk-fixable);
`OpenStruct`/`Struct` misuse LOW; absent typing INFO.