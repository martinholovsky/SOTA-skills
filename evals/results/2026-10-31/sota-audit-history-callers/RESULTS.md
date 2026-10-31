# Results — `/sota-audit` on a diff with real history (ROADMAP 70), 2026-10-31

Two pre-registered runs of the same evaluation: [v1](PREREG.md) (voided by its own probe) and
[v2](PREREG-v2.md) (the result of record). The subject, truth and command text are identical in
both; the arms ran in this Claude Code session (zero API spend), each a fresh subagent with its own
copy of the subject.

## Result of record (v2)

| arm | S1 secret in history | S2 lenient caller located | S2 strict race explained | P1 history scan | P2 caller search | P3 shallow check | contamination |
|---|---|---|---|---|---|---|---|
| w3 | 1 | 1 | 1 (by the frozen rule; see PREREG-v2 D1) | 1 | 1 | 1 | none |
| w4 | 1 | 1 | 1 | 1 | 1 | 1 | none |

- **H1** (both arms find the secret that exists only in history): **supported, 2/2.** Both ran
  `gitleaks git --redact` over the full history including merge commits (1,666 of 1,670 commits
  scanned; the default run skips merges and scanned 1,630), found the one `github-pat` at
  `tools/deploy/ci.env` line 3 in `499003f3`, and reported it by location, type and commit, with
  rotation first.
- **H2** (at least one arm locates the caller-held defect): **supported, 2/2.** Both found
  `futex.rs:76` (`futex_wait_bitset`) as `pause_timeout`'s only caller by symbol search with a
  positive control, and put it in scope as a dependent.
- **H3** (explaining the wake-versus-signal race is the hard half; predicted 0–1 of 2): **2 of 2.**
  w4: "a real futex wake can be reported as EINTR, so the wake is used up and lost", read path from
  `futex_wake` → `remove_and_wake_items` to the new `EINTR` branch, rated Medium and introduced by
  the diff. w3 (substance; the rule's credit was coincidental): "A waiter dequeued by `futex_wake`,
  so the waker side counted it as woken, can still return ETIMEDOUT or (new in this diff) EINTR.
  Linux returns 0 when the waiter was already dequeued", rated Low.

## What it shows, and what it does not

- The two steps the 2026-10-06 A/B could not exercise both **execute and detect** on a real
  repository: the full-history secret scan finds a secret that `HEAD` no longer has, and the diff
  scope's "callers two hops out" reaches the file that holds the defect.
- n = 2 arms and one defect of each kind: direction, not a rate. Same model throughout. The model
  may know asterinas or PR #1577 from training; no upstream-fix token appeared in any arm's own
  output.
- The secret is synthetic (real-shaped); the caller-held defect is real.

## v1, for the record

Both v1 arms scored **VOID** under v1's frozen rules, because the probe read harness-injected
context (the operator's memory index names a private report directory) and used one token,
`gvisor`, that occurs in the subject itself; and the scorer treated a Markdown table as one
paragraph. Post hoc, both v1 arms found the secret and the caller. Details: [PREREG.md](PREREG.md)
D1–D4. The v2 rules were written after reading v1's reports; v2's arms are the test.

## Incidents

- A v1 arm ran `cargo-audit` through the rustup proxy; the subject's `rust-toolchain.toml` made
  rustup attempt a network install of the pinned nightly, against the run's constraints. The lead's
  own damage check (`rustup component list --toolchain …`) then installed that toolchain unasked.
  v2 instructed direct scanner binaries with `RUSTUP_TOOLCHAIN=stable`; neither v2 arm ran rustup
  or a cargo subcommand.
- The harness refuses report-file writes from subagents; reports were taken verbatim from each
  arm's hand-back message.

## Library notes the arms raised (for intake, not acted on here)

- A waiter that gives up on timeout or interrupt must deregister from the wait structure it
  enqueued on; `sota-async-concurrency` rules/05 asks whether "the timeout actually cancels the
  work" but has no probe for this (raised by two arms).
- A file-wide lint suppression (`#![allow(dead_code)]`) can hide an uncalled cleanup function; no
  checklist probe looks for it.
- Running a cargo-family scanner in a repository with `rust-toolchain.toml` can trigger a rustup
  install even under a no-network, no-install constraint.

Arm reports are not committed (publication rule in PREREG.md); they stay local.
