# 04 — Application-Level Sandboxing: risky parsers, privilege separation, WASM, subprocess hygiene, macOS

Scope: sandboxing *inside* an application's trust boundary — isolating the dangerous
10% of your own code (parsers, codecs, converters), brokering privileges, using WASM
and V8 isolates correctly, spawning subprocesses safely, and macOS realities.

---

## 1. Sandbox the risky parser, not the whole service

**R1.1 — Treat every complex-format parser as presumed-compromised.** Image
(libjpeg/libpng/ImageMagick/libwebp), PDF (poppler/mupdf/ghostscript), video/audio
(ffmpeg), fonts (freetype), archives (libarchive/unzip/7z), office formats, XML with
exotic features. Decades of memory-corruption CVEs (e.g., the libwebp 0-click chain)
make "parse attacker bytes in the main service process" indefensible.

**R1.2 — The pattern: short-lived worker with a fd-only interface.**
1. Parent opens input (and output destination) and validates *metadata* only.
2. Fork/spawn worker; pass input as an already-open read-only FD or stdin —
   the worker never gets filesystem rights to open anything itself.
3. Worker applies its own sandbox *before* touching input bytes:
   `no_new_privs` → drop caps → Landlock (empty fs policy) → strict seccomp
   allowlist (compute-only: read/write/mmap/brk/futex/exit; **no openat, no socket,
   no exec**) → rlimits (`RLIMIT_FSIZE`, `RLIMIT_CORE=0`) → cgroup budget. Memory
   belongs in the cgroup or in `RLIMIT_DATA` — **never `RLIMIT_AS`**, which kills a
   Go or JVM worker at startup (`02` R7.2a); when no cgroup can be created here,
   `02` R7.2b has the ladder.
4. Worker writes the *normalized* result (decoded RGBA, extracted text, re-encoded
   archive listing) to the output FD; parent enforces output size/shape limits.
5. Worker exits; one worker per input; **never reuse a worker across inputs** from
   different sources (a compromised worker poisons all later results).

```python
# Parent side (Linux): minimal example shape
r_in = os.open(path, os.O_RDONLY | os.O_CLOEXEC)
proc = subprocess.Popen(
    ["/usr/lib/myapp/img-decoder"],          # static, sandbox-self-applying binary
    stdin=r_in, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    close_fds=True, env={}, preexec_fn=None) # decoder sandboxes itself in main()
out, _ = proc.communicate(timeout=10)
if proc.returncode != 0 or len(out) > MAX_DECODED: reject()
```

**R1.3 — Normalize-and-re-encode at the boundary.** Don't pass attacker bytes
through; pass your *re-serialization* of the parsed structure. The sandboxed decoder
converting attacker-JPEG → raw pixels → your re-encoded JPEG strips polyglots,
appended payloads, and parser-differential tricks.

**R1.4 — Output is attacker-influenced too.** Cap output size, validate dimensions/
counts before allocating in the parent (decompression bombs: zip, PNG, XML entity
expansion). The sandbox stops code execution; resource limits stop DoS.

**R1.5 — Tooling shortcuts:** `bubblewrap` (bwrap) or `minijail0`/`nsjail` give you
R1.2 step 3 without writing clone3 code. Prefer these over hand-rolled sandboxing.
A full bwrap invocation for a decoder worker:

```bash
bwrap \
  --unshare-all --die-with-parent --new-session \
  --ro-bind /usr /usr --symlink usr/lib64 /lib64 \
  --proc /proc --dev /dev \
  --tmpfs /tmp --clearenv --setenv PATH /usr/bin \
  --uid 65534 --gid 65534 \
  --cap-drop ALL \
  --seccomp 9 9< decoder-seccomp.bpf \
  -- /usr/lib/myapp/img-decoder < input.jpg > decoded.rgba
```
Notes: `--unshare-all` covers user/pid/net/ipc/uts/cgroup+mount; `--new-session`
prevents TIOCSTI terminal injection; no `--bind` of any writable host path — input
and output travel over stdio. minijail equivalent adds `-S policy.bpf -p -l -e -v -r`
plus rlimits via `-R`. nsjail adds time limits (`--time_limit`) natively.

## 2. Privilege separation / broker pattern

**R2.1 — Split into broker (trusted, privileged, tiny) + worker (untrusted, sandboxed,
does the work).** The Chromium/OpenSSH architecture. The worker holds *zero ambient
authority*: no fs access, no network, no secrets. When it legitimately needs a
resource, it asks the broker over a socketpair/pipe with a narrow, validated RPC
("open file X under /uploads read-only") and receives an **FD**, not a path —
capability-style: possession of the FD is the whole permission.

**R2.2 — Broker rules:**
- Broker validates requests against a static policy (path canonicalization via
  `openat2(RESOLVE_BENEATH | RESOLVE_NO_SYMLINKS | RESOLVE_NO_MAGICLINKS)` — never
  string-prefix checks, which symlinks and `..` defeat).
- Broker code is small enough to review exhaustively; no parsing of complex formats,
  no dynamic policy from worker input.
- Rate-limit and log broker requests — the request stream is your IDS signal for a
  compromised worker.
- Secrets never cross to the worker: broker performs the privileged action (sign,
  decrypt, call the API) and returns only the result.

**R2.3 — pledge/unveil thinking, portably.** OpenBSD's model is the right mental
API: *declare at startup the promise set (pledge) and visible paths (unveil), then
irrevocably shrink after initialization*. On Linux: do all privileged setup first
(open files, bind sockets, read config), then apply Landlock+seccomp and drop the
rest — the "initialize broad, then lock down before processing input" sequencing is
the essence. Structure `main()` so the lockdown line is grep-ably obvious and any
code path that processes input after `main` without passing lockdown fails review.

## 3. WASM as a sandbox

**R3.1 — Why WASM is a good in-process boundary:** linear memory is bounds-checked
and isolated; control flow is structured (no ROP across the boundary); **no ambient
authority** — a module can only call imports you hand it. WASI is explicitly a
capability model: preopened directory FDs scope the filesystem; no preopen, no fs.

```rust
// wasmtime: deny-by-default instantiation
let mut config = Config::new();
config.consume_fuel(true);                      // deterministic CPU metering
let engine = Engine::new(&config)?;
let mut store = Store::new(&engine, ctx);
store.set_fuel(5_000_000)?;                     // CPU budget
store.limiter(|s| &mut s.limits);               // StoreLimits: memory/table caps
let wasi = WasiCtxBuilder::new()
    .preopened_dir(dir_fd, ambient_authority(), "/job")?  // ONLY this dir
    .build();                                   // note: no inherit_env/stdio/net
```

**R3.2 — The host functions you import ARE the attack surface.** WASM's guarantees
cover the guest; every host callback is a door. Audit imports like syscalls: no
"exec", no raw fs path APIs, validate all arguments (guest memory is
attacker-controlled — copy out, then validate, no TOCTOU re-reads).

**R3.3 — Always set fuel/epoch interruption + memory limits.** WASM without metering
is an infinite-loop DoS primitive. Epoch-based interruption (wasmtime) is cheap and
preempts even non-yielding guests.

**R3.4 — Engine bugs exist (JIT/compiler CVEs in all major engines):** for untrusted
modules at scale, run the WASM engine itself inside a process sandbox (§1) —
defense in depth per `01` R2.1. RLBox-style "compile the risky C library to WASM and
back to native" gives memory-isolation benefits even fully in-process and is a good
retrofit for parser libraries (Firefox ships this).

## 4. V8 isolates

**R4.1 — Isolates separate *heaps*, not *privileges*.** Same process, same address
space at the native level: one V8 sandbox-bypass bug = all co-resident isolates and
the host process. Use isolates for density and fast context switching, but:
- Run the isolate host process under seccomp + namespaces (Cloudflare's model);
  one host process per trust *tier* at minimum.
- Expose no Node-style APIs into the isolate; build a minimal, audited host API
  (`isolated-vm` if on Node — **never `vm`/`vm2`**, both escapable by design/history).
- Watchdog thread for CPU (`TerminateExecution`), heap limits per isolate
  (`SetResourceConstraints` + near-heap-limit callback), cap code size and
  disallow dynamic WASM/SharedArrayBuffer unless needed (Spectre surface).

## 5. Subprocess execution hygiene

**R5.1 — argv arrays, never shell strings.** `shell=True` / `system()` /
backticks with any tainted segment = command injection.

```python
# BAD
subprocess.run(f"convert {path} out.png", shell=True)
# GOOD
subprocess.run(["convert", "--", path, "out.png"], shell=False, ...)
```
Same rule per language: Python `shell=False`; Node `execFile`/`spawn` (never
`exec`, never `spawn(..., {shell:true})`); Go `exec.Command` (fine; never wrap in
`sh -c`); Rust `Command` (fine — measured 2026-08-19, **neither `.arg` nor `.args`
splits on whitespace**, so the argv guarantee holds; the documented exception is
Windows `.bat`/`.cmd`, `sota-rust` rules/05 §9); Java `ProcessBuilder` with list.

**R5.2 — Argument-level injection still exists with argv arrays:** values starting
with `-` become flags (use `--` separators); some tools have argument-driven exec
(`find -exec`, `tar --checkpoint-action`, `zip -TT`, `rsync -e`, `git -c
core.fsmonitor`, ImageMagick delegates, `ssh -o ProxyCommand`). Pin flags first,
`--`, then validated operands; prefer library bindings over CLI wrappers for
attacker-influenced parameters.

**R5.3 — Clean environment and clean inheritance:** spawn with an explicit minimal
`env` (PATH set to absolute trusted dirs; no `LD_PRELOAD`/`LD_LIBRARY_PATH`/
`PYTHONPATH`/`GIT_*`/locale surprises inherited from a tainted parent), absolute
program path (no PATH lookup of attacker-named binaries), `close_fds=True` /
`O_CLOEXEC` everywhere, cwd set to a safe directory, timeout + kill-on-timeout
(kill the *process group*: `start_new_session=True` then `killpg`), and stdout/stderr
size caps (a child that prints 10GB is a DoS on your log pipeline).

**R5.3a — a timeout that waits on inherited pipes is not a deadline, and the
semantics differ per language.** Verified 2026-08-18: Python 3.14's
`subprocess.run(..., timeout=)` raises `TimeoutExpired` on schedule even when a
*grandchild* still holds the pipe — but Go's `exec.CommandContext` kills the child
on context cancel and then blocks in `Wait` anyway, because "if `WaitDelay` is zero
(the default), I/O pipes will be read until EOF, which might not occur until
orphaned subprocesses of the command have also closed their descriptors for the
pipes" (`os/exec` package docs). Set `cmd.WaitDelay` (Go 1.20+). Do not generalise
from whichever language you used last — three of them behave three different ways
under the same test. Go's `Wait` blocks past context cancellation until
`cmd.WaitDelay` is set; Python's raises on schedule; **Rust/tokio's `timeout` fires
on schedule but leaves the child and its grandchild running**, because cancelling
the future is not killing the process (`.kill_on_drop(true)`, measured 2026-08-19).
Read that language's subprocess section before trusting the timeout: `sota-golang`
rules/05 §3, `sota-python` rules/05 §2, `sota-rust` rules/05 §9,
`sota-javascript-typescript` rules/05 ("Command injection via child_process").
This is the shape of trap that lives in the *language* skill while you are reading
the *domain* one, so the routing that brought you here will not bring you to it.

**R5.4 — Files handed to children:** pass FDs not paths where possible; if paths,
re-validate with `openat2(RESOLVE_BENEATH)` semantics; never let a child write to a
directory it can also execute from (no write+exec staging dirs).

## 6. macOS specifics

**R6.1 — `sandbox-exec` is deprecated-but-load-bearing.** The CLI is marked
deprecated and the SBPL profile language is undocumented/unsupported, yet Apple's own
daemons and major sandboxing users still ride on the same Seatbelt kernel mechanism
(`sandbox_init` / libsandbox). Reality for 2026: it still works and there is no
public replacement for ad-hoc CLI sandboxing; using it = accepting an unstable,
unsupported interface. Write deny-by-default profiles:

```scheme
(version 1)
(deny default)
(allow file-read* (subpath "/usr/lib") (subpath "/System"))
(allow file-read* file-write* (subpath (param "JOB_DIR")))
(deny network*)
(allow process-exec (literal (param "TOOL")))
```
Test profiles against escape basics: `/var` vs `/private/var` aliasing, symlinks,
Mach services (`(deny mach-lookup ...)` matters as much as files).

**R6.2 — App Sandbox for shipped apps:** entitlement-based
(`com.apple.security.app-sandbox` + minimal `files.user-selected`,
`network.client`, etc.), enforced at install; security-scoped bookmarks for
persistent file access. Hardened Runtime + notarization additionally block
unsigned-code injection (`allow-dyld-environment-variables` and
`disable-library-validation` entitlements are findings unless justified).

**R6.3 — No user namespaces/seccomp on macOS:** real isolation for untrusted code on
Mac hosts = `Virtualization.framework`/`Containerization` VMs (Apple's container
tooling runs each container in its own lightweight VM — rank-3-style isolation) or
remote Linux sandboxes. Endpoint Security framework (`ES_EVENT_EXEC`, `ES_EVENT_OPEN`)
is the supported *detection* layer — auth events can block, but ES is an EDR
building block, not a per-process sandbox API.

---

## Audit checklist

- [ ] Every parser of attacker-supplied complex formats runs in a dedicated
      short-lived process with seccomp+Landlock (or bwrap/minijail/nsjail), fd-only
      I/O, no network, no exec; never in the main service process.
- [ ] Workers are one-per-input across trust domains; outputs re-encoded/normalized
      and size-capped before the parent trusts them.
- [ ] Privileged operations brokered: workers hold FDs, not paths/secrets; broker
      uses `openat2` resolve flags (no string prefix checks); broker requests
      logged and rate-limited.
- [ ] Lockdown sequencing visible in code: privileged init → irrevocable restrict →
      then and only then process untrusted input.
- [ ] WASM: WASI preopens scoped to the job dir only; fuel/epoch + memory limits
      set; host imports audited (copy-then-validate guest memory); engine itself
      process-sandboxed for untrusted modules.
- [ ] No `vm`/`vm2`/eval-jail as a boundary; V8 isolates backed by per-tier
      sandboxed host processes with CPU watchdog + heap limits.
- [ ] No `shell=True`/`exec`/`sh -c` with tainted input anywhere (grep for it);
      argv arrays with pinned flags and `--`; no exec-capable argument gadgets
      reachable (`find -exec`, `tar --checkpoint-action`, delegates…).
- [ ] Subprocesses get explicit minimal env, absolute paths, `close_fds`,
      process-group kill on timeout, bounded stdout/stderr.
- [ ] The timeout is a real deadline in *this* language — pipes held by a
      grandchild cannot extend it past the limit (Go: `cmd.WaitDelay` set) — and
      memory is capped with `RLIMIT_DATA`/cgroup, never `RLIMIT_AS` (R5.3a, `02`
      R7.2a).
- [ ] macOS: shipped apps use App Sandbox + Hardened Runtime with minimal
      entitlements; untrusted code on macOS runs in VMs, not sandbox-exec alone;
      any sandbox-exec use documented as unsupported-interface risk.
