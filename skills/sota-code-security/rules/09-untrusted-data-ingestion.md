# 09 — Untrusted Data Ingestion

Scope: safely ingesting attacker-authored external data — threat-intel feeds,
scraped content, user uploads, third-party webhooks/APIs, RAG corpora, email,
file imports — through parsers into storage and UI. This file is about hostile
data *feeds and content*, where the bytes themselves are the weapon: hostile
parsers (image/archive/PDF/Office/XML/CSV), resource-exhaustion at the ingest
boundary, schema validation, feed provenance, and the render/LLM exits. Maps to
OWASP A08:2025 (Software or Data Integrity Failures), A05:2025 (Injection),
A04:2025 (Insecure Design). CWE-409, CWE-776, CWE-434, CWE-22, CWE-502, CWE-1333.

This is **not** rules/01 (injection at a *sink* — SQL/shell/path/template) nor
rules/05 (encoding at the *render* sink). Those fix the moment data meets an
interpreter. This file fixes the moment hostile data *enters the system* — the
parse and the pipeline before any sink is reached.

Core principle: **all externally-sourced data is attacker-controlled — including
data from "trusted" partners, paid feeds, and your own collectors.** A partner's
breach is your poisoned feed; a scraper ingests whatever the page author wrote;
a webhook claims to be from Stripe until you verify it. Establish a taint mark at
the ingest boundary and carry provenance forward: who sourced it, was integrity
verified, has it been validated. Ingested data is **data forever** — it never
silently becomes instructions (HTML when rendered, SQL when queried, a prompt
when retrieved). Untrusted in → typed/validated/provenanced out, or quarantined.

## 1. Treat the ingest boundary as a trust boundary

- Every collector, webhook handler, upload endpoint, feed poller, email fetcher,
  and RAG loader is a trust boundary, on par with an HTTP handler. Apply rules/01
  validation discipline here, plus the parse-and-resource controls below.
- **Provenance/taint from ingest onward.** Tag each record with `source`,
  `fetched_at`, `integrity_verified: bool`, `validated: bool`. Downstream code
  must be able to ask "where did this come from and was it checked" — don't merge
  untrusted records into the trusted core unlabeled.
- **"Trusted partner" is not a control.** Authenticate the *transport* (mTLS,
  signed webhook, API key) but still treat the *payload* as hostile — auth proves
  who sent it, not that the contents are benign. A compromised partner sends
  authenticated poison.
- Never trust client-declared metadata: `Content-Type`, filename extension,
  `Content-Length`, charset. Determine these from the bytes, then compare.

```python
# BAD: webhook authenticated, payload trusted blindly
if hmac_ok(req): db.save(json.loads(req.body))   # unbounded parse, no schema

# GOOD: authenticate transport, then treat payload as hostile
if not hmac_ok(req): raise Forbidden()
raw = read_limited(req.stream, MAX_BODY)          # §3 size cap
rec = WebhookEventDTO.model_validate_json(raw)    # §4 parse-don't-validate
store(rec, source="stripe-webhook", integrity_verified=True, validated=True)
```

## 2. Hostile parsers — sandbox them (the big one)

Format parsers are the largest ingest attack surface: complex state machines in
C/C++ (image codecs, PDF, archive libs) with a long CVE history, plus
algorithmic-complexity bombs that need no memory-safety bug at all. **Parse
untrusted formats in a sandboxed subprocess with CPU/mem/wall-time/FD limits and
a hard recover — never in-process in a long-running service.** See
sota-sandboxing for process/app isolation (seccomp, Landlock, namespaces,
cgroups, broker pattern); the parser sandbox must reach **no secrets and no
network** (egress controls per sota-network-security).

- **Images — decompression / pixel bombs (CWE-409).** A 4 KB PNG can declare
  50000×50000 pixels and explode to gigabytes on decode. **Read dimensions via a
  header-only decode (`DecodeConfig`) and reject before the full `Decode`.** Cap
  width×height×bytes-per-pixel against a memory budget. Strip/re-encode through a
  hardened path; never feed raw uploads to image libs in-process.

```go
// BAD: decode first, OOM second
img, _, err := image.Decode(r)

// GOOD: header-only dimension check, then bounded decode
cfg, _, err := image.DecodeConfig(io.LimitReader(r, 64<<10))
if err != nil { return err }
if cfg.Width*cfg.Height > 24_000_000 { return ErrTooLarge }  // ~24MP cap
img, _, err := image.Decode(io.LimitReader(r, 16<<20))       // bounded body
```

- **Archives — zip/tar slip, zip bombs, nested amplification (CWE-22, CWE-409).**
  Validate every entry path post-join and reject absolute/`..`/symlink entries
  (Zip Slip — see rules/01 §4). Independently of count, enforce a **decompressed-
  size cap and a compression-ratio cap** (e.g. reject >100:1 or >total budget) by
  metering bytes *as you stream the inflate*, not by trusting the header. Cap
  entry count and recursion depth — a 42 KB zip-of-zips ("42.zip") expands to
  petabytes; refuse to recurse into nested archives, or bound depth to 1.

```python
# GOOD: meter decompressed bytes during extraction, cap ratio + total
total = 0
with zipfile.ZipFile(fp) as z:
    if len(z.infolist()) > MAX_ENTRIES: raise Reject("too many entries")
    for info in z.infolist():
        dest = safe_join(base, info.filename)        # rejects ../ + absolute
        with z.open(info) as src, open(dest, "wb") as out:
            while chunk := src.read(64 * 1024):
                total += len(chunk)
                if total > MAX_TOTAL: raise Reject("zip bomb")
                if info.compress_size and total / info.compress_size > 100:
                    raise Reject("ratio bomb")
                out.write(chunk)
```

- **PDF / Office (CWE-434, RCE surface).** These are containers of scripts, fonts,
  embedded files, and zipped XML. Office docs (DOCX/XLSX/PPTX) are zipped XML —
  XXE/XEE applies (rules/01 §6). Disable macro/JS execution; never hand a document
  to a full renderer in-process. Render/convert in a sandboxed worker; extract
  only the fields you need; treat embedded objects as new untrusted uploads.
- **XML (CWE-776, CWE-611).** Disable DTDs and external entities; cap entity
  expansion (billion-laughs). Full treatment in rules/01 §6 — applies to every
  SVG, RSS/Atom feed, SOAP, SAML, and Office part.
- **CSV / JSON / feed formats.** Deeply-nested JSON (`[[[[…]]]]`) is a stack/CPU
  DoS — set a max nesting depth and document/field size cap; reject unbounded
  arrays before materializing. Use streaming parsers with limits for large feeds.
  CSV formula injection (CWE-1236) is an *export* concern handled at the render
  boundary (§7), but neutralize on ingest too if cells round-trip to users.
- **Fuzzy-hash / similarity libs on hostile input.** ssdeep/tlsh/imagehash and
  similar are fed exactly the malware/spam they analyze; malformed input crashes
  or OOMs them. Run them inside the same parser sandbox, time-bounded, with the
  crash isolated to the worker — never on the request thread of a shared service.

## 3. Resource & DoS controls at the ingest boundary

The cheapest attack on an ingester is volume and amplification. Bound everything.

- **Size caps at every layer**: max request body, max field length, max file size,
  max decompressed size, max entry count. Use a `LimitReader`/bounded reader on
  the raw stream — never read an attacker-controlled `Content-Length` into a
  buffer, and never `read()`/`ReadAll` an unbounded body.
- **Timeouts and rate/volume limits**: wall-clock timeout per parse; per-source
  rate and concurrency limits so one feed can't starve others. See
  sota-async-concurrency for bounded concurrency, backpressure, and task limits.
- **Backpressure, not buffering**: when downstream is slow, slow the intake;
  don't accumulate an unbounded in-memory queue (itself a DoS).
- **Dead-letter / quarantine poison records.** A record that fails parse,
  validation, or a resource cap goes to a quarantine/DLQ with its provenance —
  it does not crash the pipeline, retry-loop forever, or get silently dropped.
- **Idempotent re-ingest.** Key records by a stable source id so replays and
  retries don't duplicate or corrupt state (cross-ref sota-data-engineering data
  contracts; idempotency in rules/01-adjacent webhook handling and sota-api-design).

```go
// BAD                              // GOOD
body, _ := io.ReadAll(r.Body)       body, err := io.ReadAll(io.LimitReader(r.Body, maxBody))
                                     if err != nil || int64(len(body)) >= maxBody { reject() }
```

## 4. Schema & content validation at the boundary

- **Parse, don't validate.** Deserialize into a typed object (pydantic / serde /
  zod / a generated struct) at the boundary, with `extra=forbid` /
  reject-unknown-fields / `deny_unknown_fields`. Unknown fields are an attack
  signal and a mass-assignment vector (rules/07) — reject, don't ignore.
- **Allowlist** values, formats, ranges, enums. **Canonicalize then validate**
  (rules/01 §1) — normalize unicode/encoding once before checking.
- **Strip/flag invisible and deceptive Unicode** on text bound for an LLM context
  or a UI (RAG-corpus and feed text especially): zero-width characters
  (U+200B–200D, U+FEFF), bidirectional overrides (U+202A–202E, U+2066–2069 —
  *Trojan-Source*, CVE-2021-42574), and tag characters (U+E0000–E007F) hide
  injected instructions a reviewer can't see. Normalize (NFKC), drop the
  format/control categories you don't expect, and flag homoglyph-heavy strings.
  This is the ingest-side complement to the prompt-injection boundary (rules/08).
- **Determine type from bytes, not declaration.** Sniff the real MIME from magic
  bytes and reject when it disagrees with the declared/extension type. Beware
  **polyglot files** (valid GIF *and* valid HTML/JS — "GIFAR"): a file that is two
  types at once defeats single-type checks and becomes stored XSS when served.
  Re-encode/normalize through a canonical pipeline so the stored artifact is
  exactly one known type.
- **Content scanning for uploads (CWE-434).** Run AV/malware scanning on uploaded
  files; store under a server-generated id (never the user filename, rules/01 §4);
  serve from a separate origin/sandbox domain with `Content-Disposition:
  attachment` and a correct `Content-Type` (upload pipeline detail in rules/05).
- Reject before persistence. Invalid data must never reach storage in a form that
  a later, less-careful reader will trust.

```python
# GOOD: typed boundary, unknown fields rejected, type from bytes
class FeedItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str; indicator: IPvAnyAddress; severity: Literal["low","med","high"]

item = FeedItem.model_validate(record)                 # reject-unknown, typed
if sniff_mime(blob) not in ALLOWED_MIME: raise Reject  # bytes, not declared
```

## 5. Pipeline trust hygiene

- **Per-feed provenance + integrity.** Where a feed offers signatures/checksums
  (signed STIX/TAXII, detached signatures, content digests), verify them and
  record the result; an unsigned feed is lower-trust and labeled as such. A
  poisoned upstream feed is a **supply-chain attack on your data** — the same
  class as a malicious dependency (cross-ref sota-devsecops for provenance, and
  sota-data-engineering for data contracts and quality gates).
- **Separate ingest/parse from the trusted core (broker pattern).** A small,
  unprivileged front layer fetches and parses in the sandbox; only typed,
  validated, provenanced objects cross into the core over a narrow interface. The
  parser process holds **no secrets, no DB credentials, no network egress** beyond
  what it strictly needs — apply egress allowlists on collectors per
  sota-network-security.
- **Detection on the ingest path.** Anomalies — sudden volume spikes, ratio-bomb
  rejects, schema-violation bursts, AV hits — are signals; emit them as events for
  sota-detection-engineering, don't just drop them.
- **No lateral trust.** Data validated for one purpose isn't validated for
  another; re-validate at each new boundary it crosses (a value safe for storage
  may be unsafe for a shell, a query, or a prompt — see §6).

## 6. The exits — render and LLM boundaries

Ingested hostile content is inert in storage; it becomes dangerous at an *exit*.
Two exits matter beyond rules/01's sinks:

- **Render boundary → stored XSS (CWE-79).** Scraped pages, feed descriptions,
  uploaded SVGs, webhook payloads displayed in a dashboard are stored-XSS fuel.
  Encoding/sanitization happens at render time, in the render context — see
  rules/05 and sota-frontend-design / sota-javascript-typescript. Sanitizing on
  ingest is brittle (you don't know the future render context); store the raw
  (taint-tagged) value and encode at output. SVG and HTML feed content in
  particular must be sanitized or served from an isolated origin.
- **LLM boundary → indirect prompt injection.** Any ingested content that reaches
  a model's context — RAG corpora, scraped pages, emails, tool outputs — is
  attacker-controlled instructions to the model. This is rules/08's domain
  (indirect prompt injection, lethal trifecta, taint gating); the ingest pipeline
  enforces the *provenance tag* that rules/08 uses to gate tool calls. Never let
  ingested text be treated as a trusted system instruction.

## Audit checklist

- [ ] Is every collector/webhook/upload/feed/RAG loader treated as a trust boundary with size cap, timeout, and schema validation?
- [ ] Are records tagged with provenance (source, fetched_at, integrity_verified, validated) and is "authenticated transport" not conflated with "trusted payload"?
- [ ] Are untrusted formats parsed in a sandboxed subprocess (CPU/mem/time/FD limits, no secrets, no egress) rather than in-process in a long-running service?
- [ ] Image decode: header-only dimension check (`DecodeConfig`) and pixel/byte budget *before* full `Decode`? (grep: `image.Decode`, `Image.open`, `imread` without a preceding dimension/`DecodeConfig` check)
- [ ] Archive extraction: per-entry path validation (no `..`/absolute/symlink), decompressed-size cap, compression-ratio cap, entry-count cap, bounded nesting depth? (grep: `zipfile`, `tarfile`, `extractall`, `archive/zip` without a metered byte counter)
- [ ] PDF/Office parsed in a sandboxed worker with macros/JS disabled, embedded objects treated as new uploads, and zipped-XML parts XXE-hardened?
- [ ] XML/SVG/RSS/SAML/Office parsers: DTDs + external entities disabled, entity expansion capped? (rules/01 §6)
- [ ] JSON/CSV/feed: max nesting depth, document/field size caps, unbounded arrays rejected, streaming parser for large inputs?
- [ ] Fuzzy-hash/similarity libs (ssdeep/tlsh/imagehash) run inside the parser sandbox, time-bounded, crash-isolated?
- [ ] Is every raw read bounded by a `LimitReader`/bounded reader? (grep: `io.ReadAll`, `read()` with no limit, `request.body` without size cap, missing `LimitReader`)
- [ ] Backpressure + bounded concurrency + per-source rate limits, with a dead-letter/quarantine for poison records and idempotent re-ingest?
- [ ] Parse-don't-validate into typed objects with reject-unknown-fields, allowlist values, canonicalize-then-validate?
- [ ] Upload type determined from magic bytes (not declared Content-Type/extension), polyglots rejected via re-encode/normalize, AV scan, server-generated storage id, isolated serving origin?
- [ ] Feed integrity verified where available (signatures/checksums), poisoned-upstream treated as a supply-chain risk, ingest/parse separated from the trusted core (broker pattern)?
- [ ] Ingested content encoded at the *render* boundary (rules/05) not sanitized-on-ingest, and provenance-tagged before reaching an LLM context (rules/08)?
- [ ] Ingest anomalies (volume spikes, ratio-bomb/schema-violation bursts, AV hits) emitted as detection events?
