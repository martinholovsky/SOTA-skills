# 18 — Tamper-Evident Logs & Audit Ledgers

Scope: hash-chained audit logs, compliance trails, agent/action ledgers, signed receipts —
anything claiming "tamper-evident", "audit-grade" or "immutable". Split out of rules/04
(formerly section 8) on 2026-09-25; the section is now §1. Maps to NIST AU-9/AU-10.

Core principle: **integrity and completeness are separate claims, and an unkeyed chain
proves neither against an attacker with write access.** Primitive choice (HMAC, signatures)
stays in rules/04.

## 1. Tamper-evident logs & audit ledgers (NIST AU-9/AU-10)

Applies to anything claiming "tamper-evident", "audit-grade", or "immutable"
records: hash-chained audit logs, compliance trails (EU AI Act Art. 12, FINRA
4511 WORM), agent/action ledgers, signed receipts.

- An **unkeyed hash chain** (each record carries the previous record's SHA-256)
  detects accidental corruption and naive edits only — an attacker with write
  access to the store recomputes every hash and forges a clean chain. Integrity
  against an adversary needs a key or an anchor: HMAC/sign entries with a key
  held outside the store's trust domain, and/or periodically **anchor the chain
  head externally** (signed checkpoints, RFC 3161 timestamps, forward to
  WORM/SIEM, transparency-log publish).
- **Tail truncation is invisible** to chain-walk verification — deleting the
  newest N records leaves a perfectly valid chain; so does deleting an entire
  chain/stream. Detection needs an externally recorded head (hash + count),
  signed close markers, or an out-of-store registry of chains.
- **A partitioned chain must chain its partitions.** Ledgers get segmented for
  ordinary operational reasons — fixed-size epochs to bound an index, daily
  partitions, rotated files, a re-shard — and the obvious implementation starts
  each segment fresh with `prev_hash = NULL`. Deleting an entire *interior*
  segment is then undetectable: both sides of the hole verify clean and the new
  first record looks like a legitimate start. Carry the previous segment's head
  hash into the first record of the next, and have the verifier carry its
  running hash **across** the boundary instead of resetting at it — the defect
  is usually in the verifier, not the writer, which makes it a `rules/15` §3
  guard-shaped bug rather than a crypto bug. Deletion has three geometries and a
  chain walk covers only two: interior record (caught by the `prev_hash`
  mismatch), interior segment (caught **only** with boundary continuity), tail
  or whole stream (never caught by a walk — needs the external head above).
- Hash **every field you attest** — including server-assigned timestamps and
  anything used to order or attribute records. Unhashed "projection" columns
  can be rewritten without breaking the chain.
- The preimage must be a canonical, unambiguous encoding (rules/04 §7) — and "canonical"
  has to name a **spec**, not an intention: RFC 8785 (JSON Canonicalization
  Scheme, June 2020, Informational) or a written encoder with its key sort,
  number format, string escaping and null/absent handling pinned. It fails in
  two directions and most guidance states only the first. **Forgery:**
  delimiter-joined concatenation of attacker-influenced fields is breakable by
  field-boundary shifting. **False alarm:** a language's default map/JSON
  encoder is not a canonical encoder — Go's spec says "the iteration order over
  maps is not specified and is not guaranteed to be the same from one iteration
  to the next", Elixir's `Map` documentation says "key-value pairs in a map do
  not follow any order", and an implementation may change that order with size
  as the map switches internal representation; float formatting, unicode
  escaping and implicit numeric→string conversion vary the same way. Identical
  data then hashes to different bytes, and the ledger reports tamper on records
  nobody touched. That is the more dangerous direction operationally: an
  integrity alarm that is wrong on ordinary traffic gets muted or ignored, and a
  muted alarm is an inert control (rules/10). Pin the encoding with a
  **known-answer test vector** committed as a fixture and reproduced by every
  implementation — without one, the off-system verifier required below is just a
  second implementation free to disagree with the first, and `chain broken` will
  not say which of them is wrong.
- **Integrity ≠ completeness.** A chain proves what was *delivered*, not what
  *happened*: records dropped before ingestion (client buffers, "never raise"
  SDKs, server-assigned sequence numbers) leave no gap. If completeness is a
  claim, attest it separately (source-assigned sequence numbers, declared
  counts, close markers) and report the two verdicts separately.
  **A TEE does not fix this** — a common and expensive wrong turn. Confidential
  computing protects a record's confidentiality and integrity *once it exists*;
  no hardware can compel a component to emit one. "Never recorded" is a
  **liveness** failure, and liveness sits explicitly outside the CC guarantee:
  the host may refuse to schedule, pause, or destroy the enclave at will
  (`sota-confidential-computing` rules/01 §2, availability row; rules/04 §7
  states that any design assuming a TEE guarantees liveness is wrong). The fix is
  the separate completeness attestation above, taken at a vantage the monitored
  component does not control — see the vantage bullet below.
- Verification must be possible **off the system that stores the data**
  (standalone verifier + a documented, cross-language canonicalization spec).
  A `verify` that only runs on the server being audited proves little.
- Vantage matters: a record emitted voluntarily by the monitored component can
  be omitted at will — for security evidence prefer an independent chokepoint
  (proxy, gateway, kernel, append-only sink). See sota-detection-engineering
  rules/02 (telemetry integrity).
- Immutable/append-only stores holding personal data need erasure designed up
  front — per-subject crypto-shredding (sota-privacy-compliance rules/03 §4);
  retrofitting deletion breaks either the chain or the law.

## Audit checklist

- [ ] Is any "tamper-evident"/audit ledger keyed (HMAC/signature) or externally anchored — not a bare unkeyed hash chain — with tail truncation and whole-stream deletion detectable?
- [ ] Is ledger completeness attested separately from integrity (source-assigned seq / close markers), and is verification possible off the storing system?
- [ ] If the ledger is segmented (epochs, daily partitions, rotated files), does the first record of each segment chain to the previous segment's head **and** the verifier carry its running hash across the boundary — demonstrated against a fixture with one whole interior segment removed?
