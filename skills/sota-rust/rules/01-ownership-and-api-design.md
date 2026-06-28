# 01 — Ownership, Borrowing & API Design

Idiomatic ownership is the difference between Rust that fights you and Rust that
documents itself. These rules cover borrow patterns, smart-pointer selection,
type-driven design (newtype, typestate, builder), trait design, and code layout.

## 1. Borrowing & clone discipline

**Never clone to satisfy the borrow checker.** A `.clone()` whose only purpose is
to silence E0502/E0505 is a design smell: restructure scopes, split borrows, or
take ownership earlier.

```rust
// BAD: clone because `self.items` is borrowed while mutating
let names: Vec<String> = self.items.iter().map(|i| i.name.clone()).collect();
for name in names { self.register(&name); }

// GOOD: split the struct so disjoint fields borrow independently
let (items, registry) = (&self.items, &mut self.registry);
for item in items { registry.register(&item.name); }
```

- Split-borrow via destructuring or accessor methods returning `(&A, &mut B)`.
- For "clone before loop" patterns over small data, `Copy` types or indices are
  cheaper than cloning `String`/`Vec`.
- `std::mem::take` / `mem::replace` extract owned values from `&mut self`
  without cloning (leave a cheap default behind).
- Legitimate clones exist: crossing thread/task boundaries, caching, fan-out.
  Comment intent when a clone looks gratuitous: `// clone: sent to spawned task`.

**Accept the most general borrowed form in APIs:**

```rust
// BAD: forces callers to own/allocate
fn process(s: String, items: Vec<u32>) -> usize { ... }

// GOOD: borrow; caller keeps ownership
fn process(s: &str, items: &[u32]) -> usize { ... }
```

- Parameters: `&str` over `&String`, `&[T]` over `&Vec<T>`, `&Path` over
  `&PathBuf`, `impl AsRef<Path>` / `impl Into<String>` when ergonomics matter
  (but not on hot generic-bloat-sensitive paths — use inner non-generic fn).
- Take ownership (`String`, `Vec<T>`) only when you store the value. Taking
  `&str` then immediately `.to_owned()` forces a copy the caller may have been
  able to move; prefer `impl Into<String>` there.
- Return `&str`/`&[T]` borrowed from `self` where lifetimes allow; `Cow<'_, str>`
  when sometimes-owned (see rules/06 for perf framing).

## 2. Rc/Arc/Box/RefCell: when shared ownership is right

Reach for smart pointers in this order; each step is a justified escalation:

| Need | Tool |
|---|---|
| Heap allocation / unsized / recursion | `Box<T>` |
| Shared ownership, single-threaded | `Rc<T>` |
| Shared ownership across threads | `Arc<T>` |
| Shared + interior mutation, single-threaded | `Rc<RefCell<T>>` |
| Shared + mutation, multi-threaded | `Arc<Mutex<T>>` / `Arc<RwLock<T>>` |
| Shared, replace-on-write, read-mostly | `Arc<T>` + swap (`arc-swap`) |

- `Arc<Mutex<T>>` everywhere is Java-in-Rust. Prefer **ownership trees**
  with message passing (channels) for cross-task state; share only what is
  genuinely shared (config, caches, connection pools).
- `Rc::clone(&x)` / `Arc::clone(&x)` (associated form) — makes "refcount bump,
  not deep copy" greppable.
- Break `Rc`/`Arc` cycles with `Weak` (parent links, observer lists). Audit any
  graph-shaped `Rc<RefCell<...>>` for leaks.
- `RefCell` panics at runtime on double-borrow; confine it to module-private
  state with documented borrow discipline. Never let `RefCell` borrows escape
  across a callback into user code.
- Immutable shared config: `Arc<Config>` (no lock). Read-mostly: `RwLock` only
  if writes are rare AND readers are many; otherwise `Mutex` (simpler, no
  writer starvation surprises).

## 3. Newtype pattern

Wrap primitives that have semantics. `u64` is not a `UserId`.

```rust
// BAD
fn transfer(from: u64, to: u64, amount: u64) -> Result<(), Error>

// GOOD
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct AccountId(u64);
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub struct Cents(u64);
fn transfer(from: AccountId, to: AccountId, amount: Cents) -> Result<(), Error>
```

- Validate at construction: `impl TryFrom<&str> for Email` returning a typed
  error; keep the field private so the only way in is the validated path
  ("parse, don't validate").
- Derive the full expected set (`Debug, Clone, Copy, PartialEq, Eq, Hash`,
  plus `serde` derives behind a feature) — missing derives are friction that
  pushes callers back to raw primitives.
- Implement `Deref` to the inner type **only** for true smart-pointer-like
  wrappers; for domain newtypes expose explicit `as_str()`/`get()` instead
  (Deref leaks the abstraction).
- Newtypes are also the coherence escape hatch: wrap a foreign type to impl a
  foreign trait (orphan rule).

## 4. Typestate pattern

Encode protocol/state machines in the type system so invalid transitions don't
compile. Use when misuse is plausible and states are few.

```rust
pub struct Connection<S> { stream: TcpStream, _state: PhantomData<S> }
pub struct Unauthenticated;
pub struct Authenticated;

impl Connection<Unauthenticated> {
    pub fn authenticate(self, creds: &Creds)
        -> Result<Connection<Authenticated>, AuthError> { ... }
}
impl Connection<Authenticated> {
    pub fn query(&mut self, q: &str) -> Result<Rows, QueryError> { ... } // only here
}
```

- Transitions consume `self` and return the next state — the old state is
  unusable afterward, enforced at compile time.
- Don't typestate everything: runtime enums are right when states are dynamic,
  numerous, or serialized. Typestate shines for build-time-known protocols
  (request builders, handshakes, init-before-use).

## 5. Builder pattern

Use a builder when a constructor would exceed ~4 params or has many optionals.

```rust
let server = Server::builder()
    .bind("0.0.0.0:8080")
    .worker_threads(8)
    .tls(tls_config)            // optional
    .build()?;                  // validation lives here, returns Result
```

- `build()` returns `Result<T, BuildError>` if any combination can be invalid;
  infallible builders may return `T`.
- Owned `self` methods (move-chain) for one-shot builders; `&mut self` methods
  when the builder is configured conditionally across branches. Pick one style
  per builder.
- Required params: take them in `T::builder(required)` rather than failing at
  `build()` — or use typestate builders for compile-time required-field checks
  (what `typed-builder`/`bon` generate). Consider `bon` (2024+) before
  hand-rolling large builders.
- `#[non_exhaustive]` on config structs + builder is the semver-safe way to add
  options later.

## 6. Trait design, sealed traits, coherence

- Keep traits **small and capability-shaped** (`Read`, `Write`, not
  `RepositoryManagerService`). Compose with supertraits sparingly.
- **Sealed traits** prevent downstream impls so you can add methods without a
  breaking change:

```rust
mod sealed { pub trait Sealed {} }
pub trait Backend: sealed::Sealed {
    fn run(&self) -> Output;
    // adding a defaulted method later is non-breaking: no foreign impls exist
}
impl sealed::Sealed for Postgres {}
impl Backend for Postgres { ... }
```

- Orphan rule: you may impl a trait only if you own the trait or the type.
  Workarounds: newtype wrapper, or define a local conversion trait. Never
  paper over it with a blanket `impl<T> From<T>` that will collide later.
- Prefer generics (`impl Trait` / `<T: Trait>`) for hot paths (monomorphized,
  inlinable); `dyn Trait` for heterogeneous collections, plugin registries, and
  to cut compile time/bloat on cold paths. `Box<dyn Error + Send + Sync>` at
  app boundaries is fine.
- Return-position `impl Trait` (and RPITIT in traits, stable since 1.75) over
  boxed returns where the concrete type is single. For public traits needing
  dyn-compatibility with async, use `async-trait` or hand-rolled
  `Box<Pin<...>>` returns (see rules/04).
- Implement standard traits eagerly: `Debug` on everything public (or a manual
  redacting impl for secrets — rules/05), `Default` where a zero-config value
  exists, `Display` + `std::error::Error` on errors, `From` for infallible
  conversions, `TryFrom` for fallible ones. Never impl `Into` directly.
- **`Eq`/`Ord`/`PartialEq`/`PartialOrd`: `#[derive]` them; hand-write only with
  care.** The std library *assumes* their invariants — `PartialEq` symmetry and
  transitivity, `Eq` reflexivity, `Ord` a total order consistent with `Eq`, and
  `PartialOrd`/`Ord` agreement. A manual impl that breaks them is not a compile
  error but silently corrupts `sort`, `binary_search`, `BinaryHeap`,
  `BTreeMap`/`Set`, and dedup — wrong results, lost entries, or a panic
  (`sort_unstable` may panic on a non-total `Ord`). If you must hand-roll,
  define the minimal method (`Ord::cmp`, then `PartialOrd` via `Some(self.cmp)`)
  so the others stay consistent, and never derive `Ord` on a type whose `f32`/
  `f64` field makes the order partial. (ANSSI `LANG-CMP-INV`/`-DERIVE`)

## 7. Exhaustive matching & `#[non_exhaustive]`

- Match exhaustively on **your own** enums; avoid `_ =>` arms so the compiler
  flags every new variant at each match site:

```rust
// BAD: silently swallows future variants
match event { Event::Open => ..., _ => {} }

// GOOD: compiler forces a decision when Event grows
match event { Event::Open => ..., Event::Close => ..., Event::Ping => {} }
```

- Mark public enums/structs `#[non_exhaustive]` when variants/fields will grow;
  downstream is then required to write `_` arms and your additions are
  non-breaking. Don't mark closed sets (e.g. `Ordering`-like) — it destroys
  downstream exhaustiveness checking for no gain.
- `let ... else` for refutable bindings with early return; `matches!()` for
  boolean checks; `if let` chains (stable since 1.88) over nested `if let`;
  `if let` guards in `match` arms (`Some(x) if let Ok(y) = f(x) =>`, stable
  since 1.95) over guard-then-rematch patterns.

## 8. Iterators & combinators

- Iterator chains over index loops: no bounds-check noise, no off-by-one, fuses
  and optimizes as well or better than manual indexing.

```rust
// BAD
let mut out = Vec::new();
for i in 0..xs.len() { if xs[i].active { out.push(xs[i].score * 2); } }

// GOOD
let out: Vec<_> = xs.iter().filter(|x| x.active).map(|x| x.score * 2).collect();
```

- Know the collect targets: `Vec<_>`, `String`, `HashMap<_,_>`,
  `Result<Vec<T>, E>` (fail-fast), `itertools::process_results` for streaming.
- Option/Result combinators over match ladders: `map`, `and_then`, `ok_or_else`,
  `unwrap_or_else`, `?` with `From` conversions. But: a 5-combinator chain that
  needs a comment should be a `match` — clarity wins.
- Use lazy variants on hot/fallible paths: `unwrap_or_else(|| expensive())`,
  `ok_or_else`, not `unwrap_or(expensive())` (argument always evaluated).
- Need the index? `.enumerate()`. Need pairs? `.zip()` / `.windows(2)` /
  `.chunks(n)` — or `array_windows::<N>()` (stable 1.94) when a const-size
  `&[T; N]` lets you destructure without bounds checks. Early exit with side
  results: `try_fold` / `find_map`.

## 9. Module & workspace organization

- Module = privacy boundary, not a filing cabinet. Keep invariant-carrying
  fields private; expose constructors that enforce them. `pub(crate)` over
  `pub` until something external needs it.
- Re-export the public API at the crate root (`pub use module::Type;`) so the
  internal tree can move without breaking users; keep the public surface flat
  and small.
- Prefer `foo.rs` + `foo/` subdir over `foo/mod.rs` (one convention per repo).
- Workspace structure for anything beyond one crate:

```toml
# /Cargo.toml
[workspace]
members = ["crates/*"]
resolver = "3"                 # edition 2024 default

[workspace.package]
edition = "2024"
rust-version = "1.85"
license = "MIT OR Apache-2.0"

[workspace.dependencies]       # single source of version truth
serde = { version = "1", features = ["derive"] }
tokio = { version = "1", features = ["rt-multi-thread", "macros"] }
```

  Member crates use `serde = { workspace = true }`. Split crates along compile
  and dependency boundaries (`core` no-heavy-deps, `cli`, `server`), not by
  "layer" for its own sake — each crate is a compile unit and a semver unit.
- Binary crates: keep `main.rs` thin (arg parsing + call into `lib.rs`) so the
  logic is testable.

## Audit checklist

- [ ] `rg '\.clone\(\)' -t rust` — review each hit near a `for`/borrow error
      fix; flag clones of `String`/`Vec`/large structs that exist only to
      appease borrowck. `clippy::redundant_clone` (note: known false negatives,
      still run it).
- [ ] `rg 'fn \w+\((&self, )?\w+: (String|Vec<|PathBuf)' -t rust` — owned params
      that are only read → should borrow.
- [ ] `rg '&String|&Vec<|&PathBuf|&Box<' -t rust` — double-indirection params
      (`clippy::ptr_arg` catches most).
- [ ] `rg 'Arc<Mutex<' -t rust` — each one: is shared mutable state actually
      required, or would a channel/owner task work? Check for `Weak` where
      graphs/cycles appear: `rg 'Rc<RefCell<'`.
- [ ] `rg '_ =>' -t rust` — wildcard arms on local enums lose exhaustiveness;
      `clippy::wildcard_enum_match_arm` (pedantic) to enforce.
- [ ] Public enums likely to grow without `#[non_exhaustive]`:
      `rg -B2 'pub enum' | rg -v non_exhaustive`.
- [ ] `rg 'for i in 0\.\.' -t rust` — index loops; check `clippy::needless_range_loop`.
- [ ] `rg 'unwrap_or\([a-zA-Z_]+\(' -t rust` — eager argument evaluation
      (`clippy::or_fun_call`).
- [ ] Raw primitive IDs in public signatures: `rg 'fn .*\b(id|user|key)\w*: (u32|u64|i64|String)'`.
- [ ] Public trait intended to be closed but unsealed — can a downstream crate
      impl it? If yes and that's unintended, seal it.
- [ ] Hand-written comparison impls: `rg 'impl (PartialEq|Eq|PartialOrd|Ord)' -t rust`
      — verify invariants (total order, consistency with `Eq`, symmetry); a
      broken `Ord` corrupts `sort`/`BinaryHeap`/`BTreeMap` or panics. Prefer
      `#[derive]`. `LANG-CMP-INV`. `clippy::derive_ord_xor_partial_ord`,
      `clippy::non_canonical_partial_ord_impl`.
- [ ] Multi-crate repo without `[workspace.dependencies]` → version drift;
      `cargo tree -d` to find duplicate dependency versions.
- [ ] Clippy gates for this file's concerns: `clippy::needless_pass_by_value`,
      `clippy::trivially_copy_pass_by_ref`, `clippy::large_enum_variant`,
      `clippy::rc_buffer`, `clippy::mutable_key_type`.
