# Roadmap

Priorities set by the 2026-07-01 audit ([AUDIT-2026-07-01.md](AUDIT-2026-07-01.md)).
Ordered; revisit after each release.

## Now — correctness of what's shipped

1. **Fix the audit's HIGH and MEDIUM findings.** The two HIGHs
   (sota-security-compliance frontmatter invalid under strict YAML;
   `init-gates.sh` language-detection SIGPIPE fail-open) plus the script
   silent no-ops, the denylist-check gaps, and the sota-jvm scoped-values
   correction. *(Landed in the audit-remediation PR, #37.)*
2. **Library lint gate** (extends `check-invariants.sh`): YAML-parse all
   SKILL.md frontmatters, VERSION == plugin.json == latest tag lockstep,
   README count-basis check, shellcheck over `scripts/`. Blocks the whole
   defect class the audit found. *(Partially landed: YAML-validity check and
   shellcheck CI job in #37; version-lockstep and count checks still open.)*

## Next — keep the core promise true

3. **Freshness ledger.** Per-rules-file `last-verified: YYYY-MM` metadata plus
   a scheduled CI job reporting files past their re-verify window. The README
   promises "fast-moving claims are web-verified against primary sources";
   today only ~21 of 220 rules files carry any verification date, so the
   promise is unauditable — and every "2026 baseline" assertion goes silently
   stale in 2027.
4. **Release procedure in-repo** (`RELEASING.md` or a CONTRIBUTING section):
   VERSION + plugin.json + CHANGELOG + tag + GitHub release, plus the
   version-bearing strings in README/CLAUDE.md. Eight releases shipped in the
   first 14 days from a procedure that lives outside the repo; the v1.0.0
   pointer rot in CLAUDE.md was the predictable result.
5. **Structured feedback intake.** `.github/ISSUE_TEMPLATE` with a
   bad-guidance report (file:line + primary source, mirroring SECURITY.md's
   format) and a skill-request template; enable Discussions. A no-telemetry
   project's only adoption signal is structured issues — currently absent.

## Later — coverage decisions (decide, don't drift)

6. **Close or declare the language/domain gaps.** PHP and Ruby have no skill
   (incidental mentions only); Swift exists only at sota-mobile's
   platform/stack level, not as a language-idiom skill; Active
   Directory/Kerberos/ADCS have zero coverage despite identity and detection
   skills whose real-world audits are AD-heavy. Ship `sota-php`, `sota-ruby`,
   a Swift-language rules file, and AD content — or add a README "coverage &
   non-goals" section stating what is deliberately excluded. The mission
   statement overclaims until one of the two happens.

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
