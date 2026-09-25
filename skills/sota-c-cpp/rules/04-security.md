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
- **`assert()` is compiled out by `-DNDEBUG`** — verified: a program whose
  `assert(x > 0)` aborted in a normal build printed `passed` when rebuilt with
  `-DNDEBUG`, which release presets set by default — CMake's
  `Modules/Compiler/GNU.cmake` appends `-DNDEBUG` to the `RELEASE`,
  `RELWITHDEBINFO` **and** `MINSIZEREL` init flags, so every non-Debug build type
  strips them. A bounds or validation check written as `assert`
  therefore does not exist in the shipped binary. Use an explicit `if` that
  returns/aborts, or a hardened contract macro that survives release flags; keep
  `assert` for impossible internal states. Class: `sota-code-security` rules/11 §4.
- **Unsafe parsing of untrusted structured input (deserialization).** Never cast or
  `memcpy` a wire buffer straight into a struct: padding, alignment, endianness and every
  length field arrive attacker-controlled, and the cast is also a strict-aliasing violation.
  Decode field by field against the remaining length, or use a generated parser with its own
  checks (protobuf; FlatBuffers only after its `Verifier` accepts the buffer). **XML through
  libxml2:** never pass `XML_PARSE_NOENT` (substitute entities) or `XML_PARSE_DTDLOAD` (load
  the external subset) on untrusted input, and add `XML_PARSE_NONET`. The flag never has to
  appear at the call: `xmlCtxtUseOptions` sets it on a context, and the deprecated process-wide
  `xmlSubstituteEntitiesDefault(1)` turns substitution on for every later parse. Measured with
  libxml2 2.12.10: after that call, `xmlReadMemory(..., 0)` with no options expanded an external
  entity into the document. Never set it, or the `xmlLoadExtDtdDefaultValue` global. OWASP XXE
  Prevention cheat sheet; the same trap as PHP's `LIBXML_NOENT`.
- **Resource limits / DoS guards on every parser and decoder.** Cap recursion depth (a
  max depth on recursive-descent parsers, or stack exhaustion is one nested input away),
  element and attribute counts, total bytes allocated per message, and the decompressed size
  of any inflate/uncompress output (meter it while streaming; the header's claimed size is
  input too). Never pass `XML_PARSE_HUGE` on untrusted input: libxml2 documents it as
  relaxing every hardcoded parser limit. OWASP XML Security cheat sheet (coercive parsing,
  quadratic blowup).

## 3. Format-string and injection

- **Never** pass user data as the format string: `printf(user)` is a
  format-string vuln (read/write via `%n`). Use `printf("%s", user)`. Compile
  with `-Wformat -Wformat=2 -Werror=format-security` to catch it.
- **Logs carry neither secrets nor raw input.** C has no standard logger, so every
  `syslog`/`fprintf(stderr, ...)` call site is the control: never pass a credential, key or
  token to it, and neutralise CR/LF in any external string before it is logged (CWE-117,
  *Improper Output Neutralization for Logs*): a forged line in a syslog-fed pipeline is an
  audit-trail defect. The user-controlled *format* is the bullet above.
- **Command injection**: don't build shell strings. Use `posix_spawn`/`execve`
  with an explicit argument vector and no shell; never `system("cmd " + input)`.
- **SQL/other injection**: parameterized queries / prepared statements only
  (the DB client API), never string-concatenated SQL — see `sota-databases`.
  In the C client APIs the unsafe call is the one that takes a whole statement
  string: `sqlite3_exec` (a convenience wrapper that runs a string), libpq
  `PQexec`, MySQL `mysql_query`/`mysql_real_query`. The safe forms bind values
  separately: `sqlite3_prepare_v2` + `sqlite3_bind_*`, `PQexecParams`/
  `PQprepare`, `mysql_stmt_prepare` + `mysql_stmt_bind_param`. SQLite's own
  printf escapes only with `%q`/`%Q`/`%w`. A `%s` in `sqlite3_mprintf` is
  plain interpolation.
- **Dynamic code evaluation from external input.** C and C++ have no `eval`, so runtime code
  generation arrives through an embedded interpreter or a lookup by name: Lua
  `luaL_dostring`/`luaL_loadstring`/`luaL_loadbuffer`, CPython `PyRun_SimpleString`, an embedded
  JavaScript engine's eval entry point, `dlsym(handle, name)` with `name` taken from input (the C
  form of reflection), or source written to disk, compiled and `dlopen`ed. Never let input reach
  any of them. Map input to behaviour through a fixed dispatch table
  (`std::unordered_map<std::string_view, handler>`, a `switch` over an `enum class`), or parse it
  with a small expression grammar you own that evaluates only the operators you list. If a
  third-party script really must run, an embedded interpreter is **not a security boundary**: it
  shares your address space, so one interpreter bug is memory corruption in your process. Run it
  in a separate sandboxed process (`sota-sandboxing`). Lua specifics, read in the Lua sources:
  `luaL_openlibs` opens `io`, `os` (`os.execute`) and `package` (native-library loading), so open
  only the libraries a script needs. A NULL load mode means `"bt"`, which accepts precompiled
  binary chunks, and the manual warns that Lua "does not check the consistency of binary chunks"
  and that such chunks "can crash the interpreter". Pass `"t"` to `luaL_loadbufferx`.
  `luaL_loadbuffer` always passes NULL. `luaL_loadstring`, and so `luaL_dostring`, passes NULL up
  to 5.5.0 and `"t"` from 5.5.1. OWASP: Code Review Guide; Proactive Controls 2024 C3; ASVS 5.0 V1.3.
- **Regex as a control (validation, allowlist, routing, redaction): escaping, anchoring,
  bounds, engine.** For untrusted input prefer RE2: it guarantees match time linear in the
  input and rejects backreferences and general lookaround rather than backtrack.
  - **Escaping.** Neither libc++ nor libstdc++ ships an escape function for `std::regex`,
    and POSIX `regcomp` has none, so never splice input into those patterns. RE2 has
    `RE2::QuoteMeta(s)`. PCRE2 can take the whole pattern as a literal with
    `PCRE2_LITERAL` (10.30+), or wrap a fragment in `\Q...\E`, which a `\E` inside the
    input closes, so strip or reject it first.
  - **Anchoring.** Validate with a whole-input API: `std::regex_match` (not
    `regex_search`), `RE2::FullMatch` (not `PartialMatch`), or PCRE2 with `PCRE2_ANCHORED |
    PCRE2_ENDANCHORED` (10.30+). POSIX `regexec` finds a match anywhere, so write `^...$`.
    Traps: PCRE2's `$` also matches before a final newline unless `PCRE2_DOLLAR_ENDONLY`
    is set (`"abc\n"` passes `^[a-z]+$`), and `std::regex::multiline` or
    `PCRE2_MULTILINE` turn `^`/`$` into line anchors, so a search accepts `"ok\nBAD"`.
  - **Bounds.** Cap the input length before matching and write bounded repeats
    (`{1,64}`, not `+`). Check `RE2::ok()` after construction and cap compiled size with
    `RE2::Options::set_max_mem` when the pattern itself is untrusted.
  - **Engine.** `std::regex` backtracks: measured on libstdc++ (GCC 16), `(a+)+$` over
    24 `a`s plus `!` took 2.3 s, quadrupling per two characters. libc++ instead throws
    `std::regex_error` with `error_complexity`, which is still an outage if uncaught.
    PCRE2 backtracks too: pass a `pcre2_match_context` with `pcre2_set_match_limit` and
    `pcre2_set_depth_limit` (never a NULL context on untrusted input) and treat
    `PCRE2_ERROR_MATCHLIMIT` as a rejection. Moving a pattern from RE2 to PCRE2 or
    `std::regex` to get a backreference or lookaround gives up the linear-time
    guarantee. Rewrite the check in code instead. OWASP: Input Validation cheat sheet;
    OWASP Proactive Controls 2024 C3; ASVS 5.0 V1.2.9; OWASP Go-SCP (validation).
- **SSRF: outbound requests to a caller-influenced destination** (policy:
  `sota-code-security` rules/01 §5; this is the libcurl idiom). Best: accept a host key or ID
  and look the URL up in your own allowlist, never forward a caller URL. If a URL must be
  taken, parse it once with the URL API curl itself uses (`curl_url_set` →
  `curl_url_get(..., CURLUPART_HOST, ...)`, hand the same `CURLU*` over via `CURLOPT_CURLU`)
  so the host you checked is the host curl connects to. Then:
  - **Check the dialled address, not the name.** Install `CURLOPT_OPENSOCKETFUNCTION`: its
    `struct curl_sockaddr *` argument is the resolved peer address libcurl is about to
    connect to, so a DNS-rebinding answer cannot slip past a check made earlier. Inspect
    `addr` by `family` and return `CURL_SOCKET_BAD` for loopback (127/8, `::1`), RFC 1918 and
    ULA `fc00::/7`, link-local (169.254/16 — the metadata endpoint `169.254.169.254` —
    and `fe80::/10`), `0.0.0.0/8` and `::`, multicast, and any IPv6 address carrying an IPv4
    one (`::ffff:a.b.c.d`: test the embedded IPv4). libcurl then treats that address as a
    failed connection and tries the next one, so every candidate passes the same check.
    Reject the metadata *hostnames* your cloud documents before the request is built.
  - **IP literals:** validate with `inet_pton`, never `inet_aton`/`inet_addr`, which accept
    octal, hex, dword and short forms (`0x7f.0.0.1`, `2130706433` and `127.1` all read as 127.0.0.1).
    `inet_pton` is not uniform either: glibc rejects `0177.0.0.1`, macOS libc accepts it as
    *decimal* 177.0.0.1 while `inet_aton` reads it as 127.0.0.1 — one more reason the socket
    callback, not a string check, is the control.
  - **Redirects:** `CURLOPT_FOLLOWLOCATION` defaults to 0; keep it off and re-validate each
    `Location` yourself. If you enable it, the socket callback still vets every new
    connection, and set `CURLOPT_REDIR_PROTOCOLS_STR` to `"https"` (its default also
    allows HTTP, FTP and FTPS) with a `CURLOPT_MAXREDIRS` cap.
  - **Schemes:** `CURLOPT_PROTOCOLS_STR` (7.85.0+; the default is every protocol the build
    supports, which can include `file`, `gopher` and `dict`) set to `"https"`. On older libcurl use the
    deprecated `CURLOPT_PROTOCOLS` bitmask. OWASP: SSRF Prevention, .NET Security and GraphQL cheat sheets.
- **Path traversal / TOCTOU** (CERT FIO): canonicalize with
  `std::filesystem::weakly_canonical`/`realpath` and verify the result stays
  under an allowed root; prefer `openat`/`O_NOFOLLOW` and operate on fds to
  avoid check-then-use races on the path.
- **Cookies the application sets itself.** The session cookie is covered in `sota-code-security`
  rules/17. This bullet is for every other cookie. Defaults, read in each framework's source:
  Drogon's `drogon::Cookie` (sent with `resp->addCookie(key, value)` or `addCookie(cookie)`)
  starts with `HttpOnly` on and `Secure` off, and writes no `SameSite`, `Path` or `Domain` until
  you set them. Its `SameSite::kNone` adds `Secure` by itself. Crow's `CookieParser`
  (`ctx.set_cookie(k, v)`) starts with every attribute off, and its `SameSitePolicy::None` does
  **not** add `Secure`, which browsers require for `SameSite=None`. cpp-httplib has no cookie
  builder, so `res.set_header("Set-Cookie", ...)` is a string you assemble, attributes included.
  Set every attribute explicitly: `Secure`, `HttpOnly` unless script must read the value,
  `SameSite=Lax` or `Strict`, and `Path=/` (Drogon: `setSecure(true)`, `setHttpOnly(true)`,
  `setSameSite(Cookie::SameSite::kLax)`, `setPath("/")`. Crow: `.secure().httponly().path("/")
  .same_site(...)`). Browsers treat an omitted `SameSite` differently (some default to `Lax`), so
  never rely on it. Prefer a `__Host-` name, because the browser then rejects the cookie unless it
  is `Secure`, has `Path=/` and has no `Domain`, so a sibling subdomain cannot set or shadow it.
  OWASP: Session Management cheat sheet; Cookie Theft Mitigation cheat sheet; ASVS 5.0 V3.3.

## 4. Cryptography and randomness

- **Never** use `rand()`/`random()`/`std::mt19937` for security
  (keys, tokens, IVs, salts) — they're predictable. Use the OS CSPRNG:
  `getrandom(2)` / `arc4random_buf` / `BCryptGenRandom`, or a vetted library
  (libsodium, OpenSSL `RAND_bytes`). `std::random_device` is *not* guaranteed
  cryptographic and may be deterministic on some libs.
- Don't roll your own crypto or protocols; use libsodium/OpenSSL/BoringSSL.
  Constant-time compare for secrets (`sodium_memcmp`, `CRYPTO_memcmp`), never
  `memcmp` on a MAC/token (timing leak). See `sota-code-security` rules/04.
- **TLS / transport verification (client side).** OpenSSL: `SSL_CTX_set_verify` with
  `SSL_VERIFY_PEER`, the expected host set with `SSL_set1_host` (the chain alone does not
  check the name), and after the handshake require **both** `SSL_get_verify_result() ==
  X509_V_OK` **and** a non-NULL `SSL_get1_peer_certificate()`. The OpenSSL man page is
  explicit that a peer that presents **no certificate** also yields `X509_V_OK`, "it does
  however not indicate success". libcurl: `CURLOPT_SSL_VERIFYPEER` and
  `CURLOPT_SSL_VERIFYHOST` are never set to 0. Pinning, when used, is checked in addition to
  chain validation, never instead of it: compare the pin against that same non-NULL peer
  certificate (or inside the `SSL_CTX_set_verify` callback), and shut the connection down before
  any application data is sent when either check fails. OWASP Pinning cheat sheet.
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
-Wl,-z,noexecstack -Wl,-z,nodlopen          # non-exec stack; no dlopen (shared objects only)
-Wtrampolines                               # warn when GCC generates a trampoline
```

- **What some older flag lists add, and what it really does** (measured with GCC 16.2, binutils
  2.44, glibc 2.41). `-Wl,-z,nodump` only sets `DF_1_NODUMP`, which marks the object for
  Solaris `dldump`. glibc exports no `dldump`, so nothing on Linux reads it: do not count it as
  hardening. `-z nodlopen` set `NOOPEN` on a shared object but not on a PIE executable, where
  `FLAGS_1` showed only `PIE`. `-Wstrict-overflow` is documented by GCC as doing nothing, and
  `=5` gave no warning on a textbook `x + 1 < x`, so it is not a detector (use the `rules/03` §2
  helpers). `-Wtrampolines` did fire on a nested function whose address was taken.
- **Stack canaries: `-strong` is the baseline, `-all` the exception.** GCC's manual:
  `-fstack-protector-strong` guards every function with a local array or a local whose address
  is taken, and `-fstack-protector-all` guards every function, including ones with nothing an
  overflow could reach. Use `-all` only where its cost on every call is irrelevant and an
  unexpected overflow is catastrophic, e.g. a small setuid helper. Elsewhere the extra checks guard
  functions that hold no buffer.
- **Speculative-execution (Spectre v2) mitigations, for code that crosses a privilege boundary**
  (a hypervisor, a sandbox broker, a process holding another tenant's secrets). GCC:
  `-mindirect-branch=thunk -mfunction-return=thunk`. Clang: `-mretpoline`, plus
  `-mfunction-return=thunk-extern`. Every indirect call and every return then goes through a
  thunk, a cost paid on each one, so benchmark before you adopt it. They conflict with the
  baseline above: GCC 16.2 refused `-mindirect-branch=thunk` beside `-fcf-protection=full` with
  "are not compatible" (measured). Its manual allows `thunk-extern` with
  `-fcf-protection=branch`, where you provide the thunks yourself. Choose per binary.
  OWASP: C-Based Toolchain Hardening cheat sheet.
- libc++ builds: production uses hardening mode FAST
  (`-D_LIBCPP_HARDENING_MODE=_LIBCPP_HARDENING_MODE_FAST`, cheap checks); the
  EXTENSIVE mode (`rules/02`) is for debug/test builds.
- Add `-fsanitize=address,undefined` to the *debug/test* build (not prod).
  Consider `-fhardened` (GCC 14+) as a shorthand umbrella — verify your
  compiler version supports it; `gcc --help=hardened` lists what it turns on.
- **Verify the shipped binary, not the build file.** A flag written down is not a flag that
  reached the compiler. Toolchain defaults are a vendor choice: measured on Fedora's GCC 16, a
  plain `gcc -O2` produced a non-PIE binary with partial RELRO, no canary and no FORTIFY, because
  that distribution hardens through its packaging flags, not the compiler (inspect
  `gcc -dumpspecs` or compile a probe rather than assume). Build systems also discard flags: an
  Automake `Makefile.am` that assigns `CFLAGS = -O0` (the user variable, where `AM_CFLAGS`
  belongs) replaced the `CFLAGS` given to `./configure`, hardening flags included, and silent
  rules (`AM_SILENT_RULES`) hid the compile line until `make V=1`. Read the real command
  (`make V=1`, or the `compile_commands.json` that `-DCMAKE_EXPORT_COMPILE_COMMANDS=ON` writes), then check each artifact with `checksec
  --file=BIN` or `annocheck BIN`, or `readelf`: type `DYN` (PIE), a `GNU_RELRO` segment plus
  `BIND_NOW` (full RELRO), `__stack_chk_fail` (canary) and `__*_chk` imports (FORTIFY). OWASP:
  C-Based Toolchain Hardening cheat sheet.
- **Debug mode in production: C/C++ has no dev server, so the "debug mode" is the build.**
  An empty `CMAKE_BUILD_TYPE`, a `Debug` build, `-fsanitize=*` or `-D_GLIBCXX_DEBUG` must never
  produce the artifact you ship. Measured with CMake 4.4.3: with no `CMAKE_BUILD_TYPE` the
  compile line carried neither `-O` nor `-DNDEBUG`, so the shipped binary is unoptimised
  and every `assert` stays live. Check it at compile time, not by habit. The release pipeline
  passes its own `-DAPP_RELEASE=1`. Do not derive it from the build type, which is the thing
  being checked. The source then refuses a debug or sanitizer build:
  `#if defined(APP_RELEASE) && (!defined(NDEBUG) || defined(APP_ASAN))` → `#error`, with
  `APP_ASAN` defined from `__SANITIZE_ADDRESS__` (GCC documents it for `-fsanitize=address`)
  **or** `__has_feature(address_sanitizer)`, behind a `defined(__has_feature)` guard. Test both
  because Apple clang 21 with `-fsanitize=address` set only the second (measured). OWASP: Error
  Handling cheat sheet; Secure Headers Project; ASVS 5.0 V13.4.
- Treat warnings as errors (`-Werror`) in CI; a clean `-Wall -Wextra` is the
  floor, not the ceiling — also run a static analyzer (`rules/06`).

## 5a. Windows / MSVC binary hardening

```
cl   /O2 /GS /sdl /guard:cf ...                               # compiler
link /DYNAMICBASE /HIGHENTROPYVA /NXCOMPAT /CETCOMPAT /GUARD:CF   # linker
```

Defaults, from Microsoft's option pages: `/GS`, `/DYNAMICBASE` (ASLR) and `/NXCOMPAT` (DEP) are on,
and so is `/HIGHENTROPYVA` for 64-bit images, where it takes effect only with `/DYNAMICBASE`. On
these the finding is an opt-out: `/GS-`, `/DYNAMICBASE:NO`, `/NXCOMPAT:NO`, `/HIGHENTROPYVA:NO`.
Two are **off** by default and must be added. `/sdl` is a superset of `/GS`: it turns on strict
`/GS` mode, clears some pointers after `delete`, and makes security warnings such as C4996 (a
deprecated unsafe CRT call) and C4700 (an uninitialised local) errors. `/guard:cf` (Control Flow
Guard) needs `/DYNAMICBASE`, and needs `/GUARD:CF` at link too when you compile and link in
separate steps. It protects only the code compiled with it, and does not work with `/ZI` or
`/clr`. `/CETCOMPAT` marks an x64 image as compatible with the CET shadow stack (VS 2019+).
Without `/sdl`, put `#pragma strict_gs_check(push, on)` in the files that parse untrusted input,
so every function there gets a cookie, not only the ones `/GS` treats as holding a buffer.
**Verify the binary**: `dumpbin /headers /loadconfig app.exe` (CFG shows `Guard` and
`CF Instrumented`), or BinSkim (`binskim analyze app.exe --output r.sarif`). BinSkim's rules
include BA2008 CFG, BA2009 ASLR, BA2011 stack protection, BA2015 high-entropy VA, BA2016 NX,
BA2025 shadow stack and BA2026 `/sdl`, and it reads ELF too. At deployment, add process
mitigations the binary cannot set itself with `Set-ProcessMitigation -Name app.exe -Enable
<list>` or an Exploit Protection XML (`-PolicyFilePath`). Where a mitigation has an `Audit*`
twin (`AuditDynamicCode` for `BlockDynamicCode`), run the audit form first and read what it logs.
OWASP: C-Based Toolchain Hardening cheat sheet.

## 6. Memory-safety strategy (the meta-control)

- Where feasible, move new untrusted-input-parsing code to a memory-safe
  language (Rust), or isolate the C/C++ parser (sandbox/seccomp, separate
  process) — see `sota-sandboxing`. CISA/NSA and the OpenSSF now treat "C/C++
  for new attack-surface code" as a risk decision, not a default.
- Use `std::span`/`std::string_view`/containers instead of pointer+length
  everywhere they fit; enable libc++/libstdc++ hardened mode (`rules/02`).

## 7. Relinquishing privileges (POSIX daemons and setuid programs)

A process that starts as root and drops to a service account can keep root in
three ways, and each one leaves the program running normally:

- **Order.** Drop supplementary groups first, then the group ID, then the user
  ID: `setgroups`/`initgroups` → `setgid` → `setuid`. After the user ID is
  gone, the process no longer has the privilege to change its groups, so a
  group ID dropped *after* it stays privileged (CERT POS36-C).
- **Check every return.** The Linux `setuid(2)` page: *"there are cases where
  setuid() can fail even when the caller is UID 0; it is a grave security error
  to omit checking for a failure return from setuid()"*. A failed drop that is
  not checked leaves the program running as root. Abort on failure.
- **Prove the drop is permanent.** `seteuid(getuid())` is a *temporary* drop:
  the saved set-user-ID still holds root, and `seteuid(0)` restores it. After a
  permanent drop, try `setuid(0)` and abort if it *succeeds* (CERT POS37-C).

```c
/* BAD: uid first (gid now cannot be dropped), nothing checked */
setuid(pw->pw_uid);
setgid(pw->pw_gid);

/* GOOD: groups, gid, uid, each checked, then prove root is gone */
if (initgroups(pw->pw_name, pw->pw_gid) != 0 || setgid(pw->pw_gid) != 0 ||
    setuid(pw->pw_uid) != 0)
    abort();
if (setuid(0) != -1)
    abort();
```

Where the process only needs one capability, prefer dropping to capabilities or
a sandbox over running as root at all (`sota-sandboxing`).

## Audit checklist

- [ ] **Banned functions — HIGH/CRITICAL** —
      `grep -rnwE '(gets|strcpy|strcat|sprintf|vsprintf|stpcpy|scanf|system|popen|strtok|atoi|atol)' --include='*.c' --include='*.cpp' --include='*.h' .`
      ; `grep -rnE '\balloca\b|\[[^]]*\] *= *\{?' --include='*.c' .` (VLA/alloca on dynamic
      size)
- [ ] **Validation at the boundary (§2) — HIGH where the value is a length, count or offset
      from input** —
      `grep -rnE 'assert[[:space:]]*\([^;]*(len|size|count|offset|idx|index)[a-z_]*[[:space:]]*[<>]' --include='*.c' --include='*.cpp' --include='*.h' .`
      (a bounds check written as `assert`: gone in every non-Debug CMake build type, §2) ;
      `grep -rnE '(memcpy|memmove|malloc|calloc)[[:space:]]*\([^;]*(hdr|header|pkt|packet|msg|frame|rec)(->|\.)[a-z_]*(len|size|count)' --include='*.c' --include='*.cpp' .`
      (an embedded length field used straight from parsed input: find its cap against the
      remaining buffer)
- [ ] **Unsafe parsing of untrusted input (§2) — HIGH, CRITICAL for XXE on reachable input** —
      `grep -rnE '\(\s*(const\s+)?struct\s+[a-z_0-9]+\s*\*\s*\)\s*\(?(buf|data|pkt|packet|msg|payload|frame|in)' --include='*.c' --include='*.cpp' --include='*.h' .`
      (a wire buffer cast straight to a struct pointer: find the field-by-field decoder that
      should replace it) ; `grep -rnE 'XML_PARSE_(NOENT|DTDLOAD)|xml(ThrDef)?(SubstituteEntitiesDefault(Value)?|LoadExtDtdDefaultValue)[[:space:]]*(\(|[|]?=)[[:space:]]*[^0=[:space:]]' --include='*.c' --include='*.cpp' --include='*.h' .`
      (entity substitution or external-subset loading on a libxml2 read, through a flag, a
      context or a process-wide default set to anything but 0)
- [ ] **Resource limits / DoS guards (§2) — HIGH where input is untrusted** —
      `grep -rnE 'XML_PARSE_HUGE|\b(inflate|uncompress|BZ2_bzDecompress|ZSTD_decompress)[[:space:]]*\(' --include='*.c' --include='*.cpp' --include='*.h' .`
      (every hit needs a visible output-size cap; `XML_PARSE_HUGE` on untrusted input is the
      finding) ; and read each recursive parser for its max depth
- [ ] **TLS / transport verification (§4) — CRITICAL when a peer certificate is never checked** —
      `grep -rnE 'SSL_VERIFY_NONE|CURLOPT_SSL_VERIFY(PEER|HOST)[^;]*,[[:space:]]*0L?[[:space:]]*\)|SSL_get_verify_result' --include='*.c' --include='*.cpp' --include='*.h' .`
      (verification disabled, or a verify-result check that must be paired with a non-NULL
      `SSL_get1_peer_certificate()`, §4) ;
      `grep -rlE 'SSL_get_verify_result[[:space:]]*\(' --include='*.c' --include='*.cpp' --include='*.cc' --include='*.h' --include='*.hpp' . | xargs -r grep -LE 'SSL_get1?_peer_certificate[[:space:]]*\('`
      (a file that reads the verify result and never fetches the peer certificate: a peer
      that sent none passes as `X509_V_OK`)
- [ ] **Format string — CRITICAL (user-controlled fmt)** —
      `grep -rnE '(printf|fprintf|snprintf|syslog|err|warn)\s*\([^,"]*\)' --include='*.c' --include='*.cpp' .`
- [ ] **build with: -Wformat=2 -Werror=format-security**
- [ ] **Secrets reaching logs (§3) — HIGH** —
      `grep -rniE '(syslog|fprintf[[:space:]]*\([[:space:]]*stderr|spdlog::[a-z]+|LOG\([A-Z]+\))[^;]*(passw|secret|token|api_?key|private_?key|credential)' --include='*.c' --include='*.cpp' --include='*.cc' --include='*.h' --include='*.hpp' .`
      (read the arguments: a credential passed to the call is the finding, while message text
      that only names one also matches)
- [ ] **Command/path injection, TOCTOU — HIGH/CRITICAL** —
      `grep -rnE 'system\(|popen\(|exec[lv]p?\(' --include='*.c' --include='*.cpp' .` ;
      `grep -rnE 'fopen|open\(|realpath|access\(' --include='*.c' --include='*.cpp' .`
      (check-then-use races)
- [ ] **Dynamic code evaluation from external input: embedded interpreter or by-name symbol
      lookup (§3) — CRITICAL where request data reaches it, HIGH for a Lua load with no `"t"`
      mode** —
      `grep -rnE '(luaL_(dostring|dofile|loadstring|loadbuffer|loadbufferx|loadfilex?)|lua_load|PyRun_[A-Za-z]+|Py_CompileString|dlsym)[[:space:]]*\(' --include='*.c' --include='*.cpp' --include='*.cc' --include='*.h' --include='*.hpp' .`
      (trace each argument back to its source. A `dlsym` name or a chunk derived from input is the
      finding. Also check for a Lua mode other than `"t"`, and for `luaL_openlibs` in place of
      the few libraries the script needs)
- [ ] **SQL built as a string (§3) — HIGH/CRITICAL where input reaches it** —
      `grep -rnE '(sqlite3_exec|PQexec|mysql_(real_)?query)[[:space:]]*\(' --include='*.c' --include='*.cpp' .`
      (a whole-statement API: read how the string was built);
      `grep -rnE 'sqlite3_v?s?n?mprintf[[:space:]]*\([^;]*%s' --include='*.c' --include='*.cpp' .`
      (`%s` into SQL is unescaped; `%q`/`%Q` are the escaping forms)
- [ ] **Regex escaping, anchoring and engine choice (§3) — HIGH where the regex is a security
      control or untrusted input reaches a backtracking engine** —
      `grep -rnE '(std::)?regex_search[[:space:]]*\(|RE2::PartialMatch[[:space:]]*\(|std::w?regex([[:space:]]+[a-z_0-9]+)?[[:space:]]*[({]([[:space:]]*[^"R)}[:space:]]|[^;]*"[[:space:]]*\+)|regcomp[[:space:]]*\([^,]*,[[:space:]]*[^",[:space:]]|pcre2_match[[:space:]]*\([^;]*,[[:space:]]*(NULL|nullptr|0)[[:space:]]*\)' --include='*.c' --include='*.cpp' --include='*.cc' --include='*.h' --include='*.hpp' .`
      (a partial match used as validation, a pattern built from a variable with no
      `RE2::QuoteMeta`, or PCRE2 with no match-limit context). Then read each surviving
      pattern for `^...$` on POSIX, `PCRE2_DOLLAR_ENDONLY`/`PCRE2_ENDANCHORED`, multiline flags,
      bounded repeats and a length cap before `std::regex` sees untrusted input
- [ ] **SSRF: outbound request to an internal address or the 169.254.169.254 metadata endpoint
      (§3) — HIGH, CRITICAL where a caller-supplied URL reaches cloud metadata** —
      `grep -rnE 'CURLOPT_FOLLOWLOCATION[^;]*,[[:space:]]*(1L?|CURLFOLLOW_[A-Z]+)[[:space:]]*\)|inet_(aton|addr)[[:space:]]*\(' --include='*.c' --include='*.cpp' --include='*.cc' --include='*.h' --include='*.hpp' .`
      (redirects followed, or a lenient IP parser used for a check) ; then
      `grep -rlE 'CURLOPT_(URL|CURLU)' --include='*.c' --include='*.cpp' --include='*.cc' . | xargs -r grep -L 'CURLOPT_OPENSOCKETFUNCTION'`
      (a file that sets a URL with no connect-time address check: read whether the destination
      is caller-influenced, and look for `CURLOPT_PROTOCOLS_STR` beside it)
- [ ] **App-set cookie attribute defaults: Secure flag, HttpOnly, SameSite, Path (§3) — HIGH
      for a cookie that carries an identifier or preference used for authorisation, MEDIUM
      otherwise** —
      `grep -rlE 'addCookie[[:space:]]*\(|set_cookie[[:space:]]*\(|"Set-Cookie"' --include='*.c' --include='*.cpp' --include='*.cc' --include='*.h' --include='*.hpp' . | xargs -r grep -LE 'setSecure[[:space:]]*\([[:space:]]*true|\.secure[[:space:]]*\([[:space:]]*\)|;[[:space:]]*Secure'`
      (each listed file sets a cookie and never marks one `Secure`. Drogon defaults it off and Crow
      defaults every attribute off. In the files that do set it, read each cookie for `HttpOnly`,
      an explicit `SameSite`, `Path=/` and a `__Host-` name)
- [ ] **Privilege drop (§7) — HIGH on a setuid program or a root-started daemon** —
      `grep -rnE '^[[:space:]]*(setuid|setgid|setresuid|setresgid|setgroups|initgroups)[[:space:]]*\([^;]*\)[[:space:]]*;' --include='*.c' --include='*.cpp' .`
      (a call used as a bare statement: its return value is discarded. The trailing `;` keeps
      a continuation line of a multi-line `if` out);
      `grep -rnE '(setuid|setgid|setgroups|initgroups)[[:space:]]*\(' --include='*.c' --include='*.cpp' .`
      (then read the order: groups, gid, uid, and a `setuid(0)` that must fail)
- [ ] **Insecure randomness for security — HIGH** —
      `grep -rnE '\b(rand|random|srand|mt19937|random_device)\b' --include='*.cpp' --include='*.c' .`
      ; `grep -rn 'memcmp' --include='*.cpp' . | grep -iE 'mac|hmac|token|secret|sig|digest'`
      (timing leak)
- [ ] **Hardening flags present? — HIGH if missing on network/setuid binary** —
      `grep -rnE '_FORTIFY_SOURCE|stack-protector|relro|cf-protection|_GLIBCXX_ASSERTIONS|fPIE' . --include='CMakeLists.txt' --include='*.cmake' --include='Makefile*' || echo "no hardening flags found"`
- [ ] **Hardening switched off by an opt-out macro or flag (§5, §5a) — HIGH on a network-facing
      binary unless a comment justifies it** —
      `grep -rnE --include='CMakeLists.txt' --include='*.cmake' --include='Makefile*' --include='*.mk' --include='*.ac' -e '-U[[:space:]]*_FORTIFY_SOURCE|_FORTIFY_SOURCE=0' . | grep -vE -- '-D[[:space:]]*_FORTIFY_SOURCE=[1-9]'`
      (an undefine with no re-define on the line) ;
      `grep -rnE '_[A-Z]+_SECURE_NO_(WARNINGS|DEPRECATE)|STRSAFE_NO_DEPRECATE|[/-]wd[[:space:]]*4996|warning[[:space:]]*\([[:space:]]*disable[[:space:]]*:[^)]*4996' --include='*.c' --include='*.cpp' --include='*.h' --include='*.hpp' --include='CMakeLists.txt' --include='*.cmake' --include='*.vcxproj' --include='*.props' .`
      (each silences Microsoft's deprecation of the unsafe CRT, C++ library or `strsafe.h`
      replacements while the unsafe calls stay: remove it and fix the calls, or justify it)
- [ ] **Windows binary hardening (§5a) — HIGH for an opt-out, MEDIUM for missing `/sdl` or
      `/guard:cf`** —
      `grep -rnE '/(GS-|guard:cf-|GUARD:NO|DYNAMICBASE:NO|NXCOMPAT:NO|HIGHENTROPYVA:NO|CETCOMPAT:NO)' --include='CMakeLists.txt' --include='*.cmake' --include='*.vcxproj' --include='*.props' --include='*.bat' --include='*.cmd' .`
      ; then `binskim analyze <artifacts> --output r.sarif` on every shipped `.exe`/`.dll` (a
      `.vcxproj` stores most of these as properties, not flags, so the binary check is the proof)
- [ ] **Inert or conflicting hardening flags counted as controls (§5) — LOW** —
      `grep -rnE --include='CMakeLists.txt' --include='*.cmake' --include='Makefile*' --include='*.mk' -e '-Wstrict-overflow|-z,nodump|-z[[:space:]]+nodump' .`
      (neither protects anything on Linux: do not credit them in a hardening review)
- [ ] **Hardening reached the shipped binary (§5) — HIGH on a network-facing or setuid binary
      that fails a check** — `checksec --file=BIN` or `annocheck BIN` on every artifact you ship
      (or `readelf -hW`/`-lW`/`-dW`/`--dyn-syms`: `DYN`, `GNU_RELRO`, `BIND_NOW`,
      `__stack_chk_fail`, `__*_chk`) ;
      `grep -rnE '^[[:space:]]*(CFLAGS|CXXFLAGS|CPPFLAGS|LDFLAGS)[[:space:]]*:?=' --include='Makefile.am' .`
      (a Makefile.am that overwrites the user's flags: confirm on the `make V=1` compile line)
- [ ] **Shipped artifact built in debug mode rather than release mode: empty or `Debug` build
      type, sanitizer runtime, `_GLIBCXX_DEBUG` (§5) — HIGH on a network-facing binary** —
      `grep -rnE '(^|[[:space:]])cmake[[:space:]]+[^|;&]*(-S|-B|\.\.)|-fsanitize=|_GLIBCXX_DEBUG' --include='Dockerfile*' --include='Containerfile*' --include='*.spec' --include='PKGBUILD' --include='rules' --include='*.yml' --include='*.yaml' . | grep -vE 'CMAKE_BUILD_TYPE=(Release|RelWithDebInfo|MinSizeRel)'`
      (a configure step with no release build type, or a debug-only flag, in packaging or CI. In
      CI only the job that produces the shipped artifact matters, since test jobs rightly
      sanitize. Then look for the `APP_RELEASE` `#error` guard in the source)
- [ ] **Static + safety-standard analysis** —
      `clang-tidy --checks='cert-*,bugprone-*,clang-analyzer-security.*' <files>` ;
      `cppcheck --enable=warning,portability --addon=cert <src>`