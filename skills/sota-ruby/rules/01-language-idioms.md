<!-- last-verified: 2026-07 -->
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
- Time: **`Time.now.utc` / monotonic clocks for durations**
  (`Process.clock_gettime(Process::CLOCK_MONOTONIC)`); never subtract two
  `Time.now` calls for measuring elapsed time in production code.
- Equality: `==` for values, `equal?` only for identity, `eql?`+`hash` pair
  when used as Hash keys.
- `method_missing` requires a matching `respond_to_missing?`; prefer
  `define_method` metaprogramming that produces real, introspectable methods.

## Audit checklist

Run from repo root; verify each hit manually.

```bash
# Interpreter floor — EOL Ruby is HIGH
cat .ruby-version 2>/dev/null; grep -n "^ruby" Gemfile 2>/dev/null
# (compare against the branches page table above)

# Missing frozen_string_literal comments — LOW (bulk-fix with rubocop -a)
grep -rL "frozen_string_literal: true" --include='*.rb' app/ lib/ 2>/dev/null | head

# rescue Exception — MEDIUM (HIGH if it wraps a main loop)
grep -rn "rescue Exception" --include='*.rb' .

# Silenced errors — MEDIUM+
grep -rn "rescue nil" --include='*.rb' .
grep -rnE "rescue(\s+StandardError)?\s*(=>\s*_?e?)?\s*$" --include='*.rb' . | head

# raise losing the original class/cause
grep -rnE "raise\s+e\.message" --include='*.rb' .

# OpenStruct in new code — LOW
grep -rn "OpenStruct" --include='*.rb' .

# Struct without keyword_init (positional-arg hazard) — INFO/LOW
grep -rn "Struct.new" --include='*.rb' . | grep -v keyword_init

# Pattern matching without pin where comparison was intended (manual review)
grep -rnE "in \{[^}]*: [a-z_]+ *\}" --include='*.rb' . | head

# Monkey patches on core classes — MEDIUM in app code
grep -rnE "^\s*class (String|Array|Hash|Integer|Symbol|Object)\b" --include='*.rb' app/ lib/ 2>/dev/null

# method_missing without respond_to_missing?
grep -rln "def method_missing" --include='*.rb' . | xargs grep -L "respond_to_missing?" 2>/dev/null

# Wall-clock durations — LOW
grep -rnE "Time\.now.*-.*Time\.now|=\s*Time\.now\b.*# .*(elapsed|duration)" --include='*.rb' . | head

# Typing posture — INFO
ls sig/ sorbet/ 2>/dev/null; grep -rn "# typed:" --include='*.rb' . | head -3
```

Severity guide: EOL interpreter HIGH; `rescue Exception`/`rescue nil` around
critical logic MEDIUM–HIGH; missing frozen-string comments LOW (bulk-fixable);
`OpenStruct`/`Struct` misuse LOW; absent typing INFO.
