# Roadmap

Priorities set by the **2026-07-10 audit**
([AUDIT-2026-07-10.md](AUDIT-2026-07-10.md)). Ordered; revisit after each
release. The 2026-07-01 cycle is fully executed and kept below as history.

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
   web-search agent recovers most of it). **Completeness +0.30** (0.59→0.89,
   `cases/completeness.jsonl` + `run-completeness.py`, blind opus judge) — the
   **thesis, validated**: from a bare "build X" prompt the base model skips
   tests/rate-limits/logging/transport ~40% of the time; the library embeds
   them, and search can't close this gap. **Live follow-through:** grow the
   completeness + freshness sets; average more samples per arm for tighter CIs.
5. **First 6-month accuracy sweep** comes due ~Jan 2027 (freshness window) —
   run it per the `docs/MAINTENANCE.md` runbook and bump `LAST-VERIFIED`.

## Later — distribution over coverage

6. **Pause net-new skills; invest in distribution.** Coverage is an exhausted
   lever at current adoption (audit: 4 stars / 1 issue after 41 skills). Put
   the effort into visibility (marketplace, a published before/after audit
   demo) and the badge→verifiable-audit idea (link the "Built with" badge to a
   committed audit report + commit SHA). *(audit STRAT-MED-1)*

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
