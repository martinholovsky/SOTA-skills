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

| Dimension | What it tests | Clean lift |
|---|---|---|
| **Completeness** | best practices embedded from a bare "build X" prompt (7 tasks) | **+0.39** (0.59 → 0.98) |
| **Freshness** | current 2026 facts (RFCs, CVEs, EOLs, versions, spec editions; 32) | **+0.50–0.53** (32-case; +0.65 on a 20-case run) |
| Routing | which skill area applies to a task | +0.09 to +0.14 |
| Audit | recognizing a textbook vulnerability | +0.00 |

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
  both arms. A real audit lift would need whole-repo, cross-file context a snippet
  can't carry. We say so.

Robustness: every value dimension is now run **multi-sample** (`--samples 3
--temp 0.7`), and the pattern is consistent — **the with-library arm has
near-zero variance while the unguided arm both scores lower and wobbles.**
Completeness holds at **0.59 → 0.98 (+0.39)**, a two-run mean with the with-arm at
±0.004 between runs (re-verified 2026-07-20/21 against the workflow that actually
*ships*, after the eval's `BUILD_WORKFLOW` mirror was found drifted; see
[MIRROR-VERIFICATION](../evals/results/2026-07-20/MIRROR-VERIFICATION.md)); routing at **0.90 → 1.00 (+0.10)**,
with-arm ±0.00; freshness at **0.44 → 0.97 (+0.53)**, with-arm ±0.00. The
library's contribution isn't a lucky sample — it removes the unguided model's
case-by-case unreliability ([multi-sample writeup](../evals/results/2026-07-13/MULTI-SAMPLE.md)).

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

4. **CI-gated library quality.** Seven invariants
   ([`check-invariants.sh`](../scripts/check-invariants.sh)) block a bad change at
   the door: every file ≤ 500 lines (so the *right* rules load, not a wall of
   text), every rules file ends with an audit checklist, skill descriptions stay
   within the Agent-Skills spec cap, versions stay in lockstep, the router lists
   every skill, and no internal names leak. Plus gitleaks over the full history.

## Reproduce it

```sh
python3 evals/run-completeness.py     # completeness (build-tasks, blind judge)
python3 evals/run-clean.py --cases evals/cases/freshness.jsonl   # freshness
python3 evals/run-clean.py --cases evals/cases/router.jsonl      # routing
```

Set `OPENROUTER_API_KEY` (env or `.env`, never committed). See
[`evals/README.md`](../evals/README.md) for the full harness and
[`BASELINE.md`](../evals/results/2026-07-10/BASELINE.md) for the honest writeup.
