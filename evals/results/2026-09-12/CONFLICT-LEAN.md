# ROADMAP 47 — the conflict rate at LEAN loading

**2026-09-12** · `evals/run-conflict-rate.py --lean --samples 3 --temp 0.0` ·
judge `anthropic/claude-sonnet-5` · 17 pairs from 8 multi-skill gold cases ·
**pre-registered** in [PRE-REGISTRATION-CONFLICT-LEAN.md](PRE-REGISTRATION-CONFLICT-LEAN.md),
committed before any call · artifact `conflict-rate-lean.json`, log `conflict-lean.log`

## Result

| arm | corpus | judge-reported | **hand-verified** |
|---|---|---|---|
| full — **same tree, same day** | 1,546,535 chars | **0.471** (8/17) | not computed (see below) |
| **lean — same tree, same day** | **147,116 (9.5%)** | **0.176** (3/17) | **0.000** |
| *full, 2026-09-09, pre-fix (historical)* | *1,496,659* | *0.353* | *0.176* |

**The attributable result is the first two rows: loading lean cuts the judge-reported
conflict rate by 63% (0.471 → 0.176), and not one of the three lean-reported pairs survives
hand-verification.** Both arms ran on the same tree on the same day, which is exactly what
the registration required and why the comparison holds.

The pre-registered prediction — *"the lean floor is near zero"* — is **confirmed on the
verified number**. Registered threshold for being wrong was ≥ 0.10.

## The ablation was asserted, not assumed

An identical *judge-reported* rate at a tenth of the corpus would have been implausible, so
the first thing checked was whether `--lean` had taken effect at all. It had: the run's own
header reads `corpus: 13 skills, 147,116 chars` against the full arm's **1,496,659** —
**9.8%**. Worth recording how nearly this went wrong: the runner's caveat line is hardcoded
to say *"the judge saw every rules file of both skills"* and printed that in the lean run
too, and the artifact's `_meta` records **neither the corpus size nor which arm ran**. Both
are instrument defects (`rules/15` §2.1): a run that cannot attribute its own number is one
transcription away from being filed under the wrong arm.

## Why all six refute — and they fall into exactly the classes the registration predicted

| # | pair | reported | verdict |
|---|---|---|---|
| 1 | kubernetes × network-security | Medium vs High for a missing default-deny NetworkPolicy | **REFUTED** — the kubernetes row carries its own scope marker *"(requirement-level; depth → network-security)"*, and network-security's High row is a different predicate (a default-deny that exists and is **inert**, not one absent). Same finding ROADMAP 39 refuted |
| 2 | kubernetes × sandboxing | finding **format**: pipe-delimited vs labelled block | **REFUTED** — the router resolves format explicitly and supersedes per-skill variants |
| 3 | kubernetes × sandboxing | Medium vs High, flat network (×2, one a restatement) | **REFUTED** — severity precedence, `sota/rules/03` §1 hard rule 5 |
| 4 | kubernetes × sandboxing | RBAC: kubernetes *"at minimum High"* vs sandboxing's Medium row listing *"broad RBAC"* | **REFUTED, and this one needed the new rule.** RBAC on a cluster is kubernetes' domain; sandboxing's Medium row is an unscoped defence-in-depth list and **does not say it is narrower**, so by the precedence rule shipped in v1.40.2 it does not outrank the model |
| 5 | code-security × shell-scripting | shell's `check-before-create` vs code-security's *"weak existence checks"* | **REFUTED — a conflation, and the most interesting miss.** Same mechanism (`[ -e ]`), different jobs: shell's is **idempotency** (do not clobber on re-run), code-security's is **verification** (existence is not proof of content). Neither forbids the other |
| 6 | code-security × shell-scripting | finding **format**: CWE template vs Evidence/Effort template | **REFUTED** — format again |

**Five of six are the two classes the judge cannot resolve because it cannot see the
router** — finding format and severity precedence. The registration said so in advance and
called them a constant across arms. They are, which is why the *difference* between arms is
still meaningful even though each level is inflated.

**Number 4 is the one worth noticing:** it is the first measured case where the severity
precedence rule added in **v1.40.2 — itself adopted from the ROADMAP 39 measurement** —
decides an otherwise-live conflict. The library's own conflict measurement produced a rule
that the next conflict measurement needed.

## What this does not establish

1. **It is a floor, not the lived rate.** A real lean session opens *some* rules files; this
   opened none. The lived rate sits between 0.000 and the ceiling.
2. **The full arm is NOT a clean before/after against 2026-09-09**, and must not be read as
   one. Its judge-reported rate went **up**, 0.353 → 0.471, despite three conflicts having
   been repaired — because the corpus also **grew**, 1,496,659 → 1,546,535 characters, and
   part of that growth is rules added to these very skills *the same day* (`rules/15` §3a,
   `rules/06` §2a/§2b, `rules/09` §4). More surface gives a judge more apparent
   contradictions to report. Repairs (−), new content (+) and judge noise are confounded in
   that pair of numbers, and no attribution is offered. **The same-tree lean-vs-full
   comparison is unaffected by all three**, which is the whole reason the registration
   demanded it.
3. **The full arm's verified rate was not computed.** Eight flagged pairs would each need
   their quotes read against both files; that is real work and is not done, so it is left
   blank rather than estimated. For scale only, and explicitly **not a measurement**: at the
   2026-09-09 ceiling the verified rate was half the judge-reported one.
3. **17 pairs, one model, one day**, and the judge is blind to the router by design.
