# 02 — Algorithmic & Data-Structure Performance

Complexity bugs are the only perf bugs that get *worse* on their own: traffic
doubles, data doubles, and O(n²) quadruples. They hide behind innocent-looking
one-liners. This file catalogs the patterns to write and the signatures to hunt.

## 1. N+1 anything

The N+1 pattern is one operation to fetch a list, then one operation *per
element*. It applies to DB queries, HTTP calls, cache gets, file reads, and
RPC — any boundary with per-call overhead.

```python
# BAD — 1 + N queries; 200 orders ≈ 201 round trips ≈ 200+ ms
orders = db.query("SELECT * FROM orders WHERE user_id = %s", uid)
for o in orders:
    o.items = db.query("SELECT * FROM order_items WHERE order_id = %s", o.id)

# GOOD — 2 queries total, regroup in memory
orders = db.query("SELECT id, ... FROM orders WHERE user_id = %s", uid)
items = db.query("SELECT ... FROM order_items WHERE order_id = ANY(%s)",
                 [o.id for o in orders])
by_order = group_by(items, key=lambda i: i.order_id)   # O(N) hash regroup
for o in orders: o.items = by_order.get(o.id, [])
```

Variants to recognize:
- **ORM lazy loading** in a loop (`order.items` triggering a query per access).
  Fix: eager loading (`select_related`/`prefetch_related`, `includes`,
  JPA fetch joins) or a dataloader.
- **HTTP N+1**: calling a microservice per item. Fix: batch endpoint
  (`GET /users?ids=1,2,3`), or GraphQL dataloader pattern (collect IDs within
  one tick, issue one batched fetch).
- **Cache N+1**: `cache.get(key)` per item over the network. Fix: `MGET` /
  pipelined multi-get.
- **N+1 writes**: INSERT per row. Fix: multi-row INSERT / `COPY` / bulk APIs —
  typically 10–100× faster.

Detection by reading: any loop body containing `await`, `query`, `fetch`,
`get`/`post`, `client.`, or an ORM relationship access. Detection by measuring:
queries-per-request metric; test assertion on query count.

## 2. Accidental quadratic

O(n²) created by composing two O(n) things. The code reads as linear.

**String building in a loop** (immutable strings copy on every concat):

```java
// BAD — O(n²): each += copies the whole accumulated string
String csv = "";
for (Row r : rows) csv += r.toLine() + "\n";

// GOOD — O(n)
StringBuilder sb = new StringBuilder(rows.size() * 64); // pre-size
for (Row r : rows) sb.append(r.toLine()).append('\n');
```

Same trap: Python `s += chunk` in a loop (use `''.join(parts)` or
`io.StringIO`), JS heavy `+=` in hot loops (use `parts.push(...); parts.join('')`),
Go `s += x` (use `strings.Builder`), repeated list concatenation
(`list = list + other` vs `extend`), `array.unshift`/`list.insert(0, x)` in a
loop (O(n) per op → O(n²); use append + reverse, or a deque).

**Linear scan inside a loop** — `O(n·m)` that should be `O(n+m)`:

```javascript
// BAD — for 10k users × 10k allowed ids = 10⁸ comparisons (~seconds)
const active = users.filter(u => allowedIds.includes(u.id));

// GOOD — build the hash set once: ~20k operations (~ms)
const allowed = new Set(allowedIds);
const active = users.filter(u => allowed.has(u.id));
```

Signatures: `.includes(`, `.indexOf(`, `in some_list`, `.find(` / `.filter(`,
`array_search`, `list.count(x)`, `.contains(` on a List — *inside another
loop or array method*. The fix is almost always: hoist a `Set`/`Map`/dict
built once, O(1) lookups after.

**Other quadratic generators:**
- Sorting or deduplicating inside a loop (`sort()` per iteration).
- `dict(list)` rebuilt per call instead of cached.
- Nested ORM/collection traversal: `for a in A: for b in a.related_b_filtered_in_python`.
- Recomputing an aggregate per element (`sum(items)` inside `for item in items`)
  — use a running total or prefix sums.
- Regex with catastrophic backtracking (`(a+)+$`) — exponential, not even
  quadratic; user-controlled input + nested quantifiers = ReDoS finding (High).
- Deep-copying or JSON-serializing a growing accumulator every iteration.

**Threshold guidance:** n ≤ 100 with no growth path: leave linear scans alone —
a linear scan over 32 elements often beats a hash map (cache locality, no
hashing cost). n is user-data-sized or grows with the business: fix on sight.

## 3. Choose structures by access pattern

| Need | Structure | Cost |
|---|---|---|
| Membership / lookup by key | Hash set/map | O(1) avg; no ordering |
| Lookup + ordered iteration / range queries | B-tree / skip list / sorted structure (`TreeMap`, `BTreeMap`, `sorted containers`) | O(log n) |
| Min/max repeatedly | Heap | O(log n) push/pop; beats re-sorting |
| FIFO / both-ends ops | Deque / ring buffer | O(1); never `shift()` an array |
| Top-K of huge stream | Bounded heap of size K | O(n log K), constant memory |
| Append-heavy, index access | Dynamic array | amortized O(1) append |
| Many membership checks, some false positives OK | Bloom/cuckoo filter | O(1), ~10 bits/elem |
| Prefix search | Trie / sorted array + binary search | — |
| Counting distinct at scale | HyperLogLog | KBs for billions |

Hash vs tree decision: need range scans, ordered traversal, floor/ceiling, or
predictable worst-case (no rehash spikes, adversarial keys)? → tree (O(log n)).
Pure point lookups → hash. At n < 10³ the difference rarely matters; at n > 10⁶
or in a hot loop, it defines the design. Also note constant factors: hash maps
cost a hash + probe (~20–50 ns); arrays with linear scan win below ~50 elements.

Hidden costs to know:
- Rehash/resize spikes: pre-size hash maps and arrays when the size is known
  (`make(map, n)`, `new ArrayList<>(n)`, `dict` over-allocation is automatic).
- Hashing long strings is O(len): hashing 1 KB keys in a hot loop is the work.
  Intern or pre-hash hot keys.
- `LinkedList` is almost never the answer: O(n) cache-hostile traversal loses
  to array shifting in practice for all but huge mid-list insert workloads.

## 4. Hidden complexity in innocent calls

Library calls have complexity classes too; they just don't print them.

| Call | Hidden cost |
|---|---|
| `list.remove(x)` / `array.splice(i,1)` | O(n) scan + O(n) shift |
| `len(set(a) & set(b))` per pair in a loop | rebuilds sets every iteration |
| `sorted(x)[0]` / `.sort()` then take first | O(n log n) for an O(n) `min` |
| `Object.keys(obj).length` in a loop (JS) | allocates the key array each time |
| `str.split()` / regex compile inside loop | recompiled/re-allocated per iteration — hoist `re.compile`/`Pattern.compile` |
| `LinkedList.get(i)` in an indexed loop (JVM) | O(n) per get → O(n²) loop |
| `in` on a Python list / `.contains` on List | O(n) — use set/dict |
| Spread-accumulate `acc = [...acc, x]` / `{...acc}` in reduce (JS) | copies accumulator per element → O(n²); mutate or push |
| `COUNT(*)` per item, `EXISTS` in app loop | a query per element — batch with `GROUP BY`/`ANY` |

**Top-K / partial results**: need the 10 largest of 10M? `heapq.nlargest`,
`partial_sort`, `select_nth` — O(n log K) instead of full O(n log n) sort.
Need "is there at least one match?" — short-circuit (`any`, `LIMIT 1`),
don't count or materialize everything.

**Precompute and reuse across iterations**: anything loop-invariant (compiled
regex, parsed config, dictionary built from a constant list, formatted
prefix) hoists out. Memoize pure expensive functions with *bounded* caches
(see [rules/05](05-caching.md) for eviction discipline).

## 5. Batching

Per-operation overhead (syscall, RTT, transaction, lock acquisition) amortizes
over batch size. Throughput scales until the batch's marginal cost dominates.

- **Batch the boundary, not the CPU**: batching matters where each op carries
  fixed overhead — network, disk, locks, GPU kernel launches.
- Typical wins: multi-row INSERT 10–100× vs row-at-a-time; Redis pipeline of
  100 commands ≈ 1 RTT instead of 100; `writev` over 100 `write` calls.
- **Bound batches** by count AND bytes AND time (e.g. "≤ 500 items, ≤ 1 MB, or
  every 50 ms, whichever first"). Unbounded batching trades latency and memory
  for throughput and breaks tail latency.
- Amortize, don't serialize: batch building must not add a full batch-interval
  to p99 of latency-sensitive paths — use small time windows (1–10 ms) or
  opportunistic batching (take whatever is queued now, send immediately).

## 6. Streaming vs materializing

Materializing = build the entire result in memory, then process/send.
Streaming = process elements as they arrive, O(1)–O(batch) memory.

```python
# BAD — loads every row into memory; 10M rows × 1 KB = 10 GB, OOM
rows = cursor.fetchall()
return json.dumps([transform(r) for r in rows])

# GOOD — constant memory, first byte leaves immediately
def generate():
    yield '['
    for i, r in enumerate(cursor):          # server-side cursor / chunked fetch
        yield (',' if i else '') + json.dumps(transform(r))
    yield ']'
return StreamingResponse(generate())
```

Stream when: result size is unbounded or user-controlled; the consumer can
start before the producer finishes (time-to-first-byte matters); data passes
through (file upload → object storage; DB → CSV export). Use: generators,
async iterators, Node streams with `pipeline` (backpressure handled), Go
`io.Reader` chains, SAX/streaming JSON parsers for huge documents.

Materialize when: you need multiple passes, sorting, or random access; data is
known-small; retry semantics require buffering anyway.

**Backpressure is part of the design**: a fast producer + slow consumer +
unbounded queue = memory leak. Use bounded channels/queues and blocking or
shedding when full.

## 7. Move work out of the hot path

When an operation is both necessary and expensive, relocate it in time:

- **Precompute on write** (read-heavy data): maintain the aggregate/denormalized
  view as writes happen (counter columns, materialized views, search indexes)
  instead of computing per read. One O(1) update per write beats O(n) per read
  when reads ≫ writes.
- **Defer off the request path**: anything the user doesn't need in the
  response (emails, analytics, thumbnail generation, fan-out) goes to a queue.
  Request latency = critical path only.
- **Incremental over recompute**: update running totals/deltas rather than
  rescanning; cache invalidation by dependency rather than recompute-all.
- The inverse also holds: don't precompute combinatorial spaces "just in case"
  (precompute cost × cardinality must beat lazy compute × actual hit count).

## 8. Database quick pointers

Detailed rules live in the **[sota-databases](../../sota-databases/SKILL.md)** skill; in a perf audit, flag
these on sight:

- **N+1 queries** — §1 above. The #1 real-world perf bug.
- **Missing indexes**: any `WHERE`/`JOIN`/`ORDER BY` column on a large table
  without a supporting index → full scan. Verify with `EXPLAIN (ANALYZE)`;
  look for `Seq Scan` on big tables, `rows` estimates in the millions.
- **`SELECT *`**: drags unneeded (possibly TOASTed/large) columns over the
  wire, defeats covering indexes, breaks when schema grows. Select named
  columns on hot paths.
- **Chatty transactions**: many small queries + app think-time inside one
  transaction → locks held for the round-trip sum, pool exhaustion under load.
  Keep transactions short, no external calls inside them, batch the reads.
- **Unbounded queries**: no `LIMIT` on list endpoints; `OFFSET` pagination on
  deep pages (O(offset) per page) → use keyset/cursor pagination.
- **Pool sizing**: connections per instance × instances > DB max_connections
  is an outage; pool too small is artificial saturation — measure pool wait.

## Audit checklist

- [ ] Grep loop bodies for I/O: `await`, `fetch`, `query`, `exec`, `.get(`,
      `client.`, ORM relation access → N+1 candidates (High on hot paths) (§1).
- [ ] Grep for `+=` on strings, `concat`, `unshift`, `insert(0,` inside
      loops → accidental quadratic (§2).
- [ ] Grep for `.includes(`, `.indexOf(`, ` in [`/`in list`, `.find(`,
      `.contains(` inside loops/`.filter` → O(n·m); recommend Set/Map hoist (§2).
- [ ] Any sort, dedupe, aggregate, deep copy, or serialization recomputed
      per-iteration (§2)?
- [ ] Hidden complexity in library calls (§4): lead list
      `grep -rnE 'sorted\(.*\)\[0\]|\.sort\(.*\)\[0\]|\[\.\.\.acc,|\{\.\.\.acc,' --include='*.py' --include='*.js' --include='*.ts' .`
      — a full sort to take one element, or a spread accumulator copied per
      element in `reduce`. Then read loop bodies for `list.remove`/`splice`,
      a regex compiled or a string split per iteration, `LinkedList.get(i)`, and
      a count or full materialization where `any`/`LIMIT 1` would short-circuit.
      Inside a loop over growable n → flag (Medium): hoist loop invariants, use
      `min`/a bounded heap, mutate the accumulator.
- [ ] Regexes on user input with nested quantifiers/backreferences →
      catastrophic backtracking risk: a ReDoS finding (High) (§2).
- [ ] Collections pre-sized where final size is known? Rehash/regrow in hot
      loops? Structure matches the access pattern — hash for point lookups,
      tree for range/ordered/floor-ceiling, heap for repeated min/max, deque or
      ring buffer for FIFO (an array `shift()` in a loop → flag), bounded heap
      for top-K? `LinkedList` on a hot path → flag (§3).
- [ ] `fetchall()` / `findAll()` / `.ToList()` / reading whole files where the
      result is unbounded → demand streaming or LIMIT (§6).
- [ ] Writes performed row-at-a-time where bulk APIs exist (§1, §5)?
- [ ] Batch jobs bounded by count, bytes, and time (§5)? On a
      latency-sensitive path, is the batch window small (1–10 ms) or
      opportunistic, not a full interval added to p99? Queues bounded with
      backpressure — blocking or shedding when full (§6)?
- [ ] Work off the hot path (§7): does a request handler do work its response
      does not need — email, analytics, thumbnail generation, fan-out — before
      returning? Lead list:
      `grep -rnE 'send_?mail\(|sendEmail\(|smtplib|\.track\(|thumbnail' --include='*.py' --include='*.js' --include='*.ts' --include='*.rb' --include='*.go' --include='*.java' .`
      then confirm the call sits on the request path → flag (Medium): queue it.
      Also flag an O(n) aggregate recomputed on every read of read-heavy data
      (precompute on write, or update incrementally), and a combinatorial space
      precomputed with no measured hit count.
- [ ] DB: EXPLAIN available for hot queries — any `Seq Scan` on a big table?
      `SELECT *`, missing LIMIT, OFFSET pagination, long transactions with app
      logic or external calls inside? Pool size × instances > DB
      `max_connections` (§8)?
- [ ] For every flagged loop: what is realistic production n? Document the
      math (n × per-op cost) in the finding; n ≤ 100 with no growth path →
      leave the linear scan alone (§2).
