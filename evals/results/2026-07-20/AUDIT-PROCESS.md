# Can we measure an audit-*process* change? — three attempts, all saturated

**Date:** 2026-07-20 · **Model:** `anthropic/claude-sonnet-4.6` · 3× @ temp 0.7

Written to answer a decision, not to publish a win: **should more audit-process
conventions be ported into the library?** Four were candidates (decision-ledger
review, re-measure-the-claim, report+roadmap deliverables, loop-until-dry). The
prerequisite was an instrument that can score audit process at all.

There isn't one. Here is the evidence.

## 1. Regression check — did today's router edits cost anything?

Three changes landed on the router path today: the silent-control pass + routing
rule 20 (#119), the negative-claim evidence burden (#119), and adversarial
refutation (#121). The library's own
[context-rot finding](../../../docs/WHY-COMPLETENESS-RESIDUAL.md) warns that
*adding* guidance can lower the salience of what's already there, so the additions
need a regression check.

**Routing (20 cases, 3× @0.7)** — the routing eval pastes the whole router, so it
sees every one of today's edits:

| Arm | Now | Recorded (2026-07-13 multi-sample) |
|---|---|---|
| without-library | 0.90 | 0.90 |
| **with-library** | **1.00** | **1.00** |
| lift | +0.10 | +0.10 |

**No regression.** Artifact: `routing-3sample-postaudit.json`.

**Completeness — deliberately NOT re-run.** It is structurally blind to today's
changes, and running it would have produced a reassuring number that means
nothing. Proven rather than assumed:

- All **17** skill files the 7 completeness cases load are unchanged since
  `v1.16.0` (`git diff --name-only v1.16.0..HEAD` ∩ loaded set = ∅). None of them
  is `rules/10`, `rules/01-audit-methodology.md`, or any file edited today.
- `principle5()` extracts principles 5–6 live from the router; the extracted text
  is **byte-identical** at `v1.16.0` and HEAD (sha256 `2a36f20d8e51` both sides).
  Principle 3 — where the negative-claim burden was added — sits *before* the
  extraction window.
- `BUILD_WORKFLOW` is a **hardcoded mirror** of router BUILD steps 3–4, unchanged
  since `v1.16.0`, so the falsification clause added to BUILD step 4 is not in the
  eval either.

Every input byte identical ⇒ the eval cannot detect the change. **Finding: the
completeness harness cannot regression-test router BUILD/AUDIT workflow edits.**
The `BUILD_WORKFLOW` mirror is now drifted from the router it claims to mirror —
logged, not silently synced, because syncing changes what the eval measures.

## 2. New instrument — audit PRECISION (false-positive resistance)

Every existing audit eval measures **recall** (find the real vulnerability) and
saturates at +0.00. Refutation targets the opposite failure: upholding a
plausible-but-wrong finding. So: a new set that scores precision.

`cases/finding-adjudication.jsonl` — 30 code+claim pairs, **15 genuine / 15
plausible-but-wrong**. The false half fails for six distinct reasons so no arm can
win by pattern-matching one refutation shape:

| Refutation class | n | Example |
|---|---|---|
| correct-behaviour | 4 | claim says "fail-open"; the error path returns `false` and logs |
| upstream-guard | 3 | claim says SQLi; the column is allowlist-checked with `abort(400)` first |
| misread-mechanism | 3 | claim says RCE; it's `ast.literal_eval`, not `eval` |
| unreachable | 2 | real-looking `os.popen` in a function with no callers |
| inflated-severity | 2 | missing HSTS called "authentication bypass (Critical)" |
| already-mitigated | 1 | "no rate limit on login" — the `@rate_limit` decorator is right there |

Arms: without-library / with-library (router principles + `rules/01`, which
contains §6) / **ablated** (the same minus §6). Metrics: **specificity** (share of
the 15 false claims correctly refuted — the load-bearing number), **sensitivity**
(share of the 15 real ones kept — the guard against an arm that refutes
everything), and accuracy.

### Result

| Arm | Accuracy | Specificity | Sensitivity |
|---|---|---|---|
| without-library | **1.00** | **1.00** | **1.00** |
| with-library | 1.00 | 1.00 | 1.00 |
| with-library-ablated (−§6) | 1.00 | 1.00 | 1.00 |

**§6 contribution: +0.00. Library contribution: +0.00.** Zero wrong answers in any
arm across 3 samples — 90 adjudications per arm, all correct.

Run twice, because the first framing was itself a defect: it enumerated the ways a
claim can fail, which *is* §6's content handed to every arm for free. The neutral
framing ("answer UPHELD if you would ship the claim as written, or REFUTED if you
would not") produced **identical** 1.00s, so the saturation is not a framing
artifact. Artifacts: `adjudication-3sample.json` (leaky framing),
`adjudication-neutral-3sample.json` (neutral).

## 3. What this means

**Four audit instruments now saturate:** audit-hard recall (+0.00), cross-file
repo audit (+0.00), silent-control detection (+0.00 at n=49), and now audit
precision (+0.00). Across recall *and* precision, a frontier model handed the code
and the question does not need the library.

The honest reading is not "the library's audit content is worthless" — it is
**"nothing we can currently measure distinguishes audit-process guidance."** The
plausible reason is consistent across all four: when the relevant code and the
question both fit in one prompt, the model performs at ceiling. What audit
guidance plausibly buys — knowing *which* question to ask, over a repo too large
to hold at once, unprompted — is precisely what a batched single-prompt eval
cannot pose.

### Limitations

- **The cases may be too easy.** Each false claim has its tell inside the snippet
  shown. A real false positive often requires code *not* in front of you. A harder
  set would put the refuting evidence in a different file, or make the correct
  answer "needs verification" rather than a confident verdict.
- **Single model, batched prompt** (30 cases in one call — cases can prime each
  other), single judge-free exact-match scoring.
- 15/15 balance is not a realistic base rate; real audits have far fewer false
  claims than true ones, so specificity here is easier than in the field.

## 4. Recommendation on the four candidate ports

Given no instrument can score these, each addition is an unmeasured judgment call
paid for in context on `rules/01-audit-methodology.md` — already **365/500** lines
and read first in every full audit.

| Candidate | Verdict |
|---|---|
| **Decision-ledger review** (audit past decisions: does the justifying evidence still hold?) | **Port.** Verified zero coverage (`grep ADR\|decision record\|stale justification` across `skills/sota/` → 0 hits). It produces a finding *class* the library currently cannot: a choice justified by a benchmark that no longer reproduces. Distinct capability, not a refinement. |
| **Re-measure the claim this session** | **Fold in** as one clause of the above. Principle 0 already accepts "a reproduced behavior"; the delta is only "re-run the measurement a past decision rests on." |
| **Report + roadmap patch deliverable** | **Skip.** §7 already specifies the report and its remediation roadmap. |
| **Loop-until-dry / ultracode** | **Skip.** `ultracode` is a harness feature — the runtime-bound class deliberately rejected in the v1.16.0 external-review batch. |

And then **stop adding to the audit path** until an instrument exists that can
score it. The candidate design is agentic: a repo too large for one context, a
generic "audit this", scored on whether the right questions get asked unprompted —
the same frontier the [cross-file audit](../2026-07-13/REPO-AUDIT.md) and
[silent-control](SILENT-FAILURE.md) runs both hit.

## 5. Post-decision-ledger regression (same day, after §6 was added)

`rules/01` grew 365 → 428 lines and the router 433 → 443 when the decision-ledger
section landed. Both are pasted whole by an eval, so both were re-run.

| Eval | Before | After decision-ledger | Verdict |
|---|---|---|---|
| Routing (20, 3×@0.7) | with 1.00 / lift +0.10 | **with 1.00** / lift +0.11 | held |
| Audit precision (30, 3×@0.7) | 1.00 / 1.00 / 1.00 | **1.00 / 1.00 / 1.00** | held |

No salience cost detected from any of today's four audit-path additions.

Two evals were **proven unaffected instead of re-run**, on the same
input-identity argument as §1: the completeness set loads 17 skill files, **none**
of them touched today, and its `principle5()` extract is still byte-identical
(sha `2a36f20d8e51`); the silent-control set pastes the `sota-code-security`
rules, **unchanged** since PR #119.

### The ablation arm caught its own breakage

The first run of this regression **aborted**:

```
§6 markers not found — ablation would silently no-op
```

Adding the decision-ledger section renumbered *Adversarial verification* from §6
to §7, and `run-adjudication.py` had hardcoded `"## 6. Adversarial verification"`.
Without the guard the ablation would have found nothing to remove, silently
returned the **full** corpus as the "ablated" arm, and reported a fake +0.00
contribution that looked exactly like the real one.

That is the failure this whole line of work is about — a control (the ablation)
that appears to run and does nothing — and it was caught only because the runner
was written to abort rather than proceed. The markers now match on section
**title** rather than number, and the ablation additionally asserts that it
removed a non-trivial block and that the section is genuinely gone. Both guards
were watched to fire before being trusted.

## Appendix — a live false positive, caught by push protection

Case `fa22` originally used a vendor's **published documentation test key**
(`sk_test_4eC…`) — the whole point of the case being that a public test-mode
credential in a fixture is *not* a credential leak. GitHub push protection blocked
the push on its Stripe pattern rule.

Worth recording because it is the same phenomenon the case describes, one level up:
a pattern match that is correct about the *shape* and wrong about the *impact*. Two
things follow.

1. **The scanner was right to block and I was wrong to write it.** A public test key
   is harmless, but committing a real-looking one to a public repo trains readers and
   future scanners on a bad example. It was replaced with an obviously synthetic
   placeholder; the case's meaning is unchanged.
2. **Local gitleaks passed and GitHub's push protection did not.** `.gitleaks.toml`
   disables the entropy-based `generic-api-key` rule so the security skills'
   intentional secret-shaped examples don't false-positive — which also means it
   cannot catch a *vendor-specific* pattern. Two scanners, two coverage sets; the
   server-side one is not redundant.

The eval was re-run after the fixture change rather than assuming the result carried
over — all three arms still 1.00/1.00/1.00. Checking the fixture before trusting the
number is the same discipline `sota-code-security` rules/10 §5 demands.
