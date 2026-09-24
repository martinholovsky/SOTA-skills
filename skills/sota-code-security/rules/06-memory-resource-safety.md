# 06 — Memory & Resource Safety

Scope: integer overflow/truncation, bounds discipline, unsafe-code policy,
untrusted size/length fields, resource exhaustion, concurrency hazards with
security impact. Maps to CWE-190/191/787/125/416/400/770/362.

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
  in both directions (lengths, encodings, null-termination).
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
- Signal/reentrancy handlers and async callbacks touching shared security state
  need the same discipline.

### 6.1 Temporary files and permissions (CWE-377/378/379)

A temp file is the filesystem TOCTOU above in its most common form. The shared temp
directory is world-writable, so **a name chosen before the file exists is a race the
attacker can win**: they create a symlink at that path first, and your write goes wherever
it points. Three shapes, the same in every language:

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
verification in rules/04 §5 (operator decision, 2026-09-24). Each language skill carries only its own spelling:

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
```

## Audit checklist

- [ ] Is all arithmetic on input-derived sizes/counts/offsets/amounts overflow-checked (checked intrinsics or pre-condition form) before use?
- [ ] Are allocation sizes guarded against multiplication overflow and capped against a memory budget?
- [ ] Are signed/unsigned conversions and 64→32 truncations on lengths eliminated or explicitly range-checked?
- [ ] Do money/quantity fields enforce positive, bounded, integer/decimal semantics?
- [ ] Are banned C string functions absent and parsers of untrusted bytes fuzzed with sanitizers in CI?
- [ ] Is `unsafe`/FFI code confined to designated modules with SAFETY comments, safe wrappers, and Miri/ASan coverage?
- [ ] In a GC language, does any code use its escape hatch into raw memory (§3's per-language list)? Each use is audited with the C rules, and a project-wide opt-in (`AllowUnsafeBlocks`, `ffi.enable=true`, `--enable-native-access=ALL-UNNAMED`) is justified in writing.
- [ ] Does every declared length/offset get validated against bytes-actually-available before allocation or read?
- [ ] Are decompression ratio caps, image pixel limits, and JSON/GraphQL depth+complexity limits enforced?
- [ ] Do all inbound listeners and outbound calls have timeouts, with cancellation propagation?
- [ ] Is rate limiting per-principal with bounded queues and load shedding (no unbounded buffering)?
- [ ] Are check-then-act sequences (files, balances, redemptions) made atomic at the storage layer?
- [ ] Is every temp file created atomically, owner-only, under a name not chosen in advance (§6.1)? Run §6.1's detector row for the language, and read each hit: a predictable name in a shared temp directory is HIGH when the file holds secrets or is later read back as trusted.
- [ ] Is request-scoped data verified never to live in shared/global state across requests?
