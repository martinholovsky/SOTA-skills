# Routing check for v1.42.2 — three descriptions changed

Required by [RELEASING.md](../../../RELEASING.md) §2c and declared for invariant 29. This
release edits three `description` blocks, and a description is the **entire** auto-load
classifier, so editing one competes for every neighbouring skill's traffic.

    python3 evals/run-desc-routing.py --samples 3 \
        --cases evals/cases/desc-routing-regressions.jsonl

    model=anthropic/claude-sonnet-4.6  cases=4  samples=3  temp=0.0
    ablation 'xref': 10 description(s) differ, 907 characters removed

| case | correct (with / without xref) | distractor (with / without) |
|---|---|---|
| `r1_token_count` | 1.00 / 1.00 | 0.00 / 0.00 |
| `r2_absence_sweep` | 1.00 / 1.00 | 0.00 / 0.00 |
| `r3_local_vs_ci_gate` | 1.00 / 1.00 | 0.00 / 0.00 |
| `r4_pwsh_injection` | 1.00 / 1.00 | 0.00 / 0.00 |

    Δ correct         (with − without) = +0.000
    Δ distractor-pick (with − without) = +0.000

**No pinned mis-route returned.** That is what this run establishes, and it is the whole of
what it establishes.

## What changed, and what this run does *not* cover

| skill | change |
|---|---|
| `sota-network-security` | gained `email spoofing, SPF, DKIM, DMARC`; dropped duplicate `WireGuard`, the literal `169.254.169.254` beside `IMDS`, and `segmentation audit` |
| `sota-c-cpp` | gained the embedded-**systems** non-ownership boundary; dropped duplicate `MISRA`, `CERT C`, `memory safety`, `cpp`, `clang-format`, `double-free` |
| `sota-php` | dropped `8.5 current`, a current-version assertion the freshness policy forbids |

**None of the four regression cases exercises any of these three skills.** They route to
`sota-llm-engineering`, `sota-shell-scripting` (twice) and `sota-devsecops`. So this run
checks that the edits did not *disturb* existing routing — a real question, because dropping
`segmentation audit` and `169.254.169.254` removes trigger vocabulary — and it is **not**
evidence that the added terms work.

## The added terms are deliberately NOT pinned with a new case

The obvious move is to add a DMARC case and watch it pass. **That would repeat a mistake this
library has already made and measured.** On 2026-09-14 a PowerShell task was reported as a
routing gap, the fix was written, and the case created to pin it **scored 1.00 before *and*
after** — with 0 of 42 descriptions naming PowerShell. An absent *string* is not an absent
*capability*; a model routes on meaning.

The external audit was careful about this and said so: the DMARC defect is *"omission of an
explicit specialist trigger, not proof that every model will miss."* **No mis-route was ever
demonstrated.** This set's own selection rule is that a case exists *because a specific
mis-route actually happened*, so adding one here for an undemonstrated gap would be
selection-by-outcome dressed as a regression pin — it would score 1.00 and prove nothing.

**Open, and recorded rather than quietly assumed:** whether `sota-network-security` already
owned the anti-spoofing task *before* this change is unmeasured. Settling it needs an arm
built from the pre-change description, which this runner does not have —
`run-prompt-independence.py` has that shape (`--ablate-ref`), the routing runner does not.
Until then the R2 edit is justified as **making ownership explicit**, not as fixing a measured
miss.
