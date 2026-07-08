# 05 — Credential Types

Scope: type-specific rules for database credentials, API keys, signing keys, TLS private keys,
SSH keys, JWT signing secrets (with `kid` rotation), encryption keys vs KMS envelope
encryption, and `.env` file discipline. Read the matching section before implementing or
auditing a specific credential class. General lifecycle rules (rules/01) still apply.

## 1. Database credentials

Preference order:

1. **IAM database auth** (RDS/Aurora IAM, Cloud SQL IAM, Azure AD for Postgres/SQL): no
   password exists; the driver presents a short-lived token. Use where the engine and driver
   support it.
2. **Vault/OpenBao dynamic creds** (`database/` engine): per-instance users with 1–24h TTL,
   auto-revoked. Each pod gets its own user → perfect attribution, instant revocation.
3. **Static password in a secret manager** with scheduled rotation — the floor, not the goal.

Rules:

- **Zero-downtime static rotation = dual users.** Two DB users (`app_a`, `app_b`) with
  identical grants; rotate the idle one's password, flip the app's secret to it, repeat next
  cycle. Single-user rotation always has a race between password change and config propagation.
  AWS Secrets Manager's "alternating users" rotation strategy implements exactly this.
- **App users are least-privilege** (schema/table grants, no `SUPERUSER`/`GRANT OPTION`/DDL for
  runtime users; migrations run as a separate, more-privileged, more-protected user).
- **Connection strings:** assemble from parts at runtime; never log the assembled DSN
  (rules/03 §2); never commit one with userinfo (`postgres://app:pw@…` in code/compose is
  Critical with real values).
- Require TLS to the DB (`sslmode=verify-full`) — a rotated password helps little if creds
  cross the wire in clear inside a "trusted" network.

```sql
-- Dual-user rotation, cycle N (app currently uses app_b):
ALTER ROLE app_a WITH PASSWORD :'new_pw' VALID UNTIL 'infinity';
-- update secret manager entry "db-user" -> {user: app_a, password: new_pw}
-- wait for consumer cache TTL + verify via pg_stat_activity that app_b sessions drain
-- cycle N+1 rotates app_b; the idle user is always the one being rotated
```

## 2. API keys (third-party SaaS)

Usually irreplaceable by federation — manage the static secret well:

- **Store in the secret manager**, runtime-injected, cached with TTL (rules/03 §4).
- **Scope at the vendor:** Stripe restricted keys per function, Google API key
  IP/referrer/API restrictions, GitHub fine-grained PATs, read-only variants wherever offered.
  One key per consuming service per environment — never share the org-wide key across services
  (rules/03 §7).
- **Test/live separation:** `sk_test_` in non-prod, `sk_live_` only in prod paths; CI uses test
  keys exclusively. A live-mode key in CI variables for "integration tests" is a High finding.
- **Rotation ≤90 days** using the vendor's dual-key/overlap mechanism if present; if the vendor
  supports only one active key, schedule a brief maintenance flip and document it.
- **Webhook signing secrets are API-key-class secrets:** verify signatures with
  constant-time comparison, support two active secrets during rotation, reject stale timestamps
  (replay).
- AUDIT: vendor key prefixes are high-signal greps (`sk_live_`, `xoxb-`, `SG.`, `key-`,
  `AC[a-f0-9]{32}` Twilio). A live vendor key in frontend bundles/mobile apps is Critical —
  client-shipped code is public.

## 3. Signing keys (code/artifact/webhook/general-purpose)

- **Private keys live in KMS/HSM and never leave.** Sign by calling `kms:Sign` / Key Vault
  sign / PKCS#11 — the app holds a *permission*, not a key. Exportable software signing keys
  are a Medium finding when a KMS path exists; a committed one is Critical.
- **Artifact/code signing:** prefer keyless (Sigstore cosign with OIDC identity + Rekor
  transparency log) — no long-lived key exists at all. If long-lived keys are mandated
  (Android keystores, Apple certs), store in HSM-backed services, restrict signing to a locked
  CI lane with audit-logged, reviewed triggers.
- **Separate keys per purpose.** The webhook-HMAC key ≠ the JWT key ≠ the artifact key; reuse
  couples blast radii and blocks independent rotation.
- **Publish verification material, version it** (public keys / certs with IDs), and rotate
  with overlap so old artifacts remain verifiable per your policy.

## 4. TLS private keys

- **Automate issuance: ACME everywhere** (Let's Encrypt/ZeroSSL via cert-manager, Caddy,
  certbot, cloud LB-managed certs). ≤90-day certs make key compromise self-limiting and force
  the automation that prevents 2am expiry outages. A multi-year manually-installed cert is a
  Medium finding (process smell), expired-soon without automation is operationally urgent.
- **Generate the key where it terminates** (CSR flow); never email/chat a `.key` or `.pfx`.
  Wildcard cert keys copied to N servers multiply exposure N-fold — prefer per-host/per-SAN
  certs, or distribute via secret manager with per-host access if a wildcard is unavoidable.
- **Permissions `0400`,** owner = the terminating process's user; key files outside web roots
  and build contexts (a `.pem` inside a Docker build context ends up in the image).
- **Internal mTLS:** run a private CA (Vault PKI engine, cert-manager + internal issuer,
  SPIFFE/SPIRE) issuing ≤24h–90d certs; never hand-manage internal certs or, worse, disable
  verification (`InsecureSkipVerify: true`, `verify=False`, `NODE_TLS_REJECT_UNAUTHORIZED=0`
  in committed code is a High finding — it's adjacent to secrets because it nullifies them).
- Compromise/leak of a key: revoke (CRL/OCSP), reissue on a new key, and rotate anything that
  transited sessions lacking forward secrecy. Committed key + cert pairs in repos are Critical
  even if expired — check the *key* for reuse in newer certs.

## 5. SSH keys

- **Ed25519, per human, per device,** passphrase-protected, ideally hardware-backed
  (`sk-ssh-ed25519` FIDO2 keys, or platform agents like Secretive/TPM). Never share a private
  key between people or copy one to a second machine — generate a new key there.
- **Better: short-lived SSH certificates** (Vault SSH CA, Teleport, Smallstep): users get
  certs valid for hours after SSO+MFA; servers trust the CA, not 400 stale `authorized_keys`
  entries. Eliminates key sprawl and offboarding gaps. At minimum, inventory and expire
  `authorized_keys` entries; remove on offboarding the same day.
- **Machine SSH (CI → server) is a smell:** prefer pull-based deploys (GitOps, image pulls) or
  cloud-native exec (SSM Session Manager — no open port 22, IAM-audited). If unavoidable: a
  dedicated keypair per pipeline, `from=` and `command=` restrictions in `authorized_keys`,
  stored in CI secret store, rotated ≤90d.
- **Deploy keys / repo SSH keys:** read-only unless write is proven necessary; one per
  consumer.
- **Agent hygiene:** `ForwardAgent no` by default (a compromised host can use your agent);
  prefer `ProxyJump`. `IdentitiesOnly yes` to avoid spraying every loaded key.
- AUDIT: `id_rsa`/`id_ed25519` files in repos or images are Critical (even passphrase-protected
  — assume crackable); `~/.ssh` COPY'd into Dockerfiles is a classic (grep Dockerfiles for
  `ssh` and `COPY.*\.ssh`); known leaked pattern: private key in a "dotfiles" repo.

## 6. JWT signing secrets and `kid` rotation

- **Prefer asymmetric (EdDSA/ES256, RS256 for interop) over HS256** whenever any party other
  than the issuer verifies tokens: with HS256 every verifier holds the *signing* secret and can
  mint tokens; with asymmetric, verifiers hold only public keys. HS256 is acceptable only
  issuer-verifies-own-tokens (e.g., session tokens in a monolith) — and then the secret is
  ≥256-bit CSPRNG (rules/01 §1), not a passphrase.
- **Pin the algorithm at verification.** Accept exactly the expected `alg`; never `alg: none`;
  never let an attacker downgrade RS256→HS256 (verifier treating the public key as an HMAC
  secret — the classic confusion attack). Library config: explicit `algorithms=["EdDSA"]`.
- **`kid` rotation (zero-downtime):**
  1. Generate key N+1; add to the published JWKS (`/.well-known/jwks.json`) alongside N.
  2. Switch issuance to N+1 (`kid` header = N+1's id).
  3. Keep N in JWKS until max token TTL elapses (all N-signed tokens expired).
  4. Remove N from JWKS; destroy the private key.
  Verifiers select the key by `kid` and cache JWKS with HTTP cache headers (≤15m TTL) plus
  refresh-on-unknown-`kid` — that last behavior is what makes emergency rotation fast.
- **Emergency rotation** (key leaked): publish N+1, issue with N+1, remove N immediately —
  accepting that live N-signed tokens die. Forced logout beats forged admin tokens. Keep
  token TTLs short (≤15m access tokens) so even routine rotation windows are short.
- AUDIT greps: `eyJhbGciOi` literals in code/tests (inline real JWTs — decode and check for
  prod claims), `JWT_SECRET` with a default value, `algorithms` lists containing both HS and RS
  variants, `verify=False`/`verify_signature: False` options, JWKS endpoints serving a single
  never-rotated key with no `kid`.

```python
# BAD — alg from attacker-controlled header; shared secret in code with fallback
jwt.decode(tok, SECRET or "devsecret", algorithms=[jwt.get_unverified_header(tok)["alg"]])

# GOOD — pinned alg, key chosen by kid from cached JWKS, refresh on unknown kid
hdr = jwt.get_unverified_header(tok)
key = jwks.get(hdr["kid"]) or jwks.refresh_and_get(hdr["kid"])  # handles rotation
claims = jwt.decode(tok, key, algorithms=["EdDSA"], audience="api://payments")
```

## 7. Encryption keys vs KMS envelope encryption

**Never hand-manage raw data-encryption keys** (a hex key in config decrypting DB fields is a
High finding — it combines the worst of secrets and crypto). Use envelope encryption:

- **Pattern:** KMS holds the root key (non-exportable). Per object/record/tenant, generate a
  **data encryption key (DEK)** via `GenerateDataKey`; encrypt the payload locally with the
  plaintext DEK (AES-256-GCM); store the *encrypted* DEK alongside the ciphertext; zeroize the
  plaintext DEK (rules/02 §7). Decrypt = ask KMS to unwrap the stored DEK, then decrypt locally.
- **Why:** the root key never exists outside the HSM; access is IAM-controlled and audit-logged
  per operation; "rotation" of the root key is a KMS toggle (old versions still unwrap old
  DEKs); revoking an app's decrypt permission instantly bricks its access without touching data.
- **Key hierarchy and rotation:** root (KMS, auto-rotate yearly) → optional per-tenant key →
  DEK per object. Re-encrypting data is only needed if a *DEK* is compromised; root rotation
  requires nothing. Per-tenant keys also give you crypto-shredding (destroy tenant key =
  tenant data unrecoverable) for deletion compliance.
- **Use a maintained client library** (AWS Encryption SDK, Tink, cloud KMS client envelopes) —
  they handle DEK caching (bound: time *and* message count), nonce management, and
  algorithm-suite headers. Hand-rolled AES around KMS calls gets nonce reuse wrong.
- **Encryption context / AAD:** bind ciphertexts to their identity (`tenant_id`, `record_id`)
  so ciphertext can't be swapped between rows; it also lands in KMS audit logs.
- AUDIT: literal 32/64-hex-char "ENCRYPTION_KEY" values (High; Critical if committed),
  AES-ECB or static-IV usage near such keys, `Fernet(key)` with a key from code, DEKs stored
  *unencrypted* next to data, KMS `Decrypt` permission granted on `*`.

```python
# BAD — raw key in config, hand-rolled crypto, no rotation story
cipher = AES.new(bytes.fromhex(os.environ["ENCRYPTION_KEY"]), AES.MODE_ECB)

# GOOD — KMS envelope per record, context-bound, wrapped DEK stored with ciphertext
dek = kms.generate_data_key(KeyId=ROOT_KEY_ARN, KeySpec="AES_256",
                            EncryptionContext={"tenant": tenant_id})
ct = AESGCM(dek["Plaintext"]).encrypt(nonce := os.urandom(12), payload, tenant_id.encode())
store(record_id, ct, nonce, wrapped_dek=dek["CiphertextBlob"])
del dek  # drop plaintext DEK immediately; zeroize where the runtime allows
```

## 8. `.env` file discipline

`.env` files are a dev convenience, not a production secret store.

- **Never committed:** `.env`, `.env.local`, `.env.production` etc. in `.gitignore` from repo
  creation; a tracked `.env` with real values is High (Critical if prod). Check history, not
  just HEAD (rules/04 §4).
- **`.env.example` is committed** and lists every variable with empty or obviously-fake values
  (`STRIPE_KEY=sk_test_REPLACE_ME`) — it is documentation. Realistic-looking values in the
  example file mask scanner findings (Low) and get copy-pasted into real use.
- **Local values are dev-scoped** (test keys, local DB) — never paste prod values into a
  laptop `.env`; that file is outside every audit log and backup policy. If devs need prod-like
  data access, that's a gated, logged, temporary credential from the secret store
  (`vault login` + dynamic creds, `aws-vault exec`), not a static copy.
- **Production:** the platform injects env/files from the secret manager (rules/02 §6);
  a `.env` file on a prod host or COPY'd into an image (grep Dockerfiles for `COPY .env`,
  and check `.dockerignore` excludes `.env*`) is a High finding.
- **Permissions `0600`**; don't `source .env` in shells with `set -x` or in CI steps with
  echoed commands; don't print env in debug scripts.
- Loader behavior: dotenv loads only in dev (`if NODE_ENV !== 'production'`-style guards or
  dev-only dependency), so a stray file can't silently override prod config.

```js
// BAD — dotenv unconditionally; a forgotten .env on a prod host wins over the platform
require("dotenv").config();

// GOOD — dev-only, explicit, and never overriding real environment
if (process.env.NODE_ENV !== "production") {
  require("dotenv").config({ override: false });
}
```

```gitignore
# Repo-template .env discipline (see rules/04 §2 for the full ignore set)
.env
.env.*
!.env.example
```

Package-manager rc files are `.env`-class: `.npmrc`/`.yarnrc.yml` with `_authToken`, `.pypirc`
with passwords, `pip.conf` with index creds, `.netrc`. Keep tokens out of the committed rc —
use env interpolation (`//registry.npmjs.org/:_authToken=${NPM_TOKEN}`) so the file is safe to
commit and the token rides the secret layer; a literal token in any rc file in VCS is High.
Registry publish tokens are no longer ordinary long-lived secrets: after the Shai-Hulud worm,
npm permanently revoked all classic tokens (Dec 2025, creation disabled) and caps granular
write tokens at 90 days — publish from CI via trusted publishing (per-job OIDC, no stored
token; rules/01 §4) and treat any residual registry token as a ≤90d rotating secret.

## Audit checklist

- [ ] DB access uses IAM auth or dynamic creds where supported; static passwords rotate via
      dual users; app DB users least-privilege; no DSNs with userinfo in code/logs; TLS to DB.
- [ ] API keys: per-service per-env, vendor-side restricted, test keys in non-prod/CI, ≤90d
      rotation, none in client-shipped code; webhook signatures constant-time + dual-secret +
      replay-protected.
- [ ] Signing keys non-exportable in KMS/HSM (or Sigstore keyless); one key per purpose;
      verification material published/versioned; signing operations audit-logged.
- [ ] TLS: ACME automation, ≤90d certs, keys generated in place, `0400`, no key files in
      repos/images/build contexts; internal mTLS via private CA; no disabled cert verification.
- [ ] SSH: Ed25519 per-person per-device or SSH CA certs; `authorized_keys` inventoried and
      pruned on offboarding; no private keys in repos/images; no unrestricted CI SSH keys;
      agent forwarding off.
- [ ] JWT: asymmetric alg for multi-verifier setups, algorithm pinned, no `none`/confusion
      paths, `kid`-based JWKS rotation with refresh-on-unknown-`kid`, ≤15m access-token TTL,
      no JWT secrets with defaults, no real JWTs in fixtures.
- [ ] Field/object encryption uses KMS envelope (wrapped DEKs, encryption context, maintained
      SDK); no raw keys in config; per-tenant keys where deletion guarantees are needed.
- [ ] `.env*` untracked (HEAD and history) with `0600`; `.env.example` fake-valued; dotenv
      dev-only and non-overriding; `.dockerignore` excludes `.env*`; no prod values in local
      env files; rc files (`.npmrc`, `.pypirc`, `.netrc`) use env interpolation, never literal
      tokens; registry publishing uses trusted publishing (OIDC), not stored long-lived tokens.
