# Roadmap

Priorities set by the **2026-07-10 audit**
([AUDIT-2026-07-10.md](AUDIT-2026-07-10.md)). Ordered; revisit after each
release. The 2026-07-01 cycle is fully executed and kept below as history.

## Open tasks — next-session pick-up *(as of 2026-07-16)*

**v1.16.0 released** (2026-07-16, PR #115, tag `v1.16.0`) — rolled up the big
post-v1.15.0 batch (PRs #88–#114). Executed across it: multi-sample tightening
(item 1), live-agent BUILD validation (item 2), cross-file audit (item 3, +0.00 →
agentic large-repo is the frontier, 3′), the **competitor benchmark** (item 6)
**and a 5-domain breadth run** (the lead tracks the unguided baseline, not the
domain — SOTA-skills leads on incomplete-by-default tasks: backend [Python+Go] +
hard frontend; ties on simple UI + templated IaC), a first **decay/multi-turn** run
(item 5, no decay at moderate scale), a **discoverability overhaul** (docs/INDEX.md,
docs/CONTEXT-MANAGEMENT.md, RESULTS.md scoreboard, README TOC), the **500-line cap
scoped to skill files only**, a **4-way accuracy sweep**, and **theme-aware
benchmark + breadth charts**.

**Post-release, same session (PRs #111–#117):** concluded the breadth comparison
(#111); mined a separate agent-orchestration project (`~/Github/Dev-AID`) and adopted
**three pure-Markdown conventions, each independently measured** — negative routing
cross-refs, plan-concreteness in BUILD step 3, and an evidence-based-completion
operating principle (#112) — with regression checks proving no loss (completeness
held **0.991/+0.385** #112; routing held **1.00** #113); built the **description-
routing eval** measuring the skill auto-loader path (#114, honest **+0.00** —
saturated like audit; cross-refs kept as zero-cost defensive clarity); cut **v1.16.0**
(#115); consolidated the breadth chart + full story into RESULTS.md (#116); and added
**`sota-docs-workflow` rules/01 §8 "The documentation baseline"** — the must-have doc
set incl. community-health files, GitHub search precedence verified (#117). Runtime-
bound Dev-AID ideas (memory-bank persistence, RAG, worktree locks, agent framework)
were deliberately **not** ported.

**Post-v1.16.0 (2026-07-20):** added **`sota-code-security` rules/10 "Silent
control failure"** — controls that look enabled and do nothing. A gap analysis
over the whole tree found 9 of its 12 concepts uncovered anywhere (the falsi-
fication question, optional-dependency degradation, weak existence checks,
zero-rule loads, attacker-triggerable early returns, doc/code default drift,
hardcoded report numbers, shipped-artifact gaps, asymmetric negative-claim
evidence); fail-open (rules/03) and test vacuity (`sota-testing` rules/02/06/09)
were already strong and are cross-referenced, not duplicated. Wired into the
**default** paths rather than left opt-in: router BUILD step 4 (falsification
question over every control in the diff), a new AUDIT **step 4 silent-control
pass**, routing rule 20, and the asymmetric evidence burden in operating
principle 3 + `sota/rules/01` §5. **Then measured** (same day,
[`evals/results/2026-07-20/SILENT-FAILURE.md`](../evals/results/2026-07-20/SILENT-FAILURE.md)):
a case set run two ways — vocabulary-given and open-ended/blind-judged — plus an
**ablation arm** that drops rules/10 from the with-library context. A first
15-case version showed **+0.07**; the set was then **grown to 49** (41 positives,
8 loud-failure negative controls, 6 mechanisms rules/10 does *not* enumerate) and
**the lift did not replicate**: **+0.03** vocabulary / **−0.01** open-ended, both
inside a per-arm spread of ±0.04, with rules/10's ablated contribution **+0.00**.
The +0.07 was small-sample noise (the 15-case with-arm sat at 0.99–1.00 — no
headroom); it is **retracted** in `RESULTS.md` and the writeup. Silent-control
detection therefore joins audit / cross-file audit / desc-routing as a **+0.00**
dimension. rules/10 is kept on gap-analysis grounds with **no efficacy claim**.
Open follow-ups: (a) **grow the `novel` subgroup to 20+** — on the current 6, the
*unguided* arm scored 1.00 vs 0.83 for both library arms, a possible
**taxonomy-anchoring** effect (a model handed an 11-item list may match against
the list instead of applying the question) that is a hypothesis at n=6 and would,
if it reproduces, argue for rewriting rules/10 to lead on the question and lighten
the catalogue; (b) the **agentic** design (large repo + generic "audit this" → do
silent no-ops appear unprompted?) — the only design that can measure what the file
is actually for, and the same frontier the cross-file audit run identified;
(c) cross-model replication. Four cases defeat every arm (build-tag no-op, glob
extension mismatch, env-filter mismatch, unawaited async assertion) — deliberately
**not** written into the rule, since that is fitting guidance to the test set.

**Now open, ordered by value:**
- **IN PROGRESS — verify the flagship +0.39 against the CURRENT BUILD workflow.**
  `evals/run-completeness.py`'s `BUILD_WORKFLOW` is a **hand-compressed mirror** of
  router BUILD steps 3–4, not a live read, and it had **drifted** for four days (the
  falsification clause added in #119 was missing), so the most-cited number was being
  measured against a workflow that no longer shipped. Unblocked 2026-07-20 after a
  credit top-up. **Arm A (drifted mirror) measured: without 0.59 → with 1.00,
  LIFT +0.40** — reproducing the recorded +0.39, so the figure was never wrong, only
  measured against stale text. The mirror is now synced and **arm B is running**;
  the open question is whether the with-arm holds at ~1.00 once the falsification
  clause is in the prompt. **Drift can no longer recur silently**: the mirror pins a
  sha256 of the router's BUILD section (`ROUTER_BUILD_SHA`) and the runner aborts on
  mismatch rather than measuring unshipped text — guard watched to fire before being
  trusted.
- **Distribution** (item 7): publish the salience write-up
  (`docs/writeups/completeness-blind-spot.md`) — LinkedIn is the proven channel
  (corroborated 2026-07-20: it is the **top referrer** in GitHub traffic);
  marketplace visibility; badge→verifiable-audit. **Traffic measured 2026-07-20:**
  ~24 organic clones/day (the three days with zero CI runs show clones exactly equal
  to unique cloners) against **7 stars, 0 watchers, 1 issue ever**. Since the install
  path *is* `git clone`, clones are the adoption metric and stars badly understate it
  — but the project also learns nothing from those users, which is what the
  **gap-reporting loop** (#124, shipped) is meant to change. Whether it produces
  reports is unmeasured; if it yields nothing in a few weeks, cut it.
- **As-deployed competitor comparison** + **more competitor domains** (data/mobile/
  CLI); the baseline-driven finding is established but these extend it.
- **Agentic large-repo audit** (3′) and **constraint-budget probe** (4).
- **Multi-turn amplification, at scale** (5): the decay run found *no* decay at
  moderate scale — needs much larger intervening context to find the breaking point.
- **Grow the eval case sets** (item 1 sub-task, content authoring). Done this cycle:
  silent-failure 15 → **69** (35 enumerated + 26 novel + 8 negative controls) and a
  new 30-case audit-precision set. Still thin: the **8 negative controls** (an arm
  that over-flags is only weakly penalised — and the one unexplained signal left is
  there, the ablated arm scoring 1.00 vs 0.75 on them), the 7-case completeness set,
  and competitor domains beyond the five measured.
- **First 6-month accuracy sweep ~Jan 2027** (item 8; bump `LAST-VERIFIED`).

Historical per-item notes below (kept as the record of what was done):

1. **Tighten the eval numbers (confidence, not point estimates).** **Multi-sample
   DONE 2026-07-13** — [`evals/results/2026-07-13/MULTI-SAMPLE.md`](../evals/results/2026-07-13/MULTI-SAMPLE.md).
   All three value dimensions re-run at `--samples 3 --temp 0.7`: completeness
   **0.60 → 1.00 (+0.39)** with the with-arm at ±0.01 across-case sd (reproduces
   the single-sample headline, 6/7 cases perfectly steady); routing **0.90 → 1.00
   (+0.10)**, with-arm ±0.00; freshness **0.44 → 0.97 (+0.53)**, with-arm ±0.00
   (reused). The with-library arm is near-zero variance everywhere; the sampling
   wobble is all in the unguided arm. Single-sample caveat retired. **Remaining
   sub-task:** *grow* the completeness (7) and freshness (32) sets — that's
   content authoring (new cases), not a re-run, and is still open.
2. **Validate the v1.15.0 BUILD-workflow changes in a *real* agent run.**
   **DONE 2026-07-13, fully closed** — [`evals/results/2026-07-13/LIVE-BUILD.md`](../evals/results/2026-07-13/LIVE-BUILD.md).
   Seven live sub-agents built the 7 completeness tasks through the real router
   flow (load-lean → checklist → terminal self-audit). Verified from their
   `process.md` audit logs (primary source): all 7 followed the workflow;
   cross-cutting concerns present in every applicable build; the self-audit gate
   **caught and fixed real gaps** live (c6: prod `/docs` exposure + unbounded DB
   critical section; c3: orphaned-task cancellation bug). The blind-judge scalar
   (run once credit was restored) is **0.99 mean, 6/7 perfect — matching the
   0.99 simulation (0.987 vs 0.988) and far above the 0.60 base**, proving the paste-based eval is a faithful
   proxy for the live router flow (`evals/results/2026-07-13/live-build.json`).
3. **Cross-file / repo-level audit eval.** **DONE 2026-07-13** —
   [`evals/results/2026-07-13/REPO-AUDIT.md`](../evals/results/2026-07-13/REPO-AUDIT.md),
   `evals/run-repo-audit.py`, 15-file fixture with 8 defects invisible in any
   single file. Result: **+0.00 on sonnet-4.6 and opus-4.8** (strict,
   file-attributed). The finding *refines* the hypothesis: cross-file is not the
   barrier — **context the model can't hold at once** is. A ~17 KB repo pastes
   whole, so recognition (already saturated) catches everything. The real
   frontier is now item 3′ below.
3′. **Agentic large-repo audit eval** *(new, replaces the snippet/small-repo
   version).* The only untested audit-lift path left: a repo too large to hold in
   context, audited through a **tool-driven agent loop** (selective file reads
   under a budget), with-library vs without — where the router's "which files to
   open, what to connect" guidance is the thing under test, not recognition.
   Materially bigger harness (a real agent loop, not one API call).
4. **Constraint-budget probe** *(new, from the v1.15.0 whack-a-mole: c1 dropped
   size-limit when principle 5 was added).** Measure how many simultaneous
   non-negotiables a model reliably satisfies — informs how short principle 5 and
   per-task checklists must stay. Directly tests the salience/attention finding
   in [`WHY-COMPLETENESS-RESIDUAL.md`](WHY-COMPLETENESS-RESIDUAL.md).
5. **Multi-turn / agentic amplification test** *(new)*. **First run DONE 2026-07-15**
   (`evals/run-decay.py`, `results/2026-07-13/DECAY.md`): guidance at turn 1 → K
   filler turns → build probe. **No decay at moderate scale** (guidance held over 30
   turns) — the filler is too small to dilute a ~18.6K-token anchor, so it bounds
   the problem but doesn't find the breaking point. **Open:** scale up (much larger
   intervening context, or a subagent chain).
6. **Competitor-library benchmark** — **DONE 2026-07-14/15** (see "Unexplored ideas"
   below for the full result): SOTA-skills beats the fair peers on completeness on
   backend tasks, content-only. **5-domain breadth (2026-07-15/16) reframes it: the
   lead tracks the unguided BASELINE, not the domain** — SOTA-skills leads +~10 pts
   where a base model ships incomplete code (Python+Go backend, hard SSR/auth
   frontend; baseline ≤0.67) and ties where it's already complete (simple frontend
   77%, IaC 87%). See `results/2026-07-13/BREADTH.md`. The honesty gate is cleared for a *scoped-to-backend* "vs library X"
   claim; every doc surface was rescoped accordingly.
7. **Distribution over coverage** (item 6): marketplace visibility, a published
   before/after demo, badge→verifiable-audit. **Started 2026-07-13/14:** (a) the
   README now leads with the measured lifts as a scannable list (completeness
   +0.39, freshness +0.53, routing +0.10) and puts the clone/script install right
   after the plugin method (PRs #92–#93); (b) a publication draft of the
   completeness/salience finding is ready at
   [`docs/writeups/completeness-blind-spot.md`](writeups/completeness-blind-spot.md)
   (verified before/after — webhook 0.50→1.00, upload 0.55→1.00). **Still open:**
   the maintainer publishes the write-up (LinkedIn is the proven referral channel
   per traffic data); marketplace visibility and badge→verifiable-audit are
   untouched. The compelling demo is **completeness** before/after, not audit —
   audit lift is +0.00 (item 3), so an audit demo would undersell.
8. **Scheduled — first 6-month accuracy sweep ~Jan 2027** (item 5): re-verify
   fast-moving claims per `docs/MAINTENANCE.md` and bump `LAST-VERIFIED`.

## Now — prove and protect accuracy *(done this cycle)*

The audit's verdict was "content is trustworthy; the gap is that nothing
*proves or protects* accuracy." Closed 2026-07-10 (PRs #63–#66):

1. **Content-accuracy runbook + shorter window** — `docs/MAINTENANCE.md`
   documents the reproducible per-skill re-verification sweep (was only in
   maintainer memory); `check-freshness.sh` window cut 12→6 months. *(#66)*
2. **Audit defect cleanup** — content corrections (OWASP/RFC/ingress/Iceberg/
   version-pins) + router-map refresh *(#63)*; **invariant 7** (router
   completeness) + check-2 fence / check-5 semver / CI fail-open hardening
   *(#64)*; installer decline-abort + profile-clobber *(#65)*.
3. **Eval-harness prototype** — `evals/` (golden-set cases + `score.py`,
   verified end-to-end) makes the efficacy claim measurable. *(#66)*

## Next — grow what the prototypes started

4. **Eval baseline + clean isolated control** — *done 2026-07-10/11*
   ([`BASELINE.md`](../evals/results/2026-07-10/BASELINE.md); `evals/run-clean.py`):
   **routing lift ~+0.10 replicates in a true library-vs-nothing raw-API
   control** (+0.09/+0.14/+0.09 across sonnet-4.6/sonnet-5/opus-4.8) — the
   contamination concern is resolved, the lift is real. **Audit +0.00**;
   **Freshness +0.50–0.65** (base model confidently wrong on 2026 facts, but a
   web-search agent would likely recover most of it — predicted, untested). **Completeness +0.39** (0.60→0.99 over
   7 tasks, full library, `cases/completeness.jsonl` + `run-completeness.py`,
   blind opus judge) — the **thesis, validated**: from a bare "build X" prompt the
   base model skips tests/rate-limits/logging/transport ~40% of the time; the
   library embeds them, and search can't close this gap. **Load-bearing as an
   ablation:** base 0.60 → +rules ~0.89 → +BUILD self-audit 0.93 → +principle 5
   0.99 (`results/2026-07-13/`). Surfaced fixes, all landed: the self-audit is a
   hard BUILD gate; cross-cutting concerns are the router's short **operating
   principle 5**; and the BUILD workflow now says load-lean + plan-with-checklist
   + terminal re-read. **Root-cause investigation (2026-07-13):** the residual is
   NOT a coverage gap (the forgotten rule was in scope + in a checklist); it's a
   **salience / context-rot attention effect** — *adding* the missing rule made it
   worse, a short reminder fixed it ([`docs/WHY-COMPLETENESS-RESIDUAL.md`](WHY-COMPLETENESS-RESIDUAL.md),
   experiments + literature). Curated for readers in
   [`docs/WHY-IT-WORKS.md`](WHY-IT-WORKS.md) (honest "vs. an unguided model"
   framing — see the unexplored idea below). **Eval-suite hardening — done
   2026-07-12:** completeness 4→**7** tasks; freshness 20→**32** cases
   (all primary-source-verified; +0.50, and +0.53 at 3 samples with 0.97±0.00 vs
   0.44±0.03); harder-audit 7→**14** — still +0.00 (a capable model catches even
   subtle/multi-vuln snippets *in isolation*, so a real audit lift needs
   cross-file context, not more snippets); and `--samples/--temp` added to both
   harnesses (retires the single-sample caveat on the cheap dimensions).
   **Shipped as v1.15.0** (2026-07-13, PRs #78–#85). Follow-through: the
   multi-sample averaging is **done** (2026-07-13, PR #91 — see Open tasks item 1,
   with-arm near-zero variance); *growing* the completeness + freshness sets is
   still open (Open tasks item 1, content authoring).
5. **First 6-month accuracy sweep** comes due ~Jan 2027 (freshness window) —
   run it per the `docs/MAINTENANCE.md` runbook and bump `LAST-VERIFIED`.

## Later — distribution over coverage

6. **Pause net-new skills; invest in distribution.** Coverage is an exhausted
   lever at current adoption (audit: 4 stars / 1 issue after 41 skills). Put
   the effort into visibility (marketplace, a published before/after audit
   demo) and the badge→verifiable-audit idea (link the "Built with" badge to a
   committed audit report + commit SHA). *(audit STRAT-MED-1)*

## Unexplored ideas

- **Comparative benchmark vs. named competing libraries.** ~~Unexplored~~
  **DONE 2026-07-14** ([`evals/results/2026-07-13/COMPETITOR-BENCHMARK.md`](../evals/results/2026-07-13/COMPETITOR-BENCHMARK.md),
  `evals/run-competitors.py`, `evals/cases/competitors.json`). SOTA vs. the fair
  peers, content-only, blind-judged, 7 build tasks: **SOTA 0.99 >
  [affaan-m/ECC](https://github.com/affaan-m/ECC) ~230k★ 0.87 >
  [PatrickJS/awesome-cursorrules](https://github.com/PatrickJS/awesome-cursorrules) ~40k★ 0.83 >
  [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) ~23k★ 0.81**
  (unguided 0.58). SOTA wins/ties every one of 21 cases, loses none; competitors
  are legitimate (all +0.23–0.28 over unguided) but drop the cross-cutting
  non-negotiables SOTA embeds. The honesty gate is **cleared** — `WHY-IT-WORKS.md`
  now carries a scoped "vs library X" claim. **Breadth DONE 2026-07-15/16 — lead tracks the
  BASELINE not the domain (5 domains, BREADTH.md):** SOTA-skills leads where the base
  model is incomplete (backend any-lang, hard frontend) and ties where it's complete
  (simple frontend, IaC). [old note kept:] on 3 simple React tasks SOTA-skills ties ECC and
  claude-skills (all 97%, even losing one task); frontend completeness is easy
  (unguided 77% vs 58% backend) so any guidance reaches the top. So the claim is
  scoped to **backend**, not general (`competitor-breadth-frontend.json`).
  **Follow-ups still open:** multi-sample the arms; more domains (data/mobile/CLI);
  optionally an *as-deployed* comparison (each library with its own method).
  Original plan/targets kept below for reference.
- **(reference) Original competitor-benchmark plan.** Every eval to
  date is library-vs-*nothing* (an unguided model), so the public claim was
  honestly limited to that; to earn a "vs X" claim, run a competitor's content
  as a **third arm** (same fixed rubric, blind judge, token budget) and report the
  delta — **publishing it even if SOTA ties or loses.**
  **Targets validated 2026-07-14 via the GitHub API** (stars + created-date +
  license + repo structure). **Pick on purpose-overlap, not raw stars** — many
  high-star repos are a *different kind* of thing, and the biggest ones are all
  2026-new with explosive (plausibly inflated) star growth, so treat the numbers
  skeptically. Tiers:
  - **Same-kind engineering guidance a model reads to build/audit code** (the fair
    completeness peers): **[affaan-m/ECC](https://github.com/affaan-m/ECC)** (~230k★, MIT, cross-AI — Claude/Codex/
    Cursor/Gemini/Kimi/Kiro; "agent harness… skills, security, research-first dev"
    → highest-profile, PRIMARY); **[alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills)** (~22.6k★, MIT,
    multi-domain engineering + `audit/` + plugin, structured like SOTA → closest
    same-kind peer); **[PatrickJS/awesome-cursorrules](https://github.com/PatrickJS/awesome-cursorrules)** (~40.3k★, CC0, per-stack
    `.cursorrules` → the rules-library reference); tertiary
    [SebastienDegodez/copilot-instructions](https://github.com/SebastienDegodez/copilot-instructions) (~190★ but genuinely same-kind: DDD/
    clean-arch/testing rules) and [sanjeed5/awesome-cursor-rules-mdc](https://github.com/sanjeed5/awesome-cursor-rules-mdc) (~3.5k★).
  - **Popular but a *different axis*** (compare only on a workflow/quality axis, not
    build-completeness): **[garrytan/gstack](https://github.com/garrytan/gstack)** (~122k★, cross-AI — a 23-tool
    role/workflow setup, not a rules library); **`multica-ai/andrej-karpathy-
    skills`** (~192k★ but **no license** → can't legally reuse content; mostly one
    behavior CLAUDE.md).
  - **Excluded, different category:** `x1xhlol/system-prompts-and-models-of-ai-
    tools` (~142k★ leaked tool prompts); [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) (~89k★ token
    gimmick); [agentsmd/agents.md](https://github.com/agentsmd/agents.md) (the spec/website); `travisvn/awesome-claude-
    skills` (link list); [ComposioHQ/awesome-claude-skills](https://github.com/ComposioHQ/awesome-claude-skills) (~67k★ productivity).
  Fairness controls: each competitor's *best-matching* content per task (not a
  strawman), same fixed rubric + blind opus judge + token budget, record commit
  SHAs, respect licenses (skip no-license repos for pasted content), state
  format/scope caveats, **publish even if SOTA ties/loses.** Expected edge =
  freshness (SOTA primary-source-verified; competitor rules go stale) + the
  cross-cutting completeness the self-audit/principle-5 design recovers; expected
  non-edge = raw "does the code work". **Cost:** ~$16 per competitor per full
  completeness run (3-arm ≈ 1.5× the 2-arm) — one pilot fits the current ~$36
  balance; the full `affaan-m/ECC` / `alirezarezvani/claude-skills` /
  `PatrickJS/awesome-cursorrules` sweep needs a top-up. Still
  gated on the maintainer wanting a "vs X" claim at all (2026-07-12 chose the
  honest vs-unguided framing).
- **Cross-file / repo-level audit eval.** ~~Unexplored~~ **Explored 2026-07-13,
  no lift** ([`evals/results/2026-07-13/REPO-AUDIT.md`](../evals/results/2026-07-13/REPO-AUDIT.md)).
  Built the planted-vuln repo (8 defects invisible in any single file) the audit
  dimension was said to need. Result: **+0.00** on two models — when the whole
  repo fits in one context, cross-file collapses to "read it all" and recognition
  (already saturated) catches everything. The hypothesis was wrong about *why*
  audit is +0.00: the barrier is **context that exceeds what the model holds**,
  not file-spanning per se. The genuine remaining frontier is the agentic
  large-repo eval (open task 3′) — a repo too big to paste, audited under a
  context budget through tool-driven reads.

---

## Completed — 2026-07-01 audit cycle *(history)*

### Now — correctness of what's shipped

1. **Fix the audit's HIGH and MEDIUM findings.** The two HIGHs
   (sota-security-compliance frontmatter invalid under strict YAML;
   `init-gates.sh` language-detection SIGPIPE fail-open) plus the script
   silent no-ops, the denylist-check gaps, and the sota-jvm scoped-values
   correction. *(Landed in the audit-remediation PR, #37.)*
2. **Library lint gate** (extends `check-invariants.sh`): YAML-parse all
   SKILL.md frontmatters, VERSION == plugin.json == latest tag lockstep,
   README count-basis check, shellcheck over `scripts/`. Blocks the whole
   defect class the audit found. *(Landed: YAML-validity check and shellcheck
   CI job in #37; version-lockstep (check 5) and count-surface (check 6)
   invariants on 2026-07-04.)*

### Next — keep the core promise true

3. **Freshness ledger.** Per-rules-file `last-verified: YYYY-MM` metadata plus
   a scheduled CI job reporting files past their re-verify window. The README
   promises "fast-moving claims are web-verified against primary sources";
   today only ~21 of 220 rules files carry any verification date, so the
   promise is unauditable — and every "2026 baseline" assertion goes silently
   stale in 2027. *(Mechanism landed 2026-07-04 as per-file line-1 markers;
   SUPERSEDED 2026-07-09, PR #52: a full-library verification sweep
   (per-skill web research, adversarially verified, 65 fixes applied)
   replaced the per-file ledger with a single root `LAST-VERIFIED` stamp —
   the per-file backfill would have duplicated git metadata at 210-file
   scale. `check-freshness.sh` now reds when the stamp exceeds the
   12-month window; re-sweeping resets it. DONE.)*
4. **Release procedure in-repo** (`RELEASING.md` or a CONTRIBUTING section):
   VERSION + plugin.json + CHANGELOG + tag + GitHub release, plus the
   version-bearing strings in README/CLAUDE.md. Eight releases shipped in the
   first 14 days from a procedure that lives outside the repo; the v1.0.0
   pointer rot in CLAUDE.md was the predictable result. *(Landed 2026-07-02:
   [RELEASING.md](../RELEASING.md), incl. the count-bearing surfaces — the
   v1.8.0 release found the social-preview image still saying "30 skills",
   the same rot class again.)*
5. **Structured feedback intake.** `.github/ISSUE_TEMPLATE` with a
   bad-guidance report (file:line + primary source, mirroring SECURITY.md's
   format) and a skill-request template; enable Discussions. A no-telemetry
   project's only adoption signal is structured issues — currently absent.
   *(Landed 2026-07-04: both issue forms — the bad-guidance form requires a
   primary source and redirects security-sensitive reports to the private
   advisory flow — plus a contact-link config; Discussions enabled.)*

### Later — coverage decisions (decide, don't drift)

6. **Close or declare the language/domain gaps.** PHP and Ruby have no skill
   (incidental mentions only); Swift exists only at sota-mobile's
   platform/stack level, not as a language-idiom skill; Active
   Directory/Kerberos/ADCS have zero coverage despite identity and detection
   skills whose real-world audits are AD-heavy. Ship `sota-php`, `sota-ruby`,
   a Swift-language rules file, and AD content — or add a README "coverage &
   non-goals" section stating what is deliberately excluded. The mission
   statement overclaims until one of the two happens. *(Closed 2026-07-04:
   all four builds shipped — `sota-php`, `sota-ruby`, `sota-mobile` rules/07
   (Swift language), and AD/Kerberos/ADCS as `sota-identity-access` rules/07
   + `sota-detection-engineering` rules/07 — each claim web-verified against
   primary sources; the README "Coverage & non-goals" section now lists only
   true non-goals (Scala/Elixir, standalone C, platform-engineering depth).)*

## Coverage additions (post-audit, demand-driven)

- **`sota-web-frameworks`** *(shipped 2026-07-06)* — React 19/Next.js + Vue 3/Nuxt 4
  and the SSR/hydration/server-components concerns those stacks share. Previously
  only incidental coverage existed (a React section in `sota-javascript-typescript`
  rules/06; XSS-sink names in rules/05). Closes the frontend-framework gap that sat
  between the language skill (`sota-javascript-typescript`) and the design skill
  (`sota-frontend-design`) without overlapping either. 40 skills total.
- **`sota-confidential-computing`** *(shipped 2026-07-09)* — TEEs
  (SEV-SNP/TDX/ARM CCA, SGX enclaves, Nitro Enclaves, confidential GPUs),
  remote attestation (RATS RFC 9334, attest-then-release), confidential
  Kubernetes (CoCo/Kata/Trustee), and cryptographic PETs (FHE/MPC/ZKP/PSI).
  Covers the workload-from-host trust direction — the inverse of
  `sota-sandboxing`; router rule 19 encodes the boundary. Demand-driven
  (user gap-check found zero prior coverage). 41 skills total.
- **Within-skill gap closures** *(2026-07-09/10, demand-driven)* — two coverage
  gaps found by user-prompted assessments, closed as sections in
  `sota-network-security` (no new skill): **rules/05 R8.1** self-hosted /
  bare-metal L3/4 DDoS hardening (SYN cookies/synproxy, conntrack, rp_filter,
  no-open-reflector — the library assumed a scrubbing edge); **rules/06
  R12–R14** email authentication & anti-spoofing (SPF/DKIM/DMARC, MTA-STS/DANE,
  bulk-sender rules — previously only incidental SPF/DKIM mentions). Assessment
  also judged firmware/UEFI/measured-boot-as-a-discipline a real-but-niche gap,
  deliberately **not** built (partly subsumed by confidential-computing +
  kubernetes; revisit only on demand).

## Maintenance mode (de-prioritized by audit evidence)

- **Optional-extras scripts** (`statusline.sh`, `init-gates.sh`,
  `gen-agents-md.sh`): highest defect density found by the audit, and plugin
  users don't get them by default. Bug-fix only; no new extras until the
  plugin path can deliver them natively.

## Explicitly rejected (with reasons, so they aren't re-litigated)

- **History rewrite to purge the pre-2026-07 denylist names** — rejected
  2026-07-01: the names are low-sensitivity, the repo already has public
  clones/forks/archives, and a rewrite breaks every clone and all release
  tags. Going forward the list is externalized (git-ignored locally, CI
  secret) so the tree no longer discloses it.
- **Telemetry/analytics in the scripts** — privacy stance; feedback comes
  from issues (see item 5).
- **Importing an external system-design "fundamentals" guide** — assessed
  2026-07-14 (a compiled X-thread series on scaling/architecture: load
  balancing, CDN, caching layers, API gateway, CAP, sharding, replication,
  consistency, queues, fault tolerance, etc.). **No action:** it is a *secondary
  source* (can't be cited under the primary-source policy), and a topic-by-topic
  check found full coverage already — caching + stale-while-revalidate
  (`sota-performance/05`, `sota-architecture/05`), CDN/origin-lock
  (`sota-cloud-infrastructure/03 §9`), L4/L7 LB + health checks
  (`cloud-infrastructure/03 §8`, `architecture/04`), gateway-vs-mesh N-S/E-W
  (`sota-network-security`), rate limiting (router principle 5), and the
  distributed-systems topics across `sota-architecture/03,05` + `sota-databases`.
  Only marginal non-coverage: enumerating LB *algorithms* (deliberately subsumed
  by the "use managed LBs + meaningful health checks" stance) and back-of-envelope
  capacity estimation (an interview skill, not a BUILD/AUDIT rule — a non-goal).
