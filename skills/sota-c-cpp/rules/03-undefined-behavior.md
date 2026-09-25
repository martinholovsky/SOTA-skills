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
  variable before assignment. Initialize at declaration. C++26 (P2795)
  downgrades this from UB to defined "erroneous behavior" — still a bug, but
  no longer optimizer-exploitable once you compile as C++26.
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
  range checks; C++26 adds saturating helpers in `<numeric>`
  (`std::add_sat`/`sub_sat`/`mul_sat`, P0543).
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
- Do **not** "fix" a UBSan report by casting it away — fix the arithmetic or
  the access.

## Audit checklist

- [ ] **Signed-overflow-prone arithmetic feeding sizes/indices — HIGH** —
      `grep -rnE '(malloc|calloc|alloca|new)[^;]*[*+][^;]*' --include='*.c' --include='*.cpp' .`
      (size math → check overflow);
      `grep -rn '__builtin_.*_overflow\|ckd_add\|ckd_mul' . || echo "no checked-arithmetic helpers found"`
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
- [ ] **Ground truth: run under UBSan, aborting on first diagnostic cmake
      -DCMAKE_CXX_FLAGS="-fsanitize=undefined,integer -fno-sanitize-recover=all" ctest # any
      abort == CRITICAL/HIGH**