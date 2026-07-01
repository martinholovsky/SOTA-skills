# 05 — Static/Dynamic Analysis & Non-Bypassable Gates

Scope: the automated checks between "code written" and "code merged/shipped", and — at
least as important — the mechanics that prevent those checks from being skipped, muted, or
quietly turned green. A scanner you can bypass selects for people who bypass it.

## 5.1 SAST: Semgrep + CodeQL

Two complementary layers; mature setups run both:

- **Semgrep** — fast, diff-aware, rules-as-readable-code. Run on every PR with
  `p/default`/`p/ci` plus language packs and **your own rules** (the highest-value Semgrep
  rules encode *your* invariants: "never call raw SQL outside the repo layer", "all
  handlers use authz decorator", "no `subprocess` with `shell=True`"). PR runs scan the
  diff; full scans run on schedule (new rules apply to old code).
- **CodeQL** — deep interprocedural taint tracking; catches what pattern-matching can't
  (source→sink across files). Heavier: default-branch + PR for the languages it supports;
  use `security-extended` query suite; budget for triage of the first full run.

```yaml
# PR gate — diff-aware semgrep, blocking
- run: semgrep ci --config p/ci --config .semgrep/   # exits non-zero on findings
  env:
    SEMGREP_BASELINE_REF: ${{ github.event.pull_request.base.sha }}
```

Suppression discipline (applies to every tool in this file):
- Inline suppressions (`# nosemgrep`, `lgtm[...]`, `#nosec`) require a reason on the same
  line: `# nosemgrep: rule-id -- input is enum-validated above`. Bare suppressions fail
  the build (semgrep `--disable-nosem` audits; a grep-based CI check works everywhere).
- Audit the suppression inventory quarterly: count, age, clustering (one file with 30
  `#nosec` is a finding in itself).
- New-code-only baselining is acceptable to get started (don't block on legacy debt), but
  the baseline must shrink: track it, never add to it.

```yaml
# CodeQL — default branch + PRs, extended queries, per-language matrix
on:
  push: { branches: [main] }
  pull_request: { branches: [main] }
  schedule: [{ cron: "31 4 * * 1" }]      # weekly full pass picks up new queries
permissions: { contents: read, security-events: write }
jobs:
  analyze:
    strategy: { matrix: { language: [go, javascript-typescript] } }
    steps:
      - uses: actions/checkout@<sha>
      - uses: github/codeql-action/init@<sha>
        with: { languages: "${{ matrix.language }}", queries: security-extended }
      - uses: github/codeql-action/analyze@<sha>
```

Tool selection note: SARIF upload + code-scanning alerts give one triage surface for
Semgrep, CodeQL, and IaC scanners — use it rather than three dashboards, and make "no new
code-scanning alerts" the required check where the platform supports it.

## 5.2 Secret scanning

Layered — each layer catches what the previous missed:

1. **Pre-commit** (gitleaks/ggshield hook): cheapest fix, before the secret ever hits a
   ref. Advisory (developers can skip hooks) — never your only layer.
2. **Push protection** (GitHub secret scanning push protection / pre-receive): blocks the
   push server-side. Turn it ON org-wide; bypasses require a reason and generate an
   auditable event — review those events.
3. **CI scan on full history** for new repos/audits (`gitleaks git`), diff scan per PR.
4. **Provider-side detection** (GitHub partner program auto-revokes some token types) —
   nice backstop, not a plan.

**A committed secret is a rotation event, not a deletion event.** `git filter-repo` after
the fact cleans the repo, not the forks/clones/caches. Process: revoke/rotate first, then
clean history, then verify the old credential is dead. Any finding response that ends at
"removed the file" is incomplete (keep it High until rotation is confirmed). The full
leak-response runbook and scanner configuration live in sota-secrets-management rules/04;
this section owns the pipeline gate layering.

Tuning: enable entropy + provider-pattern rules; maintain an allowlist for test fixtures
with fake-but-realistic secrets (and mark them clearly, e.g. `TEST_ONLY_` prefixes) so the
tool stays quiet enough to be believed.

```toml
# .gitleaks.toml — allowlist with surgical scope, never directory-wide wildcards
[allowlist]
  paths = ['''tests/fixtures/fake_credentials\.json''']   # exact files
  regexes = ['''TEST_ONLY_[A-Za-z0-9]+''']
# BAD: paths = ['''tests/.*'''] — tests are where real creds get pasted "temporarily"
```

Rotation runbook per credential type (who rotates, blast radius, dependent systems)
should pre-exist the incident — write it when you wire the scanner, not at 2am. The
scanner finding a secret is the *start* of the response; verify revocation by attempting
use of the old credential.

## 5.3 IaC scanning

- Tools: **checkov** or **trivy misconfig** (tfsec is folded into trivy) for Terraform/
  CloudFormation/k8s manifests/Dockerfiles; run on PR (changed paths) as a required check.
- Scan the **plan**, not just HCL, where possible (`terraform show -json plan.out |
  checkov -f -`): catches values resolved from variables/modules that static HCL scanning
  misses.
- Policy exceptions inline with justification and ID:
  `#checkov:skip=CKV_AWS_20:Public website bucket, approved SEC-1234` — same suppression
  discipline as §5.1 (no bare skips, periodic inventory).
- High-signal defaults to never except away: public S3/storage ACLs, 0.0.0.0/0 ingress on
  admin ports, unencrypted state/storage/DB, IAM `*:*`, disabled logging.
- Custom policies for org invariants (allowed regions, mandatory tags, blessed module
  registry only) — Rego (OPA/conftest) or checkov Python/YAML custom checks; keep them in
  a versioned policy repo with tests (rules/07 §7.2).

```yaml
# IaC gate: plan-aware checkov on Terraform changes (with no-op fallback — §5.6)
jobs:
  iac-scan:
    if: ${{ github.event_name == 'pull_request' }}
    steps:
      - uses: actions/checkout@<sha>
      - run: terraform init -backend=false && terraform plan -out=plan.bin && terraform show -json plan.bin > plan.json
      - run: checkov -f plan.json --repo-root-for-plan-enrichment . --soft-fail-on LOW
        # soft-fail ONLY on LOW; HIGH/CRITICAL and custom org policies hard-fail
```

(When the plan needs real credentials, this runs under the read-only plan role of
rules/06 §6.2 and never on fork PRs — rules/01 §1.4.)

## 5.4 DAST basics

DAST finds what static analysis can't see (auth misconfig, header gaps, real injection
through the full stack), but it's slow — keep it out of the PR path:

- **ZAP baseline scan** (passive, minutes) against ephemeral/staging deploys per merge —
  safe to run anywhere; gates on new alerts vs baseline file.
- **Authenticated active scans** scheduled (nightly/weekly) against staging with seeded
  data — never against prod without explicit scoping, and never against shared staging
  during others' test windows.
- API-aware scanning beats blind crawling: feed the OpenAPI spec (ZAP/StackHawk import) so
  coverage is your actual surface, not what a crawler stumbled into.
- Triage pipeline same as everything else: findings → tickets with owners, baseline file
  reviewed in PRs (a growing ignored-alerts baseline is the DAST version of mute culture).

Severity calibration for DAST findings: treat them as *leads*, not verdicts — confirm
exploitability before filing High/Critical (DAST false-positive rates make unconfirmed
findings a credibility tax on the whole program). Conversely, a missing-auth finding on
an internal admin route confirmed by one manual request is real regardless of scanner
confidence scores.

## 5.5 License compliance

- Enforce at the dependency-review gate (rules/03 §3.2 `deny-licenses`) and verify against
  the SBOM (rules/03 §3.5) for the full transitive picture — manifest-level checks miss
  transitive copyleft.
- Policy is a legal decision encoded as config: typical denylist for proprietary shipping:
  AGPL/SSPL always-review, GPL for statically-linked/distributed code, unknown/missing
  license = blocked until identified (unknown is not "fine", it's "no license = all rights
  reserved").
- Watch for **license changes on upgrade** (relicensing events: Mongo→SSPL, HashiCorp→BUSL,
  Redis) — the diff-aware gate catches these only if it checks licenses on version
  *changes*, not just new packages.

## 5.6 Gates that don't get bypassed

The mechanics that make everything above real:

- **Required status checks, by exact job name**, in branch protection/rulesets. A check
  that isn't required is a suggestion. Gotchas:
  - A *skipped* job satisfies "required" on GitHub if path-filtered — when using
    `paths:`/conditional jobs, required gates need a fallback (a no-op job with the same
    name on the excluded paths, or no path filter on gates).
  - Renaming a job silently un-requires it (the protection references the old name) —
    review ruleset config when workflows change; alert on required-check list drift.
- **No `continue-on-error: true`, `|| true`, `set +e`, or `exit 0` tails on gate steps.**
  Audit grep across workflows; every hit on a security/test job is a finding (Medium-High).
  Same for tools invoked with their own "don't fail" flags (`--exit-code 0`, `--soft-fail`,
  `npm audit || true`).
- **Rulesets apply to admins**; bypass lists are empty or break-glass-only with audit
  (rules/07 §7.5). `[skip ci]` must not be honored on protected branches' required gates
  (merge queue or push-triggered verification covers post-merge).
- **Merge queue** for busy repos: re-runs required checks on the actual merge result —
  closes the "green on stale base, broken on main" hole and the approve-then-push race
  (pairs with dismiss-stale-approvals, rules/01 §1.7).
- Gate jobs must not be modifiable by the change they gate, where the threat model demands
  it: reusable workflows from a protected repo (rules/01 §1.8) — otherwise a PR can edit
  the workflow to neuter the gate that judges the PR. (CODEOWNERS on workflows + required
  review mitigates; required *workflows* / org rulesets solve it properly.)

Audit greps for bypass patterns (run across `.github/workflows/`, CI config, Makefiles):

```
continue-on-error: true        # on gate jobs/steps
|| true     || exit 0     ; true
set +e                         # without a matching set -e re-arm
--soft-fail   --exit-code 0   --no-fail   --exit-zero
npm audit || …    audit-level  none
allow_failure: true            # GitLab equivalent
failFast: false                # fine for matrices; check what consumes the result
if: always()                   # on steps that should be conditional on success
```

Each hit needs a justification or a finding. Also diff the branch-protection/ruleset
required-checks list against the actual workflow job names — orphaned required checks
(job renamed/deleted) either block everything (visible, gets fixed) or, with
"required check expected but not run" semantics misconfigured, silently stop gating.

## 5.7 Test discipline — no flaky-mute culture

Flaky tests are a security topic: a suite people retry-until-green will also be retried
through a real regression, and "tests are red anyway" normalizes overriding gates.

- **Quarantine, don't delete or blind-retry**: a flaky test moves to a quarantine
  set (still runs, doesn't block) **with a tracking issue, an owner, and a deadline**;
  quarantine size is a tracked metric with a hard cap. Quarantine without deadline =
  deletion with extra steps.
- Retries: at most one automatic retry, *recorded* (flake-detection reporting), never
  silent. `retry: 3` sprinkled in CI config to make red go away is mute culture (flag it).
- A test that is muted/`@skip`ped without a linked issue is a finding (Low-Medium,
  pattern-dependent). Greps: `@pytest.mark.skip`, `it.skip`, `xit(`, `t.Skip(`,
  `@Disabled` — sample them, check for issue links and age.
- New-flake policy: a test that flakes on main within N days of introduction reverts or
  fixes-forward immediately — flake debt compounds.
- Keep the blocking suite fast (<10–15 min PR path) by tiering: fast suite gates the PR;
  slow/integration suites gate the merge queue or deploy, and **their** failures block
  promotion (rules/06 §6.6), not get waved through.

## 5.8 Putting it together — the PR gate stack

Reference layout (each its own required check, all diff-aware, all fail-closed):

```
PR opened ──► lint+unit (fast)            [required]
          ──► semgrep diff scan            [required]
          ──► dependency review + license  [required]
          ──► secret scan (diff)           [required]
          ──► IaC scan (changed paths*)    [required, *with no-op fallback]
          ──► build + image scan           [required when Dockerfile/src changes]
merge queue ─► full test suite on merge result
post-merge ─► CodeQL full, DAST baseline on preview, scheduled deep scans
```

Latency budget matters: every gate over ~10 minutes generates organizational pressure to
remove it. Diff-aware modes, caching, and tiering are how gates survive.

## Audit checklist

- [ ] SAST: diff-aware Semgrep (org rules included) required on PRs; CodeQL (or equivalent deep SAST) on default branch; full scans scheduled
- [ ] All inline suppressions (`nosemgrep`/`#nosec`/checkov skips) carry justifications; suppression inventory reviewed; baseline only shrinks
- [ ] Secret scanning: push protection org-wide, PR diff scan, history scanned at onboarding; committed secrets trigger rotation, not just removal; bypass events reviewed
- [ ] IaC scanning on PRs (plan-aware where possible) with the high-signal defaults non-exceptable; custom org policies versioned + tested
- [ ] DAST baseline on staging per merge, authenticated scans scheduled, OpenAPI-fed; baseline file changes reviewed
- [ ] License gate covers transitive deps (SBOM-based) and license *changes* on upgrades; unknown licenses block
- [ ] All gates are required checks by exact name; no `continue-on-error`/`|| true`/soft-fail on gate steps; path-filtered required checks have no-op fallbacks; rulesets apply to admins; merge queue (or equivalent) re-validates merge results
- [ ] Gate workflows protected from modification by the gated change (CODEOWNERS/required workflows)
- [ ] Flaky tests quarantined with owner+issue+deadline and a capped quarantine size; retries recorded; skipped tests linked to issues; PR gate latency within budget
