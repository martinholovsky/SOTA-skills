# Re-baseline after adding router operating principle 9 — 2026-08-21

Principle 9 (*match the rigour to the stakes*) sits inside the block `principle5()`
extracts, so it **changes the completeness treatment arm**. ROADMAP item 4 requires trim
and re-baseline together. Both runs: `--samples 1 --temp 0.0`, build
`anthropic/claude-sonnet-4.6`, judge `anthropic/claude-opus-4.8`, same 7 cases.

| | `without` | `with` | lift |
|---|--:|--:|--:|
| **before** — router 494 lines, principle-5 block 2353 chars | 0.60 | 0.99 | **+0.39** |
| **after** — router 500 lines, principle-5 block 2838 chars | 0.57 | 0.97 | **+0.40** |

The before-run **reproduces the published headline exactly** (+0.39), which validates the
harness before anything was changed.

## Why the `with` arm's −0.02 is not evidence of harm

**The `without` arm is a natural negative control: it never sees the router** (its prompt
is `case["task"]` alone). It moved **0.60 → 0.57** between two otherwise identical runs.
So `temp 0.0` is *not* deterministic here — run-to-run variation is ≈±0.03, and two cases
account for it (`c2_upload` 0.64→0.55, `c7_pwreset` 0.64→0.55), neither of which the
router could have touched.

The treated arm's −0.02 sits **inside the band the untreated arm just demonstrated**. The
paired design assumed temp-0 determinism; the control disproved that assumption and, in
doing so, made the result interpretable.

## Limits

- **n=1 per arm.** A regression smaller than ≈0.05 could not be detected here.
- The defensible claim is **no evidence of harm**, not *proof of no harm*.
- `ROUTER_BUILD_SHA` is unchanged (`71a9d78ea5e9e341`) — principle 9 is outside the BUILD
  section, so the mirror did not need re-syncing and was verified, not assumed.

Raw: `completeness-before-principle9.json`, `completeness-after-principle9.json`.
