# 02 — Memory safety: lifetimes, bounds, use-after-free, sanitizers

C and C++ give you no runtime guard against reading freed memory, walking off
the end of a buffer, or aliasing storage you no longer own. ~70% of CVEs in
large C/C++ codebases are memory-safety bugs (per Microsoft and Chromium
telemetry; see [Chromium memory-safety](https://www.chromium.org/Home/chromium-security/memory-safety/)).
These are the highest-severity findings in any C/C++ audit: presume
exploitable. The defense is ownership discipline (`rules/01`) plus the tools
below.

## 1. The bug classes

- **Buffer overflow/underflow** — index or pointer outside an object's bounds.
  Read = info leak; write = corruption/RCE.
- **Use-after-free (UAF)** — dereferencing a pointer to freed/destroyed
  storage. Includes use-after-`return` (pointer to a local) and
  use-after-move-then-reuse-of-internal-buffer.
- **Double-free / invalid free** — freeing twice or freeing non-heap/offset
  pointers; corrupts the allocator.
- **Dangling reference/view** — `T&`, `string_view`, `span`, iterator, or
  pointer outliving its storage.
- **Uninitialized read** — using memory before it holds a value (also UB,
  `rules/03`).
- **Memory leak** — lost ownership; rarely exploitable but a reliability/DoS
  issue.

## 2. Bounds: never index memory you didn't size-check

- Use containers and views that carry their size: `std::vector`, `std::array`,
  `std::span<T>` (C++20), `std::string`, `std::string_view`. `span`/`string_
  view` are *non-owning* — see §4.
- Index with `.at()` (checked) on cold paths; on hot paths bounds-check once at
  the boundary then use `operator[]`. Never compute `ptr + n` from
  attacker-controlled `n` without validating `n` against the real length.
- In C, always pass length alongside the pointer and check it; prefer
  `snprintf`/`memcpy_s`-style bounded ops. `-D_FORTIFY_SOURCE=3` adds runtime
  bounds checks to many libc calls (`rules/04`).
- Enable hardened standard-library assertions so OOB container access traps
  instead of corrupting: libstdc++ `-D_GLIBCXX_ASSERTIONS`, libc++
  `-D_LIBCPP_HARDENING_MODE=_LIBCPP_HARDENING_MODE_EXTENSIVE` (LLVM 18+ — verify
  for your toolchain).

```cpp
// BAD — trusts len from the wire; OOB read/write
void parse(const uint8_t* p, size_t len) { uint8_t b = p[off]; /* off unchecked */ }

// GOOD — span carries size; checked access
void parse(std::span<const uint8_t> buf) {
  if (off >= buf.size()) throw std::out_of_range("off");
  uint8_t b = buf[off];
}
```

## 3. Lifetimes: own clearly, observe carefully

- Single owner via `unique_ptr`/container (`rules/01`). The owner's destructor
  is the one free; observers never free.
- **Never return a pointer/reference/view to a local or temporary** (CG F.43):

```cpp
std::string_view bad() { std::string s = make(); return s; }   // dangling on return
const std::string& worse(std::map<K,V>& m, K k) { return m[k].name; } // ok only while m & entry live
```

- Beware references/views captured into objects or lambdas that outlive the
  referent (CG F.50, ES.61). A lambda capturing `[&]` stored past the enclosing
  scope dangles.
- `std::string_view`/`std::span` parameters are great for *borrowing within a
  call*; do not store them unless you control and outlive the backing storage.
  Binding `string_view` to a temporary `std::string` (e.g. from `+`) dangles.

## 4. Iterator and reference invalidation

- Mutating a container can invalidate iterators, pointers, and references into
  it: `vector` push/insert/reserve invalidates on reallocation; `erase`
  invalidates at/after the point; `unordered_*` rehash invalidates iterators.
  Re-acquire after mutation; don't cache across a modifying call (CG ES.62).
- The classic bug: iterating and erasing — use the return of `erase`
  (`it = v.erase(it)`) or `std::erase_if` (C++20).

## 5. Sanitizers — the ground truth

Build a dedicated job with sanitizers and run the full test/fuzz suite. They
catch what review and `-Wall` cannot. (Clang/GCC; see
[Clang sanitizers](https://clang.llvm.org/docs/index.html).)

| Sanitizer | Flag | Catches | Notes |
|---|---|---|---|
| **ASan** | `-fsanitize=address` | heap/stack/global overflow, UAF, double-free, leaks | ~2x slowdown; not with Valgrind; the workhorse |
| **UBSan** | `-fsanitize=undefined` | overflow, misalignment, null deref, bad casts, OOB (some) | pair with `-fno-sanitize-recover=all` to abort |
| **MSan** | `-fsanitize=memory` | uninitialized reads | Clang only; needs instrumented libs |
| **TSan** | `-fsanitize=thread` | data races, lock-order issues | `rules/05`; mutually exclusive with ASan |

- ASan and TSan can't run together — use two jobs. MSan needs an instrumented
  libc++ to avoid false positives.
- Add `-fsanitize-address-use-after-scope` to catch use of out-of-scope locals.
- **Valgrind/Memcheck** is the no-recompile fallback (catches UAF/leaks/
  uninit), but slower and misses stack/global overflows ASan catches. Prefer
  ASan+UBSan in CI; keep Valgrind for third-party binaries you can't rebuild.

## 6. Allocation hygiene

- Check every allocation: `new` throws `std::bad_alloc` (handle or let it
  propagate to a boundary); `malloc`/`calloc`/`realloc` return NULL — check
  before use. Unchecked `malloc` of an input-derived size is HIGH.
- `realloc` returning NULL must not overwrite the original pointer (else leak);
  use a temp. Free with the matching deallocator (`free`↔`malloc`,
  `delete`↔`new`, `delete[]`↔`new[]`; mismatches are UB).
- Prefer not to mix manual allocation with C++ at all — `make_unique`,
  `vector`, `string` remove the whole class.

## Audit checklist

```bash
# Banned/dangerous buffer ops — HIGH/CRITICAL (also rules/04)
grep -rnE '\b(strcpy|strcat|sprintf|gets|stpcpy|vsprintf)\b' --include='*.c' --include='*.cpp' .
grep -rnE '\b(memcpy|memmove|memset|strncpy)\b' --include='*.c' --include='*.cpp' .  # verify size provenance

# Dangling: returning address/ref/view of a local — HIGH
grep -rnE 'return &[A-Za-z_]' --include='*.cpp' --include='*.c' .
grep -rnE 'return (std::)?(string_view|span)' --include='*.cpp' .   # verify backing outlives
clang-tidy --checks='bugprone-dangling-handle,bugprone-use-after-move,clang-analyzer-cplusplus.*' <files>

# Iterator invalidation / erase-in-loop — MEDIUM
grep -rnE 'for *\(.*begin\(\).*\).*\.(erase|push_back|insert|clear)\(' --include='*.cpp' .

# Allocation checks — HIGH
grep -rnE '=\s*(malloc|calloc|realloc)\(' --include='*.c' --include='*.cpp' .  # confirm NULL-check follows
grep -rnE '(new|new\[\])' --include='*.cpp' . | grep -v make_                  # confirm RAII ownership

# Sanitizer/hardening presence in the build — HIGH if a network binary lacks them
grep -rn 'fsanitize' . ; grep -rn '_GLIBCXX_ASSERTIONS\|_LIBCPP_HARDENING\|_FORTIFY_SOURCE' .

# Build & run the suite under sanitizers (ground truth)
#   cmake -DCMAKE_BUILD_TYPE=Debug -DCMAKE_CXX_FLAGS="-fsanitize=address,undefined -fno-sanitize-recover=all"
#   ctest   # any ASan/UBSan abort == CRITICAL/HIGH finding
```
