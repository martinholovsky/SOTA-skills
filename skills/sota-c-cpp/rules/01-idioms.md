# 01 — Idioms: RAII, ownership, value semantics, error handling

Modern C++ is a different language from "C with classes". The through-line is
**let the type system and destructors enforce correctness** so that the happy
path and every error/exception path clean up identically. References:
[C++ Core Guidelines](https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines)
(cited as `CG <id>` below) and [cppreference](https://en.cppreference.com/).

## 1. RAII and the rule of zero/five

- **Rule of zero** (CG C.20): the best class manages no raw resources — it
  composes `std::string`, `std::vector`, `unique_ptr`, etc., and needs *no*
  user-declared destructor, copy, or move. Default everything. Reach for this
  first.
- **Rule of five** (CG C.21): if you declare *any* of destructor, copy ctor,
  copy assign, move ctor, move assign, declare or `= default`/`= delete` all
  five. A class that owns a raw handle and defines only a destructor silently
  gets memberwise copy → double-free.
- Wrap every C resource (FILE*, fd, mutex, malloc'd block, library handle) in
  an RAII type once, then use it by value. The destructor is the only place
  cleanup lives, so early `return`, `throw`, and normal exit all release.

```cpp
// GOOD — RAII wrapper; closes on every exit path, non-copyable, movable
class File {
  std::FILE* f_{};
public:
  explicit File(const char* p, const char* m) : f_(std::fopen(p, m)) {
    if (!f_) throw std::system_error(errno, std::generic_category(), p);
  }
  ~File() { if (f_) std::fclose(f_); }
  File(const File&) = delete;
  File& operator=(const File&) = delete;
  File(File&& o) noexcept : f_(std::exchange(o.f_, nullptr)) {}
  File& operator=(File&& o) noexcept { std::swap(f_, o.f_); return *this; }
  std::FILE* get() const noexcept { return f_; }
};
```

## 2. Ownership: smart pointers, not raw owning pointers

- `std::unique_ptr<T>` is the default owner — zero overhead, move-only, clear
  single ownership. `std::make_unique<T>(...)` (never `new`).
- `std::shared_ptr<T>` only when ownership is genuinely *shared* and lifetime
  is dynamic; it has atomic-refcount cost. `std::make_shared` for one
  allocation. Break cycles with `std::weak_ptr`.
- **Raw pointers and references are non-owning** (CG R.3, F.7): they observe,
  never delete. A function takes `T*`/`T&`/`std::span`/`string_view` to borrow;
  it takes `unique_ptr<T>` (by value) only to take ownership.
- Never `delete` a raw pointer in modern code; never store a `new`'d pointer in
  a bare member. Owning raw pointers are a MEDIUM finding (CRITICAL if they
  leak/double-free on a path).

## 3. Value semantics and move

- Prefer values and containers over pointers. Copies are explicit and safe;
  moves transfer ownership cheaply.
- Pass **cheap-to-copy** types (int, `string_view`, small structs) by value;
  pass large objects by `const&` to read, by `&` to mutate, by value + `std::
  move` when the function will store a copy (the "sink" idiom).
- `std::move` is a *cast*, not a move; it only enables the move. Don't `move` a
  `const` object (silently copies), don't use a moved-from object except to
  reassign/destroy, don't `return std::move(local)` — it pessimizes (N)RVO.
- Mark move operations `noexcept` or `std::vector` falls back to copying on
  reallocation (CG C.66).

## 4. const, constexpr, and immutability

- `const` by default — parameters, locals, methods that don't mutate, member
  data that's set once. `const` is documentation the compiler enforces.
- `constexpr`/`consteval` for compile-time constants and functions; prefer over
  macros and over runtime computation of fixed values.
- Avoid `const_cast` away constness on an object actually declared `const` —
  that's UB if you then write (`rules/03`).

## 5. References vs pointers, and casts

- Prefer references where null is not a valid state; use pointers (or
  `std::optional`/`std::expected`) where absence is meaningful.
- **No C-style casts** (`(T)x`) in C++ — they silently become whichever of
  `static/const/reinterpret_cast` compiles, hiding intent and danger (CG
  ES.49). Use the named casts; `reinterpret_cast` is a red flag requiring a
  comment and a strict-aliasing review (`rules/03`).
- `static_cast` for related types; never use it to "fix" a warning about
  signed/unsigned or narrowing without checking the value first.

## 6. Type-system leverage

- `enum class` over plain `enum` and over integer/macro constants — scoped,
  typed, no implicit conversions (CG Enum.3).
- `[[nodiscard]]` on functions whose return must be checked (error codes,
  `expected`, allocations, `empty()`); `explicit` on single-argument
  constructors and conversion operators (CG C.46) to stop surprise conversions.
- `override` on every overrider and `final` where appropriate; declare
  destructors `virtual` in polymorphic base classes (CG C.35) — deleting a
  derived object through a base pointer without a virtual destructor is UB.
- Prefer `using` aliases to `typedef`; prefer `inline`/`constexpr` to
  function-like macros (macros ignore scope and types).

## 7. Error handling: exceptions vs expected vs codes

- Within a codebase, pick one strategy per layer and be consistent (CG E.1+).
- **Exceptions** are the C++ default for errors that can't be handled locally;
  they compose with RAII so stack unwinding releases resources. Throw by value,
  catch by `const&`. Don't use exceptions for normal control flow.
- **`std::expected<T,E>`** (C++23) for expected, recoverable failures in hot or
  exception-averse paths (parsers, lookups) — explicit, allocation-free, forces
  the caller to handle `E`. `std::optional<T>` when there's no error detail.
- **Error codes** (C return-int, `std::error_code`) at C ABI boundaries and in
  freestanding/embedded where exceptions are disabled.
- A function that can fail must make failure unignorable: `[[nodiscard]]`
  return, `expected`, or a thrown exception — never a silently-ignored global
  `errno` the caller forgets to check.
- `noexcept` on functions that truly can't throw (destructors, swaps, moves);
  a `throw` escaping `noexcept` calls `std::terminate`.

## 8. C-specific idioms (when the target is C)

- Initialize every variable at declaration; designated initializers (C99+) for
  structs. Use `const` and `static` aggressively to limit scope/linkage.
- One allocation owner per resource; pair every `malloc`/`fopen`/`open` with a
  single `free`/`fclose`/`close` reached on all paths (goto-cleanup idiom is
  acceptable and idiomatic in C). Check every allocation return.
- Prefer `sizeof(*ptr)` over `sizeof(Type)` in allocations so the size tracks
  the pointer's type. Use bounded string functions (`snprintf`, `strlcpy` where
  available); see `rules/04` for the banned list.

## Audit checklist

```bash
# Owning raw pointers / manual new-delete — MEDIUM (CRITICAL if leak/double-free)
grep -rnE '\bnew\b[^=]*;' --include='*.cpp' --include='*.h' --include='*.hpp' . | grep -v make_
grep -rnE '\bdelete\b\s' --include='*.cpp' --include='*.hpp' .
grep -rn 'malloc\|calloc\|realloc\|free(' --include='*.c' --include='*.cpp' .

# C-style casts and reinterpret_cast — MEDIUM/HIGH
grep -rnE '\([[:space:]]*[A-Za-z_][A-Za-z0-9_:<> ]*[*&]?[[:space:]]*\)[[:space:]]*[A-Za-z_(]' --include='*.cpp' .  # heuristic, expect FPs
grep -rn 'reinterpret_cast\|const_cast' --include='*.cpp' --include='*.hpp' .

# Rule of five violations — class with destructor but not all 5 special members
clang-tidy --checks='cppcoreguidelines-special-member-functions,cppcoreguidelines-rule-of-*' <files>

# Missing virtual destructor in polymorphic base — HIGH (UB on delete-via-base)
clang-tidy --checks='cppcoreguidelines-virtual-class-destructor,hicpp-use-override' <files>

# Move/idiom smells — LOW
grep -rn 'return std::move' --include='*.cpp' .          # pessimizes RVO
grep -rn 'using namespace std;' --include='*.h' --include='*.hpp' .  # in headers: bad
grep -rnE '#define [A-Z_]+\(' --include='*.h' .          # function-like macros → constexpr/inline

# Broad idiom enforcement (the canonical config)
clang-tidy --checks='cppcoreguidelines-*,modernize-*,bugprone-*' <files>
```
