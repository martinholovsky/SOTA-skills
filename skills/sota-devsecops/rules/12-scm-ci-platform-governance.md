# 12 — SCM and CI Platform Governance (org-level settings)

Scope: the settings that live on the **organisation**, not in any repository file: who may
fork or publish a repo, who must use MFA, which outside contributors may run workflows,
which workflows may reach privileged runners, who must approve what, who administers the
platform, and whether any of it is kept as code. No workflow lint sees them, because no file contains them. `rules/01` hardens what the
pipeline does; this file covers the platform the pipeline runs on. Examples use GitHub's
REST API; other forges have equivalent settings under different names, so look up your own.

**Read with an owner token.** The organisation fields below come back `null` when the
caller is not an org owner. Verified 2026-09-25: `gh api orgs/github` returned `null` for
all three fields from a non-member token. A `null` means **not visible**, not "off", so an
audit that reads it as a pass has checked nothing.

## 12.1 Repository visibility and forking

A private repository becomes public through two routes: a fork that escapes the org's
controls, and a visibility flip. Close both at org level.

- Disable forking of private and internal repositories
  (`members_can_fork_private_repositories: false`). Where a team needs forks, allow them
  per repository, with a written reason.
- Only org owners may change repository visibility
  (`members_can_change_repo_visibility: false`). A flip to public exposes the entire
  history, including every secret ever committed and later "removed" (`sota-secrets-management`).
- Review visibility changes in the org audit log (event `repo.access`, "the visibility of
  a repository changed") and alert on any flip to public (rules/07 §7.3.1).
  (OWASP: CI/CD Security cheat sheet)

## 12.2 Org-wide MFA on SCM and CI platforms

MFA on privileged accounts only is not enough: any member with write access can push
a workflow, and a workflow can reach your secrets (rules/01 §1.8).

- Require two-factor authentication for **every** member, outside collaborator and billing
  manager of the SCM org, and of the CI/CD platform if it has its own accounts. Enforce it
  as an **org setting**, not as a request: GitHub's toggle removes outside collaborators
  who have no 2FA, and blocks members until they enrol.
- Also require **secure methods only**. In GitHub's definition these are passkeys,
  security keys, authenticator apps and GitHub Mobile, and SMS is excluded. An
  authenticator-app code can still be phished, so for phishing resistance require
  passkeys/security keys at the IdP behind SSO (`sota-identity-access`).
- Alert on the audit events `org.disable_two_factor_requirement` and
  `org.clear_disallowed_two_factor_methods`.
  (OWASP: CI/CD Security cheat sheet; Software Supply Chain Security cheat sheet)

## 12.3 Fork-PR approval policy, and a self-hosted runner on a public repo

GitHub lets you choose which outside contributors need a maintainer's approval before their
fork PR runs workflows. It offers three levels: `first_time_contributors_new_to_github`,
`first_time_contributors` and `all_external_contributors`. The first-time levels have a
documented hole: once any commit or PR from the user has been merged, even a typo fix,
their workflows run without approval.

- Set **`all_external_contributors`** at the organisation
  (`/orgs/{org}/actions/permissions/fork-pr-contributor-approval`) and per repository.
  Approval costs a maintainer one click per external PR, and only fork PRs from
  non-members need it.
- **A self-hosted runner attached to a public repository is banned** (rules/01 §1.6). If
  one exists anyway, the fallback is manual: a maintainer reads and approves **every**
  external run before it executes. That still leaves code execution on your
  infrastructure one careless approval away, so rate the pairing **High** whatever the
  approval setting.
  (OWASP: GitHub Actions Security cheat sheet)

## 12.4 Runner groups separate privilege tiers

A self-hosted runner that holds deploy credentials, carries a cloud role, or can reach
internal networks is as valuable as the credentials themselves. On GitHub, any workflow in
a repository that can see a runner can target it by label, so **labels route jobs but do not
restrict them**. The boundary is the runner group.

- **Put high-privilege runners in their own group** with `visibility: selected` and an
  explicit repository list, `allows_public_repositories: false` (the default), and, where
  your plan offers it, `restricted_to_workflows: true` with `selected_workflows` naming full
  workflow paths pinned to a ref, for example
  `org/deploy/.github/workflows/release.yml@refs/heads/main`. Only jobs defined directly in
  a selected workflow can then use the group. (Fields from the REST runner-group reference,
  read 2026-09-25; plan availability of the workflow restriction: needs verification.)
- **Low-trust work goes to a separate pool**: PR validation, fork PRs and repositories
  without branch protection run on GitHub-hosted or ephemeral runners with no network reach
  and no attached cloud role (`rules/01` §1.6).
- **Watch the default group.** A runner registered without a group choice is assigned to
  it (GitHub's runner-group docs), so check that group's visibility: a privileged runner
  that lands there by accident is reachable from every repository the group admits.
- Other forges use different names for the same control (runner tags and protected
  runners, agent pools); the audit question is the same: which repositories and which
  workflow files can schedule a job on this machine?
  (OWASP: GitHub Actions Security cheat sheet)

## 12.5 Review policy as an enforced setting: independent, qualified, risk-tiered approvers

A review requirement that the author can satisfy alone, or that anyone with write access can
satisfy for crypto code, is a formality.

- **The approver is not the author, and not the last pusher.** On GitHub, "pull request
  authors cannot approve their own pull requests", but a collaborator can push a commit onto someone else's approved
  PR. The ruleset `pull_request` parameter `require_last_push_approval: true` requires
  "the most recent reviewable push" to be approved by someone other than the person who
  pushed it. Combine it with dismissing stale approvals (`rules/01` §1.7).
- **Scale reviewers with module risk.** Mark the high-risk paths (cryptography,
  authentication and session handling, authorization, payment, smart contracts, the CI and
  release files of `rules/01` §1.8) and route them to a security owner or architect through
  CODEOWNERS with required code-owner review, or the ruleset `required_reviewers` parameter
  (reviewers with file patterns). Require two approvals there if one is the default.
- **Qualified reviewers**: the teams named for those paths have had secure-coding training
  for the languages involved, and the membership of those teams is itself reviewed.
- **Review for intent, not only for mistakes.** The reviewer of a high-risk change also asks
  whether it is **deliberately** malicious: obfuscated or encoded strings, new network
  destinations, weakened tests or assertions, dependency or lockfile changes the PR does
  not explain, and changes to who may approve. A trusted maintainer's change is where the
  xz-utils backdoor came from (`rules/03` §3.4).
- **Record the outcome.** Platform approvals are recorded; a review held outside the
  platform (a call, a design review) gets a written note on the PR.
- **Restricted repositories keep their reviewers inside.** Do not grant repository access
  to someone only so that they can approve; choose reviewers who already have access.
  (OWASP: Code Review Guide v2; Software Supply Chain Security cheat sheet; SCSVS S2.1.B1)

## 12.6 Least-privilege CI/CD administration

- **Running a pipeline is not administering the platform.** Keep the right to run or edit
  pipelines apart from org and project administration, and do administration through
  configuration as code in a separate, tightly owned repository (§12.7) with required
  review, so that an admin change is a reviewed PR and not a settings click.
- **Few admins, counted.** Keep org owners and repository admins to a written maximum:
  `gh api 'orgs/<org>/members?role=admin' --paginate --jq '.[].login'` lists owners, **run
  with an owner token**: from a non-member token (2026-09-25) `role=admin` and `role=all`
  returned the same 23 logins for one public org, so the filter proves nothing. Keep an
  inventory of everyone who can **view or change CI secrets and system settings**: owners,
  repository admins, and everyone with write access to a repository whose workflows can read
  a secret (`rules/01` §1.8).
- **Limit who installs plugins, apps and integrations.** On GitHub, org owners install
  GitHub Apps, and so can a repository admin when the app requests no organization
  permissions and not the "repository administration" permission (GitHub's installation
  docs, read 2026-09-25). Repository-admin grants are therefore also app-install grants.
  On a self-hosted CI server, plugin installation stays an admin-only action, and every
  plugin gets the vetting in `rules/15` §15.1.
- **Cap and time-box outside access.** External contributors, contractors and temporary
  maintainers get the lowest role that works and a recorded end date, with removal done by
  a scheduled review rather than by memory.
- **Restrict administrative access by network where the platform supports it.** GitHub's
  org IP allow list is available only to GitHub Enterprise Cloud organizations (per its
  docs); a self-hosted CI UI sits behind a VPN or identity-aware proxy
  (`sota-network-security`).
  (OWASP: CI/CD Security cheat sheet; Secrets Management cheat sheet; SCVS 3.12)

## 12.7 Settings as governed configuration: distrust defaults, keep them as code, scan for drift

- **Every setting that matters lives in version control.** Org and repository settings,
  rulesets and runner groups can be managed as code (for example the Terraform GitHub
  provider's `github_organization_settings`, `github_organization_ruleset`,
  `github_repository_ruleset` and `github_actions_runner_group` resources). CI jobs are
  defined in files in the repository; **no UI-only jobs**. On a Jenkins-class server, jobs
  come from a `Jenkinsfile` or job DSL and the server itself from Configuration as Code.
- **Treat vendor defaults as untrusted until reviewed.** A default was chosen for a first
  run, not for your threat model (default token permissions are the standing example,
  `rules/01` §1.1). Write the reviewed baseline down and make the code match it.
- **Scan for misconfiguration and drift on a schedule.** Legitify scans GitHub and GitLab
  organizations and repositories for risky settings; OpenSSF Scorecard scores individual
  repositories; Allstar enforces a policy set continuously but must now be **self-run** (its
  README: the OpenSSF-hosted GitHub App has been retired). If settings are managed as code,
  a scheduled plan that shows changes is drift (`rules/06` §6.3). Route findings to an
  owner.
  (OWASP: CI/CD Security cheat sheet)

## 12.8 Inventory CI plugins and build tools, and keep the workflow scanners current

- **Keep an automated inventory** of CI-server plugins, build tools and their versions:
  plugin manifests (`plugins.txt`/`plugins.yaml`, which Renovate's `jenkins` manager
  updates), pinned builder images and tool-version files (`rules/04` §4.1). Point the update
  bot and advisory monitoring at those manifests, as you do for application dependencies.
- **Keep workflow SAST current, or its new detections never run.** zizmor adds audits in
  minor releases: its audit reference dates `secrets-outside-env` to v1.23.0 and
  `adhoc-packages` to v1.26.0, so a pin older than those never checks them. Pin the scanner
  (`rules/04` §4.1) and let the update bot move the pin; the same goes for the CodeQL
  action that runs the `actions` queries (`rules/01` §1.9).
  (OWASP: GitHub Actions Security cheat sheet; Software Supply Chain Security cheat sheet)

## Audit checklist

- [ ] **Forking and visibility locked to owners (§12.1), High:** `gh api orgs/<org> --jq '{members_can_fork_private_repositories, members_can_change_repo_visibility}'` prints `false` for both with an owner token (`null` = not visible, re-run as owner); recent `repo.access` events in the org audit log reviewed
- [ ] **Org-wide 2FA enforced (§12.2), High:** `gh api orgs/<org> --jq .two_factor_requirement_enabled` prints `true` with an owner token; secure-methods-only on; the CI/CD platform's own accounts enforce the same; 2FA-disable events alerted
- [ ] **Fork-PR approval covers all external contributors (§12.3), Medium:** `gh api repos/<owner>/<repo>/actions/permissions/fork-pr-contributor-approval --jq '.approval_policy == "all_external_contributors"'` (and the `/orgs/<org>/…` form) prints `true`
- [ ] **No self-hosted runner on a public repo (§12.3), High:** for each repo where `gh api repos/<owner>/<repo> --jq .visibility` is `public`, `gh api repos/<owner>/<repo>/actions/runners --jq .total_count` is `0` and no org runner group grants it access; if not, every external run has a recorded maintainer approval
- [ ] **Privileged runners in restricted groups (§12.4), High:** `gh api orgs/<org>/actions/runner-groups --jq '.runner_groups[] | select(.visibility == "all" or .allows_public_repositories) | .name'` lists only groups whose runners hold no deploy credentials, cloud role or internal network reach; privileged groups use `restricted_to_workflows` where available
- [ ] **Last push approved by someone else; high-risk paths routed (§12.5), High:** `gh api repos/<owner>/<repo>/rules/branches/main --jq '[.[] | select(.type=="pull_request") | .parameters.require_last_push_approval] | any'` prints `true`; CODEOWNERS or `required_reviewers` routes crypto, auth and release paths to a named security owner
- [ ] **Admin rights counted and time-boxed (§12.6), Medium:** `gh api 'orgs/<org>/members?role=admin' --paginate --jq '.[].login' | wc -l` (owner token; a non-member gets every public member back) is within the written maximum; an inventory of who can view or change CI secrets exists; outside collaborators carry recorded end dates; app/plugin installation limited to owners
- [ ] **Settings as code, scanned for drift (§12.7), Medium:** org settings, rulesets and runner groups are defined in a reviewed repository; no CI job exists only in a UI; a scheduled Legitify/Scorecard (or equivalent) scan has an owner
- [ ] **CI plugins and workflow scanners kept current (§12.8), Medium:** `grep -n -E "package-ecosystem:[[:space:]]*[\"']?github-actions" .github/dependabot.yml` (or a Renovate config covering the workflows and any `plugins.txt`) is non-empty, and the pinned zizmor/CodeQL versions are within the update bot's reach
