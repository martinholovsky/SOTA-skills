# 01 — Secret Lifecycle & Workload Identity

Scope: generation, distribution, storage policy, rotation, revocation, expiry; replacing static
secrets with workload identity (OIDC federation, SPIFFE/SPIRE, cloud IAM roles, GitHub Actions
OIDC). Read this before creating any new credential.

## 1. Generation

**Use a CSPRNG. Always.** `secrets` (Python), `crypto.randomBytes` (Node), `crypto/rand` (Go),
`SecureRandom` (Java/Ruby), `openssl rand`. Never `random`, `Math.random()`, `rand()`,
timestamps, PIDs, or hashes of any of those — they are predictable and recoverable.

**Entropy floor: 256 bits (32 random bytes) for opaque tokens** (API keys, session secrets,
webhook signing secrets, HMAC keys). 128 bits is the absolute minimum for short-lived,
rate-limited tokens; default to 256 because the cost is zero. Encode with base64url or hex —
length on the wire is irrelevant; entropy before encoding is what counts.

**UUIDv4 is not a secret.** It has 122 bits of randomness but many generators are not
cryptographically seeded, and UUIDs leak into logs/URLs by convention. Use a real random token.

```python
# BAD — predictable, low entropy, leaks intent into the value
api_key = hashlib.md5(f"{user_id}{time.time()}".encode()).hexdigest()
reset_token = str(uuid.uuid4())

# GOOD — 256-bit CSPRNG token, with an identifiable prefix for scanners
api_key = "myapp_sk_" + secrets.token_urlsafe(32)
reset_token = secrets.token_urlsafe(32)
```

**Prefix your own tokens** (`myapp_sk_`, `myapp_pat_`): prefixes enable secret scanners
(gitleaks, GitHub secret scanning partner program) to detect leaks of *your* credentials, and
make audit greps trivial. The prefix carries zero entropy cost.

**Asymmetric keys:** Ed25519 by default for signing (SSH, JWT EdDSA, artifact signing);
ECDSA P-256 where Ed25519 unsupported; RSA only for legacy interop and then ≥3072 bits.
Generate keys *where they will live* (HSM, KMS, TPM, target host) so the private key never
transits — `aws kms create-key`, `ssh-keygen` on the client, CSR-based TLS issuance. A private
key that was ever in a chat, email, or ticket is compromised.

**Human passwords are not machine secrets.** Machine-to-machine credentials are never
human-memorable strings. If a human must create a shared secret (rare), generate it with a
password manager at ≥24 random characters.

## 2. Distribution

**Secrets move through exactly one channel: the secret store.** Producer writes to
Vault/cloud secret manager; consumer reads from it with its own identity. Never distribute via
Slack, email, tickets, wikis, READMEs, or "I'll paste it in the PR comment." Any secret that
traversed such a channel is leaked — rotate it.

**Bootstrap (the "secret zero" problem):** the credential that lets a workload reach the secret
store must itself not be a static secret. Solve it with platform identity:

- Cloud VMs/containers: instance metadata → IAM role (no credential at all).
- Kubernetes: projected service account tokens → Vault Kubernetes auth / cloud workload identity.
- Bare metal / multi-cloud: SPIFFE/SPIRE node attestation (TPM, cloud metadata, join token).
- CI: OIDC token from the CI provider (see §5).

If a design document contains the phrase "we'll put the bootstrap token in an env var," send it
back.

**Human access** to production secrets goes through the secret store's UI/CLI with SSO + MFA,
is break-glass only, and is audit-logged. Day-to-day operation should never require a human to
*see* a secret value.

## 3. Rotation, revocation, expiry

**Every secret has, at creation time:** an owner (team), a maximum lifetime or rotation
interval, a documented zero-downtime rotation procedure, and a revocation path. Record these in
the secret's metadata/tags. A secret missing any of the four is an audit finding (Medium).

**Rotation intervals (defaults, tighten for higher-value targets):**

| Credential | Max lifetime / rotation |
|---|---|
| Cloud STS / OIDC-issued tokens | 15 min – 1 h (automatic) |
| Vault dynamic DB creds | TTL ≤ 24 h (automatic) |
| Service-to-SaaS API keys | 90 days |
| Webhook/HMAC signing secrets | 180 days, dual-secret overlap |
| JWT signing keys | 90 days via `kid` rotation (see rules/05) |
| TLS leaf certs | ≤ 90 days (ACME automation) |
| Long-lived static keys (last resort) | 90 days, with a ticket explaining why they exist |

**Zero-downtime rotation = overlap, not swap.** The universal pattern:

1. Issue new secret (version N+1) alongside old (N) — both valid.
2. Roll out consumers to N+1 (redeploy or let TTL-based cache refresh pick it up).
3. Verify no traffic uses N (audit logs, metrics).
4. Revoke N.

Verifiers (webhook receivers, JWT validators) must accept *both* during the window; issuers
switch to N+1 immediately. If your system can only hold one value at a time, fix that before
setting a rotation schedule — otherwise rotation means an outage and will therefore never happen.

**Revocation must be possible in minutes, not days.** Test it: for each credential class, know
the exact command/console action that kills it (`aws iam update-access-key --status Inactive`,
Vault lease revoke, CRL/OCSP or short-lived certs, API key delete endpoint). If revocation
requires "contact the vendor," shorten the lifetime to compensate.

**Expiry beats rotation.** A credential that dies on its own at T+1h needs no rotation calendar,
no cleanup job, and limits blast radius automatically. This is the core argument for §4–5.

```yaml
# BAD — static key created once, lives forever, rotation is a wiki page nobody reads
aws_access_key_id: AKIA****************   # created 2022, owner unknown

# GOOD — secret metadata makes lifecycle enforceable
metadata:
  owner: payments-team
  rotation_interval: 90d
  rotation_runbook: runbooks/rotate-stripe-key.md
  expires: 2026-09-01
```

## 4. Short-lived beats long-lived — the workload identity ladder

A static secret is a liability with a half-life; an identity-issued credential is a claim that
expires. Whenever both ends of a connection can speak to a common trust authority, **eliminate
the static secret entirely**:

| Connection | Replace static secret with |
|---|---|
| App on AWS → AWS service | IAM role (instance profile / IRSA / EKS Pod Identity / ECS task role) |
| App on GCP → GCP service | Attached service account (metadata server), Workload Identity on GKE |
| App on Azure → Azure service | Managed Identity (system- or user-assigned) |
| CI job → cloud account | CI OIDC federation (GitHub Actions, GitLab, CircleCI, Buildkite → AWS/GCP/Azure) |
| CI job → package registry | Trusted publishing: per-job CI OIDC exchanged for a short-lived publish grant (npm, PyPI, RubyGems, crates.io) — no stored publish token |
| Cross-cloud (GCP app → AWS) | Workload identity federation: exchange GCP-issued OIDC token for AWS STS creds |
| Pod → Vault/OpenBao | Kubernetes auth (projected SA token) or JWT/OIDC auth |
| Service → service (mTLS) | SPIFFE/SPIRE-issued X.509 SVIDs, auto-rotated |
| App → database | Vault dynamic creds, or cloud IAM DB auth (RDS IAM, Cloud SQL IAM, Azure AD auth) |

**Detection rule (AUDIT):** a long-lived cloud access key (`AKIA…`, GCP service account JSON
key file, Azure client secret) used *from inside that same cloud or from a major CI provider*
is a Medium finding minimum — the federation path exists and isn't used. The same key in VCS is
Critical.

**SPIFFE/SPIRE** for platform-agnostic identity: SPIRE attests nodes (cloud metadata, TPM,
join token) and workloads (k8s SA, unix attestor, binary hash), then issues short-lived X.509
or JWT SVIDs with SPIFFE IDs (`spiffe://trust-domain/ns/prod/sa/payments`). Use it when you
need mTLS service identity across heterogeneous infrastructure without a cloud IAM common
denominator. SVIDs rotate automatically (default ~1h) — workloads consume them via the Workload
API socket, never from disk-managed certs.

## 5. GitHub Actions OIDC (and CI federation generally)

**Never store cloud keys in CI secret variables when the provider supports OIDC.** GitHub
Actions, GitLab CI, CircleCI, Bitbucket, and Buildkite all issue per-job OIDC tokens; AWS, GCP,
and Azure all accept them. The same applies to package publishing: npm, PyPI, RubyGems, and
crates.io accept per-job CI OIDC ("trusted publishing") — a stored long-lived publish token in
CI where the registry supports trusted publishing is a Medium finding (see rules/05 §8).

```yaml
# BAD — long-lived key stored in repo/org secrets; any workflow (or exfiltrating
# dependency in any workflow) can use it forever
- uses: aws-actions/configure-aws-credentials@v6
  with:
    aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
    aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}

# GOOD — per-job 1h credential, no stored secret, scoped by trust policy
permissions:
  id-token: write
  contents: read
steps:
  - uses: aws-actions/configure-aws-credentials@v6  # v6+: needs node24-capable runners
    with:
      role-to-assume: arn:aws:iam::123456789012:role/deploy-myapp
      aws-region: eu-central-1
```

**Lock the trust policy down** — this is where OIDC deployments go wrong:

- Condition on `aud` (`sts.amazonaws.com`) **and** `sub`. Pin `sub` to repo + ref or
  environment: `repo:my-org/my-app:ref:refs/heads/main` or
  `repo:my-org/my-app:environment:prod`. A trust policy matching `repo:my-org/*:*` lets any
  repo in the org assume the deploy role — High finding.
- One role per repo/purpose, least-privilege policy (deploy role ≠ admin).
- Use GitHub *environments* with required reviewers for prod-deploy roles so the OIDC `sub`
  claim can't be minted from an unreviewed branch.

The same pattern applies to GCP Workload Identity Federation (attribute conditions on
`assertion.repository`) and Azure federated credentials (subject identifier pinning):

```hcl
# GCP WIF — GOOD: provider restricted to one repo, mapped to a dedicated SA
resource "google_iam_workload_identity_pool_provider" "github" {
  attribute_condition = "assertion.repository == 'my-org/my-app'"
  attribute_mapping   = { "google.subject" = "assertion.sub" }
  oidc { issuer_uri = "https://token.actions.githubusercontent.com" }
}
# BAD: no attribute_condition -> any GitHub repo on earth can attempt the exchange,
# gated only by IAM bindings you must get perfect everywhere
```

**Residual CI secrets** (the SaaS API keys OIDC can't replace): store in the CI provider's
secret store scoped to the narrowest level (environment > repo > org), mark masked/protected,
and remember CI secrets are exposed to *every step* of jobs that receive them — including
third-party actions/orbs. Pin third-party actions by commit SHA, not tag; a retagged action is
a secret-exfiltration vector with your token in hand.

## 6. Dynamic secrets in practice

The pattern that operationalizes "short-lived beats long-lived" for things OIDC doesn't cover:

```hcl
# Vault database engine — each app instance gets its own 1h DB user
resource "vault_database_secret_backend_role" "payments" {
  backend             = "database"
  name                = "payments-prod"
  db_name             = "payments-pg"
  creation_statements = [
    "CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}';",
    "GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA app TO \"{{name}}\";"
  ]
  default_ttl = 3600
  max_ttl     = 14400
}
```

Operational rules for dynamic/leased credentials:

- **Renew before expiry, re-fetch on revocation.** Use the agent/SDK renewal loop (Vault Agent,
  AWS SDK credential providers do this natively); hand-rolled consumers must renew at ~2/3 of
  TTL and treat renewal failure as "fetch a new lease," not "crash."
- **Size `max_ttl` to your deploy cadence** — if leases outlive deployments, every deploy
  naturally rotates creds and `max_ttl` is a backstop, not a disruption.
- **Revocation drills:** revoke a live lease in staging quarterly and confirm the app recovers
  via re-fetch (rules/03 §4 retry-on-auth-failure). A dynamic-secrets setup that's never been
  revoked in anger usually breaks the first real time.
- **Watch lease floods:** a crash-looping pod minting a new DB user per restart can exhaust
  connection/user limits — alert on lease-creation rate per role.

## 7. Storage policy summary

(Backends in detail: rules/02.) Lifecycle rules that apply regardless of backend:

- **One source of truth per secret.** Copies in two stores will diverge and one will rot
  unrotated. Replicate via the store's own mechanism (e.g., external-secrets sync), never by
  hand.
- **Version every secret** and keep N-1 readable during rotation windows only.
- **Tag with owner + rotation metadata** (§3) so expiring-secret reports are automatable.
- **Audit log every read** in production; alert on reads from unexpected principals.
- **Maintain a secret inventory.** You cannot rotate what you don't know exists. The secret
  store's listing *is* the inventory only if everything lives there — which is the point.
  Quarterly: export all secrets with age + owner + last-accessed; flag anything unowned,
  unread in 90 days (delete candidates — unused secrets are pure liability), or older than its
  rotation interval (overdue).
- **Decommissioning:** when a service dies, its secrets are revoked the same week — not left
  "in case we roll back." Tie secret deletion into service-retirement checklists.

```text
# Quarterly inventory review — the three queries that matter
1. Secrets with no owner tag            -> assign or delete
2. Secrets not read in 90d (audit logs) -> delete (after a deprecation notice)
3. Secrets older than rotation_interval -> rotate now, fix the automation that missed them
```

## Audit checklist

- [ ] All token/key generation uses a CSPRNG with ≥256-bit entropy; no UUIDs, timestamps, or
      hashes-of-predictables used as secrets.
- [ ] Internally minted tokens carry a scannable prefix.
- [ ] Asymmetric keys are Ed25519/P-256 (RSA ≥3072 only for interop) and generated where they
      live; no private key ever moved through chat/email/tickets.
- [ ] No secret distributed outside the secret store; bootstrap uses platform identity, not a
      static "secret zero."
- [ ] Every secret has owner, rotation interval, zero-downtime rotation runbook, and a tested
      revocation path; intervals meet the table in §3.
- [ ] Rotation uses overlap (dual-secret / versioned), not in-place swap.
- [ ] No long-lived cloud keys where IAM roles / managed identity / workload identity
      federation are available (in-cloud workloads, CI jobs, cross-cloud calls).
- [ ] CI→cloud auth uses OIDC with `aud` + pinned `sub` trust conditions; one least-privilege
      role per repo/purpose; prod roles gated by reviewed environments.
- [ ] Package publishing from CI uses trusted publishing (registry OIDC) where the registry
      supports it; no long-lived publish tokens stored in CI.
- [ ] Database access uses dynamic creds or IAM DB auth where the engine supports it; leased
      credentials renew at ~2/3 TTL and recover from revocation; revocation drills performed.
- [ ] Third-party CI actions/orbs pinned by SHA in secret-bearing jobs; CI secrets scoped to
      environment level, masked, and absent from fork-triggered workflows.
- [ ] Secret reads are audit-logged in production with alerting on anomalous principals.
- [ ] A secret inventory exists (store listing + owner/age/last-read), reviewed quarterly;
      unused and orphaned secrets deleted; retired services' secrets revoked promptly.
