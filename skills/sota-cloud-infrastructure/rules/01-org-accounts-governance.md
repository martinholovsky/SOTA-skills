# 01 — Org, Accounts & Governance

Scope: organization structure, account/project strategy, landing zones, guardrails
(SCPs / org policies / Azure Policy), centralized logging and billing, tagging
standards. This is the layer everything else inherits from — get it wrong and every
downstream control is patchwork.

## 1. Accounts/projects are the unit of isolation

- **Use separate accounts (AWS) / projects (GCP) / subscriptions (Azure) as blast-radius
  boundaries.** IAM mistakes, quota exhaustion, credential theft, and cost overruns are
  contained by the account boundary; they are NOT contained by tags, VPCs, or naming
  conventions inside one account.
- Minimum viable structure, even for small teams:
  - **Management/org root** — billing and org administration only. No workloads, no
    users doing daily work, ever.
  - **Security/audit** — centralized logs, audit trails, security tooling. Write access
    from workload accounts, read access only for security team.
  - **Prod** — one per major system or per team at scale; one shared prod account is
    acceptable only below ~10 engineers.
  - **Non-prod** (dev/staging) — separate from prod, always. Staging in the prod
    account is the most common audit finding that enables lateral movement.
  - **Sandbox** — disposable experimentation with hard budget caps and auto-cleanup.
- Per-environment isolation beats per-application isolation when you must choose: a
  dev compromise must not be able to touch prod data under any IAM misconfiguration.
- Scale pattern: account-per-team-per-environment, vended automatically (Account
  Factory / project factory in Terraform). Manual account creation does not scale past
  ~10 accounts and produces snowflakes.

```hcl
# GOOD: environments as separate accounts under OUs (Terraform sketch)
resource "aws_organizations_organizational_unit" "workloads_prod" {
  name      = "workloads-prod"
  parent_id = aws_organizations_organization.org.roots[0].id
}
resource "aws_organizations_organizational_unit" "workloads_nonprod" {
  name      = "workloads-nonprod"
  parent_id = aws_organizations_organization.org.roots[0].id
}
resource "aws_organizations_organizational_unit" "security" {
  name      = "security"
  parent_id = aws_organizations_organization.org.roots[0].id
}

# BAD: one account, environments by tag
# tags = { Environment = "prod" }   <- this is a label, not a boundary
```

## 2. Organize by OU/folder, attach policy at the container

- Group accounts into OUs (AWS), folders (GCP), management groups (Azure) by **policy
  needs**, not by org chart. "workloads-prod", "workloads-nonprod", "security",
  "sandbox", "suspended" is a better top level than "team-alpha", "team-beta".
- Attach guardrails to OUs/folders so new accounts inherit them on creation. A
  guardrail applied per-account is a guardrail someone will forget.
- Keep a "suspended/quarantine" OU with a deny-all-but-investigation policy for
  compromised or decommissioning accounts.

## 3. Guardrails: preventive controls at the org layer

Guardrails are deny-rules that apply to everyone including account admins. They encode
"things that must never happen" — IAM inside the account encodes "who may do what."

Non-negotiable guardrail set (express as AWS SCPs / GCP org policy constraints / Azure
Policy deny assignments):

1. **Deny leaving the organization** (AWS: `organizations:LeaveOrganization`).
2. **Deny disabling/altering audit logging** (CloudTrail stop/delete/update; GCP audit
   config changes; Azure diagnostic settings deletion) outside the security account.
3. **Deny root user actions** in member accounts (AWS: deny all where
   `aws:PrincipalArn` is root) — combined with org-level root credential management /
   root access removal where available.
4. **Region restriction** — deny resource creation outside approved regions (data
   residency + reduces unwatched attack surface).
5. **Deny public object storage** at org level (S3 BPA account config protected by SCP;
   GCP `storage.publicAccessPrevention` enforced; Azure deny blob public access).
6. **Deny creation of IAM users / access keys** (AWS) except a tagged break-glass path;
   GCP: `iam.disableServiceAccountKeyCreation` enforced org-wide with per-project
   exceptions only via documented process.
7. **Deny unencrypted storage creation** (EBS/RDS/disks without encryption).
8. **Deny default-VPC usage or auto-creation** where the provider supports it (GCP:
   `compute.skipDefaultNetworkCreation`).

```json
// GOOD: SCP fragment — protect the audit trail
{
  "Effect": "Deny",
  "Action": ["cloudtrail:StopLogging", "cloudtrail:DeleteTrail", "cloudtrail:UpdateTrail"],
  "Resource": "*",
  "Condition": { "StringNotEquals": { "aws:PrincipalArn": "arn:aws:iam::SECURITY_ACCT:role/org-audit-admin" } }
}
```

- **AWS: pair SCPs with Resource Control Policies (RCPs).** SCPs cap what
  principals in member accounts may do; RCPs cap what *any* principal — including
  ones outside the org — may do to **resources** in member accounts (S3, STS, KMS,
  SQS, Secrets Manager, DynamoDB, ECR, CloudWatch Logs, and more). Use an RCP for
  the org-wide data perimeter — deny access from principals outside the org,
  require TLS — instead of repeating those conditions in every bucket/key policy
  (rules/02 §3, rules/05 §1). RCPs don't affect the management account or
  service-linked roles.

```json
// GOOD: RCP fragment — org-wide S3 identity perimeter (external principals denied
// even where a bucket policy grants them access)
{
  "Effect": "Deny",
  "Principal": "*",
  "Action": "s3:*",
  "Resource": "*",
  "Condition": {
    "StringNotEqualsIfExists": { "aws:PrincipalOrgID": "o-example" },
    "BoolIfExists": { "aws:PrincipalIsAWSService": "false" }
  }
}
```

- SCPs/RCPs/org policies do not grant anything; test them with org-policy dry-run /
  SCP simulation against real workflows before enforcing, and roll out OU-by-OU.
- Pair preventive guardrails with detective baseline: AWS Config / Security Hub, GCP
  Security Command Center, Azure Defender for Cloud / Policy compliance — deployed
  org-wide from the security account, findings centralized. (Alert routing and
  on-call: see sota-observability.)

## 4. Centralized logging and billing

- **One audit trail, org-wide, to a bucket the producers cannot touch.** AWS: an
  organization CloudTrail delivering to a bucket in the security/log-archive account
  with object lock + deny-delete bucket policy. GCP: org-level log sink to a project
  in the security folder. Azure: diagnostic settings to a central Log Analytics
  workspace / storage in a locked subscription.
- Workload accounts get *write* into the central store and *no* delete/modify. Admins
  of a compromised account must not be able to erase their tracks.
- Centralize: control-plane audit logs (always), DNS query logs, VPC flow logs
  (sampled where volume demands), object-storage access logs for sensitive buckets,
  LB access logs.
- **Consolidated billing under the management account** with cost data exported
  (CUR / BigQuery billing export / Cost Management exports) to a queryable store
  available to FinOps tooling. Per-account billing views delegated to team leads.
  Details: rules/06.

## 5. Tagging/labeling standard — non-negotiable

Untagged resources cannot be attributed, costed, or safely deleted. Enforce, don't
request.

Minimum mandatory tag set (adapt names to house style, keep the semantics):

| Tag | Meaning | Example |
|---|---|---|
| `owner` | Team or service owner (group, not person) | `payments-team` |
| `env` | Environment | `prod` / `staging` / `dev` / `sandbox` |
| `service` | System/application name | `checkout-api` |
| `cost-center` | Billing attribution | `cc-4012` |
| `data-class` | Highest data sensitivity touched | `public` / `internal` / `confidential` / `regulated` |
| `managed-by` | Provisioning source | `terraform:repo-name` / `manual` |

- Enforce at three layers: (1) provider policy — AWS tag policies + SCP requiring tags
  on create for taggable services, GCP/Azure label/tag policy; (2) IaC — `default_tags`
  in the Terraform AWS provider / module-level mandatory variables; (3) detective —
  scheduled report of noncompliant resources with auto-quarantine in sandbox.
- `managed-by: manual` is an explicit exception flag, reviewed monthly, not a default.
- Tag VALUES come from a controlled vocabulary (tag policy / validation in module),
  or you get `Prod`, `prod`, `production`, and `prd` and lose attribution anyway.

```hcl
# GOOD: provider-level default tags — applies to every resource in the config
provider "aws" {
  default_tags {
    tags = {
      owner      = "payments-team"
      env        = "prod"
      service    = "checkout-api"
      managed-by = "terraform:infra-payments"
    }
  }
}
```

## 6. Landing zone: bootstrap once, vend forever

A landing zone is the automated baseline every new account/project receives:

- Org placement (correct OU/folder) and guardrail inheritance.
- Baseline IAM: SSO permission sets mapped, no local users, break-glass role.
- Audit logging wired to central store; security tooling enrolled.
- Network: either a vended VPC pattern (rules/03) or explicit "no network" for
  serverless-only accounts.
- Budget + anomaly alert with an owner (rules/06).
- Mandatory tags applied at the account level.

Use the provider's framework as a starting point (AWS Control Tower / Landing Zone
Accelerator, GCP project factory blueprints, Azure landing zones) but keep the
definition in version-controlled IaC — pipeline and IaC-scanning concerns belong to
sota-devsecops. A landing zone you can't reproduce from code is a liability.

Bootstrap exceptions (the only acceptable console-click steps, documented in a runbook):
org creation, root MFA enrollment, initial SSO/identity-provider connection, billing
contacts.

## 7. Anti-patterns

- **The "one big account" with tag-based separation.** Every IAM policy becomes a
  condition-key puzzle; one wildcard ends the separation.
- **Workloads in the management account.** The management account can alter every
  guardrail; a compromise there is org-wide root.
- **Org chart as OU tree.** Reorgs then force account migrations; policy needs are
  stabler than reporting lines.
- **Guardrails only in dev** ("we'll enable in prod later"). Reverse it: guardrails in
  prod first; dev gets looser quotas, not looser security.
- **Shadow orgs**: a second cloud provider or personal accounts on the corporate card
  with no guardrails. Audit billing data for unknown payer lines.

## Audit checklist

- [ ] Org exists; all accounts/projects/subscriptions are members; none standalone.
- [ ] Management account/root project has no workloads, no daily-use identities.
- [ ] Prod and non-prod are separate accounts/projects (not tags in one).
- [ ] Security/log-archive account exists; org audit trail delivers there; producers
      cannot delete/modify logs (bucket policy / object lock / sink permissions).
- [ ] Root/owner credentials: MFA enforced, no access keys, usage alarmed (any root
      login pages someone).
- [ ] SCPs/org policies enforce, at minimum: no audit-log tampering, no public
      buckets, region restriction, no new IAM users/SA keys, no leaving org.
- [ ] AWS: RCPs enforce the org-wide data perimeter on supported services (deny
      principals outside the org, require TLS) — not left to per-resource policies.
- [ ] Guardrails attached at OU/folder level, inherited by new accounts automatically.
- [ ] Account vending is automated and IaC-defined; pick a recent account and verify
      it matches the baseline.
- [ ] Mandatory tag set defined, enforced on create, and a compliance report exists;
      sample 10 resources across accounts for tag presence and vocabulary compliance.
- [ ] Consolidated billing with cost export to queryable store; per-team visibility.
- [ ] Quarantine/suspended OU (or equivalent) exists with deny-most policy.
- [ ] No unknown accounts: reconcile org account list against billing and ownership
      records; every account has a responsive owner.
