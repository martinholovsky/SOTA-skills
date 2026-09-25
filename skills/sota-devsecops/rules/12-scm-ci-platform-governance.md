# 12 — SCM and CI Platform Governance (org-level settings)

Scope: the settings that live on the **organisation**, not in any repository file: who may
fork or publish a repo, who must use MFA, and which outside contributors may run workflows.
No workflow lint sees them, because no file contains them. `rules/01` hardens what the
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

## Audit checklist

- [ ] **Forking and visibility locked to owners (§12.1), High:** `gh api orgs/<org> --jq '{members_can_fork_private_repositories, members_can_change_repo_visibility}'` prints `false` for both with an owner token (`null` = not visible, re-run as owner); recent `repo.access` events in the org audit log reviewed
- [ ] **Org-wide 2FA enforced (§12.2), High:** `gh api orgs/<org> --jq .two_factor_requirement_enabled` prints `true` with an owner token; secure-methods-only on; the CI/CD platform's own accounts enforce the same; 2FA-disable events alerted
- [ ] **Fork-PR approval covers all external contributors (§12.3), Medium:** `gh api repos/<owner>/<repo>/actions/permissions/fork-pr-contributor-approval --jq '.approval_policy == "all_external_contributors"'` (and the `/orgs/<org>/…` form) prints `true`
- [ ] **No self-hosted runner on a public repo (§12.3), High:** for each repo where `gh api repos/<owner>/<repo> --jq .visibility` is `public`, `gh api repos/<owner>/<repo>/actions/runners --jq .total_count` is `0` and no org runner group grants it access; if not, every external run has a recorded maintainer approval
