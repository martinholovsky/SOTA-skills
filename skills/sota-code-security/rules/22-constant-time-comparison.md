# 22 — Constant-Time Comparison (CWE-208)

Split out of [rules/04](04-cryptography.md) (formerly section 6) on 2026-09-25, when [rules/04](04-cryptography.md) reached the 485-line
working limit; the section is now §1 and its subsection 6.1 is §1.1.

## 1. Constant-time comparison (CWE-208)

- Any comparison where one side is secret (MACs, tokens, API keys, OTP codes,
  signatures) must be constant-time: `hmac.compare_digest`,
  `crypto.timingSafeEqual`, `subtle.ConstantTimeCompare`, `MessageDigest.isEqual`.
- `==`/`memcmp`/`String.equals` short-circuit on first mismatch → a timing side
  channel. Treat it as a defect wherever an attacker can submit candidates, but state
  the claim at the strength the evidence supports: byte-by-byte recovery is the
  *worst case*, and whether it is reachable depends on the protocol, network noise,
  attacker position and query volume. The primary sources are careful here and so
  should you be: Python's `compare_digest` is *"designed to prevent timing analysis by
  avoiding content-based short circuiting behaviour"* and still notes that *"a timing
  attack could theoretically reveal information about the types and lengths"* of the
  operands; libsodium says of `sodium_memcmp` that *"the goal is to mitigate
  side-channel attacks."* So: fix it unconditionally — the fix is one call — but in a
  finding, do not promise an exploit you have not demonstrated (principle 3).
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

### 1.1 Constant time is a property of the emitted code, not of the source

The compiler decides whether your fix survives. That is already the accepted rule for
*wiping* — plain `memset` is dead-store-eliminated, which is why `explicit_bzero` /
`sodium_memzero` / `SecureZeroMemory` exist ([`sota-c-cpp` rules/04](../../sota-c-cpp/rules/04-security.md) §4) — and the same
reasoning governs every other constant-time construct, where it is far less widely applied:

- **Secret-dependent `/` and `%` lower to a variable-latency instruction** (x86-64 `IDIV`,
  arm64 `SDIV`) whose timing depends on the operands. The KyberSlash class is exactly this,
  and no amount of source-level care removes it.
- **"I made the divisor a constant so it strength-reduces" is a hope, not a fix.** Whether
  the optimiser turns a constant division into a multiply-shift varies by compiler, target
  *and* optimisation level. Field-reported: one such fix still emitted a real divide at
  **every** level on one target, and at `-Os`/`-Oz` on two others — and `-Os`/`-Oz` are
  levels shipped binaries commonly use.
- **So read the disassembly, across the matrix you actually ship** — each target
  architecture and each optimisation level, built with the toolchain that builds your
  product rather than whichever cross-compiler was convenient. **A clean result proves one
  configuration constant-time, never the code.**
- If you hand-write the multiply-shift, **check it against the original expression over the
  whole input domain**, not over samples: an off-by-a-power-of-two reciprocal agrees for
  millions of inputs before it diverges — the exhaustive-domain case in [`sota-testing`
  rules/06](../../sota-testing/rules/06-property-fuzzing-mutation.md).
- Static inspection of emitted code and **statistical timing measurement of the running
  binary are two different instruments** answering two different questions, and neither sees
  cache or other microarchitectural channels. Say which one you ran, and do not let one
  stand in for the other ([`rules/15`](15-instruments-and-guards.md) §2).
- **Name the instrument when you claim one.** *Dynamic taint:* mark the secret as
  undefined to Valgrind memcheck (`VALGRIND_MAKE_MEM_UNDEFINED`, stock `memcheck.h`), and
  memcheck reports every branch or memory index that depends on it. BoringSSL builds this in
  as `CONSTTIME_SECRET` under `BORINGSSL_CONSTANT_TIME_VALIDATION`. **ctgrind**, which
  introduced the technique, is a patch against Valgrind SVN r11097 and has not been pushed to
  since 2017. Use the stock client request, not ctgrind. *Statistical timing:*
  **dudect** (Reparaz et al., DATE 2017) times two input classes and applies a Welch t-test.
  By its README, |t| above 5 likely means a leak and above 10 is a clear one. A
  low t is evidence for one machine and input distribution, never proof. Both instruments
  see only the configuration they ran on (above).

## Audit checklist

- [ ] **Was every constant-time claim checked in the emitted code (§1.1)**, across the
      architectures and optimisation levels actually shipped — including `-Os`/`-Oz` — rather
      than read off the source? Any secret-dependent `/` or `%` located, and a hand-written
      multiply-shift replacement verified over the whole input domain rather than samples?
- [ ] Are all secret comparisons (tokens, MACs, OTPs) constant-time (§1)? A short-circuit compare is
      MEDIUM, HIGH where it verifies a MAC or signature, or a bearer secret, that an
      unauthenticated caller can submit repeatedly (webhook HMACs, API keys) — the library's one
      rating; language skills point here. Lead list, not verdicts
      (operand names only; each hit needs reading):
      `grep -rniE -e '(^|[^A-Za-z])(mac|signature|sig|digest|token|otp|api_?key|secret|tag)[^=!]{0,40}(===?|!==?)[[:space:]]*[A-Za-z_]|(===?|!==?)[[:space:]]*[A-Za-z_.]*(mac|signature|sig|digest|token|otp|key|secret)|(^|[^_A-Za-z])(memcmp|bytes\.Equal|Arrays\.equals)\(|(key|secret|token|mac|sig|digest)[A-Za-z]*\.equals\(' . | grep -viE -e 'compare_digest|timingSafeEqual|ConstantTimeCompare|MessageDigest\.isEqual|(===?|!==?)[[:space:]]*(null|None|nil|undefined|"")|len\(|\.length|_type|_count'`
      Built on a labelled set (10/10 bad caught across Python, JS, Go, Java and C; 0/11 good
      flagged, including null checks and `CRYPTO_memcmp`; BSD grep and ugrep, 2026-10-13).
      Its precision on real code is unmeasured. Missed: a secret held under a neutral name.
