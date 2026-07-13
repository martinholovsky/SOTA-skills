# Roadmap

Priorities set by the **2026-07-10 audit**
([AUDIT-2026-07-10.md](AUDIT-2026-07-10.md)). Ordered; revisit after each
release. The 2026-07-01 cycle is fully executed and kept below as history.

## Open tasks — next-session pick-up *(as of v1.15.0, 2026-07-13)*

Nothing is blocking; v1.15.0 shipped clean. Ordered by value. **Items 2 and 3
were executed 2026-07-13 (post-v1.15.0, Unreleased in CHANGELOG) — see notes.**

1. **Tighten the eval numbers (confidence, not point estimates).** Completeness
   is single-sample (deterministic at temp 0); routing/freshness mostly single.
   Run `run-completeness.py --samples N --temp 0.7` (support already added) and
   report mean ± spread; grow the completeness (7) and freshness (32) sets.
   Small–medium effort, high trust payoff. **(OpenRouter credit restored
   2026-07-13 — no longer blocked; still the top open eval task.)**
2. **Validate the v1.15.0 BUILD-workflow changes in a *real* agent run.**
   **DONE 2026-07-13, fully closed** — [`evals/results/2026-07-13/LIVE-BUILD.md`](../evals/results/2026-07-13/LIVE-BUILD.md).
   Seven live sub-agents built the 7 completeness tasks through the real router
   flow (load-lean → checklist → terminal self-audit). Verified from their
   `process.md` audit logs (primary source): all 7 followed the workflow;
   cross-cutting concerns present in every applicable build; the self-audit gate
   **caught and fixed real gaps** live (c6: prod `/docs` exposure + unbounded DB
   critical section; c3: orphaned-task cancellation bug). The blind-judge scalar
   (run once credit was restored) is **0.99 mean, 6/7 perfect — identical to the
   0.99 simulation and vs 0.60 base**, proving the paste-based eval is a faithful
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
5. **Multi-turn / agentic amplification test** *(new)*. The forgetting was
   measured in a *single* call; the literature says chains/subagents make it
   worse. Build the same task across a subagent chain and see if the fixes hold.
6. **Deferred — competitor-library benchmark** (Unexplored, below): only if a
   "better than library X" claim is wanted; needs a named target.
7. **Distribution over coverage** (item 6): marketplace visibility, a published
   before/after demo, badge→verifiable-audit. **Started 2026-07-13:** a
   publication draft of the completeness/salience finding is ready at
   [`docs/writeups/completeness-blind-spot.md`](writeups/completeness-blind-spot.md)
   (with the verified before/after contrast — webhook 0.50→1.00, upload
   0.55→1.00). Maintainer to publish (LinkedIn is the proven referral channel per
   traffic data). Note: the compelling demo is **completeness** before/after, not
   audit — audit lift is +0.00 (item 3), so an audit demo would undersell.
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
   web-search agent recovers most of it). **Completeness +0.39** (0.60→0.99 over
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
   **Shipped as v1.15.0** (2026-07-13, PRs #78–#85). Remaining follow-through:
   grow the completeness + freshness sets further and average more samples per
   arm for tighter CIs.
5. **First 6-month accuracy sweep** comes due ~Jan 2027 (freshness window) —
   run it per the `docs/MAINTENANCE.md` runbook and bump `LAST-VERIFIED`.

## Later — distribution over coverage

6. **Pause net-new skills; invest in distribution.** Coverage is an exhausted
   lever at current adoption (audit: 4 stars / 1 issue after 41 skills). Put
   the effort into visibility (marketplace, a published before/after audit
   demo) and the badge→verifiable-audit idea (link the "Built with" badge to a
   committed audit report + commit SHA). *(audit STRAT-MED-1)*

## Unexplored ideas

- **Comparative benchmark vs. a named competing skill library.** Every eval to
  date is library-vs-*nothing* (an unguided model), so the public claim is
  honestly limited to that; we make **no** "better than library X" claim. To
  earn one, run `run-completeness.py`/`run-clean.py` with a competitor's content
  pasted as a third arm and report the delta. Deferred until there's a reason to
  make the comparison (user weighed it 2026-07-12 and chose the honest
  vs-unguided framing for now).
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
