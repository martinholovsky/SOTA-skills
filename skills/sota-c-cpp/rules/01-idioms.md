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

## 7a. In-band sentinels, and the platform that changes the answer

C has no option type, so the in-band sentinel (`sota-architecture` rules/02 §8a) is
the *native* idiom — and its two classic bugs are both about the sentinel's type
rather than its value.

- `atoi("x")` and `atoi("0")` both return `0` (verified, clang 21, macOS): failure
  and a legitimate parse are indistinguishable. Use `strtol` + `errno`/`endptr`
  (already in rules/04's banned-API table).
- **`EOF` is `-1` as an `int`, and storing it in a `char` breaks the comparison —
  on some platforms only.** Measured, clang 21 on x86-64 Darwin: with the default
  **signed** `char`, `(char)EOF == EOF` is **true** and the code works; compiled
  `-funsigned-char` (the default on ARM and PowerPC Linux) it is **false**, and the
  read loop never terminates. Note which way the diagnostic runs: clang warns
  (`-Wtautological-constant-out-of-range-compare`) only in the **broken**
  configuration, so a developer on a signed-`char` machine sees neither the bug nor
  the warning. Always `int c; while ((c = getchar()) != EOF)`. This is the
  location-dependent silence class — `sota-code-security` rules/13 §5.
- POSIX's `-1`-plus-`errno` is a genuine out-of-band pair; it only degrades into an
  in-band sentinel when the caller keeps the `-1` and drops `errno`.
- **C++ has the alternatives — use them:** `std::optional<T>` for absent,
  `std::expected<T,E>` (C++23) for failed. A function returning `int` where `-1`
  means "no result" is a C++ API bug, not a style preference.

## 8. C-specific idioms (when the target is C)

- Initialize every variable at declaration; designated initializers (C99+) for
  structs. Use `const` and `static` aggressively to limit scope/linkage.
- One allocation owner per resource; pair every `malloc`/`fopen`/`open` with a
  single `free`/`fclose`/`close` reached on all paths (goto-cleanup idiom is
  acceptable and idiomatic in C). Check every allocation return.
- Prefer `sizeof(*ptr)` over `sizeof(Type)` in allocations so the size tracks
  the pointer's type. Use bounded string functions (`snprintf`, `strlcpy` where
  available); see `rules/04` for the banned list.

## 8a. Construction and destruction — what actually runs is not what you wrote

Four traps where the code is legal, the compiler is silent, and the behaviour is not the one
the source reads like. All measured below on clang 17, x86-64 Darwin. cppcheck flags all four
(`virtualCallInConstructor`, `pureVirtualCall`, `initializerList`, `assertWithSideEffect`) —
this section is the rule behind those ids.

**Virtual dispatch does not work in a constructor or destructor.** During the base
constructor the object *is* a base — the derived vtable is not installed yet — so a virtual
call dispatches to the **base** override, not the derived one. Measured: a `B` constructor
calling `tag()` on a `D` object printed **BASE**. In a destructor the same happens in reverse
as the derived part is torn down first. If the base is abstract there, it is worse: a pure
virtual call is **undefined behaviour**, usually a `pure virtual method called` abort.
*Fix:* do not call virtuals from a constructor/destructor. Two-phase `init()`, a factory that
constructs then initialises, or pass the varying behaviour in as a parameter.

**Members initialise in DECLARATION order, not in the order of the initialiser list.**

```cpp
struct M {
    int a, b;                       // declaration order: a, then b
    M() : b(1), a(b + 10) {}        // reads like b first -- it is not
};
```

`a` is initialised **first**, reading `b` before it exists. Measured — and the tell is that
the answer *changed with the build*: `a` came out **70261** at `-O0` and **10** under
`-DNDEBUG`. Same source, same compiler, different value, no diagnostic. Order the initialiser
list to match declaration order and let `-Wreorder` (in `-Wall`) keep it that way.

**`assert` is deleted by `NDEBUG`, so anything inside it must be side-effect free.**
Measured: `assert(++n == 1)` left `n == 1` in a normal build and **`n == 0`** compiled with
`-DNDEBUG` — the increment simply did not happen, in the build you ship. Any expression with
an effect belongs on its own line, with the assert testing the result. And an `assert` is
never a security control for the same reason — `sota-code-security` rules/11.

**Self-assignment must be safe**, because a copy assignment that frees before it copies
destroys the object when `x = x` happens through two references. The copy-and-swap idiom gets
this right by construction; if you hand-write `operator=`, either guard `if (this == &other)`
or build the copy before releasing anything. Rule of five (§1) says *declare* all five — it
does not say the bodies are correct.

## 9. Designing a public surface — what a released header promises

The shared design rules (what belongs in a public API at all, deprecation policy, semver)
are `sota-architecture` rules/02 and `sota-api-design`. **This section is the C/C++
mechanism**: here the compiled *layout* is part of the contract, so a change that is source-
compatible can still break every caller — and unlike a signature change, which fails loudly
at link time, a layout change frequently links fine and corrupts memory at run time.

**What a header change costs, by kind:**

| change | source-compatible | ABI-compatible | how it fails |
|---|---|---|---|
| add a data member (even `private`) | yes | **no** | caller's `sizeof`/offsets are stale — silent corruption |
| add the *first* virtual function | yes | **no** | adds a vptr; every offset moves |
| add a virtual to a class others derive from | yes | **no** | vtable slots shift under the derived class |
| reorder members | yes | **no** | silent: offsets change, names do not |
| change a C++ function's parameters or `const` | no | no | **loud** — the mangled name changes, link error |
| change an `extern "C"` function's parameters | no | **no** | **silent** — C has no mangling, the symbol still resolves |
| change a default argument | yes | **no** | the default is compiled into the *caller*; old callers keep the old value |
| change an `inline` body | yes | **no** | the old body is already inlined into callers |
| add a new non-virtual, non-inline function | yes | yes | safe |

**The rule that falls out of the table: a released class is frozen unless you hid its
layout.** That is what `pimpl` buys — the public class holds one owning pointer and nothing
else, so members can be added to the implementation struct forever without moving anything a
caller measured:

```cpp
// widget.hpp — layout frozen: one pointer, whatever the implementation grows into
class Widget {
public:
    Widget(); ~Widget();                       // defined in the .cpp: Impl is incomplete here
    Widget(Widget&&) noexcept;                 // = default in the HEADER would need Impl
    Widget& operator=(Widget&&) noexcept;
    void draw() const;
private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};
```

The destructor and move operations must be **declared** here and **defined** in the `.cpp`
where `Impl` is complete; `= default` in the header instantiates `unique_ptr`'s deleter
against an incomplete type and fails to compile. Costs: one indirection and one allocation
per object, so it buys stability on a *library boundary*, not on a hot internal type.

**A standard-library type in an exported signature exports your toolchain with it.**
`std::string`, `std::vector` and friends have no standardised layout, so both sides must be
built with the same implementation *and* the same configuration. Verified against GCC's own
documentation: libstdc++ introduced a second ABI in **GCC 5.1**, selected by
`_GLIBCXX_USE_CXX11_ABI`, and mixing the two surfaces as *"undefined references to symbols
that involve types in the `std::__cxx11` namespace or the tag `[abi:cxx11]`"*. For a boundary
you do not control both sides of, pass primitives, pointers and POD structs — or an
`extern "C"` layer.

**Note what that layer costs, because it is the one remedy here that removes a safety
net.** C++ encodes parameter types in the mangled name, so a changed C++ signature cannot
link against an old caller — the toolchain catches it for you. **C has no mangling**:
change an `extern "C"` function's parameters and the symbol still resolves, the program
links clean, and the old caller passes the old arguments to the new function. That
boundary is stable precisely because nothing checks it, so version it by hand — add a
`_v2` entry point rather than editing an existing one, and never quietly change what an
existing parameter means.

**Header hygiene** — what a header drags in is part of its cost:

- **Include what you use, and forward-declare what you only refer to.** A declaration needs
  only `class Widget;`; a definition needs the header. Pulling in a heavy header for a
  reference or pointer multiplies build time across every translation unit.
- **Never `using namespace` at file scope in a header.** It is inherited by every file that
  includes it, and it changes overload resolution in code that never asked for it.
- **`#pragma once` or include guards on every header** — `#pragma once` is universally
  supported by current compilers but is not in the standard; guards are the portable form.
- **Default to hidden.** Compile with `-fvisibility=hidden` and export deliberately through
  one macro. A smaller exported set means fewer accidental promises, faster loads and a
  smaller ABI surface to keep stable.
- **Macros are not namespaced.** A macro in a public header has no scope and no owner; if one
  is unavoidable, prefix it with the library name.

## Audit checklist

- [ ] **Owning raw pointers / manual new-delete — MEDIUM (CRITICAL if leak/double-free)** —
      `grep -rnE '\bnew\b[^=]*;' --include='*.cpp' --include='*.h' --include='*.hpp' . | grep -v make_`
      ; `grep -rnE '\bdelete\b\s' --include='*.cpp' --include='*.hpp' .` ;
      `grep -rn 'malloc\|calloc\|realloc\|free(' --include='*.c' --include='*.cpp' .`
- [ ] **C-style casts and reinterpret_cast — MEDIUM/HIGH** —
      `grep -rnE '\([[:space:]]*[A-Za-z_][A-Za-z0-9_:<> ]*[*&]?[[:space:]]*\)[[:space:]]*[A-Za-z_(]' --include='*.cpp' .`
      (heuristic, expect FPs);
      `grep -rn 'reinterpret_cast\|const_cast' --include='*.cpp' --include='*.hpp' .`
- [ ] **Rule of five violations — class with destructor but not all 5 special members** —
      `clang-tidy --checks='cppcoreguidelines-special-member-functions,cppcoreguidelines-rule-of-*' <files>`
- [ ] **Missing virtual destructor in polymorphic base — HIGH (UB on delete-via-base)** —
      `clang-tidy --checks='cppcoreguidelines-virtual-class-destructor,hicpp-use-override' <files>`
- [ ] **Move/idiom smells — LOW** — `grep -rn 'return std::move' --include='*.cpp' .`
      (pessimizes RVO); `grep -rn 'using namespace std;' --include='*.h' --include='*.hpp' .`
      (in headers: bad); `grep -rnE '#define [A-Z_]+\(' --include='*.h' .` (function-like macros
      → constexpr/inline)
- [ ] **Error handling (§7) — the section had no probe at all until 2026-08-21** —
      `grep -rnE 'catch[[:space:]]*\([^)]*\)[[:space:]]*\{[[:space:]]*\}' --include='*.cpp' .`
      (empty catch — HIGH); `grep -rn 'catch (...)' --include='*.cpp' .` (swallow-all: needs a
      rethrow or a logged reason);
      `clang-tidy --checks='bugprone-empty-catch,bugprone-exception-escape,misc-throw-by-value-catch-by-reference' <files>`
- [ ] **Ignored error returns — the C half of §7, and the one nobody greps then ask the §7
      question a grep cannot: is ONE error model used across a given boundary, or do exceptions,
      codes and expected<> meet at an ABI seam? Mixed models at a boundary is the finding, not
      any one of them.** —
      `clang-tidy --checks='bugprone-unused-return-value,cert-err33-c' <files>` (cert-err33-c
      aliases the former);
      `grep -rn 'std::expected\|absl::Status\|tl::expected' --include='*.cpp' --include='*.hpp' . | head`
- [ ] **Broad idiom enforcement (the canonical config)** —
      `clang-tidy --checks='cppcoreguidelines-*,modernize-*,bugprone-*' <files>`
- [ ] **In-band sentinels (§7/§8) — absence encoded as a value** —
      `grep -rnE 'return -1;' --include='*.c' --include='*.cpp' .` (producer: same constant from
      2 branches?); `grep -rn 'atoi(\|atol(' --include='*.c' --include='*.cpp' .` (0 on garbage
      == 0 on "0" (rules/04))
- [ ] **Construction/destruction traps (§8a) — legal code, silent compiler, wrong behaviour All
      four are cppcheck ids, so the cheapest probe is to RUN it with these enabled** —
      `cppcheck --enable=warning,style --inline-suppr <src>` (virtualCallInConstructor,)
- [ ] **pureVirtualCall, initializerList, assertWithSideEffect, operatorEqToSelf Without
      cppcheck, by hand: a side effect inside assert() VANISHES under -DNDEBUG. Measured:
      assert(++n == 1) left n==1 normally and n==0 with -DNDEBUG. Check the build actually
      defines NDEBUG. written this way on purpose. The one-line form -- a grep with stderr
      discarded, then an or-echo announcing absence -- reports YOUR broken sweep as THEIR
      defect, because the or-branch fires on every non-zero exit and the discarded stderr took
      the reason with it. rules/06 2d. Invariant 32 rejected the short form here while this
      section was written, and then rejected this very comment for spelling the pattern out
      literally: refer to it by name, never by its characters, in prose that shares a file with
      the check.** —
      `grep -rnE 'assert\(' --include='*.cpp' --include='*.c' --include='*.h' . | grep -E '\+\+|--|=[^=]|\('`
      ; `err=$(grep -rn 'NDEBUG' CMakeLists.txt *.cmake 2>&1 >/dev/null); rc=$?` ; `case $rc in`
      ; `0) ;;` (found: asserts are compiled out in that build);
      `1) echo "NDEBUG not set here: release builds may still run asserts" ;;` ;
      `*) echo "SWEEP FAILED, not a finding about their code: $err" ;;` ; `esac`
- [ ] **Members init in DECLARATION order, not list order -- -Wreorder catches it, so verify the
      build does not silence it** —
      `grep -rnE '\-Wall|\-Wreorder|\-Wno-reorder' CMakeLists.txt *.cmake 2>/dev/null`
- [ ] **Virtual call from a ctor/dtor dispatches to the BASE (measured), and a pure one is UB:
      each hand-written operator= must be self-assignment safe (copy-and-swap, or a guard)** —
      `grep -rnE '^\s*(virtual |[A-Z][A-Za-z0-9_]*::)?~?[A-Z][A-Za-z0-9_]*\s*\([^)]*\)\s*(:|\{)' --include='*.cpp' . | head`
      (then read each ctor/dtor body for a virtual call);
      `grep -rn 'operator=' --include='*.cpp' --include='*.h' . | grep -v 'delete\|default'`
- [ ] **Public surface / ABI (§9) — layout is part of a released header's contract THE question,
      which no linter asks: does any + line add a data member, add a virtual, reorder members,
      or change a default argument? Each is source-compatible and ABI-BREAKING, and only the
      signature change fails loudly at link time. default arguments in public headers — the
      value is baked into each CALLER stdlib types in an EXPORTED signature tie both sides to
      one toolchain+config; libstdc++ has had two since GCC 5.1 (_GLIBCXX_USE_CXX11_ABI,
      std::__cxx11 / [abi:cxx11] undefined references are the tell). Fine internally; a promise
      at a boundary you do not build both sides of. unique_ptr/shared_ptr are deliberately NOT
      in the pattern: a unique_ptr<Impl> member is what pimpl above prescribes, so including
      them would flag this file's own recommendation (tested, it did). the `||` prints on a
      FAILED SEARCH too (`sota-shell-scripting` rules/06 §2d): confirm the grep ran before reading the message as a
      finding.** — `git diff <last-release-tag>..HEAD -- '*.h' '*.hpp' | grep -nE '^\+[^+]'` ;
      `grep -rnE '=[[:space:]]*[A-Za-z0-9_"'"'"'{(-]+[[:space:]]*\)' --include='*.h' --include='*.hpp' . | head`
      ;
      `grep -rnE '\b(std::(string|vector|map|list|deque|set))\b' --include='*.h' --include='*.hpp' .`
      ; `grep -rn 'using namespace' --include='*.h' --include='*.hpp' .` (inherited by every
      includer); `grep -rL  '#pragma once\|#ifndef' --include='*.h' --include='*.hpp' .` (-L =
      files NOT matching);
      `grep -rn 'fvisibility' --include='CMakeLists.txt' --include='*.cmake' . || echo "no -fvisibility=hidden: everything is exported by default — a larger ABI surface than intended"`
      ; `grep -rnE 'char[[:space:]]+[a-z_]+[[:space:]]*=[[:space:]]*getchar' --include='*.c' .`
      (EOF in a char: breaks only where char is UNSIGNED)