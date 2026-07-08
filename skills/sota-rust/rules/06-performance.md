# 06 — Performance

Rust is fast by default; most "slow Rust" is accidental allocation, debug
builds, or architecture — not missing micro-tricks. The discipline: measure,
fix the proven bottleneck, re-measure. Never trade soundness or clarity for an
unmeasured win (see rules/03 §1 on unsafe "optimizations").

## 1. Measure first — profiling toolbox

- **Always profile release builds** with debug symbols:

```toml
[profile.release]
debug = true            # or: [profile.profiling] inherits = "release", debug = true
```

  The #1 perf bug report is "Rust is slow" on a debug build (10–100x off).
- **CPU profiles**: `samply record ./target/release/app` (works macOS+Linux,
  Firefox Profiler UI) or `perf record -g --call-graph dwarf` + `perf report`
  on Linux; `cargo flamegraph` for one-command flamegraphs. Wide flat flames =
  death-by-allocation/memcpy; deep narrow = algorithmic hotspot.
- **Microbenchmarks**: `criterion` (statistical, regression-detecting) or
  `divan` (lighter, allocation counting). Use `std::hint::black_box` to stop
  the optimizer deleting your benchmark. Bench realistic input sizes —
  O(n²) hides at n=10.
- **Allocation profiling**: `dhat-rs` (heap profiling as a test harness),
  `heaptrack` (Linux); divan's `AllocProfiler` for per-bench alloc counts.
- **Async**: tokio-console for task-level stalls (rules/04); `tracing` spans +
  `tracing-timing`/OTel histograms for production latency attribution.
- Lock contention: `perf lock` / mutex wrappers with metrics; high sys-time +
  low throughput on many cores is the contention signature.

## 2. Allocation reduction — the usual 80%

Allocations (and the copies feeding them) dominate most non-numeric Rust
hotspots.

- **Borrow in signatures** (`&str`, `&[T]` — rules/01 §1) so callers don't
  allocate to call you.
- **Reuse buffers in loops**:

```rust
// BAD: fresh String/Vec per iteration
for record in records { let mut line = String::new(); render(record, &mut line); out.write_all(line.as_bytes())?; }

// GOOD: clear-and-reuse keeps capacity
let mut line = String::new();
for record in records {
    line.clear();
    render(record, &mut line);
    out.write_all(line.as_bytes())?;
}
```

- **`with_capacity`** when the size is known (`Vec`, `String`, `HashMap`);
  growth is amortized but reallocation+memcpy of large buffers still hurts.
  (Untrusted sizes: cap it — rules/05 §6.)
- **`Cow<'_, str>`** for transform-sometimes functions: borrow the common
  case, allocate only when modified. Don't `Cow` everything — it infects
  signatures; use where the borrow-rate is meaningfully high.
- **`SmallVec`/`ArrayVec`/inline strings (`compact_str`)** only with profile
  evidence that small-collection allocs dominate; `SmallVec` adds branch +
  size costs and is a pessimization when it spills or gets moved a lot.
- **Avoid intermediate collections**: `collect()` then re-iterate is two
  passes + an allocation; keep it lazy until the terminal op. `format!` into
  `write!(buf, ...)`; `Vec<String>` + `join` into a single fold/`itertools::join`
  when hot; `to_string()` in comparisons (`x.to_string() == y`) never.
- String building: `push_str`/`write!` over repeated `+`/`format!`.
- Interning/arenas (`bumpalo`, `typed-arena`, `lasso`) for parser/compiler
  workloads with many small same-lifetime objects — wholesale drop, zero
  per-object free.

## 3. Accidental clones & copies

- Hot-path `.clone()` of `String`/`Vec`/maps found in a profile: restructure
  ownership (rules/01 §1) — pass borrows down, return owned up, `Arc<str>`/
  `Arc<[T]>` for shared immutable data cloned often (refcount bump vs deep
  copy; also half the size of `Arc<String>`'s double indirection).
- Large types moved by value are memcpys: 1KB struct passed through 5 call
  frames = 5KB of copying. `clippy::large_types_passed_by_value`,
  `clippy::large_enum_variant` (box the big variant), `clippy::large_stack_arrays`.
  Async: oversized futures (big locals held across await) — `clippy::large_futures`,
  box the future or shrink the locals.
- Hidden copies: `*slice.to_vec()` where a borrow works, `as_bytes().to_vec()`,
  `iter().cloned()` where `iter()` + borrows suffice (`clippy::cloned_instead_of_copied`
  for Copy types — `copied()` is explicit and free).
- Derive `Copy` for small (≤ ~16-byte) plain-data types — clone noise gone,
  and the compiler stops you when it grows? It won't — so re-check `Copy`
  types' sizes when fields are added (`static_assertions::assert_eq_size!`).

## 4. Iterator fusion & loop shape

- Iterator adapter chains compile to single fused loops — no intermediate
  materialization, bounds checks elided. Trust the chain; verify with a
  benchmark when in doubt, not by rewriting to indices.
- Keep bounds-check elision intact: iterate (`for x in &xs`, `zip`) instead of
  `xs[i]` under a manually-checked index; when indexing is unavoidable, hoist
  one `assert!(n <= xs.len())` so LLVM elides the per-element checks.
- `extend` over push-in-loop (`vec.extend(iter)` can use size hints and
  specialized memcpy paths); `collect::<Vec<_>>()` from a sized iterator
  preallocates exactly.
- `chunks_exact`/`array_chunks` over `chunks` in SIMD-able inner loops (the
  exact variant lets LLVM vectorize without remainder branches).
- Data layout beats instruction tweaks: struct-of-arrays for scanned columns,
  `Vec<T>` over `Vec<Box<T>>` (pointer-chasing kills cache), sort+binary-search
  or `HashMap` with `FxHash`/`ahash` (default SipHash is DoS-resistant but
  slow — switch only for non-attacker-controlled keys, see rules/05).
- Parallelize embarrassingly-parallel CPU work with `rayon`
  (`par_iter`) — after confirming single-thread is actually optimized;
  parallel O(n²) is still O(n²).

## 5. Release profile settings

```toml
[profile.release]
lto = "thin"            # near-fat-LTO wins, fraction of the compile cost; "fat" for final binaries if it measures better
codegen-units = 1       # better codegen, slower builds — for release artifacts
# opt-level = 3 is default; try "s"/"z" for size-bound targets (embedded/wasm)
strip = "symbols"       # smaller binaries (keep debug=true in a separate profiling profile)

# panic = "abort"       # smaller/faster, no unwinding — decide per rules/02 §5
                        # (kills catch_unwind containment; not for libs that embed elsewhere)
```

- `panic = "abort"`: ~smaller binary, removes landing pads; cost = no panic
  containment (rules/02/05). Choose deliberately for servers; fine for CLIs.
- `overflow-checks = true` in release for security-sensitive services
  (rules/05 §3) — measure, it's typically <2%.
- Target-specific codegen for owned deployments:
  `RUSTFLAGS="-C target-cpu=native"` (or a fixed `target-cpu=x86-64-v3`) —
  unlocks AVX2+ vectorization; never for distributed portable binaries.
- **PGO** for the last 5–15% on hot services: `cargo pgo` (or manual
  `-Cprofile-generate` → run representative load → `-Cprofile-use`); BOLT on
  top for large binaries. Only worth wiring once the easy wins are done.
- Build-time hygiene: keep one `profiling` profile; don't ship `debug = true`
  symbols accidentally in size-sensitive contexts (use `strip` + split-debuginfo).

## 6. Allocators & zero-copy I/O

- **Global allocator swap** is the cheapest multithreaded-throughput win in
  alloc-heavy services: `mimalloc` or `tikv-jemallocator` as `#[global_allocator]`
  often yields 5–30% on multithreaded alloc-heavy loads vs system malloc
  (glibc malloc contends; macOS/musl mallocs are slow). Measure with your
  workload; jemalloc additionally gives heap profiling (`jeprof`) in prod.
  musl-target deployments almost always want this (musl malloc is a known
  multithreaded bottleneck).
- **`bytes::Bytes`** for network payloads: cheaply cloneable, sliceable,
  refcounted views — one recv buffer shared across framing/parsing/handlers
  without copies. Pair with `tokio_util::codec` framing.
- **Zero-copy parsing**: borrow from the input (`&'a str` fields,
  `#[serde(borrow)]` with `serde_json::from_slice`) instead of owning
  `String` fields — turns deserialization allocations into pointer
  arithmetic; `zerocopy`/`bytemuck` for fixed-layout binary views (rules/03
  for the safety side).
- **Writes**: unbuffered `write!` to a raw `File`/`TcpStream` syscalls per
  call — wrap in `BufWriter` (and remember to flush; dropped `BufWriter`
  errors are swallowed). `vectored writes` (`write_vectored`) for
  header+body patterns.
- mmap (`memmap2`) for large read-mostly files beats read-into-Vec; the
  safety caveat (file truncated under you = UB) is real — confine to files
  you control or accept advisory locking.

## 7. Build-time performance (developer loop)

Slow builds are a perf problem too — they tax every iteration.

- `cargo check`/rust-analyzer for the inner loop, not `cargo build`.
- Linker: `rust-lld` is already the default on `x86_64-unknown-linux-gnu`
  since Rust 1.90 (opt-out: `-C linker-features=-lld`); `mold` is the further
  Linux upgrade, and manual `-C link-arg=-fuse-ld=lld` pays only on targets
  where lld isn't the default yet.
- Split heavy generics: generic shells delegating to non-generic inner fns
  (`fn run(p: impl AsRef<Path>) { fn inner(p: &Path) {...} inner(p.as_ref()) }`)
  cut monomorphization bloat (binary size AND compile time).
- `cargo build --timings` to find the long pole; feature-trim heavy deps
  (`tokio` full vs needed features, `syn` full); move optional integrations
  behind features (rules/07 §5).
- Workspace split so hot-edit crates are leaves, not roots (rules/01 §9);
  proc-macro and build.rs crates dominate cold builds — audit their cost.

## 8. Don'ts

- Don't sprinkle `#[inline(always)]` — it defeats the inliner's cost model and
  bloats icache; `#[inline]` only on small cross-crate hot functions (and it's
  unnecessary for generics, which are already monomorphized downstream).
- Don't micro-optimize before architecture: batching, caching, removing a
  network round-trip, or a better algorithm beats any amount of `SmallVec`.
- Don't benchmark on laptops with thermal throttling / background noise and
  publish 3% wins; criterion's noise floor on shared CI is ~5%+ — gate
  regressions with thresholds, not single runs.
- Don't unsafe-away bounds checks without a flamegraph showing them (§1,
  rules/03).

## Audit checklist

- [ ] Benchmarks exist for claimed-hot code (criterion/divan in `benches/`);
      perf-sensitive PRs include before/after numbers. Claims without
      measurements = Low finding, ask for receipts.
- [ ] `rg '\.clone\(\)|to_vec\(\)|to_string\(\)|to_owned\(\)' -t rust` scoped
      to loop bodies / per-request paths — review each; clippy
      `redundant_clone`, `cloned_instead_of_copied`, `unnecessary_to_owned`.
- [ ] `rg 'format!' -t rust` in hot loops (want `write!` into reused buffer);
      `rg 'String::new\(\)|Vec::new\(\)' -t rust` inside loops (want hoisted
      clear-and-reuse or `with_capacity`).
- [ ] `rg 'collect::<Vec' -t rust` immediately followed by `.iter()`/`into_iter()`
      — needless materialization (`clippy::needless_collect`).
- [ ] `[profile.release]` reviewed: LTO set, codegen-units decision, strip,
      panic-strategy documented; profiling profile with `debug = true` exists.
- [ ] `rg 'inline\(always\)' -t rust` — each needs benchmark justification.
- [ ] Hash maps on hot non-adversarial keys still on SipHash (perf left on
      table) or, inversely, `FxHash/ahash` on attacker-controlled keys
      (HashDoS — High, see rules/05).
- [ ] `clippy::large_enum_variant`, `large_types_passed_by_value`,
      `large_futures`, `needless_range_loop`, `or_fun_call`, `manual_memcpy`
      enabled; `Vec<Box<T>>`-style pointer-chasing layouts in scanned data.
- [ ] Alloc-heavy multithreaded service on default allocator — try
      mimalloc/jemalloc with a benchmark; musl deployments especially.
- [ ] `rg 'File::create|TcpStream' -t rust` write paths without `BufWriter`;
      `rg 'BufWriter' -A20` missing explicit `flush()` before drop.
- [ ] Network parsing copying into owned `String`/`Vec` where
      `Bytes`/`#[serde(borrow)]` would zero-copy.
- [ ] CI bench regression gate (criterion + `critcmp`/`cargo bench` artifacts,
      or codspeed/iai-callgrind instruction counting for noise-free CI).
