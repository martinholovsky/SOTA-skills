# 03 — Undefined behavior and the optimizer

Undefined behavior (UB) is not "implementation-defined" or "works on my
machine" — it is the standard granting the compiler permission to assume the
program *never* does the thing, and to optimize on that assumption. A single
UB on a reachable path can delete your bounds check, miscompile a loop, or open
a vulnerability. "It worked in a debug build" proves nothing: optimizers
exploit UB at `-O2`. Treat any UBSan diagnostic as CRITICAL/HIGH. Reference:
[cppreference UB](https://en.cppreference.com/w/cpp/language/ub),
[SEI CERT C/C++](https://wiki.sei.cmu.edu/confluence/display/seccode).

## 1. The high-frequency UB catalog

- **Signed integer overflow** (CERT INT32-C) — `INT_MAX + 1` is UB; the
  compiler may assume `x + 1 > x` always and remove your overflow check.
  Unsigned overflow is *defined* (modular), so it's safe but can still produce
  logic bugs.
- **Out-of-bounds access** — indexing/pointer past an object (incl. one-past-
  the-end deref). Often the optimizer assumes in-bounds and reorders.
- **Use of uninitialized values** (CERT EXP33-C) — reading an automatic
  variable before assignment. Initialize at declaration. C++26 (P2795R5)
  downgrades this from UB to defined "erroneous behavior" (EB), with three limits the paper
  states: it covers **automatic storage only** (memory from `new`/`malloc` still holds
  indeterminate values, and reading them is still UB); a variable marked `[[indeterminate]]`
  opts back into UB; and EB is "always the consequence of incorrect program code", which an
  implementation may diagnose or terminate on. So it is a smaller blast radius, not a fix:
  still initialize, value-initialize heap objects (`new T()`, `calloc`), and treat each
  `[[indeterminate]]` as a sharp tool that needs a `NOTE(sota)` reason. GCC 16's release notes
  list P2795R5 as implemented; Clang's C++ status page listed it as not yet (read 2026-09-25).
- **`= {0}` does not zero a whole union on GCC 15+.** The GCC 15 release notes: `{0}` for a
  union "just initializes the first union member to zero" (static storage excepted). Measured
  with GCC 15.3: a 32-byte automatic union whose first member is a `char`, initialized `= {0}`
  on a stack pre-filled with `0xAA`, still had 31 non-zero bytes at `-O2` (19 at `-O0`); `= {}`
  left none, and so did `-fzero-init-padding-bits=unions` or `=all` (`rules/04` §5). Apple clang
  21 zeroed all 32 either way, so the leak depends on the compiler. Copying such a union to the
  wire, a file or another privilege level discloses stack bytes: write `= {}` (C23, C++) or
  `memset` it before filling.
- **Null / misaligned / invalid pointer deref** — incl. calling a method on a
  null `this`. The optimizer may assume a dereferenced pointer is non-null and
  delete subsequent null checks.
- **Strict aliasing violation** (§3) — accessing an object through an
  incompatible type.
- **Data races** (§5, `rules/05`) — concurrent access where ≥1 is a write,
  without synchronization, is UB.
- **Invalid shifts** — shifting by ≥ width, or shifting a negative/by-negative
  (CERT INT34-C). `x << 32` on a 32-bit `int` is UB.
- **Signed→unsigned surprises, modifying a `const` object, infinite loops with
  no side effects, calling through a wrong function-pointer type.**

## 2. Integer overflow and conversions

- Validate ranges *before* arithmetic that could overflow, especially when the
  result feeds an allocation size, array index, or loop bound — overflow-to-
  small-allocation is a classic exploit primitive (`rules/04`).
- Use checked arithmetic: GCC/Clang `__builtin_add_overflow`/`mul_overflow`,
  or C23 `<stdckdint.h>` `ckd_add`/`ckd_mul`. For C++ prefer typed wrappers or
  range checks; C++26 adds saturating helpers in `<numeric>` ([numeric.sat]):
  `std::saturating_add`/`_sub`/`_mul`/`_div` and `std::saturating_cast`. P0543 named them
  `add_sat`/`sub_sat`/`mul_sat`/`div_sat`/`saturate_cast`; P4052R0 renamed them, and early
  standard-library implementations shipped the old names, so check which yours has.
- **A check written after the addition is deleted.** `x + 1 < x` on a signed `int` returned 0
  for `INT_MAX` at `-O2` on both GCC 16.2 and Apple clang 21 (measured): the optimiser assumed
  no overflow and folded the test away. `-fwrapv` (signed arithmetic wraps) and GCC's
  `-fno-strict-overflow` each kept it, returning 1. The OpenSSF Compiler Options Hardening
  Guide lists `-fno-strict-overflow` in its **production** set (`rules/04` §5; in Clang it is a
  synonym for `-fwrapv`), so ship with it. It is still **not the fix**: it makes the wrapped
  value defined, not correct. The fix is to test *before* adding, or to use the checked
  helpers below. OWASP: C-Based Toolchain Hardening cheat sheet.
- Avoid implicit narrowing/sign conversions; compile with `-Wconversion
  -Wsign-conversion`. Brace-init (`int x{expr};`) rejects narrowing at compile
  time.
- Index/size types: prefer unsigned (`size_t`) for sizes but beware unsigned
  *wraparound* in subtractions (`a - b` when `b > a` is a huge number) — guard
  the order.
- **Float to integer truncates, and is UB out of range.** The fraction is dropped toward
  zero, and a value that does not fit the target type is undefined behaviour (C++
  [conv.fpint], C 6.3.1.4). UBSan's `-fsanitize=float-cast-overflow` reports it: measured
  with Apple clang 21, `1e20` to `long long`. **Money is never `double`/`float`.** Neither
  language has a standard decimal type, so keep integer minor units in `int64_t` with the
  checked arithmetic above, or use a vetted decimal library. Convert a computed float to
  minor units with `llround`/`std::llround` (half away from zero), not a cast: measured,
  `(long)(19.99 * 100)` is `1998` and `llround` gives `1999`. `printf("%.2f")` rounds the
  binary value (`2.675` prints `2.67`, measured), so it is display, not arithmetic.
- **Arithmetic edge cases at the boundary.** `strtod`, `std::stod` and `std::from_chars`
  all accept `"nan"`, `"inf"` and `"-Infinity"` from input and return a non-finite value
  with no error (measured, Apple clang 21 / libc++). Every comparison with NaN is false,
  so `if (x < lo || x > hi) reject();` lets a NaN through: test `std::isfinite(x)`
  (`isfinite` in C) first. Integer `/` or `%` by zero is UB (it trapped with SIGFPE on
  x86-64, measured; do not rely on that), and so is `INT_MIN / -1` and `-INT_MIN`: guard
  `b == 0` and `a == MIN && b == -1` before dividing. Floating `/0.0` is UB in the
  standards (UBSan `-fsanitize=float-divide-by-zero` flags it) even though IEEE hardware
  yields `inf`. Multi-term expressions overflow in the intermediate, and so do unit
  conversions: `std::chrono::nanoseconds{seconds_from_input}` multiplied a signed
  `long long` past its range under UBSan (measured), so bound the input or convert with
  `ckd_mul`/`__builtin_mul_overflow` first. (OWASP: Go-SCP general coding practices; SCSVS
  arithmetic.)

```cpp
// BAD — n*size can overflow to a small value; tiny alloc, then huge copy
T* p = (T*)malloc(n * sizeof(T));
// GOOD — checked
size_t bytes;
if (__builtin_mul_overflow(n, sizeof(T), &bytes)) return err();
T* p = (T*)malloc(bytes);
```

## 3. Strict aliasing and type punning

- The compiler assumes objects of unrelated types don't alias, and reorders/
  caches loads accordingly. Reading the bytes of a `float` through an `int*`
  is UB (CERT EXP39-C).
- **Correct type punning**: `std::bit_cast<To>(from)` (C++20, constexpr, both
  trivially copyable, same size) or `memcpy` into a destination object. Not a
  pointer cast, not a union read-of-other-member in C++ (defined in C, UB in
  C++).
- `char`, `unsigned char`, and `std::byte` may alias anything — that's how you
  inspect raw bytes legally.
- `reinterpret_cast` does not bless aliasing; it's the usual source of these
  bugs. Each use needs a comment justifying why it's defined.

## 4. Alignment, object lifetime, and pointer provenance

- Don't access an object through a misaligned pointer; `alignas`/`alignof` and
  proper allocation matter for SIMD and some ABIs.
- An object's lifetime begins at initialization and ends at destruction;
  accessing storage outside that window is UB even if the memory is still
  mapped (this is what UAF *is* at the language level). Placement-new + manual
  destructor must bracket any reuse of storage.

## 5. Data races are UB (see rules/05)

Two threads accessing the same non-atomic object, at least one writing, with no
happens-before relation, is UB — not "a stale read". Use `std::atomic` or a
mutex. Build threaded code under TSan.

## 6. Tooling: make UB visible

- **UBSan** (`-fsanitize=undefined -fno-sanitize-recover=all`) traps signed
  overflow, OOB (some), misalignment, null deref, bad enum/bool values, invalid
  shifts — run the test/fuzz suite under it.
- `-fsanitize=integer` (Clang) additionally flags *defined-but-suspicious*
  unsigned wrap. `-ftrapv` is a blunter alternative for signed overflow.
- `-Wall -Wextra -Wconversion -Wsign-conversion -Wshadow -Wcast-align` catch
  many at compile time. Static analyzers (clang-analyzer, cppcheck) and
  Coverity find aliasing/uninit paths (`rules/06`).
- **TypeSanitizer** (`-fsanitize=type`, Clang only; its docs call it brand new and still in
  development) detects strict-aliasing violations (§3) at run time. Measured with Fedora's Clang
  22.1: an `int*` write to a `float` object was reported as a `type-aliasing-violation`, yet the
  process exited 0, so fail the job on the report text, not the exit status. It refused to
  combine with `address` ("not allowed with"), and Apple clang 21 compiled it but shipped no
  TySan runtime to link (measured). Run it as a periodic job, not a gate: the docs warn of wrong
  results around unions and of about 8x shadow memory.
- Do **not** "fix" a UBSan report by casting it away — fix the arithmetic or
  the access.

## 7. C++26 contracts are not input validation

- `pre(...)`, `post(...)` and `contract_assert(...)` (P2900R14, adopted for C++26) check a
  predicate under an **evaluation semantic**: *ignore* (the predicate is not evaluated),
  *observe* (call the violation handler, then carry on), *enforce* (handler, then terminate) or
  *quick-enforce* (terminate at once). Which one applies is implementation-defined and may
  differ between evaluations of the same assertion; the paper recommends enforce as the default
  and asks implementations to offer an all-ignore build. A contract therefore states what a
  correct caller does; it does not stop a hostile one.
- Measured with GCC 16.2, `-std=c++26` (no `-fcontracts` needed): `int get(int i) pre(i >= 0
  && i < 4) { return buf[i]; }` called with 11 terminated under the default semantic (enforce,
  per `g++ --help=c++`) and under `quick_enforce`. With `-fcontract-evaluation-semantic=observe`
  the handler ran and the out-of-bounds read followed; with `=ignore` it followed silently.
- **Rule:** validate untrusted input (length, index, range, format) with an explicit `if` that
  returns an error or throws, the same rule as for `assert` (`rules/04` §2). A contract may
  restate that invariant for internal callers. Where a contract is nonetheless the only guard on
  external data, the build pins `-fcontract-evaluation-semantic=enforce` (or `quick_enforce`)
  for every unit and the release pipeline asserts it; a packager's `observe` or `ignore` turns the
  guard off with no source change. Toolchains (read 2026-09-25): GCC 16's release notes list
  P2900R14 as implemented; Clang's C++ status page lists contracts as not yet implemented.

## Audit checklist

- [ ] **Signed-overflow-prone arithmetic feeding sizes/indices — HIGH** —
      `grep -rnE '(malloc|calloc|alloca|new)[^;]*[*+][^;]*' --include='*.c' --include='*.cpp' .`
      (size math → check overflow);
      `grep -rn '__builtin_.*_overflow\|ckd_add\|ckd_mul' . || echo "no checked-arithmetic helpers found"`
- [ ] **Overflow tested after the addition (§2) — HIGH where the sum is a size or index** —
      `grep -rnE 'if[[:space:]]*\([[:space:]]*[a-z_][a-z_0-9]*[[:space:]]*\+[[:space:]]*[a-z_0-9]+[[:space:]]*<[[:space:]]*[a-z_][a-z_0-9]*[[:space:]]*\)' --include='*.c' --include='*.cc' --include='*.cpp' --include='*.h' .`
      (read each: when the right side is one of the addends and the type is signed, the check is
      gone at `-O2`. Rewrite with `ckd_add`/`__builtin_add_overflow`, and until then look for
      `-fwrapv` or `-fno-strict-overflow` on that target)
- [ ] **Type punning / strict-aliasing — HIGH** —
      `grep -rn 'reinterpret_cast' --include='*.cpp' --include='*.hpp' .` ;
      `grep -rnE '\*\s*\(\s*[A-Za-z_][A-Za-z0-9_ ]*\*\s*\)' --include='*.c' .` (C pointer-cast
      deref (heuristic)); `grep -rn 'union' --include='*.cpp' .` (union type-pun is UB in C++)
- [ ] **Bad shifts / conversions — MEDIUM/HIGH** —
      `grep -rnE '<<|>>' --include='*.c' --include='*.cpp' . | grep -vE '(cout|cerr|<<=|stream)'`
      (verify shift amounts)
- [ ] **Money in binary floats, truncating float-to-int (§2) — MEDIUM, HIGH in money paths** —
      `grep -rniE '(double|float)[[:space:]]+[*&]?[a-z_]*(price|amount|total|balance|cost|fee|tax)' --include='*.c' --include='*.h' --include='*.cc' --include='*.cpp' --include='*.hpp' .`
      (money declared as a binary float) ;
      `grep -rnE '(\((long long|long|int|u?int(32|64)_t)\)[[:space:]]*\(|static_cast<[a-z0-9_ ]+>\()[^;]*\*[[:space:]]*100' --include='*.c' --include='*.cc' --include='*.cpp' .`
      (scaled to minor units by a truncating cast; use `llround`)
- [ ] **NaN/infinity from parsed input, divide by zero, INT_MIN / -1 (§2) — HIGH on size,
      price or limit paths** —
      `grep -rLE 'isfinite|isnan' --include='*.c' --include='*.cc' --include='*.cpp' . | xargs grep -nE '(strto(d|f|ld)|sto(d|f|ld)|atof)[[:space:]]*\(' /dev/null`
      (float parsed in a file that never checks finiteness); then review each `/` and `%`
      by an input-derived divisor for the zero and MIN/-1 guards
- [ ] **Build with conversion warnings: -Wconversion -Wsign-conversion -Wshadow -Wcast-align
      -Wshift-overflow=2**
- [ ] **Uninitialized — MEDIUM** —
      `clang-tidy --checks='cppcoreguidelines-init-variables,clang-analyzer-core.uninitialized.*' <files>`
      ; `grep -rnE '\[\[[[:space:]]*indeterminate[[:space:]]*\]\]' --include='*.cpp' --include='*.cc' --include='*.hpp' --include='*.h' .`
      (§1: each opt-out of C++26 erroneous behaviour restores UB; it needs a stated reason)
- [ ] **Union zeroed with `= {0}` (§1) — MEDIUM, HIGH when the union is copied out of the
      process or across a privilege boundary** —
      `grep -rnE 'union[[:space:]]+[A-Za-z_][A-Za-z0-9_]*[[:space:]]+[A-Za-z_][A-Za-z0-9_]*[[:space:]]*=[[:space:]]*\{[[:space:]]*0[[:space:]]*\}' --include='*.c' --include='*.h' --include='*.cc' --include='*.cpp' .`
      (a typedef'd union escapes this pattern: also read `= {0}` hits on union types. Fix with
      `= {}` or `memset`, or `-fzero-init-padding-bits=unions` on GCC 15+)
- [ ] **Contract assertion as the only guard on external input (§7) — HIGH where the value
      comes from input and the build can select `ignore` or `observe`** —
      `grep -rnE '\)[^;{]*[[:space:]](pre|post)[[:space:]]*\(|contract_assert[[:space:]]*\(' --include='*.cpp' --include='*.cc' --include='*.hpp' --include='*.h' .`
      (read each: is there an explicit check on the input path before it?) ;
      `grep -rnE -e '-fcontract-evaluation-semantic=[a-z_]+' . || echo "contract semantic not pinned"`
- [ ] **Ground truth: run under UBSan, aborting on first diagnostic (Clang only: `integer` is a
      Clang sanitizer group; with GCC drop it) cmake -DCMAKE_CXX_COMPILER=clang++
      -DCMAKE_CXX_FLAGS="-fsanitize=undefined,integer -fno-sanitize-recover=all" ctest # any
      abort == CRITICAL/HIGH**