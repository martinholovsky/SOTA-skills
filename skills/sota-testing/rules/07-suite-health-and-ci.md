# 07 — Suite Health & CI

A test suite is a production system with an SLO: fast, deterministic signal
on every change. This file is about keeping it one.

## 7.1 Flaky-test policy

A flaky test (same code, different outcomes) is worse than a missing test: it
costs run time, destroys trust in red, and trains retry-until-green — which
also masks *real* intermittent bugs, the most expensive kind.

**The policy (write it down, automate what you can):**

1. **Detect**: track per-test pass/fail history across CI runs (most CI/test
   platforms can; minimum viable = parse JUnit XML into a dashboard). A test
   that fails then passes on retry with no code change is flagged
   automatically.
2. **Quarantine within a day, not debate**: move the flagged test to a
   non-blocking quarantine lane (still runs, never gates merges). Quarantine
   entry REQUIRES: a ticket, an owner, and an **expiry date** (e.g. 14–30
   days). The worst steady-state is a permanent quarantine pile — that's
   deleting tests with extra steps.
3. **Root-cause with the taxonomy** — the fix differs by class:
   - **Ordering/isolation**: passes alone, fails in suite (shared state,
     leaked globals, DB residue). Fix via `rules/02` §2.5 / `rules/03` §3.6.
     Repro: run shuffled / run the failing pair alone.
   - **Async/race**: fixed sleeps, unawaited promises, racing a spinner,
     assertion before settle. Fix via `rules/02` §2.6, `rules/05` §5.3.
   - **Time**: real clocks, midnight/DST/month boundaries, timeout tuned to
     a fast machine. Fix: inject clock; never assert wall-clock durations.
   - **Infra/environment**: port collisions, disk full, container pull
     flakes, third-party sandbox blips. Fix in harness/CI, not the test.
   - **Test bug**: nondeterministic data (unseeded random, map ordering),
     overspecified assertion. Fix the test.
   - **Real bug**: the code IS intermittently wrong (race in prod code).
     The flake was the alarm — escalate, don't quarantine the alarm.
4. **At expiry**: fixed and re-promoted, or deleted with rationale. No third
   state.
5. **Retries**: at most one auto-retry, with both outcomes recorded and
   feeding the detector. Retry-to-green WITHOUT tracking is the suite
   silently rotting; blanket `retries: 3` to "stabilize CI" is a High
   finding wherever you see it.

```python
# BAD — permanent amnesty; nothing tracks it, nothing expires it
@pytest.mark.flaky(reruns=3)
def test_checkout_updates_inventory(): ...

# GOOD — quarantined: out of the gate, owned, dated, classified
@pytest.mark.quarantine(ticket="QA-1432", owner="payments-team",
                        expires="2026-07-01", cause="async")  # CI fails the
def test_checkout_updates_inventory(): ...                    # build past expiry
```

## 7.2 Coverage philosophy

Coverage measures what tests *execute*, not what they *verify* (an
assertion-free test covers everything it touches — `rules/02` §2.7; mutation
testing measures verification — `rules/06` §6.3).

- **Use coverage as a gap-finder**: the uncovered-lines report on YOUR diff
  is genuinely useful — it shows the error path you forgot. Read it per-PR.
- **Branch coverage over line coverage** where the tooling offers it: line
  coverage credits `if err != nil` lines without ever taking the branch.
- **Never set a global percentage target.** Goodhart's law is undefeated:
  targets manufacture assertion-light tests on easy code while risky code
  stays bare. 80% chosen-by-committee says nothing — the *which* 20% is
  everything.
- **Ratchet instead of threshold**: fail CI only if coverage *decreases*
  (with small tolerance), or apply a diff-coverage rule ("changed lines ≥ X%")
  so the bar applies to new work without backfill theater. Ratchets create
  pressure exactly where code is being touched.

```text
BAD:  fail_under = 80            # global target → gamed on easy code,
                                 # ignored on risky code, fought at 79.9
GOOD: diff-coverage: changed lines >= 85% branch coverage   AND
      ratchet: total branch coverage >= last main build - 0.1%
      (stored number auto-raises; lowering it requires a reviewed commit)
```
- Exclude generated/vendored code from measurement; measuring it inflates
  the number and buries the signal. Same for the environment-bound shell that
  unit tests cannot drive (GUI, device, process-spawn adapters) — but the fix
  there is architectural: make that boundary explicit and keep it thin
  (`sota-architecture` rules/02 §14), then measure the core.
- **Rank the gaps by risk, not by size of deficit.** Coverage alone cannot say
  where the next test belongs. Cross it with complexity: a module that is both
  **branch-dense and thinly covered** is the highest-value target, and the
  composite (complexity weighted by how little of it is verified) ranks work
  better than either number alone. A 200-branch payment router at 50% is a
  finding; a 3-line getter at 0% is not. Use the ranking to aim mutation runs
  (`rules/06` §6.3) and review attention — as a *pointer*, never as a gate,
  or it becomes the same Goodhart target as a coverage threshold.
- Reporting coverage in PRs: show the uncovered lines, not just the delta
  percentage — reviewers act on lines, not numbers.

## 7.3 Speed budgets

Slow suites change behavior: engineers batch changes, skip running tests
locally, and context-switch during CI — each worse for quality than any
individual missing test.

Set explicit budgets per layer and enforce them like perf SLOs:

- **Unit suite**: fast enough to run on every save for the module you're
  editing (sub-second per module; whole unit suite minutes at most, fully
  parallel).
- **PR pipeline (test stages total)**: ~10 minutes wall-clock is the
  long-standing target that keeps PRs flowing; parallelize/shard to hold it
  as the suite grows rather than letting it drift to 40.
- **Track the top-10 slowest tests** per suite (every runner can emit
  timings) and treat a new entrant like a perf regression: push it down a
  layer, fix its waits, or justify it.
- Standard speed sinks, in order of yield: hard sleeps (`rules/02`/`05`),
  per-test container/app boot instead of per-suite (`rules/04` §4.1),
  serialized DB tests that could namespace, e2e tests that should be API
  tests, unbatched fixture I/O.
- **Nightly is not a landfill**: slow-but-valuable jobs (long PBT runs, fuzz,
  mutation, full-matrix, soak) belong post-merge/nightly — but each needs an
  owner who triages failures next morning, or it's a dead letter queue.

## 7.4 Parallelization correctness

Parallel execution is the main speed lever and the main isolation auditor —
a suite that can't run parallel is telling you it has shared state.

- **Design for parallel from test #1**: unique-per-test data (`rules/03`
  §3.6), no fixed ports (ask the OS for ephemeral ports / let the container
  lib assign), no shared temp paths (per-test temp dirs from the framework),
  no env-var mutation without scoped isolation (process-level env is shared
  across threads — prefer config injection over env mutation entirely).
- **Know your runner's model** (process-per-worker vs threads vs both —
  detail in language skills) — "thread-safe enough" fixtures that share a
  DB schema across workers serialize or corrupt. Pair worker-scoped
  resources (one schema per worker) with test-scoped isolation inside them.
- **Singletons and static caches** in production code surface here: if the
  SUT caches global state, tests must be able to construct isolated
  instances. "Reset the singleton between tests" is a workaround; injectable
  construction is the fix.
- Verify continuously: run shuffled AND parallel in CI (`rules/02` §2.5).
  Failures unique to parallel runs are isolation bugs, never "just rerun".

## 7.5 CI sharding and pipeline shape

- **Shard by measured timing, not file count**: balanced shards by recorded
  per-test duration keep the long pole short; naive alphabetical splits give
  you one 12-minute shard and five 2-minute ones. Most ecosystems have
  timing-based splitters; persist timing data between runs.
- **Stage by speed and signal**: lint/type/unit first (fail in 2 min),
  integration next, e2e last (or post-merge beyond the smoke set —
  `rules/05` §5.7). A pipeline that runs e2e before unit wastes its fastest
  signal.
- **Test selection** (running only tests affected by the diff) is a real
  lever in monorepos — build-graph based selection (Bazel-style, Nx-style)
  is reliable; heuristic selection needs a periodic full run as a safety
  net (e.g. full suite on merge to main, selected on PR).
- **The merge queue / main must run the full blocking suite.** Skipping on
  "it passed on the PR branch" breaks under concurrent merges (semantic
  conflicts between independently-green PRs).
- Cache dependency/image layers, never test *results* across code changes
  unless keyed by a content hash you trust (build systems that hash inputs
  may; hand-rolled "skip if green yesterday" may not).

## 7.6 Failure triage discipline

A red main/merge-queue is a site incident for the team's delivery:

- **Red main stops the line**: fix-forward or revert within a defined window
  (e.g. 30 min); reverting an innocent-looking PR is cheaper than a day of
  everyone rebasing onto broken.
- **Every CI failure gets classified**, even (especially) the rerun-and-it-
  passed ones: real bug / flaky test / infra. The classification feeds the
  flake detector (7.1) and the infra backlog. "Reran, green, moved on" with
  no record is how suites rot invisibly.
- **Failure output must be diagnosable from CI alone**: assertion diffs, SUT
  logs, artifacts (`rules/05` §5.7). A failure that requires local repro to
  understand multiplies triage cost by 10.
- **Don't normalize deviance**: a permanently-yellow optional job, a
  `continue-on-error` on a once-important suite, a skipped-tests count
  drifting upward (`grep -rc 'skip\|xfail\|todo(' tests/` trending) — each
  is a finding. Skips need the same ticket+expiry discipline as quarantine.
- Weekly suite-health review (10 min): flake list vs expiry, slowest-10,
  quarantine size, skip count, coverage ratchet position. Suites stay
  healthy by inspection, not by hope.

## Audit checklist

- [ ] Is there a written flaky-test policy with quarantine + expiry? No
      policy and visible retry-to-green culture → High.
- [ ] Blanket retries? Grep CI/test config:
      `retries:|retry:|jest.retryTimes|flaky|rerun-fails|--retry` without
      per-test tracking/tickets → High.
- [ ] Quarantine pile: how many tests are quarantined/skipped and how old?
      Grep `skip|xfail|disabled|@Ignore|\.todo|t\.Skip` with `git blame` on a
      sample; skips >90 days with no ticket → Medium each, pattern → High.
- [ ] Coverage gating: hard global threshold (`fail_under|coverageThreshold`
      with a flat number) and evidence of gaming (assertion-light tests on
      trivial code) → Medium; ratchet/diff-coverage instead → good.
- [ ] Is generated/vendored code excluded from coverage? Check coverage
      config excludes vs `*_pb2.py|.pb.go|generated|vendor` → Low.
- [ ] Does the measured scope match the testable core, or does an
      environment-bound shell (UI, device, process-spawn adapters) sit in the
      denominator? Whole-tree measurement with an untestable region →
      Low–Medium (the number is noise; fix the boundary, `sota-architecture`
      rules/02 §14).
- [ ] Are coverage gaps prioritized against complexity (branch-dense +
      thinly-covered first), or is the backlog being worked by whatever moves
      the percentage fastest (trivial modules) → Medium (effort aimed at the
      metric, not the risk).
- [ ] Pipeline timing: PR wall-clock now vs 6 months ago (CI history). >15
      min and growing with no sharding/selection plan → Medium.
- [ ] Slowest tests known? Runner timing reports enabled and reviewed? No
      timing visibility → Low; top test >60s in the unit lane → Medium.
- [ ] Parallel + shuffled in CI? Config shows `-shuffle|--randomize|-p auto|
      --parallel|maxWorkers` in the blocking lane; serial-only suite for
      speed reasons → Medium (isolation debt).
- [ ] Fixed ports/paths blocking parallelism? Grep
      `:8080|:5432|/tmp/test|port = [0-9]{4}` literals in tests → High.
- [ ] Shards balanced by timing? One shard consistently 3× the others in CI
      history → Low–Medium (rebalance).
- [ ] Does main/merge-queue run the full blocking suite? PR-only testing
      with merge-queue skips → High.
- [ ] Red-main discipline: recent history of main staying red >1 day →
      High (process, not code).
- [ ] Nightly jobs owned? Long-running suites whose failures nobody triages
      (check last 10 nightly failures for follow-up) → Medium (dead letter
      queue).
