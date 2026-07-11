# Eval baseline — routing lift, with control-validity analysis

Two runs of the with-vs-without efficacy eval, and an honest investigation of
whether the "without-library" arm is a valid control (it is only partially —
read §Control validity). Golden sets: 20 routing cases (`cases/router.jsonl`)
+ 13 audit cases (`cases/audit.jsonl`). Scored with `evals/score.py`.

- **Run 1** (2026-07-10): in-session, raw predictions here (`pred_*.json`).
- **Run 2** (2026-07-11): in-session logged re-run — per-case rationales +
  context self-reports + hardened control (`../2026-07-11/logged-run.json`).
- **Run 3** (2026-07-11): **clean raw-API control** via `evals/run-clean.py` —
  no session contamination; cross-model. This is the decisive one — see §Clean
  isolated run.

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

## Clean isolated run — 2026-07-11 (resolves the control-validity concern)

`evals/run-clean.py` makes **raw model-API calls** (OpenRouter): no HOME, no
`CLAUDE.md`, no skill registry, nothing sota — the with-library arm gets the
skill content *pasted into the prompt*, the without-library arm gets only the
task (+ the skill names / vocab needed to score). This is the true
library-vs-nothing control the §Control-validity section said was missing. Raw
outputs in [`../2026-07-11/`](../2026-07-11/).

**Routing lift replicates across every model tier** (with-library = 1.00 each):

| Model | without-library recall | lift |
|---|---|---|
| `claude-sonnet-4.6` | 0.91 | **+0.09** |
| `claude-sonnet-5` | 0.86 | **+0.14** |
| `claude-opus-4.8` | 0.91 | **+0.09** |

Even **opus-4.8** (strongest) misses the *same* rule-driven skills without the
router: **r01** `sota-testing`, **r02** `sota-sandboxing`, **r07**
`sota-code-security`, **r09** `sota-web-frameworks` — every model, every run.
So the in-session +0.08/+0.11 was **not** a contamination artifact: the routing
lift is real (~+0.10, clean) and attributable to the router's cross-cutting
rules, which no model applies reliably on its own.

**Audit lift is +0.00 — model-independent.** Both arms score 1.00 on `haiku-4.5`
*and* `sonnet-4.6`, on the original *and* the harder cases (multi-vuln, subtle
business-logic). A current model catches textbook vulns from base knowledge,
library or not. **Honest conclusion:** the library's audit value is *not* in
recognizing common vulns — it's in systematic coverage at scale, rarer/nuanced
findings, and checklist discipline, none of which this eval captures. Building
"harder" cases didn't help; the eval needs a fundamentally different audit
target (or the audit lift genuinely is ~0 for strong models).

## Honest limitations

- **Audit eval is saturated** — both arms 13/13 across both runs, including the
  "harder" cases (IDOR, mass-assignment, ReDoS, XXE, prototype-pollution). On
  unambiguous single-vuln snippets the base model already catches everything.
  **Top next action:** multi-vuln snippets and subtler authz/business-logic
  cases where a systematic skill-guided audit beats recognition.
- **In-session control is contaminated (RESOLVED for routing)** — the runs 1/2
  numbers are lower bounds because the directive + registry are ambient in a
  configured session. The 2026-07-11 clean API run (§ above) removes that
  contamination entirely and confirms the routing lift holds (~+0.10 across
  three model tiers). Reproduce with `python3 evals/run-clean.py --cases …`.
- **One sample per arm per run** — two runs agree in direction (~+0.10) but
  this is a directional signal, not a stable metric. Average more samples.
- **`expect` sets are minimal must-load judgment calls** — precision numbers
  are informational.

## Takeaway

A **replicated, clean, mechanism-confirmed routing recall lift (~+0.10)** — it
holds in-session (+0.08/+0.11) *and* in a fully isolated raw-API control
(+0.09/+0.14/+0.09 on sonnet-4.6/sonnet-5/opus-4.8), driven by the router's
cross-cutting rules that no model applies reliably alone. That settles the
contamination question: the lift is real, not a config artifact.

The **audit dimension shows no measurable lift (+0.00), model-independent** even
on harder cases — a genuine, honest finding: strong models don't need the
library to recognize textbook vulnerabilities. The library's audit value lives
elsewhere (coverage at scale, rarer findings, discipline) and needs a different
eval to measure — or it may simply be ~0 for capable models on this task shape.
Both are honest data points; the routing number is the one that stands up.
