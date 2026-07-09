# 04 — I/O & Network Performance

Everything crossing the kernel boundary or the wire costs 10³–10⁶× more than
memory work. The strategy is always the same: **fewer, bigger, reused,
concurrent** — fewer round trips, bigger batches, reused connections,
concurrent independent operations.

## 1. Syscalls: batch and buffer

A syscall costs ~100–300 ns plus icache/TLB pollution. Unbuffered I/O turns
one logical write into thousands of syscalls.

```python
# BAD — one write() syscall per line; 1M lines ≈ 1M syscalls ≈ seconds
for line in lines:
    os.write(fd, line.encode())

# GOOD — buffered: ~64 KB per syscall; 1M lines ≈ hundreds of syscalls
with open(path, "w", buffering=1 << 16) as f:
    f.writelines(lines)
```

- Always wrap raw fds/sockets in buffered writers (`bufio.Writer`,
  `BufferedOutputStream`, default Python buffering) — and **flush at
  boundaries** (message end, before fsync, before close). A missing flush is a
  correctness *and* latency bug (data sits in the buffer until it fills).
- Vectored I/O (`writev`/`readv`) sends multiple buffers in one syscall —
  header + body without concatenating.
- `fsync` is the expensive one (~ms on SSD): batch durability points (group
  commit), don't fsync per record unless the contract demands it.
- Reads: read in ≥ 64 KB chunks; `mmap` for large read-mostly files with
  random access; `posix_fadvise`/`readahead` for known sequential scans.
- io_uring (Linux) batches submission *and* completion — relevant for
  syscall-bound services at 10⁵+ IOPS; most apps get 90% of the win from
  plain buffering.

## 2. Zero-copy

Each unnecessary copy burns memory bandwidth and CPU. Classic file-to-socket
path copies 4× (disk→page cache→user→socket buffer→NIC); zero-copy paths skip
the user-space bounce:

- `sendfile()` / `splice()`: serve static files kernel-to-socket. Exposed as
  Go `io.Copy` (uses sendfile/splice when src/dst are *os.File/TCPConn), Java
  `FileChannel.transferTo`, Node `fs.createReadStream().pipe(res)` (still
  user-space but chunked), nginx `sendfile on`.
- Don't read a file into memory just to write it elsewhere; pipe/stream it.
- In-process: pass slices/views (`ByteBuffer.slice`, Go subslices, Rust
  `Bytes`) instead of copying; beware retention (rules/03 §5 Go subslice trap).
- Serialization is the hidden copy machine: JSON encode→string→buffer→socket
  can copy a payload 3–4×. Encoders that write directly to the output stream
  (`json.NewEncoder(w)`, streaming serializers) remove the intermediate
  strings.

## 3. Connection pooling and reuse

A new connection costs: TCP handshake (1 RTT) + TLS handshake (1 RTT on
TLS 1.3, 2 on 1.2) + slow start (small initial congestion window) + server-side
session setup (a Postgres connection fork costs ~ms and ~5–10 MB). Per-request
connections can triple latency and crush the backend.

```javascript
// BAD — new client (and pool) per invocation; handshakes every call,
// leaks sockets under load
async function getUser(id) {
  const client = new pg.Client(cfg); await client.connect();
  const r = await client.query("SELECT ...", [id]); await client.end();
  return r.rows[0];
}

// GOOD — module-level pool, bounded, reused across requests
const pool = new pg.Pool({ ...cfg, max: 10, idleTimeoutMillis: 30_000 });
const getUser = (id) => pool.query("SELECT ...", [id]).then(r => r.rows[0]);
```

- One pooled client per process for each upstream (HTTP client with
  keep-alive, DB pool, Redis client). Grep for `new .*Client(`, `connect(`,
  `createConnection` inside request handlers — finding on sight.
- HTTP: ensure keep-alive is actually on (Node needs an `Agent` with
  `keepAlive: true` pre-v19 defaults; Python `requests.Session` vs bare
  `requests.get`).
- **Bound pools and measure wait time.** Pool too small = invisible queueing
  (saturation); too large = overload the upstream. DB pools: start ~2–4× CPU
  cores of the DB-bound work, verify with pool-wait metrics. Total across all
  instances must fit DB max_connections (use a server-side pooler like
  PgBouncer beyond that).
- Set idle timeouts below any NAT/LB idle cutoff (~350 s on some clouds) and
  enable TCP keepalive, or you'll pay for silently dead connections (first
  request hangs until timeout).

## 4. Round trips, concurrency, and coalescing

In-DC RTT ~0.5 ms; cross-region ~80 ms. Sequential round trips add linearly;
**latency of concurrent calls is the max, not the sum**.

```typescript
// BAD — 3 sequential awaits on independent data: ~3 × RTT
const user = await getUser(id);
const orders = await getOrders(id);
const prefs = await getPrefs(id);

// GOOD — concurrent: ~1 × RTT (max of the three)
const [user, orders, prefs] =
  await Promise.all([getUser(id), getOrders(id), getPrefs(id)]);
```

Same in Python (`asyncio.gather`), Go (errgroup), Java (CompletableFuture /
structured concurrency). **Bound the concurrency** when fanning out over
collections (semaphore / `errgroup.SetLimit` / `p-limit`) — unbounded fan-out
is a self-DDoS.

**Request coalescing / singleflight**: when many concurrent callers need the
same expensive fetch, let one do the work and share the result (Go
`singleflight`, promise memoization in JS, distributed locks). Essential in
front of caches (rules/05 §4) and for config/metadata fetches.

**Pagination over the wire**: offset pagination re-scans O(offset) rows and
skews under concurrent writes; cursor/keyset pagination (`WHERE (created, id)
> ($1, $2) ORDER BY created, id LIMIT $3`) is O(page) at any depth and stable.
APIs: return opaque cursors, enforce max page size, never offer unbounded
`?limit=`. Deep-paging a 10M-row table by offset is a Critical finding on hot
paths.

**Timeouts/retries shape tail latency**: every remote call needs a deadline
propagated end-to-end; retries need backoff + jitter + budget (retry storms
amplify outages); hedged requests (send a second attempt at ~p95) cut tail
latency for idempotent reads at small extra load.

## 5. HTTP/2 and HTTP/3

- **HTTP/1.1**: one request in flight per connection (pipelining is dead) →
  browsers open 6 connections/origin; head-of-line (HoL) blocking at the
  application layer. Domain sharding and asset spriting are obsolete hacks.
- **HTTP/2**: multiplexes streams over one TCP connection, header compression
  (HPACK), stream prioritization. Removes app-layer HoL but keeps **TCP-layer
  HoL**: one lost packet stalls all streams. Use one connection per origin;
  enable on all public endpoints and internal LBs (gRPC requires it).
- **HTTP/3 (QUIC)**: streams over UDP — packet loss stalls only the affected
  stream; 1-RTT handshake combining transport+TLS; 0-RTT resumption;
  connection migration (Wi-Fi↔cellular without reconnect). Biggest wins on
  lossy/mobile/high-RTT networks (typically 5–15% p95 improvement, more at
  p99 on bad networks). Serve via CDN/edge (broad support); advertise with
  `Alt-Svc`.
- Server-internal hops: HTTP/2 (gRPC) for multiplexing; HTTP/3 rarely matters
  in-DC where loss ≈ 0.
- Don't let a proxy downgrade you: check the whole chain (CDN→LB→app) actually
  negotiates h2/h3, not h2 outside and 1.1 inside with per-request connections.

## 6. Compression tradeoffs

Compression trades CPU for bytes. Win condition: `time_saved_on_wire >
compress_time + decompress_time`. Always true cross-internet for text; often
false in-DC on 10 Gbps+ links for already-small payloads.

| Codec | Ratio (text) | Compress speed | Use |
|---|---|---|---|
| gzip -6 | baseline | ~50–100 MB/s | Legacy compatibility |
| brotli -4..5 | ~+10–15% vs gzip | comparable to gzip | Dynamic web responses |
| brotli -11 | ~+20–25% vs gzip | very slow (~1 MB/s) | **Static assets, precompressed at build** |
| zstd -3 (default) | ≈ gzip -6 or better | ~300–500 MB/s | APIs, internal traffic, storage, logs |
| zstd -19 + dict | best-in-class | slow compress, fast decompress | Precompressed artifacts; small payloads w/ dictionary |
| lz4 | lowest | GB/s | In-memory / latency-critical, RPC in-DC |

Rules:
- **Precompress static assets at build time** (brotli -11 + gzip fallback);
  serve with `Content-Encoding` negotiation. Never compress per-request what
  never changes.
- Dynamic responses: brotli 4–5 or zstd 3; gzip 6 as floor. `Accept-Encoding:
  zstd` is now sent by major browsers — support br + zstd + gzip.
- Don't compress: already-compressed media (JPEG/AVIF/WebP/MP4/ZIP — you burn
  CPU for ~0%), payloads < ~1 KB (header overhead, MTU fits anyway).
- zstd **dictionaries** give 2–5× better ratios on small similar payloads
  (per-message JSON/events) — train on a sample, version the dictionary.
- **Compression Dictionary Transport** (RFC 9842: `dcb`/`dcz` encodings,
  `Use-As-Dictionary`/`Available-Dictionary` headers) delta-compresses new
  asset versions against ones the client already cached — big wins on
  frequently redeployed JS bundles and templated HTML. Chromium-only (not
  Baseline); serve as progressive enhancement over the br/zstd/gzip ladder.
- Compression level is a live tuning knob under CPU pressure: dropping a level
  is a cheap capacity lever.
- Security: BREACH-style attacks — don't compress responses mixing secrets
  with attacker-reflected input (or mask tokens).

## 7. TLS efficiency

- TLS 1.3 everywhere: 1-RTT full handshake (vs 2 in 1.2), modern ciphers.
- **Session resumption** (session tickets): returning clients skip the full
  handshake; verify ticket keys rotate and resumption rate is monitored
  (target > 50% on browser traffic).
- **0-RTT early data**: resumed clients send the request in the first flight —
  saves a full RTT. Replay-unsafe: enable only for idempotent GETs and ensure
  the app/CDN rejects 0-RTT for mutations (`Early-Data` header / 425 status).
- OCSP stapling on; certificate chain minimal (every extra cert is bytes in
  the handshake, can overflow initcwnd).
- Internal mTLS meshes: handshake cost × per-request connections is a classic
  hidden tax — pooling (§3) matters double under mTLS.

## 8. CDN strategy

The fastest request is one that terminates ~10 ms from the user instead of
~150 ms.

- **Static assets**: immutable URLs (content hash in filename) +
  `Cache-Control: public, max-age=31536000, immutable`. Cache hit ratio on
  static should be > 95%.
- **Dynamic acceleration**: even uncacheable APIs benefit — TLS terminates at
  edge, long-lived warm connections edge→origin, better congestion control on
  the long haul.
- **Cacheable APIs/HTML**: `s-maxage` +`stale-while-revalidate`; purge by
  surrogate key/tags on writes (rules/05 §3). Short TTL (30–60 s) +
  request collapsing at the CDN shields origins from thundering herds.
- Normalize cache keys (strip marketing query params, normalize
  `Accept-Encoding`) or hit ratio dies of key fragmentation.
- Origin shield / tiered caching: one designated mid-tier reduces origin
  fan-in from hundreds of edge POPs to one.
- Edge compute for personalization-at-edge (rules/06 §7).

## 9. Async runtimes: never block the loop

In Node, Python asyncio, and single-threaded reactors, one blocked event loop
blocks **every** in-flight request.

- Grep for sync APIs on hot paths: Node `fs.readFileSync`, `zlib.gzipSync`,
  `crypto.pbkdf2Sync`, `child_process.execSync`, `JSON.parse` of multi-MB
  bodies; Python `time.sleep`, `requests.*`, blocking DB drivers inside
  `async def`.
- CPU-heavy work (hashing, compression, image resize, big serialization) →
  worker threads / process pool / dedicated service.
- Measure event-loop lag (Node `monitorEventLoopDelay`, asyncio debug slow
  callbacks); p99 loop delay > ~20 ms = something is blocking.
- Sync I/O in threaded runtimes is fine **if** the thread pool is sized for
  the blocking (and bounded); mixing blocking calls into a small shared pool
  (e.g. seda-style executors) causes whole-service stalls.

## Audit checklist

- [ ] Connections/clients created per request anywhere? (`new Client`,
      `connect(` in handlers.) Keep-alive verified on HTTP clients?
- [ ] Pools bounded? Pool wait time and saturation measured? Total
      connections fit upstream limits? Idle timeout < NAT/LB cutoff?
- [ ] Sequential awaits on independent operations? Fan-out concurrency
      bounded?
- [ ] Every remote call has a timeout; retries have backoff + jitter +
      budget; deadlines propagate?
- [ ] Offset pagination on large tables / unbounded page sizes on APIs?
- [ ] Unbuffered writes to files/sockets in loops? Missing flushes? fsync per
      record where group commit would do?
- [ ] Files read fully into memory only to be streamed out (sendfile/pipe
      candidates)? Serializers writing to intermediate strings vs streams?
- [ ] h2/h3 negotiated along the entire chain? gRPC/internal hops multiplexed
      or per-request 1.1 connections?
- [ ] Compression: static precompressed (brotli)? Dynamic on gzip-only when
      zstd/brotli available? Compressing compressed media or < 1 KB bodies?
- [ ] TLS 1.3? Resumption rate monitored? 0-RTT restricted to idempotent
      requests?
- [ ] CDN: immutable hashed assets with long max-age? Cache key normalized?
      stale-while-revalidate / surrogate-key purge in place? Hit ratio known?
- [ ] Any sync/blocking calls reachable from the event loop? Event-loop lag
      measured?
- [ ] Singleflight/coalescing in front of expensive shared fetches?
