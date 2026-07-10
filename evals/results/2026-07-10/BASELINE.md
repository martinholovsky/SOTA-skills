# Eval baseline — routing lift, with control-validity analysis

Two runs of the with-vs-without efficacy eval, and an honest investigation of
whether the "without-library" arm is a valid control (it is only partially —
read §Control validity). Golden sets: 20 routing cases (`cases/router.jsonl`)
+ 13 audit cases (`cases/audit.jsonl`). Scored with `evals/score.py`.

- **Run 1** (2026-07-10): raw predictions in this directory (`pred_*.json`).
- **Run 2** (2026-07-11): logged re-run — per-case rationales + a context
  self-report per arm + a hardened control. Raw in
  [`../2026-07-11/logged-run.json`](../2026-07-11/logged-run.json).

## Method

Four arms, run as parallel subagents on the same underlying model, identical
answer-stripped inputs per pair:

- **with-library** — reads the actual repo skill files (`skills/sota/SKILL.md`
  for routing; `skills/sota-code-security/rules/*` + language skill for audit)
  and applies them.
- **without-library (control)** — forbidden from reading `skills/`; uses only
  the skill *names* + base judgment. In run 2 it was **hardened**: explicitly
  told to disregard the ambient "consult the sota router" directive, and it
  self-reported doing so.

The delta is the library's marginal contribution **on top of the same base
model** — not a claim about the model.

## Control validity (read this before citing the number)

The eval runs *inside* a configured Claude Code session, so the
"without-library" arm is **not** a clean "no library at all" baseline. Verified
by a direct introspection probe (2026-07-11):

- **Present in every subagent's context:** the global `~/.claude/CLAUDE.md`
  directive *"consult the sota router skill first, load the matching sota-*
  skills"*, and the injected available-skills registry (all 40 sota-* skill
  **names**, with descriptions). This is ambient routing awareness the control
  can't fully shed.
- **NOT present (a suspected leak, refuted):** the stack profile's task→skill
  **mapping tables** (`Projects → Always also load`, `Stack mapping`). The
  probe found these **ABSENT** from subagent context — the profile is not
  loaded into subagents, only referenced conditionally.

**Why the measurement still holds.** The router's *value* isn't the directive
or the skill names — it's the **cross-cutting routing rules** (e.g. "tests
accompany everything", "AI/LLM security → code-security + sandboxing", "K8s
audit trio", "IaC → devsecops"). Those live **only** in `skills/sota/SKILL.md`,
which the without-arm never reads. Run 2's logs make this concrete: both
without-arms' `context_report` confirm they had the directive + names and
**disregarded** them, and their per-case `why` fields show naive
keyword-matching that misses exactly the rule-driven cases:

| Case | without-arm reasoning (verbatim) | missed | router rule it lacked |
|---|---|---|---|
| r01 | "REST = API design; uploads = code security" | `sota-testing` | tests accompany everything |
| r02 | "K8s = kubernetes; Dockerfiles = devsecops" | `sota-sandboxing` | K8s audit trio |
| r03 | "multi-tenant = architecture; billing = databases" | `sota-api-design` | — |
| r07 | "RAG with tools = LLM engineering" | `sota-code-security` | LLM security → code-security |
| r20 | "IAM guardrails = identity-access" | `sota-devsecops` | Terraform IaC → devsecops |

So this measures **"value of reading the router's cross-cutting rules, over
ambient skill-awareness"** — a real and arguably more interesting question than
"library vs nothing", and the lift is attributable to the rules. It is a
**lower bound** on the full library-vs-nothing gap (a truly clean control would
strip the directive + registry and score lower still).

## Results

| Arm | Run 1 recall | Run 2 recall | precision (run 2) |
|---|---|---|---|
| routing — with library | 1.00 | **1.00** | 0.59 |
| routing — without (control) | 0.92 | **0.89** | 0.93 |
| audit — with library | 1.00 | 1.00 | 1.00 |
| audit — without (control) | 1.00 | 1.00 | 1.00 |

**Routing recall lift: +0.08 (run 1), +0.11 (run 2)** — replicated, ~+0.10
average. Driven entirely by the cross-cutting rules (table above).

**Precision tradeoff (real, worth noting):** the with-library arm optimizes
recall hard and loads the *full* fan-out — precision 0.59–0.84 vs the control's
0.93. Loading an extra *relevant* skill isn't a bug, but it costs context
budget; the router errs toward over-loading. Recall is the load-bearing metric
for "did the security-relevant skill get applied", but the precision cost is a
genuine tradeoff, not noise.

## Honest limitations

- **Audit eval is saturated** — both arms 13/13 across both runs, including the
  "harder" cases (IDOR, mass-assignment, ReDoS, XXE, prototype-pollution). On
  unambiguous single-vuln snippets the base model already catches everything.
  **Top next action:** multi-vuln snippets and subtler authz/business-logic
  cases where a systematic skill-guided audit beats recognition.
- **Not a truly library-free control** — the directive + skill registry are
  ambient and can't be stripped from within a configured session. A clean
  library-vs-nothing run needs an **isolated environment** (fresh API call, no
  sota `CLAUDE.md`, no registered skills). The number here is a lower bound.
- **One sample per arm per run** — two runs agree in direction (~+0.10) but
  this is a directional signal, not a stable metric. Average more samples.
- **`expect` sets are minimal must-load judgment calls** — precision numbers
  are informational.

## Takeaway

A **replicated, mechanism-confirmed routing recall lift (~+0.10)** attributable
to the router's cross-cutting rules — even against a control that already knows
the skills exist and was told to route. The audit dimension can't measure
anything until it gets harder cases. The number is a lower bound vs a
routing-aware control; a truly clean library-vs-nothing measurement needs an
isolated run outside this session's config. First real efficacy data point —
value is the delta as golden sets grow and runs are averaged.
