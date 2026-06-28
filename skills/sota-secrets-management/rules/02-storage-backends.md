# 02 — Storage Backends

Scope: choosing and operating the place a secret lives — Vault/OpenBao, cloud secret managers,
SOPS+age for GitOps, Kubernetes secret delivery (sealed-secrets, external-secrets, CSI), env
vars vs file mounts, and in-memory handling. Read this when deciding *where* a secret goes.

## 1. Decision table

| Situation | Backend |
|---|---|
| Single-cloud app (AWS/GCP/Azure) | That cloud's secret manager + IAM; lowest operational cost, native audit |
| Multi-cloud / on-prem / dynamic creds / PKI / transit encryption needed | Vault or OpenBao |
| Kubernetes consuming secrets from any of the above | External Secrets Operator or Secrets Store CSI driver pulling from the backend |
| GitOps repo must carry secret material (no reachable store at deploy time) | SOPS+age (preferred) or sealed-secrets |
| Local development | Per-dev `.env` (untracked) with fake/dev-scoped values, or `vault`/cloud CLI with dev profile; never shared prod values |
| Raw encryption keys for app data | Never stored directly — KMS envelope encryption (rules/05 §7) |

Rules that override the table:

- **Never build a custom secret store** (encrypted DB column with a key in config, "our own
  crypto service," secrets in Redis/Consul KV without encryption + ACLs). Custom stores fail at
  audit logging, rotation, and access control — the parts that matter.
- **Terraform/Pulumi state contains plaintext secrets** regardless of backend. State must live
  in an encrypted, access-controlled backend (S3+SSE+restricted IAM, Terraform Cloud) and never
  in VCS. Prefer ephemeral resources / `write-only` arguments (Terraform ≥1.11) so secret values
  never enter state at all.

## 2. Vault / OpenBao

OpenBao is the open-source fork (post Vault-BSL), now a Linux Foundation project with an
active 2.x release train; operationally interchangeable below. Choose
Vault/OpenBao when you need any of: **dynamic secrets** (DB creds, cloud creds minted on
demand), **PKI** (internal CA with short-lived certs), **transit** (encryption-as-a-service so
apps never hold keys), or a single store spanning clouds/on-prem.

Non-negotiables:

- **Auth via platform identity, not tokens:** Kubernetes auth (projected SA tokens with
  audience), AWS/GCP/Azure auth methods, OIDC/JWT for CI, AppRole only as a last resort and then
  with response-wrapped SecretIDs and short TTLs. A long-lived Vault token in an env var
  defeats the point — High finding.
- **Policies are deny-by-default, path-scoped, one per consumer.** A policy granting
  `path "secret/*" { capabilities = ["read"] }` is a Medium finding.
- **Prefer dynamic engines over KV.** A KV entry holding a static DB password is the fallback;
  the `database/` engine issuing 1h creds per pod is the target (rules/05 §1).
- **Short token/lease TTLs** (≤1h default, renewable) so a stolen token expires; audit devices
  enabled and shipped off-box; auto-unseal via cloud KMS, recovery keys Shamir-split among ≥3
  officers and never stored together.
- **Treat the vault itself as a tier-0 asset** (same bar as the IdP, identity-access rules/02):
  run it **HA** (Raft ≥3 nodes / clustered) so one node loss isn't an outage; take **encrypted
  Raft/storage snapshots on a schedule, ship them off-box, and DR-restore-drill** them — an
  unrecoverable secrets store is a total outage *and* the place every dynamic credential dies;
  define a **break-glass** path (sealed root token / extra recovery-key quorum, stored offline)
  for when auth backends or the network are down, and **log + alert on every use** of it.

```hcl
# BAD — god policy bound to a token pasted into CI variables
path "secret/*" { capabilities = ["read", "list"] }

# GOOD — per-service, per-env policy bound to Kubernetes auth role
path "secret/data/prod/payments/*" { capabilities = ["read"] }
# role binding: namespace=prod, serviceaccount=payments, token_ttl=1h
```

## 3. Cloud secret managers

**AWS Secrets Manager** (rotation Lambdas, RDS-integrated rotation, cross-account access via
resource policies; use SSM Parameter Store `SecureString` for cheap non-rotating config-grade
secrets). **GCP Secret Manager** (versions + IAM conditions, CMEK optional). **Azure Key Vault**
(secrets/keys/certs in one service; use RBAC mode, not legacy access policies).

Rules:

- **IAM is the perimeter.** Grant `GetSecretValue`-equivalent per secret ARN/name per principal.
  `secretsmanager:*` on `*`, or project-wide `secretmanager.secretAccessor`, is a Medium finding
  (High in prod). Separate read (apps) from write/rotate (rotation function, admins).
- **Reference by name + stage/version label** (`AWSCURRENT`/`latest`) so rotation needs no
  deploy; pin exact versions only for break-glass rollback.
- **Use native rotation** where it exists (Secrets Manager rotation functions for RDS/Redshift/
  DocumentDB); otherwise schedule rotation via your own function and the dual-secret pattern.
- **Enable and route audit logs** (CloudTrail data events, GCP Data Access logs, Key Vault
  diagnostics) — reads must be attributable. Alert on `GetSecretValue` from unexpected
  principals or regions.
- **Replicate via the service** (multi-region replication) rather than copying values into a
  second region's store by hand.

## 4. SOPS + age (GitOps)

Use when the deployment model is "git is the source of truth" and a runtime secret store isn't
reachable at render time (Flux/Argo without ESO, edge clusters, bootstrap configs).

- **Encrypt with age recipients or cloud KMS keys; commit only the encrypted file.** With KMS
  recipients you get IAM-controlled decryption + audit logs — prefer KMS recipients for prod,
  age keys for personal/dev.
- **`creation_rules` in `.sops.yaml` per environment**, different keys per env, so a dev key
  cannot decrypt prod files. `encrypted_regex: '^(data|stringData)$'` for k8s manifests keeps
  diffs reviewable while ciphering values.
- The **age private key is the new crown jewel**: it lives in the secret manager or KMS, never
  in the repo, never shared in chat. Losing control of it = every encrypted file in history is
  plaintext; rotate recipients with `sops updatekeys` and re-encrypt, then rotate the *secrets
  themselves* (history still holds old ciphertexts decryptable by the leaked key).
- Flux has native SOPS support; Argo CD needs a plugin — confirm decryption happens in the
  controller, not in a CI step that writes plaintext manifests to an artifact (High finding).

```yaml
# .sops.yaml — GOOD: per-env keys, value-only encryption
creation_rules:
  - path_regex: k8s/prod/.*\.yaml
    encrypted_regex: ^(data|stringData)$
    kms: arn:aws:kms:eu-central-1:123456789012:key/prod-sops
  - path_regex: k8s/dev/.*\.yaml
    encrypted_regex: ^(data|stringData)$
    age: age1devteamkeyq...
```

## 5. Kubernetes secret delivery

Kubernetes `Secret` objects are base64-encoded, **not encrypted**, in etcd by default. Baseline
hardening regardless of delivery mechanism: enable etcd encryption at rest with a KMS provider,
RBAC-restrict `get`/`list`/`watch` on secrets (no wildcard cluster roles), and never commit a
`Secret` manifest with real `data:`/`stringData:` to git (Critical if real values).

Delivery options, in order of preference:

1. **External Secrets Operator (ESO):** syncs from Vault/AWS/GCP/Azure into k8s Secrets via
   `ExternalSecret` CRs. Source of truth stays in the real store; rotation propagates via
   `refreshInterval`. The committed CR contains only *references* — safe for GitOps.
2. **Secrets Store CSI driver:** mounts secrets as files directly from the backend, optionally
   without creating a k8s Secret at all (strongest: nothing in etcd). Use when apps can read
   files and you want zero etcd footprint.
3. **Vault Agent / Vault Secrets Operator:** sidecar/operator renders secrets to a shared
   memory volume with template support and lease renewal — best for dynamic creds.
4. **sealed-secrets:** asymmetric-encrypted `SealedSecret` CRs committed to git; controller
   decrypts in-cluster. Simple, but the controller key becomes critical state (back it up,
   rotate it), secrets are cluster/namespace-bound, and rotation means re-sealing commits.
   Prefer ESO when a real backend exists; prefer SOPS when you want backend-free GitOps with
   easier key handling.

```yaml
# ExternalSecret — GOOD: git holds only a reference; rotation flows automatically
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata: { name: payments-db, namespace: prod }
spec:
  refreshInterval: 5m
  secretStoreRef: { name: aws-prod, kind: ClusterSecretStore }
  target: { name: payments-db, creationPolicy: Owner }
  data:
    - secretKey: password
      remoteRef: { key: prod/payments/db, property: password }
```

Comparison when choosing among the GitOps-capable options:

| | ESO | CSI driver | sealed-secrets | SOPS |
|---|---|---|---|---|
| Source of truth | External store | External store | Git (encrypted) | Git (encrypted) |
| Lands in etcd | Yes (as Secret) | Optional/no | Yes | Yes (after decrypt) |
| Rotation effort | Automatic (refresh) | Automatic (remount) | Re-seal + commit | Re-encrypt + commit |
| Needs reachable backend at runtime | Yes | Yes | No | No (decrypt at apply) |
| Critical key to protect | Backend creds (workload identity) | Same | Controller keypair | age/KMS key |

Consumption: **mount as files (`volumeMounts` from Secret/CSI), not env vars**, when the app
permits — see §6. Set `defaultMode: 0400` on secret volumes. Remember mounted Secrets update
in-place (~1m propagation) but `subPath` mounts do **not** update — avoid `subPath` for
secrets you intend to rotate without restarts.

## 6. Env vars vs file mounts

Env vars are *acceptable* but file mounts are *better*. Know why, and apply the table:

| Property | Env var | File mount (tmpfs) |
|---|---|---|
| Visible to child processes | Yes — entire environment is inherited | No, unless fd/path passed |
| Leaks via crash dumps / `/proc/<pid>/environ` / debug endpoints (`phpinfo`, Spring `/env`) | Commonly | Rarely |
| Appears in `docker inspect`, ECS/k8s pod spec describes | Yes | No (only the mount path) |
| Rotatable without restart | No (env is fixed at exec) | Yes — re-read or inotify-watch the file |
| Captured by error trackers that snapshot env (Sentry default off, but common in homegrown handlers) | Yes | No |

Rules:

- Env vars are acceptable for: 12-factor apps on platforms where mounts are impractical
  (most PaaS), short-lived processes, dev. Mitigate: don't pass env to children
  (`env -i`, explicit allowlists), scrub env in error handlers, never log full env.
- Env vars are **not** acceptable when: the platform offers file mounts (Kubernetes, ECS with
  Secrets Manager file support, systemd `LoadCredential=`), the secret must rotate without
  restarts, or the process spawns untrusted/third-party children.
- **Never** put secrets in: Dockerfile `ENV`/`ARG` (baked into image layers/metadata — Critical
  in pushed images; use BuildKit `--mount=type=secret` for build-time needs),
  docker-compose literals committed to git, systemd unit `Environment=` lines (world-readable
  via `systemctl show`; use `LoadCredential=`), or process command lines (rules/03 §3).
- File-mounted secrets: tmpfs-backed (k8s Secret volumes already are), mode `0400`, owned by the
  app user, path conventional (`/run/secrets/<name>` — Docker/compose secrets land there too).

```dockerfile
# BAD — secret baked into a layer forever; `docker history` shows it
ARG NPM_TOKEN
RUN echo "//registry.npmjs.org/:_authToken=${NPM_TOKEN}" > ~/.npmrc && npm ci

# GOOD — BuildKit secret mount: exists only during this RUN, in no layer
RUN --mount=type=secret,id=npmrc,target=/root/.npmrc npm ci
# build: docker build --secret id=npmrc,src=$HOME/.npmrc .
```

```ini
# systemd — BAD: world-readable via `systemctl show -p Environment myapp`
[Service]
Environment=DB_PASSWORD=s3cr3t
# GOOD: LoadCredential mounts root-owned source to a private, service-only path
[Service]
LoadCredential=db_password:/etc/credstore/myapp.db_password
# app reads $CREDENTIALS_DIRECTORY/db_password; SetCredentialEncrypted= for TPM-sealed values
```

**Docker Compose / Swarm:** use top-level `secrets:` (file- or external-backed) mounted at
`/run/secrets/`, never `environment:` literals; for local dev, `env_file: .env` with an
untracked `.env` is acceptable (rules/05 §8).

```yaml
# BAD — secret in pod spec env, visible in `kubectl describe`, frozen until restart
env:
  - name: DB_PASSWORD
    value: "s3cr3t..."          # literal: Critical if committed
# GOOD
volumeMounts:
  - { name: db-creds, mountPath: /run/secrets/db, readOnly: true }
volumes:
  - name: db-creds
    secret: { secretName: payments-db, defaultMode: 0400 }
```

## 7. In-memory handling

Threats at app level: crash dumps and core files, swap, heap-dumping debug endpoints, error
trackers serializing objects, language-runtime introspection. Proportionate measures:

- **Hold secrets in the narrowest scope for the shortest time.** Fetch → use → drop the
  reference. Don't stash secrets on long-lived global config objects that every error handler
  serializes.
- **Wrap in a redacting type** whose `__repr__`/`toString`/`Debug`/JSON-serialization yields
  `[REDACTED]` (Pydantic `SecretStr`, Rust `secrecy::SecretBox`, your own 20-line wrapper).
  This converts whole classes of log/trace leaks into non-events. (Examples: rules/03 §2.)
- **Zeroization** (overwriting buffers after use) is best-effort in GC languages — strings are
  immutable and copied; use `byte[]`/`bytearray` and wipe where the runtime allows (JVM
  `Arrays.fill`, .NET `CryptographicOperations.ZeroMemory`). In Rust/C use `zeroize`/
  `explicit_bzero`. Worth doing for long-lived master keys; don't pretend it's airtight.
- **Swap/core**: at app level, prefer platform controls — encrypted swap or none (standard on
  k8s nodes), `ulimit -c 0` / `RLIMIT_CORE=0` and `prctl(PR_SET_DUMPABLE, 0)` for processes
  holding master keys; `mlock` only for small, genuinely critical buffers (libsodium
  `sodium_mlock`). Don't `mlock` the whole heap.
- **Disable heap-dump/debug endpoints in prod** (JMX heap dump, `/debug/pprof/heap` exposed
  publicly, py-spy on prod boxes by default). These are remote secret extraction tools.

## Audit checklist

- [ ] Backend matches the decision table; no custom/homegrown secret stores; no secrets in
      Consul/Redis/plain DB columns.
- [ ] Terraform/Pulumi state not in VCS; state backend encrypted and access-controlled;
      write-only/ephemeral used for new secret-bearing resources.
- [ ] Vault/OpenBao: platform-identity auth (no static tokens), deny-by-default path-scoped
      policies, short TTLs, audit devices on, KMS auto-unseal, dynamic engines preferred to KV.
- [ ] Cloud secret managers: per-secret per-principal IAM (no wildcard access), native or
      scheduled rotation, audit/data-access logs enabled and alerted.
- [ ] SOPS: per-env keys in `.sops.yaml`, encrypted_regex for k8s, age/KMS private keys never in
      repo; decryption happens in controller, not CI artifacts.
- [ ] Kubernetes: etcd encryption at rest, secrets RBAC tightened, no real `Secret` manifests in
      git; ESO/CSI/Vault-agent used; secret volumes `0400`, read-only, and no `subPath` mounts
      on rotating secrets.
- [ ] No secrets in Dockerfile ENV/ARG, image layers, compose files, systemd `Environment=`, or
      pod-spec literals; build-time secrets via BuildKit secret mounts.
- [ ] File mounts preferred over env vars where the platform supports them; env-var usage has
      child-process and error-handler scrubbing mitigations.
- [ ] Secrets wrapped in redacting types; debug/heap-dump endpoints disabled in prod; core
      dumps disabled for key-holding processes; long-lived keys zeroized where the runtime
      permits.
