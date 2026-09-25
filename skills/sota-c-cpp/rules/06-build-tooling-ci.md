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
- **Pin the C dialect too: the compiler default moves.** GCC 15 changed the C default from
  `gnu17` to `gnu23`, and GCC 16 the C++ default from `gnu++17` to `gnu++20` (their release
  notes). Measured: under GCC 15.3, `typedef int bool;` built with `-std=gnu17` and failed by
  default ("'bool' cannot be defined via 'typedef'"); GCC 16.2 with no `-std` reported
  `__cplusplus` 202002 and `__STDC_VERSION__` 202311. Set `CMAKE_C_STANDARD` and
  `CMAKE_C_STANDARD_REQUIRED ON` beside the C++ pair, or `-std=` in every Makefile.
- **`-fpermissive` in a C build is a finding, not a porting fix.** GCC 14 made implicit
  function declarations, implicit `int`, int-conversion, incompatible-pointer-types, return
  mismatches and missing parameter types errors; its porting guide names `-fpermissive` (or
  `-std=gnu89`/`c89`) as the way back to warnings. Measured with GCC 15.3: an undeclared call
  plus `int *p = 5;` failed with two errors by default and produced an object file under
  `-fpermissive`. Each is a call or pointer with the wrong type at run time: fix the code.
- Treat compiler/linker warnings as errors in CI builds. Generate
  `compile_commands.json` (`CMAKE_EXPORT_COMPILE_COMMANDS ON`) so clang-tidy/
  clang-analyzer see exact flags.
- Pin the toolchain (compiler version) in CI; build with multiple compilers
  (GCC + Clang, and MSVC if you ship Windows) — each finds different bugs.
- CMake 4.x removed compatibility with policy versions <3.5:
  `cmake_minimum_required(<3.5)` now errors (`CMAKE_POLICY_VERSION_MINIMUM` is
  the escape hatch). Audit legacy subprojects and FetchContent deps for old
  floors before a CMake 4 toolchain bump.

## 1a. Build configurations: Debug, Release, and what NDEBUG means

- **Name the configurations and keep their flags apart.** *Debug*: `-O0` or `-O1`, `-g3`, `-fno-omit-frame-pointer`, `DEBUG` defined and
  `NDEBUG` not; MSVC `/Od`. *Release*: `-O2` (MSVC `/O2`), `NDEBUG` defined, `DEBUG` not, plus
  the hardened set in `rules/04` §5 and §5a. Sanitizer and fuzz builds are further Debug
  variants (§3, §4), never the shipped artifact.
- **Make a mixed or empty configuration fail loudly, or fall back to release.** CMake with no
  `CMAKE_BUILD_TYPE` passes neither `-O` nor `-DNDEBUG` (`rules/04` §5). Default it for
  single-config generators with `if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)` →
  `set(CMAKE_BUILD_TYPE Release CACHE STRING "" FORCE)`. Measured with CMake 3.31.6, the compile
  line then gained `-O3 -DNDEBUG`. In the source, a shared header refuses both at once and treats
  neither as release:
  `#if defined(NDEBUG) && defined(DEBUG)` → `#error`, then
  `#if !defined(NDEBUG) && !defined(DEBUG)` → `#define NDEBUG` followed by `#include <assert.h>`
  again, because `assert` follows the `NDEBUG` in force at each inclusion. Measured with Apple clang
  21: `-DNDEBUG -DDEBUG` stopped at the `#error`, a plain build ran `assert(0)` as a no-op, and
  `-DDEBUG` aborted. The `APP_RELEASE` guard in `rules/04` §5 is the check the release pipeline adds.
- **No "test" configuration that turns private members public** (`-Dprivate=public` and similar).
  The C++ standard forbids a macro named like a keyword ([cpp.replace.general]), and the build
  tests an access model you never ship. Test through the public interface. Where an
  internal really needs a direct test, move it into its own unit with a real interface.
  (`sota-testing` owns test strategy.)
- **Flags must reach every compiled unit.** Plain Make does not rebuild when only the flags change.
  Measured with GNU Make 4.4.1: after a `make CFLAGS=-O0`, `make CFLAGS="-O2 -D_FORTIFY_SOURCE=3"`
  printed "Nothing to be done", so a release can link objects built for debug. Clean between
  configurations, or keep one build directory per configuration. CMake's Makefile and Ninja
  generators both recompiled when `CMAKE_C_FLAGS` changed (measured, CMake 3.31.6).
- **User flags add to the project's, never replace them.** A command-line `make CFLAGS=-O2`
  replaced a Makefile's `CFLAGS += -fstack-protector-strong` outright, while the same value from
  the environment was appended to (measured, GNU Make 4.4.1). Keep hardening in a variable of its own
  and write `override CFLAGS += $(HARDEN_CFLAGS)`, or in Automake use `AM_CFLAGS` (`rules/04` §5).
- **Vendored and bundled libraries get the same hardening.** A third-party tree built by its own
  build system (`ExternalProject_Add`, a vendored Makefile, a prebuilt `.a`) gets none of your
  target's `target_compile_options`. Pass the flags through explicitly (its `CMAKE_ARGS`, its
  `CFLAGS`). Then check the linked result with `checksec`/`annocheck`/BinSkim, since the binary is
  where the flags either arrived or did not. OWASP: C-Based Toolchain Hardening cheat sheet.

## 2. Warnings and static analysis

- Baseline flags: `-Wall -Wextra -Wpedantic -Wconversion -Wsign-conversion
  -Wshadow -Wcast-align -Wnull-dereference -Wdouble-promotion
  -Wimplicit-fallthrough -Werror`. MSVC: `/W4 /permissive- /WX`.
- **A periodic `-Weverything` sweep, never a gate.** Clang's manual advises against building with
  `-Weverything` routinely, since it includes experimental diagnostics and makes compiler upgrades
  painful. So run it as a scheduled, non-blocking job. Triage the output, and promote a warning
  that finds real bugs to the gating set by name. For example, `-Wmissing-prototypes` fired under
  `-Weverything` and not under `-Wall -Wextra` on the same file (Apple clang 21, measured).
- **Suppress at the site, with a reason, not for the whole project.** A project-wide `-Wno-<x>`
  or MSVC `/wd<n>` hides every future instance too. Silence one site instead: C23/C++17
  `[[maybe_unused]]` on an unused parameter, or `#pragma GCC diagnostic push` / `ignored "-W<x>"`
  / `pop` around the few lines, with a comment saying why. A per-file `-Wno-` for generated or
  third-party code is the widest acceptable scope. This is the C/C++ form of Rust's per-site
  `#[allow(..., reason = "...")]`. OWASP: C-Based Toolchain Hardening cheat sheet.
- **clang-tidy** with a curated set is the primary linter:
  `bugprone-*, cppcoreguidelines-*, cert-*, performance-*, modernize-*,
  clang-analyzer-*, misc-*` (tune noisy checks). Commit a `.clang-tidy`.
- **cppcheck** (`--enable=warning,performance,portability`) and the
  **Clang Static Analyzer** (`scan-build` or via clang-tidy) catch path-
  sensitive bugs the compiler misses. Commercial: Coverity, PVS-Studio for
  deeper interprocedural analysis. Do not pass cppcheck `--addon=cert`: 2.21 ships no such
  addon, prints "Did not find addon cert.py" and exits 1 having analysed nothing (measured).
  SEI CERT coverage comes from clang-tidy `cert-*` or a commercial tool.
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
- **One exception: a trap-mode UBSan subset may ship as hardening.** Clang's UBSan docs say its
  full runtime is for testing and may weaken a production executable, and point production at
  trap mode (`-fsanitize-trap=`, no runtime) or the minimal runtime
  (`-fsanitize-minimal-runtime`). A cheap set: `-fsanitize=bounds,signed-integer-overflow
  -fsanitize-trap=bounds,signed-integer-overflow`. Measured on the same overflow-plus-OOB file:
  Apple clang 21 and GCC 15.3 both died with SIGILL (exit 132) and linked no `ubsan` symbol;
  Fedora's Clang 22.1 minimal runtime printed one line per check (`ubsan: add-overflow by
  0x…`); Apple clang 21 does not support the minimal runtime (warned, then failed to link).
  Benchmark it, and list every check of `-fsanitize=` in `-fsanitize-trap=` too. ASan, TSan
  and MSan stay out of production (`rules/04` §5's `#error` guard refuses them at compile time).

## 4. Fuzzing for input parsers

- Any code parsing untrusted bytes (network, file formats, decoders) gets a
  fuzz target: prefer **AFL++** or **FuzzTest**/Centipede for new targets —
  libFuzzer is in maintenance mode (bug fixes only, per the LLVM docs; its
  authors moved to Centipede), though the `-fsanitize=fuzzer` interface and
  existing libFuzzer targets remain supported. Run continuously; enroll
  high-value OSS in [OSS-Fuzz](https://google.github.io/oss-fuzz/).
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
- **Before adding a dependency** (typed by a person or proposed by an AI assistant),
  confirm it is the project you meant, not a lookalike or a name that only sounds right:
  `vcpkg search <name>` lists the ports your baseline actually knows, and
  `conan search <name> -r conancenter` the recipes ConanCenter carries (measured with
  Conan 2.32). A port or recipe is a packaging of an upstream repository, so check that
  the port's source URL points at the upstream you expected, then judge the upstream
  itself: maintainer count and recent commits, release cadence, open advisories, licence.
  deps.dev's package API does not index Conan or vcpkg, but its project endpoint
  (`https://api.deps.dev/v3/projects/github.com%2F<owner>%2F<repo>`) returns the
  repository's OpenSSF Scorecard; the `scorecard --repo=github.com/<owner>/<repo>` CLI
  computes it directly (needs `GITHUB_AUTH_TOKEN`). Record the result in the PR that adds
  the manifest line.
- **A library's insecure defaults become your code's defaults.** Every security-relevant
  option you do not set is a decision the library made for you. Verified examples:
  OpenSSL leaves peer verification at `SSL_VERIFY_NONE` unless `SSL_CTX_set_verify` or
  `SSL_set_verify` changes it (and checks no host name without `SSL_set1_host`);
  libcurl's `CURLOPT_TIMEOUT` defaults to 0, "never times out", and
  `CURLOPT_CONNECTTIMEOUT` to 300 s, so a stalled peer holds the thread; libcurl's
  `CURLOPT_PROTOCOLS_STR` allows every compiled-in scheme (`rules/04` §4). Audit every
  option passed to a library at a trust boundary, and the ones *not* passed.
- **Sample code is not production code.** curl's own `docs/examples/https.c` carries
  `CURLOPT_SSL_VERIFYPEER, 0L` behind `SKIP_PEER_VERIFICATION`; a copied README snippet
  brings its demo switches (verification off, no timeouts, debug logging) with it. Strip
  them on paste. *(OWASP: Vulnerable Dependency Management cheat sheet; Software Supply
  Chain Security cheat sheet; Secure Coding with AI cheat sheet; SCVS V1, V6.)*
- **Treat dependency build scripts as code that runs at install/build time, on the
  developer's machine and the CI runner, with their credentials, before any test.**
  C/C++ has no `--ignore-scripts`: building a dependency from source *is* running its
  build system. Know every execution point:
  - `FetchContent_MakeAvailable` calls `add_subdirectory` on the fetched tree, so the
    dependency's `CMakeLists.txt` (any `execute_process`, `file(DOWNLOAD)`) runs at
    **configure** time. Measured with CMake 4.4: a dependency pinned to a full commit
    hash ran its `execute_process` on a plain `cmake -S . -B build`. Pinning fixes
    *which* code runs, not *whether*.
  - `ExternalProject_Add` runs the dependency's own configure/build/install steps at
    build time; `find_package` in config mode includes the installed
    `<Name>Config.cmake`, which is CMake code too.
  - `CMAKE_PROJECT_TOP_LEVEL_INCLUDES` (CMake 3.24+) injects files at the first
    `project()` call, often from `CMakePresets.json` or a CI command line.
  - vcpkg: each port's `portfile.cmake` is the build script, including any overlay port
    listed under `overlay-ports` in `vcpkg-configuration.json` or passed with
    `--overlay-ports`.
  - Conan: every recipe `conanfile.py` is Python, and hooks are `hook_*.py` files under
    `<CONAN_HOME>/extensions/hooks`. `conan install --build=never` forbids source
    builds but does **not** stop recipe code. Measured with Conan 2.32: module-level
    code in an exported recipe ran under `--build=never`, and the install then failed
    for want of a binary.
- **Controls.** No switch turns this off, so narrow it and review it. Set
  `FETCHCONTENT_TRY_FIND_PACKAGE_MODE=ALWAYS` (3.24+; the default `OPT_IN` only tries
  `find_package` when the declaration passes `FIND_PACKAGE_ARGS`) so a reviewed,
  package-manager-provided build wins over fetching. Use
  `FETCHCONTENT_SOURCE_DIR_<NAME>` to point at a reviewed local checkout.
  `FETCHCONTENT_FULLY_DISCONNECTED` is **not** a control: CMake's docs say it is for use
  only after the first run. On every dependency bump, diff the executed files
  (`CMakeLists.txt`, `*.cmake`, `portfile.cmake`, `conanfile.py`) between the old and
  new pins, not just the C/C++ sources. Put the repo's **own** build-executing files
  (`CMakeLists.txt`, `cmake/`, `CMakePresets.json`, `vcpkg.json`,
  `vcpkg-configuration.json`, overlay ports, `conanfile.*`, CI workflows) under
  CODEOWNERS (or your forge's equivalent) with required review. That applies
  to a change an AI agent authored too.
- **CI placement.** Run dependency resolution and the first configure in a job that has
  no deploy/publish secrets and no write token, or in an isolated job whose output is
  a cached, hashed artifact. Credentials belong only to the later job that needs them.
  Details in `sota-devsecops`. *(OWASP: CI/CD Security cheat sheet; Software Supply
  Chain Security cheat sheet; NPM Security cheat sheet, for the `ignore-scripts`
  analogue.)*

## 6. Reproducible, deterministic builds

- Avoid timestamps/paths leaking into binaries (`-ffile-prefix-map`,
  `SOURCE_DATE_EPOCH`); enable LTO for release (`-flto`) but verify it doesn't
  mask UBSan. Keep debug info (`-g`) and ship split symbols.

## Audit checklist

- [ ] **What has been SILENCED? -- the analyser's escape hatch (ROADMAP 60) clang-tidy (syntax
      from its own docs): NOLINT silences the SAME line, NOLINTNEXTLINE the NEXT one,
      NOLINTBEGIN/END a range whose markers must pair and match. A bare form with no (check)
      list silences EVERY check there. the `|$` is load-bearing: a bare `// NOLINT` at END OF
      LINE has no character after it, so `[^(]` alone silently misses the most common blanket
      form (measured: 1 of 2).** —
      `grep -rn 'NOLINT' --include='*.c' --include='*.cpp' --include='*.h' --include='*.hpp' .`
      ; `grep -rnE 'NOLINT(NEXTLINE|BEGIN)?([^(]|$)' --include='*.cpp' --include='*.h' .` (no
      (check-list) = blanket);
      `grep -rn 'NOLINTBEGIN' . | wc -l ; grep -rn 'NOLINTEND' . | wc -l` (must be equal)
- [ ] **cppcheck: `// cppcheck-suppress <id>` on the line BEFORE the reported line -- and it is
      INERT unless --inline-suppr is passed. Measured with cppcheck 2.21.0: without that flag
      both planted warnings still fired; with it, one was suppressed and the other was NOT,
      because the comment sat above the wrong line. So check the FLAG before reading the
      comments.** —
      `grep -rn 'cppcheck-suppress' --include='*.c' --include='*.cpp' --include='*.h' .` ;
      `err=$(grep -rn 'inline-suppr' --include='CMakeLists.txt' --include='*.cmake' --include='*.yml' --include='*.yaml' . 2>&1 >/dev/null); rc=$?` ;
      `case $rc in 0) ;; 1) echo "cppcheck-suppress comments present but --inline-suppr never passed: every one is decoration" ;; *) echo "SWEEP FAILED, not a finding about their code: $err" ;; esac`
- [ ] **compiler-level, which no lint grep finds** —
      `grep -rn '#pragma GCC diagnostic ignored\|#pragma clang diagnostic ignored\|#pragma warning(disable' --include='*.c' --include='*.cpp' --include='*.h' .`
      ; `grep -rn 'suppressions' CMakeLists.txt *.cmake 2>/dev/null` (cppcheck
      --suppressions-list=)
- [ ] **Warning silenced project-wide, or a pragma with no scope (§2) — MEDIUM** —
      `grep -rnE '(-Wno-[a-z]|/wd[[:space:]]*[0-9])' --include='CMakeLists.txt' --include='*.cmake' --include='Makefile*' --include='*.mk' . | grep -v 'set_source_files_properties'`
      (a global disable: move it to the sites, or to the one generated file) ;
      `grep -rlE 'pragma[[:space:]]+(GCC|clang)[[:space:]]+diagnostic[[:space:]]+ignored' --include='*.c' --include='*.cpp' --include='*.h' --include='*.hpp' . | xargs -r grep -LE 'diagnostic[[:space:]]+push'`
      (a file that ignores a warning with no `push`/`pop`: it stays off for the rest of the unit)
- [ ] **Build configuration: empty build type, a keyword redefined for tests (§1a) — MEDIUM, HIGH
      when it builds the shipped artifact** —
      `grep -rnE '(-D|#[[:space:]]*define[[:space:]]+)(private|protected)[[:space:]=]+public' --include='CMakeLists.txt' --include='*.cmake' --include='Makefile*' --include='*.c' --include='*.cpp' --include='*.h' --include='*.hpp' .` ;
      `err=$(grep -rE 'NOT[[:space:]]+CMAKE_BUILD_TYPE' --include='CMakeLists.txt' . 2>&1 >/dev/null); rc=$?` ;
      `case $rc in 0) ;; 1) echo "no default CMAKE_BUILD_TYPE: an unset one compiles with no -O and no -DNDEBUG" ;; *) echo "SWEEP FAILED, not a finding about their code: $err" ;; esac`
- [ ] **Hardening flags dropped on the way to a unit (§1a) — HIGH on a network-facing binary** —
      `grep -rnE '^[[:space:]]*(C|CXX|CPP|LD)FLAGS[[:space:]]*(\+|:|\?)?=' --include='Makefile' --include='GNUmakefile' --include='*.mk' .`
      (no `override`: a `make CFLAGS=...` on the command line replaces the line) ;
      `grep -rn 'ExternalProject_Add' --include='CMakeLists.txt' --include='*.cmake' .` (read
      whether its `CMAKE_ARGS` pass the hardening flags) ; then `checksec` the linked artifact
- [ ] **Warnings-as-errors and standard pinned?** —
      `grep -rnE 'Werror|/WX' . --include='CMakeLists.txt' --include='*.cmake' --include='Makefile*' || echo "no -Werror"`
      ; `grep -rnE 'CXX_STANDARD|cxx_std_|std=c\+\+' CMakeLists.txt 2>/dev/null`
      ; `grep -nE 'C_STANDARD|c_std_|std=(gnu|c)[0-9]' CMakeLists.txt || echo "C dialect not pinned, unless grep printed an error"`
      (§1: the default moved to `gnu23` in GCC 15 and `gnu++20` in GCC 16)
- [ ] **GCC 14 C errors downgraded (§1) — MEDIUM, HIGH if the code then warns about
      int-conversion or implicit declarations** —
      `grep -rnE -e '-fpermissive|-std=(gnu|c)89' --include='CMakeLists.txt' --include='*.cmake' --include='Makefile*' --include='*.mk' --include='configure.ac' --include='meson.build' .`
- [ ] **UBSan in a production build is trap-only or minimal-runtime (§3) — HIGH for ASan, TSan
      or MSan in the shipped artifact** —
      `grep -rnE -e '-fsanitize=' --include='CMakeLists.txt' --include='*.cmake' --include='CMakePresets.json' --include='Makefile*' --include='*.mk' . | awk '/fsanitize=([a-z-]+,)*(address|thread|memory|leak|hwaddress|kernel-address)([^a-z-]|$)/ || !/fsanitize-trap=|fsanitize-minimal-runtime/'`
      (prints every line whose `-fsanitize=` list names a runtime sanitizer — even beside a
      trap flag, which covers only UBSan — plus any UBSan line with neither trap nor minimal
      runtime. Each line left: is it the release configuration? then it ships a sanitizer runtime)
- [ ] **clang-tidy / clang-format / cppcheck configs present?** —
      `ls .clang-tidy .clang-format 2>/dev/null | grep -q . || echo "missing lint/format config"`
      ; `test -f compile_commands.json || grep -rn EXPORT_COMPILE_COMMANDS CMakeLists.txt`
- [ ] **Sanitizer & fuzzing jobs in CI?** —
      `err=$(grep -rniE 'fsanitize|asan|ubsan|tsan|libfuzzer|oss-fuzz|scan-build' --include='*.yml' --include='*.yaml' --include='Jenkinsfile' . 2>&1 >/dev/null); rc=$?` ;
      `case $rc in 0) ;; 1) echo "no sanitizer/fuzz job in CI config — HIGH for input-parsing code" ;; *) echo "SWEEP FAILED, not a finding about their code: $err" ;; esac`
- [ ] **Dependency manager + lockfile?** —
      `ls vcpkg.json conan.lock conanfile.* 2>/dev/null | grep -q . || echo "no pinned dependency manifest/lockfile"`
      ;
      `grep -rni 'FetchContent\|ExternalProject\|git submodule' CMakeLists.txt .gitmodules 2>/dev/null`
      (verify pinning)
- [ ] **Fetched sources verified, and dependencies scanned (§5) — HIGH for a shipped
      binary** —
      `grep -rnE 'URL[[:space:]]+[^[:space:]]*(https?|ftp)://' --include='CMakeLists.txt' --include='*.cmake' .`
      against `grep -rn 'URL_HASH' --include='CMakeLists.txt' --include='*.cmake' .` (a `URL`
      download with no `URL_HASH`: CMake's ExternalProject docs call the hash "strongly
      recommended ... as it ensures the integrity of the downloaded content") ;
      `grep -rnE 'GIT_TAG[[:space:]]+[^[:space:])]+' --include='CMakeLists.txt' --include='*.cmake' . | grep -vE 'GIT_TAG[[:space:]]+[0-9a-f]{40}'`
      (a branch or tag, not a commit: the same docs prefer the hash, and an omitted `GIT_TAG`
      defaults to `master`) ;
      `grep -rniE 'osv-scanner|dependency-track|grype|trivy|cyclonedx|spdx' --include='*.yml' --include='*.yaml' .`
      (no CVE-scan or SBOM step at all leaves §5 unenforced. OSV-Scanner's own table lists
      `conan.lock` for C/C++, plus commit-level scanning of submoduled or vendored code, and
      no vcpkg lockfile)
- [ ] **New dependency: selection recorded, and the library's insecure defaults
      overridden (§5) — HIGH for a TLS context with no verify mode, MEDIUM for a curl
      handle with no transfer timeout** —
      `git diff "$BASE" -- vcpkg.json 'conanfile.*' | grep -E '^\+[^+]'` (each added or reformatted
      line needs a selection note: exact name, upstream, Scorecard) ;
      `grep -rlE 'SSL_CTX_new' --include='*.c' --include='*.cpp' --include='*.cc' . | xargs -r grep -LE 'SSL_(CTX_)?set_verify'`
      (OpenSSL's default is `SSL_VERIFY_NONE`) ;
      `grep -rlE 'curl_easy_init' --include='*.c' --include='*.cpp' --include='*.cc' . | xargs -r grep -LE 'CURLOPT_(TIMEOUT|LOW_SPEED_TIME)'`
      (libcurl's transfer timeout defaults to never; each hit is a file to read)
- [ ] **Dependency code that runs at build time (configure/install) is inventoried and
      owner-reviewed (§5) — HIGH if these files have no CODEOWNERS entry, since a
      dependency bump or an agent-authored edit then executes unreviewed on CI** —
      `grep -rnE 'FetchContent_MakeAvailable|FetchContent_Populate|ExternalProject_Add|CMAKE_PROJECT_TOP_LEVEL_INCLUDES|overlay-ports' --include='CMakeLists.txt' --include='*.cmake' --include='CMakePresets.json' --include='vcpkg-configuration.json' .`
      (each hit: diff the fetched tree's build files on every bump) ;
      `find . -name conanfile.py -not -path './build/*'` (Python that runs on every
      `conan install`, even with `--build=never`) ;
      `cat .github/CODEOWNERS CODEOWNERS docs/CODEOWNERS 2>/dev/null | grep -qE 'CMakeLists|\.cmake|conanfile|vcpkg' || echo "no CODEOWNERS entry for build-executing files"`
- [ ] **Global (non-target) CMake anti-patterns — LOW/MEDIUM** —
      `grep -rnE 'include_directories\(|link_libraries\(|^set\(CMAKE_CXX_FLAGS' CMakeLists.txt 2>/dev/null`