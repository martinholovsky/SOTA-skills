# 04 — Cryptography & Secrets

Scope: algorithm selection, AEAD/nonce discipline, key management, randomness,
TLS configuration, secrets handling (constant-time comparison: rules/22).
Maps to OWASP A04:2025 (Cryptographic Failures), CWE-327/326/330/321/323/208.

Core principle: **don't design, don't implement, barely even compose.** Use a
misuse-resistant high-level library (libsodium/NaCl, Tink, age, Go `crypto/*`
high-level APIs) and its documented recipes. Hand-assembled crypto (manual
IV handling, custom padding, DIY key derivation, homemade protocols) is a finding
by default (CWE-1240).

## 1. Algorithm choices (2026 defaults)

| Purpose | Use | Never |
|---|---|---|
| Symmetric encryption | AES-256-GCM, ChaCha20-Poly1305, XChaCha20-Poly1305 (random-nonce safe) | ECB, CBC w/o MAC, RC4, RC2, DES/3DES, AES-CTR alone |
| Key exchange | X25519 (hybrid w/ ML-KEM-768 for PQ readiness), peer key validated and authenticated (§1.1) | static DH < 2048, custom DH params, unauthenticated ECDH |
| RSA encryption / key transport | RSA-OAEP (SHA-256) — or avoid RSA encryption and use a KEM/hybrid scheme | RSAES-PKCS1-v1_5 (`RSA1_5` in JOSE, `xmlenc#rsa-1_5` in XML Encryption), textbook/`NoPadding` RSA |
| Encrypting to a public key (no shared symmetric key) | HPKE (RFC 9180: KEM + KDF + AEAD, `info` bound to the context), libsodium sealed box or Tink hybrid; all hide the sender, so authenticate it separately | RSA over the payload itself, a hand-built "ECDH then AES" |
| Signatures | Ed25519; ECDSA P-256 (deterministic nonce, RFC 6979) where required | RSA-PKCS1v1.5 for new code, DSA |
| Hashing (integrity) | SHA-256/SHA-512, BLAKE2/3 | MD5, SHA-1 (CWE-328) |
| Password hashing | argon2id (see rules/02) | any fast hash |
| Key from a password/passphrase | argon2id, scrypt, or PBKDF2-HMAC-SHA256 at ≥ 600,000 iterations (parameters: rules/02 §1) | HKDF, a bare or iterated fast hash, OpenSSL `EVP_BytesToKey` |
| KDF from keys | HKDF (per-purpose `info` labels) | raw hash of key material, hash chains |
| MAC | HMAC-SHA-256, Poly1305 (within AEAD), KMAC | H(key‖msg) — length extension (CWE-328) |

- Encrypt-then-MAC if composing manually — but don't compose manually; use AEAD.
- Key sizes: new designs target 128-bit security, consistent across a key hierarchy (§4).
- **Encoding, XOR and checksums are not security controls** (CWE-327/CWE-311). Base64,
  hex, URL-encoding and compression are reversible by anyone; XOR with a fixed or short
  key falls to one known plaintext; CRC32, Adler-32 and other non-cryptographic checksums
  can be recomputed by whoever changed the data, so they detect accidents, not attackers.
  Wherever one of these is what stands between a value and an adversary — "obfuscated"
  config secrets, a CRC guarding a licence blob or a cookie, a Base64 "encrypted" field —
  it is a finding: use AEAD for confidentiality and a MAC or signature for integrity.
  Sweep for RC2 and single DES in the same pass.
- **RSA encryption is OAEP or nothing.** PKCS#1 v1.5 encryption is kept in RFC 8017 "only
  for compatibility with existing applications": any decrypter that lets a caller tell a
  bad-padding failure from any other outcome (error text, status, timing) is a
  Bleichenbacher-class oracle that decrypts ciphertexts and can forge signatures with the
  same key. XML Encryption 1.1 section 6.1 recommends RSA-OAEP and says documents carrying
  PKCS#1 v1.5 or AES-CBC ciphertexts should be rejected without decryption — so a SAML SP
  or XML decrypter must **allowlist its key-transport and data-encryption algorithms**
  rather than honour whatever `EncryptionMethod` the document names, and must not keep a
  v1.5 decryption path "for old clients" on a key that also decrypts OAEP or signs (section
  6.1.3 of the same spec: the legacy path breaks the modern one). Never share one RSA key pair
  between encryption and signing. OWASP: Cryptographic Storage cheat sheet, SAML Security
  cheat sheet.
- **Password-derived keys need a stretched KDF**: HKDF can concentrate entropy but not
  add it, and RFC 5869 section 4 points password use elsewhere; a fast hash lets an attacker test
  billions of guesses per second against the ciphertext. OpenSSL's own manual says newer
  applications should use PBKDF2 rather than `EVP_BytesToKey`, which is what `openssl enc`
  runs, with one iteration, unless given `-pbkdf2` or `-iter` (and `-pbkdf2` alone
  defaults to 10,000 iterations — set `-iter`). Store the salt and parameters beside the
  ciphertext. OWASP:
  Cryptographic Storage cheat sheet, Go-SCP (data protection), ASVS 5.0 V11.4.4.
- **Algorithm, parameters and key choice come from server-side configuration, never from the message** (JWT `alg`, rules/17 §3; XML `EncryptionMethod`, above). On a device the attacker owns, crypto and RNG calls can be hooked:
  where that threat is in scope, rely on attestation and server-side checks (`sota-mobile` rules/04 §4.5, §4.8). OWASP: Cornucopia CRK, CRMK.

### 1.1 Key agreement — validate the peer key, authenticate the peer, confirm the key

- **Validate the peer's public key before using it.** A point that is off the curve, on
  the twist, or of small order lets an attacker learn bits of a static private key
  (invalid-curve and small-subgroup attacks). For NIST curves, the decoder must reject
  such points; for X25519, RFC 7748 section 6.1 lets both sides check for an all-zero shared
  secret (a small-order input) and abort. Mainstream high-level APIs do this — measured
  2026-09-25: pyca/cryptography 49 and Node 22 raise on an all-zero X25519 result and Node
  rejects an off-curve P-256 point, and Go's `crypto/ecdh` documents both checks. The
  finding is hand-rolled curve arithmetic, a raw scalar-multiplication call whose error
  return is ignored, or a library whose validation you have not confirmed.
- **Unauthenticated (EC)DH proves nothing about who is on the other end** (CWE-322): an
  active attacker runs one exchange with each side. Bind the exchange to an identity —
  sign the ephemeral keys or the transcript with a long-term key, use certificates, or mix
  in a pre-shared key — or use a vetted protocol (TLS 1.3, Noise, HPKE) that does.
- **Confirm the key before using it**: both sides prove they derived the same key, for
  example with a MAC over the full handshake transcript (this is what the TLS 1.3
  `Finished` message does, RFC 8446 section 4.4.4), and abort on mismatch. Derive the session
  keys with HKDF over the shared secret **and** both public keys, never use the raw shared
  secret as a key. OWASP: DotNet Security cheat sheet, Java Security cheat sheet, Key
  Management cheat sheet.
- Post-quantum: for long-lived confidentiality (data recorded now, decrypted
  later), prefer hybrid KEMs (X25519+ML-KEM-768) in TLS/protocol layers where
  the stack supports it; signatures can wait, harvest-now-decrypt-later can't.
  NIST IR 8547 (draft) sets the migration clock: 112-bit-security RSA/ECC
  (RSA-2048, P-256) deprecated after 2030 and all quantum-vulnerable
  RSA/ECDSA/ECDH/DSA disallowed after 2035 — maintain a cryptographic
  inventory (CBOM) now so the swap to ML-KEM/ML-DSA/SLH-DSA is a config
  change, not a rewrite (see §9 crypto agility).
- **What that inventory holds**: every key, algorithm, parameter set and certificate; per
  key, which components and operations may use it and which must not, and which data
  classes it may and may not protect; and every place key material is generated, stored,
  cached or processed (HSM, KMS, keystores, config, CI secrets, backups). Rebuild it on a
  schedule and at each release by *discovery* — a sweep for every use of encryption,
  hashing, signing, MAC and key agreement (§10 discovery row), not only the weak ones —
  and reconcile: a call site the inventory does not list is a finding. OWASP: ASVS 5.0
  V11.1.2, V11.1.3, Key Management cheat sheet.

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
  the tag verifies (no streaming-decrypt-then-check). Internally, every encrypt, decrypt or verify
  failure emits a security event (`crypt_decrypt_fail`, rules/07 §2.1): a spike is tampering or a probe.
- **Full 128-bit tag, length-checked input.** Java `new GCMParameterSpec(128, iv)` (SunJCE also accepts 96–120, measured JDK 25), Go `NewGCM` rather than
  `NewGCMWithTagSize` below 16, Python's default `min_tag_length=16`, Node `authTagLength: 16`. Check `len(ct) >= nonce + tag` before slicing:
  Go's `data[:ns]` on a short input panics (measured Go 1.27). OWASP: Java Security, Cryptographic Storage, DotNet Security cheat sheets.

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
- Token entropy ≥ 128 bits; compare tokens constant-time (rules/22 §1); store long-lived
  tokens hashed (SHA-256) so a DB leak isn't a credential leak.
- Entropy is destroyed by post-processing: `random_string[:6]`, modulo into a
  small alphabet with bias, or "human-friendly" filtering can collapse 128
  bits to brute-forceable space — generate directly in the target alphabet
  (`secrets.token_urlsafe`, `secrets.choice` loops) and recount bits after.
- **The CSPRNG stays a CSPRNG under load and at boot.** A path that falls back to a time-
  or PID-seeded PRNG, `Math.random()` or a cached value when the OS source errors, blocks
  or is slow is a finding (CWE-338): fail the request instead. Use the interfaces Linux
  `random(7)` recommends (`getrandom()` without `GRND_RANDOM`, or `/dev/urandom`) and keep
  blocking sources off hot paths — Java `SecureRandom.getInstanceStrong()` returns
  `NativePRNGBlocking` on Linux where `new SecureRandom()` returns `NativePRNG` (measured
  JDK 25). OWASP: ASVS 5.0 V11.5.2.
- **Randomness a participant can steer** (lotteries, on-chain games, winner or leader
  selection among parties who distrust each other) must resist manipulation, not only
  prediction. `block.timestamp`, `blockhash` and `block.prevrandao` are seen or chosen by
  block producers; use a VRF whose proof is verified, or commit-reveal where every party
  commits a hash before any value is known. OWASP: SCSVS S6.3.A2, SCWE-031, SCWE-153.
- **Keys come from a vetted generator; keys you import get checked for known weak
  classes.** Uploaded certificates, CSRs, SSH keys and JWKS can carry a generator flaw:
  ROCA (CVE-2017-15361, Infineon's RSA library) or Fermat-factorable close primes
  (CVE-2022-26320). `badkeys -c fermat,roca key.pem` tests both — measured with 0.0.20: exit
  4 on a close-prime RSA-2048 key, exit 0 on an OpenSSL one. OWASP: ASVS 5.0 V11.6.1.

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
- **Key strength holds all the way down the hierarchy** (CWE-326). A key that wraps other
  keys is at least as strong as the strongest one it protects: an AES-256 DEK under an
  RSA-2048 or AES-128 KEK has 112 or 128 bits of security, not 256. Match asymmetric sizes
  to their symmetric neighbours with SP 800-57 Part 1 Rev 5 Table 2 (128-bit: AES-128,
  RSA-3072, P-256; 192-bit: AES-192, RSA-7680, P-384). Generate DEK and KEK independently;
  a DEK recomputable from the KEK's own secret gains nothing from being wrapped. Size for
  how long the data must stay secret: Table 4 lets 112-bit protection be *applied* only
  through 2030, and the text says data needing four years of secrecy should not be
  encrypted after 2026 with an algorithm whose lifetime ends in 2030. **New designs target
  128-bit security**; 112 bits (§1.1) is a legacy allowance. OWASP: ASVS 5.0 V11.2.3,
  Cryptographic Storage cheat sheet, Key Management cheat sheet.
- **Rotation must be designed in from day one**: version every ciphertext/token
  with a key ID; decrypt with old, encrypt with new; automate rotation cadence
  and revocation on suspicion. "We can't rotate without downtime" is a finding.
- Envelope encryption for data at rest: KMS master key wraps per-object data
  keys; plaintext data keys held only in memory, zeroized where the language
  allows.
- **Passphrase-protected data uses the same envelope**: a random DEK encrypts the data,
  and a KEK derived from the passphrase with the stretched KDF of §1 (salt + parameters
  stored alongside) wraps the DEK. A passphrase change then re-wraps one small key
  instead of re-encrypting everything, and several passphrases or a recovery key can wrap
  the same DEK. Encrypting the data directly under the passphrase-derived key is a
  finding. OWASP: Cryptographic Storage cheat sheet, Secrets Management cheat sheet.
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
  Convergent encryption (key derived from the content, for deduplication) is
  deterministic too: anyone who can guess a candidate plaintext can confirm it, so
  it needs a secret, high-entropy key mixed into the derivation and, where the
  content space is small, a resource-hard derivation.
- **Crypto fails closed** (CWE-311/CWE-636). When encryption, key unwrapping, a
  keystore or a KMS call fails, the operation fails: never store or send the value
  in plaintext, never retry under a weaker algorithm or a hard-coded fallback key,
  and never accept an unverifiable ciphertext or signature "for now". A `catch`
  whose body writes the plaintext, or a `crypto_enabled=false` default taken when
  the KMS is unreachable, is the silent-no-op shape of rules/10 §1 — make it loud
  (rules/10 §3) and failing.
- **Defence in depth**: encrypted data still gets access control, and the design
  should stay safe if one layer breaks — field encryption does not replace authz
  on the rows (rules/03), and a leaked DEK should expose one object, not all.
  OWASP: Cryptographic Storage cheat sheet, Secure Coding Practices QRG, Cornucopia.
- Don't encrypt what you can avoid storing; hashing (rules/02) or truncation (last-4 of PAN) beats
  encryption when you never need the value back, and a value you must recover is encrypted, never hashed.

## 5. TLS configuration (CWE-295/319)

- Minimum TLS 1.2 with AEAD ciphers + ECDHE only; prefer TLS 1.3. No CBC suites,
  no RSA key exchange (no forward secrecy), no renegotiation, no compression
  (CRIME).
- **Certificate verification is never optional**: `verify=False`,
  `InsecureSkipVerify: true`, `rejectUnauthorized: false`, trust-all
  TrustManagers, hostname-check disabling — all findings, including in tests
  that can leak into prod paths (CWE-295). Internal services get a private CA,
  not disabled verification.
- **Verification can also be absent without any flag**, which a skip-verify grep misses:
  - Raw sockets: Java's `SSLSocket`/`SSLEngine` do not check the hostname unless
    `SSLParameters.setEndpointIdentificationAlgorithm("HTTPS")` is set (JSSE
    Reference Guide); Python's bare `ssl.SSLContext()` starts with
    `check_hostname=False` and `CERT_NONE` (measured on 3.14 — use
    `ssl.create_default_context()` or `PROTOCOL_TLS_CLIENT`).
  - Handshake and certificate errors abort the connection. A `catch` that logs the
    exception and reconnects without TLS, or retries with verification off, is the
    same finding as `verify=False`. Interactive clients surface a clear warning and
    do not proceed silently.
  - **mTLS servers must chain-validate the client certificate** against the CA you
    expect before its subject becomes an identity: Go `RequestClientCert` and
    `RequireAnyClientCert` do not verify the certificate (`RequireAndVerifyClientCert`
    does); nginx `ssl_verify_client optional_no_ca` does not require a trusted CA, and
    with `optional` the app must still check `$ssl_client_verify` = `SUCCESS`.
  - **A forwarded client-certificate header is only as trustworthy as the hop that set
    it.** Envoy's `x-forwarded-client-cert` (XFCC) is sanitised by default;
    `ALWAYS_FORWARD_ONLY` forwards whatever the client sent, even without mTLS. Accept
    such a header only from an authenticated proxy link, and strip it at the edge
    (the `X-User-Id` rule in `sota-api-design` rules/07 §8).
  OWASP: ASVS 5.0 V12.1.3, MASTG-TEST-0234, Go-SCP (http tls), User Privacy Protection
  cheat sheet.
- **SSH host-key verification is the same control, and it is disabled the same
  way** (CWE-322, key exchange without entity authentication). A client that
  accepts any host key has encrypted its session to whoever answered. Every
  mainstream library ships an opt-out, and some **default to it**:
  - paramiko: `AutoAddPolicy`, and `WarningPolicy`, which warns and still
    accepts. The default is `RejectPolicy`.
  - Go `x/crypto/ssh`: `ssh.InsecureIgnoreHostKey()` ("accept any host key").
  - Ruby `net-ssh`: `verify_host_key: :never` or `false`. **Unset defaults to
    `:accept_new_or_local_tunnel`**, which its own docs rank as insecure, so
    here too the finding can be an absence.
  - JVM: JSch `StrictHostKeyChecking` set to `no`; Apache MINA SSHD
    `AcceptAllServerKeyVerifier`.
  - Node `ssh2`: **auto-accepts when no `hostVerifier` is set**, so the finding
    there is an *absence*.
  - Rust: `russh` rejects unknown keys by default (`check_server_key` returns
    `Ok(false)`), so the finding is an override returning `Ok(true)` without
    `check_known_hosts`. The crate's own test handler does exactly that, which is
    the version people copy. The `ssh2` crate's `Session::handshake()` checks no
    host key at all: an *absence* unless the code calls `known_hosts()` and
    `check_port`.
  - PHP: phpseclib's `login()` never compares the host key, and the key-exchange
    signature is verified only inside `getServerPublicHostKey()`, which nothing in
    the library calls. ext-ssh2 has no known-hosts support at all. Both are
    *absences*: compare `getServerPublicHostKey()` or `ssh2_fingerprint()` (ask for
    SHA-1; the default is MD5) to a pinned value before sending credentials.
  - .NET SSH.NET: **accepts any key when no `HostKeyReceived` handler is attached**,
    and inside a handler `CanTrust` starts out `true`. So both an absent handler and
    one that never sets `CanTrust = false` are findings.
  - OpenSSH and anything that shells out to it: `StrictHostKeyChecking=no`/`off`
    lets a *changed* key through. `accept-new` refuses a changed key but trusts
    first use, and `UserKnownHostsFile=/dev/null` throws the record away.

  The fix is a pinned `known_hosts` entry distributed with the deployment, or
  host certificates signed by an SSH CA, the analogue of the private CA above.
  **This rule is stated once, here.** Each language skill carries only its
  library's spelling of the detector (decided 2026-09-23; see
  `docs/LANGUAGE-TIER.md` in the library repo).
- Verify hostname AND chain. Pin only when you control both ends and the client's update cadence (native mobile, first-party
  clients), never in browsers (HPKP is obsolete) or toward a third party: SPKI pins with a backup key and a rotation plan (`sota-mobile` rules/04 §4.3).
- Plaintext fallbacks: no HTTP listeners that serve content (redirect-only),
  HSTS (rules/05); internal traffic encrypted too — mTLS for service-to-service
  (identity, not just confidentiality).
- Outbound TLS from your code deserves the same scrutiny as inbound config —
  audit every HTTP client construction for verification overrides.

```nginx
# GOOD: server baseline (nginx) — TLS 1.2/1.3, AEAD+ECDHE only
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
ssl_prefer_server_ciphers off;        # TLS1.3 best practice: client picks
ssl_session_tickets off;              # or rotate ticket keys — static keys break FS
# no ssl_stapling: OCSP is being retired — Let's Encrypt dropped OCSP URLs from
# certs (May 2025) and shut its responders (Aug 2025) in favor of CRLs; enable
# stapling only for a CA that still runs OCSP
# generate from Mozilla SSL Config Generator ("intermediate") and re-check yearly
```

- Verification-key distribution: publish via versioned key sets (JWKS-style,
  `kid` on every artifact), cache with TTL, overlap old+new during rotation,
  and pin the JWKS *endpoint* to your own allowlist (rules/17 §3 `jku` rules).

Constant-time comparison (formerly section 6) moved to [rules/22](22-constant-time-comparison.md) §1 on 2026-09-25.

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

Tamper-evident logs and audit ledgers (formerly section 8) moved to [rules/18](18-tamper-evident-logs.md) §1 on
2026-09-25; signed request/response exchanges and self-describing receipts are rules/18 §2.

## 9. Secrets hygiene in code & pipelines

- Secret detection in CI (gitleaks/trufflehog) blocking merges; pre-commit hooks
  as the early net. On any hit: **rotate first**, then scrub history.
- Secrets never in: URLs/query strings (CWE-598), log statements (rules/07),
  error messages, client-visible config (`NEXT_PUBLIC_*`, mobile binaries —
  anything shipped to the client is public), CI logs (mask + use OIDC-federated
  short-lived cloud creds instead of static keys).
- Distinguish secret classes: long-lived signing keys (KMS, non-exportable) vs
  rotating service credentials (secrets manager, TTL) vs per-user tokens
  (hashed at rest).
- Crypto agility: one crypto module holds algorithms and parameters, with ciphertext version tags, so a significant
  new attack on an algorithm triggers a planned migration and key rotation, not a rewrite.

## 10. Audit grep starters

High-signal patterns to sweep for in AUDIT mode (confirm reachability before
reporting — see SKILL.md):

```text
verify=False | InsecureSkipVerify | rejectUnauthorized:\s*false | TrustAllCerts
NoopHostnameVerifier | ssl._create_unverified | VERIFY_NONE
(SSL_VERIFYPEER|SSL_VERIFYHOST|verify_peer(_name)?)["']?\s*(,|=>)\s*(false|0) | allow_self_signed["']?\s*=>\s*(true|1)   (PHP)
AutoAddPolicy | WarningPolicy | InsecureIgnoreHostKey | verify_host_key:\s*(:never|:accept_new|false)
StrictHostKeyChecking["']?[=, ]*["']?(no|off) | AcceptAllServerKeyVerifier | UserKnownHostsFile=/dev/null
CanTrust\s*=\s*true (SSH.NET) | fn check_server_key then Ok(true) (russh)   absences: SSH.NET client with no
HostKeyReceived; Rust ssh2 handshake() with no known_hosts(); phpseclib/ext-ssh2 with no host-key compare
MD5|SHA1 near sign/verify/token/password   AES/ECB | DES | RC4 | Blowfish
Math\.random|random\.random|java\.util\.Random near token/key/secret/otp/nonce
new IvParameterSpec\(.*getBytes  (static IV)
-----BEGIN ([A-Z0-9]+ )*PRIVATE KEY( BLOCK)?-----   (RSA/EC/OPENSSH/PKCS#8/ENCRYPTED/PGP; pass after --)
== or equals\( comparing signature|mac|token|otp    secret\s*=\s*["'][A-Za-z0-9+/]{8,}
createCipheriv\(.*, *(['"]).{1,16}\1  (short/static key/nonce)
Base64 | btoa | XOR | crc32 | adler32 used as encryption/integrity   RC2 | single DES     (§1)
PKCS1Padding | PKCS1v15() | PKCS1_v1_5 | RSA_PKCS1_PADDING | RSAEncryptionPadding.Pkcs1 | xmlenc#rsa-1_5 | "RSA1_5"
sha256/md5/HKDF over a password | EVP_BytesToKey | `openssl enc` without -pbkdf2/-iter   (§1)
ECDH/X25519 exchange with no KDF in the file   catch/except that stores or returns plaintext (§4.1)
optional_no_ca | ALWAYS_FORWARD_ONLY | RequireAnyClientCert | RequestClientCert | ssl.SSLContext() | raw SSLSocket (§5)
discovery, every use not only weak ones (§1.1 inventory): *.getInstance of Cipher/MessageDigest/Signature/Mac/
KeyAgreement/KeyGenerator | createCipheriv/Hash/Hmac/Sign | crypto.subtle | hashlib | cryptography.hazmat | EVP_*
```

## Audit checklist

- [ ] Are all symmetric encryptions AEAD (GCM/ChaCha20-Poly1305 family), with no ECB/unauthenticated-CBC/custom modes anywhere?
- [ ] Is nonce generation per-key safe (counter or XChaCha/SIV for random), never hardcoded or derived from predictable values?
- [ ] Is AAD used to bind ciphertexts to their context?
- [ ] Do all security tokens/keys come from the OS CSPRNG with ≥128-bit entropy?
- [ ] Are there zero hardcoded secrets in source, git history, or client bundles, with CI secret scanning enforced?
- [ ] Are keys separated per purpose/environment, versioned, and rotatable without downtime?
- [ ] Is every TLS client verifying certificates and hostnames (no skip-verify flags), TLS ≥1.2 AEAD-only?
- [ ] **Is every SSH client verifying host keys? HIGH on any hit** — the §10 host-key row, plus
      every Node `ssh2` connect call with no `hostVerifier` (it auto-accepts). The pattern must
      match JSch's `setConfig("StrictHostKeyChecking", "no")` as well as `-o ...=no`; the
      first draft missed it:
      `grep -rnE 'AutoAddPolicy|WarningPolicy|InsecureIgnoreHostKey|verify_host_key:\s*(:never|:accept_new|false)|AcceptAllServerKeyVerifier|StrictHostKeyChecking["'"'"']?[=, ]*["'"'"']?(no|off)|UserKnownHostsFile=/dev/null|CanTrust[[:space:]]*=[[:space:]]*true' .`
      ; `grep -rn -A6 'fn check_server_key' --include='*.rs' . | grep -E 'Ok\(true\)'` (russh
      accepting every key). The absences (§5: SSH.NET, Rust `ssh2`, phpseclib, ext-ssh2, Node
      `ssh2`) need a per-file read: a client constructed in a file with no host-key check is the finding.
- [ ] **Is Base64, XOR or a CRC standing in for encryption or integrity, or is RC2/single DES
      in use (§1)? HIGH when it guards a secret or an authorization decision**:
      `grep -rniE '(encrypt|obfuscat|protect|secret|signature|integrity|tamper|password).*(base64|b64encode|btoa|crc32|adler32|xor|\^)|(crc32|adler32|b64encode|btoa)\(.*(signature|secret|password|token|licen[cs]e)|(^|[^a-z])(des|rc2)([^a-z]|$)' .`
      — read each hit; Base64 of an image or a CRC as a cache validator is fine.
- [ ] **Does any RSA encryption use PKCS#1 v1.5 or no padding, or does an XML/SAML/JOSE
      decrypter accept `rsa-1_5`/`RSA1_5` (§1)? HIGH**:
      `grep -rnE 'RSA/[A-Za-z]+/(PKCS1Padding|NoPadding)|PKCS1v15\(\)|PKCS1_v1_5|RSA_PKCS1_PADDING|RSA_NO_PADDING|RSAEncryptionPadding\.Pkcs1|xmlenc#rsa-1_5|"RSA1_5"' .`
      — `PKCS1v15()`/`PKCS1_v1_5` also name the v1.5 *signature* padding, so confirm the
      call encrypts or decrypts. An XML decrypter with no algorithm allowlist is the finding
      even with zero hits.
- [ ] **Is any key derived from a password with a fast hash, HKDF or `EVP_BytesToKey` (§1),
      and is passphrase-protected data encrypted directly under that key instead of wrapping
      a random DEK (§4)? HIGH**:
      `grep -rniE '(sha(1|256|512)|md5|hkdf|createHash|digest|Sum256)[^;]*(passw|passphrase|pwd)|EVP_BytesToKey|openssl enc [^|;]*-(pass|k )' . | grep -vE -e '-pbkdf2|-iter'`
- [ ] **Is every key agreement validated, authenticated and confirmed (§1.1)? HIGH when the
      peer is unauthenticated.** Files that run an exchange but never derive a key:
      `grep -rlE '\.exchange\(|\.ECDH\(|computeSecret\(|diffieHellman\(|KeyAgreement\.getInstance|crypto_scalarmult|ECDiffieHellman' . | while IFS= read -r f; do grep -qiE 'hkdf|kdf|derive' "$f" || echo "$f"; done`
      ; then read every exchange for peer-key validation, an identity binding and key
      confirmation — none of the three is visible to a grep.
- [ ] **Does any crypto, keystore or KMS failure fall back to plaintext, a weaker algorithm
      or acceptance (§4.1)? HIGH**:
      `grep -rn -A3 -E '(except|catch|rescue)' . | grep -iE 'plain(text)?|unencrypted|encrypt[a-z_]*[[:space:]]*=[[:space:]]*(false|False|0|nil|None)|=[[:space:]]*(data|payload|raw)[[:space:]]*(#|;|$)'`
- [ ] **Is TLS verification present where no flag disables it (§5)** — raw sockets, bare
      contexts, mTLS client-certificate trust, forwarded client-cert headers? HIGH:
      `grep -rnE 'optional_no_ca|ALWAYS_FORWARD_ONLY|RequireAnyClientCert|RequestClientCert|SSLContext\(\)|check_hostname[[:space:]]*=[[:space:]]*False|\(SSLSocket\)|createSSLEngine\(' .`
      — a raw `SSLSocket` hit is fine only with `setEndpointIdentificationAlgorithm("HTTPS")`;
      a Go `RequestClientCert` hit only with a `VerifyPeerCertificate` that chain-validates.
- [ ] Are long-lived stored tokens hashed at rest?
- [ ] Is MD5/SHA-1 absent from any security-relevant use?
- [ ] Do decryption/verification failures return uniform errors and stop processing before plaintext use?
- [ ] **Is every AEAD tag 128 bits and every ciphertext length-checked before slicing (§2)? MEDIUM**: `grep -rnE 'GCMParameterSpec\((32|64|96|104|112|120)[,)]|NewGCMWithTagSize\([^,]*,[[:space:]]*(1[0-5]|[0-9])\)|min_tag_length[[:space:]]*=[[:space:]]*([0-9]|1[0-5])([^0-9]|$)|authTagLength:[[:space:]]*([0-9]|1[0-5])([^0-9]|$)' .` ; then read each `[:nonceSize]`-style slice for a preceding length check.
- [ ] Are signed URLs/blobs HMAC'd over canonical encodings with expiry, verified before any field is used?
- [ ] Is sensitive-field encryption application-layer (envelope, AAD-bound), with deterministic encryption confined to blind indexes?
- [ ] Are dependencies and release artifacts checksum/signature-verified in CI/CD?
- [ ] Is there a single crypto wrapper module rather than scattered primitive calls?
- [ ] **Is key strength consistent and at 128 bits for new designs (§4)** — every KEK at least
      as strong as what it wraps, DEK and KEK independent, sizes chosen for the data's secrecy
      lifetime? MEDIUM (HIGH at 1024-bit RSA or a sub-224-bit curve): `grep -rnE 'key_size=(1024|2048)([^0-9]|$)|genrsa[^|;&]*[[:space:]](1024|2048)([^0-9]|$)|initialize\((1024|2048)[,)]|modulusLength:[[:space:]]*(1024|2048)([^0-9]|$)|GenerateKey\([^,]*,[[:space:]]*(1024|2048)\)|ssh-keygen[^|;&]*-b[[:space:]]*(1024|2048)([^0-9]|$)|secp192|secp224|SECP192R1|SECP224R1|P-224|prime192' .`
      — a 2048-bit hit is acceptable only for data whose secrecy ends before 2031.
- [ ] **Does any RNG path fall back to a weak PRNG, block on a hot path, or draw steerable
      on-chain randomness, and are imported public keys screened for weak classes (§3)? HIGH**:
      `grep -rn -A1 -E '(except|catch|rescue)' . | grep -E 'Math\.random|random\.(random|randint|choice)\(|java\.util\.Random|mt_rand\(|srand\(' ; grep -rnE 'getInstanceStrong\(|keccak256\(abi\.encode(Packed)?\([^;]*block\.(timestamp|prevrandao|difficulty)|blockhash\(' .`
      ; then pass each imported certificate and key file to `badkeys -c fermat,roca`.
- [ ] **Does a cryptographic inventory list every key, its allowed uses, data classes and
      holders, rebuilt by discovery (§1.1)? MEDIUM when absent** — reconcile every hit of
      `grep -rnE '(Cipher|MessageDigest|Signature|Mac|KeyAgreement|KeyGenerator|KeyPairGenerator)\.getInstance|create(Cipheriv|Decipheriv|Hash|Hmac|Sign|Verify)\(|crypto\.subtle\.|hashlib\.|hmac\.new|cryptography\.hazmat|from nacl|"crypto/(aes|cipher|hmac|sha[0-9]+|ecdsa|ed25519|rsa|ecdh)"|EVP_[A-Za-z0-9_]+\(|System\.Security\.Cryptography' .`
      against it; an unlisted call site is the finding.
