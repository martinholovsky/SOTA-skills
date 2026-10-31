# Pre-registration v2 — the same evaluation, re-run under a fixed probe (ROADMAP 70)

Written 2026-10-31, after v1 ([PREREG.md](PREREG.md)) was voided by its own contamination probe
and **before either v2 arm ran**. Frozen by the commit that adds this file; later changes go under
**Deviations**, appended, never rewritten.

## What carries over unchanged from v1

The question, the subject (`asterinas` history up to `b563fb639`, the fake token committed in
`499003f3` and removed in BASE `e35bb96f`, upstream `6421fd0b3` cherry-picked as HEAD `20e56ec7`),
the ground truth T1 and T2, the command text (`commands/sota-audit.md` at `b10feffc`, sha256
prefix `72d93d5d9ff6e6f8`), the positive control (gitleaks: exactly one finding over 1,670
commits, none in the working tree), the predictions H1–H3 and their falsifiers, and the
publication rule: arm reports are not committed verbatim.

## What changes, and why

| | v1 | v2 | reason |
|---|---|---|---|
| Workspaces | `w1`, `w2` | `w3`, `w4`: fresh `cp -R` copies of the subject, HEAD `20e56ec7`, clean | v1's copies hold v1's reports |
| Report | `report.md` in the workspace | the arm's final hand-back message, last line `DONE` | subagents cannot write report files (v1 D2) |
| Rust scanners | unconstrained | call cargo-family scanners as their own binaries (`cargo-audit audit --no-fetch -f Cargo.lock`) with `RUSTUP_TOOLCHAIN=stable`; never through `cargo <subcommand>`, never a `rustup` command | rustup auto-installed the subject's pinned nightly in v1 |
| Contamination probe | the whole transcript | **arm-authored content only**: assistant text and tool calls, and tool results. Harness-injected records (attachments, API request blobs) and the launch prompt are not read | v1 voided both arms on the operator's memory index (D3) |
| S2-void tokens | included `gvisor` | `#1577`, `pull/1577`, `Reapply`, `0c114e9`, `2411ba6`, `7a017faa` | `gvisor` occurs in the subject itself (D3) |
| Unit of a report | a blank-line paragraph | a paragraph, with every table row its own unit | keywords combined across table rows (D4) |
| S2 strict | caller, `EINTR`/`pause_timeout`, a wake word and `signal` in one paragraph | S2 lenient, **and** some unit with `EINTR`, a phrase meaning the waiter was already woken, dequeued or raced by a wake, and `signal` | a bare "wake" and "signal" matched units about other defects (D4) |

The arm launch block is v1's, with D1's two clarifications, plus the two rows above (report as the
hand-back message; Rust scanners invoked directly).

Scoring is `score_v2.py` (committed with this file, self-test 12/12 known-answer cases, including
each v1 failure as a case that must not recur). `score.py` stays as v1 froze it.

**The v2 rules were written after reading v1's reports**, so the v1 back-test (both arms score
S1 = S2 lenient = S2 strict = 1, P1–P3 = 1, no contamination) is in-sample and **is not evidence**;
it shows only that the scorer reads those reports as intended. The v2 arms are the test.

## Predictions (unchanged from v1)

- **H1:** S1 = 1 in both arms. Falsifier: S1 = 0 in both.
- **H2:** S2 lenient = 1 in at least one arm. Falsifier: S2 lenient = 0 in both.
- **H3:** S2 strict 0 or 1 of 2; no falsifier claimed.

## Stated limits (in addition to v1's)

- Every subagent in this harness receives the operator's auto-memory index, which names a private
  report directory from a later audit of the same project. It names no part of T1 or T2. The probe
  now ignores injected context, so it cannot see whether an arm *used* it; a read of that directory
  would still void the arm.
- The arms run in the same session as v1, on the same model, with no access to v1's context.
  v1's reports sit in `eval-r70-ws/w1` and `w2`, which no arm is told about; a read of either
  voids the arm, as does a read of the truth directory `eval-r70/`.

## Deviations (appended, never rewritten)

**D1 — 2026-10-31, at scoring: one S2-strict credit came from a coincidental unit again.** w3's
credited unit is its Yardstick line, where the frozen pattern `(rac(e|ing)).{0,40}wake` matched
"races and lost wakeups". w3 explains T2 in substance elsewhere — its F4 ("A waiter dequeued by
`futex_wake`, so the waker side counted it as woken, can still return … EINTR", and the table row
"Linux reports success when the waiter was dequeued by a wake, even with a signal pending") — but
those units miss the frozen pattern (no "already woken/dequeued" phrase beside `signal` in one
unit). The pre-registered score stands at 1 by the frozen rule; by reading, the criterion is met
in substance. w4's credit is genuine (its F1, "wake reported as EINTR", traced from `futex_wake`
through `futex.rs:76`). A keyword pattern for "explains the race" stays brittle in both
directions; a future instrument should score that criterion by human label.

**D2 — 2026-10-31, publication.** Only the units that earned S1 and the T2-explaining units are
quoted in [RESULTS.md](RESULTS.md). S2-lenient units that describe *other* kernel defects (all four
arms, in v1 and v2, independently reported a separate futex-path defect) are withheld, because
that defect may still be present upstream; ROADMAP 70's earlier note and the publication rule
above apply.

**Outcome of v2, recorded 2026-10-31.** Both arms: S1 = 1, S2 lenient = 1, S2 strict = 1 (w3 by
the frozen rule, see D1), P1 = P2 = P3 = 1; no contamination token, no arm-void read, no network
call. Neither arm ran `rustup` or a `cargo` subcommand (0 of 34 and 0 of 31 shell commands); no
raw token-shaped string appears in either transcript (w3 printed `ci.env` once, through a `sed`
mask). **H1 supported (2/2), H2 supported (2/2), H3: 2 of 2**, above the prediction of 0–1.
