# Why SOTA-skills works — the measured case

Most prompt/skill collections *assert* they make an assistant better. This one
**measures it**, publishes the harness, and reports the numbers by dimension —
including the dimensions where the lift is small or zero.

**What the comparison is.** The headline numbers below are the library
**vs. an *unguided model*** — the same model, same task, with the library loaded
vs. with nothing. Separately, a **fair head-to-head against the most popular
competing libraries** now exists too (see [below](#vs-competing-libraries)). The
control is clean: raw model-API calls (OpenRouter, no Claude Code config or skill
registry), and a **different** model grades each artifact **blind** to which arm
produced it. Reproduce it yourself with [`evals/`](../evals/); full methodology,
per-case data, and honest limitations are in the
[baseline writeup](../evals/results/2026-07-10/BASELINE.md).

## Measured lift over an unguided model

**Each row names the model it was measured on.** A lift can be overtaken by model
progress and then read as current when it is historical — that is exactly what happened
to defect-avoidance between February and June 2026, and it is stated rather than hidden.

| Dimension | What it tests | Clean lift |
|---|---|---|
| **Completeness** | best practices embedded from a bare "build X" prompt (7 tasks) | **+0.39** (0.59 → 0.98) `sonnet-4.6` · **+0.44** `gpt-5.1` · **+0.38** (0.62 → 1.00) on **`sonnet-5`, the current flagship** — it did not expire |
| **Freshness** | current 2026 facts (RFCs, CVEs, EOLs, versions, spec editions; 32) | **+0.50–0.53** (32-case; +0.65 on a 20-case run) — `sonnet-4.6` |
| **Defects avoided** | security defects the model must not *write*, from a spec that never names one (7 classes) | **+0.19** (0.81 → 1.00) on `sonnet-4.6`; **+0.00** on `gpt-5.1`, whose bare arm already scores 1.00 |
| Defects avoided — *with positive evidence of the safe path* | the stricter reading of the same 7 classes; **does not saturate on either model** | **+0.33** (0.29 → 0.62) sonnet · **+0.10** (0.43 → 0.52) gpt-5.1 |
| Routing | which skill area applies to a task | +0.09 to +0.14 |
| Audit | recognizing a textbook vulnerability | +0.00 |
| Audit — **real repo, real CVEs** | recall *and* precision on 16 live BOLA sites (Harbor v2.5.1) | +0.00 / +0.00 |

The lift is only "small" if you measure the easy dimensions. The two that matter
most for *building* software are the two that are large:

- **Completeness is the thesis.** Told to "build X" (an API, an upload handler, a
  webhook receiver, a password-reset flow…) with **no** security or logging cues,
  a base model embeds ~60% of best practices and *systematically* skips tests,
  rate limiting, structured logging, and transport hardening. With the full
  library — the router's short universal non-negotiables (operating principle 5),
  the matched rules, and the **BUILD self-audit** (check the diff against each
  audit checklist and fill every gap) — coverage reaches **~99% across 7 tasks**
  (6 of 7 perfect). What occasionally still slips is a *single* low-salience
  cross-cutting item, and it's a **finite-constraint-budget** effect, not a
  coverage gap: the guidance was in context with a checklist item, but a long,
  dense rules context makes some items fade (a measured attention effect — see
  [WHY-COMPLETENESS-RESIDUAL.md](WHY-COMPLETENESS-RESIDUAL.md), where *adding* the
  "missing" rule made it worse and a short salient reminder fixed it). This gap is
  unlikely to be recoverable by "just verify via web search" (untested — no search
  arm was run; the reasoning is direct): an agent won't search
  *"should I add rate limiting"* — it simply omits it. That makes completeness the
  library's most defensible, least-redundant value. And it is not a
  paste-simulation artifact: seven **live** agents driven through the real router
  BUILD workflow scored **0.99 (6/7 perfect)**, matching the simulation (0.987 vs 0.988)
  ([live-agent validation](../evals/results/2026-07-13/LIVE-BUILD.md)).
- **Defects avoided — the newest result, and the one that changes the argument.**
  Every other lift here measures what a model *puts into* code. This measures what it
  **leaves out**. The setup is deliberately adversarial to the library: a build spec
  states the operational pressure that makes each unsafe shortcut attractive — *"cache
  it"*, *"must never 5xx"*, *"keep the guard cheap"*, *"it may come back"* — and **never
  names a defect**. Scoring is avoidance of a failure pattern the model never sees.
  Unguided, the model writes them: `ORDER BY {sort}` interpolated straight into SQL, and
  a report fetched with no ownership check. With the library: **1.000, three runs, zero
  variance** (unguided **0.809**). On the stricter measure that also requires *positive
  evidence of the safe path* — not merely the absence of the bad one — **0.29 → 0.62**.

  Why this matters more than its size suggests: **the library's audit passes score +0.00
  on these same classes.** A frontier model already *finds* them. Seven instruments say
  so, and we publish that. So the value on offer was never detection — it is that the
  code arrives without the defect, which is the half no scanner and no review budget
  gives you back. That is the first direct evidence for it.

  **The second model deflates the headline, and we ran it on purpose.** On
  `openai/gpt-5.1` the *unguided* arm already scores **1.000** — it does not write these
  defects, so there is no gap and the lift is **+0.00**. The `+0.19` is therefore
  **baseline-dependent**, exactly as the five-domain breadth test found for completeness:
  the lead tracks the unguided baseline, not the domain — and here, not the model. What
  survives on both is the stricter measure, because neither bare arm saturates there
  (**+0.33** sonnet, **+0.10** gpt-5.1). So the defensible claim is *"closes a
  defect-avoidance gap where one exists"*, and "prevents these defects" is not one we make.

  **Other limits, out loud:** n=3; the treated arm is at **ceiling** (1.000, zero
  variance), so the delta is bounded by the instrument and cannot separate *"the library
  helped"* from *"these cases are easy once guided"*; **one task** (a second needs a new
  instrument — three of seven `fail` patterns are domain-specific); and **prompt length is
  an uncontrolled confound** — the
  guided prompt is ~66k characters against ~4k, so some of the effect may be "more
  instruction to be careful" rather than this library's content. The competitor benchmark
  below controls for that; this pilot does not.
  [Method, per-run scores, all six limits →](../evals/results/2026-08-21/BUILD-SAFE.md)

- **Calibration — measured, and deliberately *not* sold as a lift.** With the library,
  audit reports bound their claims by what was actually run, label unverified findings,
  and condition severity on stated assumptions; unguided reports do it less often
  (**2.67/4 → 4.00/4**, the mover being *conditioning severity on evidence*, 1/3 → 3/3).
  We keep this **off the headline scoreboard on purpose**: it measures adherence to *our
  own reporting doctrine*, which is a far weaker claim than "finds more bugs", and a
  project that scored its own house rules and called it efficacy would deserve the
  scepticism. It is here because a reader deciding whether to trust the audit output
  should know the reports are hedged where the evidence is thin — not because it is a
  selling point.

- **Freshness — the base model is confidently wrong.** On current-2026 facts it
  doesn't merely lack knowledge, it *fabricates* plausible answers (in our 32-case
  set: inventing RFC 9334 for the Entity Attestation Token — it's 9711 — or
  claiming PostgreSQL 17 added `uuidv7()` when it was 18). The library carries the
  verified fact (with-library **0.97**, dead steady across samples; without **0.44
  ±0.03**). A web-search agent would *likely* recover much of this gap (searchable facts —
  predicted, not measured in this harness), so we report freshness as *plausibly*
  partly redundant for tool-using agents — stated plainly rather than inflated.
- **Audit +0.00 is reported, not hidden.** On isolated snippets a capable model
  already recognizes the vulnerability — even the 14 *harder* cases (subtle IDOR,
  SSRF allowlist bypass, TOCTOU, prototype pollution, multi-vuln) score 1.00 in
  both arms.

  **This page used to say a real audit lift "would need whole-repo, cross-file
  context a snippet can't carry". That hypothesis was tested on 2026-08-13 and it
  is false.** Two live agents audited a real container registry at a real
  vulnerable commit — 232 files, ~245k tokens of Go, 16 genuine
  broken-object-level-authorization sites disclosed as 5 CVEs — with the whole
  repository available and no snippet framing. **Recall 15/16 for both arms.
  Precision 1.00 for both arms**, over 59 findings adjudicated blind against the
  code by scorers that passed a 4/4 known-answer control. Severity mix
  indistinguishable. That is the ninth audit instrument to read ≈ +0.00, and the
  explanation this page offered for the previous eight does not survive it.
  [REAL-REPO-AUDIT](../evals/results/2026-08-13/REAL-REPO-AUDIT.md).

  What remains untested is not *more context* but a different **dependent
  variable** — time-to-find, report usability, or whether a non-expert reaches the
  same findings. Accuracy, on every instrument built so far, is saturated in both
  arms.

Robustness: every value dimension is now run **multi-sample** (`--samples 3
--temp 0.7`), and the pattern is consistent — **the with-library arm has
near-zero variance while the unguided arm both scores lower and wobbles.**
Completeness holds at **0.59 → 0.98 (+0.39)**, a two-run mean with the with-arm at
±0.004 between runs (re-verified 2026-07-20/21 against the workflow that actually
*ships*, after the eval's `BUILD_WORKFLOW` mirror was found drifted; see
[MIRROR-VERIFICATION](../evals/results/2026-07-20/MIRROR-VERIFICATION.md)); and it is **not sonnet-specific — three model families from three labs all show a positive lift: `openai/gpt-5.1` +0.44 ([CROSS-MODEL](../evals/results/2026-07-22/CROSS-MODEL.md)) and `google/gemini-3.1-pro-preview` 0.38 → 0.96, **+0.58 at 3 samples/arm** ([CROSS-FAMILY-GEMINI](../evals/results/2026-08-13/CROSS-FAMILY-GEMINI.md))**. The lift tracks the *baseline*, not the lab: the weaker the unguided arm, the larger the gain. Routing sits at **0.90 → 1.00 (+0.10)**,
with-arm ±0.00; freshness at **0.44 → 0.97 (+0.53)**, with-arm ±0.00. The
library's contribution isn't a lucky sample — it removes the unguided model's
case-by-case unreliability ([multi-sample writeup](../evals/results/2026-07-13/MULTI-SAMPLE.md)).

## The claims are dated, and one has already expired

Every number above was measured on `claude-sonnet-4.6` (Feb 2026) or `gpt-5.1`. On
2026-08-21 the **defect-avoidance** row was re-run on `claude-sonnet-5` (Jun 2026) and
went to **+0.000** — the newer model simply does not write those defects unaided, and its
*unguided* strict score equals what `sonnet-4.6` scored **with** the library. Four months
of model progress absorbed that result entirely.

That is the honest frame for everything here: **these lifts measure a gap between a model
and a standard, and the model side moves.** Where a model is already strong, the library
adds nothing measurable; where it is weak — older models, cheaper models, unusual tasks,
the long tail where training data is thin — it closes the gap. That is a real value
proposition and a narrower one than "makes your model better".

**That question was then answered, and the answer is the good one.** Completeness *was*
re-measured on `claude-sonnet-5` the same day: **0.62 → 1.00, +0.38** — unchanged within
the harness's ±0.03 noise floor. The two results together draw a line worth having:

- **Knowledge gaps close with model progress.** "Do not interpolate into `ORDER BY`" is a
  fact about code; newer models have it, and the defect-avoidance lift went to zero.
- **Salience gaps do not.** `sonnet-5` unguided still omits **tests in 7 of 7 tasks**,
  transport in 5, rate limiting in 5 — the same blind spots as its predecessor. Adding
  rate limiting to an endpoint nobody mentioned is not something the model *doesn't know*;
  it is something it doesn't *think of* while doing something else.

So the durable value here is not telling a model things it does not know. It is making
cross-cutting concerns **salient at the moment of writing** — a failure that scales with
task length and context pressure rather than with model weakness, which is consistent with
this project's own root-cause finding in
[WHY-COMPLETENESS-RESIDUAL.md](WHY-COMPLETENESS-RESIDUAL.md), where *adding* the missing
rule made things worse and a short salient reminder fixed it.
[Method and limits →](../evals/results/2026-08-21/COMPLETENESS-SONNET-5.md)

## Vs. competing libraries

The comparisons above are vs. *nothing*. We also ran SOTA head-to-head against the
most-starred competing guidance libraries (by GitHub stars, snapshot 2026-07-14)
on the same 7 build tasks — same rubric,
same blind judge, **content-only** (SOTA's self-audit forcing function turned off,
so its win is the guidance, not the method):

Scores are % of a fixed best-practice rubric the generated code implements
(blind-judged); higher is better.

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="../assets/benchmark-dark.svg">
    <img alt="Best-practice completeness by library: SOTA-skills 99%, affaan-m/ECC 87%, PatrickJS/awesome-cursorrules 83%, alirezarezvani/claude-skills 81%, unguided model 58%." src="../assets/benchmark-light.svg" width="100%">
  </picture>
</p>

| Library | Stars | Completeness |
|---|---|---|
| [**SOTA-skills**](https://github.com/martinholovsky/SOTA-skills) | — | **99%** |
| [affaan-m/ECC](https://github.com/affaan-m/ECC) | ~230k | 87% |
| [PatrickJS/awesome-cursorrules](https://github.com/PatrickJS/awesome-cursorrules) | ~40k | 83% |
| [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | ~23k | 81% |
| unguided model | — | 58% |

This is a **backend** result. On these 7 tasks SOTA-skills wins or ties every one
of the 21 head-to-head cases and loses none — yet the competitors are no strawmen
(all three beat an unguided model by +23 to +28 pts). Where they fall short is the
same place unguided models do: the **cross-cutting production non-negotiables** —
rate limiting, transport/TLS, tests, structured logging — dropped endpoint after
endpoint (even the ~230k-star `affaan-m/ECC` omits rate limiting on 3 of 7 tasks).
That is exactly what SOTA's operating principle 5 + the matched rules exist to close.

**Where the lead holds — it tracks task difficulty, not the domain.** A five-domain
breadth run ([BREADTH.md](../evals/results/2026-07-13/BREADTH.md)) shows SOTA-skills
leads every competitor by ~10 points wherever the base model's default is
*incomplete* — production backend in **any** language (Python 58%→lead +12, Go
67%→+10) and **complex/security-sensitive frontend** (hard SSR/auth 53%→+10) — and
*ties* where the base model is already near-complete (simple React forms 77%→+0,
templated IaC 87%→+0). There's a clean threshold near a 0.7 baseline. So the honest
claim isn't "backend only": SOTA-skills leads **on the tasks a base model gets
wrong** — the harder and less templated, the more it adds — and converges with the
field where guidance can't add what the model already emits. Full method, per-domain
notes, and limits: [competitor benchmark](../evals/results/2026-07-13/COMPETITOR-BENCHMARK.md)
+ [BREADTH.md](../evals/results/2026-07-13/BREADTH.md).

## What you get by design (beyond the numbers)

These are properties of how the library is built — verifiable in this repo, no
comparison to anyone else required.

1. **Auto-routing & composition — describe the task, not the files.** A
   [router skill](../skills/sota/SKILL.md) maps a request to the right
   *combination* of skills (e.g. a websocket endpoint pulls API-design + async +
   code-security together) and applies cross-cutting **universal non-negotiables**
   — rate limiting, transport enforcement, tests — on *any* endpoint regardless
   of which domain skill routed the task. A plain folder of skills has no such
   orchestration. `scripts/install.sh --routing` can make routing always-on.

2. **Freshness-maintained and cited.** Fast-moving claims (versions, RFCs, CVEs,
   EOLs) are web-verified against **primary sources**, not asserted from training
   data. A root `LAST-VERIFIED` stamp records the last full re-verification sweep;
   `scripts/check-freshness.sh` flags the library stale past a **6-month** window,
   and a **monthly** CI job ([`freshness.yml`](../.github/workflows/freshness.yml))
   enforces it. Version numbers appear only as semantic boundaries ("GA since",
   "fixed in"), never as rot-prone "current release is X".

3. **Build *and* audit from the same rules.** Every skill runs in two modes: BUILD
   (apply the rules while writing code) and AUDIT (review existing code). Audit
   findings are actionable, not vague — each cites
   `file:line | rule violated | severity | effort | fix` and maps to a standard
   (CWE, OWASP, MITRE ATT&CK/ATLAS) where one applies.

4. **CI-gated library quality.** Fourteen invariants
   ([`check-invariants.sh`](../scripts/check-invariants.sh)) block a bad change at
   the door: every **skill** file ≤ 500 lines — `skills/*/SKILL.md` and
   `skills/*/rules/*.md`, the files an agent actually loads, and nothing else (so
   the *right* rules load, not a wall of text; README, CHANGELOG and `docs/` are
   prose for people and are deliberately uncapped), every rules file ends with an audit checklist, skill descriptions
   stay within the Agent-Skills spec cap, versions stay in lockstep, the router
   lists every skill, internal Markdown links resolve (no dead cross-references),
   and no internal names leak. Plus gitleaks over the full history.

## Reproduce it

```sh
python3 evals/run-completeness.py     # completeness (build-tasks, blind judge)
python3 evals/run-clean.py --cases evals/cases/freshness.jsonl   # freshness
python3 evals/run-clean.py --cases evals/cases/router.jsonl      # routing

# defects avoided — validate the scorer FIRST, then produce and score the two arms
python3 evals/run-build-safe.py --selftest
python3 evals/run-build-safe-arms.py u OUTDIR anthropic/claude-sonnet-4.6 32000
python3 evals/run-build-safe.py --build OUTDIR

# calibration — the judge is blinded and carries its own two controls
python3 evals/run-calibration.py u REPORT.md anthropic/claude-sonnet-4.6 16000
python3 evals/judge-calibration.py
```

Set `OPENROUTER_API_KEY` (env or `.env`, never committed). See
[`evals/README.md`](../evals/README.md) for the full harness and
[`BASELINE.md`](../evals/results/2026-07-10/BASELINE.md) for the honest writeup.
