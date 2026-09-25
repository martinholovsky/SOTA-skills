# 05 — Caching: Hierarchy, Invalidation, Stampedes

A cache is a bet that the past predicts the future, paid for with staleness
and operational complexity. Every cache must declare: what's cached, the key
schema, where it lives, how long it lives, how it's invalidated, what happens
when 10,000 requests miss at once, and how its hit ratio is watched. A cache
missing any of these answers is an incident on a timer.

## 1. The cache hierarchy — place data deliberately

| Layer | Latency | Scope | Coherence | Use for |
|---|---|---|---|---|
| CPU/data layout | ~1–40 ns | core | hardware | rules/03 §4 |
| In-process (map/LRU) | ~100 ns–1 µs | one instance | none across instances | hot config, compiled artifacts, per-entity hot reads |
| Distributed (Redis/Memcached) | ~0.3–1 ms in-DC | fleet-wide | single source | sessions, computed views, API responses |
| CDN/edge | ~5–30 ms to user | global | purge/TTL | static assets, cacheable HTML/API |
| Browser/client | 0 ms (hit) | one user | HTTP semantics | assets, API GETs, app state |

Rules:
- **Cache as close to the consumer as coherence allows.** Each layer down
  adds ~10–1000× latency.
- In-process caches are 100–1000× faster than Redis but multiply staleness by
  instance count and eat heap — use small bounded LRUs with short TTLs
  (1–60 s) for ultra-hot keys, backed by the distributed layer (L1/L2
  pattern). Per-instance hit ratio drops as the fleet scales out; don't expect
  L1 to carry a 200-instance fleet.
- Distributed cache is also a *shared failure domain*: a Redis hiccup becomes
  everyone's latency spike. Set aggressive client timeouts (~50–100 ms) and a
  fallback path; a cache that can take down the service is an availability
  finding, not just perf.
- The browser/CDN layers are governed by HTTP caching headers — get
  `Cache-Control`, `ETag`, and `Vary` right before adding server caches
  (rules/04 §8, rules/06).

## 2. Cache key design

Bad keys cause the two real cache bugs: **wrong data served** (key misses a
dimension) and **hit ratio collapse** (key includes a needless dimension).

- Key = every input that changes the value, and nothing else.
  `user:{id}:profile:v2:{locale}` — entity, qualifier, **schema version**,
  variant dimensions.
- **Version the schema in the key** (`:v2`): deploying a new shape then
  invalidates by abandonment — old keys age out, no purge needed, instant
  rollback (old code still reads `:v1`).
- Normalize inputs before keying: sort query params, lowercase where
  case-insensitive, strip irrelevant params (tracking junk), canonicalize
  `Vary` dimensions. Unnormalized keys fragment one logical value into
  hundreds of entries.
- Never build keys from raw user input without bounding/hashing (cardinality
  explosion + key injection via delimiter characters — hash long/dirty parts).
- Watch cardinality: a key including `user_id × endpoint × locale` may be
  fine; adding `?page&filter&sort` permutations can make every entry
  single-use (hit ratio → 0, memory → full). Audit: top key *prefixes* by
  count and by hit ratio.

## 3. Invalidation strategies

Pick per data class — there is no universal answer, only explicit tradeoffs:

1. **TTL-only**: simplest; staleness bounded by TTL. Right for data where
   bounded staleness is acceptable (prices refresh in 60 s). Wrong alone for
   anything users expect to see change immediately (their own edits).
2. **Write-through / write-invalidate**: on write, update or delete the cache
   entry. **Prefer delete over update** (update races: two concurrent writes
   can land in cache out of order; delete + lazy refill is idempotent).
   Still keep a TTL as backstop — invalidation paths have bugs.
3. **Event-driven**: writes publish invalidation events (or CDC from the DB)
   consumed by cache layers / CDN purge API. Scales to many caches; adds
   pipeline lag (purge latency = staleness window) and a component to monitor.
4. **Versioned/generation keys** (invalidation by abandonment): bump a
   generation counter (`tenant:{id}:gen`) on write; readers include the
   generation in keys. O(1) "invalidate everything for tenant" without
   scanning keys. Costs an extra lookup (cacheable in-process) and leaves
   garbage for LRU/TTL to sweep. CDN equivalent: surrogate keys / cache tags.
5. **Never use wildcard scans (`KEYS pattern*`) for invalidation** in Redis —
   O(N) blocking scan. If you need group invalidation, design for it
   (sets of keys, generations, tags).

**Read-your-own-writes**: after a user mutates data, route their next reads
around the cache (session flag, short-lived bypass) or write-through —
"I edited it and it didn't change" is the most-reported staleness bug.

**Permission and tenancy changes are invalidation events.** A role grant or
revocation, a membership change, or a user moving between tenants must do one
of two things in the same transaction path: purge the keys/tags that hold data
computed under the old permissions, or bump a per-user or per-tenant
*permission version* that is itself a component of those keys (strategy 4
applied to authz). Otherwise an entry filled before a revocation keeps serving
the revoked user until its TTL runs out — a TTL backstop bounds that window, it
does not close it. SSR frameworks expose the same move as tag/path
revalidation (`sota-web-frameworks` rules/03 §4); the session side of a stale
privilege is `sota-code-security` rules/03 §3; §9 covers the key itself.
OWASP: Nextjs Security cheat sheet.

**TTL discipline**: every entry gets a TTL even with active invalidation
(backstop). Choose TTL from a staleness budget ("how stale is acceptable?"),
not vibes. Document it next to the cache code.

## 4. Stampede protection (dogpile)

When a hot key expires (or cache restarts), every concurrent request misses
and hits the origin simultaneously. A 99% hit-ratio cache in front of a DB
sized for 1% traffic produces a 100× origin spike — the cache *caused* the
outage.

Defenses — layer them:

1. **Singleflight / request coalescing** (per instance): first miss computes;
   concurrent misses for the same key wait for that result.

```go
var g singleflight.Group
func Get(ctx context.Context, key string) (Val, error) {
    if v, ok := cache.Get(key); ok { return v, nil }
    v, err, _ := g.Do(key, func() (any, error) {
        val, err := loadFromOrigin(ctx, key)      // exactly one caller runs this
        if err == nil { cache.Set(key, val, ttlWithJitter()) }
        return val, err
    })
    if err != nil { return zero, err }
    return v.(Val), nil
}
```

   JS equivalent: memoize the *promise*, not the value (concurrent callers
   share one in-flight promise; clear on settle/error). Distributed
   singleflight: short-TTL lock key (`SET lock:k token NX PX 3000`), losers
   serve stale or wait briefly.

2. **Jittered TTLs**: identical TTLs synchronize expiry of keys populated
   together (deploy, cache flush, midnight cron). `ttl = base × (0.9 + 0.2 ×
   rand())` (±10%) decorrelates expirations. Apply everywhere by default.

3. **Soft TTL / refresh-ahead (stale-while-revalidate)**: store
   `(value, soft_expiry)` with a longer hard TTL. After soft expiry, serve the
   stale value immediately and refresh asynchronously (one refresher via
   singleflight). Users never wait on origin latency; origin sees ~1 request
   per key per refresh period. This is the SOTA default for hot keys; HTTP's
   `stale-while-revalidate` and CDN request collapsing are the same idea.
   Probabilistic early expiration (XFetch: refresh early with probability
   rising as expiry nears) avoids even the soft-expiry synchronization.

4. **Cold-start protection**: cache warmers for known-hot keys before taking
   traffic; rate-limit/queue origin concurrency (bounded semaphore around
   origin loads) so a cache wipe degrades latency instead of toppling the DB.

Audit shortcut: find the hottest cached key, ask "what happens the instant it
expires under full load?" If the answer is "everyone queries the origin",
that's a High finding regardless of current hit ratio.

## 5. Write strategies and consistency

How writes interact with the cache determines both performance and the bugs
you'll debug at 3 a.m.:

- **Cache-aside (lazy)** — default. App reads cache, on miss loads origin and
  fills; writes go to origin + delete the key. Simple, origin is source of
  truth. Race to know: read-miss loads stale row, a write lands, the stale
  fill overwrites the delete. Mitigate with short TTLs, compare-and-set
  (`SET ... NX` for fills), or version checks on fill.
- **Write-through** — write cache + origin synchronously. Reads never miss
  hot data; writes pay double latency. Use for read-heavy keys with strict
  read-your-writes needs.
- **Write-behind (write-back)** — write cache, flush to origin async. Fastest
  writes, but the cache becomes the durability story: a crash loses acked
  writes. Only with replicated cache tiers and idempotent replay; treat as a
  queue, monitor flush lag. Rarely the right call for business data.
- **Refresh-ahead** — §4.3; reads never pay origin latency for hot keys.

Distributed caches are not transactional with your DB. Any "update DB and
cache together" code has a window where one succeeded and the other didn't —
prefer delete-on-write + TTL, or CDC-driven invalidation, over dual writes.

## 6. Negative caching

Cache "not found" / empty results too — otherwise every lookup for a missing
key (typos, deleted users, enumeration attacks, retry loops on 404s) goes to
origin forever. A miss-storm on nonexistent keys is indistinguishable from a
DoS at the database.

- Store an explicit sentinel (`NOT_FOUND`) — distinguish "cached absence" from
  "cache miss". Don't conflate with `null`/nil returns.
- **Short TTL** (5–60 s): absence changes when the entity is created, and you
  usually have no invalidation event wired for creations. Long negative TTLs
  cause "I just signed up and the site says I don't exist".
- Bound negative-cache memory (attackers can enumerate infinite missing keys):
  separate small LRU, or a Bloom filter of *existing* keys in front of the
  cache for cheap "definitely absent" answers.
- Cache errors with care: brief caching of upstream 5xx (1–5 s) acts as a
  circuit-breaker valve; never cache them as long as successes.

## 7. Metrics — a cache without metrics is unfalsifiable

Track per logical cache (not just per Redis instance):

- **Hit ratio** — but interpret it: 95% hits with a 1 ms origin saves little;
  60% hits with a 2 s origin is gold. The number that matters is
  `misses × origin_cost` (origin offload).
- Origin load with/without cache (what happens if it flushes?).
- Latency of the *cache path itself* (p99 — a slow Redis adds latency to every
  request, hit or miss).
- Eviction rate & memory: high eviction = undersized or key-cardinality
  explosion; near-zero eviction with full memory = TTLs too long.
- Stale-serve rate (if soft TTL) and invalidation pipeline lag (if event-driven).

## 8. When caching is the wrong fix

Caching hides cost; it doesn't remove it. Reach for it after cheaper, more
honest fixes:

- **A missing index is not a caching problem.** A 2 s query that should be
  20 ms with an index gets an index, not a Redis layer. Cache-on-top leaves
  the pathology to detonate on every miss.
- **N+1 is not a caching problem** — batching removes the cost; caching N+1
  multiplies key cardinality and stampede surface.
- **Don't cache cheap things**: if origin cost ≈ cache cost (~sub-ms indexed
  PK lookup vs ~0.5 ms Redis hop in another AZ), you added staleness and an
  invalidation bug surface for zero latency win.
- **Low hit ratios** (< ~50–80% depending on origin cost): per-user
  rarely-repeated data, long-tail key distributions, highly personalized
  responses — the cache is mostly overhead. Compute it cheaper or precompute
  (materialized views, denormalization) instead.
- **Correctness-critical reads** (balances, inventory, auth/permissions):
  staleness is a security/correctness bug. If you must cache authz, keep TTL
  seconds-short and provide kill-switch invalidation.
- **Caching to mask a leak/regression**: if latency degraded recently, find
  the regression; a cache on top converts a visible problem into a latent one.
- Smell: caches added inside the same process directly in front of another
  cache (cache-on-cache) without distinct purpose — usually one layer is
  unmanaged.

Decision order: fix the query/algorithm → batch the calls → precompute on
write → then cache, with the full contract from this file's intro.

## 9. Optimization must not erode security

Caching and other speedups are where security regressions hide — the code
still "works", just for the wrong user:

- **Identity in the key, or no shared cache.** Any authz-sensitive or
  per-user/per-tenant response cached in a shared layer (Redis, CDN, shared
  in-process map) must carry the user/tenant — and role/scope where the value
  varies by it — in the cache key. A key missing the identity dimension serves
  user A's response to user B: a cache-key authorization bypass. Same family
  as web cache deception (sota-code-security rules/05): cacheability must
  never be decided by URL shape alone. Default for personalized responses:
  `Cache-Control: private` at the HTTP layer, identity-scoped keys elsewhere.
  **Declare a sharing scope for every entry** in the key contract (§2):
  `global`, `tenant` or `user`, carried as the key's leading segment
  (`global:…`, `tenant:{tid}:…`, `user:{uid}:…`). A value that is genuinely the
  same for everyone goes under the explicit `global:` prefix, with a one-line
  comment beside the key builder saying why sharing it cannot leak anything —
  so an unprefixed key is visibly undecided, not silently shared. Same
  classification as for stored objects in `sota-architecture` rules/05 §12.
  OWASP: Multi Tenant Security cheat sheet.
- **Key separation is not authorization.** An identity-scoped key keeps one
  principal's entry apart from another's; it says nothing about whether *this*
  request may see the resource. Run the same access check the uncached path
  runs *before* reading a protected value from cache and returning it — a
  handler that returns the cached copy first and authorizes only on a miss
  serves it to a user whose access was revoked, and a key built from a request
  parameter (`user:{id_from_url}:…`) serves the owner's copy to whoever asks —
  an IDOR through the cache (`sota-code-security` rules/03 §2). OWASP: Multi
  Tenant Security cheat sheet.
- **Constant-time comparisons stay constant-time.** Secret/token/MAC checks
  (`hmac.compare_digest`, `crypto.timingSafeEqual`,
  `subtle.ConstantTimeCompare`) are deliberately "inefficient" — "optimizing"
  them into early-exit `==`/memcmp reintroduces the timing oracle. Never flag
  them as a perf finding; never accept a patch that replaces them.
- **Fast paths keep the guards.** Streaming/zero-copy parsing, parallel
  handlers, and request coalescing must preserve the input validation, size
  and recursion limits, and auth checks the slow path performed. An
  optimization PR that touches a validation path needs a security review, not
  just a benchmark.

## Audit checklist

- [ ] Inventory every cache (in-process maps, memoizers, Redis, CDN, HTTP
      headers). For each: key schema, TTL, bound/eviction, invalidation path,
      stampede defense, metrics. Any blank cell is a finding.
- [ ] Unbounded in-process caches (plain `Map`/dict with no LRU/TTL) → memory
      leak (rules/03), High.
- [ ] TTLs constant (no jitter)? Mass-populated keys expiring in sync
      (deploy/cron)?
- [ ] Hot keys: singleflight or soft-TTL in place? What happens on expiry
      under peak load — and on full cache flush/restart?
- [ ] Promise/value memoization in JS: are *errors* cached forever
      (rejected promise never cleared)?
- [ ] Keys: schema-versioned? Inputs normalized? Cardinality bounded?
      User-controlled fragments hashed/escaped?
- [ ] Invalidation: delete-vs-update on writes? TTL backstop present even
      with event-driven purge? Any `KEYS pattern*` scans? Read-your-own-writes
      handled after mutations?
- [ ] Negative caching present for high-miss lookups? Sentinel distinct from
      miss? Short TTL? Bounded against enumeration?
- [ ] Cache client timeouts set (~50–100 ms) and a degradation path if the
      cache tier is down? Or does cache-down = site-down?
- [ ] Hit ratio, eviction rate, and origin offload measured per logical
      cache? Any cache with hit ratio < 50% — should it exist?
- [ ] Any cache papering over an uninvestigated slow query / N+1 / missing
      index? Recommend the honest fix first.
- [ ] Authz/financial data cached? TTL and invalidation justified in writing?
- [ ] Shared-cache keys for per-user/per-tenant responses include the
      identity/tenant (and role where it varies)? Any personalized response
      cacheable by URL alone (cache deception / key bypass —
      sota-code-security rules/05)?
- [ ] Every shared-layer key declares its scope (`global:`/`tenant:`/`user:`
      leading segment, §9), and each `global:` key has a written reason it
      cannot leak? High for an undeclared key holding tenant or user data.
      Lead list (variable keys need their builder read):
      `grep -rniE '(redis|cache|memcached?)[[:alnum:]_]*\.(get|set|setex|mget|hget|hset)\(' . | grep -viE '(global|tenant|user):'`
- [ ] Does any handler return a cached protected value before its access
      check runs (§9 "key separation is not authorization")? High. Flags a
      `return` of cached data with no authz call earlier in the function (an
      authz decorator counts):
      `find . -type f \( -name '*.py' -o -name '*.[jt]s' -o -name '*.go' -o -name '*.rb' -o -name '*.java' \) -exec awk 'FNR==1{s=0;p=0} /(def |function |func )/{s=p;p=0} /(authoriz|permission|can_access|check_access|require_role|enforce\()/{if(/^[[:space:]]*@/)p=1; else s=1} /return.*(cache|hit)/ && !s {print FILENAME":"FNR": "$0}' {} +`
- [ ] Do role, membership and tenancy changes purge the affected keys/tags or
      bump a permission version in the key (§3)? High where authz-derived data
      is cached. Lists change functions with no invalidation call:
      `find . -type f \( -name '*.py' -o -name '*.[jt]s' -o -name '*.go' -o -name '*.rb' -o -name '*.java' \) -exec awk 'function fl(){if(t&&!ok)print fn":"ln": "hd; t=0} FNR==1{fl()} /(def |function |func )/{fl(); if(tolower($0)~/(set|update|assign|grant|revoke|remove|change)_?(user_?)?(role|member|permission|tenant)/){t=1;ok=0;fn=FILENAME;ln=FNR;hd=$0}} t&&/(invalidat|purge|revalidate|perm_?version|cache[[:alnum:]_]*\.(delete|del|unlink))/{ok=1} END{fl()}' {} +`
- [ ] Any optimization that replaced a constant-time compare or relaxed
      validation/size limits for throughput? Treat as Critical, not perf win.
