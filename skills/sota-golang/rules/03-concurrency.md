# 03 — Concurrency: goroutines, channels, sync, races

Concurrency bugs are the most expensive class of Go defect: they pass review,
pass tests, and corrupt data or leak memory in production. The discipline is
ownership: every goroutine, channel, and shared variable has exactly one
defined owner and lifecycle.

## 1. Goroutine lifecycle ownership

**Before writing `go`, answer three questions in code, not in your head:**

1. **When does it exit?** (ctx canceled, input channel closed, work done)
2. **How do we wait for it?** (`errgroup.Wait`, `sync.WaitGroup`, join channel)
3. **Where does its error/panic go?** (errgroup, error channel, recover+log)

If any answer is "it doesn't / we don't", that's a leak by design — HIGH.

```go
// BAD — fire-and-forget: no exit signal, no join, error lost
go processQueue(q)

// GOOD — owned: bounded by ctx, joined, error surfaced
g, ctx := errgroup.WithContext(ctx)
g.Go(func() error { return processQueue(ctx, q) })
// ...
if err := g.Wait(); err != nil { ... }
```

- **A panic in any goroutine kills the process** — goroutines running
  panic-capable code (callbacks, plugins, parsers on untrusted input) need
  their own `defer func(){ if r := recover(); ... }()`.
- Libraries must not spawn goroutines that outlive the call unless the API
  has an explicit `Close`/`Shutdown` that joins them.
- Never use `time.Sleep` to "wait for the goroutine to start/finish" — that's
  a race with a timer on it. Synchronize with channels/WaitGroup. In tests on
  1.25+, `testing/synctest` gives you a fake-time bubble instead of sleeps.

## 2. Goroutine leak catalog

Each pattern below leaks the goroutine (and everything it references) forever.

**Blocked send, receiver gone** — classic in "first result wins" and timeouts:

```go
// BAD — if caller times out, the worker blocks on send forever
func fetch() chan result {
    ch := make(chan result)
    go func() { ch <- slowCall() }() // leak when nobody receives
    return ch
}

// FIX — buffer of 1 (send always completes) or select on ctx.Done()
ch := make(chan result, 1)
// or:
select {
case ch <- slowCall():
case <-ctx.Done():
}
```

**Forgotten receiver / abandoned range** — producer ranges forever on a
channel nobody closes, or consumer ranges a channel whose producer errored
out before closing:

```go
// BAD — if produce() returns early on error without close(ch), this blocks forever
for v := range ch { ... }

// FIX — producer owns the channel: defer close(ch) unconditionally
go func() {
    defer close(ch)
    for _, v := range items {
        select {
        case ch <- v:
        case <-ctx.Done():
            return
        }
    }
}()
```

**Missing ctx cancellation** — goroutine blocks on I/O or a channel with no
`<-ctx.Done()` branch. Every blocking select in a spawned goroutine must
include the done channel.

**`time.After` in a loop** — pre-1.23, each call allocates a timer not
collected until it fires; in a hot select loop this is unbounded memory.
Since Go 1.23 unreferenced timers are collectable, so it's no longer a leak —
but it still allocates per iteration; `time.NewTimer` + `Reset` or
`time.Tick`/`time.NewTicker` remains correct for loops:

```go
// BAD (pre-1.23 leak; ≥1.23 still allocates per iteration)
for {
    select {
    case m := <-in:
        handle(m)
    case <-time.After(timeout):
        return
    }
}

// GOOD
t := time.NewTimer(timeout)
defer t.Stop()
for {
    select {
    case m := <-in:
        handle(m)
        t.Reset(timeout)
    case <-t.C:
        return
    }
}
```

**Detection**: goroutine count metric (`runtime.NumGoroutine`) trending up;
`pprof/goroutine?debug=2` dumps; `goleak` (`go.uber.org/goleak`) in tests:
`defer goleak.VerifyNone(t)` — make it standard in packages that spawn.
Go 1.26 adds an experimental `goroutineleak` pprof profile
(build with `GOEXPERIMENT=goroutineleakprofile`, fetch
`/debug/pprof/goroutineleak`) that reports goroutines blocked on unreachable
concurrency primitives — planned on-by-default in 1.27; use it where available.

## 3. Channels vs mutexes

Decision rule: **mutex for state, channels for handoff/signaling.**

- Protecting a map/counter/struct field → `sync.Mutex`/`RWMutex`. A channel
  "manager goroutine" for simple state is slower, harder to read, and
  deadlock-prone.
- Transferring ownership of data, pipelines, fan-out/fan-in, completion
  signals, semaphores → channels.
- If you're tempted by both, the simpler mutex wins.

Channel rules:

- **The producer (writer) closes; never the consumer.** Closing is a
  broadcast: "no more values". Send on closed channel panics; close of closed
  channel panics; receive from closed channel returns zero immediately —
  `v, ok := <-ch` to distinguish.
- Multiple producers: nobody closes directly; coordinate via a `sync.WaitGroup`
  + a single closer goroutine, or signal with a separate `done` channel.
- Buffer sizes are 0 (synchronization), 1 (async handoff/notification), or a
  measured capacity (bounded queue). Any other magic number needs a comment;
  "buffered so it probably won't block" is a latent leak — MEDIUM.
- `nil` channel in select disables that case — idiomatic for toggling cases
  off, surprising otherwise:

```go
// Idiomatic: disable send case once drained
var out chan<- Item
if len(pending) > 0 { out = outCh } else { out = nil }
select {
case out <- pending[0]: ...
case v := <-in: ...
}
```

- Don't use channels as mutexes (`make(chan struct{}, 1)` as a lock) unless
  you need ctx-aware locking (`select` on acquire) — then comment it.

## 4. sync primitives

- **`errgroup` is the default for fan-out** (`golang.org/x/sync/errgroup`):
  first error cancels the derived ctx, `Wait` joins and returns it,
  `SetLimit(n)` bounds concurrency. Prefer it over hand-rolled
  WaitGroup+error-channel every time:

```go
g, ctx := errgroup.WithContext(ctx)
g.SetLimit(8)
for _, u := range urls {
    g.Go(func() error { return fetch(ctx, u) }) // 1.22+: u is per-iteration
}
if err := g.Wait(); err != nil { return err }
```

- **WaitGroup pitfalls**: `Add` before `go` (never inside the goroutine —
  race with `Wait`); never copy a WaitGroup (pass pointer; vet `copylocks`
  catches it); don't reuse before `Wait` returns. Go 1.25 adds `wg.Go(fn)`
  which does Add/Done correctly — prefer it where available.
- **`sync.Once`** for lazy init; `sync.OnceValue/OnceValues/OnceFunc` (1.21+)
  are cleaner. Beware: if the once-fn panics, Once is consumed — subsequent
  calls return without retrying. For retryable init, use mutex + done flag.
- **`sync.RWMutex`**: only when profiling shows read contention; RLock is not
  free and write starvation is real. Default to plain Mutex.
- **`sync.Map`** is a niche tool (append-mostly caches, disjoint key sets);
  a mutex-guarded map is the default and is type-safe.
- **`atomic`**: use the typed API (`atomic.Int64`, `atomic.Bool`,
  `atomic.Pointer[T]`) — it can't be misused with mixed atomic/non-atomic
  access the way `atomic.AddInt64(&x, 1)` on a plain int can. Atomics are for
  counters/flags; multi-field invariants need a mutex.
- **Never copy a struct containing a mutex/WaitGroup/Cond** after first use —
  methods needing the lock take pointer receivers; `go vet` `copylocks`.

## 5. Data races

A data race is undefined behavior in Go — not "stale reads", actual memory
corruption is possible (interface values, slice headers, maps).

- **Race detector in CI, always**: `go test -race ./...`. Run race-enabled
  binaries in staging/canary if feasible (`go build -race`, ~2-10x CPU,
  5-10x memory). A `-race` report is CRITICAL — there are no benign races.
- **Loop variable capture**: since Go 1.22 (`go 1.22`+ in go.mod), `for`
  variables are per-iteration — the classic `go func(){ use(v) }()` bug is
  fixed *only if* the module's `go` directive is ≥1.22. Auditing a module
  with `go 1.21` or lower: every closure over a loop variable is suspect
  (HIGH). Check `go.mod` first.
- **Concurrent map access**: unsynchronized read+write throws
  `fatal error: concurrent map writes` (unrecoverable, no recover) — or
  worse, races undetected. Any map reachable from multiple goroutines needs a
  mutex or redesign.
- **Lazy "checked" init** (`if m == nil { m = make(...) }` from multiple
  goroutines), bool flags as ad-hoc signaling, and stat counters
  (`count++`) are all races even when "writes are rare".
- HTTP handlers run concurrently: any handler touching shared server fields
  without sync is racy — top audit target.

## 6. Bounding concurrency: pools and semaphores

**Unbounded `go` per work item is a self-DoS** (memory, FD, downstream
overload). Bound everything fed by external input.

- First choice: `errgroup` with `SetLimit` (above).
- Channel semaphore when you need ctx-aware acquire or weighted slots
  (`golang.org/x/sync/semaphore` for weights):

```go
sem := make(chan struct{}, maxInFlight)
for _, job := range jobs {
    select {
    case sem <- struct{}{}:
    case <-ctx.Done():
        return ctx.Err()
    }
    go func() {
        defer func() { <-sem }()
        process(ctx, job)
    }()
}
```

- Worker pool (long-lived workers + job channel) only when worker setup is
  expensive (per-worker connections, caches) or you need strict FIFO; for
  plain throughput bounding, errgroup is less code and self-draining:

```go
jobs := make(chan Job)
g, ctx := errgroup.WithContext(ctx)
for range numWorkers {
    g.Go(func() error {
        for j := range jobs {
            if err := handle(ctx, j); err != nil { return err }
        }
        return nil
    })
}
// feed then close — producer owns the channel
go func() { defer close(jobs); for _, j := range all { jobs <- j } }()
err := g.Wait()
```

- GOMAXPROCS: 1.25+ respects container CPU quotas automatically; on older
  runtimes in containers, `go.uber.org/automaxprocs` or explicit setting
  prevents throttling-induced latency.

## Audit checklist

- [ ] **go.mod language version — decides loop-var semantics (HIGH if <1.22 with closures in
      loops)** — `grep -E '^go ' go.mod`
- [ ] **Fire-and-forget goroutines — review each: exit path? join? error?** —
      `grep -rn 'go func' --include='*.go' . | grep -v _test.go` ;
      `grep -rnE '^\s*go [a-zA-Z]' --include='*.go' .`
- [ ] **Goroutines without ctx plumbed (manual: does the func take/select on ctx?)** —
      `grep -rn -A3 'go func()' --include='*.go' . | grep -L 'ctx'`
- [ ] **time.After in loops — MEDIUM (HIGH pre-1.23)** —
      `grep -rn -B5 'time.After' --include='*.go' . | grep -E 'for |select'`
- [ ] **Unbounded fan-out: go inside range — HIGH if input is external** —
      `grep -rn -B2 'go func' --include='*.go' . | grep 'for .*range'`
- [ ] **WaitGroup misuse: Add inside goroutine, copied WG** —
      `grep -rn -A2 'go func' --include='*.go' . | grep 'wg.Add'` ; `go vet ./...` (copylocks,
      loopclosure (pre-1.22))
- [ ] **Raw atomic on plain ints (prefer atomic.Int64 types)** —
      `grep -rnE 'atomic\.(Add|Load|Store|Swap)(Int|Uint|Pointer)' --include='*.go' .`
- [ ] **sync.Map usage — verify it matches its niche** —
      `grep -rn 'sync.Map' --include='*.go' .`
- [ ] **Consumer-side close, double close candidates** — `grep -rn 'close(' --include='*.go' .`
      (verify producer owns each)
- [ ] **Sleep-based synchronization — MEDIUM (flaky + racy)** —
      `grep -rn 'time.Sleep' --include='*.go' . | grep _test.go`
- [ ] **Race detector + leak detection — non-negotiable** — `go test -race ./...` ;
      `go test -race -count=5 ./...` (shake out flaky interleavings);
      `grep -rn 'goleak' --include='*_test.go' .` (present in goroutine-spawning pkgs?)
- [ ] **Runtime evidence (live systems)** —
      `curl -s localhost:6060/debug/pprof/goroutine?debug=2 | head -100`

Severity guide: confirmed race CRITICAL; goroutine leak / unbounded fan-out
on request path HIGH; missing `-race` in CI HIGH; `time.After` loop MEDIUM;
hand-rolled errgroup-equivalent LOW.