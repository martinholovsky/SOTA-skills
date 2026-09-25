# 03 — Unsafe Discipline

`unsafe` does not turn off the rules; it makes **you** the checker. The standard
is: minimal surface, sound encapsulation, documented invariants, and tooling
(Miri, sanitizers) that re-checks what the compiler can't.

## 1. Minimize, then isolate

- First question for any `unsafe`: **is there a safe equivalent?** Most are:
  `split_at_mut`, `MaybeUninit` + `Vec::spare_capacity_mut`, `bytemuck`/`zerocopy`
  for transmutes, `OnceLock`/`LazyLock` for lazy statics, `Cell`/`RefCell` for
  interior mutability, `Pin` APIs instead of raw self-references. The safe
  surface keeps growing — 1.93 stabilized `MaybeUninit` slice APIs
  (`assume_init_ref`/`assume_init_mut`/`write_copy_of_slice`), retiring many
  hand-rolled init loops.
- Performance claims require receipts: an `unsafe` "optimization"
  (`get_unchecked`, skipped UTF-8 checks) without a benchmark showing the safe
  version is the bottleneck is a finding. Bounds checks usually vanish under
  iterators or a single up-front `assert!(len <= buf.len())` hoisting.
- Isolate unsafe in **small modules/crates with a safe public API** whose
  soundness can be argued locally. The privacy boundary is the soundness
  boundary: if a `pub` field or safe method can break the invariant your
  unsafe code relies on, the abstraction is unsound *even if no caller does it
  today*.

```rust
// Sound abstraction: invariant (`init <= N`) is privately owned,
// every safe method maintains it, unsafe is locally justifiable.
pub struct FixedVec<T, const N: usize> {
    buf: [MaybeUninit<T>; N],
    init: usize, // INVARIANT: buf[..init] is initialized
}
impl<T, const N: usize> FixedVec<T, N> {
    pub fn push(&mut self, v: T) -> Result<(), T> {
        if self.init == N { return Err(v); }
        self.buf[self.init].write(v);
        self.init += 1;
        Ok(())
    }
    pub fn as_slice(&self) -> &[T] {
        // SAFETY: buf[..init] is initialized (struct invariant, maintained
        // by push/pop; init never exceeds N).
        unsafe { slice::from_raw_parts(self.buf.as_ptr().cast(), self.init) }
    }
}
```

## 2. SAFETY comments — non-negotiable

**Every `unsafe` block carries a `// SAFETY:` comment proving each obligation
of the called API is met.** Every `unsafe fn` and unsafe trait impl carries a
`/// # Safety` doc section stating what callers/implementors must uphold.

```rust
// BAD
let x = unsafe { *ptr };

// GOOD
// SAFETY: `ptr` comes from Box::into_raw in `Self::new`, is non-null and
// aligned, and is not freed until Drop; no &mut alias exists because we
// hold &self and the field is not otherwise exposed.
let x = unsafe { *ptr };
```

- The comment addresses the **specific preconditions** in the unsafe API's
  docs (non-null, aligned, initialized, valid-for-reads, no aliasing, lifetime
  bounds) — not vibes like "this is fine".
- Enforce mechanically: `#![deny(clippy::undocumented_unsafe_blocks)]`
  (and `clippy::missing_safety_doc`, which is warn-by-default). Edition 2024:
  `unsafe_op_in_unsafe_fn` is warn-by-default — write explicit `unsafe {}`
  blocks inside `unsafe fn` so each obligation site is visible and commented.
- An `unsafe fn` whose safety contract can't be written in one paragraph has
  the wrong API shape — split it.

## 3. The UB catalog — what actually bites

Audit unsafe code against these, in observed-frequency order:

1. **Aliasing violations**: constructing two `&mut` to the same data, or a
   `&mut` while a `&` lives — *creating* the reference is UB even if unused.
   Classic source: `&mut *ptr` twice, casting `&T` → `&mut T` (always UB —
   rustc's `invalid_reference_casting` lint, deny-by-default; the old
   `clippy::cast_ref_to_mut` name is a rename alias),
   `Vec`/self-referential pointer invalidated by reallocation.
2. **Uninitialized memory**: `mem::uninitialized()` (deprecated, instant UB
   for most types) and `MaybeUninit::assume_init` before full init. Reading
   uninit bytes is UB even for `u8`. Use `MaybeUninit`, `Vec::spare_capacity_mut`,
   `ptr::write` (not `*ptr = v`, which drops the uninit "old value").
3. **Transmute abuse**: size/alignment mismatch, invalid bit patterns (`bool`
   not 0/1, invalid enum discriminant, null fn pointer, uninhabited types),
   transmuting `&T` lifetimes, transmuting between repr(Rust) types whose
   layout is unspecified. Prefer `bytemuck::{cast, Pod}` / `zerocopy`
   (derive-checked), `f32::from_bits`, `ptr::cast`. Transmuting to extend a
   lifetime is a soundness hole, full stop.
4. **Invalid values & ranges**: producing a `str` with invalid UTF-8 via
   `from_utf8_unchecked` on unvalidated input; out-of-range `char`;
   `NonZero*`/`NonNull` holding zero/null.
5. **FFI lifetimes & ownership**: returning a pointer into a Rust object the C
   side outlives; freeing with the wrong allocator (must round-trip
   `Box::into_raw`/`Box::from_raw`, or expose `mylib_free`); double-free when
   C calls a destructor twice; `CString::new(s).unwrap().as_ptr()` — temporary
   dropped at end of statement, dangling pointer (`temporary_cstring_as_ptr`
   lint). Struct layout across FFI requires `#[repr(C)]`.
6. **Unwinding across FFI** — see rules/02 §5. A Rust panic leaving an `extern "C"`
   fn **aborts** since 1.81 (a DoS, no longer UB); a foreign exception unwinding
   into Rust through a `"C"` declaration is still UB.
7. **Data races**: `unsafe impl Send/Sync` on types containing raw pointers or
   `Cell`-like internals without an argument; `static mut` (deprecated pattern;
   edition 2024 denies `static_mut_refs`) — use `AtomicX`, `OnceLock`,
   `Mutex`, or an `UnsafeCell` inside a wrapper with a hand-written
   `unsafe impl Sync` whose SAFETY comment states who synchronises access
   (`SyncUnsafeCell` is nightly-only — E0658 on stable 1.97.1).

## 3a. Layout, provenance, and Pin — the subtler contracts

**Layout:** `repr(Rust)` layout is unspecified and may differ between
compilations — any unsafe code assuming field order/offsets needs `#[repr(C)]`
(FFI, byte-casting) or `#[repr(transparent)]` (newtype with identical ABI to
its single field — required for soundly casting `&Wrapper<T>` ↔ `&T`).
Enum-discriminant tricks need explicit `#[repr(u8)]`-style declarations.
`bytemuck::Pod`/`zerocopy::FromBytes` derives verify these statically — prefer
them over manual offset math; for unavoidable offsets use
`core::mem::offset_of!` (stable), never hand-computed constants.

**Pointer provenance:** a pointer is more than an address. Casting ptr→int→ptr
strips provenance and is UB-adjacent under strict provenance; round-trip with
`ptr.with_addr(...)`/`ptr.map_addr(...)` (strict provenance APIs, stable) or
keep it as a pointer. Pointers derived from a `&T` may only access that `T`'s
bytes for that borrow's lifetime — offsetting into a sibling field via a field
reference is UB even if the address is "right". Run Miri with
`-Zmiri-strict-provenance` to catch the class.

**Pin:** `Pin<&mut T>` promises T won't move again until drop. Unsafe code
relying on pinning must uphold the drop guarantee (pinned memory must be
dropped before reuse, can't be deallocated without drop) and never hand out
`&mut T` from `Pin<&mut T>` for `!Unpin` types except via `map_unchecked_mut`
with a SAFETY argument that the projection is structural. Hand-rolled
self-referential types: use `pin-project` (safe projections, checks the rules)
instead of manual `unsafe` projections — hand-rolled pin projections are a
recurring soundness-bug source even in expert crates.

**Drop interaction:** `ManuallyDrop` + `ptr::read` patterns (taking ownership
out of `&mut self` in `Drop`) must guarantee no double-drop on every path
including panics; `mem::forget` is safe but leaks — unsafe code may NOT rely
on Drop running for soundness (leakpocalypse rule: `Rc` cycles + `mem::forget`
make "Drop always runs" a false invariant).

## 3b. The FFI boundary — types that cross, values that arrive

The `improper_ctypes` / `improper_ctypes_definitions` lints (warn-by-default) reject
types with no C layout — measured on rustc 1.97.1, `String` and `&str` in an `extern`
signature both warn. They are **silent on types whose layout is fine but whose values
are restricted**: an `extern "C" fn` taking a `#[repr(u8)]` enum or a `bool` compiles
with no warning (measured). A C caller that passes `7` or `2` then *produces an invalid
value*, which the Reference lists as immediate UB — a `bool` must be 0 or 1, an `enum`
must have a valid discriminant, a `fn` pointer and a reference must be non-null, a
`char` must not be a surrogate.

- **Restricted types arrive as integers and are checked in Rust.** Take `u8`/`c_int`/
  `u32` and convert with `TryFrom` (or a `match` with a rejecting arm) into the
  `enum`/`bool`/`char`. Never declare an `enum`, `bool`, `char`, `&T`, `&str` or bare
  `fn` pointer as a parameter or field that *foreign* code fills — unless the foreign
  side is type-checked for it (a C++ `enum class` bound by a generator), or the value
  is opaque and only Rust ever creates it. (ANSSI FFI-CKNONROBUST, -CKINRUST, -NOENUM)
- **Foreign pointers are raw pointers, checked before use.** Receive `*const T`/`*mut T`
  and test `is_null()` (and alignment, where it is not guaranteed) before `&*p` — or
  receive `Option<&T>` / `Option<NonNull<T>>`, which std guarantees have the pointer's
  size and call ABI with `None` as null, so a null arrives as `None` instead of as UB.
  A bare `&T` parameter is a promise the C caller can break. (FFI-CK-PTR-VALID,
  FFI-INPUT-PTR, FFI-CK-INPUT-REF-VALID)
- **Callbacks are `Option<unsafe extern "C" fn(..)>`.** A non-`Option` fn-pointer type
  asserts non-null, and C passes `NULL` for "no callback" routinely. `unsafe` plus the
  exact ABI makes every call site an audited `unsafe` block. (FFI-MARKEDFUNPTR, -CKFUNPTR)
- **Platform-width C types come from `core::ffi`.** `c_long` is `i64` on 64-bit
  non-Windows targets and `i32` on Windows, and `c_char`'s signedness varies by
  architecture (both read from `core::ffi`'s source). Writing `i64` for `long` is a
  layout mismatch on Windows. (FFI-PFTYPE)
- **Generate bindings, don't hand-write them.** `bindgen` (C → Rust) and `cbindgen`
  (Rust → C header) keep both sides' sizes and alignments consistent. Regenerate in CI,
  or diff the committed output against a fresh run so the header cannot drift from
  the code. (FFI-AUTOMATE, FFI-TCONS)
- **Opaque foreign types are distinct Rust types, not `*mut c_void`.** The Nomicon
  pattern `#[repr(C)] pub struct Handle { _data: (), _marker: PhantomData<(*mut u8,
  PhantomPinned)> }` gives each handle its own type, so a `Foo*` cannot be passed where
  a `Bar*` is expected, and withholds `Send`/`Sync`/`Unpin`. Never an empty `enum`: it is
  uninhabited, and a reference to one is a UB footgun (Nomicon). Rust types exposed to C
  go out the same way — a pointer to an incomplete struct plus a constructor/destructor
  pair. (FFI-R-OPAQUE, FFI-C-OPAQUE)
- **Ownership is one-sided and wrapped.** Whoever allocates frees (§3 item 5). A foreign
  allocation lives in a Rust owner whose `Drop` calls the foreign free function. A value
  moved *by value* into foreign code abandons its destructor, so such types should be
  `Copy` and must not implement `Drop`. Expose Rust to other languages only through a
  dedicated `extern "C"` API module (`cdylib`/`staticlib` plus a generated header), not by
  exporting internal functions. (FFI-MEM-OWNER, -WRAPPING, -NODROP, FFI-CAPI)

## 3c. Leaks are safe, not free

`mem::forget` is safe because, in the std docs' words, "Rust's safety guarantees do not
include a guarantee that destructors will always run" — which is why §3a forbids unsafe
code from relying on `Drop`. The operational half is separate: **every leak API skips the
destructor.** In a long-running service a per-request leak is an unbounded-memory DoS, and
for a secret it is an erasure that never happens (rules/05 §5).

- **`mem::forget`: don't.** To suppress a drop, hold the value in `ManuallyDrop` and hand
  it back with `ManuallyDrop::into_inner` (or drop it explicitly) on every path.
  `clippy::mem_forget` (restriction) enforces it at the crate root, but it fires only
  when the forgotten type has drop glue — measured, a denied lint failed the build on
  `mem::forget(Vec)` and said nothing about `Box::leak` in the same file. (ANSSI
  MEM-FORGET, MEM-FORGET-LINT, MEM-MANUALLYDROP)
- **`Box::leak` / `Vec::leak` / `String::leak`: once-per-process data only.** The std
  docs call `Box::leak` "mainly useful for data that lives for the remainder of the
  program's life". Reached per request or per connection, it is a leak with a counter.
  Prefer `OnceLock`/`LazyLock` for the once-per-process case. No lint covers these, so
  only a search does. (MEM-LEAK, MEM-NO-LEAK)
- **`into_raw` / `into_non_null` is a leak until the matching `from_raw` runs.** This
  covers `Box`, `Rc`, `Arc`, `Weak` and `CString`. Pair the two in one owner on every
  path, including errors, and call `from_raw` only on a pointer that came from the same
  type's `into_raw` (§3 item 5). In a crate with no `unsafe`, an `into_raw` has no
  legitimate partner. (MEM-INTOFROMRAWALWAYS, -ONLY, MEM-NORAWPOINTER)
- `Rc`/`Arc` cycles leak silently — rules/01 §2 (`Weak`). (MEM-MUT-REC-RC)

## 4. Miri, sanitizers, fuzzing — CI for the unchecked

Any crate with non-trivial `unsafe` runs **Miri in CI**:

```yaml
# .github/workflows/miri.yml (core job)
- run: rustup toolchain install nightly --component miri
- run: cargo +nightly miri test
  env:
    # many-seeds reruns under seeds 0..64 to vary scheduling/allocation
    # nondeterminism; strict provenance catches ptr-int abuse
    MIRIFLAGS: "-Zmiri-strict-provenance -Zmiri-many-seeds"
```

- Miri checks the aliasing model — **Stacked Borrows by default**, Tree
  Borrows opt-in via `-Zmiri-tree-borrows` —
  plus init, alignment, leaks — but **only on executed paths**: unsafe code without tests
  is unaudited code. Write tests that exercise every unsafe branch.
- Miri can't run FFI/syscall-heavy paths; for those use sanitizers:
  `RUSTFLAGS="-Zsanitizer=address" cargo +nightly test` (ASan), TSan for
  concurrency claims, and `loom` for testing lock-free/atomic algorithms
  exhaustively.
- Parsers and any unsafe-touching decoder: fuzz with `cargo fuzz` (libFuzzer)
  — fuzzing + Miri/ASan is the practical soundness net (see rules/05 §6).

## 5. Supply-chain visibility of unsafe

- `cargo geiger` reports unsafe usage across the dependency tree — use it to
  *direct review attention*, not as a verdict (unsafe ≠ unsound; zero-unsafe ≠
  sound). Heavy-unsafe deps doing things std could do = replace.
- Prefer audited foundations: `bytemuck`/`zerocopy` over hand transmutes,
  well-known FFI `-sys` crates over bespoke bindings.
- `#![forbid(unsafe_code)]` in crates that need none — it's a semver-visible
  promise and makes regressions un-mergeable. Workspace-wide:
  `[lints.rust] unsafe_code = "forbid"` with per-crate opt-out.
- Record unsafe review in `cargo vet` audits (criteria `safe-to-deploy` +
  unsafe review) — rules/05 §2.

## 6. Soundness review protocol (for AUDIT mode)

For each `unsafe` block, in order:

1. Identify the exact unsafe operations (deref, call, transmute, impl).
2. List each documented precondition of those operations.
3. Check the SAFETY comment discharges **all** of them (missing comment =
   automatic finding; wrong comment = worse).
4. Hunt invariant escapes: can safe code (pub fields, safe methods, trait
   impls, `Deref`, `Drop`, panics mid-modification, reentrancy via callbacks)
   break the invariant the unsafe block assumes? Panic-safety: if user code
   (closures, `T: Clone`, comparators) can panic while your invariant is
   temporarily broken, Drop/unwinding observes broken state → need guard
   objects or `catch_unwind` reasoning.
5. Check `Send`/`Sync`: any manual `unsafe impl` needs a written argument per
   field; raw pointers suppress auto-derive for a reason.
6. Confirm Miri runs over this code path in CI; if not, that's a finding
   regardless of how correct the code looks.

## Audit checklist

- [ ] `rg 'unsafe' -t rust --count-matches` — map the surface first; unsafe
      outside dedicated modules/crates is a structure finding.
- [ ] Undocumented blocks: `rg -B2 'unsafe \{' -t rust | rg -v 'SAFETY'` (then
      verify by eye); enforce `clippy::undocumented_unsafe_blocks`.
- [ ] `rg 'transmute' -t rust` — each one: why not `bytemuck`/`zerocopy`/
      `from_bits`/`cast`? Lifetime-extending transmute = Critical.
- [ ] `rg 'from_utf8_unchecked|get_unchecked|assume_init|set_len' -t rust` —
      verify the stated invariant actually holds on all paths incl. panics.
- [ ] `rg 'static mut|&mut \*\(|as \*mut' -t rust`; compiler lints
      `static_mut_refs`, `invalid_reference_casting` must be deny.
- [ ] `rg 'unsafe impl (Send|Sync)' -t rust` — require per-field justification
      comment; absence = High.
- [ ] FFI: `rg 'extern "C"' -t rust` — check `#[repr(C)]` on crossing types,
      panic containment, allocator pairing (`into_raw`/`from_raw` symmetry),
      `as_ptr()` on temporaries.
- [ ] **Values that foreign code fills** (§3b):
      `grep -rnE -A12 'extern "C(-unwind)?"' --include='*.rs' . | grep -E '(: *|-> *)(bool|char|&)|: *(unsafe )?extern "C(-unwind)?" fn|(: *|-> *)[A-Z][A-Za-z0-9_]*([,;)]|$| *\{)'`
      — an inbound `bool`, `char`, `&T`, non-`Option` fn pointer, or a capitalised by-value
      type that turns out to be an `enum` = UB on one bad value, High (Critical if the
      caller is attacker-influenced). `improper_ctypes` does not flag these. Hits inside
      function bodies are noise — read the signature. Hand-written `i64`/`i32` for C
      `long`/`int` in an `extern` block = Medium (use `core::ffi::c_*`).
- [ ] **Leak APIs** (§3c): `grep -rnE 'mem::forget\(|(Box|Vec|String)::leak\(|\.leak\(\)|ManuallyDrop::new\(|::into_raw\(|\.into_raw\(\)|into_non_null\(' --include='*.rs' .`
      — a hit reached per request or connection = High (unbounded memory); an `into_raw`
      without `from_raw` on every path = Medium; `mem::forget` of a secret-bearing value =
      High (erasure skipped).
- [ ] `grep -rnE 'mem::(uninitialized|zeroed)(::<[^>]*>)?\(' --include='*.rs' .` —
      `uninitialized` = Critical for almost every type; `zeroed` is UB wherever all-zero is
      invalid (references, `NonNull`, fn pointers, most enums). rustc's `invalid_value`
      lint flagged both on concrete types and said nothing for a generic `T` (measured).
- [ ] Layout assumptions: `rg 'repr\(' -t rust` — byte-casting/FFI types have
      `repr(C)`/`repr(transparent)`; `rg 'as usize as \*|usize as \*' -t rust`
      — int→ptr casts (provenance loss).
- [ ] `rg 'map_unchecked_mut|Pin::new_unchecked|get_unchecked_mut' -t rust` —
      hand-rolled pin projections; prefer `pin-project`. Drop impls using
      `ptr::read`/`ManuallyDrop` checked for panic-path double-drop.
- [ ] CI: Miri job exists and isn't `continue-on-error: true`; fuzz targets
      exist for unsafe parsers; `cargo geiger` output reviewed for the tree.
- [ ] Crates with zero unsafe missing `#![forbid(unsafe_code)]` — Low, but
      free hardening.
- [ ] Severity calibration: reachable UB = Critical; unsound public API (safe
      code can trigger UB) = Critical even if unexercised; missing SAFETY
      comment = Medium; missing Miri CI on unsafe crate = Medium.
