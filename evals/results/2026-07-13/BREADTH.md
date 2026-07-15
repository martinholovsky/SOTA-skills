# Does the competitor lead generalize? — five domains (run 2026-07-15/16)

The [competitor benchmark](COMPETITOR-BENCHMARK.md) measured Python/FastAPI backend
and found SOTA-skills ahead. Two questions remained: is that **Python-specific**, and
does it hold **outside backend**? We ran the same harness (content-only, blind
opus-4.8 judge, each competitor given its best per-domain content) across **five
domains** — and the answer reframes the whole result.

## The five-domain picture

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="../../../assets/breadth-dark.svg">
    <img alt="Completeness % by domain (unguided / best competitor / SOTA-skills), ordered by unguided baseline: hard frontend 53/83/93, Python backend 58/87/99, Go backend 67/87/97, simple frontend 77/97/97, IaC 87/100/100. SOTA-skills leads where the unguided baseline is low and ties where it is high." src="../../../assets/breadth-light.svg" width="100%">
  </picture>
</p>

Completeness = % of a fixed objective rubric the generated code implements
(blind-judged). "Lead" = SOTA-skills minus the best competitor.

| Domain (tasks) | Unguided | **SOTA-skills** | affaan-m/ECC | alirezarezvani/claude-skills | PatrickJS/awesome-cursorrules | SOTA lead |
|---|---|---|---|---|---|---|
| Python backend (7) | 58% | **99%** | 87% | 81% | 83% | **+12** |
| Go backend (3) | 67% | **97%** | 83% | 80% | 87% | **+10** |
| Frontend — hard SSR/auth (3) | 53% | **93%** | 83% | 70% | 60% | **+10** |
| Frontend — simple forms (3) | 77% | 97% | 97% | 97% | 90% | **+0** |
| IaC — K8s/Docker/Terraform (3) | 87% | 100% | 97% | 97% | 100% | **+0** |

## The finding: the lead tracks the *unguided baseline*, not the domain

Sort the rows by how well an **unguided** model already does, and the pattern is
unmistakable:

| Unguided baseline | SOTA-skills lead vs best competitor |
|---|---|
| 0.53 (hard frontend) | **+0.10** |
| 0.58 (Python backend) | **+0.12** |
| 0.67 (Go backend) | **+0.10** |
| 0.77 (simple frontend) | +0.00 |
| 0.87 (IaC) | +0.00 |

There is a clean threshold around **0.7**: **below it, SOTA-skills leads every
competitor by ~10 points; above it, everyone converges near the top and SOTA-skills
ties.** The domain label (backend vs frontend vs infra) does **not** predict the
lead — the baseline does.

## What each domain settled

- **Go backend (control) — the win is not Python-specific.** Same concern set as the
  Python tasks, different language: SOTA-skills 97% vs 80–87% (unguided 67%). Backend
  security/ops guidance generalizes across languages.
- **Hard frontend (SSR/auth) — the earlier "frontend tie" was rubric difficulty, not
  a domain truth.** The [first frontend run](COMPETITOR-BENCHMARK.md) used *simple*
  forms/tables (baseline 77%) and everyone tied. Re-run with the *invisible*
  concerns — server-side authz, secret leakage across the client boundary, injection,
  hydration, CSP — the baseline drops to 53% and SOTA-skills leads clearly (93% vs
  60–83%). claude-skills (no frontend content) scored lowest of the three.
- **IaC (K8s/Docker/Terraform) — a tie, but instructively.** Infra *is* dense with
  security concerns, yet the unguided model already wrote a fully hardened Kubernetes
  Deployment (100%) and near-complete Dockerfile/Terraform (baseline 87%). These
  concerns are **template-shaped** (add a `securityContext` block, a public-access
  block) and heavily represented in training, so the base model includes them — and
  guidance can't add what's already there.

## Why the baseline predicts the lift

SOTA-skills' value is **forcing in the concerns the base model would silently omit.**
That headroom is large only when the base model's *default* output is incomplete —
which happens when the missing pieces require **non-trivial added code/logic** (rate
limiting middleware, a server-side auth check, secret-boundary handling) rather than a
**well-known template field** the model already emits (a K8s `securityContext`, a
React controlled input). Backend production hardening and security-sensitive frontend
are full of the former; simple UI and templated IaC are mostly the latter.

## The honest, reframed claim

Not "SOTA-skills wins on backend." Rather:

> **SOTA-skills leads the most popular libraries on tasks where a base model ships
> incomplete code — production backend (any language) and complex/security-sensitive
> frontend — by ~10 points. On tasks a base model already handles well (simple UI,
> templated infra), it ties the field.**

That is more useful than a domain label: it tells you *when the library earns its
keep* — the harder and less templated the task, the more it adds; where the model is
already complete, you don't need a library and everyone converges.

## Limits (stated, not buried)

- **3 tasks/domain (7 for Python), single-sample, one build model, content-only.** The
  cross-domain **baseline correlation** is the signal, not any single cell. Raw data:
  `competitor-breadth-{go,iac,frontend,frontend-complex}.json` + `competitor-benchmark.json`.
- Rubrics are objective but author-chosen; the manifests
  (`evals/cases/competitors-*.json`) make content selection inspectable and re-runnable.
- Competitor coverage varies by domain and is noted honestly (claude-skills has no
  Go/frontend-specific content; cursorrules is thin on IaC) — a real property of each
  library, not a handicap.
