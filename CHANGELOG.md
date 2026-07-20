# Changelog

All notable changes to SOTA-skills are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/2.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- **Silent-control eval grown 15 → 49 cases, and its headline lift RETRACTED.**
  The 15-case set saturated the with-library arm (0.99–1.00), leaving no headroom
  to measure. The set now carries **41 positives + 8 negative controls** (loud
  failures, incl. a display-only truncation and a *documented deliberate*
  fail-open, both of which must NOT be flagged) and **6 positives tagged `novel`**
  — mechanisms rules/10 does not enumerate (case-sensitive blocklist regex vs
  lowercased input, unawaited async authz check, decorator/route ordering bypass,
  inverted config-merge precedence, a context timeout never attached to its
  request, a retry loop that swallows its final failure) — which separates
  "teaches the lens" from "recites its own list". Harder positives were added
  across Go/TS/SQL/YAML/Helm/Markdown.
  **Result: the +0.07 lift measured at n=15 does not replicate.** At n=49 it is
  **+0.03** (vocabulary design) and **−0.01** (open-ended design), both inside a
  per-arm spread of ±0.04; rules/10's own ablated contribution is **+0.00** (the
  vocabulary design's with- and ablated arms are *identical* — 0.918, zero spread,
  same four missed cases). `RESULTS.md` corrected from +0.07 to +0.00 with the
  retraction stated in place. One signal logged as a **hypothesis, not a finding**:
  on the 6 unenumerated mechanisms the *unguided* arm scored 1.00 and both library
  arms 0.83 — possible **taxonomy anchoring**, one case at n=6, needs a larger
  novel subgroup. Four cases defeat every arm (build-tag no-op, `*.yaml` glob vs
  `.yml`, env-filter mismatch, unawaited `expect().rejects`); adding them to the
  rule text was deliberately **not** done, as that would fit the guidance to the
  test set.
- **Both eval runners now whitelist prompt fields** (`id`/`language`/`snippet`)
  instead of blacklisting known answer keys — a new case field such as `novel` or
  `reference` can no longer leak the answer into the prompt just because nobody
  updated a strip list. `run-silent-open.py` additionally reports **novel** and
  **negative-control** subgroup recall per arm.

### Added

- **Audit-precision eval + the regression check for this PR** —
  `evals/cases/finding-adjudication.jsonl` (30 code+claim pairs, 15 genuine / 15
  plausible-but-wrong across six distinct refutation classes) and
  `evals/run-adjudication.py`, scoring **specificity** (refute the false claims) and
  **sensitivity** (keep the real ones) with an ablation arm that strips §6. Every
  other audit set here measures *recall*; this measures the false-positive side that
  refutation actually targets. **Result: +0.00 — all three arms 1.00**, zero wrong
  answers in 90 adjudications per arm. Run twice: the first framing enumerated the
  ways a claim can fail (i.e. handed §6's content to every arm) and was replaced with
  a neutral one — identical 1.00s, so the saturation is not a framing artifact.
  Routing was re-run as the regression check for today's three router edits and
  **held at 1.00** (lift +0.10, both matching the recorded multi-sample numbers).
  Completeness was deliberately **not** re-run and the reason is documented: all 17
  skill files it loads are unchanged since v1.16.0, its `principle5()` extract is
  byte-identical (sha `2a36f20d8e51`), and its `BUILD_WORKFLOW` is a hardcoded mirror
  — so it is structurally blind to today's changes and a green run would have been a
  vacuous test. That mirror's drift from the router is logged, not silently synced.
  **Four audit instruments now saturate** (recall, cross-file, silent-control,
  precision); the writeup states plainly that no current instrument can score an
  audit-*process* change, and recommends stopping additions to the audit path until
  an agentic one exists:
  [`evals/results/2026-07-20/AUDIT-PROCESS.md`](evals/results/2026-07-20/AUDIT-PROCESS.md).
- **Adversarial verification in AUDIT mode** — `sota/rules/01-audit-methodology.md`
  gains **§6 "Try to kill your own findings"**, and the router's AUDIT workflow step 6
  changes from *verify* to **refute**. Re-reading your own finding re-runs the
  reasoning that produced it, so it is the weakest check available; every
  Critical/High now gets an **independent pass prompted to kill it** — a separate
  agent or a fresh-context hostile read, working from the code at the pinned commit
  rather than the write-up, defaulting to REFUTED when evidence is ambiguous.
  Includes the three distinct refuter lenses (is the mechanism real / is it
  reachable / is the impact inflated), majority-refute-kills, **recording
  refutations** so the next auditor doesn't re-raise them, a refuter for absence
  claims, effort scaling by severity, and the two failure modes that make the pass
  theatre (the rubber-stamp refuter told to "verify" rather than refute, and
  refuting the *description* instead of the code). Report §7 and hygiene §8
  renumbered accordingly; one audit-checklist line added.
  Adopted from a field-tested external audit harness — verified first that the
  library had **no** independent-refutation language anywhere (`grep` for
  refut/adversarial/independent-verify across `sota/` and `sota-testing/` returned
  zero hits), so this is a genuine gap, not a restatement. **Unmeasured:** the audit
  dimension already saturates at +0.00, so the existing evals cannot show a lift
  here; no efficacy claim is made.

- **`sota-code-security` rules/10 "Silent control failure"** — a new rule file for
  the class the library had no home for: a control, feature, or safeguard that
  **appears active but does nothing**, where a broken system and a working system
  are indistinguishable from the outside. Organized around the *falsification
  question* ("if this were silently a no-op, would anything observable differ? —
  if no, that IS the finding"), then eleven places no-ops hide: weak existence
  checks (`exists()`/`is_dir()` standing in for a loaded artifact), optional-
  dependency degradation (`except ImportError` → feature vanishes), empty or
  placeholder rulesets loaded as real, swallowed exceptions on the enforcement
  path, overloaded flags, attacker-triggerable early returns, truncation before
  inspection, config keys silently ignored by permissive schemas, doc/code drift
  on defaults, hardcoded numbers in tool output, and **shipped-artifact gaps**
  ("works in a dev checkout, dead in the image"). Plus the mutation probe for
  vacuous tests (with the two traps that make a green run lie), the shared
  deduped-per-cause degraded-control helper, and the evidence rules — including
  that **a negative claim needs more proof than a positive one**.
  A prior gap analysis confirmed 9 of these 12 concepts had no coverage anywhere
  in the tree; fail-open (rules/03) and test vacuity (`sota-testing` rules/02/06/
  09) were already covered and are cross-referenced rather than duplicated.
- **The lens is now part of the default BUILD and AUDIT paths**, not an opt-in
  file: the router's BUILD self-audit gate (step 4) asks the falsification
  question of every control in the diff; AUDIT mode gains a **step 4
  "silent-control pass"** run over the controls the domain passes confirmed
  exist (the class is invisible to those passes and to pattern-based SAST,
  because the code isn't wrong — it's inert); `sota-code-security` BUILD mode
  gains step 6 ("every control must be falsifiable") and AUDIT mode step 5
  ("check the inert"); and routing rule 20 ("'it's enabled' is a claim, not a
  fact") points at it from the router.
- **Asymmetric evidence burden for negative claims** — router operating
  principle 3 and `sota/rules/01-audit-methodology.md` §5 now require a widened
  search plus a second independent method before asserting "no instances of X",
  and require positive observations to be evidenced by **effect** (a rejection,
  a log, a test that fails when the control is disabled) rather than presence.
  Two audit-checklist lines added.
- **Eval case set for the silent-control class** — `evals/cases/silent-failure.jsonl`
  (15 cases: 13 positives, one per hiding place, across Python/Go/JS/YAML/Dockerfile,
  plus **2 negative controls** whose correct answer is "not silent" so an
  over-flagging arm cannot score 1.00), a `silent` kind in `run-clean.py`, a new
  **`--ablate`** flag that drops rules/10 from the with-library arm to isolate a
  single file's contribution, and `evals/run-silent-open.py` — an open-ended,
  no-vocabulary variant graded by a **different** model blind to the arm.
  **Result, reported as measured:** at the initial 15 cases the library appeared to
  lead **0.92 → 0.99 (+0.07)**, and that number briefly shipped in `RESULTS.md`.
  **It did not replicate and is retracted** — see the grow-the-set entry below.
  The design's own limit is documented: both arms must be *told* to hunt inert
  controls, and that framing is the falsification question itself, so what the rule
  actually adds — asking unprompted — is what this design cannot measure. Writeup,
  raw artifacts, and limitations:
  [`evals/results/2026-07-20/SILENT-FAILURE.md`](evals/results/2026-07-20/SILENT-FAILURE.md);
  scoreboard row added to `evals/results/RESULTS.md`.
- Cross-references so each home keeps its own doctrine: `sota-testing` rules/06
  (hand-mutating a control's body as a no-tooling audit probe, plus the
  missing-dependency and mutation-didn't-take traps), `sota-observability`
  rules/05 (one shared degraded helper, deduped per cause not per request),
  `sota-devsecops` rules/04 (the built image must contain what the code needs at
  runtime; smoke-test controls against the artifact, not the checkout).

- **`sota-docs-workflow` rules/01 §8 "The documentation baseline"** — the must-have
  doc set every repo should carry, closing a real gap (the individual docs were
  covered but scattered, and the community-health files SECURITY/CODE_OF_CONDUCT/
  SUPPORT/GOVERNANCE were absent entirely). Enumerates *always* (README + LICENSE +
  CHANGELOG) vs *trigger-based* (CONTRIBUTING/CODE_OF_CONDUCT/SECURITY once public,
  runbooks once on-call, AGENTS.md for AI-assisted repos, ADR log, CODEOWNERS), with
  GitHub's community-health-file search precedence (`.github/` → root → `docs/`,
  verified against GitHub docs) and the single-canonical-home rule so the baseline
  itself doesn't become sprawl. Two audit-checklist lines added; SKILL index + BUILD
  step updated.

### Changed

- **`evals/results/RESULTS.md` now embeds the five-domain breadth chart** and
  carries the full breadth story inline (chart + table + 0.7-baseline threshold +
  the "why the baseline predicts the lift" mechanism), so the scoreboard is
  self-contained instead of splitting the visual off into `BREADTH.md`. `BREADTH.md`
  stays as the per-domain-notes and raw-data appendix.

## [1.16.0] - 2026-07-16

The competitor + breadth release: a fair, blind, reproducible head-to-head against
the most popular guidance libraries; a five-domain breadth study showing the lead
tracks the *unguided baseline*, not the domain; three conventions distilled from an
external review (each independently measured); plus a discoverability and
eval-harness overhaul. No skill added (41 unchanged) — content, evals, and docs.

### Added

- **Three conventions adopted from an external agent-orchestration review**
  (pure-Markdown, generic; runtime-bound ideas like memory-bank persistence,
  RAG, and worktree locks were deliberately skipped):
  1. **Negative routing cross-references** — 9 confusable skill descriptions now
     name the sibling to use instead ("Not for X — use sota-Y": api-design,
     observability, async-concurrency, performance, threat-modeling, devsecops,
     cli-ux, databases, docs-workflow), sharpening disambiguation inline. No
     harness reads skill descriptions, so this is off every measured eval path.
  2. **Plan-concreteness** — router BUILD step 3 now requires each planned
     checklist item be a concrete, checkable done/not-done outcome (vague items
     rejected); mirrored into `run-completeness.py`'s `BUILD_WORKFLOW` so the eval
     reflects the real workflow.
  3. **Evidence-based completion** — new router operating principle 6: never claim
     "done"/"working" from plausibility; state the check run and its result.
  Regression-tested (our [context-rot finding](docs/WHY-COMPLETENESS-RESIDUAL.md)
  warns added text can lower salience): the 3× completeness eval held at **0.991
  with-arm / +0.385 lift** (vs 0.996 / +0.395 — Δ −0.005, within sampling noise;
  no cross-cutting concern systematically dropped), and the 3× routing eval (which
  pastes the whole router, so it sees principle 6) **held at 1.00** with-arm, no
  misses. Raw: `evals/results/2026-07-13/completeness-3sample-postadopt.json` +
  `routing-3sample-postadopt.json`; summary in `evals/results/RESULTS.md`.

- **Description-based routing eval** (`evals/run-desc-routing.py`,
  `evals/cases/desc-routing.jsonl`, `results/2026-07-13/desc-routing-3sample.json`)
  — the first measurement of the skill **auto-loader** path (pick a skill from the
  description catalogue), distinct from the router table. A/Bs the catalogue with vs
  without the negative cross-references added above, on 10 adversarially-confusable
  tasks. **Honest +0.00:** the model never routed to the warned-against sibling in
  *either* arm (distractor-pick 0.00 across all cases/samples), so the cross-ref had
  nothing to fix — the description-selection path is already saturated for a frontier
  model, like audit. The cross-refs are kept as zero-cost defensive clarity; no
  routing lift is claimed. Summary in `evals/results/RESULTS.md` §5.

### Fixed

- **Accuracy sweep (4-way doc audit against the result JSONs).** Corrected claims stated more strongly than the data: the **web-search recovers/can't-recover** claims (freshness + completeness) were never measured — now marked as predictions; the live-agent 0.99 was called *identical* to the 0.99 simulation (actually 0.987 vs 0.988) — softened to *matching*; `claude-skills` 3-tightest confidence 83% → **82%** (recomputed 0.8249); DECAY guidance/filler sizes were tokens mislabeled as KB (18.7 KB → **~18.6K tokens / ~72 KB**); freshness **+0.65** was mis-attributed to the 32-case set (it's a 20-case run; 32-case is +0.53); `completeness-blind-spot` upload 0.55 → **0.58** (multi-sample mean); ROADMAP item 6 and the AGENTS.md WHY-IT-WORKS pointer were stale (competitor benchmark is done, WHY now carries a scoped vs-libraries section); star counts dated. Cited literature was spot-verified accurate (Chroma 2025 '18 models') and left as-is.

### Added

- **Competitor breadth experiment (five domains) — concludes the comparison.**
  `evals/results/2026-07-13/BREADTH.md` plus the case/manifest/result files for
  Go backend, complex frontend (SSR/auth), simple frontend, and IaC
  (`evals/cases/completeness-{go,iac,frontend,frontend-complex}.jsonl`,
  `evals/cases/competitors-{go,iac,frontend}.json`,
  `results/2026-07-13/competitor-breadth-{go,iac,frontend,frontend-complex}.json`);
  `run-competitors.py` gained `--cases`/`--manifest`/`--ids`/`--samples`/`--temp`
  and incremental `--out` saving. **Finding: the lead tracks the *unguided
  baseline*, not the domain.** Below a ~0.7 baseline (Python backend 58%→lead +12,
  Go 67%→+10, hard SSR/auth frontend 53%→+10) SOTA-skills leads every competitor by
  ~10 pts; above it (simple React forms 77%→+0, templated IaC 87%→+0) everyone
  converges. This **supersedes** the earlier "backend-specific" reading — the first
  frontend run used *easy* forms; a re-run with the invisible concerns (server-side
  authz, secret-boundary leakage, injection, hydration, CSP) shows SOTA-skills leads
  hard frontend too. All docs (README, WHY-IT-WORKS, RESULTS, COMPETITOR-BENCHMARK,
  ROADMAP) reframed from "backend-specific" to baseline-driven.
- **Five-domain breadth chart** (`assets/breadth-{light,dark}.svg` + matching
  1520px `.png`, regenerable via `assets/gen-breadth-chart.py`) — a theme-aware
  grouped bar of unguided / best-competitor / SOTA-skills completeness across the
  five domains, ordered by baseline so the lead-where-incomplete pattern is visible;
  embedded in `BREADTH.md`. Palette validated with the dataviz skill's checker.
- **Competitor-benchmark bar chart** (`assets/benchmark-{light,dark}.svg` +
  matching 1440px `.png`, regenerable via `assets/gen-benchmark-chart.py`) — a
  theme-aware visual of best-practice completeness per library (SOTA-skills 99%
  highlighted vs the field), embedded in the README, `evals/results/RESULTS.md`,
  and `docs/WHY-IT-WORKS.md` via `<picture>` (light/dark SVG). The PNGs are for
  LinkedIn/slides/anywhere SVG isn't supported. Palette validated with the dataviz
  skill's checker; alt text carries the numbers.
- **Discoverability overhaul.** `docs/INDEX.md` (a find-it-fast map: every topic →
  where it's documented, organized by intent), `docs/CONTEXT-MANAGEMENT.md` (the
  single home for how the library keeps the model applying rules as context fills —
  the re-injection hook, principle 5, terminal re-read, deterministic gates, and
  the *why*), and `evals/results/RESULTS.md` (a consolidated scoreboard of every
  measured number). README gained a **table of contents** and deep-doc links; both
  new indexes are linked from AGENTS.md.
- **Skill-application decay eval** (`evals/run-decay.py`,
  `results/2026-07-13/DECAY.md`) — the first measurement of the *temporal*
  (multi-turn) dimension of rule forgetting, not just single-call. Arms: anchor /
  reminder (the `UserPromptSubmit`-hook analog) / control. First run: **no decay at
  moderate scale** (guidance held over 30 unrelated turns); bounds the problem but
  needs a bigger intervening context to find the breaking point (roadmap item 5).

### Changed

- **Every competitor-repo reference now uses its full `owner/repo` name + a
  GitHub link** (no bare "ECC"/"claude-skills"/"awesome-cursorrules", which
  collide with unrelated same-named repos), and `evals/results/RESULTS.md` bundles
  all competitor numbers into **one consolidated per-repo table** (completeness,
  confidence, gap vs SOTA, head-to-head).
- **The 500-line cap now applies to skill Markdown only** (`skills/**/*.md`), where
  it's load-bearing for incremental loading. README, CHANGELOG, and `docs/` are
  uncapped — navigability comes from the TOC + `docs/INDEX.md`, not a line ceiling.
  CHANGELOG archiving is now optional hygiene, not forced. *(PR #100)*

Evaluation-harness additions (no skill-content change; not in CI — see
`evals/README.md`). These execute two roadmap follow-ups from v1.15.0.

### Added

- **Cross-file repo-audit eval** (`evals/run-repo-audit.py`,
  `evals/cases/repo-audit.jsonl`, `evals/cases/repo-audit/orderdesk/`). A 15-file
  FastAPI fixture with **8 defects that are invisible in any single file** (an
  authz check one layer assumes another enforces, a taint crossing modules, an
  invariant one file documents and another violates, an insecure default trusted
  by its caller). Answers roadmap item 3 — the only identified path to a real
  audit lift. Result: **+0.00** on both `claude-sonnet-4.6` and `claude-opus-4.8`
  (strict, file-attributed scoring). When the whole repo fits in one context, a
  capable model reads across files unaided; making defects cross-file changes
  nothing while every file is visible. The library makes **no audit-lift claim**;
  the real frontier is a repo too large to hold at once (agentic selective
  reading), logged as the open follow-up
  (`evals/results/2026-07-13/REPO-AUDIT.md`).
- **Live-agent BUILD validation** (`evals/judge-live-build.py`). Closes the
  completeness eval's one simulation gap (roadmap item 2): `run-completeness.py`
  *pastes* the router's principle 5 + rules to stand in for what an agent loads.
  This scores artifacts from a **real sub-agent** driven over each build task
  through the actual router BUILD workflow, with the same blind opus judge and
  rubrics. Live-agent mean completeness is **0.99 (6/7 perfect)** — identical to
  the 0.99 paste-based simulation and vs 0.60 unguided base, confirming the
  simulation is a faithful proxy. Result: `evals/results/2026-07-13/LIVE-BUILD.md`
  (+ `live-build.json`).
- **Multi-sample eval tightening** (roadmap item 1) —
  `evals/results/2026-07-13/MULTI-SAMPLE.md` + `completeness-3sample.json` +
  `routing-3sample.json`. Re-ran the value dimensions at `--samples 3 --temp
  0.7`: completeness **0.60 → 1.00 (+0.39)** (reproduces the single-sample
  headline; with-arm ±0.01 across-case sd, 6/7 cases perfectly steady), routing
  **0.90 → 1.00 (+0.10)** (with-arm ±0.00), freshness **0.44 → 0.97 (+0.53)**
  (reused 3× run). The with-library arm is near-zero variance everywhere; the
  sampling wobble is all in the unguided arm. Retires the single-sample caveat in
  `docs/WHY-IT-WORKS.md`.
- **Publication draft** — `docs/writeups/completeness-blind-spot.md`, a
  reader-facing write-up of the completeness/salience finding (context rot →
  dropped rate-limiting; adding rules made it worse, a short reminder fixed it),
  with the before/after data and honest boundary. Draft for the maintainer to
  publish (roadmap item 7, distribution).

### Added

- **Competitor benchmark** (`evals/run-competitors.py`,
  `evals/cases/competitors.json`, `results/2026-07-13/COMPETITOR-BENCHMARK.md`) —
  SOTA vs. the most popular competing guidance libraries on the 7 completeness
  tasks, content-only and blind-judged. **SOTA-skills 0.99 vs
  [affaan-m/ECC](https://github.com/affaan-m/ECC) (~230k★) 0.87,
  [PatrickJS/awesome-cursorrules](https://github.com/PatrickJS/awesome-cursorrules) (~40k★) 0.83,
  [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) (~23k★) 0.81**;
  unguided 0.58. SOTA wins or ties every one of the 21 head-to-head cases and
  loses none; competitors are legitimate (all beat unguided by +0.23–0.28) but
  drop the cross-cutting non-negotiables (rate limiting, transport, tests) SOTA
  embeds. Clears the roadmap honesty gate for a scoped, reproducible "vs library
  X" claim; `docs/WHY-IT-WORKS.md` now carries it. A **3-sample/temp-0.7 confidence
  check** on the 3 tightest cases confirms the lead holds — SOTA's worst sample is
  ≥ each competitor's best, and the gaps match the single-sample run. The harness
  gained `--samples/--temp`, `--ids`, and crash-safe incremental `--out` saving.

### Changed

- **README surfaces the measured lift up front** — the dense one-liner is now a
  scannable per-dimension list (completeness +0.39, freshness +0.53, routing
  +0.10, with the multi-sample endpoints and the "near-zero variance" note). The
  clone/script install method now sits in the top quick-install block right after
  the plugin commands; the Installation section keeps the clone-path details
  without repeating the command blocks.

## [1.15.0] - 2026-07-13

The measured-efficacy release: completeness proven as the library's thesis, the
one residual root-caused, and the BUILD workflow rewritten around it.

### Added

- **Completeness eval — the library's thesis, measured** (`evals/cases/completeness.jsonl`,
  `evals/run-completeness.py`). Given a minimal "build X for my app" prompt with
  no security/logging cues, does the model embed best practices from v1? Clean
  raw-API, generate-then-**blind-judge** (opus-4.8 grades sonnet-4.6's artifacts,
  blind to arm), 7 build tasks. Vs. an unguided model the full library lifts
  best-practice coverage **0.60 → 0.99 (+0.39), 6/7 tasks perfect** — embedding
  the tests/rate-limits/logging/transport a base model *systematically* skips.
  Unlike freshness, this is **not** recoverable by "verify via search" (an agent
  won't search "should I add rate limiting"), which makes it the most defensible,
  least-redundant value. Ablation: base 0.60 → +rules ~0.89 → +BUILD self-audit
  0.93 → +router principle 5 0.99.
- **`docs/WHY-IT-WORKS.md`** — the measured case, framed honestly (**vs. an
  unguided model**, explicitly *not* vs. other libraries — we haven't benchmarked
  one) + the four in-repo-verifiable benefits (auto-routing/composition,
  freshness-maintained + primary-source-cited, build+audit, CI-gated quality).
  README hero links it.
- **`docs/WHY-COMPLETENESS-RESIDUAL.md`** — why a with-library build still
  occasionally drops a cross-cutting rule, and the design that counters it.

### Changed

- **Root-caused the completeness residual; it is a salience / context-length
  attention effect, NOT a "coverage gap"** (`docs/WHY-COMPLETENESS-RESIDUAL.md`).
  In all 7 tasks the forgotten rule was in context *and* in a pasted Audit
  checklist, yet dropped. Five controlled experiments (+ a 4-case recovery test)
  disprove the coverage story: **adding the missing rule files made it worse**
  (context 72→100 KB, compliance fell — live context rot), while a **short salient
  reminder recovered it to 1.00**. Matches the literature — context rot
  ([Chroma 2025](https://www.trychroma.com/research/context-rot)), lost-in-the-middle
  ([Liu 2023](https://cs.stanford.edu/~nfliu/papers/lost-in-the-middle.arxiv2023.pdf)),
  instruction-count decay ([arXiv 2507.11538](https://arxiv.org/html/2507.11538v1)).
  It occurs in a single call, so it is not a workflow/subagent artifact — chains
  only amplify it.
- **Router BUILD workflow rewritten around the finding** (`skills/sota/SKILL.md`):
  a **hard self-audit gate** (step 4 — do not present code until every checklist
  item is implemented or explicitly scoped out); a short **operating principle 5**
  (universal non-negotiables — rate-limiting / transport / tests / logging on any
  endpoint, kept short for salience, 947→765 chars); **load lean** (extra
  similar-looking rules *measurably lower* compliance — correctness, not economy);
  **plan with the checks up front**; **self-audit LAST with a terminal re-read**
  (recency); plus recommend a separate fresh-context audit pass + deterministic
  CI gates. The eval's with-arm now pastes principle 5, so its number reflects the
  real library.
- **Eval suite hardened and validated against primary sources.** Completeness
  4 → 7 build tasks (+search, webhook, password-reset). **Freshness 20 → 32
  cases** (+12 across languages/security/cloud/crypto/web specs, each
  grep-confirmed in the library and primary-source-verified) — lift **+0.50**
  (with 0.97, without 0.47), and +0.53 at 3 samples; the base model still
  *fabricates* (RFC 9334 for EAT, PG 17 for `uuidv7`). **Harder audit 7 → 14
  cases** (realistic, non-telegraphed, multi-vuln: IDOR / SSRF-bypass / TOCTOU /
  prototype-pollution / ReDoS) — **still +0.00**: a capable model catches them
  *in isolation*, so a real audit lift needs cross-file context, not more
  snippets. **Multi-sample** `--samples N` / `--temp T` on both harnesses
  (default 1 / 0), plus 32k gen cap / 100k judge window / progress logging +
  retries for observable, resilient long runs.

## [1.14.1] - 2026-07-11

### Changed

- **Grew the freshness eval 8 → 20 cases** (`evals/cases/freshness.jsonl`): +12
  objective 2026-current-fact cases across domains (TypeScript 7 GA, Cilium
  ztunnel, PQ MLKEM768, OpenAPI 3.2, K8s user-ns 1.36, Keep-a-Changelog 2.0,
  MISRA C:2025, RateLimit draft status, SCIM RFC 9967, libFuzzer maintenance,
  Azure Cobalt 200, rust-lld 1.90) — each verified present in the library +
  primary-source correct + token-scorable. Clean 20-case lift **+0.65
  (sonnet-4.6) / +0.50 (opus-4.8)**, with-library 1.00 on all 20. The tighter
  set strengthens the finding and reveals the base model **fabricates**
  plausible wrong facts with confidence — invents RFC 9440 for RateLimit
  headers, RFC 9816 for SCIM events; "Cobalt 100" not 200, "MISRA C:2023" not
  2025, Keep-a-Changelog "1.1.0" not 2.0. BASELINE.md / README / ROADMAP
  updated to the robust 20-case figures.

## [1.14.0] - 2026-07-11

### Added

- **code-security rules/04 §8 — Tamper-evident logs & audit ledgers** (NIST
  AU-9/AU-10). New section codifying the audit-ledger pattern: unkeyed hash
  chains detect accidents, not adversaries (HMAC or external anchoring
  required); tail truncation / whole-stream deletion is invisible to
  chain-walk verification; hash every attested field incl. server timestamps;
  canonical preimage encoding (§7); **integrity ≠ completeness** (attest and
  report separately); verification must be possible off the storing system;
  vantage (self-reported vs independent chokepoint →
  detection-engineering rules/02); erasure-by-design for immutable stores
  (privacy rules/03 §4 crypto-shredding). +2 audit-checklist items;
  code-security SKILL.md index row and router rule 18 (crypto fan-out)
  updated. Motivated by a real audit of a public "tamper-evident AI-agent
  ledger" where this gap class recurred (unkeyed SHA-256 chain marketed as
  compliance evidence).

- **Eval golden sets + efficacy baseline + clean isolated control** (roadmap
  Next, done). Cases expanded to 20 routing + 13 audit + 7 harder audit
  (`evals/cases/`). New `evals/run-clean.py` — a **raw model-API** harness
  (OpenRouter, key from `.env`, never committed) that removes the in-session
  contamination entirely (no HOME/`CLAUDE.md`/skill-registry) for a true
  library-vs-nothing control. Findings (all in
  `evals/results/2026-07-10/BASELINE.md`, raw in `results/2026-07-11/`):
  **routing recall lift replicates ~+0.10 in the clean control** — +0.09
  (sonnet-4.6), +0.14 (sonnet-5), +0.09 (opus-4.8), with-library 1.00 each;
  even opus-4.8 misses the same rule-driven skills without the router (r01
  testing, r02 sandboxing, r07 code-security, r09 web-frameworks). So the
  in-session +0.08/+0.11 was **not** a contamination artifact — the routing
  lift is real and attributable to the cross-cutting rules. README now cites
  the freshness evidence ("Measured, not asserted") linking `evals/`. **Audit
  lift = +0.00, model-independent** (haiku→sonnet-4.6, original + harder cases):
  strong models recognize textbook vulns library-or-not. **Freshness lift =
  +0.75 (sonnet-4.6) / +0.50 (opus-4.8)** on **8** objective 2026-current-fact
  cases (`cases/freshness.jsonl`, each answer carried in a rules file;
  with-library 1.00) — the decisive finding: the base model is not just missing
  current facts but **confidently wrong** (asserts RFC 7489 not 9989, OWASP A04
  not A06, ingress-nginx "maintained", NIST "8 chars" not 15, TorchServe
  "maintained"), while the with-library arm is 1.00. So the library's value is
  currency (large lift, ~5–7× routing), not routing/recognition (small/zero).
  Also: `.env` added to `.gitignore` (was untracked but unignored).

## [1.13.0] - 2026-07-10

### Added

- **Content-accuracy runbook + eval harness** (2026-07-10 audit STRAT-HIGH-1/2,
  the two top strategic gaps). `docs/MAINTENANCE.md` documents the reproducible
  per-skill re-verification sweep (extract rot-prone claims → verify vs primary
  sources → fix under the no-pins/EOL policies → adversarial re-verify → bump
  `LAST-VERIFIED`) that previously lived only in maintainer memory, and states
  honestly which dimensions are CI-automated vs human/agent discipline. The
  freshness re-verify window is cut **12 → 6 months** (content drifts far
  faster; 6mo stays clearable). New `evals/` prototype: a runnable
  efficacy-regression harness — golden-set cases (`cases/router.jsonl`,
  `cases/audit.jsonl`) + `score.py` (recall/precision vs an agent's
  predictions, exit 1 on any miss). Deliberately not in CI (an LLM eval is
  non-deterministic); it gives a repeatable with-vs-without baseline. Harness
  verified end-to-end this session (perfect predictions → exit 0, misses →
  exit 1); AGENTS.md/CONTRIBUTING.md link the runbook.
- **Invariant 7 — router completeness** (`check-invariants.sh`): every domain
  skill must appear in the router's routing table AND library map; every map
  entry must name a real skill. Automates the drift class the 2026-07-10 audit
  found (the 41st skill was missing from the map for a full release).
  Documented in AGENTS.md/CONTRIBUTING.md.

### Changed

- **Roadmap re-cut around the 2026-07-10 audit** (`docs/ROADMAP.md`): the
  2026-07-01 cycle (fully executed) demoted to history; a fresh Now/Next/Later
  reflects the audit — Now (prove/protect accuracy) closed this cycle, Next
  (grow evals + first 6-month sweep), Later (distribution over coverage,
  STRAT-MED-1). Fixed two STALE bookkeeping items the audit flagged: the
  2026-07-08 sweep is a "34-skill" pass (not "full-library" — it covered 34 of
  40 skills), and the low-severity-triage tally no longer implies 58+32=75
  (the ~75 candidate findings split across files into more line-items).
- **Invariant-gate hardening** (2026-07-10 audit): check 2 now tracks code-fence
  state so a `## Audit checklist` inside a fence no longer satisfies the
  "ends-with" rule (the 2026-07-01 fix was incomplete; verified identical
  verdicts on all current files); check 5's semver guard is a strict
  `X.Y.Z` regex that rejects interior malformations (`1..2`, `1.2`, `1.2.3.4`);
  and CI now fails loudly if `SOTA_DENYLIST` is empty on a trusted (push-to-main
  or same-repo-PR) run instead of silently degrading check 3 to generic-only
  (S-MED-1). Each change adversarially tested to confirm it catches the
  violation.

### Fixed

- **Installer script defects** (2026-07-10 audit): `install.sh` no longer
  aborts (`set -e`, exit 1) when the user declines a routing prompt — routing
  setup is best-effort and now always returns success, so pre-commit setup and
  the final instructions still run (Q-MED-4, reproduced fixed: exit 0, reaches
  the end); `install.sh` profile-linking no longer silently clobbers a real
  file in `~/.claude/profiles` — it backs up + asks first, matching
  `setup_claude_md`'s contract, and keeps the file untouched non-interactively
  (Q-MED-5, reproduced: user content preserved); and `init-gates.sh` writes
  `.pre-commit-config.yaml` as 644 instead of the `mktemp` 600 (Q-LOW).
- **Audit 2026-07-10 content corrections** (all primary-source verified):
  OWASP Top 10 2025 mislabel — Insecure Design is **A06**, not A04
  (`sota-code-security` rules/09); JSON Merge Patch citation **RFC 7386 →
  7396** (obsoleted 2014, `sota-api-design` rules/01); ingress-nginx wording —
  the 2026 CVE wave **was** patched in the final releases (≥1.13.9/1.14.5/
  1.15.1), the standing risk is post-EOL CVEs (`sota-kubernetes` rules/01);
  Iceberg v3 "GA across major engines" overstated → GA on Snowflake/Databricks/
  Spark, Trino still lagging (`sota-data-engineering` rules/01); a
  `grep -v "--"` end-of-options bug in an audit checklist
  (`sota-javascript-typescript` rules/07); a dangling retired-convention
  "last-verified" reference (`sota-confidential-computing` rules/04); and
  ~7 rot-prone version pins reworded to the no-pins policy (Rust 1.96→"recent
  stable", golangci-lint, Swift, Flutter, PHP, Ruby, Vue/Nuxt patch→minor).
- **Router library map** (`skills/sota/SKILL.md`) — added the missing
  `sota-confidential-computing` bullet (41st skill) and refreshed the stale
  `sota-testing` (→09) and `sota-docs-workflow` (→05) bullets. Routing table
  and per-skill indexes were already correct; only the map overview drifted.

### Added

- **`docs/AUDIT-2026-07-10.md`** — second adversarial repository audit (13
  fan-out auditors across 4 lenses + refutation pass, at v1.12.1). Verdict:
  **strong health** — all 6 invariants pass, supply-chain pins genuine, ~150
  rot-prone content claims sampled and primary-source-verified with only a
  handful of small errors, no dangerous advice. Headline findings are
  strategic: no automated content-accuracy gate, no eval harness, coverage
  expansion exhausted vs near-zero adoption. Plus a tail of low-severity
  content/script defects (OWASP A04→A06 mislabel, RFC 7386→7396, ingress-nginx
  "unpatched" wording, router library-map omission of the 41st skill,
  `check-invariants` check-2 fence bypass, two `install.sh` interactive-path
  bugs, ~8 residual version-pins). 11/11 non-trivial findings survived
  adversarial verification; 0 refuted.

## [1.12.1] - 2026-07-10

### Added

- **`sota-network-security` rules/06 — email authentication & anti-spoofing**
  (R12–R14): the library had no coverage of SPF/DKIM/DMARC beyond incidental
  mentions — a real gap given domain spoofing (BEC/phishing) and deliverability.
  Adds SPF (RFC 7208, `-all`, 10-lookup limit), DKIM (RFC 6376, >=2048-bit +
  rotation), **DMARC** (RFC 9989 — the 2026 Proposed Standard obsoleting the
  original RFC 7489; reporting RFC 9990/9991) with the `p=none→quarantine→reject`
  progression and alignment as the actual anti-spoofing control, MTA-STS
  (RFC 8461) + TLS-RPT (RFC 8460) + DANE-for-SMTP (RFC 7672), parked/non-sending
  domain lockdown, ARC (RFC 8617), and the Gmail/Yahoo bulk-sender requirements
  (5,000+/day: SPF+DKIM+aligned DMARC, RFC 8058 one-click unsubscribe, spam
  <0.3%). BIMI noted accurately as an IETF draft (not an RFC), VMC optional.
  Three audit-checklist items + SKILL/router routing updates. Cross-refs
  sota-copywriting rules/04 (marketing-mail content law) and
  sota-detection-engineering (DMARC RUA as a spoofing feed). Every claim
  primary-sourced (RFC editor/IETF datatracker + the Gmail/Yahoo sender rules).
- **`sota-network-security` rules/05 — self-hosted / bare-metal DDoS
  hardening** (R8.1): the one gap in the library's DDoS coverage. Existing
  guidance assumed a scrubbing edge (Cloudflare/Shield/Cloud Armor); this
  adds the L3/4 kernel layer for edges with no provider in front — TCP SYN
  cookies + nftables synproxy (prereqs per the nftables wiki), conntrack-table
  exhaustion sizing/alerting, reverse-path filtering (RFC 3704), and
  not-being-an-amplifier hygiene (BCP 38 / RFC 2827 — no open DNS/NTP/
  memcached/SSDP/chargen reflectors). R8 reframed to name edge scrubbing
  generically (Anycast/provider tiers), with cross-refs to
  sota-cloud-infrastructure rules/03 §10. Two audit-checklist items + SKILL
  index/scope/trigger updates. All claims primary-sourced (nftables wiki,
  kernel.org ip-sysctl, RFC 2827/3704).

## [1.12.0] - 2026-07-09

### Added

- **`sota-confidential-computing`** — confidential computing and cryptographic
  PETs (41 skills total): protecting workloads and data in use from the
  infrastructure they run on — the explicit inverse of `sota-sandboxing`
  (router cross-cutting rule 19 encodes the boundary). SKILL.md + 5 rules:
  01 threat model & selection (CCC definition test — memory encryption alone
  is not CC; five-rung escalation ladder; adversary→mechanism table),
  02 TEE technologies (SEV→SEV-ES→SEV-SNP insufficiency ladder, TDX on
  TME/TME-MK, ARM CCA status incl. Azure Cobalt 200, SGX/LibOS reality,
  Nitro Enclaves' distinct trust model, NVIDIA confidential GPUs,
  side-channel posture), 03 remote attestation (RATS RFC 9334 roles,
  attest-then-release, evidence hard rules, hosted vs self-hosted verifiers,
  TCB recovery, RA-TLS/IETF SEAT), 04 confidential Kubernetes (nodes vs pods,
  CoCo/Kata/Trustee KBS, AKS preview retirement caveat, operational reality),
  05 PETs/COED (FHE families + ISO/IEC 28033 + NIST PEC, MPC/threshold, ZKP
  circuit risk, PSI/OPRF, TEE-vs-PET-vs-DP selection). Built by 5 parallel
  research agents + 2 adversarial verifiers; 54 claims re-verified, 8
  corrected against primary sources (CCC, AMD/Intel/Arm docs, RFC editor,
  Azure/GCP docs, CNCF, NIST, ISO). Per repo policy no current-version pins —
  "latest stable, verify at time of use" throughout.
- **README "how it works" diagram** (`assets/how-it-works.png` + HTML source):
  a four-stage invocation flow (plain prompt → auto-routing → selective
  rules-file loading → BUILD/AUDIT application) with a worked file-upload
  example showing 4 skills loading automatically. Deliberately count-stable
  ("40+") so it never needs re-rendering on skill additions. Also clarified
  two README lines: the language-standards bullet no longer reads as
  "only 4 languages supported", and the invoicing example prompts no longer
  imply the user must name a stack (profile/skill defaults fill it in).
- **Count-surface floor model for the social preview**: the image pill and
  README alt now read **"40+"** so the PNG needs no re-render/re-upload per
  skill addition; `check-invariants.sh` gained `ck_floor` (fails only if the
  tree count drops below the floor); PNG re-rendered once; RELEASING.md
  updated.

### Fixed

- **Low-severity sweep triage (2026-07-09)** — the never-verified
  low-severity suggestions from the 2026-07-08 sweep (~75 candidate findings)
  were re-verified hypothesis-by-hypothesis against primary sources by one
  agent per skill: **58 applied** (each cites the verifying source; e.g.
  GraphQL @oneOf per the September 2025 spec edition, Mercurius WS depth-bypass
  CVE-2026-30241 checklist item, NATS 2.12–2.15 feature gates + the 2.15
  ack-subject ACL migration warning, PEP 734 subinterpreters + Python 3.14
  asyncio introspection, Go 1.25 testing/synctest, C++26 DIS status),
  **32 skipped** with recorded reasons (refuted, already covered by the
  verified-fix pass, or not worth the lines). The applied+skipped tallies
  exceed 75 because some findings split across multiple files. No version pins
  added; all invariants green.
- **Freshness sweep 2026-07-08** — 34-skill research pass (one web-research
  agent per skill; every high/medium finding independently
  adversarially verified against primary sources) fixed **7 high + 58 medium**
  confirmed gaps across 31 skills. Highlights: SurrealDB 3.1.5 security batch
  (databases/08); Argo CD repo-server unpatched gRPC RCE → require
  NetworkPolicy isolation (devsecops/06); ASP.NET Core Data Protection
  CVE-2026-40372 (dotnet/04); TorchServe archived → maintained serving
  runtimes (ml-engineering/05); Cilium mTLS guidance moved to the ztunnel
  integration (network-security/04); ingress-nginx EOL 2026-03-24 + migration
  guidance (network-security/05, kubernetes/01); jqwik 1.10.0 protestware
  advisory (testing/06); NIST SP 800-63B-4 15-char password floor
  (code-security/02); OCSP-stapling guidance retired after Let's Encrypt
  ended OCSP (code-security/04, network-security/06); ATT&CK v18/v19
  restructuring + BadSuccessor/dMSA detection (detection-engineering);
  JDK 24 ZGC/virtual-thread-pinning updates (jvm); K8s user-namespaces GA,
  Landlock ABI correction, 2025 runc CVE triple (sandboxing); TypeScript 7 GA,
  npm v12 script-blocking defaults, June-2026 supply-chain campaigns
  (javascript-typescript); Kyverno CVE-2026-4789 + CEL policy-type
  stabilization (devsecops/07, kubernetes/03); and more — see the PR for the
  full list.
- Genericity: removed three internal-abbreviation/reader-assumption phrasings
  that had slipped past the denylist; patterns added to the private denylist.

### Changed

- Contributor docs synced to this cycle's policy changes: AGENTS.md and
  CONTRIBUTING.md now state the **no-version-pins rule** (latest stable +
  semantic boundaries only, EOL→successor) as a standing convention and
  describe invariant 6's exact-count vs "N+"-floor split; RELEASING.md's
  pre-tag checklist matches the floor model; docs/ROADMAP.md logs
  `sota-confidential-computing` under coverage additions.
- **Version-claim policy applied library-wide**: rot-prone "current release is
  X.Y" claims replaced with "use the latest stable release — verify via a
  quick web search"; version numbers that mark semantic boundaries
  ("introduced/fixed/removed in vX", CVE fix versions, GA milestones) are
  kept. EOL/unmaintained tools are replaced by their maintained successors
  (project-recommended target first, then CNCF-maintained alternatives), with
  a one-line EOL note kept for auditors.
- **Freshness tracking model**: per-file line-1 `<!-- last-verified: YYYY-MM -->`
  markers retired (they duplicated git metadata and stayed 84% unstamped);
  replaced by a single root `LAST-VERIFIED` stamp recording the date of the
  last full-library verification sweep (initialized to 2026-07-08).
  `scripts/check-freshness.sh` rewritten for the new model (red when the
  stamp exceeds the 12-month window; warns on stray per-file markers);
  `freshness.yml`, AGENTS.md, CONTRIBUTING.md, and the README maintenance
  prompt updated accordingly.
- Router (`skills/sota/SKILL.md`): added cross-cutting routing rule 18,
  **"Cryptography fans out"** — a single lookup that maps a crypto task to its
  distributed owners (algorithm/AEAD/key-handling/TLS-client/PQC →
  `sota-code-security` rules/04; key material/storage/rotation →
  `sota-secrets-management`; TLS server/PKI/cert lifecycle →
  `sota-network-security` rules/06; FIPS-validated-module →
  `sota-security-compliance` rules/02). Documents the deliberate no-single-crypto-skill
  design; no content moved.

## [1.11.0] - 2026-07-06

### Added

- **`sota-web-frameworks`** — React 19 + Next.js and Vue 3 + Nuxt 4 engineering,
  plus the cross-cutting concerns of server rendering (40 skills total). SKILL.md
  + 7 rules files: 01 baseline (support/EOL matrix, render-mode selection, React
  Compiler), 02 React 19 (hooks, Suspense, the Actions model, `dangerouslySetInnerHTML`),
  03 Next.js (App Router, Server Actions as public endpoints, the caching model —
  `use cache`/Cache Components/PPR/ISR — `proxy.ts`, the Data Access Layer), 04 Vue 3
  (Composition API, reactivity pitfalls, `defineModel`, `v-html`), 05 Nuxt 4
  (`useFetch`/`useAsyncData`, `useState`, `runtimeConfig`, Nitro server routes,
  `routeRules`), 06 SSR & hydration (mismatches, state-serialization XSS,
  cross-request state pollution, cache safety, CSP with streaming SSR), and 07
  framework security (server/client secret boundary, authorization placement,
  SSRF surfaces, consolidated CVE reference). Every version and CVE claim
  web-verified against primary sources (react.dev, nextjs.org, vuejs.org, nuxt.com,
  GitHub Security Advisories) and stamped `last-verified: 2026-07`. Notable
  security coverage: the 2025-12 React Server Components RCE (CVE-2025-55182
  "React2Shell" / CVE-2025-66478), the middleware auth bypass (CVE-2025-29927),
  Next cache-poisoning and SSRF CVEs, and the Nuxt/Nitro/h3/IPX/devalue advisory
  waves. Router routing table + library map + cross-cutting rule 6 updated;
  count surfaces updated to 40 skills / 289 files / ~57k lines (README
  badge/hero/alt/table, plugin.json, marketplace.json, social-preview pill + PNG).

---

Releases **1.10.0 and earlier** are archived: 1.10.0–1.5.0 in
[docs/CHANGELOG-archive.md](docs/CHANGELOG-archive.md), 1.4.0 and earlier in
[docs/CHANGELOG-archive-2.md](docs/CHANGELOG-archive-2.md).

[1.16.0]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.16.0
[1.15.0]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.15.0
[1.14.1]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.14.1
[1.14.0]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.14.0
[1.13.0]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.13.0
[1.12.1]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.12.1
[1.12.0]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.12.0
[1.11.0]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.11.0
