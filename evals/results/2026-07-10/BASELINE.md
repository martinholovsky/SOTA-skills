# Eval baseline — 2026-07-10

First efficacy measurement (roadmap Next item). Golden sets: 20 routing cases
(`cases/router.jsonl`) + 13 audit cases (`cases/audit.jsonl`). Scored with
`evals/score.py`. Raw predictions for each arm are in this directory
(`pred_*.json`) so the run is re-scorable.

## Method

Four arms, run as parallel subagents on the same underlying model:

- **routing / with-library** — read `skills/sota/SKILL.md` (the router: routing
  table + cross-cutting rules) and apply it.
- **routing / without-library** — forbidden from reading `skills/`; given only
  the 40 skill *names* + own judgment.
- **audit / with-library** — read `skills/sota-code-security/rules/*` (+ the
  matching language skill) and apply the checks.
- **audit / without-library** — forbidden from reading `skills/`; own knowledge.

Both arms of a pair got identical inputs (prompts / snippets), with the
`expect` answers stripped. The delta between arms is the library's **marginal
contribution on top of the same base model** — not a claim about the model.

## Results

| Arm | Cases | Mean recall | Mean precision |
|---|---|---|---|
| routing — with library | 20 | **1.00** | 0.84 |
| routing — without library | 20 | **0.92** | 0.93 |
| audit — with library | 13 | 1.00 | 1.00 |
| audit — without library | 13 | 1.00 | 1.00 |

**Routing recall lift: +0.08 (0.92 → 1.00).** The without-library arm missed a
must-load skill on 4 of 20 cases; with the router it missed none:

- **r01** (file-upload API) — without missed `sota-testing` (router rule 7,
  "tests accompany everything").
- **r02** (review Dockerfiles/K8s) — without missed `sota-sandboxing`
  (pod/container isolation).
- **r03** (multi-tenant billing) — without missed `sota-api-design`.
- **r07** (LLM agent runs tools on user input) — without routed only to
  `sota-llm-engineering` and missed `sota-code-security` (router rule 5 puts
  prompt-injection/tool-call security there).

These are exactly the **cross-cutting routing rules** the router encodes and a
bare model doesn't reliably apply — the library's clearest measured value.

The recall gain comes with a **precision cost** (0.93 → 0.84): the with-library
arm loads more skills, some beyond the minimal must-load set (e.g. r02 also
loaded network-security + devsecops + shell-scripting — plausibly relevant, but
not in the golden set). For routing this is expected and mostly benign (loading
an extra relevant skill isn't a bug); recall is the load-bearing metric.

## Honest limitations

- **Audit eval is saturated** — both arms scored 13/13, including the cases I
  designed to be *harder* (IDOR, mass-assignment, ReDoS, XXE,
  prototype-pollution). On unambiguous single-vuln snippets the base model
  already catches everything, so the eval can't discriminate here. **Next
  iteration:** multi-vuln snippets, subtler business-logic/authz cases, and
  cases keyed to library-specific knowledge (specific CVEs, the
  "hidden-field-is-adversarial" doctrine, timing/side-channel nuance).
- **Single run, non-deterministic** — one sample per arm; treat as a
  directional signal, not a stable metric. Re-run and average for a real trend.
- **`expect` sets are judgment calls** — the routing must-load sets are minimal
  by design; precision numbers are informational, not a grade.
- **Same-model control** — "without-library" is the base model instructed not
  to read `skills/`; it measures marginal library value, and relies on the arm
  honoring the instruction.

## Takeaway

The library delivers a **measurable, mechanism-explained routing lift** (+0.08
recall, driven by the cross-cutting rules). The audit dimension needs harder
cases before it can measure anything — that is itself the top action for the
next eval iteration. This is the first data point; the value is the delta over
time as the golden sets grow and the runs are averaged.
