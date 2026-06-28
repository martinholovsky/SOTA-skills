# 04 — Cryptography & Secrets

Scope: algorithm selection, AEAD/nonce discipline, key management, randomness,
TLS configuration, constant-time comparison, secrets handling.
Maps to OWASP A04:2025 (Cryptographic Failures), CWE-327/326/330/321/323/208.

Core principle: **don't design, don't implement, barely even compose.** Use a
misuse-resistant high-level library (libsodium/NaCl, Tink, age, Go `crypto/*`
high-level APIs) and its documented recipes. Hand-assembled crypto (manual
IV handling, custom padding, DIY key derivation, homemade protocols) is a finding
by default (CWE-1240).

## 1. Algorithm choices (2026 defaults)

| Purpose | Use | Never |
|---|---|---|
| Symmetric encryption | AES-256-GCM, ChaCha20-Poly1305, XChaCha20-Poly1305 (random-nonce safe) | ECB, CBC w/o MAC, RC4, DES/3DES, AES-CTR alone |
| Key exchange | X25519 (hybrid w/ ML-KEM-768 for PQ readiness) | static DH < 2048, custom DH params |
| Signatures | Ed25519; ECDSA P-256 (deterministic nonce, RFC 6979) where required | RSA-PKCS1v1.5 for new code, DSA |
| Hashing (integrity) | SHA-256/SHA-512, BLAKE2/3 | MD5, SHA-1 (CWE-328) |
| Password hashing | argon2id (see rules/02) | any fast hash |
| KDF from keys | HKDF (per-purpose `info` labels) | raw hash of key material, hash chains |
| MAC | HMAC-SHA-256, Poly1305 (within AEAD), KMAC | H(key‖msg) — length extension (CWE-328) |

- Encrypt-then-MAC if composing manually — but don't compose manually; use AEAD.
- Post-quantum: for long-lived confidentiality (data recorded now, decrypted
  later), prefer hybrid KEMs (X25519+ML-KEM-768) in TLS/protocol layers where
  the stack supports it; signatures can wait, harvest-now-decrypt-later can't.
  NIST IR 8547 (draft) sets the migration clock: 112-bit-security RSA/ECC
  (RSA-2048, P-256) deprecated after 2030 and all quantum-vulnerable
  RSA/ECDSA/ECDH/DSA disallowed after 2035 — maintain a cryptographic
  inventory (CBOM) now so the swap to ML-KEM/ML-DSA/SLH-DSA is a config
  change, not a rewrite (see §8 crypto agility).

## 2. AEAD and nonce discipline (CWE-323)

- **Nonce reuse with the same key in GCM/ChaCha20-Poly1305 is catastrophic**:
  reveals XOR of plaintexts and (GCM) the auth key → forgeries.
- Rules per cipher:
  - AES-GCM, 96-bit nonce: counter/LFSR per key, or random with a hard cap of
    ~2^32 encryptions per key (birthday bound). Rotating keys beats counting.
  - XChaCha20-Poly1305: 192-bit nonce — random nonces safe at any realistic
    volume. **Default choice when callers pick nonces.**
  - Or use nonce-misuse-resistant modes: AES-GCM-SIV, where available.
- Never derive nonces from timestamps, user IDs, or row IDs alone; never hardcode
  (CWE-329); never reuse a key across encryption contexts without HKDF separation.
- Authenticate context with **associated data (AAD)**: bind ciphertexts to their
  purpose/record (`aad = user_id || field_name`) so ciphertexts can't be swapped
  between rows/columns (cryptographic confused deputy).
- Decryption failures: uniform error, no padding/MAC distinction surfacing to the
  caller (padding-oracle family, CWE-209/CWE-203); never act on plaintext before
  the tag verifies (no streaming-decrypt-then-check).

```python
# GOOD: libsodium-style sealed usage
from nacl.secret import Aead  # XChaCha20-Poly1305
box = Aead(key)
ct = box.encrypt(plaintext, aad=record_id)   # nonce generated & prepended
pt = box.decrypt(ct, aad=record_id)
```

## 3. Randomness (CWE-330/338)

- Security-relevant randomness (keys, tokens, nonces, session IDs, reset codes,
  CSRF tokens) comes from the OS CSPRNG only: `secrets`/`os.urandom`,
  `crypto.randomBytes`, `crypto/rand`, `SecureRandom`, `getrandom(2)`.
- Findings on sight: `Math.random()`, `random.random()`, `rand()`, Java
  `java.util.Random`, time-seeded PRNGs, or UUIDv1/v4-from-non-crypto-PRNG used
  for any credential-like value.
- Token entropy ≥ 128 bits; compare tokens constant-time (§6); store long-lived
  tokens hashed (SHA-256) so a DB leak isn't a credential leak.
- Entropy is destroyed by post-processing: `random_string[:6]`, modulo into a
  small alphabet with bias, or "human-friendly" filtering can collapse 128
  bits to brute-forceable space — generate directly in the target alphabet
  (`secrets.token_urlsafe`, `secrets.choice` loops) and recount bits after.

```python
# BAD: 6-digit code via modulo of a 32-bit value — biased AND tiny
code = str(struct.unpack("I", os.urandom(4))[0] % 1000000)
# GOOD: unbiased, library-managed
code = "".join(secrets.choice(string.digits) for _ in range(6))   # + rate limits (rules/02)
token = secrets.token_urlsafe(32)                                  # 256-bit URL-safe
```

## 4. Key management (CWE-320/321/798)

- **No hardcoded keys/secrets in source, config files in git, or client-side
  bundles** (CWE-798). Scan history too — a committed-then-removed key is leaked.
- Storage hierarchy (best→acceptable): cloud KMS/HSM (keys never leave; you call
  encrypt/sign) → secrets manager (Vault/ASM/GSM) with short-TTL dynamic secrets
  → env vars injected at deploy (last resort; visible in /proc, crash dumps,
  child processes).
- **Key separation**: one key per purpose (encrypt ≠ sign ≠ token-MAC), per
  environment (prod ≠ staging), derived via HKDF with distinct `info` labels if
  from a master key.
- **Rotation must be designed in from day one**: version every ciphertext/token
  with a key ID; decrypt with old, encrypt with new; automate rotation cadence
  and revocation on suspicion. "We can't rotate without downtime" is a finding.
- Envelope encryption for data at rest: KMS master key wraps per-object data
  keys; plaintext data keys held only in memory, zeroized where the language
  allows.
- **Design for key *loss*, not just compromise** (OWASP Key Management): a root key
  with no recovery path means every ciphertext it protects is gone (the SOPS+age root
  is exactly this risk — back it up to hardware/escrow). **Back up / escrow
  data-encryption keys** so encrypted data stays recoverable; **never escrow signing or
  authentication keys** — a second copy destroys non-repudiation. Store key backups
  under the same KMS/HSM control as the originals, with their own access audit.
- Key material in memory: avoid copies (immutable strings in GC languages spread
  copies — prefer byte arrays you can zero); never in logs, exceptions, or
  serialized debug output.

```python
# GOOD: envelope encryption with key versioning and AAD context-binding
def encrypt_field(plaintext: bytes, record_id: str) -> bytes:
    dek = secrets.token_bytes(32)                       # per-object data key
    wrapped = kms.encrypt(key_id=CURRENT_KEY, plaintext=dek)   # master never leaves KMS
    box = ChaCha20Poly1305(dek)
    nonce = secrets.token_bytes(12)
    ct = box.encrypt(nonce, plaintext, record_id.encode())     # AAD = record binding
    return pack(version=CURRENT_KEY, wrapped=wrapped, nonce=nonce, ct=ct)
    # decrypt: unpack -> kms.decrypt(wrapped) by version -> open with same AAD

# GOOD: per-purpose subkeys from one master via HKDF (never reuse raw master)
enc_key  = HKDF(master, info=b"app/v1/field-encryption", length=32)
mac_key  = HKDF(master, info=b"app/v1/url-signing",      length=32)
```

### 4.1 Encrypting data at rest — design notes

- Decide the threat first: full-disk/volume encryption defeats stolen disks
  only; application-layer field encryption defeats DB compromise and curious
  DBAs — most "encrypt PII" requirements mean the latter.
- Deterministic encryption (same plaintext → same ciphertext, for
  equality-searchability) leaks equality and frequency — confine to
  low-sensitivity lookup keys, or use blind indexes (HMAC of normalized value,
  separate key) alongside randomized encryption of the value itself.
- Don't encrypt what you can avoid storing; hashing (rules/02) or truncation
  (last-4 of PAN) beats encryption when you never need the value back.

## 5. TLS configuration (CWE-295/319)

- Minimum TLS 1.2 with AEAD ciphers + ECDHE only; prefer TLS 1.3. No CBC suites,
  no RSA key exchange (no forward secrecy), no renegotiation, no compression
  (CRIME).
- **Certificate verification is never optional**: `verify=False`,
  `InsecureSkipVerify: true`, `rejectUnauthorized: false`, trust-all
  TrustManagers, hostname-check disabling — all findings, including in tests
  that can leak into prod paths (CWE-295). Internal services get a private CA,
  not disabled verification.
- Verify hostname AND chain; pin only when you control update cadence (mobile
  apps), pin to SPKI of an intermediate/leaf set, with backup pins.
- Plaintext fallbacks: no HTTP listeners that serve content (redirect-only),
  HSTS (rules/05); internal traffic encrypted too — mTLS for service-to-service
  (identity, not just confidentiality).
- Outbound TLS from your code deserves the same scrutiny as inbound config —
  audit every HTTP client construction for verification overrides.

```nginx
# GOOD: server baseline (nginx) — TLS 1.2/1.3, AEAD+ECDHE only, OCSP stapling
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
ssl_prefer_server_ciphers off;        # TLS1.3 best practice: client picks
ssl_stapling on; ssl_stapling_verify on;
ssl_session_tickets off;              # or rotate ticket keys — static keys break FS
# generate from Mozilla SSL Config Generator ("intermediate") and re-check yearly
```

- Verification-key distribution: publish via versioned key sets (JWKS-style,
  `kid` on every artifact), cache with TTL, overlap old+new during rotation,
  and pin the JWKS *endpoint* to your own allowlist (rules/02 §3 `jku` rules).

## 6. Constant-time comparison (CWE-208)

- Any comparison where one side is secret (MACs, tokens, API keys, OTP codes,
  signatures) must be constant-time: `hmac.compare_digest`,
  `crypto.timingSafeEqual`, `subtle.ConstantTimeCompare`, `MessageDigest.isEqual`.
- `==`/`memcmp`/`String.equals` short-circuit on first mismatch → remote timing
  oracle that recovers secrets byte-by-byte.
- Don't branch on secret data or index arrays by secret values in hot crypto
  paths; in app code, the rule reduces to: use the library comparator, and
  compare hashes of variable-length secrets to avoid length leaks.

```python
# BAD
if token == stored: ...
# GOOD
if hmac.compare_digest(hashlib.sha256(token.encode()).digest(),
                       hashlib.sha256(stored.encode()).digest()): ...
```

## 7. Signing & signed artifacts

- Signed URLs / signed cookies / license blobs: HMAC-SHA-256 over a
  **canonical, unambiguous encoding** of all security-relevant fields
  (object, verb, expiry, principal) — concatenation without delimiters is
  forgeable (`user=ab` + `role=c` vs `user=a` + `brole=c`); use length-prefixed
  or serialized-struct encoding. Always include and verify expiry.
- Verify-then-parse: check the signature before interpreting any field
  (signature covers everything you act on, including the key version).
- Ed25519 for third-party-verifiable signatures (webhooks you emit, release
  artifacts, inter-service assertions); HMAC when signer and verifier are the
  same trust domain. Publish/rotate verification keys via versioned key sets
  (JWKS pattern), never "the current key" with no ID.
- For software supply chain: sign releases/containers (Sigstore/cosign-class
  tooling), verify in deploy pipelines; lockfile + checksum verification for
  dependencies is the minimum (CWE-494, A08:2025; supply chain is now its own
  OWASP category, A03:2025).

## 8. Secrets hygiene in code & pipelines

- Secret detection in CI (gitleaks/trufflehog) blocking merges; pre-commit hooks
  as the early net. On any hit: **rotate first**, then scrub history.
- Secrets never in: URLs/query strings (CWE-598), log statements (rules/07),
  error messages, client-visible config (`NEXT_PUBLIC_*`, mobile binaries —
  anything shipped to the client is public), CI logs (mask + use OIDC-federated
  short-lived cloud creds instead of static keys).
- Distinguish secret classes: long-lived signing keys (KMS, non-exportable) vs
  rotating service credentials (secrets manager, TTL) vs per-user tokens
  (hashed at rest).
- Crypto agility: central crypto module/wrapper so algorithm/params live in one
  place; grep-able, upgradeable, with ciphertext version tags.

## 9. Audit grep starters

High-signal patterns to sweep for in AUDIT mode (confirm reachability before
reporting — see SKILL.md):

```text
verify=False | InsecureSkipVerify | rejectUnauthorized:\s*false | TrustAllCerts
NoopHostnameVerifier | CURLOPT_SSL_VERIFYPEER,\s*0 | ssl._create_unverified
MD5|SHA1 near sign/verify/token/password   AES/ECB | DES | RC4 | Blowfish
Math\.random|random\.random|java\.util\.Random near token/key/secret/otp/nonce
new IvParameterSpec\(.*getBytes  (static IV)   "-----BEGIN (RSA|EC|) PRIVATE KEY"
== or equals\( comparing signature|mac|token|otp    secret\s*=\s*["'][A-Za-z0-9+/]{8,}
createCipheriv\(.*, *(['"]).{1,16}\1  (short/static key/nonce)
```

## Audit checklist

- [ ] Are all symmetric encryptions AEAD (GCM/ChaCha20-Poly1305 family), with no ECB/unauthenticated-CBC/custom modes anywhere?
- [ ] Is nonce generation per-key safe (counter or XChaCha/SIV for random), never hardcoded or derived from predictable values?
- [ ] Is AAD used to bind ciphertexts to their context?
- [ ] Do all security tokens/keys come from the OS CSPRNG with ≥128-bit entropy?
- [ ] Are there zero hardcoded secrets in source, git history, or client bundles, with CI secret scanning enforced?
- [ ] Are keys separated per purpose/environment, versioned, and rotatable without downtime?
- [ ] Is every TLS client verifying certificates and hostnames (no skip-verify flags), TLS ≥1.2 AEAD-only?
- [ ] Are all secret comparisons (tokens, MACs, OTPs) constant-time?
- [ ] Are long-lived stored tokens hashed at rest?
- [ ] Is MD5/SHA-1 absent from any security-relevant use?
- [ ] Do decryption/verification failures return uniform errors and stop processing before plaintext use?
- [ ] Are signed URLs/blobs HMAC'd over canonical encodings with expiry, verified before any field is used?
- [ ] Is sensitive-field encryption application-layer (envelope, AAD-bound), with deterministic encryption confined to blind indexes?
- [ ] Are dependencies and release artifacts checksum/signature-verified in CI/CD?
- [ ] Is there a single crypto wrapper module rather than scattered primitive calls?
