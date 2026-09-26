# 06 — Memory & Resource Safety

Scope: integer overflow/truncation, bounds discipline, unsafe-code policy and
native library search paths, untrusted size/length fields, resource exhaustion,
concurrency hazards with security impact, temp files. Maps to
CWE-190/191/787/125/416/400/770/362/427/377.

Core principle: **arithmetic on attacker-influenced numbers is a security
operation.** Most memory-safety exploits start as an integer bug; most outages
start as a missing limit. In memory-safe languages the corruption goes away but
the logic, truncation, and exhaustion bugs remain.

## 1. Integer overflow & truncation (CWE-190/191/197)

- Treat any length, count, offset, size, index, or money amount derived from
  input as hostile: it can be huge, zero, negative, or crafted to wrap.
- Check **before** the operation, in a form that cannot itself overflow:

```c
/* BAD: a+b may wrap before the check */
if (a + b > MAX) reject();
/* GOOD */
if (a > MAX - b) reject();            /* unsigned, b <= MAX */
if (__builtin_add_overflow(a, b, &r)) reject();   /* best: checked intrinsics */
```

- Multiplication for allocation sizing is the classic heap-overflow setup:
  `malloc(count * size)` → use `calloc(count, size)` (checks internally) or
  explicit `count > SIZE_MAX / size` guard (CWE-131).
- Signed/unsigned conversion: a negative `int` length becomes a huge `size_t`
  (CWE-195). Validate signedness/range at the boundary, then use one type
  (`size_t`/`usize`) consistently.
- Truncation: 64→32 bit assignment silently drops high bits — a 4GiB+X length
  truncates to X and passes small-size checks while the real data is huge.
- Language quick reference for input-derived arithmetic:

| Language | Default behavior | Use instead |
|---|---|---|
| C/C++ | UB (signed), wrap (unsigned) | `__builtin_*_overflow`, `std::cmp_*` (C++20), UBSan in CI |
| Rust | panic (debug), **wrap (release)** | `checked_*`/`saturating_*`/`try_into()`; `overflow-checks = true` in release profile |
| Go | silent wrap | manual guards, `math/bits.Mul64` carry checks |
| Java | silent wrap | `Math.addExact/multiplyExact`, `long` before narrowing |
| C# | silent wrap | `checked {}` blocks or `/checked` compiler flag |
| JS/TS | precision loss > 2^53 | `Number.isSafeInteger` on ingest, `BigInt` for counters |
| Python | arbitrary precision | still range-check semantics (negative/huge values) |
| SQL | dialect-dependent | constrain columns (`CHECK (qty > 0)`), DECIMAL for money |
- Money/quantities: overflow and negative-amount bugs are business-critical
  (transfer of `-100` credits the attacker). Range-check semantic validity
  (`0 < amount <= LIMIT`), use decimal/integer-cents types, never floats.
  - **Multiply before you divide.** Integer `amount / 10000 * fee_bps` truncates
    first and loses the remainder on every call; `amount * fee_bps / 10000` keeps
    it, and the product then needs the checked form above.
  - **Round in the system's favour.** Round what you issue or pay out (shares
    minted, amounts returned) down, and what the user must supply up. EIP-4626's
    security considerations spell out exactly that split for tokenised vaults, and
    the reason carries to any ledger: whichever side receives the rounding can
    repeat it until it adds up.
  - **Enforce a minimum meaningful amount.** Dust and zero-value operations (a
    transfer of 0, a deposit worth less than one unit after rounding) are free
    spam and rounding-exploit loops; reject below the floor.
  OWASP: SCSVS S7.2.A4, SCSVS S7.2.A6, SCSVS S7.2.B1.
- **Arithmetic edge cases beyond sizes.** The same hostility applies to every
  input-derived number: reject NaN and ±Infinity from parsed floats before any
  range check (every comparison with NaN is false, so `x < lo || x > hi` lets it
  through); guard divisors and fail explicitly on zero; bound values before
  unit conversions (seconds × 10^9 overflows a signed 64-bit nanosecond
  duration past roughly 292 years of seconds, which a "positive number" check
  lets through); inside an explicitly unchecked
  region (C# `unchecked`, Rust `wrapping_*`) write down the bound that makes
  wrapping impossible, because the compiler no longer checks; and check
  intermediates of multi-term expressions and the MIN/MAX extremes — `-INT_MIN`,
  `abs(INT_MIN)` and `INT_MIN / -1` have no representable result. The
  per-language behaviour is measured in each language skill: `sota-c-cpp`
  rules/03 §2, `sota-dotnet` rules/01 §1, `sota-golang` rules/02 §4,
  `sota-javascript-typescript` rules/02, `sota-jvm` rules/01 §1, `sota-php`
  rules/01 §4, `sota-python` rules/03 §12, `sota-ruby` rules/01 §7, `sota-rust`
  rules/01 §3. OWASP: Go-SCP (general coding practices), SCSVS S7.1.A3,
  SCSVS S7.1.A4, SCSVS S7.1.A6, SCSVS S7.2.B5.

```rust
// BAD: wraps silently in release; negative-after-cast passes a < check
let total = price as u32 * qty as u32;

// GOOD: checked, bounded, one unsigned type end-to-end
let qty: u32 = input.qty.try_into().map_err(|_| Invalid)?;
if !(1..=MAX_QTY).contains(&qty) { return Err(Invalid); }
let total = price.checked_mul(qty).ok_or(Overflow)?;
```

## 2. Bounds & buffer discipline (CWE-787/125/120)

- In C/C++: every read/write through a pointer needs a known, checked bound.
  Banned-by-policy: `gets`, `strcpy`, `strcat`, `sprintf`, `scanf("%s")`;
  use `snprintf`, `strlcpy`, or length-explicit APIs — and check *their* return
  values for truncation.
- Off-by-one audit points: `<=` vs `<` against array length, NUL-terminator
  space (`strlen` excludes it), inclusive ranges, loop bounds derived from
  decremented unsigned values (`for (size_t i = n-1; i >= 0; ...)` never ends).
- Prefer structurally safe containers: `std::span`/`std::array::at`,
  `std::string`, Rust slices, Go slices — and keep raw-pointer arithmetic inside
  small, reviewed modules.
- Use-after-free/double-free (CWE-416/415): ownership must be explicit
  (RAII/smart pointers, single owner); null out freed pointers in legacy code;
  beware iterator/reference invalidation on container mutation, and callbacks
  that outlive their captures.
- Build with the mitigations on (they're table stakes, not fixes): ASLR/PIE,
  stack protectors, `_FORTIFY_SOURCE=3`, CFI where available; CI runs ASan/UBSan
  on tests and fuzzers (libFuzzer/AFL++) on every parser of untrusted bytes.
- New-code policy (CISA/NSA memory-safety guidance direction): prefer
  memory-safe languages for new components that parse untrusted input; new C
  is a decision requiring justification, not a default. When extending C/C++,
  isolate parsers in least-privilege processes (sandboxing — seccomp,
  pledge/unveil, AppContainer) so a parser bug is a crash, not a compromise.

```c
/* BAD: trusts decoded length twice over (overflow + over-read) */
uint32_t n = read_u32(pkt);
char *buf = malloc(n + 1);            /* n = 0xFFFFFFFF -> malloc(0) */
memcpy(buf, pkt->data, n);            /* over-read + heap overflow */

/* GOOD */
uint32_t n = read_u32(pkt);
if (n > MAX_MSG || n > pkt->remaining) return ERR_MALFORMED;
char *buf = malloc((size_t)n + 1);
if (!buf) return ERR_OOM;
memcpy(buf, pkt->data, n); buf[n] = '\0';
```

## 3. Unsafe-code policy (Rust `unsafe`, FFI, native modules)

- Default: forbid. `#![forbid(unsafe_code)]` in app crates; `unsafe` allowed
  only in designated low-level crates with:
  - a `// SAFETY:` comment per block stating the invariants and why they hold;
  - the **smallest possible scope** wrapped in a safe API whose type signature
    makes misuse impossible (the safety boundary is the module, not the block);
  - Miri/ASan coverage in CI and mandatory second-reviewer sign-off.
- The same policy applies to FFI surfaces everywhere: JNI, cgo, Python C
  extensions, Node native addons — memory-unsafe code reachable from safe code
  inherits the full C threat model. Validate all data crossing the FFI boundary
  in both directions (lengths, encodings, null-termination). Copy mutable input
  (arrays, buffers) first, then validate and pass the copy: a caller or another
  thread holding the original can change it between check and use (the WASM
  copy-then-validate rule, `sota-sandboxing` rules/04, at every native boundary).
  In JNI, keep `native` methods private behind a public wrapper that does both.
  OWASP: Code Review Guide v2.
- `unsafe` justified by "performance" without a benchmark is a finding.
- **A memory-safe language reaches the same threat model without anyone writing C.** Each
  one ships an escape hatch into raw memory as an ordinary library call, and a codebase
  "in a GC language" is memory-safe only until it uses one. Each language skill carries
  its own spelling; the rule is the one above (confine it, justify it, validate at the
  boundary). The hatches, each checked against its vendor's documentation (2026-09-23):
  - **Go:** `unsafe.Pointer`, `cgo`, `//go:linkname` (`sota-golang` rules/05 §7).
  - **JVM:** JNI (`native` / Kotlin `external`, `System.loadLibrary`); the FFM API
    (final in JDK 22, JEP 454), whose restricted methods only *warn* unless
    `--enable-native-access` names the module; `sun.misc.Unsafe` memory access
    (deprecated for removal in JDK 23, JEP 471).
  - **.NET:** `unsafe` blocks, pointers and `fixed`, which need `AllowUnsafeBlocks`
    (default `false`); P/Invoke through `[DllImport]` or `[LibraryImport]` (.NET 7+, which
    also requires `AllowUnsafeBlocks`); `Marshal.*` on raw pointers.
  - **Python:** `ctypes` and `cffi`, which read and write arbitrary process memory from pure
    Python; the docs warn that incorrect use can "corrupt data and objects, reveal sensitive
    information, cause crashes".
  - **Node:** native addons (`.node`, Node-API), and **`Buffer.allocUnsafe`**, whose memory
    "is *not initialized*" and "may contain sensitive data". That is an information leak
    with no native code at all.
  - **PHP:** the FFI extension; `ffi.enable` defaults to `"preload"` (CLI and preloaded files
    only), and `"true"` opens it to every request.
  - **Ruby:** Fiddle (a libffi wrapper), the `ffi` gem, and C extensions.

  **A `.csproj` with `AllowUnsafeBlocks`, a Python import of `ctypes`, or a PHP
  `ffi.enable=true` is the one-line signal** that a codebase crosses into unmanaged memory.
  Audit that code with the C rules in §2, not the language's own.

### 3.1 Which file gets loaded: native library search paths (CWE-427)

Every escape hatch above ends in a loader call, and **a library loaded by bare name or
relative path comes from whichever search directory answers first**. Anyone who can write to an
earlier directory supplies the code, with the process's privileges. Microsoft calls this a
*DLL preloading* or *binary planting* attack. The fix is the same everywhere: load by absolute
path from a directory that only the owner or installer can write, or restrict the search to
such directories. The per-platform facts, from each vendor's documentation, with the
measurements dated 2026-09-24:

- **Windows.** With safe DLL search mode on (the default), a bare-name `LoadLibrary`
  searches the application's folder, the system folders, **the current folder**, then `PATH`.
  Safe mode only moves the current folder later; it does not remove it. A DLL loaded by full
  path still has its *dependencies* searched by module name. Fix:
  `SetDefaultDllDirectories(LOAD_LIBRARY_SEARCH_DEFAULT_DIRS)` early in the process
  (application directory, System32 and `AddDllDirectory` entries only), or `LoadLibraryEx`
  with `LOAD_LIBRARY_SEARCH_*` flags. `SetDllDirectory("")` removes the current folder. An
  application folder the user can write to (a download directory) is itself a planting site.
- **.NET.** `[DllImport]` with no `DefaultDllImportSearchPaths` probes *"a number of
  directories, including the current working directory"* (CA5392). CA5393 flags the unsafe
  values `AssemblyDirectory`, `UseDllDirectoryForDependencies`, `ApplicationDirectory` and
  `LegacyBehavior`, and names `SafeDirectories`, `System32` and `UserDirectories` as safe. CA3011
  flags HTTP input reaching an assembly load (`Assembly.Load`). **None of the three is enabled
  by default** in .NET 10: turn them on.
- **Linux (glibc).** `dlopen` treats a name containing `/` as a pathname, so `"./x.so"` is
  relative to the CWD. A bare name searches `DT_RPATH`, `LD_LIBRARY_PATH`, `DT_RUNPATH`,
  `ld.so.cache`, then `/lib` and `/usr/lib`. The CWD is not on that list, and **three things put
  it back**. Each loaded a planted library in the measurement:
  - **An empty `LD_LIBRARY_PATH` entry** (`ld.so(8)`: *"A zero-length directory name indicates
    the current working directory"*). `LD_LIBRARY_PATH=/opt/lib:$LD_LIBRARY_PATH` with the
    variable unset produces one; `/opt/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}` does not.
  - **A relative `RPATH`/`RUNPATH`** (`-Wl,-rpath,lib`), resolved against the CWD. Check
    shipped binaries with `readelf -d`.
  - **A relative path** passed to `dlopen`.

  On musl the empty entry did *not* resolve to the CWD, but the relative `RUNPATH` did.
  `$ORIGIN` resolved to the binary's own directory, so it is safe exactly when that directory
  is. The dynamic linker ignores `LD_LIBRARY_PATH` for set-user-ID programs.
- **macOS.** `dlopen` of a bare leaf name searches `DYLD_LIBRARY_PATH`, then `LC_RPATH`, then
  **the current working directory if the process is unrestricted** (`man dlopen`). Measured:
  `dlopen("libplug.dylib")` loaded a planted dylib from the CWD. That is worse than Linux,
  where a bare name reaches the CWD only through an empty `LD_LIBRARY_PATH` entry or a
  relative `RUNPATH`. Use `@rpath/` or an absolute path. `DYLD_*`
  variables are ignored for binaries protected by System Integrity Protection.
- **Python.** `ctypes.CDLL` hands the name to the platform loader: `CDLL("./x.so")` loaded the
  CWD's copy (measured, glibc). On Windows, since 3.8, `ctypes` and extension-module
  dependencies no longer search `PATH` or the current directory. Add directories with
  `os.add_dll_directory`. `ctypes.util.find_library` searches at run time, and the docs suggest
  hardcoding a name fixed at development time instead.
- **Java.** `System.load` requires an absolute path; a relative one threw (measured).
  `System.loadLibrary` searches `java.library.path`, and a relative entry
  (`-Djava.library.path=lib`) loaded the CWD's copy (measured). A library extracted from a jar
  into the shared temp directory under a predictable name, then loaded, is also §6.1's race.
- **Node.** `process.dlopen` and `require()` of a `.node` file load native code. Build the path
  from `__dirname` or `import.meta.url`, as Node's own examples do, never from the CWD or input.
- **The environment is a search path too.** `LD_PRELOAD`, `LD_LIBRARY_PATH` and `DYLD_*` taken
  from an untrusted parent or request pick the code. Spawn children with a clean environment
  (`sota-sandboxing` rules/04 R5.3).

Detectors, each run against a known-bad and a known-good fixture under ugrep and BSD grep.
Every hit needs reading, not counting. A hit is a finding when the name has no absolute path
and the directories searched are not all owner-writable only:

```text
C/C++ Win   grep -rnE 'LoadLibrary(Ex)?[AW]?[[:space:]]*\([[:space:]]*(L|TEXT\()?"[^"\\/:]+"' --include='*.c' --include='*.cpp' --include='*.h' .
C/C++ Unix  grep -rnE 'dlopen[[:space:]]*\([[:space:]]*"(\.{1,2}/|[^"/]+")' --include='*.c' --include='*.cpp' --include='*.h' .
Build       grep -rnE 'rpath[,=]["'"'"']?[^"'"'"'$@/[:space:]]|LD_LIBRARY_PATH=["'"'"']?(:|[^[:space:]+]*(::|:(["'"'"'[:space:]]|$)|:\$\{?LD_LIBRARY_PATH))' .
Binaries    readelf -d BINARY | grep -E 'R(UN)?PATH'      otool -l BINARY | grep -A2 LC_RPATH
.NET        grep -rnE 'DllImportSearchPath\.(AssemblyDirectory|UseDllDirectoryForDependencies|ApplicationDirectory|LegacyBehavior)|Assembly\.(Load|LoadFrom|LoadFile)[[:space:]]*\(' --include='*.cs' .
Python      grep -rnE "(CDLL|WinDLL|PyDLL|LoadLibrary)[[:space:]]*\([[:space:]]*[\"'](\.{1,2}/|[^\"'/\\\\]+[\"'])|find_library[[:space:]]*\(" --include='*.py' .
Java        grep -rnE 'System\.loadLibrary[[:space:]]*\(|java\.library\.path' .
Node        grep -rnE 'process\.dlopen[[:space:]]*\(|require[[:space:]]*\([^)]*\.node["'"'"'`]' --include='*.js' --include='*.ts' --include='*.mjs' --include='*.cjs' .
```

The .NET row finds explicit unsafe values. A `[DllImport]` with *no* search-path attribute is an
absence, and CA5392 is the tool that reports it.

## 4. Untrusted size/length fields (CWE-130/805)

Binary protocol & file-format parsing is where size fields kill:

- **Never allocate or read based on a declared size before sanity-checking it**
  against: protocol maximums, remaining-bytes-actually-available, and global
  memory budget. `length = read_u32(); buf = alloc(length)` is a one-line DoS
  (and with truncation, a heap overflow).
- Cross-check redundant fields: header total-size vs sum of section sizes vs
  actual file size; mismatches → reject, don't "repair".
- Offsets are size fields too: `base + offset` must be bounds-checked post-add
  (overflow-safe, §1) before dereference/seek.
- Decompression: enforce output-size caps and **ratio caps** (zip/gzip/zstd
  bombs, CWE-409); decode images with pixel-count limits before full decode;
  same for XML entity expansion (rules/01 §6).
- Parse with length-aware cursors that return errors on underrun, not raw
  pointer math; fuzz every such parser.

```rust
// GOOD pattern: declared length vs available bytes
let len = cur.read_u32()? as usize;
if len > MAX_RECORD || len > cur.remaining() { return Err(Malformed); }
let body = cur.take(len)?;
```

## 5. Resource exhaustion (CWE-400/770)

Every resource an unauthenticated or cheaply-authenticated request can consume
needs a cap. Inventory: memory, CPU, file descriptors, threads, DB connections,
disk, queue depth, downstream API quota.

- Request limits: max body size (enforced while streaming), max header
  count/size, max URL length, max multipart parts, max JSON depth/keys (deeply
  nested JSON is a parser CPU/stack bomb), max GraphQL query depth/complexity
  and disabled introspection-driven amplification (batching, aliases).
- Timeouts everywhere: server read/write/idle timeouts (slowloris), and
  **every** outbound call (HTTP, DB, DNS, gRPC) gets a deadline — a missing
  client timeout turns a slow dependency into thread-pool exhaustion. Propagate
  cancellation (context/AbortSignal) so abandoned requests stop working.
- Rate limiting: per-principal (user/API key) primary, per-IP secondary
  (IPv6: limit per /64); token-bucket at the edge plus per-endpoint costs for
  expensive operations (search, export, password hashing — argon2id itself is a
  CPU lever, queue/limit login attempts).
- Concurrency caps + bounded queues + load shedding (fail fast with 429/503)
  beat unbounded buffering; unbounded channels/queues just move the OOM.
- Amplification asymmetry: reject work where attacker cost ≪ your cost before
  doing the expensive part (validate-cheap-first ordering; cache negative
  results; require auth before expensive ops).
- Disk: log rotation with caps, temp-file cleanup on all error paths
  (try/finally), quota per tenant for stored artifacts.
- Denial-of-wallet: on serverless/usage-billed infra and metered third-party
  APIs (LLM tokens, SMS, email), exhaustion shows up as your invoice — hard
  budget caps + alerts per tenant/feature, and never let an unauthenticated
  path trigger metered work (SMS-OTP send endpoints are the classic pump).
- Slow senders: enforce a minimum ingress data rate, set from a baseline of real
  traffic, and drop slower connections (Kestrel's `MinRequestBodyDataRate`, for
  one). CAPTCHA and other puzzles curb functional abuse, such as a form that sends
  mail, but are no DoS defence. Put logs on a volume apart from application data,
  so a log flood cannot fill the disk the database writes to. OWASP: Denial of
  Service cheat sheet, Logging cheat sheet.
- **HTTP/2 stream-reset and frame floods** (this section owns the class; other skills point
  here). A request limit does not bound work a client can cancel: *Rapid Reset*
  (CVE-2023-44487) opens and client-resets streams so the concurrent-stream cap never binds;
  *MadeYouReset* (CVE-2025-8671) makes the **server** reset them via malformed frames or
  flow-control errors; a *CONTINUATION flood* makes a server parse unbounded header frames, and
  is fixed per implementation (e.g. CVE-2023-45288 Go `net/http`/`x/net/http2`, CVE-2024-27983
  Node.js). Patch **both** the application's HTTP/2 stack **and** every proxy/load balancer that
  terminates HTTP/2, and cap at the edge: concurrent streams per connection, resets (client- and
  server-initiated) per connection per interval with a connection close past it, and total
  header bytes including CONTINUATION frames. CVE records: cve.org.

```go
// GOOD: every outbound call carries a deadline; caller cancellation propagates
ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
defer cancel()
row := db.QueryRowContext(ctx, q, id)        // DB
req, _ := http.NewRequestWithContext(ctx, "GET", url, nil)  // HTTP
// server side: http.Server{ReadHeaderTimeout, ReadTimeout, WriteTimeout, IdleTimeout}
// all set — Go's zero values are "no timeout", i.e. slowloris-vulnerable by default
```

## 6. Concurrency hazards with security impact (CWE-362/367)

- TOCTOU on filesystems: check-then-use (`access()` then `open()`) races against
  symlink swaps — use `open` with `O_NOFOLLOW|O_EXCL` semantics, operate on the
  fd (`fstat`, `openat`), not the re-resolved path (CWE-367/59).
- Race-driven logic bypass: balance checks, coupon redemption, invite
  acceptance, rate counters — concurrent requests pass the same check before
  either writes. Fix with DB-level guarantees: atomic conditional updates
  (`UPDATE ... WHERE balance >= x`), unique constraints, `SELECT ... FOR
  UPDATE`/serializable transactions, or idempotency keys — never in-process
  locks across multiple instances.
- **No race window is too small to exploit.** PortSwigger's single-packet
  attack puts 20–30 HTTP/2 requests in one TCP packet and measured a median
  arrival spread of about 1 ms across 17,000 km; last-byte synchronisation does
  the same for HTTP/1.1, less tightly. A window of about a millisecond is
  therefore within reach from across the internet, and "the window is tiny" is
  not a mitigation. The fix is atomicity or locking at the store; delays, jitter and
  retries only move the window. OWASP: Business Logic Security cheat sheet.

```sql
-- BAD: check in app code, then write (two requests both pass the check)
-- SELECT balance FROM accounts WHERE id=$1;  ... if balance >= amt: UPDATE ...

-- GOOD: the check IS the write; 0 rows affected = insufficient funds
UPDATE accounts SET balance = balance - $2
 WHERE id = $1 AND balance >= $2;

-- GOOD: single-use tokens/coupons via atomic claim
UPDATE coupons SET used_by = $1, used_at = now()
 WHERE code = $2 AND used_by IS NULL;
```
- Shared mutable state across requests (globals, class attributes in pooled
  workers) leaks one user's data into another's response — keep request state
  request-scoped; audit caches and reused buffers for cross-request bleed.
  Serverless is no exception: a warm FaaS environment is reused, and AWS's Lambda
  docs say objects declared outside the handler stay initialised and `/tmp`
  content survives between invocations (an invoke-failure reset does not clear
  it). Keep per-invocation data in handler scope, delete temp files and wipe
  sensitive state before returning, and never assume a fresh filesystem. OWASP:
  Serverless FaaS Security cheat sheet.
- Signal/reentrancy handlers and async callbacks touching shared security state
  need the same discipline.

### 6.1 Temporary files and permissions (CWE-377/378/379)

A temp file is the filesystem TOCTOU above in its most common form. The shared temp
directory is world-writable, so **a name chosen before the file exists is a race the
attacker can win**: they create a symlink at that path first, and your write goes wherever
it points. Three shapes, the same in every language (and on reused serverless runtimes
the files also outlive the invocation, §6):

- **Name now, file later.** An API that returns a *name* and creates nothing (C
  `mktemp`/`tmpnam`/`tempnam`, Python `tempfile.mktemp`). The C man page is blunt: the
  window between choosing the name and opening it is *"particularly dangerous from a
  security perspective"*. Use the call that creates the file atomically, owner-only
  (`mkstemp`/`mkdtemp` create mode 0600), and work on the handle it returns.
- **A hand-built path in the temp directory.** `"/tmp/" + name`, or the temp dir joined to a
  fixed or guessable name. It is the same race without the API call, and the more common one.
- **Permissions widened after the fact.** A secret written into a 0644 file, a later
  `chmod 0777`, or a process `umask(0)` hands it to every local account. Pass the mode at
  creation time. The process umask can only narrow a requested mode, never widen it.

This is a **class stated once, with per-language detectors**, the same design as host-key
verification in rules/04 §5 (operator decision, 2026-09-24). The per-language spellings live in the table below, not in the language skills:

| language | the unsafe form | the safe API |
|---|---|---|
| C / C++ | `mktemp`, `tmpnam`, `tempnam` | `mkstemp`, `mkdtemp`, `tmpfile` |
| Python | `tempfile.mktemp`, `"/tmp/..."` literals | `tempfile.mkstemp`, `NamedTemporaryFile`, `TemporaryDirectory` (`sota-python` rules/05 §4a) |
| Go | `filepath.Join(os.TempDir(), fixedName)` | `os.CreateTemp`, `os.MkdirTemp` (`sota-golang` rules/05 §4a) |
| Ruby | `"/tmp/#{name}"` | `Tempfile`, `Dir.mktmpdir` (`sota-ruby` rules/02 §7) |
| Rust | `std::env::temp_dir().join(name)` + `File::create` | the `tempfile` crate (`NamedTempFile`), or `OpenOptions::create_new(true)` + `.mode(0o600)` |
| Java / Kotlin | `File.createTempFile`, `java.io.tmpdir` + a name | `Files.createTempFile`, `Files.createTempDirectory` |
| Node | `path.join(os.tmpdir(), name)` + a default `writeFile` | `fs.mkdtemp`, then write inside it with `{ flag: 'wx', mode: 0o600 }` |
| PHP | `sys_get_temp_dir() . '/name'` + `file_put_contents` | `tempnam()`, `tmpfile()`, `fopen($p, 'x')` |
| .NET | `Path.Combine(Path.GetTempPath(), name)` + `File.WriteAllText` | `Path.GetTempFileName()` (0600 on Unix, `mkstemps`), `Directory.CreateTempSubdirectory()`, or `FileMode.CreateNew` with `UnixCreateMode` |

**What the gap-checks measured (2026-09-24, umask 022), and the traps inside the safe APIs:**
- **The symlink attack worked in every language tried.** A symlink planted at the predictable
  name was followed, and the victim file was overwritten. This was reproduced with Rust
  `File::create`, Node's default `writeFile`, PHP `file_put_contents` and .NET
  `File.WriteAllText`. Exclusive create refused it every time: Rust `create_new`, Node
  `'wx'`, PHP `fopen(…, 'x')`, .NET `FileMode.CreateNew`.
- **The default mode of a new file is 0644**: readable by every local account.
- **Java: `File.createTempFile` creates `rw-r--r--`.** `Files.createTempFile` creates
  `rw-------`, and `Files.createTempDirectory` creates `rwx------`.
- **Rust: `tempfile::tempdir()` creates the directory 0755.** `NamedTempFile` is 0600, but a
  file later made inside that directory with `File::create` is world-readable.
- **PHP: `tempnam()` with a directory that does not exist silently falls back** to the
  system temp directory and returns a path there. Check the `dirname()` of the result.
- **Node: `fs.mkdtemp` created its directory 0700** (measured on macOS; Node's docs do not
  state a mode).

Detectors, each run against a known-bad and a known-good fixture under ugrep and BSD grep.
Every hit needs reading, not counting. A hit is a finding when the name was chosen before the
file existed, or when the mode reaches other accounts:

```text
C/C++   grep -rnwE 'mktemp|tmpnam|tempnam' --include='*.c' --include='*.cpp' --include='*.h' .
Python  grep -rnE 'tempfile\.mktemp\(|["'"'"']/tmp/' --include='*.py' .
Go      grep -rnE 'os\.TempDir\(\)|"/tmp/' --include='*.go' .
Ruby    grep -rnE '"/tmp/|Dir\.tmpdir' --include='*.rb' .
Rust    grep -rnE 'temp_dir\(\)|"/(tmp|var/tmp|dev/shm)/' --include='*.rs' .
JVM     grep -rnE 'File\.createTempFile\(|createTempDir\(|getProperty\("java\.io\.tmpdir"\)' --include='*.java' --include='*.kt' .
Node    grep -rnE 'tmpdir\(\)|/tmp/' --include='*.js' --include='*.ts' --include='*.mjs' --include='*.cjs' .
PHP     grep -rnE '(file_put_contents|fopen|touch|mkdir|copy|rename)[[:space:]]*\([^;]*(sys_get_temp_dir[[:space:]]*\(\)|["'"'"']/(var/)?tmp/)' --include='*.php' .
.NET    grep -rnE 'Path\.(Combine|Join)\([[:space:]]*Path\.GetTempPath\(\)|Path\.GetTempPath\(\)[[:space:]]*\+' --include='*.cs' .
```

The Node row also matches `fs.mkdtemp(path.join(os.tmpdir(), …))`, which is the safe form, so
read each hit rather than piping through `grep -v`. The pipeline's exit status would then
belong to `grep -v`, and a failed first stage would read as clean.

## 7. Audit grep starters

```text
gets\(|strcpy|strcat|sprintf\(|scanf\("%s     malloc\(.*\*  (unchecked multiply)
alloca\(  with input-derived arg              memcpy\(.*, *len\)  trace len's origin
\(int\)|\(uint32_t\) casts on size_t/length   unsafe \{ without // SAFETY:
as u32|as usize on parsed input (Rust)        overflow-checks absent in release profile
http.Client\{ without Timeout                 requests.(get|post)\( without timeout=
new Worker|Thread\( in request handlers       unbounded chan / Queue() / Buffer concat
zip|tar|gzip extract without size/ratio cap   Image.open/decode without pixel limit
os.access\(|fs.exists\( followed by open      SELECT.*FOR UPDATE absent near balance/credit math
unsafe.Pointer|cgo  (Go)   JNI native|external fun|sun.misc.Unsafe|java.lang.foreign  (JVM)
AllowUnsafeBlocks|DllImport|LibraryImport  (.NET)   ctypes|cffi  (Python)
Buffer.allocUnsafe|\.node|node-addon-api  (Node)   FFI::|ffi.enable  (PHP)   Fiddle|FFI::Library  (Ruby)
LoadLibrary("bare.dll") | dlopen("./x" or "bare") | CDLL("./x") | rpath,lib | LD_LIBRARY_PATH=...:  (§3.1 rows)
DllImportSearchPath.(AssemblyDirectory|ApplicationDirectory|LegacyBehavior) | loadLibrary + relative java.library.path
```

## Audit checklist

- [ ] Is all arithmetic on input-derived sizes/counts/offsets/amounts overflow-checked (checked intrinsics or pre-condition form) before use?
- [ ] Are allocation sizes guarded against multiplication overflow and capped against a memory budget?
- [ ] Are signed/unsigned conversions and 64→32 truncations on lengths eliminated or explicitly range-checked?
- [ ] Do money/quantity fields enforce positive, bounded, integer/decimal semantics?
- [ ] Does money and share arithmetic multiply before it divides, round in the system's favour (issued/paid out down, owed up), and reject amounts below a minimum meaningful unit (§1)? MEDIUM, HIGH on value-moving paths. Probe for divide-then-multiply, reading each hit (money and share maths first): `grep -rnE '[[:alnum:]_)][[:space:]]*/[[:space:]]*[[:alnum:]_.]+[[:space:]]*\)?[[:space:]]*\*[[:space:]]*[[:alnum:]_(]' .`
- [ ] Are NaN/±Infinity rejected from parsed floats, divisors guarded against zero, unit conversions and multi-term intermediates bounded, MIN/MAX extremes handled, and every unchecked region's bound written down (§1)? MEDIUM, HIGH where the value sizes, prices or authorizes something. Probe listing files that parse floats and never test finiteness: `grep -rlE '(float|parseFloat|ParseFloat|parseDouble|strto[dfl]|atof)[[:space:]]*\(' . | while IFS= read -r f; do grep -qiE 'is_?finite|is_?nan|isinf' "$f" || echo "$f"; done` — file-level, so one check hides the rest of that file; then run the language skill's own probe.
- [ ] Are banned C string functions absent and parsers of untrusted bytes fuzzed with sanitizers in CI?
- [ ] Is `unsafe`/FFI code confined to designated modules with SAFETY comments, safe wrappers, and Miri/ASan coverage?
- [ ] In a GC language, does any code use its escape hatch into raw memory (§3's per-language list)? Each use is audited with the C rules, and a project-wide opt-in (`AllowUnsafeBlocks`, `ffi.enable=true`, `--enable-native-access=ALL-UNNAMED`) is justified in writing.
- [ ] Is every native library loaded by absolute path, or through a search restricted to directories only the owner can write (§3.1)? Run §3.1's detector row for the platform and language, `readelf -d`/`otool -l` the shipped binaries for relative or `$ORIGIN` run paths, and on .NET enable CA5392, CA5393 and CA3011, which are off by default. HIGH when the process runs with more privilege than whoever can write the CWD, the application folder, or an `LD_LIBRARY_PATH` entry.
- [ ] Does every declared length/offset get validated against bytes-actually-available before allocation or read?
- [ ] Are decompression ratio caps, image pixel limits, and JSON/GraphQL depth+complexity limits enforced?
- [ ] Do all inbound listeners and outbound calls have timeouts, with cancellation propagation?
- [ ] Is rate limiting per-principal with bounded queues and load shedding (no unbounded buffering)?
- [ ] Are check-then-act sequences (files, balances, redemptions) made atomic at the storage layer?
- [ ] Is any race accepted because its window is "too small" (§6)? HIGH on balances, redemptions and limits: single-packet and last-byte-sync attacks reach millisecond windows. Probe for the rationalisation in comments and tickets: `grep -rniE 'race.{0,40}(unlikely|rare|tiny|small|negligible|acceptable)|(unlikely|rare|tiny|small|negligible).{0,40}race' .` (also matches `trace`; read each hit).
- [ ] Is every temp file created atomically, owner-only, under a name not chosen in advance (§6.1)? Run §6.1's detector row for the language, and read each hit: a predictable name in a shared temp directory is HIGH when the file holds secrets or is later read back as trusted.
- [ ] Is request-scoped data verified never to live in shared/global state across requests, including across warm serverless invocations, with `/tmp` files deleted before the handler returns (§6)? HIGH when the state holds another user's data. Python probe for a handler writing a module global: `grep -rnE '^[[:space:]]+global[[:space:]]+[[:alpha:]_]' --include='*.py' .` (read each hit).
- [ ] Does every FFI/JNI wrapper copy mutable input before validating it, with `native` methods private behind that wrapper (§3)? MEDIUM, HIGH when the native side trusts a length. Probe for JNI methods callable without a wrapper: `grep -rnE '(public|protected)[[:space:]]+([[:alpha:]]+[[:space:]]+)*native[[:space:]]' --include='*.java' .`
- [ ] Is a minimum ingress data rate enforced, CAPTCHA not counted as DoS defence, and are logs on a volume separate from application data (§5)? MEDIUM. Probe for a disabled rate floor: `grep -rnE 'Min(RequestBody|Response)?DataRate[[:space:]]*=[[:space:]]*null' --include='*.cs' .`
- [ ] Does every HTTP/2 terminator — app server and each proxy/load balancer — carry the fixes for Rapid Reset (CVE-2023-44487), MadeYouReset (CVE-2025-8671) and its implementation's CONTINUATION-flood CVE, with concurrent streams, resets per connection and total header bytes capped at the edge (§5)? HIGH on an internet-facing HTTP/2 listener; compare each terminator's version against its vendor advisory for all three
