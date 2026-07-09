# 04 — Security: CERT/MISRA, banned APIs, injection, hardened builds

Every byte from network, file, env, argv, IPC, or another process is untrusted
until validated. In C/C++ the memory-safety classes (`rules/02`) and UB
(`rules/03`) are themselves the dominant vulnerability surface; this file adds
the input-handling, API, and build-hardening controls. Standards:
[SEI CERT C](https://wiki.sei.cmu.edu/confluence/display/c) /
[CERT C++](https://cmu-sei.github.io/secure-coding-standards/sei-cert-cpp-coding-standard/),
[MISRA C:2025 / C++:2023](https://misra.org.uk/) (safety-critical),
[OpenSSF Compiler Hardening Guide](https://best.openssf.org/Compiler-Hardening-Guides/Compiler-Options-Hardening-Guide-for-C-and-C++.html).

## 1. Banned and dangerous functions

Replace on sight (CERT STR/FIO; MISRA):

| Banned | Why | Use instead |
|---|---|---|
| `gets` | no bounds; removed in C11 | `fgets`, bounded reader |
| `strcpy`/`strcat` | no bounds → overflow | `std::string`; or `snprintf`/`strlcpy` |
| `sprintf`/`vsprintf` | no bounds | `snprintf`/`vsnprintf`; `std::format` (C++20) |
| `scanf("%s")` | unbounded | width-limited `%Ns`, or parse manually |
| `system`/`popen` | shell injection | `posix_spawn`/`exec*` with argv array |
| `strtok` | not reentrant | `strtok_r`/`strtok_s` |
| `alloca`/VLA on input size | stack overflow | fixed cap or heap + check |
| `atoi`/`atol` | no error report | `strtol` + range/errno check |

- Prefer C++ types that eliminate the class entirely: `std::string`,
  `std::vector`, `std::format`/`std::print` (C++23), `std::filesystem`.

## 2. Input validation at the boundary

- Validate once, at the trust boundary, into a typed/bounded value; interior
  code trusts its types. Allowlist (enums, ranges, lengths), not denylist.
- Bounds- and overflow-check every length/count/offset from input *before*
  using it to allocate, index, or copy (`rules/03` §2). This is the single
  most important control against C/C++ RCE.
- For binary parsers: never trust an embedded length field; cap it against the
  remaining buffer. Fuzz the parser (`rules/06`).

## 3. Format-string and injection

- **Never** pass user data as the format string: `printf(user)` is a
  format-string vuln (read/write via `%n`). Use `printf("%s", user)`. Compile
  with `-Wformat -Wformat=2 -Werror=format-security` to catch it.
- **Command injection**: don't build shell strings. Use `posix_spawn`/`execve`
  with an explicit argument vector and no shell; never `system("cmd " + input)`.
- **SQL/other injection**: parameterized queries / prepared statements only
  (the DB client API), never string-concatenated SQL — see `sota-databases`.
- **Path traversal / TOCTOU** (CERT FIO): canonicalize with
  `std::filesystem::weakly_canonical`/`realpath` and verify the result stays
  under an allowed root; prefer `openat`/`O_NOFOLLOW` and operate on fds to
  avoid check-then-use races on the path.

## 4. Cryptography and randomness

- **Never** use `rand()`/`random()`/`std::mt19937` for security
  (keys, tokens, IVs, salts) — they're predictable. Use the OS CSPRNG:
  `getrandom(2)` / `arc4random_buf` / `BCryptGenRandom`, or a vetted library
  (libsodium, OpenSSL `RAND_bytes`). `std::random_device` is *not* guaranteed
  cryptographic and may be deterministic on some libs.
- Don't roll your own crypto or protocols; use libsodium/OpenSSL/BoringSSL.
  Constant-time compare for secrets (`sodium_memcmp`, `CRYPTO_memcmp`), never
  `memcmp` on a MAC/token (timing leak). See `sota-code-security` rules/04.
- Zero secrets after use with a *guaranteed* wipe (`explicit_bzero`,
  `sodium_memzero`, `SecureZeroMemory`) — plain `memset` can be optimized away.

## 5. Hardened build (the OpenSSF baseline)

Turn these on for production builds (GCC/Clang); missing them on a
network-facing or setuid binary is a HIGH finding. From the OpenSSF guide:

```
-O2 -Wall -Wextra -Wformat -Wformat=2 -Wconversion -Wimplicit-fallthrough \
-Werror=format-security \
-U_FORTIFY_SOURCE -D_FORTIFY_SOURCE=3      # libc fortified bounds checks
-D_GLIBCXX_ASSERTIONS                       # libstdc++ bounds assertions
-fstack-protector-strong                    # stack canaries
-fstack-clash-protection                    # large-stack probing
-fcf-protection=full                        # CET: indirect-branch protection
-fstrict-flex-arrays=3                      # only true flex arrays are unbounded
-ftrivial-auto-var-init=zero                # zero-init locals (kills uninit reads)
-fzero-init-padding-bits=all                # zero padding bits too (GCC 15+)
-mbranch-protection=standard                # AArch64 PAC/BTI (-fcf-protection analogue)
-fPIE -pie                                  # ASLR for the executable
-Wl,-z,relro -Wl,-z,now                     # full RELRO (GOT read-only)
-Wl,-z,noexecstack -Wl,-z,nodlopen          # non-exec stack, no dlopen
```

- libc++ builds: production uses hardening mode FAST
  (`-D_LIBCPP_HARDENING_MODE=_LIBCPP_HARDENING_MODE_FAST`, cheap checks); the
  EXTENSIVE mode (`rules/02`) is for debug/test builds.
- Add `-fsanitize=address,undefined` to the *debug/test* build (not prod).
  Consider `-fhardened` (GCC 14+) as a shorthand umbrella — verify your
  compiler version supports it.
- Treat warnings as errors (`-Werror`) in CI; a clean `-Wall -Wextra` is the
  floor, not the ceiling — also run a static analyzer (`rules/06`).

## 6. Memory-safety strategy (the meta-control)

- Where feasible, move new untrusted-input-parsing code to a memory-safe
  language (Rust), or isolate the C/C++ parser (sandbox/seccomp, separate
  process) — see `sota-sandboxing`. CISA/NSA and the OpenSSF now treat "C/C++
  for new attack-surface code" as a risk decision, not a default.
- Use `std::span`/`std::string_view`/containers instead of pointer+length
  everywhere they fit; enable libc++/libstdc++ hardened mode (`rules/02`).

## Audit checklist

```bash
# Banned functions — HIGH/CRITICAL
grep -rnwE '(gets|strcpy|strcat|sprintf|vsprintf|stpcpy|scanf|system|popen|strtok|atoi|atol)' \
  --include='*.c' --include='*.cpp' --include='*.h' .
grep -rnE '\balloca\b|\[[^]]*\] *= *\{?' --include='*.c' .   # VLA/alloca on dynamic size

# Format string — CRITICAL (user-controlled fmt)
grep -rnE '(printf|fprintf|snprintf|syslog|err|warn)\s*\([^,"]*\)' --include='*.c' --include='*.cpp' .
# build with: -Wformat=2 -Werror=format-security

# Command/path injection, TOCTOU — HIGH/CRITICAL
grep -rnE 'system\(|popen\(|exec[lv]p?\(' --include='*.c' --include='*.cpp' .
grep -rnE 'fopen|open\(|realpath|access\(' --include='*.c' --include='*.cpp' .  # check-then-use races

# Insecure randomness for security — HIGH
grep -rnE '\b(rand|random|srand|mt19937|random_device)\b' --include='*.cpp' --include='*.c' .
grep -rn 'memcmp' --include='*.cpp' . | grep -iE 'mac|hmac|token|secret|sig|digest'  # timing leak

# Hardening flags present? — HIGH if missing on network/setuid binary
grep -rnE '_FORTIFY_SOURCE|stack-protector|relro|cf-protection|_GLIBCXX_ASSERTIONS|fPIE' \
  CMakeLists.txt cmake/ Makefile* 2>/dev/null || echo "no hardening flags found"

# Static + safety-standard analysis
clang-tidy --checks='cert-*,bugprone-*,clang-analyzer-security.*' <files>
cppcheck --enable=warning,portability --addon=cert <src>
```
