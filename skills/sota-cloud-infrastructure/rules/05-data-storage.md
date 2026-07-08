# 05 — Data & Storage Architecture

Scope: object storage design, block/file/object selection, backup architecture,
encryption and KMS key strategy. Database engine selection, schema, replication
internals: see sota-databases. This file covers where data lives, how it's protected
at rest, and how it survives deletion — malicious or accidental.

## 1. Object storage design

- **Bucket-per-purpose, not bucket-as-filesystem.** One bucket = one data class +
  one access pattern + one lifecycle + one policy. Mixing public assets, internal
  exports, and PII in one bucket under prefix conventions means the loosest policy
  wins. Bucket names are global/guessable — never security-relevant.
- **Public access blocked, belt and suspenders.** Provider defaults now help (S3
  Block Public Access on + ACLs disabled for all new buckets since April 2023; GCP
  public access prevention; Azure blob public access disable) — but defaults protect
  only new resources. Enforce at account/org level (S3 BPA account setting guarded
  by SCP; GCP org policy `storage.publicAccessPrevention`; Azure Policy), and audit
  legacy buckets explicitly. Genuinely public content goes behind a CDN with origin
  access control (rules/03 §9), not a public bucket.
- **ACLs disabled everywhere** (S3 Object Ownership = bucket owner enforced).
  Policy-only access control; ACL grants found on legacy buckets are migration debt.
- **Versioning on** for any bucket whose objects you'd miss (protects against
  overwrite/delete), paired with lifecycle rules expiring noncurrent versions —
  versioning without expiry is an unbounded bill.
- **Lifecycle policy on every bucket, by design not retrofit:** transition to
  infrequent-access/archive tiers on access-pattern evidence (storage class
  analysis / intelligent tiering for unknown patterns), expire what has a retention
  end, always abort incomplete multipart uploads (silent cost leak), expire stale
  delete markers.

```hcl
# GOOD: baseline private bucket (AWS flavor; mirror on GCS/Azure)
resource "aws_s3_bucket_public_access_block" "b" {
  bucket                  = aws_s3_bucket.b.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
resource "aws_s3_bucket_versioning" "b" {
  bucket = aws_s3_bucket.b.id
  versioning_configuration { status = "Enabled" }
}
resource "aws_s3_bucket_lifecycle_configuration" "b" {
  bucket = aws_s3_bucket.b.id
  rule {
    id     = "baseline"
    status = "Enabled"
    abort_incomplete_multipart_upload { days_after_initiation = 7 }
    noncurrent_version_expiration { noncurrent_days = 90 }
  }
}
```

- Bucket policies: require TLS (`aws:SecureTransport`), pin org
  (`aws:PrincipalOrgID`) on shared buckets, restrict to VPC endpoints
  (`aws:SourceVpce`) for internal data planes. The TLS and org-perimeter
  conditions are better enforced org-wide once via an RCP (rules/01 §3); keep
  bucket policies for the bucket-specific conditions. Access logging on sensitive
  buckets to the central log account.
- Cross-account writes (log delivery, partner drops): bucket-owner-enforced
  ownership + explicit service principals with source-account/org conditions —
  never `Principal:"*"` with a prefix "restriction".

## 2. Block vs file vs object

| Use | Pick | Notes |
|---|---|---|
| Boot volumes, databases on VMs, low-latency random IO | **Block** (EBS / PD / Managed Disks) | Single-instance attach (mostly); size + IOPS/throughput are separate dials — provision from measurements; snapshots ≠ backup until copied out (see §3) |
| Shared POSIX across instances/pods, lift-and-shift NFS | **File** (EFS / Filestore / Azure Files) | Pay premium for shared semantics; check throughput mode pricing; don't use as a default because "it mounts everywhere" |
| Everything else — artifacts, media, exports, data lake, backups, static sites | **Object** | Default choice; design per §1 |

- Choosing file storage to share state between app replicas is usually an
  architecture smell — externalize state to object storage or a database.
- Block storage hygiene: delete-on-termination set deliberately, snapshots
  lifecycle-managed, unattached volumes reaped (cost finding, rules/06), encryption
  by default at the account/org setting.

## 3. Backup architecture: survive the account, not just the disk

Design backups against four failure classes: hardware/AZ loss, bad deploy/data bug,
accidental deletion, and **malicious actor with prod credentials** (ransomware). Most
backup setups handle the first two only.

- **3-2-1 translated to cloud: primary + same-region backup + cross-account (and
  cross-region per DR tier, rules/07) copy.** Replication is not backup —
  replication faithfully copies the corruption and the deletes. Versioning is not
  backup either (a principal with delete rights removes versions).
- **Cross-account is the ransomware control:** backup vault in a dedicated backup
  account (AWS Backup cross-account vault copy; GCS bucket in a backup project with
  distinct IAM; Azure Backup vault in isolated subscription) that prod admin
  credentials cannot reach.
- **Immutability where supported:** S3 Object Lock (compliance mode for regulated
  retention, governance otherwise), AWS Backup vault lock, GCS retention policy +
  bucket lock, Azure immutable blob storage / vault immutability. An admin-deletable
  backup fails the threat model.
- Coverage by data-tier policy, not per-team improvisation: every stateful resource
  is tagged with a backup tier; org-wide backup plans select by tag; an untagged
  stateful resource is a finding.
- **Restore is the product; backups are a means.** Tested restores (at least
  quarterly for tier-1 data) with measured restore time vs RTO; an unrestored backup
  is Schrödinger's backup. Verify backup of the *whole* unit of recovery (DB +
  config + KMS access), not just one piece.
- Retention matches policy/regulation explicitly — both minimum (compliance) and
  maximum (privacy/GDPR deletion duties). Infinite retention is a liability, not
  diligence.

## 4. Encryption defaults & KMS key strategy

Encryption-at-rest with provider-managed keys is table stakes (mostly default-on).
The real design decisions are about **key control and blast radius**:

- **Three key tiers — pick deliberately per data class:**
  1. **Provider-managed keys** (SSE-S3-style / Google default / Microsoft-managed):
     fine for low-sensitivity data; zero ops; no access separation — anyone with
     data-read IAM reads plaintext.
  2. **Customer-managed keys, CMK** (KMS / Cloud KMS / Key Vault): the default for
     confidential/regulated data. You get: key policy as a *second, independent*
     authorization layer, per-key CloudTrail/audit usage logs, rotation control,
     and a kill switch (disable key = data unreadable everywhere, including in
     stolen snapshots).
  3. **Hold-your-own/external key stores** (XKS, Cloud EKM, HYOK): only under
     explicit regulatory mandate — you inherit an availability dependency on your
     key store; treat as exceptional.
- **Key segmentation = blast radius:** key per environment per data domain (e.g.,
  `prod/payments-data`), not one org-wide key. One key for everything means one key
  grant reads everything and key compromise is total.
- **Separate key admins from data readers.** Key policy: security/platform team
  administers (no Decrypt); workload roles get Encrypt/Decrypt via grants; nobody
  holds both `kms:PutKeyPolicy`-class admin and broad decrypt. This is the control
  that makes stolen-snapshot exfiltration fail: copying an encrypted snapshot
  cross-account requires key access, not just data access.

```json
// BAD: one statement, everyone in the account, full key control + use
{ "Effect": "Allow",
  "Principal": { "AWS": "arn:aws:iam::111122223333:root" },
  "Action": "kms:*", "Resource": "*" }

// GOOD: admin and use split into distinct principals
{ "Sid": "KeyAdmins",
  "Effect": "Allow",
  "Principal": { "AWS": "arn:aws:iam::111122223333:role/platform-kms-admin" },
  "Action": ["kms:Put*", "kms:Update*", "kms:Enable*", "kms:Disable*",
              "kms:TagResource", "kms:ScheduleKeyDeletion", "kms:CancelKeyDeletion"],
  "Resource": "*" },
{ "Sid": "DataUsers",
  "Effect": "Allow",
  "Principal": { "AWS": "arn:aws:iam::111122223333:role/payments-api-runtime" },
  "Action": ["kms:Encrypt", "kms:Decrypt", "kms:GenerateDataKey*"],
  "Resource": "*" }
```
- Enable **automatic key rotation** where supported (yearly rotation of backing key
  material); deletion only via scheduled deletion windows (and alarms on
  `ScheduleKeyDeletion` — it's a destruction primitive).
- KMS calls cost per-request at volume: use S3 Bucket Keys / data-key caching
  (envelope encryption) for high-request-rate paths instead of dropping to
  provider-managed keys for cost reasons.
- Secrets (API keys, passwords) do not live in object storage at all — see
  sota-secrets-management. Field-level/application-layer encryption for the most
  sensitive fields: see sota-code-security.

## 5. Data placement hygiene

- Residency: data-class tags (rules/01) + region restrictions (org guardrails) keep
  regulated data in approved regions; cross-region replication of regulated data is
  a compliance decision, not a convenience default.
- Minimize copies: every export/"temp" bucket/analytics dump is an unguarded replica.
  Data flows into the lake/warehouse through governed pipelines, with the same
  data-class controls as the source.
- Snapshot/AMI sharing: shared-to-public snapshots are a recurring breach class —
  audit for any snapshot/image shared outside the org; block publicly shared
  snapshots via org guardrail where available.

## Audit checklist

- [ ] Account/org-level public-access prevention enforced (not just per-bucket);
      zero public buckets/containers outside an approved, documented list.
- [ ] ACLs disabled (bucket-owner-enforced) on all buckets; legacy ACL grants gone.
- [ ] Every bucket has: versioning decision, lifecycle rules (incl. multipart
      abort + noncurrent expiry), TLS-required policy; sensitive buckets have
      access logging and endpoint/org conditions.
- [ ] No `Principal:"*"` in bucket/queue/key resource policies without strong
      conditions.
- [ ] Stateful resources carry backup-tier tags; org backup plans select by tag;
      sample-verify an actual recovery point exists for each tier-1 system.
- [ ] Backups copied cross-account; immutability/vault-lock on tier-1; verify prod
      admin role genuinely cannot delete backup copies.
- [ ] Restore tested within the last quarter for tier-1 (ask for the record and
      the measured time); retention matches stated policy, both min and max.
- [ ] Unattached volumes, orphaned snapshots, stale AMIs reaped or scheduled;
      no snapshots/images shared public or to unknown accounts.
- [ ] Default encryption on for block storage and DBs account-wide; CMKs used for
      confidential/regulated data classes.
- [ ] Key-per-domain segmentation (no single god key); key admins ≠ data readers in
      key policies; rotation on; ScheduleKeyDeletion alarmed.
- [ ] Regulated data regions match residency policy; exports/temp copies of
      sensitive data inventoried and governed.
