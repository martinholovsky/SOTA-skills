# 06 — Build, tooling, and CI

A C/C++ project's safety is only as good as its build and CI gates. The
toolchain is where warnings-as-errors, static analysis, sanitizers, fuzzing,
and supply-chain controls are enforced. This file owns build/test *mechanics*;
test **strategy** (suite shape, doubles, coverage philosophy) lives in
`sota-testing`.

## 1. CMake hygiene (the de-facto standard)

- Use modern, target-based CMake (≥3.20): `target_link_libraries`,
  `target_compile_features(tgt PUBLIC cxx_std_23)`,
  `target_compile_options`/`target_include_directories` with `PRIVATE`/
  `PUBLIC`/`INTERFACE` scoping. Avoid global `include_directories`,
  `link_libraries`, and `CMAKE_CXX_FLAGS` mutation.
- Set the standard explicitly and require it:
  `set(CMAKE_CXX_STANDARD 23)`, `CMAKE_CXX_STANDARD_REQUIRED ON`,
  `CMAKE_CXX_EXTENSIONS OFF` (no `-std=gnu++23` unless you mean it).
- Treat compiler/linker warnings as errors in CI builds. Generate
  `compile_commands.json` (`CMAKE_EXPORT_COMPILE_COMMANDS ON`) so clang-tidy/
  clang-analyzer see exact flags.
- Pin the toolchain (compiler version) in CI; build with multiple compilers
  (GCC + Clang, and MSVC if you ship Windows) — each finds different bugs.

## 2. Warnings and static analysis

- Baseline flags: `-Wall -Wextra -Wpedantic -Wconversion -Wsign-conversion
  -Wshadow -Wcast-align -Wnull-dereference -Wdouble-promotion
  -Wimplicit-fallthrough -Werror`. MSVC: `/W4 /permissive- /WX`.
- **clang-tidy** with a curated set is the primary linter:
  `bugprone-*, cppcoreguidelines-*, cert-*, performance-*, modernize-*,
  clang-analyzer-*, misc-*` (tune noisy checks). Commit a `.clang-tidy`.
- **cppcheck** (`--enable=warning,performance,portability --addon=cert`) and the
  **Clang Static Analyzer** (`scan-build` or via clang-tidy) catch path-
  sensitive bugs the compiler misses. Commercial: Coverity, PVS-Studio for
  deeper interprocedural analysis.
- **clang-format** with a committed `.clang-format`; enforce in CI
  (`--dry-run --Werror`) so style never enters review.

## 3. Sanitizers in CI (non-negotiable)

- A dedicated job builds Debug with `-fsanitize=address,undefined
  -fno-sanitize-recover=all` and runs the full test suite; any abort fails CI
  (`rules/02`, `rules/03`). A second job runs `-fsanitize=thread` for
  concurrent code (`rules/05`). MSan optionally (needs instrumented libs).
- Set `ASAN_OPTIONS=detect_leaks=1:strict_string_checks=1` and
  `UBSAN_OPTIONS=print_stacktrace=1` in CI.
- Sanitizer builds are for test/CI, not production; production uses the
  hardened flag set (`rules/04` §5).

## 4. Fuzzing for input parsers

- Any code parsing untrusted bytes (network, file formats, decoders) gets a
  fuzz target: **libFuzzer** (`-fsanitize=fuzzer,address,undefined`) or AFL++.
  Run continuously; enroll high-value OSS in [OSS-Fuzz](https://google.github.io/oss-fuzz/).
- Keep a seed corpus and regression corpus in-repo; a new crash is a CRITICAL
  finding. Pair fuzzing with ASan/UBSan so memory/UB bugs surface.

## 5. Dependencies and supply chain

- Use a real package/dependency manager: **vcpkg** or **Conan** with a
  *manifest* and a **lockfile** (`vcpkg.json`+baseline / `conan.lock`) so
  builds are reproducible and versions are pinned. Avoid vendoring random
  source or system-package drift.
- Pin versions; review and update deliberately (Dependabot/Renovate where
  supported). Verify checksums/signatures of fetched artifacts. Generate an
  **SBOM** (CycloneDX/SPDX) for releases and scan dependencies for known CVEs.
  See `sota-devsecops`.
- Minimize the dependency tree; each header-only or binary dep is attack
  surface and a build-integrity risk. Prefer the standard library.

## 6. Reproducible, deterministic builds

- Avoid timestamps/paths leaking into binaries (`-ffile-prefix-map`,
  `SOURCE_DATE_EPOCH`); enable LTO for release (`-flto`) but verify it doesn't
  mask UBSan. Keep debug info (`-g`) and ship split symbols.

## Audit checklist

```bash
# Warnings-as-errors and standard pinned?
grep -rnE 'Werror|/WX' CMakeLists.txt cmake/ Makefile* 2>/dev/null || echo "no -Werror"
grep -rnE 'CXX_STANDARD|cxx_std_|std=c\+\+' CMakeLists.txt 2>/dev/null

# clang-tidy / clang-format / cppcheck configs present?
ls .clang-tidy .clang-format 2>/dev/null || echo "missing lint/format config"
test -f compile_commands.json || grep -rn EXPORT_COMPILE_COMMANDS CMakeLists.txt

# Sanitizer & fuzzing jobs in CI?
grep -rniE 'fsanitize|asan|ubsan|tsan|libfuzzer|oss-fuzz|scan-build' .github/ ci/ 2>/dev/null \
  || echo "no sanitizer/fuzz job found — HIGH for input-parsing code"

# Dependency manager + lockfile?
ls vcpkg.json conan.lock conanfile.* 2>/dev/null || echo "no pinned dependency manifest/lockfile"
grep -rni 'FetchContent\|ExternalProject\|git submodule' CMakeLists.txt .gitmodules 2>/dev/null  # verify pinning

# Global (non-target) CMake anti-patterns — LOW/MEDIUM
grep -rnE 'include_directories\(|link_libraries\(|^set\(CMAKE_CXX_FLAGS' CMakeLists.txt 2>/dev/null
```
