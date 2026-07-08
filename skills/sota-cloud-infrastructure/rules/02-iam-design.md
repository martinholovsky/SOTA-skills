# 02 — IAM Design

Scope: human access, workload identity, OIDC federation, permission boundaries,
least-privilege iteration, cross-account patterns, break-glass, and the IAM findings
that dominate real audits. Secret storage/rotation mechanics: see
sota-secrets-management. CI pipeline identity specifics: see sota-devsecops.

## 1. Humans: federated SSO, short-lived sessions, zero static keys

- **All human access goes through the identity provider** (AWS IAM Identity Center,
  Google Cloud Identity / Workspace, Microsoft Entra ID) with MFA — phishing-resistant
  (FIDO2/passkeys) for admin roles. Humans assume short-lived roles; sessions ≤ 8h for
  standard, ≤ 1h for privileged.
- **Zero IAM users for humans.** No console passwords, no access keys. AWS IAM users
  exist only for the rare service that cannot do roles (legacy SMTP, some third-party
  integrations) — each one inventoried, key-rotated, and condition-restricted
  (source IP, single action).
- Access is granted to **groups in the IdP**, mapped to permission sets / role
  bindings. Direct user-to-role grants are an audit finding: they survive offboarding
  reviews invisibly.
- Tier the permission sets: `read-only` (default for everyone), `developer`
  (env-scoped write), `admin` (per-account, time-bound). Prefer just-in-time
  elevation (PIM in Entra, temporary elevated access tooling elsewhere) over standing
  admin: standing admin count per prod account should be ~0–2.
- Offboarding = disable in IdP only. If that doesn't kill all access (because a local
  user or shared credential exists), that's the finding.

## 2. Workloads: platform-issued identity, never embedded keys

Every workload gets identity from the platform it runs on; credentials are
short-lived and auto-rotated by the provider:

| Runtime | Mechanism |
|---|---|
| AWS EC2/ECS/Lambda | Instance profile / task role / execution role |
| EKS | EKS Pod Identity or IRSA — role per service account, never node-role inheritance for app permissions |
| GCP compute/run/functions | Attached service account (dedicated per workload, NOT default compute SA) |
| GKE | Workload Identity Federation for GKE |
| Azure compute/AKS | Managed identity (user-assigned per workload) / workload identity for AKS |
| External (CI, SaaS, other cloud) | OIDC/workload identity federation — exchange the external token for short-lived cloud creds |

- **A static cloud access key or service-account JSON key in an env var, file, or
  secret manager is a finding** (High), not a pattern. The fix is federation, not
  better hiding. Enforce with org policy: deny SA key creation (GCP), deny
  `iam:CreateAccessKey` (AWS SCP) except documented exceptions.
- One identity per workload. Shared "app-runner" roles across services destroy both
  least privilege and audit attribution.
- OIDC federation trust must pin **issuer AND subject**: a trust policy that accepts
  any repo/branch from a CI provider is public assumability with extra steps.

```json
// BAD: any GitHub repo in the org (or worse, any at all) can assume this role
"Condition": { "StringLike": { "token.actions.githubusercontent.com:sub": "*" } }

// GOOD: pinned to repo and environment
"Condition": {
  "StringEquals": {
    "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
    "token.actions.githubusercontent.com:sub": "repo:my-org/infra-payments:environment:prod"
  }
}
```

## 3. Policy authoring rules

- **No wildcards in Action or Resource for write/admin permissions.** `s3:Get*` on a
  scoped bucket: acceptable. `s3:*` on `*`: finding. `iam:*`, `sts:AssumeRole` on `*`,
  `kms:*`: always findings outside admin roles.
- Watch **privilege-escalation primitives** as if they were admin: `iam:PassRole`
  (unscoped = become any role a service can wear), `iam:CreatePolicyVersion`,
  `iam:AttachUserPolicy`, `lambda:UpdateFunctionCode` on privileged functions, GCP
  `iam.serviceAccounts.actAs` / `getAccessToken`, Azure role-assignment write. Scope
  `PassRole` to specific role ARNs plus `iam:PassedToService`.
- Use **conditions as containment**: `aws:SourceVpce`/`SourceIp` for data-plane
  access, `aws:ResourceOrgID`/`PrincipalOrgID` to stop confused-deputy and
  cross-org exfiltration, `sts:ExternalId` for third-party assume-role. On AWS,
  enforce the org-perimeter conditions once, centrally, with an RCP (rules/01 §3)
  instead of hand-copying them into every resource policy.
- Resource policies (bucket/key/queue policies) are a second IAM system — audit them
  with the same rigor. A perfect identity policy is irrelevant if the bucket policy
  grants `Principal: "*"`.
- Write policies in IaC with comments stating *why* each statement exists. An
  uncommented broad grant cannot be safely narrowed later.

```json
// BAD: "deploy role" that is actually privilege escalation to any role
{
  "Effect": "Allow",
  "Action": ["iam:PassRole", "lambda:*"],
  "Resource": "*"
}

// GOOD: pass exactly the runtime role, to exactly the service, update exactly our functions
{
  "Effect": "Allow",
  "Action": "iam:PassRole",
  "Resource": "arn:aws:iam::111122223333:role/checkout-api-runtime",
  "Condition": { "StringEquals": { "iam:PassedToService": "lambda.amazonaws.com" } }
},
{
  "Effect": "Allow",
  "Action": ["lambda:UpdateFunctionCode", "lambda:UpdateFunctionConfiguration"],
  "Resource": "arn:aws:lambda:eu-west-1:111122223333:function:checkout-*"
}
```

## 4. Permission boundaries & delegated administration

- When teams self-manage IAM in their accounts, cap them: **permission boundaries**
  (AWS) on every role they create — boundary forbids IAM/org/billing/guardrail
  mutation and touching other teams' resources; deny role creation *without* the
  boundary attached. GCP/Azure: restrict grantable roles via
  `iam.allowedPolicyMemberDomains` + custom-role discipline / Azure
  `roleDefinitionIds` constraints on owners.
- Separate **control-plane admin** from **data access** in role design: the person
  who can change KMS key policy should not be the role that decrypts production data
  (see rules/05 §encryption).

## 5. Least privilege is iterative — wire the loop

Nobody writes least-privilege first try. Ship slightly-scoped, then tighten on
evidence:

1. Start from activity, not imagination: generate policies from access logs
   (IAM Access Analyzer policy generation from CloudTrail; GCP role recommendations
   from Policy Intelligence; Entra access reviews).
2. Run **unused-access detection** continuously (IAM Access Analyzer unused-access
   findings, GCP IAM Recommender, Azure access reviews): unused roles, unused keys,
   unused granted permissions ≥ 90 days → remove, with an owner-notified grace path.
3. Run **external/public-access analysis** continuously (Access Analyzer external
   findings, SCC, Defender CSPM): any resource or role reachable from outside the
   org zone of trust is reviewed or removed.
4. Quarterly access review for privileged grants; automated diff of who-has-admin
   between quarters.

## 6. Cross-account / cross-project access

- Pattern: **hub identity, spoke roles.** Humans and CI authenticate once (IdP /
  identity account), then assume scoped roles in target accounts. No duplicated users
  per account.
- Every cross-account trust policy must pin the exact principal ARN (not account
  root unless deliberate), and for third parties add `sts:ExternalId` (confused
  deputy) — better: require their OIDC federation instead of an account-wide trust.
- Maintain an inventory of all trust relationships pointing outside the org;
  unknown account IDs in trust policies are Critical until identified.
- GCP: prefer service-account impersonation with
  `roles/iam.serviceAccountTokenCreator` over keys; Azure: cross-tenant via Entra
  B2B/Lighthouse with scoped delegations, never shared SP secrets.

## 7. Break-glass

- Two break-glass paths per cloud, tested quarterly:
  1. **Org level:** management-account root (or equivalent) credentials —
     hardware-MFA, credentials split/sealed (e.g., password in one vault, MFA token in
     a safe), any use alarms the security channel.
  2. **Account level:** a pre-provisioned `break-glass-admin` role assumable by a
     tiny named group via a path that does NOT depend on the IdP (IdP outage is a
     primary break-glass scenario).
- Break-glass use requires: alert fires automatically, post-use review within 24h,
  credential rotation after use. A break-glass account that has ever been used for
  routine work is just an admin account with worse logging.

## 8. Common audit findings (what to actually look for)

| Finding | Severity (typical) | Detection |
|---|---|---|
| Role/bucket/topic assumable or readable by `*` / `allUsers` | Critical | Access Analyzer external findings; policy grep for `"Principal":"*"` without conditions |
| OIDC trust with wildcard subject | Critical | Read every federation trust policy |
| Human IAM users with active access keys | High | Credential report; keys > 90d unrotated |
| `Action:*` / `iam:PassRole` on `*` in non-admin roles | High | Policy lint (Access Analyzer policy checks, custom rules) |
| CI using stored long-lived cloud keys instead of OIDC | High | Inspect CI secret stores + key last-used |
| Unused roles/keys/permissions > 90 days | Medium | Unused-access analyzers |
| Direct user grants bypassing groups | Medium | IdP + cloud mapping diff |
| No permission boundary on delegated-admin-created roles | Medium | List roles missing boundary in self-service accounts |
| Standing admin > 2 humans per prod account | Medium | Enumerate admin-equivalent bindings |
| Break-glass untested / undocumented | Medium | Ask for last test record |

## Audit checklist

- [ ] Credential report / key inventory: zero human IAM users with keys or passwords
      (exceptions documented, conditioned, rotated).
- [ ] SSO enforced with MFA; admin roles require phishing-resistant MFA; sessions
      time-bound.
- [ ] Access granted via IdP groups → permission sets; no direct user bindings.
- [ ] Every workload identity is platform-issued or federated; zero static SA
      keys/access keys in apps or CI (check key-creation org policy is enforced).
- [ ] All OIDC federation trusts pin issuer + audience + exact subject.
- [ ] No `Action:*`/`Resource:*` writes outside admin roles; PassRole/actAs scoped;
      escalation primitives enumerated and justified.
- [ ] Resource policies reviewed: no `Principal:"*"` without strong conditions;
      org-ID conditions on shared resources.
- [ ] Cross-account trusts inventoried; every external account ID identified;
      ExternalId or federation for third parties.
- [ ] Permission boundaries (or provider equivalent) on self-service IAM.
- [ ] Unused-access analyzer running; findings older than 90 days are zero or
      ticketed.
- [ ] Break-glass: exists, IdP-independent, alarmed, tested within last quarter.
- [ ] Offboarding test: pick a recent leaver; verify zero residual access.
