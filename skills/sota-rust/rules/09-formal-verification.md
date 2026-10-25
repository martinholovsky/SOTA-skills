# 09 — Formal verification: Kani and Flux

Scope: proving a property of Rust code rather than sampling for it. A fuzz target or a property
test runs inputs it happens to generate; a **Kani** harness explores every execution within a
bound and reports a concrete counterexample, and **Flux** checks refinement types in signatures
at compile time. Both are opt-in per crate, by criticality: nothing here is a default for every
crate. Miri, sanitizers and fuzzing stay in [rules/03](03-unsafe-discipline.md) §4 and
[rules/05](05-security-supply-chain.md) §6; this file is the layer above them, not a replacement.

**BUILD** uses §1–§8: choose the tool, write the harness, make it able to fail, wire it into CI.
**AUDIT** uses §9 and the checklist: a proof is a control, and the defect that matters is the one
that prints success over nothing. Behaviour quoted here was measured on **Kani 0.68.0 / CBMC
6.11.0** in a Linux container on 2026-10-24 unless a line says otherwise; Flux was **not**
executed and its lines come from its own install guide. Re-measure on the release you run.

## 1. When to prove, and with which tool

Cumulative obligations — each line adds to the ones above it, it does not replace them:

- **Untrusted-input parser or decoder** → fuzz target and property test always (rules/05 §6);
  a Kani harness when the input can be bounded and the crate is security-critical.
- **`unsafe` wrapper** → Miri (rules/03 §4), plus a Kani harness on the *safe* API for panic
  freedom and pointer validity. Flux does not reason about the `unsafe` body.
- **Index, length or range relations every caller must respect** (`off + len <= buf.len()`, a
  port range) → Flux, if the crate can carry one pinned-nightly CI job (§8).
- **Whole-function behaviour, bit tricks, arithmetic on lengths** → Kani.
- **Unbounded input** → Kani function and loop contracts (§5), or Flux.
- **Custom sync primitives, lock-free code** → `loom` or `shuttle`; neither Kani nor Flux covers
  interleavings.
- **Neither is feasible for a security-critical unit** → fuzzing plus property tests, and write
  the residual down where the next reader sees it.

**First pass, before hand-writing anything:** `cargo kani autoharness -Z autoharness` builds and
runs bounded harnesses for every eligible function whose arguments implement `kani::Arbitrary`.
Measured: without `-Z autoharness` it exits 2 (``The `autoharness` subcommand is unstable and requires -Z autoharness``); with it,
it found a planted `(v * 2) / 2` overflow. Its output defaults to `terse`. It is triage, not a
proof plan: it asserts nothing about results (§6).

Why these two and not a deductive verifier (Verus, Creusot — both actively released): those
prove more, and need ghost code and proof scripts maintained beside the implementation. Kani runs
on unmodified Rust and Flux keeps its specs in signatures, so the proof stays green on every
change at a cost a team will keep paying. That is a cost argument, not a maturity one; a crate
that needs full functional correctness may pay it.

## 2. Writing a Kani harness

- Harnesses live in `#[cfg(kani)] mod proofs`, named `verify_<fn>_<property>`, written as a
  literal `#[kani::proof]` or `#[kani::proof_for_contract(f)]` on a free function — not produced
  by a macro or `cfg_attr`, so static review and the §9 probes can see them. Declare the cfg:
  `[lints.rust] unexpected_cfgs = { level = "warn", check-cfg = ['cfg(kani)'] }`.
- Every input comes from `kani::any()`. Every constraint — `kani::assume`, `kani::any_where`,
  `#[kani::requires]` — carries a comment saying why it is a real precondition.
- **Bound:** the smallest that covers every structural case, one element past each limit; state
  it and why in the harness's doc comment.
- **Assert on the result**, not only on the call: the invariant of `Ok(v)`, the invalidity of the
  input on `Err`. A harness that discards the result proves panic freedom only, and its name and
  doc comment say so.
- **End every harness with an unconditional `kani::cover!()`** — after the call and after every
  assertion. §3 says why "after the last constraint" is not enough.
- `#[kani::should_panic]` only in a negative control. Measured: a real out-of-bounds bug under
  `should_panic` reported `VERIFICATION:- SUCCESSFUL (encountered one or more panics as expected)`
  and exit 0 — a found bug becomes a pass.
- **Timeouts:** split the harness, add contracts, or stub callees with verified contracts
  (`#[kani::stub_verified]`). Never shrink the bound below the structural minimum and never pass
  `--no-unwinding-checks`: measured, a harness whose loop exceeded `#[kani::unwind(3)]` failed on
  `unwinding assertion loop 0` (exit 1), and the same run with `--no-unwinding-checks` printed
  `VERIFICATION:- SUCCESSFUL` (exit 0) beside a warning to use `--unwinding-assertions`.

## 3. Vacuity: a proof over nothing prints the same success line

An over-constrained `assume` or a contradictory `requires` makes a proof hold over **zero**
executions, and Kani's verdict does not change. Measured, four vacuous shapes, each
`VERIFICATION:- SUCCESSFUL`, exit 0 — three of them with a false assertion behind the constraint:

| shape | how it empties the input space |
|---|---|
| `kani::assume(a > 10 && a < 5)` | contradictory constraint |
| `if a > 20 { … }` after `assume(a < 10)` | dead branch |
| `let Ok(p) = parse(&b) else { return; };` where `parse` never returns `Ok` | **early return**: semantically an `assume`, and no probe for `assume` sees it |
| `impl kani::Arbitrary` whose `any()` calls a contradictory `kani::assume` | **hidden in the type**: the harness body looks unconstrained |

The guard is `kani::cover!`, and its placement decides what it guards. A cover after the last
`assume` misses the early-return and `Arbitrary` rows. **A bare `kani::cover!()` as the final
statement** caught the three shapes that empty the whole harness (rows 1, 3 and 4): each printed
`** 0 of 1 cover properties satisfied (1 unreachable)`. It cannot catch a dead branch, because the
harness end is still reachable: that needs a cover **inside** each intended path, which reported
the dead one `UNREACHABLE`. So: one cover per intended path, plus the trailing one. Covers go in
harness bodies only; one in library code is unreachable from unrelated harnesses.

**The trap behind the guard: an unsatisfied cover does not fail the run either.** Kani still
prints `VERIFICATION:- SUCCESSFUL` and exits 0. RFC 0003 ("Status: Stable") describes a
`--fail-uncoverable` option and a summary line reading `cover statements satisfied`; the released
tool has neither — `--fail-uncoverable` is rejected as an unexpected argument (with and without
`-Z unstable-options`) and the line reads **`cover properties satisfied`**. A gate written from the
RFC therefore matches nothing and passes everything (§4). A design doc states intent; only a run
reports behaviour. This is the "gate that cannot fail" of
[`sota-devsecops` rules/09](../../sota-devsecops/rules/09-gates-that-hold.md) §2 and
[`sota-code-security` rules/12](../../sota-code-security/rules/12-verifying-the-verifier.md) §1,
arriving inside a verification tool.

## 4. A gate that fails on vacuity

Run Kani through this, never bare `cargo kani`, in any job whose harnesses carry covers:

```bash
#!/usr/bin/env bash
# kani-cover-gate: fail on any unsatisfied or unreachable kani::cover!, and on a summary
# format it no longer recognises. Usage: kani-cover-gate.sh <cargo kani args>
set -uo pipefail
PAT="${KANI_COVER_PAT:-\*\* [0-9]+ of [0-9]+ cover properties satisfied}"
fmt=""; prev=""
for a in "$@"; do
  case "$a" in --output-format=*) fmt="${a#*=}" ;; esac
  [[ "$prev" == --output-format ]] && fmt="$a"
  prev="$a"
done
[[ -z "$fmt" && "${1:-}" == autoharness ]] && fmt=terse   # autoharness defaults to terse
if [[ -n "$fmt" && "$fmt" != regular ]]; then
  printf 'kani-cover-gate: --output-format=%s drops the per-check lines the drift guard counts; use regular\n' "$fmt" >&2; exit 2
fi
out="$(cargo kani "$@" 2>&1)"; rc=$?
printf '%s\n' "$out"
(( rc == 0 )) || exit "$rc"                      # Kani's own failure wins
checks=$(grep -cE '^Check [0-9]+: .*\.cover\.[0-9]+$' <<<"$out" || true)
sums="$(grep -oE "$PAT" <<<"$out" || true)"
nsums=$(grep -c . <<<"$sums" || true)
if (( checks > 0 && nsums == 0 )); then
  printf 'kani-cover-gate: %s cover checks but no summary line matched; output format changed?\n' "$checks" >&2; exit 3
fi
bad=0
while read -r _ n _ m _; do [[ -n "$n" && "$n" != "$m" ]] && bad=1; done <<<"$sums"
if (( bad )); then printf 'kani-cover-gate: unsatisfied or unreachable kani::cover!\n' >&2; exit 1; fi
printf 'kani-cover-gate: %s cover checks, %s summaries, all satisfied\n' "$checks" "$nsums" >&2
```

Measured on Kani 0.68.0, shellcheck clean. Live runs: exit **1** on a contradictory-`assume`
harness, on a dead-branch harness, and on a run mixing a good harness with a vacuous one; exit
**3** with the pattern mutated to the RFC's wording, which is the format-drift guard firing.
Replayed (recorded Kani output fed through a `cargo` shim, so the arguments reach only the gate):
exit **1** on the early-return and `Arbitrary` harnesses and on a real bug (Kani's own failure),
exit **0** on two good harnesses and on a clean harness with no covers (`0 cover checks`).
**Why it refuses `terse` (exit 2), `autoharness` included:** terse output has no per-check lines,
so the drift guard cannot fire — replayed, terse output with the summary wording changed passed
as `0 cover checks, 0 summaries, all satisfied`.

Why it counts cover *checks in Kani's output* rather than `cover!` in the source: a source search
cannot tell which harnesses this run selected. Measured on a gate that did (a pathless
`rg -q 'kani::cover!'`): replayed on a clean harness with no covers in a crate whose source has
covers, it failed (exit 1); with its stdin a pipe, its pathless `rg` read the pipe and the guard
passed (exit 0); in an image without ripgrep it printed `command not found` and passed a vacuous
harness (exit 0).

**Its negative controls are part of it.** Keep a harness with a contradictory `assume` and a
trailing cover in the repository, run the gate on it in CI, and require exit 1; run it once with
`KANI_COVER_PAT` set to a pattern that cannot match, and require exit 3. A gate shown failing once
at adoption proves nothing about the next Kani release.

## 5. Flags that silently change what is checked

| what | without the flag | measured |
|---|---|---|
| `#[kani::proof_for_contract(f)]` | build error: *requires activating the unstable `function-contracts` feature* | loud — good. `requires`/`ensures` on a function no contract harness names: not measured |
| `#[kani::loop_invariant(...)]` | **ignored, silently**: the loop is unrolled instead | a deliberately **false** invariant passed with `VERIFICATION:- SUCCESSFUL`, exit 0; with `-Z loop-contracts` it failed its step check (the base check passed: the invariant held on entry) |
| `#[kani::stub_verified(f)]` | build error: *requires activating the unstable `stubbing` feature* — `-Z function-contracts` alone is not enough | loud |
| `--harness name` | **substring** match: `--harness verify_get_bug` also ran `verify_get_bug_should_panic` | add `--exact` and the fully qualified name in CI |

Put the unstable features in `Cargo.toml` so a bare `cargo kani` and CI agree. Measured:
`[package.metadata.kani.unstable]` with `function-contracts = true` made a bare `cargo kani`
verify a contract harness; `[package.metadata.kani] flags = ["-Z", "function-contracts", "-Z", "loop-contracts"]` did not
(the same build error as no flag). `loop-contracts` and `stubbing` were not measured in that table.

## 6. A postcondition needs teeth: mutation adequacy

A satisfied cover proves the **input** side is non-empty. It says nothing about the **output**
side: a postcondition that holds for every implementation passes too.
`model-checking/verify-rust-std` #630 shows merged contracts of that shape — an `ensures` that a
type invariant already guarantees, so it holds for an implementation that ignores its argument.

So a harness, or a contract's `ensures`, must **fail against at least one mutated
implementation** of the function it covers (verify-rust-std #617's second criterion, "mutation
adequacy"). Mutate the body by hand — return a constant, drop a bound check — run the harness,
require `VERIFICATION:- FAILED` naming the broken check, revert, and record the run beside the
harness. A harness never seen failing is the instrument that has never been shown capable of a
hit ([`sota-testing` rules/06](../../sota-testing/rules/06-property-fuzzing-mutation.md) covers
mutation testing generally). `autoharness` (§1) asserts nothing about results, so it proves panic
and UB freedom only and is never evidence of this.

## 7. Contracts on `unsafe` code: where the proof stops

A verified contract is used *as an assumption* wherever `stub_verified` replaces the callee, so a
contract that is too weak makes every caller's proof unsound. Recorded in the std verification
effort (`model-checking/verify-rust-std`; issues read, not reproduced here):

- **Aliasing must be in the precondition.** #693: `Rc`/`Arc::get_mut_unchecked`'s contract did
  not encode its aliasing precondition. The borrow checker supplies that for `&mut T`; for raw
  pointers the contract has to say it, and a `modifies` clause has to name every write.
- **Provenance must be in the precondition.** #712: allocator `dealloc`/`realloc` contracts did
  not require the pointer to come from the allocator.
- **Uninitialised memory has blind spots.** #671: Kani's uninitialised-memory checker could not
  analyse `MaybeUninit` prefixes in `flt2dec`. Code using `MaybeUninit` keeps its Miri job.
- **Recursion:** Kani's contract docs describe inductive verification of recursive functions and
  do not state that termination is proven. Treat termination as your obligation.

## 8. Flux, operationally

From Flux's install guide (not executed here): Flux is built **from source** (`cargo xtask
install`) on a pinned nightly from its `rust-toolchain.toml`, and needs `liquid-fixpoint` and
`z3` on `PATH`. It has no versioned releases, so pin the git dependency by commit and allowlist
exactly that source in `cargo deny`; the guide's own example `flux-rs = { git = … }` carries no
`rev`, which [rules/05](05-security-supply-chain.md) §1 does not accept.

- Opt in per crate: `[package.metadata.flux] enabled = true`; run with `cargo flux`. Specs are
  written as `#[spec(fn(n: i32) -> bool[0 < n])]` after `use flux_rs::attrs::*;`.
- **`trusted` and `opaque` are both opt-outs.** `trusted` skips a function body; `opaque` hides a
  type from Flux (verify-rust-std #716 removes both together, one on `ptr::NonNull`). Each needs a
  written reason and a Kani harness or test that covers what Flux no longer checks.
- On an internal compiler error, `FLUXFLAGS="-Fflux-verbose" cargo flux` names the last function
  checked: mark that one `trusted` with a reason, or report upstream — never drop the crate from
  the job.
- A separate CI job on Flux's toolchain, gating only the crates that opt in.

## 9. AUDIT: a proof is a control

Audit a crate's proofs the way [`sota-code-security` rules/12](../../sota-code-security/rules/12-verifying-the-verifier.md)
audits any verifier: first ask whether it can fail, then what it covers.

1. **Inventory.** `rg -c '#\[kani::(proof|proof_for_contract)' -t rust .` and the CI job that runs
   them. A harness no job runs is documentation.
2. **Can it fail?** Is the job's verdict the cover gate (§4) or a bare `cargo kani`? Are its
   negative controls present and run? Does any flag in §5 change what is checked —
   `--no-unwinding-checks`, `should_panic`, a missing `loop-contracts`, `--harness` without
   `--exact`?
3. **Vacuity, per harness.** Does each end in `kani::cover!()` (§3)? For a harness that does not,
   read its constraints, its early returns and the `Arbitrary` impls of its input types before
   believing its verdict.
4. **Teeth.** Pick the security-critical harnesses, mutate the function, re-run (§6). A harness
   that still passes is a finding, at the severity of the property it claims.
5. **Scope.** For each contract on `unsafe` code, check the §7 preconditions. For Flux, count
   `trusted`/`opaque` and read each reason.

Severity: a proof cited as the evidence for a security property that is vacuous, unrun or
mutation-blind is that property **unverified**, rated as if no proof existed — usually High for
an untrusted-input parser. A missing trailing cover with the harness otherwise sound = Low.

## Audit checklist

- [ ] **Security-critical crate parsing untrusted input with no fuzz target and no Kani harness**
      (§1): `rg -l 'fuzz_target!|#\[kani::proof' -t rust .` empty in such a crate = Medium.
      A security-critical crate wrapping `unsafe` behind a safe API (§1) where
      `rg -l '#\[kani::proof' -t rust .` is empty and `rg -l 'unsafe' -t rust .` is not = Low.
- [ ] **Harnesses that do not end in `kani::cover!()`** (§3): the loop below
      prints `file:line harness-name` for each `#[kani::proof]`/`#[kani::proof_for_contract]`
      function whose body does not end in `kani::cover!()`. It brace-counts lines, so a brace inside a
      string or comment confuses it, and a macro-generated harness is invisible; a hit is a lead,
      not a finding.
      `rg -l '#\[kani::proof' -t rust . | while IFS= read -r f; do awk 'FNR==1{p=0;inb=0} /#\[kani::proof/{p=1} p&&!inb&&/fn [A-Za-z0-9_]+/{match($0,/fn [A-Za-z0-9_]+/);n=substr($0,RSTART+3,RLENGTH-3);l=FNR;inb=1;d=0;s=0;b=""} inb{b=b $0 "\n";o=gsub(/\{/,"{");c=gsub(/\}/,"}");if(o>0)s=1;d+=o-c;if(s&&d<=0){g=b;gsub(/[ \t\n]+/,"",g);if(g!~/kani::cover!\(\);?\}$/)print FILENAME":"l" "n;inb=0;p=0}}' "$f"; done`
      (a loop, not `awk … $(rg -l …)`: an empty file list would leave awk reading stdin)
- [ ] **A bare `cargo kani` as the CI verdict** (§4): `rg -n 'cargo kani' .github/ .gitlab-ci.yml Makefile justfile scripts/ 2>&1`
      — each hit not wrapped by a cover gate passes vacuous proofs = Medium where the proofs
      back a security claim. Then confirm the gate's negative controls run.
- [ ] **Flags that change what is checked** (§2, §5):
      `rg -n --hidden -g '!.git' -e '--no-unwinding-checks' -e 'kani::should_panic' -e '--harness' .` (`--hidden`, or CI under `.github/` is never read) — `--no-unwinding-checks` anywhere = Medium;
      each `should_panic` outside a named negative control = Medium; `--harness` without
      `--exact` = Low.
- [ ] **Contract or loop attributes without their feature** (§5):
      `rg -l 'loop_invariant' -t rust .` non-empty while
      `rg -n --hidden -g '!.git' -g 'Cargo.toml' -g '*.y*ml' -g '*.sh' -g 'Makefile' -g 'justfile' -e 'loop-contracts\s*=\s*true' -e '-Z\s*loop-contracts' .` is empty (a `flags = ["-Z", "loop-contracts"]` array does not count: §5 measured that form not enabling `function-contracts`, and whether it enables `loop-contracts` was not measured — treat it as off) = **High** for the
      properties those invariants claim: they are not checked, and the run passes.
      Same pair for `stub_verified` → `stubbing` (loud, but a job "fixed" by deleting the
      harness hides it).
- [ ] **Harness that calls and discards** (§2): `rg -l '#\[kani::proof' -t rust . | while IFS= read -r f; do rg -nH 'let _ = ' "$f"; done`
      — inside a harness, panic freedom only; Low unless the harness is cited for more.
- [ ] **Postcondition with no recorded mutation run** (§6): for each harness or `ensures` cited
      as evidence, is there a record of it failing on a mutant? None = Medium for
      security-critical code.
- [ ] **Flux opt-outs** (§8): `rg -n -g '*.rs' -e '#\[(flux_rs::|flux::)?(trusted|opaque)\b' .` (the bare form is what `use flux_rs::attrs::*;` produces) — each without a
      reason and a covering harness or test = Low; a Flux job that excludes a crate after an ICE =
      Medium.
