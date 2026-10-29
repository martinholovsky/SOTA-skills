# 16 — Fast CI without blind spots: measure, cache, scope, parallelise

Scope: making a pipeline faster without making it see less. A slow pipeline gets worked
around (batched changes, skipped local runs, a gate quietly removed), so speed is part of a
gate holding ([rules/05](05-analysis-gates.md) §5.8: "every gate over ~10 minutes generates
organizational pressure to remove it"). But every speed lever here also has a way to make a
required check pass without running. This file is the levers with their failure modes side by
side. What a suite should contain and how to shard tests by timing is
[`sota-testing` rules/07](../../sota-testing/rules/07-suite-health-and-ci.md) §7.3 and §7.5;
cache *security* is [rules/01](01-pipeline-security.md) §1.6; deploy concurrency is §1.9 there.
The platform facts below are GitHub Actions', read from GitHub's documentation on
2026-10-28; other CI systems have the same failure modes under other names, so check yours.

## 16.1 Measure before you optimise

Read the time per job **and per step** across enough runs to have a median, and find the
critical path: the chain of jobs the run's wall-clock actually waits on. Queue time (created to
started) is a separate number and has a separate fix (runner capacity, not the pipeline).

```bash
# per job and per step for one run; repeat over N runs for a median
gh api "repos/OWNER/REPO/actions/runs/RUN_ID/jobs?per_page=100" \
  --jq '.jobs[] | [.name, .created_at, .started_at, .completed_at] | @tsv'
```

Measured on this library's own CI (2026-10-28, the latest 40 runs of `ci.yml`, `gh run list --limit 40`): a PR run's median was 18.1 minutes,
and **one step was 15.3 of them**: a harness that ran 129 probes serially, each a full run of a
44-check gate. Every other job took about a minute, so dependency caching would have saved
seconds; the lever was the repeated unit, not the installs. Optimising without this table
tunes whatever is most familiar. When one unit runs N times, a second off the unit is N
seconds off the run: this repo's earlier speed-up made the gate itself faster and proved the
change with a byte-identical differential over 12 trees (CHANGELOG 1.44.1, 2026-09-24: that job went from 7.5–8.7 to 2.9 minutes).

## 16.2 Cache inputs that are expensive to fetch, keyed on what determines them

CI caching starts here, and each concern has a home: trust boundaries, poisoning and
`cache-mode` are [rules/01](01-pipeline-security.md) §1.6; verifying a restored dependency is
[rules/04](04-build-containers.md) §4.1, and BuildKit cache mounts are §4.2; caching test results
is [`sota-testing` rules/07](../../sota-testing/rules/07-suite-health-and-ci.md) §7.5, whose exception for a
hand-built cache is below. Keys, partial restores, hit counts and reusing a gate's own pass are
this section; shared compiler, layer and remote build caches are §16.2a.

- **What to cache:** dependency downloads, toolchains and compiler caches, keyed on a hash of
  what determines them (the lockfile, the toolchain file). A key that omits an input serves a
  stale artifact as if it were current.
- **A partial restore is not a hit.** `actions/cache` sets `cache-hit` to `true` only for an
  exact match on `key`, and `false` when the restore came through `restore-keys`; its README
  recommends installing missing or updated dependencies on a partial match. A step skipped on
  `cache-hit` also skips the frozen install's verification, so a restored directory is trusted
  on its key alone ([rules/04](04-build-containers.md) §4.1: "a CI cache restore is matched on
  its key").
- **Never cache a verdict** across code changes unless a build system you trust keys it on
  the content hash of every input ([`sota-testing` rules/07](../../sota-testing/rules/07-suite-health-and-ci.md) §7.5), or
  a hand-built reuse meets every condition in the next bullet.
- **Reusing a gate's own pass** (a local or self-hosted runner that skips a gate whose inputs
  match an earlier pass) is that verdict cache built by hand, so it carries the whole burden
  itself. It is acceptable only when every condition below holds; with any one missing it is
  "skip if green yesterday":
  - **The key is every input, byte for byte**: the tracked tree plus untracked and generated
    files the gate reads; the toolchain and tool binaries; container image digests; environment
    variables and config read from outside the tree (`$HOME`, global tool config); the gate's
    own arguments; and any host input it exercises, such as the kernel for a gate that loads
    code into it. A file is left out only when a recorded file-access trace or a build
    system's declared inputs shows the gate never reads it, and the runner refuses an exclusion
    with no such record behind it; a hand-kept exclusion list drifts as the code moves (§16.3).
  - **A gate whose verdict depends on what the key cannot capture is never reused**: a remote
    database, the network, the clock or randomness; a gate that has flaked is never reused
    either. Advisory, licence and scanner gates are the common case, since their database
    changes while the tree does not.
  - **A pass expires** a stated number of days after the run that actually executed the gate (a
    week is a reasonable default), and reusing it never renews it, so an input the key missed is
    wrong for a bounded time.
  - **Trusted paths rerun everything**: a tag, publish, sign or deploy job, and the merge queue
    or default branch, refuse a record that reused any gate (§16.3: a scoped run needs an
    unscoped one behind it).
  - **Records cross no trust boundary**: a pass recorded by lower-trust code (a PR, a fork, a
    shared runner) is never reused by a higher-trust job ([rules/01](01-pipeline-security.md) §1.6).
  - **Reuse is visible**: the run prints which gates it reused and the record names them, so a
    reused pass is never read as a fresh one.
  - **The cache has known-bads**: a self-test changes one input from each class above (a
    tracked file, the toolchain, an image digest, an environment variable, a host input) and
    asserts the gate runs again each time; another adds a file the gate does read to the
    exclusion and asserts the exclusion check refuses it ([rules/09](09-gates-that-hold.md) §2).
- **Count the hits.** Print `cache-hit` or the tool's own hit statistics in the job log; a cache
  that never hits costs an upload per run and saves nothing. The `actions/cache` README at
  v6.1.0 states a per-repository cap with eviction of entries unused for a week, so a key that
  churns evicts the entries that would have hit.
- **Trust boundaries come first.** The default branch's cache is readable from other branches,
  so a cache a PR can write must never reach a release or signing job ([rules/01](01-pipeline-security.md) §1.6,
  `cache-mode`).

## 16.2a Shared build caches: compiler, image layer and remote

A compiler cache (ccache, sccache), a BuildKit layer cache exported with `--cache-to`, and a
remote build cache (Bazel, Gradle, Nx) all store **outputs**, and a later build links or ships
them without rebuilding. So whoever can write the cache chooses what other builds contain.
GitHub's dependency-caching reference calls this cache poisoning: an untrusted run could
"write a malicious cache that a later, more privileged workflow restores and trusts", and
"Cache contents are not signed or verified". CVE-2025-36852 is the published case: with a
self-hosted Nx remote-cache plugin (a bucket or a shared filesystem), any contributor with
pull-request privileges could inject compromised artifacts, because the first write to a key
wins.

- **Only trusted CI writes; everything else reads.** Each tool has a read-only switch, and the
  vendors recommend it: Bazel ("You may want only your CI system to be able to write to the
  remote cache"; clients set `--remote_upload_local_results=false`), Gradle (remote push is
  off by default; CI populates the cache "while developers only load from it", and a PR job must
  not count as the CI server that pushes), Nx Cloud ("Use a read-write token only on protected
  branches"; it is not in the CVE's affected list; a self-hosted Nx cache gives PR jobs
  read-only storage credentials), sccache (`SCCACHE_GHA_RW_MODE=READ_ONLY`, or
  `SCCACHE_S3_NO_CREDENTIALS` for "a readonly cache for pull requests", which needs a publicly
  readable bucket, so the cache contents are public), ccache (a `read-only` property on a
  `remote_storage` entry) and BuildKit's `gha` backend (in
  read-only workflows "keep `cache-from: type=gha` and omit `cache-to`"). A pull request, a
  fork and a developer machine are readers. The trust rules are [rules/01](01-pipeline-security.md) §1.6.
- **The key must name the compiler, not just the source.** sccache hashes "the compiler binary"
  for C and C++. ccache identifies the compiler by size and modification time unless
  `compiler_check=content` is set. Bazel "does not track tools outside a workspace", so two
  machines with different compilers in `/usr/bin` "wrongly share cache hits", and only
  environment variables passed with `--action_env` reach its key. Gradle: "Missing task inputs
  can cause incorrect cache hits." Pin the toolchain inside the build (a hermetic toolchain or a
  pinned image digest) rather than trusting the host's.
- **A layer cache is keyed on the instruction text, not on what it fetches.** For `RUN`, Docker
  says "just the command string itself is used to find a match", so a cached `apt-get install`
  keeps last week's packages, and a base image already in the builder's store is reused under a
  moved tag unless `--pull` is passed.
  Cache mounts (`RUN --mount=type=cache`) are not part of the exported cache: on an ephemeral
  runner they start empty every build ([rules/04](04-build-containers.md) §4.2).
- **Some work never hits; measure before crediting a cache.** sccache cannot cache
  incrementally compiled Rust crates, or crates that invoke the system linker (`bin`, `dylib`,
  `cdylib`, `proc-macro`). Print hit statistics in the job log: `sccache --show-stats`,
  `ccache --show-stats`, Bazel's summary line ("remote cache hit"), Gradle's `FROM-CACHE` task
  outcome.
- **Absolute paths stop hits across checkouts.** ccache's `base_dir` and sccache's
  `SCCACHE_BASEDIRS` strip a base directory before hashing; without them two runners with
  different workspace paths never share an entry.
- **A poisoned cache is rebuilt, not repaired.** Bazel lists "Create a clean cache after a cache
  was poisoned" as a reason to delete its contents. Know how to empty each shared cache, and do
  it after any write by an untrusted party.

Sources, read 2026-10-29: GitHub "Dependency caching" reference; sccache README and
`docs/GHA.md`, `docs/S3.md`, `docs/Caching.md`; the ccache manual; bazel.build "Remote
caching" and "Debugging remote cache hits"; Gradle "Build Cache"; Nx "Remote cache"; the
CVE-2025-36852 record; Docker "Cache management with GitHub Actions", "Build cache
invalidation", "Building best practices" and the Dockerfile reference.

## 16.3 Run less only where skipping cannot pass a required check

Change-scoping is the biggest lever and the most dangerous one, because GitHub treats the two
ways of skipping differently (GitHub's "Troubleshooting required status checks"):

| how the work is skipped | what the required check does | failure mode |
|---|---|---|
| the **workflow** is skipped by `paths`, `branches` or a commit message | stays **"Pending"** and blocks merging | fails closed, and deadlocks a PR that touched nothing it filters |
| a **job** is skipped by an `if:` condition | reports **"Success"** | **fails open**: the gate passed without running |
| a job whose `needs` failed is skipped | "may not block merging" | fails open, silently |

GitHub counts `success`, `skipped` and `neutral` as passing statuses. So:

- **Keep required workflows unfiltered.** Do the change detection *inside* the job: compute the
  changed files against the merge base (`git diff --name-only "$BASE"...HEAD`, which needs the
  history: `fetch-depth: 0` or a fetch of the base), and if nothing relevant changed, exit 0 **and
  print the reason and the list it read**, so a no-op is visible in the log rather than
  indistinguishable from a pass.
- **A check that reads the whole tree cannot be path-scoped.** Link checkers, generated-file
  checks, cross-file invariants and coverage reconciliations can be broken by an edit to a file
  they do not "own". Measured in this repo: a negative-control probe went inert after a docs
  edit, so "skip when `scripts/` is unchanged" would have passed a gate that had stopped working.
- **Every scoped run needs an unscoped one behind it**: the full suite on the default branch, in
  the merge queue (which needs the separate `merge_group` trigger), or on a schedule with an owner
  ([`sota-testing` rules/07](../../sota-testing/rules/07-suite-health-and-ci.md) §7.5: heuristic selection needs a periodic full run).
- Graph-based selection (a build system that knows the dependency graph) is the reliable form;
  a hand-written path map drifts as the code moves.

## 16.4 Run in parallel, and keep one check that proves the whole ran

Sharding the long pole cuts wall-clock and raises total runner minutes (each shard pays its
own setup). Shard by measured duration, not by count, and make the verdict a property of the
union, not of any shard:

- **One aggregator job carries the required check's name**, with `needs:` on the shards and
  `if: always()`, and its first step fails unless `needs.<shards>.result` is `success`. Without
  `always()` a failed shard skips the aggregator, and a skipped required job reports Success
  (§16.3). Keeping the name means branch protection needs no change.
- **The aggregator proves completeness**: every shard reported, they agree on the total, every
  unit ran exactly once (no gap, no overlap), and any coverage declaration is checked over the
  union. A shard prints its count, never PASS.
- **`fail-fast: false`** on the shard matrix, so a red run shows every shard's failures.
- **The aggregator has its own known-bads** (a missing shard, a gap, an overlap, an aborted shard,
  short coverage), each asserting its own message ([rules/09](09-gates-that-hold.md) §2).

Worked example: `scripts/check-negative-controls.sh` (`NC_SHARD=i/n`, `--aggregate`) and its
9-case self-test `scripts/test-negative-controls-aggregate.sh`, wired in this repo's `ci.yml`.

## 16.5 Stop paying for runs nobody reads

- **Cancel superseded PR runs**: `concurrency:` keyed on the PR number with `cancel-in-progress`
  true **for `pull_request` only**. A push to the default branch keys on its own SHA and is never
  cancelled; a deploy or apply never cancels in progress ([rules/01](01-pipeline-security.md) §1.9).
- **Set `timeout-minutes` on every job.** The default is 360: a hung job holds a runner for six
  hours and reports nothing until then. Set it near three times the job's measured time.
- **Order by speed and signal**: the cheapest checks that fail most often run first or in
  parallel with the slow ones, never queued behind them.

## 16.6 What a faster pipeline must still prove

A speed change is a change to the gates, and it is reviewed as one:

- The **required check names** are unchanged, or branch protection is updated in the same
  change (`gh api repos/OWNER/REPO/branches/BRANCH/protection --jq '.required_status_checks.contexts'`).
- **Equivalence is measured**: the new pipeline reports the same totals as the old one on the
  same commit (this repo's sharded harness had to aggregate to the unsharded `127/127`).
- No lever adds `continue-on-error`, a retry that hides a red, or a skip without a printed reason.

## Audit checklist

- [ ] **Per-job and per-step durations were measured over several runs before any speed change, and the critical path is named** (§16.1) — Info: optimising without it; Low: a cache added to a job that was never on the critical path
- [ ] **A runner that reuses a gate's earlier pass** (§16.2) — read how it builds the key, which gates it may skip and who writes its records: a reused advisory, licence or scanner gate whose record a tag, publish, sign or deploy job or the merge queue accepts = High (an advisory published after the pass ships unchecked); the same gate reused only on development runs that a trusted path reruns = Medium; a key missing an input class, no stated expiry or a reuse that renews it, records written by lower-trust code and reused by a trusted job, reuse the record does not name, or no known-bad per input class = Medium
- [ ] **A shared build cache (compiler, layer or remote) that untrusted code can write** (§16.2a) — list each cache and the credential that writes it: a pull request, fork or developer machine able to write a cache that a release, publish or deploy build reads = High, assuming review gates what merges (Critical where any fork PR can write without review): it chooses what ships, as in CVE-2025-36852; a key that omits the compiler or relies on the host's toolchain = Low, Medium where a release build reads that cache; no hit statistics in the job log = Low
- [ ] **Workflows with no `timeout-minutes`** (§16.5) — `find .github/workflows -name '*.y*ml' -exec grep -L -e 'timeout-minutes' {} +` — each file printed runs every job at the 360-minute default = Low (a hung job holds a runner for six hours)
- [ ] **A cache restore that skips the install** (§16.2) — `grep -rnE --include='*.yml' --include='*.yaml' -e "cache-hit (!=|==) '(true|false)'" .github/workflows` — each hit: confirm the key covers every input and that a `restore-keys` partial match still runs the frozen install; a skipped verification on a partial match = Medium
- [ ] **A path-filtered workflow that is a required check** (§16.3) — `grep -rnE --include='*.yml' --include='*.yaml' -e '^[[:space:]]+(paths|paths-ignore):' .github/workflows` — each hit whose workflow's job names appear in the branch's required contexts = Medium (it blocks PRs it skips); a required job gated by `if:` with no in-job reason = High (it reports Success without running)
- [ ] **Every change-scoped check has an unscoped run behind it** (§16.3) — the full suite on the default branch, in the merge queue (`merge_group`) or on an owned schedule; a whole-tree check (links, generated files, cross-file invariants) scoped by path = High
- [ ] **A sharded check's verdict is an `always()` aggregator under the required name** (§16.4) — it fails unless every shard succeeded, proves the union ran each unit once, and ships known-bads for a missing shard, a gap and an overlap; a required check set on the individual shards, or an aggregator without `always()` = High
- [ ] **Superseded PR runs are cancelled and default-branch runs are not** (§16.5) — `cancel-in-progress` true on a push to the default branch or on a deploy = Medium
- [ ] **A speed change kept the required names and measured equivalence** (§16.6) — same totals on the same commit, before and after; no `continue-on-error`, hidden retry or silent skip introduced
