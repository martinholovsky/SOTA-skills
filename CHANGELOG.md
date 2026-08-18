# Changelog

All notable changes to SOTA-skills are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/2.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

**The arm nobody writes.** An external session transcript — a session *applying* the
library to Go subprocess sandboxing — came back with five proposals. All five landed,
three of them with a correction, and the most useful one inverts a rule the library
already had.

`rules/12`'s mutation probe is **directional**: it installs the *permissive* no-op and
asks what fails, which finds the control that does nothing. Nothing finds the opposite —
an enforcement control (cap, quota, filter, allowlist, sandbox policy) tightened until it
refuses the legitimate case too. Both defects pass the same test, because a security suite
asserts refusal and refusal is exactly what an over-tight control produces. `sota-testing`
rules/09 §1 said so in as many words ("the assertion is that the attack is *refused*, not
that the happy path works") and `sota-sandboxing` rules/01's in-sandbox probe was
**entirely** denial arms — a policy that denies everything passed all of them.

The worked instance is the batch's other finding, and it is why the two arrived together.
`RLIMIT_AS` is not usable as a memory budget: measured in a container, a Go 1.26 hello
world reserves **1,227,204 kB** of address space at **2,376 kB** RSS and a Temurin 25
process **3,937,756 kB**, so any AS cap near the real working set kills the process at
startup. `RLIMIT_DATA` — which has covered private anonymous `mmap` since Linux 4.7 —
does the job. Deny-only, the two configurations are indistinguishable: neither lets the
runaway allocation through — the AS cap only because nothing runs at all — and one of
them also refuses every legitimate run. The allow arm is the only thing that tells
them apart.

### Added

- **`sota-code-security/rules/12` §1a — the control that blocks everything.** The
  two-arm rule for enforcement controls, the asymmetry that explains why only the inert
  half ever gets found, and "a negative control on the environment is not a negative
  control on the control". Counterweights at `sota-testing/rules/09` §1 and
  `sota-sandboxing/rules/01` R5.1b, both of which pointed the other way.
- **`sota-sandboxing/rules/02` R7.2a — never `RLIMIT_AS` for a memory budget**, with the
  measured Go/JVM reservation table and `RLIMIT_DATA`'s Linux 4.7 boundary; cross-referenced
  from `rules/04` §1.2. The library never *recommended* `RLIMIT_AS` — this is the missing
  warning, not a corrected instruction.
- **`sota-sandboxing/rules/02` R7.2b — no cgroup available for a nested child.** A
  four-rung fallback ladder, and the tell that makes the situation findable: the cgroupfs
  is mounted `ro` while `cgroup.controllers` still lists `memory`, so **probe with `mkdir`,
  never by reading the controller list**. `GOMEMLIMIT`/`-Xmx` are documented soft limits
  and are not a boundary for untrusted code.
- **`sota-devsecops/rules/05` §5.6 — the negative control proves the gate *can* fail, not
  that it still covers you.** A refactor that moves code into a nested module, a second
  manifest, a submodule or a sidecar image shrinks the gate's scope with no diff to the
  workflow file: `govulncheck ./...` analyses the current module only. The temporal form of
  `rules/11` §2.2 — fail the build when a gate's enumerated denominator **drops**.
- **`sota-sandboxing/rules/04` R5.3a — a timeout that waits on inherited pipes is not a
  deadline**, and the semantics differ per language (Python 3.14 fires on schedule with a
  pipe-holding grandchild; Go's `Wait` does not without `cmd.WaitDelay`). Carries the
  pointers into `sota-golang`, `sota-python` and `sota-javascript-typescript` that §5 never
  had — the placement fix for a trap that lives in the language skill while you are reading
  the domain one.

### Changed

- **`sota-devsecops/rules/03` §3.6** — advisory **applicability** added as a fourth triage
  axis beside reachability, exposure and KEV/EPSS. "Only 32-bit platforms are affected" is
  a precondition in the advisory prose that no scanner ordering reflects; it resolves to a
  `not_affected` VEX from the closed OpenVEX justification list, not an ignore-with-expiry.

### Notes

- Every factual claim in this entry was reproduced this session rather than cited: the
  Go/JVM reservations and both rlimit arms in a Linux container, the nested-module omission
  by running `go list ./...`, the Python timeout behaviour by running it, and the cgroup
  `ro` mount by attempting the `mkdir`. `WaitDelay`, `SetMemoryLimit`, `setrlimit(2)` and
  the OpenVEX justification list come from their primary docs.
- The transcript's own two misses — `cmd.WaitDelay` and zsh word-splitting — were both
  **already in the library**, the second one twice (routing rule 17 and `rules/12` §2).
  Deliberately not restated a third time: that is the salience effect documented in
  [WHY-COMPLETENESS-RESIDUAL](docs/WHY-COMPLETENESS-RESIDUAL.md), where adding the missing
  rule made adherence *worse*. The placement fix (R5.3a) was taken instead.
- Logged as eight rows in [docs/ADOPTION-LOG.md](docs/ADOPTION-LOG.md), including one
  **deferred**: `sota-rust` has no `std::process::Command` coverage at all, found while
  validating the R5.3a cross-references.

## [1.22.9] - 2026-08-18

**The domain the library kept gesturing at.** An external intake
([system-design-notes](https://github.com/liquidslr/system-design-notes), read at full
depth, 29 files) landed three rules, all from the same blind spot: the library banned
float money in five language skills, required prices to be recomputed server-side, and
told you to use "ledger rows with unique keys" — while `debit` and `double-entry` scored
**zero** hits across `skills/`. It knew everything about money except how to model it.

Cutting it also turned the lens on the docs, which is where most of this entry's line
count went: a release cut is the moment stale claims are cheapest to catch.

**Front door checked:** double-entry · reconciliation · ledger

### Added

- **`sota-databases` rules/01 — ledgers and consumable balances.** The authoritative
  state is append-only entries, at least two per movement summing to zero under one
  journal; the balance is derived (a rollup is a cache a job re-derives and compares),
  and corrections are reversing entries. Sum-zero is enforced by a **deferred constraint
  trigger**, not app code — a one-sided write becomes an invariant the database rejects
  instead of drift a customer reports months later. The DDL was **executed on PostgreSQL
  17.11, negative control first**: a one-sided write returns `INSERT 0 1` and fails at
  `COMMIT` — the asymmetry that proves the deferral is real — and `BEFORE` / `FOR EACH
  STATEMENT` are syntax errors, so the two restrictions the rule states stop a reader
  rather than silently downgrading the check.
- **`sota-architecture` rules/03 §5b — reconciliation against an external system of
  record.** The word appeared eight times in the tree and never as a rule: every instance
  was domain-bound (orphaned accounts, a webhook backfill API, pipeline row counts).
  §2–§4 buy *integrity*; reconciliation is the only thing that buys **completeness**.
  Reconcile against the counterparty's extract, not your own event log; classify breaks
  into auto-adjustable / manual / unclassified; age them. A reconciliation that has never
  reported a break has the inert-control signature (`sota-code-security` rules/11 §2.2).
- **`sota-architecture` rules/03 §5 — conservative leg ordering.** Debit before credit, so
  a crash between legs leaves value *missing* (recoverable by compensation) rather than
  *duplicated* (not, once spent). Credit-first only where the credit provably cannot be
  consumed before the terminal state — enforced, not assumed.

### Changed

- Audit checklists gained the probe for each rule, not just the rule
  (`grep -rn "SET balance"` for the mutable-balance CRITICAL; "has the reconciliation ever
  been observed reporting a break?").
- Routing surfaces updated so the new material is reachable: the router's routing table
  rows for `sota-architecture` and `sota-databases`, and both skills' rules-index rows.
- [docs/ADOPTION-LOG.md](docs/ADOPTION-LOG.md): the intake recorded in full — three
  adopted, two deferred (event-sourcing determinism; geospatial, which is **thin, not
  absent**), four rejected, including one **rejected: contrary** (the source teaches CAP
  as "pick two of three"; `rules/03` §1 is PACELC and per-operation). The source is
  unlicensed and derivative of a copyrighted book, so nothing was copied — only the idea
  class, re-derived.

### Fixed — four stale claims, found by re-reading rather than by a gate

None of these had a gate that could catch them; all four were prose asserting a state
the tree had moved past.

- **README claimed "seven audit instruments across three designs"** while the scoreboard
  carried **nine rows across four**. The missing two are the strongest form of the test —
  a real repository at a real vulnerable commit — so the stale number understated the
  evidence rather than overstating it: across 16 real BOLA sites in Harbor v2.5.1 both
  arms recalled 15/16, and across 59 blinded findings both scored precision 1.00.
- **`evals/DESIGN-real-repo-audit.md` still announced itself as "nothing measured yet",
  "No run, no number, no lift"** — four days after the eval ran and closed the question.
  A reader following the link from RESULTS would have concluded the opposite of the
  truth. Re-headed as executed, with the outcome and a pointer to the results; the
  method sections are kept, since those held up.
- **[RESULTS.md](evals/results/RESULTS.md)** called the audit question "Final" at seven
  instruments. The dated paragraph is left standing — it was true when written, and
  rewriting history is not correcting it — with a **superseding** note above it: closed
  at nine instruments and four designs, and no tenth accuracy instrument.
- **[docs/ROADMAP.md](docs/ROADMAP.md)** carried a router count of 491/500 (actual:
  **494**, six lines of headroom) and a "pending release cut" for **1.22.4**, five patch
  versions ago.

### Changed — docs

- [AGENTS.md](AGENTS.md) now honours its own "keep it under 200 lines" rule for the
  first time in several releases — **208 → 199** — by compressing narration of
  *closed* incidents while keeping every operative rule. It is the one file that loads
  into every session, so its length is a live cost, not a tidiness question.
- [docs/ROADMAP.md](docs/ROADMAP.md) gained the two deferred ideas as an explicit open
  item, so neither gets silently dropped or silently re-litigated.
- The negative-control harness was **re-run** rather than cited from memory:
  `PASS: 21/21 mutations caught by the intended check`.

## [1.22.8] - 2026-08-16

**A rejection, and three counts that had drifted.** The as-deployed competitor
comparison is closed as *rejected* rather than deferred — checking the pinned clones
showed it would measure corpus size and a retrieval path already scored saturated, not
guidance quality. Alongside it, the docs were re-counted against the tree: the router
headroom, the ledger's own list of verdict states, and a roadmap row whose premise had
been overtaken by evidence.

**Front door checked:** competitor · benchmark · roadmap

### Changed

- **The as-deployed competitor comparison is rejected, not deferred.** It sat on the
  roadmap as a ~$8 purchase; checking the pinned clones instead of memory shows it is not
  a purchase and not a harness gap — it is a measurement that would land on the wrong
  variable. **ECC ships 889 `SKILL.md` files with a `.claude-plugin/marketplace.json`;
  claude-skills ships 777** — so two of three competitors deploy through *our own*
  mechanism over a corpus 20× ours (41). The result would partly measure repo size, and
  it would route through a description-selection layer `run-desc-routing.py` already
  scores at **+0.00, saturated**. Neither confound has a neutral fix: simulating a loader
  none of them ships lets our choices decide the outcome, and a retrieval **miss** would
  score as a content zero — defensible as a deployment fact, rigged-looking as a published
  claim about a named third party. The content-only benchmark stays the claim, with its
  own disclosed weakness (the maintainer hand-picks 4–8 files per competitor), which is
  the better-understood limitation. Reasoning kept in
  [ROADMAP](docs/ROADMAP.md) and [ADOPTION-LOG](docs/ADOPTION-LOG.md) so it is not
  re-litigated.


- **`adopted with a correction` is now a documented ledger verdict.**
  [ADOPTION-LOG](docs/ADOPTION-LOG.md) said every entry ends in one of four states, and
  v1.22.7 introduced a fifth without saying so. It exists for the real case it was coined
  for: a proposal whose *substance* was right but whose *wording* would have licensed the
  opposite behaviour. Plain `adopted` would hide the edit from whoever wrote the proposal;
  `rejected` would be false.
- **Docs re-counted against the tree.** `AGENTS.md` claimed the router sits at 491 lines;
  it is **494** — six left against the 500 cap, so the next router addition has to reflow
  rather than append. That number has now been wrong twice in this file, so the sentence
  tells the reader to re-count instead of trusting it. `ROADMAP` drops the closed
  denylist-divergence row (re-derived and canary-proven 2026-08-13) and renumbers; the
  remaining five were each re-checked, including the star count, which is unchanged at 13.

## [1.22.7] - 2026-08-16

**Two rules written because I broke them.** A gate joined to an irreversible action with
`;` instead of `&&` — so a push ran while the check printed FAIL — and a verification
instrument that runs *over time*, where "abort on a missing result" kills the watch and a
dead watcher is indistinguishable from a waiting one. Both arrived from field use, both
ship with an audit probe, and both name the failure as observed rather than as advice.

**Front door checked:** instrument · shell · invariant

### Added

- **`rules/12` §2.2a — instruments that run over time.** §2.2's "abort on a missing
  result" is right for a one-shot scorer and wrong for a watcher: abort on the first
  unreadable read and the watch dies on any transient failure, and because **silence is a
  watcher's normal state**, a dead watcher and a waiting one are indistinguishable. Both
  resolutions of an unreadable read are live defects — fail open invents a success, fail
  closed-by-aborting loses the event — so the section adds a **third state**: done /
  not-done / **cannot-tell**, with the terminal condition asserted *positively*, a bound
  on consecutive unknowns so persistent blindness is reported, and an **independent
  signal printed beside the verdict** so a false verdict has something to disagree with.
  Reported from a watcher that announced success on a job that was 89% done, because
  `!= "0"` is satisfied by an empty read. Paired in `sota-shell-scripting` rules/02 §2:
  validate **captured output**, not just arguments — verified that `""`, `error`, `null`
  and a usage message all compare `!= "0"`.

  Two decisions recorded in [ADOPTION-LOG](docs/ADOPTION-LOG.md): the finding stays in
  `rules/12` rather than `sota-observability` §8 (which owns probing a *running service*,
  a different subject), and the drafted wording "§2.2 **inverts**" was corrected to "its
  principle holds, its remedy does not" — the stronger claim would license dropping §2.2
  inside a watcher, which is the opposite of the intent.


- **A gate and the irreversible action it gates must be joined by `&&`, never `;`**
  (`sota-shell-scripting` rules/04 §1b, with an audit probe). In a script `set -e` stops
  you; typed at a prompt or joined with `;` inside a CI `run:` block, nothing does — the
  check runs, prints FAIL, and the push happens anyway because it was the next token.
  Two aggravating factors named because they make it invisible rather than merely
  ignored: a pipe rewrites the status (`check | tail -2` reports `tail`), and
  **diff-based checks legitimately differ before and after a push** because their merge
  base changes — so a pre-push result must never be what authorises the push.

### Changed

- **`RELEASING.md` now documents how invariant 14 actually matches.** The comparison is
  literal (`grep -F`) and the front-door line is excluded from the entry search, so a
  term cannot satisfy itself. Both failure modes are recorded because both happened on
  real cuts: declaring `negative control` when the entry writes `negative-control`, and
  declaring a word that appears only in the declaration. Includes a one-liner to test a
  candidate term before committing to it, plus the note that invariants 11 and 14 are
  diff-based and should be re-run once the branch exists upstream.

## [1.22.6] - 2026-08-16

**The audit turned inward.** A scoped audit of the code that *measures* this library —
`evals/` and `scripts/`, the two areas 15 of 16 invariants never touch — found a
Critical data-loss bug, two gates that passed while structurally unable to see anything,
and a drift guard that did not span what it protects. **Zero findings in `skills/`.**
The prediction was committed before any auditor reported. Alongside it, five findings
from a session that used the library on a real project, each re-validated here.

**Front door checked:** negative-control · instrument · invariant

### Added

- **Five field-use findings from a live build, each re-validated here before landing.**
  A handoff brief from a session that used the library end to end on a real project. Every
  anchor and every empirical claim was re-checked at this commit rather than taken on
  trust; full intake with the one rejection is in
  [ADOPTION-LOG](docs/ADOPTION-LOG.md) 2026-08-16.

  - **The auditor's own verification one-liner is an uninstrumented instrument**
    (`sota/SKILL.md` rule 17 + `rules/12` §2). Unlinted shell, run against the system
    under test, producing false findings *about the product* — three in one session, all
    zsh joining/pipeline bugs this library already documents. The rule existed; nothing
    **routed** to it, because the task did not look shell-shaped. Rule 17 now names the
    commands you type, and `rules/12` §2 carries the three tells and an explicit
    cross-reference.
  - **`set -e` cannot be re-armed, and `$-` lies about it** (`sota-shell-scripting`
    rules/01 §2). Inside a suspended call tree neither `set -e` nor `set -o errexit`
    restores errexit, while `case $- in *e*)` still matches — the shell reports the safety
    flag as enabled while it is behaviourally inert. **Reproduced here on GNU bash 5.3.15
    *and* 3.2.57** (the brief had only checked 5.3.15), so the rule states both. Only
    explicit `&&` or a fresh `bash -c` work.
  - **`SECURITY.md`'s "never open an issue" now has a private-repo carve-out**
    (`sota-docs-workflow` rules/01, both the table row and the checklist). GitHub's
    private vulnerability reporting is **public-repo only** — *"Owners and administrators
    of public repositories can enable private vulnerability reporting"* (docs, checked
    2026-08-16) — so the rule pointed at a feature that cannot be enabled, while the thing
    it forbade (a collaborator-only tracker) *is* private. The file must now name the
    switch to make on going public.
  - **Location-dependent silence** — a new class in `rules/11` §3.5, with the count fixed
    in all **four** ripple sites. A filter whose predicate matches the *ambient
    environment* rather than the data: `"private" not in p.parts` against an absolute path
    empties the collection on macOS, where `/var` resolves to `/private/var` (verified).
    Generalises to hostnames, usernames, env vars and locales; the defences are anchoring
    the predicate and asserting non-empty on every collection a suite iterates.
  - **A platform-refused pipeline is a third state** (`rules/10` §2.13) and **proving a
    pipeline runs** is now a section (`sota-devsecops` rules/01 §1.11). Refused runs
    report *failure*, not skipped, so the all-skipped test misses them; the tell is every
    job failing in seconds with no step logs and the reason only in annotations. The
    remedy — run the jobs locally against a fresh clone of committed state, treat missing
    tooling as a hard failure, print substitutions — deliberately names **no tool**, since
    the brief flagged its own suggestion as unevaluated.


### Changed

- **Docs re-synced to what the audit changed, with the numbers re-counted rather than
  carried forward.** `AGENTS.md`: **16 → 21 negative-control probes**, and the enumeration
  now names the 11 probed invariants plus the five that need a fixture a worktree cannot
  provide. Its "every file-list-driven check reports its denominator" sentence is now
  annotated with the fact that it was **false for checks 4 and 8** until this cycle — in
  the one file that states the rule. `CONVENTIONS-LEDGER`: runner-enforced conventions
  **5 → 8** (judge-verdict shape, pin-what-you-compare-against, a probe must assert its own
  mutation) — every one of them arrived from an incident, which is that ledger's own
  thesis. `evals/README` gained the judge-shape convention with the two demonstrated
  0.00/12 failures. `ROADMAP` records the audit outcome and its two deliberate residuals.

### Fixed

- **Instrument audit, final pass — every remaining finding closed.**
  - **Negative-control coverage: 6 of 16 invariants probed → 11 of 16.** New probes for
    invariants **3, 4, 7, 8, 13** — all single-file edits, so the old "diff-, history- or
    release-shaped" rationale never applied to them. `PASS: 21/21`. The remaining five
    (5, 9, 11, 12, 14) genuinely need state a worktree lacks (a tag, a merge base, an
    mtime) and the harness now says exactly that. Probe 3 synthesises its trigger phrase
    at runtime because writing it literally made the harness trip check 3 — **the gate
    caught its own probe**, which is the best evidence it works.
  - **`run-decay` silently measured a different depth than it printed.** `FILLER[:depth]`
    caps at 30, so `--depths 0,12,60` reported "depth=60" while measuring 30 — and the
    DECAY headline is computed from `depths[-1]`. Now refuses.
  - **`run-repo-audit` had no empty-fixture guard** (its sibling ten lines below does): a
    renamed fixture dir would hand both arms an empty source and print a fake `+0.00`.
  - **`run-unscoped-audit` credited a defect when the file and the mechanism appeared
    anywhere in the report** — a report naming `db.py` in one paragraph and "sql
    injection" in another scored a hit. Matching is now windowed to the same block.
    **This changes a published method:** the +0.00 in `RESULTS.md` was produced by the
    looser matcher and would need a re-run to be strictly comparable. Both arms were at
    ceiling, so the direction of any change is to lower both — recorded rather than
    quietly re-scored.
  - **`install.sh` leaked temp files on any abort** — four `mktemp` sites cleaned only on
    the success path. Now a registry plus an `EXIT` trap. The first attempt was **broken
    and the test caught it**: the tracker ran inside `$( )`, a subshell, so the parent's
    registry stayed empty and the trap cleaned nothing. Rewritten to track in the parent
    shell; verified by aborting mid-run and confirming zero files remain.


- **Instrument audit, second pass — the remaining findings.**
  - **The judge parser validated nothing.** All four judge-driven instruments call one
    `judge()`; it parsed the reply and scored `verdict.get(id) == "present"`, so a
    *well-formed* reply of the wrong shape scored **0.00 in silence** — `{"results":{…}}`
    and `"Present"` with a capital P both demonstrated at 0.00/12. It now normalises case
    and **aborts** on missing/extra ids or values outside present/absent. Each of the four
    failure modes was replayed against the real rubric shape.
  - **Competitor SHAs are now enforced, not just documented.** `comp["sha"]` appeared only
    inside an error string, so every published competitor number rested on an unverified
    clone — in a repo that pins `ROUTER_BUILD_SHA` for exactly this reason. The runner now
    compares `git rev-parse HEAD` against the manifest and refuses on mismatch (proven
    both directions), and the artifact records build/judge model, manifest path and the
    resolved SHAs.
  - **Artifact provenance**: the flagship completeness artifact stored only case results —
    no models, samples, temp, or router SHA. It now writes a `_meta` block.
  - **A stale probe used to accuse a healthy gate.** Every mutation in the negative-control
    harness is a hardcoded literal; when one goes stale the edit is a no-op and the probe
    reported `NOT CAUGHT: INERT`. It now asserts the mutation actually changed the tree
    and reports **PROBE BROKEN** instead — watched to fire by neutering probe 1. `restore()`
    also no longer swallows a failed reset with `|| true`, which would have leaked one
    probe's mutation into the next.
  - **The denylist degrade is now announced** — an all-comment `.denylist.local` silently
    fell back to two generic phrases with output byte-identical to a full scan.
  - **`install.sh backup()` clobbered the original** on a second `--update`, overwriting
    the backup with the already-modified file. Rewritten as a real function (kept-backup,
    no `cp` on a missing file, `die` on failure) after the one-line version introduced an
    `A && B || C` bug — the same class fixed in `verify-setup.sh` earlier in this cycle.
  - **Two known-good/known-bad selftests ran nowhere.** `run-build-safe.py --selftest` and
    `unscoped-audit/selfcheck.py` are the repo's only reference *pairs* and no CI job or
    hook invoked them; both are now in CI. The unscoped-audit selfcheck also hardcoded
    "7 planted defects, 6 demonstrated" (the 6 already stale) — it now counts its own
    checks against a floor, watched to fail at `MIN_CHECKS = 8`.
  - Workflow-level `defaults: run: shell: bash` (steps were getting `bash -e {0}` — no
    `pipefail`, no `-u`), and `.gitattributes` pins `*.sh`/`*.py` to LF so a CRLF commit
    cannot produce `/usr/bin/env: bash\r`.


- **Instrument audit: a Critical data-loss bug in `install.sh`, and two gates that
  passed while unable to see anything.** Three scoped auditors read `evals/*.py` and
  `scripts/*.sh` at `cc1529b` against `rules/10`–`12`. The prediction was
  [pre-registered and committed first](evals/results/2026-08-16/PRE-REGISTRATION-INSTRUMENT-AUDIT.md);
  it held — **highest severity in `scripts/`, zero findings in `skills/`**.

  - **Critical — `install.sh` could delete a user's file.** With an altered/indented END
    marker, `grep -qF` (substring) passed and `extract_block` returned BEGIN→EOF, so it
    was non-empty and the emptiness guard passed too; `refresh_block`'s awk then never
    left its delete branch and **erased every line below the block** in
    `~/.claude/CLAUDE.md`. Reproduced end-to-end. Both marker greps are now `-qxF` and
    the block check is end-anchored (`tail -n 1 == RT_END`). Verified three ways: the
    bad case refuses, a healthy block still proceeds, an indented BEGIN falls through.
  - **Invariants 4 and 8 had no denominator** — a drifted glob printed `ok` and exited 0,
    contradicting `AGENTS.md:69` ("every file-list-driven check reports its denominator").
    Both now print counts (`ok (41 descriptions)`, `ok (351 markdown files)`) and were
    **watched to fail closed** on a mutated pathspec.
  - **CI's shell lint could not see its own top defect class.** `shellcheck -S warning`
    exits 0 on `rm -rf $dir` because SC2086 is info-level — the class this repo's
    `sota-shell-scripting` rules/01 §3 calls "a bug, not style". Raised to `-S style`,
    widened from `scripts/*.sh` to every tracked `.sh` (which brought
    `evals/cases/dead-path/selfcheck.sh` under lint for the first time), and made to fail
    closed on an empty file list. The tree was cleaned to **0 findings at style** first —
    `ls`-parsing and `A && B || C` fixed properly rather than suppressed.
  - **`principle5()` returned `""` on a moved marker**, silently weakening the treatment
    arm of the flagship +0.39 — and `ROUTER_BUILD_SHA` does not cover it (the hash spans
    chars 24111–26758; principle 5 lives at 4079–6433, **disjoint**). Now aborts, with a
    length floor. Watched to fire.
  - **`judge-live-build.py` averaged over survivors** — the defect fixed in
    `run-competitors.py` two days earlier, in the instrument that produced the published
    **0.987**. Now aborts when nothing was judged, labels partial runs in stdout *and*
    the artifact (`cases_done`/`cases_total`/`complete`/`skipped`).
  - **The negative-control harness misreported its own coverage**: invariants 3, 4 and 7
    were in neither the covered nor the "not covered" list, so
    `AGENTS.md:97` ("what is not covered is printed, not implied") was false. The list is
    now exhaustive — 6 covered + 10 uncovered = 16, no overlap — and says *why* each is
    uncovered. Harness still **16/16**.
  - **Invariant 14 matched front-door terms as a regex** (`a.b` matched `axb`); both
    greps are now `-F`.
  - Silent-zero guards added and each watched to fire: `score.py` (empty corpus),
    `run-adjudication.py` (`assert` → `sys.exit`, plus a router-marker guard),
    `run-desc-routing.py` (the ablation must actually remove something, or the null is
    manufactured), `run-clean.py` (empty freshness corpus).

### Added

- **A missing tool is a decision, not automatically a failure**
  (`sota-shell-scripting/rules/02` §6). `|| die` is right only for a dependency the
  script cannot be correct without; for everything else the rule is now explicit —
  **skip the affected check with a named note** (never let a summary read clean when a
  check did not execute), degrade for optional tooling, and **on an interactive run stop
  and ask the human to install it, printing the exact command**. Never auto-install:
  installing software is a change to someone's machine and a non-interactive run has
  nobody to consent. Ships with a `need()` helper and its audit half.



### Measured

- **Competitor benchmark re-run: the published claim holds after a month of library
  change.** SOTA **98.7%**, ECC 84.9%, awesome-cursorrules 80.0%, claude-skills 77.0%,
  unguided **58.2%** — and SOTA again **won 17, tied 4, lost 0** of 21 head-to-head
  cases. Same build model (`git log -S` shows the default was set by the original
  benchmark commit and never changed) and the same pinned competitor SHAs, so library
  content was the only variable. **The unguided arm reproducing to 0.2 points is the
  control** that says the harness and judge did not drift underneath the comparison.
  Competitor moves of 2–4 points are **not** claimed as regressions — n=1 per arm, and a
  2-point move is one rubric item on one case.
  [COMPETITOR-RERUN](evals/results/2026-08-14/COMPETITOR-RERUN.md)

### Fixed

- **A partial results artifact reached `main`, and the runner now refuses to hide it.**
  A `git add -A` in an unrelated docs commit swept up `competitor-rerun.json` while the
  run was still executing, and it merged. The committed file was **valid JSON with 2 of 7
  cases** and `means` recomputed over just those two — `ECC` read **0.954** against a true
  **0.849**, with nothing in the artifact saying it was partial. That is the dangerous
  shape: not corrupt, just plausibly wrong. The incremental save stays (it is deliberate
  crash-safety); the artifact now carries `cases_done`, `cases_total` and `complete` so a
  reader or scorer can refuse an unfinished file instead of averaging it. The complete
  file replaces the partial one in this change.


### Added

- **zsh does not word-split unquoted expansions — and the library said it did.**
  `sota-shell-scripting/rules/01` §3 stated word splitting as universal, which is a
  *bash* fact: zsh's `SH_WORD_SPLIT` is off in native mode (the manual marks it
  `<K> <S>`, ksh/sh emulation only). So `cmd $args` passes **one** argument in zsh, and
  the same line that is a splitting bug in bash is a **joining** bug in zsh — on the
  platform that defaults to zsh. Verified by execution, not assertion:
  `printf "[%s]" $args` → `[one two three]`, `${=args}` → `[one][two][three]`.

  Shipped with its audit half. **`shellcheck` refuses zsh outright** (`SC1071 … only
  supports sh/bash/dash/ksh`, confirmed by running it — and popular web summaries claim
  the opposite, which the binary settles). The checklist now carries a verified tool
  table rather than the absence claim this entry first made: `zsh -n` catches **syntax
  only** (proven on a broken script), `WARN_CREATE_GLOBAL` is runtime and narrow, and
  `z-shell/zsh-lint` exists and is actively pushed (~33 stars) — so "no linter for zsh"
  is false, while "no widely-adopted static analyser catches the splitting class" holds.
  The checklist adds the
  grep for `${var:+--flag $var}` and bare `cmd $args`, and names the symptom that
  misleads: a **usage error (exit 2) from the callee**, which reads as a bug in the tool
  rather than in the harness calling it. `rules/02` §4 gained zsh's `${pipestatus[1]}`
  (1-indexed) beside bash's `${PIPESTATUS[0]}`.

### Changed

- **The empty-completion guard is now a recorded convention, not just code.**
  [CONVENTIONS-LEDGER](docs/CONVENTIONS-LEDGER.md) goes from **four** runner-enforced
  conventions to **five** — and it arrived the way that ledger predicts they do, from an
  incident rather than from re-reading the docs. `AGENTS.md` and the evals harness
  conventions were updated to match.
- **Competitor benchmark re-run in flight** at the pinned competitor SHAs, with the same
  build model as the 2026-07-13 original (`git log -S` confirms the default was
  introduced by the original benchmark commit and never changed, so the library content
  is the only variable). The **as-deployed** variant stays unbuilt and is now recorded as
  blocked on a *design* decision rather than effort: "as their users install them" means
  something different per competitor, and choosing those mechanics chooses the result on
  a public claim about named third parties.

## [1.22.5] - 2026-08-14

**Instruments, corrected.** Every entry here is a measuring tool that was wrong or
silent, found by using it: an empty completion counted as a successful call in five
runners, a probe that counted Go import paths as network traffic, two arms that
reported a verification they never ran, and a page still explaining the audit +0.00
with a hypothesis this cycle falsified. The one new number, +0.58 at three samples,
exists because the harness crash that produced it was fixed rather than retried.

**Front door checked:** cross-family · real-repo · precision

### Measured

- **Cross-family #2 re-run at 3 samples/arm: 0.38 → 0.96, lift +0.58** (`$4.48`, 1753 s,
  temp 0.7 — the same multi-sample protocol the other value dimensions use). The n=1
  caveat is discharged: **all 7 cases positive** (+0.52 to +0.67), and the arms behave as
  they do everywhere else — with-arm mean 0.96 with a max within-case sample spread of
  **0.10**, against the unguided arm's **0.18**. Three labs now read +0.39 / +0.44 /
  +0.58. [CROSS-FAMILY-GEMINI](evals/results/2026-08-13/CROSS-FAMILY-GEMINI.md)

### Fixed

- **The same empty-completion defect was in four more runners — now guarded in all of
  them.** After fixing `run-completeness.py`, a sweep found `run-clean.py`,
  `run-decay.py`, `run-desc-routing.py` and `run-repo-audit.py` reading
  `choices[0].message.content` raw with no check. That set includes **`run-clean.py`,
  which produces the flagship +0.39** — and the two importers (`run-adjudication`,
  `run-silent-open`) plus `run-competitors` inherit its `call()`, so four files cover all
  twelve runners. Each guard was **watched to fire** against a stubbed
  200-with-null-content response, not merely compiled: two exit with
  `empty completion from …: finish_reason=length`, two raise it so their retry loop
  engages first.
- **`run-completeness.py` treated an empty completion as a successful call.** A reasoning
  model can spend its whole `max_tokens` budget on reasoning and return
  `content: null` under HTTP 200; the harness passed that to the judge, where it
  surfaced 80 lines away as `'NoneType' object is not subscriptable`. Worse than the
  crash was the near miss: an **empty artifact that reached the judge would have scored
  ~0 and silently depressed an arm**. `call()` now retries an empty completion and then
  fails loudly with the finish reason, and warns when `finish_reason == "length"` because
  a truncated artifact is a floor, not a measurement. Watched to fail before being
  trusted (`max_tokens=1` → `RuntimeError: empty completion … finish_reason=length`), and
  the 3× run that followed produced **zero** truncation warnings.

- **Stale claims removed from the docs that carry them.** `AGENTS.md` said the
  negative-control harness runs **15 probes** and enumerated five invariant probes; it
  runs **16** and the enumeration omitted invariant 16, which shipped with its own probe
  in v1.22.2 (re-counted: 6 in part A, 10 in part B). And
  [WHY-IT-WORKS.md](docs/WHY-IT-WORKS.md) still explained the audit +0.00 by saying a
  real lift "would need whole-repo, cross-file context a snippet can't carry" — that
  hypothesis was **tested and falsified** this cycle on a real repository with real CVEs,
  on both recall and precision, so the page now says so and points at what is actually
  untested (a different dependent variable, not more context). The third cross-family
  result was added there too.

### Measured

- **Audit precision measured: 1.00 vs 1.00 — the ninth null.** All 59 findings from the
  two clean arms of the Harbor run were pooled, blinded, hash-shuffled and adjudicated
  against the code by three independent agents barred from the internet. **Zero false
  positives on either side.** With recall already 15/16 = 15/16 and severity mix
  indistinguishable, the library arm and the bare arm are the same auditor on this
  subject. The adjudicator itself passed a **4/4 known-answer control** (two fabricated
  findings REFUTED with the deciding code quoted, two real ones CONFIRMED), so the 1.00
  is not a lenient scorer.

### Fixed

- **Two corrections to the published real-repo audit, both found by re-checking my own
  probes.** The "upstream fetches" column counted `github.com/goharbor` — the Go **module
  path in every import statement** — not network calls; re-counted from actual commands.
  And the correction surfaced worse: **both clean arms claimed a byte-identical diff
  against upstream that neither ever ran** (r1 executed one `cat VERSION` in a workspace
  with no `.git`, and invented a "sanity-checked against v2.6.0" detail). The two arms
  that *did* run the diff are precisely the two that got contaminated by reading the fix.
  Symmetric across a bare and a library arm, so it is a model property, not a library one
  — but it lands on this library's own "claim done only with evidence" doctrine.
  [REAL-REPO-AUDIT](evals/results/2026-08-13/REAL-REPO-AUDIT.md)

## [1.22.4] - 2026-08-14

**Rules from someone else's incident notes, a leak the leak-check could not see, and
the eighth audit null.** Three of this cycle's rule additions came from reading an
outside implementation's own failure write-ups; one came from our own gate passing
while a name sat in two tracked docs. The measurement half is one positive and one
null, both published.

**Front door checked:** business logic · cross-family · real-repo

**Three rules from a 1-star repo that documented its own failures.** An intake pass over
[spanchain](https://github.com/ghostfactory-art/spanchain) (Elixir hash-chained audit
ledger for agent runs) found six of its lessons already in `sota-code-security/rules/04`
§8 — independently arrived at on both sides — and three that were not. Full intake with
verdicts, rejections and the verification notes: [docs/ADOPTION-LOG.md](docs/ADOPTION-LOG.md)
2026-08-11.

### Changed

- **Business-logic flaws are now reachable by name.** A coverage/depth audit of that
  defect class against OWASP WSTG-BUSL (all **10** sub-tests, IDs read from OWASP's own
  repo — the task that commissioned this audit recalled 9 and missed
  `WSTG-BUSL-10 Test Payment Functionality`), API6:2023 and the CWE-840 cluster found the
  **content is there — 10 of 10 map at depth ≥3, most at 4** — but the class was
  unreachable: "business logic", "checkout", "refund" and "state machine" appeared in
  **zero** of 41 `SKILL.md` descriptions, and "workflow" appeared only in the CI, SOC and
  docs senses. Descriptions are the only auto-loaded trigger classifier, so the fix is one
  word-pair in `sota-code-security`'s description (998 → 1014 of the 1024 cap).

  **Two drafted rules edits were cut after refutation**, which is the point of running
  one: the BUSL-07 and BUSL-10 "gaps" were both covered under other names, and the
  refuter's own surviving residual (currency mismatch) fell to
  `rules/01-input-injection.md:28`. No rule text changed.
  [COVERAGE-BUSINESS-LOGIC-2026-08-13](docs/COVERAGE-BUSINESS-LOGIC-2026-08-13.md)

### Measured

- **The real-repo audit eval ran: no measurable lift, and a new contamination vector.**
  Four live agents (2 bare, 2 library) audited Harbor `v2.5.1` against 16 real
  broken-object-level-authorization sites. Clean result: **bare 15/16, library 15/16** —
  the eighth audit instrument to read ≈ +0.00, and the first on a real repository with
  real CVEs. **Two of four arms were discarded**: they looked up Harbor's *fixed* source
  mid-audit, proven by counting symbols the fix introduces (`requirePolicyAccess` and
  friends, 63 and 54 occurrences) which exist nowhere in the vulnerable tree. A synthetic
  subject leaks the answer through structure; a real one leaks it through the internet.
  The probe is now a documented harness convention.
  [REAL-REPO-AUDIT](evals/results/2026-08-13/REAL-REPO-AUDIT.md)
- **Third model family confirms the completeness lift: `google/gemini-3.1-pro-preview`,
  0.41 → 0.96, lift +0.55** ($1.63, 7 cases, n=1 per arm). Three labs, three positive
  lifts — +0.39 sonnet, +0.44 gpt-5.1, +0.55 gemini — and the same relationship each
  time: the lift tracks the **baseline**, not the lab. Recorded as a confirmation of
  direction, not a precision estimate.
  [CROSS-FAMILY-GEMINI](evals/results/2026-08-13/CROSS-FAMILY-GEMINI.md)

### Fixed

- **The real-repo audit subject was mischaracterized, and reading the tree caught it.**
  [DESIGN-real-repo-audit.md](evals/DESIGN-real-repo-audit.md) described Harbor's 8
  advisories as a *missing* authorization check. They are not: at `v2.5.1` every
  vulnerable handler already calls `requireAccess`, and `retention.go` has 11 checks for
  11 handlers. What is missing is the **object-to-tenant binding** — that the policy or
  execution named in the URL belongs to the project the caller was authorized against
  (34 object-binding lines added in the fix, against 1 project-access line). It is OWASP
  API1:2023, and a *silent control* in `rules/10`'s sense: the guard runs, returns nil,
  and everything downstream believes authorization happened. A better subject than the
  original reading, and the correction only surfaced because the claim was checked
  against the tree instead of the filenames.
- **An internal-name leak the internal-name check could not see.** Two tracked docs
  named one of the maintainer's other projects, and one of those lines also carried a
  local `~/` path; a third line elsewhere did the same. Invariant 3 passed on all of it,
  because the private denylist had no pattern for that name — the gate was green on an
  incomplete **list**, not a clean tree, which is `rules/12` §3's guard-whose-predicate-
  misses-its-own-target in this repo's own machinery. Lines redacted (the meaning is
  kept, the identifiers are gone), the private list extended, and the new pattern
  **watched to fail** against a staged known-bad before being trusted (`[3/16]` flagging
  the probe, full run exiting 1, then 0 once removed). The pre-2026-07-01 disclosure in
  git history is unchanged and stays an accepted risk — re-confirmed with the sweep's
  scope recorded in [docs/AUDIT-2026-07-01.md](docs/AUDIT-2026-07-01.md) S1.

  [CONTRIBUTING.md](CONTRIBUTING.md) now documents the part that bit: the list lives in
  two places that cannot see each other (a git-ignored local file and a **write-only**
  CI secret), so a name added to one silently leaves the other lane open. It also
  documents the **canary** — a synthetic pattern in both copies that lets anyone prove
  the secret is loaded and blocking by pushing a file containing it, without printing a
  real internal name into a public CI log, which is what probing with a real name would
  do.

### Added

- **`sota-code-security/rules/04` §8 — a partitioned chain must chain its partitions.**
  Ledgers get segmented for ordinary reasons (fixed-size epochs to bound an index, daily
  partitions, rotated files) and the obvious implementation starts each segment with
  `prev_hash = NULL`. Deleting a whole **interior** segment then verifies clean on both
  sides of the hole. §8 previously enumerated two deletion geometries, tail and
  whole-stream; the rule now names three and says which a chain walk can and cannot
  catch. Audit checklist asks for the fixture: one whole interior segment removed.
- **`sota-code-security/rules/12` §3 — a fourth form of "the guard that is an instance of
  what it guards".** The segment bug lived in the *verifier*, which reset its carried
  hash at each boundary: predicate right, traversal right, blind to the removal of a
  whole chunk. Also a new axis for §3's per-target rule — for a guard that walks a
  sequence the population includes the **seams** (first chunk, last chunk, interior chunk
  removed, empty chunk), and three of those four survive any amount of single-record
  mutation.
- **`sota-code-security/rules/04` §8 — canonicalization fails in two directions, and
  "canonical" must name a spec.** The library said "canonical, unambiguous encoding" in
  three places and never said how to get one; a reader complying with `sort_keys=True`
  has a single-language encoder with unpinned float and escaping behaviour, which
  contradicts the same section's requirement that verification run off the storing
  system. Now names RFC 8785 (JSON Canonicalization Scheme, June 2020, Informational) or
  a written encoder spec, pinned by a committed known-answer vector. Adds the missing
  **false-alarm** direction: a default map/JSON encoder is not canonical — quoting the Go
  spec ("the iteration order over maps is not specified…") and the Elixir `Map` docs
  ("key-value pairs in a map do not follow any order") — so identical data hashes
  differently, the ledger reports tamper on untouched records, and an alarm that is wrong
  on ordinary traffic gets muted, which is `rules/10`'s inert control by another route.
- **`sota-llm-engineering/rules/01` §5 — a replay harness is not an eval.** Recorded-trace
  or cassette replay re-executes nothing, so it tests pipeline determinism, not the
  system's behaviour; wired into the gate as if it were the suite, the CI job stays green
  through a prompt rewrite, a model swap or a retrieval change. Suites must declare what
  is live and what is replayed, and the gate must fail with the model endpoint
  unreachable — the file's first link into the silent-control family.

## [1.22.3] - 2026-08-05

**Closing the loop on the gates.** The v1.22.x cycle built a harness to prove our checks
can fail, then found the harness itself could not block a merge. This closes that, and
tidies the roadmap the cycle left messy.

**Front door checked:** negative control · activation

### Fixed

- **All four CI jobs are now required checks.** Branch protection required only
  `Repository invariants` and `Secret scan (gitleaks)`; `Negative controls (the gate can
  fail)` and `Shell lint (shellcheck)` ran on every PR and **could not block a merge** —
  so the harness built to prove our gates can fail was itself unable to stop anything.
  A gate that executes with no enforcement power is `rules/10` §2.13 one level up.

  **Watched to block, not merely configured.** A throwaway PR made invariant 2 inert so
  that *only* the negative-controls job failed — `check-invariants.sh` stays green when
  one of its checks goes inert, which is exactly the defect the harness exists to catch,
  so the other three jobs stayed passing and the protection's reaction was unambiguous:

  ```
  BEFORE   mergeable=MERGEABLE  mergeStateStatus=UNSTABLE   ← could have been merged
  AFTER    mergeable=MERGEABLE  mergeStateStatus=BLOCKED
           gh pr merge → "the base branch policy prohibits the merge"
  ```

  `UNSTABLE` vs `BLOCKED` is the discriminating observable — `UNSTABLE` means a
  *non-required* check failed. Applied via the dedicated `required_status_checks`
  endpoint, not the full `/protection` PATCH, which requires every field and silently
  drops what you omit: everything outside that key diffed **identical** before/after,
  `enforce_admins` stayed `true`, `strict` stayed `false`.
- **`docs/ROADMAP.md`'s actionable table had three rows numbered 8 and two numbered 9**,
  because three consecutive cuts each appended "the next item" without checking. Record
  rot of our own making. The five completed items now sit in a dated **closed list**
  below the table, without numbers; the table holds only what is still actionable (1–7).

### Changed

- **`docs/INDEX.md` gained the two rows this cycle needed.** The find-it-fast index had
  **zero** hits for `negative control` and for skill *activation* — both shipped in
  v1.22.0–v1.22.2 with no way to reach them from the index a lost reader is told to start
  at. The `CONTEXT-MANAGEMENT.md` anchor was derived from the live heading rather than
  assumed: invariant 8 resolves `*.md` targets, not fragments.
- `AGENTS.md` and `RELEASING.md` said **"both required checks"** — now four.
  `docs/AUDIT-2026-07-01.md`'s "both checks green" is a dated historical record and was
  deliberately left alone.

**Nothing here is measured; no lift is claimed.**

## [1.22.2] - 2026-08-05

**Invariant 16 — the hook we document is the hook we install.** `install.sh` *writes*
the `UserPromptSubmit` hook and `README.md` *documents* it, and nothing kept them equal.
On 2026-08-05 three texts existed simultaneously: the README block (two revisions
behind), `HOOK_CMD`, and what was actually in a real `settings.json`. The README's is
the one a reader copies **by hand**, so the stale one is the version that spreads — and
nothing executes a README, so the drift is silent by construction.

**Front door checked:** install.sh · UserPromptSubmit

### Added

- **Invariant 16.** Parses the README's fenced JSON block rather than regexing the
  string, so reformatting the block is not a false positive, and compares the extracted
  `command` to the single `HOOK_CMD` assignment in `install.sh`.
- Its **known-bad is in `check-negative-controls.sh`**, per the rule this repo now
  applies to itself: a check whose failure nobody has watched is not a check. The
  harness reports **16/16**.

### Verification

Watched to fail **four** ways, then restored: README drifts; `install.sh` drifts; the
README block is removed (fails **closed** via `SCOPE EMPTY`, not silently); and the
`HOOK_CMD` assignment is renamed (same). The two empty-scope cases matter most — they
are the mode where a gate keeps printing green over nothing.

**Nothing here is measured; no lift is claimed.**

## [1.22.1] - 2026-08-05

**Turning the negative-control bar on our second gate — and finding a rotted number
while doing it.**

### Fixed

- **`verify-setup.sh` printed a hardcoded, repo-specific, and by then false number.**
  Check 10b's message carried `(this repo: 0 failures in 60, 1 in 200)`. Two defects in
  one parenthetical: the script is **generic** and runs against anyone's repo, so a
  sample measured on *this* one is wrong for the reader (AGENTS.md: *"never phrase
  guidance as an assumption about the reader's setup"*); and it had **rotted in three
  days** — re-measured 2026-08-05, the last 200 runs are 200/200 success and the single
  failure sits at ~position 400 (2026-07-14), pushed out of the window by this session's
  CI volume. It is `rules/10` §2.10 — a literal in reporting output instead of a derived
  value — inside the script whose whole job is verifying claims. The derived
  `$n_runs` and the actionable `Widen with --runs N` remain.

### Added

- **`check-negative-controls.sh` part B — negative controls for `verify-setup.sh`.**
  It had 14 checks and nothing had ever proven one could fail. The fixture is inverted
  from part A: `verify-setup.sh` audits a **machine**, so part B builds a
  fully-configured fake one — `CLAUDE_CONFIG_DIR` at a temp home (the script reads that
  env var, so the real `~/.claude` is never touched), a throwaway git repo, and a stub
  `gh` on `PATH` so run history is decidable — then **removes one thing per probe**.
  10 probes over checks 1, 2, 3, 4, 6a, 6b, 7, 8, 9 and 10a; the harness now reports
  **15/15**. Extended the existing script rather than adding a second CI job.
- Both parts keep the FALSE-PASS rule: a non-zero exit for any reason *other than the
  intended check* is reported as a false pass, not a catch.

### Verification

Watched to fail, per the script's own bar: making `verify-setup.sh` check 6a
unconditionally pass makes the probe report **`NOT CAUGHT: This check is INERT`** and
the harness exit 1. `CLAUDE_CONFIG_DIR` redirection was proven rather than assumed (a
temp home with 2 planted skills reports 2, against the real 41). `shellcheck -S warning`
caught an `rm -rf "$VS/home"` that would expand to `rm -rf /home` on an empty variable —
now `${VS:?}`.

**Front door checked:** check-negative-controls · verify-setup

**Nothing here is measured; no lift is claimed.**

## [1.22.0] - 2026-08-05

**The activation release — and gates that prove they can fail.** Two findings, both
from real sessions rather than from re-reading docs. First: a ~25-turn session doing
upstream-contribution work invoked **zero** `sota-*` skills, because only the
frontmatter `description` auto-loads and the old trigger verbs all assumed you own the
codebase. The router's content was never in question; it was never read. Second: the
repo's own CI printed "ok" fifteen times without anything ever proving those checks
could still fail — the thing this library requires of everyone else.

**Front door checked:** check-negative-controls · pull request · publishing · negative control

**Nothing in this release is measured; no lift is claimed.** `desc-routing` reads
**+0.00 (saturated)** and cannot distinguish two descriptions; the AUDIT arm remains
+0.00 across seven instruments.

**Activation, not content.** A real ~25-turn session doing upstream contribution work
invoked **zero** `sota-*` skills. The router body — which already contained rules that
would have caught the worst error — was never read, so its quality was irrelevant. Only
the frontmatter `description` auto-loads
([Agent Skills docs](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview):
*"until a Skill is triggered, only its name and description occupy context"*), which makes
the description the entire trigger classifier and everything downstream dead weight until
it fires.

### Added

- **Router description now covers code you do not own** — reviewing a pull request or
  diff, responding to code review, evaluating someone else's patch, preparing an upstream
  contribution, *including mid-session once you are already reading source, a diff or CI
  config*. The old verbs all assumed you own the codebase. Paid for by cutting the
  31-domain enumeration (**−445 chars**), which duplicated the routing table in the body;
  the description is a matcher, and verbs like `diff`/`upstream`/`review` match harder
  than 31 nouns. Net **951/1024**, recovering 73 chars of headroom against invariant 4.
- **Principle 7 — restate from the artifact, never from your own summary.** Principle 0
  listed what does *not* validate (training data, plausibility, "the rules file says so")
  and never named the commonest one: **your own earlier prose in this session**.
- **Principle 8 — publishing under someone else's name raises the bar**, with the full
  procedure as `sota-docs-workflow` rules/03 **§8**. The library assumed findings go to
  the person who asked; a PR comment, issue or commit message posted upstream is public,
  attributed and permanent. Nothing covered that. (`llm-engineering` rules/04's approval
  gates are about agents you *build*; rules/03 §3's "ask, don't assert" is a tone rule.)
- **Falsification precondition on principle 0** — state what result would falsify a claim
  *before* measuring; if none could, read the deciding code path instead of benchmarking
  symptoms.

### Fixed

- **The shipped hook buried its own routing rule.** `install.sh`'s `HOOK_CMD` put routing
  in a subordinate clause after two numbered rules. In the session above, rules (1) and
  (2) were obeyed every turn and the routing clause was dropped every turn — same text,
  same repetition, opposite outcome. Routing is now **numbered rule (3)** of equal weight,
  and it is **recoverable**: *"If you have already read code this session without routing,
  route now."*
- **A reworded hook silently stopped receiving updates.** `HOOK_SIG` was
  `"sota standing rules:"` — the first three words of the message — so a user who
  reworded the opening un-managed their own hook, and `--update` would then **add a second
  hook** rather than refresh it. Verified against a real install with the exact `jq`
  `install.sh` runs. The marker is now **`sota-* skills`**, a phrase present in every
  version ever shipped and in hand-edited variants; tested to match those and to ignore an
  unrelated hook.
- **Three different hook texts** existed across `README.md`, `install.sh` and installed
  configs. The README now shows exactly what `install.sh` writes, and documents that
  hand-edits must keep the `sota-* skills` marker.

### Changed

- `skills/sota/SKILL.md` reflowed (library map, cross-cutting rules, AUDIT workflow) from
  ~72 to ~98 columns to buy the lines for principles 7 and 8 — content unchanged, **491/500**.

**Nothing here is measured; no lift is claimed.** The repo's one adjacent instrument, the
`desc-routing` eval, reads **+0.00 (saturated)** and cannot distinguish these descriptions.

**Proving the gate can fail.** v1.21.1 shipped two known gaps in our own CI and wrote
them down as ROADMAP #8 and #9. Both are now closed, and the second one justified
itself within a minute of first running.

### Added

- **Invariant 15 — the router's library map lists every rules file, both
  directions.** Invariant 7 proves every *skill* is in the map; invariant 10 proves
  every rules file is indexed by its *own* `SKILL.md`. Neither reads the map's
  **contents**, which is how `sota-code-security/rules/11` sat unlisted in
  `skills/sota/SKILL.md` from **v1.19.8 to v1.21.0** with all fourteen checks green.
  The check compares the `NN` numbers the map enumerates per skill against
  `skills/<skill>/rules/NN-*.md` and reports a file missing from the map *and* a map
  entry naming a file that does not exist. The number is anchored to a list position
  so a title containing digits cannot be misread — `02 NIST 800-53/800-171` yields
  `02`, never `80` or `53`. **Watched to fail first**, per the script's own header:
  once by recreating the real defect, once on its inverse, then restored.
- **`scripts/check-negative-controls.sh` — a negative control for our own gates**,
  running in CI as its own job. `check-invariants.sh` passing proves the *tree* is
  clean; it has never proved the *checks* still work, and those two states print
  identically. The harness injects a known-bad per invariant into a disposable git
  worktree and requires **the intended check** to be the one that complains — a
  non-zero exit for any other reason is a **FALSE PASS**, not a catch. It runs a
  positive control first (clean copy must pass, else abort rather than report), and
  copies in the working-tree gate and byte-compares it, because a worktree at `HEAD`
  would otherwise test the *committed* gate rather than the one being edited.
  Covers invariants 1, 2, 6, 10, 15; states plainly that the diff-, history- and
  release-shaped checks are **not** covered.

### Why the second one earned its keep immediately

On its **first run** the harness reported a FALSE PASS against its own probe 15.
`git clean` does not remove *staged* files, so a fixture added by probe 10 leaked
into the next mutation, which then failed on the file-count check instead of the
check it targeted. **A harness that accepted any non-zero exit would have printed
`5/5 caught` and been wrong about one of them** — precisely the `rules/12` §2.1
"instrument that cannot fail" mode, caught in our own instrument by the one
assertion added to catch it. Fixed with `git reset --hard` (which clears the index)
plus a re-copy and re-compare of the gate, since the reset also reverts it.

### Changed

- Invariant count **14 → 15** across `AGENTS.md` (table + prose),
  `CONTRIBUTING.md` (numbered list + a new "proving the gate can still fail"
  section) and `docs/MAINTENANCE.md`. `docs/ROADMAP.md` line 426 says "14 checks"
  about **`verify-setup.sh`**, a different script, and was deliberately left alone.
- `AGENTS.md`'s "two gaps in the gates, known and unfixed" paragraph — added one
  release ago — was **false as of this change** and now records both as closed.
- ROADMAP #8/#9 struck through with what shipped; `docs/CONVENTIONS-LEDGER.md`
  moves both candidates from "gateable but not gated" (2 → **0**) to gated, and
  records that the doctrine-only candidate is no longer doctrine-only.

**Nothing here is measured; no lift is claimed.**

## [1.21.1] - 2026-08-05

**The inert-control release — three days of "the rule was there, the probe wasn't."**
An external audit spec (seven classes beyond our five) and two commissioned research
reports were taken in, and the recurring finding was the same each time: the library
*stated the BUILD rule* and had never written the **AUDIT probe**. It said "unit tests
touch no sockets" in three places and offered no way to find out that they do; it
governed the *numbers* a tool prints and not the *words*; it declared instruments to be
controls without ever turning that recursion on **guards**. The inert-control family is
now three files — `rules/10` catalogs, `rules/11` sweeps, **`rules/12` proves a control
works and distrusts whatever did the proving.**

**Front door checked:** negative control · metamorphic · oracle problem · rules/12

**Nothing here is measured; no lift is claimed for any of it.** The AUDIT arm remains
at +0.00 across seven instruments, and none of this changes that.

**Naming the prior art, and the four gaps two research reports found.** Two
commissioned reports on inert controls were evaluated against the tree. They agree
on the headline — the missing layer is a control shown *capable of failing* — and
they are not of equal quality: one misquotes NIST SSDF PO.3.3, over-generalises the
formal-verification vacuity statistic from hardware to software, and sources
aviation self-test to Scribd uploads. Every claim that became library text was
checked against a primary source first, which is why four gaps landed out of
thirteen proposals. Full verdicts, both rejections, and the misquote are in
[docs/ADOPTION-LOG.md](docs/ADOPTION-LOG.md) (entry 2026-08-05).

**Nothing here is measured; no lift is claimed for any of it.**

### Added

- **`rules/12` §3 — per-target kill verification.** A guard protects a
  *population*. Watching it reject one member proves the predicate can fire and
  says nothing about the other 19; the real shape is a tripwire that fired for 2
  of 20 targets and stayed green for 18, indistinguishable from full coverage on
  any single-instance test. Inject the defect into **each** member. For a security
  gate the bar is a **100% kill rate** — unlike a code mutation score, where
  surviving mutants are triaged and a number below 1.0 is normal.
- **`rules/12` §2.4 — evidence the subject supplies about itself.** An instrument
  that accepts the evaluated party's own report is transcribing, not measuring.
  The anchor is now measured: across 1.5M assets and 128K agents, **"over 84% of
  approved assets bypass quality checks using vacuous tests (e.g. `console.log()`)"**
  ([arXiv:2605.25815](https://arxiv.org/abs/2605.25815)) — the platform accepted
  each agent's own execution log as proof. Notably the *other* report asserts no
  such corpus exists; this one found it.
- **`rules/11` §2.6 — when you cannot state the right answer, state how it must
  change.** A **metamorphic relation** as a liveness oracle for a tool: commit a
  fixture with N known items, assert the count is N, assert it rises when you add
  one. The only diagnostic in that file that catches an analyser emitting an
  empty-but-well-formed artifact while exiting 0.
- **`sota-devsecops` rules/05 §5.6 — what the standards ask for, and the one thing
  none of them ask.** SSDF **PW.8.2**/**PO.3.3** and CRA **Annex VII** require a
  record that the scan *ran*; OpenSSF Scorecard's SAST check detects tool
  *presence* only, and its Dependency-Update-Tool check says outright it "does not
  ensure that the tool is run". **None require evidence the gate can fail** — SLSA
  will sign provenance for a scanner configured to scan zero files. So a passing
  compliance check is evidence of process, not protection, and the negative
  control has to be a house rule.

### Changed

- **The cross-discipline lineage is now named.** The library had described proof
  tests (IEC 61508's dangerous-undetected framing), positive controls, aviation
  built-in test, poka-yoke, **vacuous satisfaction** (Ball & Kupferman, quoting
  Beer et al. on hardware verification) and **the test oracle problem** (Barr,
  Harman, McMinn, Shahbaz & Yoo, *IEEE TSE* 41(5):507–525, 2015) for months
  without using any of those words — `poka-yoke` and `oracle problem` returned
  **zero** hits across all 41 skills. Named in `rules/12` intro + §3 and
  `rules/11` §2.6.

### Rejected (recorded so they are not re-litigated)

- **A minimum mutation-score threshold in CI** — contrary to `sota-testing`
  rules/07 §7.2 ("never set a global percentage target") and rules/06 §6.3
  differential mutation, adopted 2026-07-24. The *per-gate* kill rate above is
  compatible and was adopted; a global score is not.
- **GSN / assurance-case notation** — a notation, not a mechanism, and its own
  cited critique (arguments that "assume the conclusion") describes what
  `sota/rules/01` §7 adversarial refutation already prevents.

### Not verified, and therefore not asserted

IEC 61508 §3.8.5/§3.8.6 clause text is paywalled — the *concept* is named and no
clause number is quoted. The CRA Annex VII **point number** was not confirmed
(EUR-Lex returned only recitals); the sentence was verified against published
copies of the regulation, and `rules/05` says so at the point of use.

**The rules/12 split — the inert-control family gets a third file.** The previous
entry below shipped `rules/10` and `rules/11` at 493 and 495 of the 500-line cap and
said plainly that the next addition needed a split rather than another squeeze. This
is that split, and the boundary is not arbitrary: rules/10 catalogs inert controls,
rules/11 sweeps for them at scale, and **rules/12 is the third move — proving a
specific control works, then turning the same suspicion on everything that did the
proving.** That layer was previously split across two files (a mutation procedure at
the end of one, an instrument section at the end of the other) and belonged together.

### Added

- **`sota-code-security` rules/12 — Verifying the Verifier** (191 lines). Composed
  from `rules/10` §3 (the mutation probe for a security control) and `rules/11` §7
  (your instrument is a control), plus the **guard that is an instance of what it
  guards** promoted from a bullet to its own §3 with all three forms written out:
  the predicate the defect satisfies (`"auth=" in line` passes on `auth=None`), the
  guard nested in another gate's success branch, and the denominator counting only
  survivors. Its organising asymmetry: a broken feature produces a complaint, but a
  **broken verifier produces a green tick or a number**, and both get believed.
- **`rules/11` §7 "Then turn the lens around"** — a short hand-off replacing the
  moved section, stating the rule that motivates the file: a finding produced by an
  unvalidated instrument is not yet a finding.

### Changed

- **`rules/10` renumbered**: §3 (vacuous tests) moved out, so §4 → §3 (degradation
  helper) and §5 → §4 (evidence rules). All live cross-references repointed —
  `rules/11` ×4, `sota-devsecops` rules/03, README, `docs/CONVENTIONS-LEDGER.md`,
  `evals/README.md` ×2, and a comment in `scripts/check-invariants.sh`. Historical
  CHANGELOG and ADOPTION-LOG entries were deliberately **not** rewritten: they
  record what shipped at the version they describe.
- **`### 7.1 Four failure modes` listed five bullets** — count-rot introduced by the
  previous entry when the guard bullet was added without updating the heading. Fixed
  structurally rather than by editing the number: the guard is now its own section
  and 7.1 (`rules/12` §2.1) is back to four.
- **The router's library map had never listed `rules/11`.** `skills/sota/SKILL.md`
  stopped at "10 silent control failure"; it now lists 10, 11 and 12. Invariant 7
  gates skills against the router, not *rules files*, so this drifted unnoticed —
  and `sota/SKILL.md` is itself at exactly 500 lines, so the entry was rewritten to
  fit the same four lines rather than growing the file.
- **`rules/11` §2.2 — the runners disagree, which is the point.** Both verified by
  running them: `go test ./...` over a package with no test files **exits 0**, while
  `pytest` on the same empty scope **exits 5** — as it does for a file with no test
  functions and for a `-k` selector that deselects everything (pytest 9.1.1). One
  fails closed, one fails green, so no folklore about "runners exit 0 when they find
  nothing" tells you which you have. (The previous entry deliberately omitted the
  pytest half as unverified; it is now measured.)
- README file count 297 → **298** (invariant 6 again), and the "your own scorer"
  class now points at `rules/12`.

### Family headroom after the split

`rules/10` 468, `rules/11` 415, `rules/12` 191 — from 12 lines of combined headroom
to 426.

**The audit half of a rule we already had.** An external inert-control audit spec
(seven classes beyond our five) was evaluated against the tree class by class. Two
were already covered end to end and stay rejected; the rest split into a pattern
worth naming: **we had stated the build rule and never written the probe.** The
library said "unit tests touch no sockets" in three places and offered no way to
find out that they do; it governed the *numbers* a tool prints and not the *words*;
it declared instruments to be controls without ever turning that recursion on
guards. Full reasoning, including the five candidates rejected as already ours, is
in [docs/ADOPTION-LOG.md](docs/ADOPTION-LOG.md) (entry 2026-08-04).

**Nothing here is measured; no lift is claimed for any of it.**

### Added

- **`sota-code-security` rules/10 §2.10 — unearned claims are words, not just
  numbers.** The section governed literals in reporting output. It now also
  governs the verbs: `verified`, `confirmed`, `reachable from`, `tainted`,
  `sanitized`, and any severity or confidence set from a constant. The test is
  "which line would have to succeed for this word to be true, and can I make that
  line fail?" — with both traps stated, because keyword-hedging every message
  saying "tainted" leaves the identical claim phrased "reachable from input", and
  "TLS certificate not verified" is correct English describing the analysed code.
- **`sota-code-security` rules/10 §2.14 — a control parked in observe-only mode.**
  Kyverno `Audit`, PSA `warn`, WAF detection-only, `SCMP_ACT_LOG`, CSP
  report-only, DMARC `p=none`, `--soft-fail`. Each is correct as a rollout *stage*
  and inert as a destination, and renders identically to an enforcing control on
  every dashboard. Ships with an owner and an expiry, enforced somewhere that
  fails — the discipline `sota-testing` rules/07 §7.1 puts on a quarantined test.
  The staged ladders already existed in `sota-devsecops` rules/07 and
  `sota-network-security` rules/06; the inert-control framing did not.
- **`sota-code-security` rules/11 §3.4 — contract drift by interaction.** Neither
  component is wrong: a producer change silently alters a layout its consumer
  depends on, and both sides' isolation tests pass while the seam is broken. The
  distinguishing feature is that **no schema declares this seam**, so nothing
  exists for a registry or compat check to compare — every contract rule we own
  presumes a declared contract. The high-yield trigger is a config-level backend
  or frontend swap that changes the output layout as a side effect. Rule: run the
  consumer on the producer's real output before merging.
- **`sota-code-security` rules/11 §7.1 — the guard that is an instance of what it
  guards.** §7 already said an instrument is a control; it never turned the
  recursion on guards. Three forms: a coverage test whose *scope* is narrower than
  the population **and** whose *predicate* the defect satisfies (`"auth=" in line`
  passes on `auth=None`); a tripwire nested inside another gate's success branch;
  a denominator counting only the items that survived earlier filtering. §2.2
  catches an *empty* scope — this catches one merely wrong, and a predicate merely
  weak.
- **`sota-code-security` rules/11 §7.2 — three rules for the auditor's own
  instrument.** Sample and read before you count (a regex over prose reported 50
  unearned claims where reading found 8); a control validated on inputs that
  **cannot** produce the failure proves nothing, which is the negative control's
  twin; when a wrapper reports an empty reason, go one layer down.
- **`sota-code-security` rules/11 §6 — run every script before reading any of
  them.** A measurement tool nobody has executed this quarter is presumed dead
  until it prints something; the ones needing credentials, a daemon, a rules
  directory or a network fail in precisely the way a clean result looks, and one
  environment change kills them all at once.
- **`sota-testing` rules/02 §2.6 — prove hermeticity, don't assert it.** Block
  egress and run the suite; anything that fails was not the unit test it claimed
  to be. What this catches is not a slow test but one *passing for the wrong
  reason*, its usual mechanism being a config object the SUT never reads (it
  resolves from the environment instead — `rules/11` §6.7). Plus: check each
  surviving assertion against the test's own **name**.
- **`sota-testing` rules/02 §2.7 — resource optimism** added as its own smell, and
  **mystery guest** restored to its standard external-resource sense. Ours had
  narrowed a standard catalog term to a readability defect — record rot in our own
  file, found while auditing for it.

### Changed

- **`rules/10` §2.13 now cites the platform mechanic.** Per
  [GitHub Docs](https://docs.github.com/en/pull-requests/reference/status-checks),
  a **skipped job reports its status as *Success*** and "will not prevent a pull
  request from merging, even if it is a required check" — strictly worse than
  §2.13's existing "all-skipped is not all-green". A required gate whose `if:`
  condition stops matching turns green, not pending.
- **`rules/11` §2.2 gained the instance everyone meets.** `go test ./...` over a
  package with no test files prints `? x [no test files]` and **exits 0**
  (verified this session). Gate on a floor for tests actually executed, never on
  the runner's exit code — and check *your* runner rather than assuming, since
  they differ.
- `rules/11` §3 is now "**Four** classes rules/10 does not cover", with the
  matching count in `rules/10`'s header pointer; both `SKILL.md` routing rows and
  the README's `~62k lines` figure updated (invariant 6 caught that one).

### Note for the next contributor

`rules/10` and `rules/11` now sit at **493** and **495** of the 500-line cap. That
pair is effectively full: the next addition to this family needs a `rules/12`
split, not another round of trimming.

## [1.21.0] - 2026-08-03

**The output-you-can-read release.** Nothing the installer *does* changed — what changed
is that you can tell its actions apart. Every line it printed was the same two-space
grey, so "created your `CLAUDE.md`" and "already up to date" were indistinguishable at a
glance; and the one command everybody needs after the first day — updating — existed only
as a *flag* on the install command, which is discoverable if you already know it is there.

**Front door checked:** update.sh · --color · NO_COLOR

**Nothing here is measured; no lift is claimed for any of it.**

### Added

- **`scripts/update.sh`** — the update path was reachable only as a *flag*
  (`install.sh --update`), which is discoverable if you already know it exists. The new
  script is a **pure `exec` forwarder** (`exec install.sh --update "$@"`) and holds no
  logic of its own by design: a wrapper carrying its own copy of the update rules is a
  wrapper that drifts from them. Every install.sh flag still works
  (`update.sh --yes`, `--project DIR`, `--no-color`, …). The three places that named the
  old command — the installer's closing hint, the "upstream is ahead" line, and the
  SessionStart update reminder — now point at `scripts/update.sh`.

### Changed

- **`scripts/install.sh` output is colour- and emoji-coded.** The installer printed one
  undifferentiated wall of two-space-indented lines, so "created your CLAUDE.md" and
  "already up to date" looked identical and the sections (update / skills / routing /
  hygiene) had no visible boundary. It now prints emoji section headers and three
  distinct line kinds — `✓` green (something was done), `↻` cyan (changed, or you should
  act), `·` dim (a no-op or context) — with `⚠ warning:` and `✗ error:` on stderr.
  **The decoration is never the message**: every line still says in words what it means,
  the `warning:`/`error:` prefixes stay, and the glyphs degrade to ASCII (`+ ~ - ! x`).
- **…and it turns itself off, per stream** (`sota-cli-ux` rules/02 §4). Colour requires a
  terminal on *that* stream, `TERM` set and not `dumb`; `NO_COLOR` (non-empty) disables,
  `FORCE_COLOR`/`CLICOLOR_FORCE` re-enables, and the new **`--color=always|never|auto`**
  (plus `--no-color`) beats both. Emoji additionally require a UTF-8 locale, so a C-locale
  box gets ASCII markers rather than mojibake. Verified by running the installer under a
  pty, piped, with stdout redirected but stderr on the tty, and with each of `NO_COLOR`,
  `TERM=dumb`, `LC_ALL=C` and `--color=always`.

## [1.20.1] - 2026-08-03

**The don't-do-the-thing release.** Four questions answered with evidence instead of
reasoning, and three answers were *no*: long rules files do **not** need a table of
contents (242-file sweep cancelled), a **synthetic** large-repo fixture **cannot** test
audit skill (built twice, ruled out), and the router should **not** be restructured to
hit a token recommendation. The fourth was yes: §2b's front-door check **can** be
gated — not by gating discovery, which is judgement, but by gating the declaration.

**Front door checked:** front door · duration

**Nothing here is measured; no lift is claimed for any of it.**

### Changed

- **`docs/ROADMAP.md` opens with *Start here next session*** — every actionable item in
  one ordered table with why it is not done and the first move, plus an explicit
  **do-not** list so nine settled decisions are not re-litigated. Added because this
  cycle's real output was largely *decisions not to act*, and those are worthless if the
  next session cannot find them.
- **This cycle's research is summarised in one block** instead of scattered across four
  documents: the TOC test, the size-limits table, the synthetic-fixture result, and how
  §2b's gate came unblocked.
- **Two stale claims in `evals/results/RESULTS.md` corrected.** It twice called the
  agentic large-repo audit *"the real remaining audit frontier"*; both are now qualified
  — a **synthetic** one is ruled out, and only a real repo with real defects could still
  test it.
- **`docs/ROADMAP.md`'s header and cycle range were stale** (*as of 2026-08-02*, "PRs
  #174–#176"); corrected.
- **README gained the two front-door sentences §2b's grep found missing** — the
  fourteenth invariant (the sentence claimed "Fourteen" while listing thirteen) and the
  eval duration baseline.

### Fixed

- **Invariant 14 caught two real defects on its own first release**, which is why it
  shipped before a cut rather than after one.
  - Its pattern was **unanchored**, so it also matched the format example quoted inside
    its own CHANGELOG entry; the two matches concatenated into a garbage "term". Now
    anchored to line start — a declaration is its own line, unindented and unbackticked.
  - It then rejected `sample size` as **declared but absent from this release's entry**,
    correctly: that capability shipped in v1.20.0. The anti-filler guard earned itself
    on first use.

### Added

- **The agentic large-repo audit was attempted, and a synthetic fixture cannot do it**
  ([BIG-REPO-AUDIT](evals/results/2026-08-03/BIG-REPO-AUDIT.md)). This was the one
  audit design the roadmap kept open after seven +0.00 results, on the theory that
  prior instruments saturated because code and question both fit one prompt.
  - Two fixture generations, **360+ files / ~95k tokens** each, six planted defects
    from classes this library owns. Bare-arm recall: **6/6, 6/6, 6/6** (v1) and
    **6/6, 5/6** (v2). At ceiling, with no library.
  - **The library arm was never run, and that is the disciplined call**: with the bare
    arm at ceiling there is no headroom, and the instrument is confounded, so any
    number would be uninterpretable. Publishing one would be worse than having none.
  - **The reason generalises, and is the actual finding.** In a synthetic corpus a
    planted defect is *by construction* a deviation from generated filler, and agents
    find deviations mechanically — v1 by file naming (*"the six seeded-looking
    modules"*), v2, after that tell was removed, by AST-normalising every method body:
    *"the only substantive code is six methods that deviate from the template."*
    **Scaling the repo makes the anomaly cheaper to find, not harder**, because more
    filler is a stronger baseline to diff against.
  - **The pre-registered prediction was wrong by ~2×** — bare 0.30–0.50 predicted,
    0.92–1.00 measured — and is reported as wrong, in the direction the repo's own
    prior evidence favoured and the prediction discounted.
  - Recorded as an **instrument failure, not a null**, and deliberately kept **off the
    scoreboard**. What would be needed: a *real* repository with *real* defects at a
    known commit, where the flaw is ordinary code someone believed was correct.
- **Two roadmap entries this cycle closed but left reading as open** are now marked:
  the front-door capability gate (invariant 14) and the clone-install update path
  (`update-reminder.sh`).

- **The eval runners now have a duration baseline, not just a printed duration.**
  Closes the open half of the duration item: every run appends to a git-ignored
  `evals/results/durations.tsv`, and the next run of the same runner prints the delta
  — `[run-completeness elapsed 12.3s over 7 cases | previous 380.0s — 30.9x faster
  (total)  <-- CHECK THIS: a large swing usually means the work changed, not the
  speed]`.
  - **Printing alone was never enough.** `sota-code-security` rules/11 §2.1's tell —
    a step that finishes far faster than its claimed work allows did not do the work
    — is a **comparison**, and there was nothing to compare against. It was
    *"visible only to a human reading two logs"*; it is now in the log you are
    already reading.
  - **A duration without a denominator is the same defect in time form.** "12s" says
    nothing; "12s over 7 cases" does. **7 of 12 runners** declare one via
    `note_work(len(cases), "cases")`; the other five have no single `cases = load…`
    line to hook, so their rows record `-` and print `[no denominator — bare seconds,
    weak evidence]` rather than being quietly compared. Differing corpus sizes are
    compared **per case**, and the line says which basis it used.
  - **The ledger is git-ignored, and that is correctness rather than convenience**: a
    duration is only comparable on the same machine and network, so committing one
    would invite exactly the cross-machine comparison it cannot support — and would
    dirty the tree on every local run.
  - **Printed, never gated**, consistent with `check-invariants.sh`'s own wall-time
    decision: these call a remote API whose latency is not ours, and a flaky gate
    gets disabled. **Fails open on every path** — corrupt ledger, unwritable
    location, and absent ledger were each tested by breaking them.
  - **The CI half of the item needed nothing built.** The GitHub API already returns
    `started_at`/`completed_at` per *step* (verified 2026-08-03:
    `Check invariants 21:48:18 → 21:48:20`), so per-step duration is already
    observable. Recorded rather than reimplemented.
  - Verified end-to-end on the two `--selftest` paths CI runs without an API key —
    both still PASS, with correct denominators (dead-path **4**, reimplement **10**,
    matching their real case counts) — plus `py_compile` across `evals/` and
    `test_scoring.py` still green at 38 checks.

- **Invariant 14 — a release declares its front-door terms, and they resolve.**
  Closes the last actionable candidate in
  [docs/CONVENTIONS-LEDGER.md](docs/CONVENTIONS-LEDGER.md), which had it **blocked**
  on *"needs a machine-readable capability list per release"*.
  - **That objection was right, and is still right: discovery cannot be gated.**
    Deciding what counts as a capability is judgement. What *can* be gated is the
    **declaration** — the same move invariant 11 makes for `LAST-VERIFIED`, where
    the escape is a claim that must be *true*. A release adds
    `**Front door checked:** term · term` to its CHANGELOG section and the gate
    proves every term resolves in `README.md`/`docs/INDEX.md` **and** appears in
    that release's own entry — so a filler word cannot buy a pass.
  - **Fires only when `VERSION` changes**, so it adds nothing to an ordinary PR.
    The problem it fixes is release-time: invariant 6 fails on a wrong *number* in
    the README, and nothing failed on a *capability* that never got a sentence —
    five shipped across v1.17.0–v1.19.7 with zero README hits.
  - **Watched to fail on five paths**: ordinary PR (skips, no ceremony), release
    with no declaration (fails, naming the required line), a term in no front door
    (fails, naming the term), a term absent from the release's own entry (fails),
    and a valid release (passes, `ok (2 terms declared, all resolve)`).
  - **The fail-watch found a real bug rather than confirming behaviour.** The first
    cut read the *topmost* `## [` section, which is `[Unreleased]` when one still
    sits above the new entry — so it reported "no declaration" for a release that
    had one. It now selects the section matching `VERSION`. Case C failing for the
    wrong reason is what exposed it.

### Changed

- **One decision table now settles every size question.**
  `docs/CONTEXT-MANAGEMENT.md` gains *Size limits: what to actually do* — all ten
  limits that govern this library, each marked **hard** or **recommendation**,
  each with its verified source and a standing decision. Written because this
  cycle produced findings across four documents and the useful form of that is one
  table, not four narratives. The load-bearing entries: `description` is at
  **1024/1024** with no slack, the router is at **500/500 lines** with no slack,
  long `rules/*.md` are **correct by design**, and the router's 2× token overrun is
  **accepted rather than restructured** — trimming it would break
  `ROUTER_BUILD_SHA` and invalidate comparability with every historical +0.39 run,
  while the compaction truncation it causes is self-healing on the next invocation.
- **Tested whether long rules files need a table of contents. They don't — so the
  242-file sweep is off the table.** Anthropic's skill-authoring guidance says
  reference files over 100 lines should carry a TOC *"even when previewing with
  partial reads"*; **242 of this repo's rules files exceed 100 lines and none has
  one**. Rather than assume, the *mechanism* was tested: four arms, one agent each,
  an unguessable canary constant so a hit proves retrieval and not prior knowledge,
  the prompt silent about position/length/TOCs, and the arm kept out of every path
  (opaque workspace IDs — two agents in an earlier study read their arm from a
  directory name).
  - Control (434 lines, canary at 99% depth, no TOC): **found**. With a TOC:
    **found**. Stress at **1,719 lines / 92 KB**, 4× the repo's longest rules file:
    **found**, with the agent reporting the canary's exact line range.
  - **The positive control is what makes it readable**: moving the canary to 1%
    depth changed nothing, so there was no depth effect for a TOC to correct. Every
    agent read the file whole — two said so unprompted. The TOC's only measurable
    effect was **+183 tokens** of context.
  - **Limits stated rather than implied**: *n* = 1 per arm, a pilot, deliberately
    **not** on the scoreboard. It covers the `Read`-tool path on a directly named
    file; the guidance's own trigger is *nested* references, which this library does
    not have — `SKILL.md → rules/NN.md` is already the "one level deep" structure the
    same guidance prescribes.

### Fixed

- **A skill description violated a documented constraint, found by applying this
  repo's own absence-claim rule to itself.** `sota-dotnet`'s `description` contained
  `Span<T>/Memory<T>` — C# generics, but `<T>` is also a well-formed XML start tag,
  and Anthropic's Agent Skills reference states that `name` and `description`
  *"Cannot contain XML tags"*. Rewritten as "Span and Memory" (965 → 963 chars).
  - **How it surfaced is the point.** The claim under test was *"there is no hard
    size cap for skills"* — an **absence claim**, and `skills/sota/rules/01` §5/§7
    require a widened search **plus a second independent method**, because a narrow
    search and a true absence are indistinguishable. The first source
    (`agentskills.io/specification`) does not mention XML tags at all. Only the
    second (`platform.claude.com` Agent Skills reference) carries that constraint —
    and a reserved-word rule for `name` (`anthropic`, `claude`) that the spec page
    also omits. One source would have missed both.
  - The absence claim itself **held**, and the second source states it more
    strongly than the first: *"No practical limit on bundled content… There's no
    context penalty for bundled content that isn't used."*
- **Invariant 4 now checks both new constraints** — an XML tag in `name` or
  `description`, and a reserved word in `name`. Watched to fail on the real defect
  (`XML TAG in description ['<T>', '<T>']`), on a synthetic `claude-golang` name
  (`RESERVED WORD 'claude'`), and to pass on the clean tree. It stays inside
  invariant 4 rather than becoming invariant 14: same file, same parse, same
  failure mode — a description a loader silently mangles or rejects.

### Changed

- **`AGENTS.md` is back under the platform's 200-line target** (234 → **170**
  lines, 15.4 → 10.9 KiB). `CLAUDE.md` and `GEMINI.md` symlink to it, so it loads
  into **every** session, and the Claude Code memory documentation is explicit:
  *"target under 200 lines per CLAUDE.md file. Longer files consume more context
  and reduce adherence."* There is **no hard limit** — *"CLAUDE.md files are loaded
  in full regardless of length"* — so nothing was truncating; adherence was the
  cost. The file had crossed the target while gaining invariants 12 and 13.
  - The 128-line invariant section became a **13-row table**, one line each. No
    detail was lost: the rationale and the incident behind every invariant already
    live in `check-invariants.sh`'s own header (the point of use), and the
    practical "what this means for your PR" version in `CONTRIBUTING.md` — both
    verified to carry all 13 before the cut.
  - The file now states its own constraint, because it is the one file in the repo
    where invariant 1 does *not* apply and a **different, ungated** limit does.
    That is the `docs/CONVENTIONS-LEDGER.md` "unwritten convention" class again:
    a real constraint, documented nowhere in the repo, discovered by exceeding it.
- **The `rules/*.md` files were checked against the same target and deliberately
  left alone.** The 200-line figure governs *always-loaded* context. Skills load on
  demand — *"unlike CLAUDE.md content, a skill's body loads only when it's used, so
  long reference material costs almost nothing until you need it"* — and their
  documented cap is *"keep `SKILL.md` under 500 lines; move detailed reference
  material to separate files"*, which is invariant 1 exactly, with `rules/*.md`
  being those separate files. **162 of 256 rules files exceed 200 lines and that is
  correct by design**; splitting them would work against the documented model.
- **Validated against the Agent Skills spec: there is no byte cap for skills, but
  the 500-line cap is a loose proxy for the one budget that exists.** Prompted by
  the observation that `MEMORY.md`'s hard cap is *"200 lines **or** 25KB, whichever
  comes first"* — so a few long lines can exhaust it well under 200 lines. Checked
  whether the same shape applies to skills:
  - **It does not, as a hard cap.** The spec's only hard limits are on frontmatter
    (`name` ≤ 64, `description` ≤ **1024** — which confirms invariant 4 — and
    `compatibility` ≤ 500). Of the body it says outright: *"There are no format
    restrictions."* Nothing truncates a skill at load. And the 200-line/25KB rule is
    scoped in the memory docs to `MEMORY.md` alone: *"This limit applies only to
    `MEMORY.md`. CLAUDE.md files are loaded in full regardless of length."*
  - **But the budget it stands in for is stated in tokens, not lines**:
    *"Instructions (< 5000 tokens recommended)"*. Measured across this repo's **297**
    skill files, line density varies **3.3×** (38–127 bytes/line, median 57), so a
    500-line file lands anywhere between **~4,750 and ~15,870 tokens** — the median
    density already puts it 42% over. **12 files exceed ~5,000 tokens and 11 of them
    pass invariant 1 comfortably** (`sota-mobile/rules/07-swift-language.md`: 254
    lines, half the cap, ~6,737 tokens).
  - **Exactly one file breaches the recommendation where it applies** — the
    `SKILL.md` body: `skills/sota/SKILL.md` at **~10,211 tokens**, 2× the budget,
    at 500/500 lines with no slack. `rules/*.md` are stage-3 resources, for which
    the spec gives no number.
  - **Logged, not gated.** A byte-or-token check passes all three ledger filters but
    would fail on `main` today, and the only fix is trimming a router with no line
    slack — a design decision. Recorded in `docs/ROADMAP.md` with the explicit
    caveat that `bytes/4` is a heuristic and a real tokenizer should be used before
    acting on any specific number.
- **`docs/CONTEXT-MANAGEMENT.md` records a platform behaviour none of the six
  defenses covers.** Auto-compaction *"re-attaches the most recent invocation of
  each skill after the summary, keeping the **first 5,000 tokens of each**"*, with a
  combined 25,000-token budget. The six defenses fight *attention*; this is
  *deletion*. By a rough `bytes/4` estimate the router (~10,200 tokens) and two
  rules files exceed the per-skill cut. **Explicitly recorded as unverified** — read
  off the docs and a byte heuristic, not observed in a session — and deliberately
  not acted on, since the router has no line slack and the honest next step is to
  watch a real compaction first.

- **`RELEASING.md`'s minor-vs-patch rule now matches 31 releases of practice.** It
  said *"adding a skill is a **minor** bump; fixes to existing content are a
  **patch**"* — whose first half is exceptionless and whose second half misleads,
  because it reads as *no new skill → patch*. Measured with `git ls-tree` across
  every tag: **6** skill-adding releases, **all 6 minor** (so a skill is
  *sufficient*), but **15 of 21 minors added no skill at all** (so it is never
  *necessary*). The rule that actually separates them, spot-checked against six
  releases: **minor when the library gains a new surface someone can *use*** — a
  skill, a script or command, a hook, a cross-tool integration (v1.9.0's
  `AGENTS.md` support), or a new eval instrument (v1.13.0, v1.14.0, v1.17.0,
  v1.18.0); **patch when the change lives inside surfaces that already exist** —
  rule text, docs, intakes, and, on the evidence, **a new CI invariant on its
  own**: invariants 8, 9 and 11 each shipped in a *patch*. Invariants 12 and 13
  rode a minor because that release also added two scripts and a hook. Tie-breaker
  recorded for the next cut: does a reader of the release notes gain something new
  to run? Found while cutting v1.20.0, where the old line would have argued for a
  patch.
- **`AGENTS.md` and `docs/INDEX.md` describe the setup check as the two halves it
  now is.** Both still framed it as a paste-in prompt, which had been true for four
  days: `scripts/verify-setup.sh` answers the mechanical half in a second and tells
  the agent which checks are left. Both now say to run the script first.

## [1.20.0] - 2026-08-02

**The reported-but-never-read release.** Every change here traces to the same
shape: a control that *was already printing what you needed* and nobody looked.
`gitleaks` prints `179 commits scanned` — in a shallow clone it prints `1` and
still exits 0. The scoreboard prints a `Samples` column — nothing checked a new
row filled it. The `how-it-works` diagram's source was fixed and the rendered PNG
the README actually embeds was not, so `main` served the corrected-and-still-wrong
claim all day. The eval runners printed no duration at all. Two invariants (12,
13), two scripts, and one CI fix later, the denominators are read.

The one deliberate inversion: the new update reminder reports **less** than it
could. It never phones home, because the value was the nudge, not the telemetry.

**Nothing here is measured; no lift is claimed for any of it.**

### Added

- **`scripts/update-reminder.sh` — an occasional update nudge that makes no
  network request.** Closes the *push* half of the update-notification item, open
  since the 2026-07-28 cycle: symlinked skills update the moment you `git pull`,
  but nothing ever told you to pull, and the plugin's first-run notice is
  marker-guarded to fire once ever, so it is onboarding rather than a version
  channel.
  - **The phone-home question was dissolved, not answered.** The roadmap had this
    blocked on "a `SessionStart` version check reaches passive users but phones
    home — a deliberate privacy decision, not to be built without an explicit
    call." The resolution is that the *benefit* — reminding you updates exist —
    never needed the network. The hook cannot tell whether a new version exists,
    only how long since it last spoke. A real check from every session start would
    turn a documentation library into something that reports when and how often you
    work; you run the check instead, and it is one command.
  - **Verified, not asserted**: run under a `PATH` seeded with `curl`/`wget`/`git`/
    `nc`/`ssh` stubs that report any invocation, it makes **zero** attempts. The
    only external commands it uses are `find`, `tr`, `mkdir`, `printf`, `dirname`
    and `pwd`.
  - Silent on first run (a fresh install is current by definition), then at most one
    message every `SOTA_UPDATE_REMINDER_DAYS` days (default 14, `0` disables). TTL
    from the state file's **mtime** via `find -mtime` rather than date arithmetic,
    because GNU `date -d` and BSD/macOS `date -v` disagree.
  - **Fails open on every path**, because a `SessionStart` hook that errors degrades
    the session it is attached to: unwritable data dir, missing `VERSION`, and
    garbage in the interval env var were each tested and each exit 0.
  - Reaches **both** install paths — the plugin via `hooks/hooks.json`, clone
    installs via a new `setup_update_reminder` in `install.sh`. The installer path
    was tested against a `settings.json` already holding the user's *own*
    `SessionStart` hook: that hook and an unrelated `theme` key survive untouched,
    and a second run adds nothing (idempotent).
- **`scripts/verify-setup.sh` — the deterministic half of
  [docs/VERIFY-SETUP.md](docs/VERIFY-SETUP.md)**, open since the 2026-07-28 cycle.
  14 checks, strictly **read-only**, exit 1 on any FAIL: skills reachability and
  whether the *router* is among them, the three always-on routing layers reported
  separately, profile symlinks resolving, a licence under *any* name, which gate
  mechanisms exist, whether a hook is **installed** rather than merely configured,
  and — from real run conclusions — whether CI has ever *executed* and ever
  *rejected* anything. `--runs N` widens the run-history sample.
  - The read-only claim is **verified, not asserted**: hashing the file tree and
    `git status` before and after a full run shows both unchanged.
  - The three checks a script cannot do (agent-file content, whether its claims
    are still *true*, the routing dry-run) print as `N/A — judgement check` with a
    pointer to the prompt, so the split is visible where you run it rather than
    only in the doc.
  - **Writing it found a bug in itself.** Check 8 used `git grep`, which reads only
    **tracked** files — so an untracked `.pre-commit-config.yaml` configuring
    gitleaks was reported as *no secret scanning*. That is a false FAIL on exactly
    the case the doc names first ("on a repo you just scaffolded"), and it was found
    by running the fail path, not by reading the code. Now plain `grep`.
  - **It also validated its own UNVERIFIED vocabulary.** On this repo check 10b
    (*has CI ever rejected anything?*) reads UNVERIFIED at the default 60-run
    sample — 60/60 success — and turns up **1 failure at 200**. "Not in the last 60"
    really is not "never"; the sample size is printed for that reason.
- **`evals/_elapsed.py` — the eval runners report their wall time.** All 13 now
  print `[<runner> elapsed 12.3s]`, closing the runner half of the duration item.
  Registered with `atexit` so the line survives the `sys.exit(...)` several runners
  use on an empty corpus — the fast-exit case most worth timing — and written to
  **stderr** so a runner whose stdout is piped or parsed is not handed an extra
  line. **Printed, never gated**: these call a remote API whose latency is not ours,
  and a flaky gate gets disabled. Verified end-to-end on the two `--selftest` paths
  CI runs without an API key, plus `py_compile` across all of `evals/`.

### Removed

- **The `gh-sota` extension idea is cancelled, not deferred.** Its one real benefit
  was update notification, now delivered directly by the `SessionStart` reminder
  above — without a second repo, a shim, or a CLI nobody would invoke for a library
  used *inside* an agent session. The original blocker stands and is kept in the
  roadmap for why the shape never worked (gh requires a `gh-*` repo with a matching
  root executable, so it could not live here). Closed rather than left deferred: a
  deferred item whose rationale has died is indistinguishable, on a list, from a
  live one.

### Fixed

- **The secret scan reported a denominator nobody read.** `gitleaks` prints
  `179 commits scanned`, and the roadmap had carried *"still unexamined: what
  gitleaks reports as its scope"* since 2026-07-30. Examined: in a `--depth 1`
  clone of this repo it scans **1 of 179 commits**, prints `no leaks found`, and
  **exits 0** — a green secret scan over 0.5% of history, where `fetch-depth: 0`
  is the only thing preventing it and nothing asserts that. CI now asserts the
  scope.
  - The assertion keys on `git rev-parse --is-shallow-repository`, **not** on a
    commit count. `git rev-list --count HEAD` truncates to 1 in the same clone, so
    it degrades alongside the scan it would be checking; and the three available
    numbers disagree anyway (measured: rev-list HEAD **175**, rev-list --all
    **181**, gitleaks **179** — gitleaks walks refs beyond HEAD), so any equality
    test would be flaky, and a flaky gate gets disabled.
  - It also fails when gitleaks prints **no** `N commits scanned` line: an output
    format we can no longer parse means the scope is no longer verified, which must
    not read as a pass.
  - Watched to fail on four paths: shallow clone (exit 1), unparsable output (exit
    1), a degenerate 1-commit count on a non-shallow tree (exit 1), and the real
    repo (exit 0, `179 commits scanned`).

### Changed

- **The 500-line cap is stated as *instruction-files-only* everywhere it appears.**
  A file is capped **iff an agent loads it as instructions** — `skills/*/SKILL.md`
  and `skills/*/rules/*.md`, nothing else. README, CHANGELOG, `docs/`, `evals/`,
  `AGENTS.md` and the scripts have **no line cap at all** (decided 2026-07-15,
  PR #100). The scope was already correct in `check-invariants.sh`, `AGENTS.md`,
  `CONTRIBUTING.md`'s checklist and the README's contributing section, but five
  surfaces still read as a repo-wide rule and have been fixed: the README hero
  ("each file under 500 lines"), the pre-commit hook's own name, the
  `how-it-works` diagram, the router's opening paragraph, and
  `CONVENTIONS-LEDGER`'s enforced list. `AGENTS.md`, `CONTRIBUTING.md` and the
  script's header now lead with the rule in one line and say outright that any
  line-cap claim not scoped to skill files is stale.

  **Correction: the `how-it-works` fix reached the source and not the surface.**
  It edited `assets/how-it-works.html`, but the README embeds
  `assets/how-it-works.png`, which was last rendered in #55 (2026-07-09) and was
  not re-rendered — so every reader kept seeing `every file < 500 lines` while
  the diff, the commit message and the line above all reported the surface fixed.
  Rendered now; the same claim that opened this entry had been *counted* on a
  surface it never reached, which is the shape v1.19.9 is named for.
- **The `how-it-works` diagram shows the loop it describes.** The README hero
  argues the library is "a **loop**, not a prompt dump — route in only the rules a
  task needs, re-state them every turn, and re-check them *last* before shipping",
  and [docs/CONTEXT-MANAGEMENT.md](docs/CONTEXT-MANAGEMENT.md) documents six
  defenses behind that claim. The diagram drew a **one-way four-box pipeline** and
  showed exactly one of the six (stage 4's terminal self-check). It now carries a
  return path from stage 4 back to stage 2 for the per-prompt re-injection —
  labelled **optional · always-on**, because that layer is opt-in setup
  (`install.sh --routing`) and the diagram must not imply it ships on by default.
  The footer's always-on aside moved into that rail and now points at the six
  defenses. The repo URL was added to the header, since the image travels
  (LinkedIn, forks, docs) far from anything that links back.
- **`CONTRIBUTING.md` gained a "Rendered assets" section and a PR-checklist line**
  — `assets/*.png` are committed build outputs of the `*.html` beside them, nothing
  regenerates them, and the README embeds the image. The section carries the render
  command, the exact size per asset, the `file://`-is-blocked reason for serving
  over localhost, and the `sips` dimension check. Placed in `CONTRIBUTING.md`, not
  `RELEASING.md`: the failure happened in an ordinary docs PR, not at a release cut,
  so release-time guidance would have been guidance at the wrong point of use
  (v1.19.9's proximity finding, applied).
- **Invariant 12 — a rendered asset is never older than its source.** Every
  `assets/*.png` must be committed no earlier than the `assets/*.html` it renders.
  It passes all three [CONVENTIONS-LEDGER](docs/CONVENTIONS-LEDGER.md) filters (it
  had already failed, that same day; it fails silently, since nobody reads the HTML
  and the PNG looks fine — it just says the old thing; and it is checkable from
  `git log -1` alone).
  - **Commit times, not mtimes.** A fresh clone stamps every file with the checkout
    time, so an mtime comparison would pass on every CI runner while examining
    nothing — `rules/11` §2.2, built into the gate meant to prevent it. Equal
    timestamps pass: rendering in the same commit as the edit is the wanted
    behaviour, not a violation.
  - **Escape: `[no-render]` in the HTML's own commit subject**, for an edit that
    cannot change the output. A declaration rather than a heuristic, because
    nothing short of rendering both can distinguish a cosmetic HTML edit from a
    load-bearing one — and invariant 11 already learned that a gate firing on
    non-events gets waved through until it is decorative.
  - **Watched to fail on six paths before being trusted**, per the script's own
    "adding a check?" block: the real defect (a worktree at `0f08094`, the commit
    where the drift existed → exit 1), a live HTML-only commit (exit 1), an HTML
    with no committed PNG (exit 1), a drifted pathspec (`SCOPE EMPTY`, exit 1), the
    declared escape (exit 0), and current `main` (exit 0, `ok (2 asset pairs)`).
  - One earlier attempt at the fail-watch was **vacuous** and is recorded because
    it is the failure mode this repo keeps rediscovering: a `git reset --hard`
    reverted the still-uncommitted script, so two mutation cases ran against a
    build with no check 12 in it and printed nothing at all. Empty output — not a
    passing result — is what exposed it. The check is now committed before any
    mutation runs, and the mutations run in a throwaway worktree.
  - The first diagnostic printed `%cs` (date only) and so reported the **same date**
    on both lines of a same-day miss while asserting one was older. It prints full
    timestamps now: a finding that reads as a broken check is one people switch off.
- **Invariant 13 — every scoreboard row declares its sample size.** Each row of the
  results table in [evals/results/RESULTS.md](evals/results/RESULTS.md) must fill its
  `Samples` cell. A lift from one run is typographically identical to a lift from ten,
  and this repo has been burned twice: a **+0.07** retracted when the set grew 15 → 49,
  and a **+0.40** corrected to **+0.39** by a second run. Neither looked uncertain on
  the page.
  - Like invariant 10 it is a **regression guard** with no incident of its own — all
    10 rows pass today. It catches the *next* row added without an `n`, which is the
    cheap moment; the expensive moment is after the number has been quoted.
  - **Shape-driven, not position-driven**: it finds the table by its `Samples`
    **header** and checks that column in every data row beneath. So a renamed or
    dropped column fails closed (`SCOPE EMPTY`) rather than passing over zero rows —
    the drift a hardcoded column index sails straight past.
  - The loop reads from a **process substitution, not a pipe**. A `| while` runs in a
    subshell, so every `v13=1` set inside it would be discarded on exit: a gate that
    finds offenders, prints them, and still exits 0.
  - Watched to fail on four paths first: a blanked `Samples` cell (exit 1, naming the
    row), a renamed column (`SCOPE EMPTY`, exit 1), a missing scoreboard file
    (skipped, not assumed), and the clean tree (exit 0, `ok (10 scoreboard rows)`).
  - This closes the **last actionable candidate** in
    [docs/CONVENTIONS-LEDGER.md](docs/CONVENTIONS-LEDGER.md). One candidate remains
    (§2b's front-door grep) and is blocked on machine-readable capability names.
- **Five stale surfaces fixed, found by re-checking the ones this cycle touched.**
  - `README.md` still said **"Eleven invariants"** — missed by the earlier sweep
    because its grep was case-sensitive. Its list of what they cover also omitted
    four: rules-file indexing, the single `[Unreleased]`, `LAST-VERIFIED` pairing,
    and rendered-asset currency. Both fixed, and the list now names all thirteen
    areas rather than trailing off after six.
  - `docs/MAINTENANCE.md`'s structure row had its **count** bumped to 12 in the same
    breath as leaving its **parenthetical list** without the new check — a count that
    agrees with the script while the prose beside it does not.
  - `docs/INDEX.md` had **no route to the render procedure** added a day earlier: a
    documented procedure with no front-door row, which is `RELEASING.md` §2b's class
    applied to the index rather than the README.
  - `RELEASING.md`'s social-preview step described re-rendering by hand with no
    mention that **invariant 12 now enforces the commit-both half**, and no pointer
    to the fuller procedure in `CONTRIBUTING.md`.
  - `docs/ROADMAP.md`'s open-tasks header still read *as of 2026-08-01* and called
    §2b "the only other candidate" while the Samples guard was still listed as open.
- **Two stale invariant counts fixed.** `docs/MAINTENANCE.md` said
  `check-invariants.sh` runs **7 checks** and `docs/WHY-IT-WORKS.md` said **eight
  invariants**; both are **11** (the script prints its own count, so the drift was
  only ever in the prose). `docs/ROADMAP.md`'s `test_scoring.py` floor note now
  records that 25 has since risen to **38**.

## [1.19.9] - 2026-08-01

**The counted-as-a-layer release.** Five changes with one shape between them: a
control that is *counted* — in a threat model, in a release runbook, in a repo's
list of conventions — while being structurally unable to cover the case it is
counted for. A second-opinion classifier from the same model family. A TEE bought
to fix records that were never emitted. A rule written three times and still nearly
broken twice. **Nothing here is measured; no lift is claimed for any of it.**

### Added

- **`sota-code-security/rules/08` §1 — a same-class checker is not an independent
  layer.** A classifier, judge or "second opinion" tier drawn from the same model
  family as the system it guards shares that system's blind spots by construction:
  **common-cause failure**, so the two do not multiply into defence in depth however
  the diagram is drawn. Escalate-only cascades are worse *deductively*, not
  empirically — a tier that only sees inputs the primary scored **uncertain** cannot
  see one the primary scored **confidently wrong**, which is the failure it was added
  to catch; its marginal recall on the hard class is bounded by the primary's
  uncertainty coverage, not by its own accuracy, so a better second model does not fix
  it. The rule's demand is a measurement: marginal recall **on the hard class**, not on
  a mixed corpus where easy cases dominate the mean. Closes onto `rules/10` §1 — a
  layer that adds nothing on the class you care about is a control that looks enabled
  and does nothing. Same reasoning for any guard sharing a substrate (model family,
  tokenizer, training corpus, or the normalization step that produced the miss).
- **`sota-code-security/rules/04` §8 — a TEE does not fix a completeness gap.** §8
  already separated integrity from completeness for audit ledgers; this names the
  expensive wrong turn — reaching for confidential computing to fix *"records that were
  never emitted"*. CC protects a record's confidentiality and integrity once it exists;
  no hardware can compel a component to emit one. That is a **liveness** failure and
  sits outside the guarantee. Cross-refs `sota-confidential-computing` rules/01 §2
  (availability row) and rules/04 §7, which state it from the CC side — the new text
  makes it reachable from the crypto side, where the mistake is actually made.
- Audit-checklist entries for both, so each new rule is reachable from an audit pass.

- **`docs/CONVENTIONS-LEDGER.md`** — which repo conventions are enforced, which are
  prose, and why the rest should stay prose. Built after invariant 11, so the next
  documented-but-unenforced rule is found deliberately rather than by luck.
  Mechanically extracted from the five agent-facing docs: **49 raw entries, 8
  duplicates, 41 distinct**, of which **11** are invariants and **4** more are
  enforced inside the eval runners — so reading `check-invariants.sh` alone
  undercounts what this repo enforces by about a third.
  - It corrects an earlier estimate of "~122 conventions", which came from a loose
    regex matching any bold line or any line containing *must/never/always* — an
    over-count of roughly 3×, recorded so it is not repeated.
  - Applying three filters (has it already failed · does it fail silently · is it
    mechanically checkable) yields **one** actionable candidate, not the 2–4
    predicted: a regression guard requiring every scoreboard row to declare its
    sample size. The other candidate (§2b's front-door grep) stays **blocked** on
    needing machine-readable capability names.
  - For the ~18 judgment conventions the ledger argues against a fourth copy of the
    text and for **proximity**: `LAST-VERIFIED` failed while documented in three
    places, all far from the point of use.

- **`docs/INDEX.md`** reaches the reimplement case set, and the case file now
  carries the predictions written **before** any run existed — so if it is ever
  run, the pre-registration is the authoring session's, not one composed after
  seeing data. It also records, in advance, that a null there is the **eighth**
  and the conclusion is to stop rather than author a ninth.
- **`evals/cases/reimplement.jsonl` + `run-reimplement.py` — documentation, not a
  measured instrument.** Ten cases (5 disqualified / 5 legitimate) encoding the
  §3.9.4-vs-§3.9.6 conflict, with every legitimate case resembling a disqualified one
  so that *ratio-only* and *refuse-everything* both land at exactly **0.500** — a
  three-arm selftest in CI holds that, and four guards abort on an empty case file, a
  vacuous reason axis, a one-sided case file, and a report with no parsable lines
  (all four verified to exit non-zero). `test_scoring.py` grows to **38 checks**,
  including the row where the decision and reason metrics legitimately diverge, which
  is what a metric-conflating mutation dies on.

  **It has never been run and no number from it may be cited.** Seven audit
  instruments already read +0.00 and the roadmap records "do not build another
  audit-recall instrument"; an eighth run was declined. It is kept because building it
  produced the rule fix above, and the scorer stays so the case set stays checkable.

### Changed

- **README — the audit-class list grew from seven classes to eight.** The §2b
  front-door grep returned **0 hits** in `README.md` and `docs/INDEX.md` for every
  term this release added, the **second consecutive cut** where that happened *with
  the checklist item already written* — evidence the habit does not stick without the
  gate §2b still lacks. New class: **"Layers that were never layers"**, covering both
  additions above. `RELEASING.md` §2b now also says where such a fix belongs — the
  README is the front door for a rule-level capability; `docs/INDEX.md` indexes
  *documents*, so a new rule inside an existing file usually does not earn a row there.
- **`RELEASING.md`'s pre-tag `ADOPTION-LOG` check is now case-insensitive and
  bracket-tolerant** (`grep -ni '· \[\?unreleased'`). Two rows in this release were
  written `· [Unreleased]`, which the documented case-sensitive `grep -n '· unreleased'`
  **would not have matched** — a checklist step that silently matches nothing, in the
  release that is otherwise about exactly that.
- **`AGENTS.md`** gained a pointer to `docs/CONVENTIONS-LEDGER.md`, which shipped in
  v1.19.8 with no mention in the file every agent reads first, and records that the
  adoption ledger also takes proposals from **our own** sessions, not only outside repos.
- **`docs/ROADMAP.md` — one item was stale and is now marked superseded.** It said
  *"the BUILD-safe eval needs a thinner spec before it measures anything"*, while a
  closed item twenty lines above records that the thinner spec was written **and**
  tested and did not discriminate either. Kept for the diagnosis it holds; the
  remedy it proposes is done and did not work. Also records this cycle's items: the
  one remaining gateable convention (a Samples-column regression guard, low priority
  because it currently passes), §2b's grep still blocked, the reimplement set being
  documentation-never-run, and an explicit note **not** to "finish" the point-of-use
  work by relocating the other ~18 judgment conventions.
- **`scripts/check-freshness.sh`'s header caught up with its own parser** — it still
  described `LAST-VERIFIED` as holding only a date, after the parser was taught to
  strip `#` comments so the file could carry the rule that governs it. Now also
  points at invariant 11.

- **Three conventions moved to their point of use** — step 4 of the ledger plan,
  and the one step its data actually supported. The principle comes from a measured
  failure: `LAST-VERIFIED` was documented in three places and mentioned across nine
  files, and two sessions still nearly broke it. **Proximity beats repetition.**
  - **`LAST-VERIFIED` now carries its own rule.** This required teaching
    `check-freshness.sh` to strip comment lines — its strict
    `tr -d '[:space:]'` + `YYYY-MM-DD` glob was *precisely why* the rule could not
    live in the file it governs. Both rejection paths were re-verified after the
    change (comments-only and comment-plus-malformed-date each still exit 1), because
    a parser loosened until it accepts anything is worse than the problem it solved.
  - **`scripts/check-invariants.sh` gained an "adding a check?" block.** The file had
    **zero** guidance on adding a check, despite being where every check is added:
    watch it fail first (invariant 9's first cut printed its heading and nothing else
    — a `grep -m 1` on a pipe SIGPIPE'd the upstream `printf`), print your
    denominator and fail on an empty scope, and skip rather than guess when a
    prerequisite is missing.
  - **All three live-agent runners now carry the A/B conventions** they govern —
    that a bare arm is not bare by default (sub-agents inherit the agent files and 2
    of 3 loaded the router anyway), and that the arm must never be encoded in a path
    or label. None of the three carried this before.

  **The move exposed an imprecision in invariant 11, fixed in the same change.**
  The gate keyed on the *file* changing rather than the *stamp* changing — so this
  very commit, which only added comments, demanded an escape and got one
  reflexively. A gate that fires on non-events trains people to wave it through,
  which is how it becomes decorative (rules/11 §7). It now compares the parsed date
  and reports `LAST-VERIFIED touched but the stamp is unchanged` for comment-only
  edits. The fail path was **re-watched** after the refinement rather than assumed:
  a real date bump with no escape still exits 1.

  Not moved: the remaining judgment conventions have no single point of use.
  *Verify every claim* applies everywhere, which is exactly why it cannot be
  relocated and must stay a principle.

- **`evals/README` — the n=1 convention contradicted itself.** Its bolded headline
  read *"Never publish from n=1"* while the next sentence permitted it *"or state
  the sample size"*. A skim-reader saw a prohibition, a close reader a disclosure
  rule, and the scoreboard follows the body (the audit row is a declared `1×`, and
  is therefore compliant). Headline reworded to match the rule it actually states.
  Found by checking the scoreboard for a violation and discovering a wording defect
  instead.

- **Invariant 11 — `LAST-VERIFIED` moves only alongside a sweep.** The stamp
  records the last *full* re-verification pass, not the newest verified fact, so a
  rules section may legitimately carry today's verification dates while the stamp
  reads months old. Bumping it on an ordinary edit asserts a sweep that never
  happened — a false green planted in the one control whose job is detecting stale
  claims.

  The rule was already written in `AGENTS.md`, `docs/MAINTENANCE.md` and
  `check-freshness.sh`'s own header, and **two separate sessions still proposed
  bumping it wrongly**, catching themselves only on verification. A convention
  documented three times and still nearly broken twice is `sota-code-security`
  rules/10 §2.12 — a natural-language instruction standing in for an enforced
  control — so it became a gate.

  Two escapes, matching the batched and rolling passes the runbook allows: a
  **sweep-shaped diff** (≥ 20 skill files; the real 2026-07-08 sweep touched
  **100**, so the floor sits far below a genuine one), or **naming `LAST-VERIFIED`
  in the CHANGELOG**, which the runbook already requires and which is how a rolling
  pass declares completion.

  This is the repo's first **diff-based** invariant — every other check reads the
  whole tree — so with no merge base it skips with a note rather than guessing,
  the way checks 4 and 8 skip without `python3`. Watched to fail before being
  trusted (rules/11 §7): a lone stamp bump exits **1** with an actionable message,
  a 25-skill-file diff passes, and a CHANGELOG declaration passes.

- **`sota-devsecops` rules/03 §3.9.6 — the protocol prohibition now says which side
  you are on.** The clause read *"never recommend an in-house implementation of:
  crypto primitives or protocols…"*, which forbids writing a request signer against a
  published spec — something reasonable, and something the rule's own reasoning does
  not actually argue against. Found by building a case set for the §3.9.4-vs-§3.9.6
  conflict, where the ambiguity made the answer key unusable.

  Primitives remain out unconditionally. A **protocol** is out whenever *this* system
  is the **validating** side: there a canonicalisation, parsing or comparison bug
  fails **permissively and silently** — it accepts what it should reject and nothing
  errors, which is the `rules/10` family and the reason the prohibition exists.
  Composing stdlib primitives per a published spec so that a **remote authority**
  validates the result is a different class: a wrong signature is rejected on the
  first request, loudly. Taking that path now requires stating which side you are on,
  pinning the spec version, and testing against the publisher's vectors where they
  exist — and when you cannot say which side fails first, treat it as validating and
  keep the library.

## [1.19.8] - 2026-07-31

### Changed

- **README gained the seventh class**: `rules/11 §7` — your own scorer, gate or
  benchmark is a control too. Found by the front-door grep that `RELEASING.md`
  §2b added at the previous cut: the only "instrument" hits in the README were
  about *eval* instruments, so a capability shipped since v1.19.7 had no
  front-door mention. The step earned its place one release after being written.

### Changed

- **`evals/cases/build-safe/SPEC.md` rewritten to stop leaking its own answers**,
  and the rule behind it recorded where a subject cannot read it. The first spec
  stated the quality property to preserve; the rewrite states features and facts
  only. Verified: zero "must …" clauses and zero defect names remain, with all six
  product tensions intact. The note explaining this was initially placed in the spec
  as an HTML comment — still text the agent reads, naming every leaked property —
  and now lives in the ground-truth file's header. General form: **keep guidance
  about the instrument out of the artifact the subject sees.**
- **The build-safe instrument is closed, not pending.** The rewritten spec was
  tested: two bare agents scored **1.000 / 1.000**, making five bare builds across
  two spec versions all at ceiling. These seven defect classes are **not elicitable
  from a spec** at this model tier. The residue is a distinction worth keeping —
  the +0.39 completeness lift comes from *cross-cutting omissions* under a
  one-sentence prompt (rate limiting, logging, TLS, tests), while these are *local
  correctness decisions inside a feature the model is actively writing*. Defect
  avoidance and practice completeness are different measurement targets, and only
  the second has ever shown a gap here. Recorded with "do not rebuild this
  instrument" so a third spec version is not attempted.
- **`docs/INDEX.md` now reaches the day's results.** The find-it-fast index had
  **zero** pointers to the four 2026-07-30 result files, so the most consequential
  findings — why the audit half has no measured lift, a prediction written down
  before the run that killed it, and an eval that failed as an *instrument* rather
  than as a result — were reachable only by knowing they existed. Four rows added.
- **`docs/ROADMAP.md`** records two pending items rather than implying closure: the
  rewritten build-safe spec is **untested** (a bare pilot is mid-flight, and no
  build-safe number should be cited until it lands), and **calibration** is the one
  untested claim left about the audit half — measurable, but it would measure
  adherence to our own reporting doctrine and must never be reported as a lift.
- **`evals/README` gained a "Live-agent A/B runs" convention block**, so the
  contamination lessons stop living only in a result write-up: a bare arm is not
  bare by default (sub-agents inherit the agent-file rule to consult this library,
  and the API harness's *"use only your own security knowledge"* line did not
  survive the move to live agents); never encode the arm in a path or label
  (agents read `ub1` as "unguided-bare" and self-assigned); establish contamination
  per agent from citation evidence, never from the prompt or self-report; and the
  contamination detector is itself an instrument that needs a known-positive and a
  known-negative — ours produced one false positive and then a false negative on a
  known-contaminated report. Also added: bound what an instrument reads, and read
  the denominator it prints.

### Added

- **`sota-code-security` rules/11 §7 — the instrument that measures a control is
  itself a control.** Scorers, quality gates, benchmarks, coverage thresholds and
  dashboards decide whether something is *OK*, so every rule in that file applies
  to them — the most commonly skipped application, because measurement code reads
  as scaffolding. The asymmetry: a broken feature produces a complaint, a broken
  instrument produces a **number**, and numbers get quoted.
  - Four instrument-specific failure modes, each observed: unbounded or **unread**
    scope (a scorer printed "851 files" for a ten-module service — it was reading a
    vendored virtualenv and the project's own test assertions, and the denominator
    went unread); generalising from one sample (§3.3 turned inward — patterns
    written against a single reference flag every *other* correct spelling, each
    time punishing code better than the sample); errors running **both** ways, with
    only the excusing direction going unchased because it agrees with the hoped-for
    result; and the instrument that cannot fail (a mutation harness reporting
    18/18 caught while every run died before the tests started).
  - The bar: **never trust a number from an instrument you have not watched produce
    a wrong answer on purpose.** Two references wired into CI (known-bad at the
    floor, known-good at the ceiling), a negative control for anything that
    classifies, abort-don't-warn on a missing summary, and assert the mutation took.
  - §7.3 covers changing an instrument *after* seeing results — sometimes correct,
    also how a result gets massaged: disclose the change, the reason, and the
    before/after, and show no ranking moved for another reason.
  - Written because the class recurred: three new scorers needed eight corrections
    between them in one session, on top of four harness failures already recorded in
    `evals/README`. That file now points at the rule; the lesson had been repo-local
    and so invisible to anyone using the library elsewhere.

### Added

- **A procedure-compliance eval — `evals/cases/dead-path/` + `run-dead-path.py`.**
  Every existing audit instrument scores *recognition* and returns **+0.00**,
  because a frontier model handed the code and the question is already at ceiling.
  This one scores whether the model **does the procedure** rules/11 and §3.9
  require — mutate the control, delete the dependency, run the real build — which
  is behaviour, not knowledge, and is checkable without a judge.
  - The fixture is built so a careful static read gets **half the items wrong**:
    `csv_export` looks unused (named only as a config string) but is resolved at
    runtime, so deleting it breaks the suite → **KEEP**; `xml_export` is
    statically imported and called from a branch whose condition the only entry
    constructor can never produce → **DELETE**; `check_currency` looks untested
    (no test names it) but a no-op mutation breaks the suite → **REFUTED**, so
    flagging everything scores *worse*; `validate_amount` reads as enforcement but
    its boolean is discarded, so an over-limit entry posts → **CONFIRMED**.
  - Scored on two axes because they fail differently: **verdict accuracy** and
    **proof compliance** (a correct verdict with no command-plus-observed-outcome
    is not full credit — rules/11 §5). Deterministic: no API key, no network.
  - `selfcheck.sh` re-derives all six planted properties **by mutation** against
    the real suite, and `--selftest` feeds the scorer one report that only reasoned
    and one that ran, failing unless they separate (they score **0.000** and
    **1.000**). Both wired into CI, because a fixture that quietly loses its traps
    keeps printing plausible numbers while measuring nothing.
  - **Not yet run against a live agent.** The instrument exists; the number does
    not, and none is claimed.


- **`sota-code-security` rules/11 — dead-path diagnostics.** rules/10 asks, per
  control, "if this were a no-op would anything look different?". rules/11 is the
  **sweep**: the cheap signals that surface the family across a codebase without
  reading every line, plus three classes rules/10 does not cover because they are
  correctness rather than security. From two user-authored audit prompts; the
  library covered roughly two thirds of them, and the third that was missing is
  where this file starts.
  - **Diagnostics**: duration-vs-claimed-work (the highest-yield tell, and the
    only one needing no code reading); **printing every gate's denominator** —
    `0 checked, 0 failed, exit 0` is the family's signature; cross-scale delta;
    telemetry silence; and proving a fix's new path actually executed.
  - **Classes**: scale-dependent silence (unbounded traversal, size-gated paths no
    fixture crosses, and budgets that truncate **coverage** while reporting a
    normal result); stale-artifact no-ops (a cache/tag/fingerprint key narrower
    than the behaviour — "what input can change while the key stays constant?");
    and format assumptions generalised from one sample, including lenient parsers
    that return a plausible-but-wrong value instead of raising.
  - **`assert` is not a control.** Verified by running each case 2026-07-30:
    `python3 -O` and `PYTHONOPTIMIZE=1` deleted a failing `assert` (the program
    printed `passed`); `cc -DNDEBUG` did the same in C; Java disables assertions
    by default, and Oracle's guide calls disabled ones "essentially equivalent to
    empty statements". CMake's `Modules/Compiler/GNU.cmake` appends `-DNDEBUG` to
    `RELEASE`, `RELWITHDEBINFO` *and* `MINSIZEREL`, so every non-Debug C/C++ build
    strips them. Cross-refs landed in `sota-python` rules/05, `sota-c-cpp`
    rules/04, `sota-jvm` rules/04.
  - **Evidence bar**: one *discriminating* proof per class, and ACTIVE / LATENT /
    REFUTED labels (report refuted suspicions too). Plus: a fix that moves a
    detector's decision boundary needs known-bad/known-good validation before
    shipping, or a silent miss is traded for a silent flood.
- Cross-refs where a builder meets these classes: `sota-testing` rules/03 §3.7a
  (fixtures must cross the thresholds the code branches on), `sota-performance`
  rules/01 §9a (duration as a *correctness* signal, not just a cost one), the
  router's AUDIT step 4, and the README's audit section (now six classes).


- **Invariant 10 — every `skills/*/rules/*.md` must be referenced by its own
  `SKILL.md`.** The library's loading model is that `SKILL.md` loads first and the
  model reads only the rules files its index names, so an unindexed rules file is
  written, capped, checklist-ed — and never loaded. It is the skill-level twin of
  invariant 7 (a skill missing from the router) and the same class as the new
  §3.9, turned on ourselves. **Invariant 8 does not cover it:** measured
  2026-07-30, **30 of 41** `SKILL.md` files list their rules as plain backticked
  text rather than Markdown links, so a rename leaves the link checker nothing to
  resolve — verified by renaming `sota-golang/rules/01-errors.md` and watching
  invariant 8 report `ok` while invariant 10 caught it. All 255 rules files pass,
  so this is a **regression gate, not a repair**; watched to fail on two injected
  cases (an unindexed new file, and a renamed reference) before being trusted,
  per the harness convention.
- **`scripts/install.sh --version`** — nothing reported which release was in use,
  so a bug report ("the day-zero check fired wrongly") could not name the version
  that produced it. Reports the release (read from `VERSION`, never hardcoded),
  `git describe` incl. `-dirty`, whether the remote is ahead **as of the last
  fetch** (no implicit network call), and whether skills are symlinked (update
  live) or a pinned `--copy` snapshot. **`--update` now prints the version delta**
  (`1.19.7 → 1.20.0 — see CHANGELOG.md`) or `(unchanged)`: because symlinked
  skills change under you on a pull, "nothing happened" and "you just moved three
  releases" previously looked identical. Tested on six paths — normal checkout,
  non-git snapshot, missing `VERSION`, unlinked target, `--update` with and
  without a change, and behind-upstream — each verified to exit 0 without
  tripping `set -euo pipefail`.

### Changed

- **The dead-path eval was run, and it is an honest +0.00 that refutes our own
  explanation.** Six live Claude Code sub-agents, 3 per arm, identical prompts
  except the treatment: **both arms scored 1.000 verdict / 1.000 proof**, 12/12
  items each, including both inverted traps and the REFUTED case. The
  pre-registered hypothesis — *"a bare agent reasons and scores ~0.25 verdict /
  0.00 proof; a library-guided one runs the mutations"* — is **wrong**. The bare
  agents worked in scratch copies, mutated the controls, deleted the modules and
  ran `trace.Trace` unprompted; one used `dis` to identify `POP_TOP` after the
  control's `CALL` as the bytecode tell for a discarded return. Nothing asked them
  to.
  - This matters beyond one eval: the standing explanation for the other four
    audit nulls was that they score *recognition*, and a procedure-graded
    instrument would separate the arms. It did not. That explanation is retired,
    and `RESULTS.md` says so at the top of the audit section.
  - The arms differ only in **reporting discipline** — ACTIVE/LATENT labels 0/3 vs
    3/3, claims bounded by what actually ran 0/3 vs 3/3, flagging that the fix
    moves a decision boundary 0/3 vs 3/3. Post-hoc, n=3, and partly tautological
    (the library arm was told to follow a file that defines that vocabulary).
    **Not a lift, and not to be cited as one.**
  - Two disclosures in the write-up: the scorer's execution regex was **widened
    mid-run** after a false negative on a real, prose-described deletion proof (no
    arm's ranking changed; the `--selftest` guard still separates the arms 0.000 vs
    1.000), and one agent's report file is a transcription because the harness
    blocked it from writing `.md` — its verdict lines are verbatim, its method text
    abridged. Full detail: `evals/results/2026-07-30/DEAD-PATH.md`.

### Fixed

- **The rest of the automation got the same treatment as the invariant checks**
  (the two roadmap items opened yesterday). `check-freshness.sh` printed its
  denominator but never failed on zero — a drifted pathspec would have reported
  freshness over nothing; it now exits 1. `evals/test_scoring.py` printed
  `PASS: eval scoring functions behave correctly` **without saying how many
  assertions ran**, so an early return or an emptied test tuple read exactly like
  a pass; it now prints `(25 checks)` and fails below a floor — watched to fail by
  simulating a test that returns early (`only 17 ran, expected at least 25`).
  `check-invariants.sh` now reports its **wall time** alongside the denominators,
  since rules/11 §2.1's tell is unavailable unless someone records the duration;
  printed, deliberately **not gated** — a duration threshold in CI is flaky under
  runner variance, and a flaky gate gets disabled, which is how a control becomes
  inert.
- **A suspected third case was REFUTED and is recorded as such.** CI's
  `shellcheck -S warning scripts/*.sh` looked like it would pass silently if
  `scripts/` were renamed. Verified in bash (CI's shell): an unmatched glob stays
  literal, shellcheck exits **2** with `scripts/*.sh: openBinaryFile: does not
  exist`. It fails loudly. Reported rather than "fixed", per rules/11 §5.
- **Our own gates were vacuous under an empty scope — found with the diagnostic
  rules/11 §2.2 teaches, and fixed.** `scripts/check-invariants.sh` enumerated
  files via `git ls-files 'skills/*/rules/*.md'`; mutating that pathspec to match
  nothing (simulating a `rules/` directory rename) made checks 2 and 10 print
  `ok` and the script exit **0** while examining **zero files**. Check 6's tree
  recount did *not* catch it, because the `SKILL.md` count it recounts was
  unaffected — one gate's green does not cover another gate's scope. Classified
  **LATENT**: the mechanism was verified, and verified not to have fired (today's
  pathspecs match 296/255 files). Checks 1, 2, 7 and 10 now report their
  denominator (`ok (255 rules files)`) and **fail closed** on an empty scope; the
  same mutation now exits **1**. An early version of the fix printed `ok` on the
  line after a failure note — misleading green, the exact defect this file warns
  about — corrected so the count prints only on success.

### Changed

- **The README told users auto-update would keep them current. It doesn't.** The
  roadmap had flagged "git-hosted marketplaces also check at session start" as
  documented-but-unverified; checked against the Claude Code docs 2026-07-30, it is
  wrong in the way that matters: *"Third-party and local development marketplaces
  have auto-update disabled by default"* — this is a third-party marketplace, so a
  plugin user gets **no** automatic refresh unless they turn it on. Even enabled,
  the check runs after session start "with a random delay of up to ten minutes"
  while the running session keeps its launch versions. The section now carries the
  quote, the opt-in path (`/plugin` → Marketplaces → Enable auto-update), and a
  pointer to `--version`. This makes the open update-notification item **more**
  pressing, not less: neither install path pushes updates by default.
- **`docs/ROADMAP.md` corrected an item that was itself wrong.** It claimed
  `install.sh --update` "already pulls and knows both versions — have it print the
  delta". The script had **zero** references to `VERSION`
  (`grep -c VERSION scripts/install.sh` → 0), so the cheap fix it proposed did not
  exist. Now implemented, and the item split into what is done (report) and what
  remains open (push).
- **A third copy of the stale 500-line claim, this time inside the checker.**
  `scripts/check-invariants.sh`'s own header said invariant 1 covers "every tracked
  `*.md`", contradicting its own implementation (skills-only, with a comment
  explaining why). Fixed. After the README and CONTRIBUTING fixes, that is three
  places one policy change failed to reach — the reason RELEASING.md §2b now says
  to re-read long-lived prose at each cut.
- **`CONTRIBUTING.md` carried the same wrong cap the README did.** Rule 3 said
  "Every Markdown file is ≤ 500 lines" and the PR checklist said "All touched files
  are ≤ 500 lines". The cap has been **skill-files-only since PR #100**
  (2026-07-15) — README/CHANGELOG/`docs/` are deliberately uncapped. Both fixed,
  with the reason (incremental rule loading) and where navigability comes from
  instead. `AGENTS.md` was checked and needed no change: its wording already scopes
  the cap correctly ("the cap is load-bearing only there").
- **`RELEASING.md` gained the step that would have caught the invisible-audit-half
  problem** — a new §2b "Front-door surfaces", because **no invariant catches a
  capability that never got a sentence anywhere a reader looks**. Invariant 6 fails
  on a wrong *number* in the README; nothing fails on a missing *feature*, which is
  how five audit capabilities went undocumented across v1.17.0–v1.19.7. The pre-tag
  checklist now carries a matching item. Also documented there: avoid dots in release
  branch names — the assistant's `Bash(git checkout *.*)` deny rule matches a branch
  name containing dots, so `release/v1.19.7` is refused while
  `chore/release-v1-19-7` works. It bit again at this cut.
- **`docs/MAINTENANCE.md` now names its high-rot targets** instead of treating every
  claim as equally durable. First on the list is §3.9.2's eight-project tool table,
  which demonstrated its own failure mode the day it landed: two of the eight had
  been renamed under the URLs a manifest still carries. The runbook now says to
  re-verify with `gh api` **and read `full_name` back**, and flags that the Ruby row
  asserts a *negative* ("no established tool") that needs re-checking rather than
  assuming.
- **`docs/ROADMAP.md` re-stamped to 2026-07-30 / post-v1.19.7**, recording a third
  discovery mode (a user-authored prompt aimed at the library's own coverage, with
  CVEs ruled out), four new open items, and live re-checked adoption signals: **8
  stars, 0 watchers, 2 forks, exactly one true issue ever** (#4, closed — filtering
  `has("pull_request")` out of the issues endpoint, which otherwise counts every PR
  as an issue), and **0 external gap reports in 8 days**. `ROUTER_BUILD_SHA` was
  **re-computed and matched** (`71a9d78ea5e9e341`), confirming v1.19.7's router edits
  landed outside the eval-pinned BUILD block, so historical completeness runs stay
  comparable. Router headroom re-counted at 497/500.
- **`docs/INDEX.md`** points at the README's new audit section, so the capability is
  reachable from the find-it-fast index rather than only from the README itself.

## [1.19.7] - 2026-07-30

### Added

- **`sota-devsecops` rules/03 §3.9 — the declared-but-not-reached sweep.** The
  dependency file covered whether what you ship is *vulnerable* (CVEs, SBOM,
  confusion, typosquats) and never whether a declared dependency is **reached at
  all**. Found by running an audit prompt against the library that explicitly
  excluded CVEs and versions: five of its six requirements had no home. The new
  section covers reachability tracing from a real entrypoint (with the
  impossible-path trap — a symbol referenced only on a branch the live code
  cannot produce — and its inverse, dynamic loading, where static tools
  false-*positive*); per-ecosystem tooling with each tool's blind spot named;
  **deletion as proof** (scratch copy, real build + lint + full suite, exact
  commands, exit codes, before/after transitive counts) with the two traps that
  make a green run lie; the leverage ratio (<5 symbols used / >10 modules
  inherited); upstream health fetched **this session** via `gh api`; and an
  A–D classification (DELETE / REPLACE IN-HOUSE / KEEP / UNMAINTAINED-but-keep).

  Every tool named was verified live on 2026-07-30 via `gh api repos/<o>/<r>` —
  the same command the rule prescribes. Two checks were promoted from what that
  verification itself turned up: `gh api` **follows renames silently**
  (`fpgmaas/deptry` answers as `osprey-oss/deptry`, `icanhazstring/composer-unused`
  as `composer-unused/composer-unused`), so `full_name` must be read back; and
  the honest per-ecosystem answer for Ruby is that **no established tool exists**
  — its candidates are single-maintainer and low-adoption, which is precisely
  the case the deletion proof exists for.

  The KEEP bucket's do-not-reimplement list adds a class the library did not
  have: **an algorithm whose output is persisted and must stay comparable with
  stored data** (fuzzy/LSH hashes, similarity digests, tokenizers, ID derivations).
  A merely *equivalent* reimplementation invalidates every stored value it has to
  compare against, and the failure is silent — comparisons keep returning
  answers, just wrong ones.

- Cross-refs so the sweep is reachable from where the question gets asked:
  `sota/rules/01` §2 inventory, `sota-code-security` rules/10 §2.13 (the sibling
  class one layer up), the router's routing table and library map, and the four
  language skills that had partial or zero coverage — `sota-golang` rules/05
  (`go mod why -m` and its test-inclusive graph), `sota-javascript-typescript`
  rules/07 (knip output is a candidate list, not a finding), `sota-python`
  rules/01 (`deptry` DEP002/003/005), `sota-rust` rules/05 (`cargo machete`
  false positives vs `cargo udeps` nightly + false negatives).

### Changed

- **README: the audit half of the library was invisible.** The README sold BUILD
  completeness and listed standards; nothing described what the audit actually
  *does*, so five capabilities shipped across v1.17.0–v1.19.7 were documented
  nowhere a reader would look. New section **"What the audit hunts that a scanner
  can't"** covers inert controls, declared-but-unreached dependencies, decisions
  that stopped being right, adversarial refutation, and absence-claim discipline —
  each linked to the rules file that owns it. It carries its own honest caveat:
  the measured lift is in BUILD, every audit eval sits at **+0.00**, and one
  earlier audit lift was retracted when its sample grew 15 → 49 cases. Also:
  "How it works" step 3 described a 5-step audit chain that omitted the
  silent-control pass, the decision ledger, and the refutation pass — now the
  real seven; two Conventions bullets added (negative claims need a second
  independent method; positive observations must show *effect*, not existence).
- **README fixed a stale invariant claim.** Contributing said "keep every file
  ≤ 500 lines". The cap has been **skill-files-only since PR #100** (2026-07-15) —
  README/CHANGELOG/`docs/` are deliberately uncapped, which is why this file and
  `docs/` can hold full narrative entries. It now says so, names the reason
  (incremental rule loading), states that nine invariants enforce the conventions,
  and links `docs/ADOPTION-LOG.md`, which the README had never mentioned.
- **Docs refreshed to the post-v1.19.6 state**, and stale claims corrected:
  - `docs/MAINTENANCE.md` said CI enforces **7** invariants — it is **9** since
    v1.19.5. The only stale count left in the tree (`grep -rn "[0-9] invariants"`
    over docs/README/AGENTS/CONTRIBUTING/evals now returns nothing wrong).
  - `docs/ROADMAP.md` "Open tasks" was stamped **2026-07-22** and predated six
    releases. Re-stamped 2026-07-28 with what v1.19.1–v1.19.6 actually shipped,
    the day-zero field-validation result, and six new open items (see below).
    Adoption signals re-checked live via `gh` rather than restated: **8 stars, 0
    watchers, 2 forks, 1 issue ever** — and **0 gap reports in 6 days**.
  - The roadmap's OpenRouter credit figure is now marked *as of 2026-07-22, not
    re-checked* instead of reading as current — no paid eval ran this cycle.
  - `RELEASING.md` now says to consolidate duplicate `[Unreleased]` sections
    before a cut, and that invariant 9 fails the build on them.
  - `AGENTS.md` (and so `CLAUDE.md`/`GEMINI.md`, its symlinks) gained pointers to
    `docs/VERIFY-SETUP.md` and `docs/ADOPTION-LOG.md`, neither of which was
    listed despite both being current working surfaces.

  New open items recorded in the roadmap: no update-notification path for clone
  installs; nothing reports which version is in use; `scripts/verify-setup.sh`
  for the deterministic half of VERIFY-SETUP; the `gh-sota` extension considered
  and **deferred with its reason** (gh requires a `gh-*` repo name, and its
  update notice fires only on invocation); router headroom at **497/500**; and
  one unverified README claim about marketplace session-start re-checks.

## [1.19.6] - 2026-07-28

The **field-found** release: both changes came from watching the library be used
rather than from reading it. A live BUILD session hit two of the library's own
rules contradicting each other, resolved it correctly by reasoning, and thereby
exposed that nothing told it how. No skill added (41 unchanged).

### Added

- **Router — how to resolve two loaded rules that contradict each other.** The
  library has 41 skills that can disagree and, until now, said nothing about
  what to do when they do: a `grep` for `conflict|precedence|disagree|override`
  across `skills/sota/SKILL.md` returned only an unrelated table row. Six lines
  in "When this library is wrong": a contradiction is usually a **scope
  collision** (a general default vs a requirement inside a narrower domain), the
  narrower wins *in its domain*, pick by which failure mode is worse here, and
  **never resolve it silently** — name the rule you followed and why in a comment
  beside the code, or the next reader reverts it. Then report it, because a
  contradiction needing judgment is itself a defect. Placed next to the report
  path, outside the eval-pinned BUILD block (`ROUTER_BUILD_SHA` unchanged).

### Fixed

- **`sota-python` rules/07 §1 contradicted `sota-observability` rules/05 §1.**
  rules/07:56 called an `async def` endpoint with zero `await` "a bug marker";
  rules/05 specifies a liveness probe as process-internal-only, "usually just
  return 200" — which *is* a no-`await` `async def`. A reader following rules/07
  literally makes the handler `def`, it runs in the anyio threadpool, and
  saturation by slow sync handlers delays the probe until the orchestrator
  restarts a process whose event loop was fine: the restart storm rules/05
  exists to prevent. rules/07 now carves the liveness case out explicitly, cross-
  references rules/05 §1, tells the author to say so in the docstring (or the
  next reader "fixes" it), and notes that readiness follows the normal rule. One
  audit-checklist grep added.

  Found by running the library, not reading it: a live BUILD session hit the
  collision, resolved it correctly by judgment, and documented why — but only
  because the model was thinking. The rule as written would have produced the
  wrong code for a literal reader. Third gap this week surfaced by field use.

  **Scoped deliberately to Python**, verified rather than assumed: no other
  language skill carries an analogous "async without await" rule (checked all
  eight), and the trap is FastAPI-specific — a `def` handler is dispatched to
  the anyio threadpool. `sota-javascript-typescript` rules/04 shows a *sync*
  `/healthz` handler, which is correct for Node, where nothing dispatches
  request handlers to a threadpool. No equivalent carve-out is needed elsewhere.

## [1.19.5] - 2026-07-28

The **verify-what-you-set-up** release. The library could scaffold a repo and
could state what a repo needs; nothing checked the result, and nothing in CI
noticed when two PRs each opened a `[Unreleased]` section. Every item here comes
from something being run rather than reasoned about. No skill added (41
unchanged).

### Added

- **`docs/VERIFY-SETUP.md` — the read-only setup check.** `init-gates.sh` sets a
  repo up; nothing checked the result, and "configured" and "working" render
  identically. A paste-in prompt that reports whether the library reaches the
  directory, whether the repo's agent file is *true*, and whether its gates are
  real — changing nothing, and marking anything unobservable as UNVERIFIED
  rather than passing it. Linked from README → Enforcing the gates and
  docs/INDEX.md. Derived from two live runs against a 4300-commit repository:
  the first run's own limitations produced four of its checks (claims-vs-commands,
  the three-state hook distinction, execute-vs-reject, and can-you-land-the-fix),
  each a gap the run exposed rather than something reasoned in advance.
- **`sota-code-security` rules/10 §2.13 — a control that never executes.** One
  step earlier than "runs but does nothing": a gate whose trigger never fires —
  an `issue_comment` job nobody comments on, a path filter matching nothing, a
  branch filter naming a renamed branch. Its whole run history is *skipped*, and
  **all-skipped is not all-green, but every dashboard renders it the same way**.
  Verify on two axes (ever executed / ever rejected) and state the sample.
  Found in the wild: a review workflow with 5/5 skipped runs. One checklist item.
- **`sota-docs-workflow` rules/01 §7 — check an agent file's *claims*, not just
  that its commands exist.** The two rot at different rates and only the first
  gets noticed. Observed on that same repo: all seven `make` targets resolved,
  while the stated toolchain was seven months stale and the stated contents of
  `make check` were wrong. Verify in two passes, and prefer linking the file that
  owns a fact over asserting it. One checklist item.

- **Invariant 9 — at most one `## [Unreleased]`, and it must be the top entry**
  (`scripts/check-invariants.sh`), with archives allowed none. Invariant 5 reads
  only the *first* `## [` heading, so a second `[Unreleased]` further down was
  invisible to CI; on 2026-07-28 PRs #142 and #143 each opened one above
  `[1.19.3]` and `main` carried both until the v1.19.4 cut caught it by hand.
  Fence-aware (a heading quoted inside a code block doesn't count), portable to
  bash 3.2, no `python3` needed. Documented in AGENTS.md and CONTRIBUTING.md,
  where the contributor-facing rule is: if `[Unreleased]` exists, add to it.

  Watched to fail before being trusted, on all four cases — duplicate headings,
  a single one buried below a release, one in an archive, and one quoted inside
  a fence (must pass). The second case exposed a defect **in the check itself**:
  `grep -m 1` on a pipe closes it early, the upstream `printf` dies of SIGPIPE,
  and `pipefail` + `set -e` then killed the script mid-check — it printed its
  heading and nothing else. Fixed by reading the first heading without an
  early-exit consumer. (Invariant 5's `grep -m 1` is safe because it reads a
  file, not a pipe.) A guard that dies silently is the failure this repo keeps
  writing rules about; only running it against a real break surfaced it.

## [1.19.4] - 2026-07-28

The **field-testing** release. v1.19.3 wrote down what a new repo needs; this one
makes the library *raise* it unprompted, then corrects it against two real repos
— a 4304-commit kernel project and a live agent session scaffolding it. Four of
the six changes below exist because something written from reasoning met a real
repo and turned out to be wrong or incomplete. No skill added (41 unchanged).

### Added

- **Router `skills/sota/SKILL.md` — a "Day zero" section.** On the first BUILD
  task in an unfamiliar repo, check by *looking* (gate config, LICENSE, agent
  file, git history length) and, if two or more are missing and the history is
  short, surface `init-gates.sh` / `gen-agents-md.sh` **once, in a line**. Two
  guards are part of the rule: a long history means a mature repo that decided
  against them (say nothing), and **offer, never perform** — the scripts write
  config into the user's repo, and a decline is decided. Placed outside the
  `## BUILD mode — workflow` block on purpose: it is a per-repo precondition,
  not a per-task step, and keeping it out leaves the eval-pinned BUILD section
  byte-identical (`ROUTER_BUILD_SHA` still `71a9d78ea5e9e341`, verified).
- **`sota-docs-workflow` rules/01 §10 — "an ambient install doesn't travel".**
  User-scoped rule libraries, skills and linters resolve against one home
  directory; a teammate's clone and CI see nothing. Solo vs shared is an
  explicit choice, but the **gates** must be repo-resident either way — a
  secret scan that exists only in your shell is not a control on anyone else's
  commit. Plus: a pointer file referencing tooling the reader lacks is worse
  than no pointer, because it reads as a satisfied requirement. One
  audit-checklist item added.
- **`sota-docs-workflow` rules/01 §6 — the host-capability report.** Where a
  repo's documented dev loop doesn't run on every supported host, ship a small
  executable report that probes the machine and prints, per target, whether it
  works here and **what each gap blocks**. Its three load-bearing properties:
  probe capabilities rather than one implementation's name (a `docker` check
  reports "no runtime" on a machine running podman), name the consequence of
  each gap so nobody discovers it through a ten-minute failed build, and report
  rather than gate. Verified absent — every `preflight` in the library was CORS
  and `doctor` appeared nowhere. Taken from a *worked example* rather than a
  repo of ideas: a live agent session scaffolding that same clone.
- **`sota-docs-workflow` rules/01 §7 — automation on an agent's edits must
  check, not rewrite.** A format-on-write hook is right for a human editor and
  wrong for an agent: rewriting the file *after* the agent wrote it stales the
  agent's view, so its next edit fails or clobbers the reformat. Such hooks
  report (non-zero, with file and fix) and let the agent apply it; rewriting
  belongs at commit time or in CI, where nothing holds a live view. Zero prior
  hits across the tree. Two audit-checklist items added.

### Fixed

Both found by running the new detection against a real repo
([asterinas](https://github.com/asterinas/asterinas), 4304 commits) rather than
trusting it as written:

- **Licence detection matched the bare name `LICENSE`.** Asterinas ships
  `LICENSE-MPL` + `COPYRIGHT`, so a literal check reports the licence missing
  and feeds a false signal into the day-zero trigger. The router now matches
  `LICENSE*` / `COPYING*` / `COPYRIGHT`, and says explicitly not to match the
  bare name. Gate detection likewise widened beyond `.pre-commit-config.yaml`
  to any hook manager or CI job.
- **rules/01 §10 offered only two ways to point a second tool at `AGENTS.md`**
  (symlink, CI-generated copy). Asterinas uses a third that is better than
  both — a 28-byte `CLAUDE.md` reading `See [AGENTS.md](AGENTS.md).`:
  platform-independent, no build step, and unable to degrade silently the way a
  `core.symlinks=false` checkout does. It is now option 1 and the recommended
  default, with the trade (one hop the agent must follow) stated.

### Changed

- **README Installation** gains "An install is personal, not repo-resident" —
  that one install covers every project including brand-new ones, that it
  resolves only on your machine, the `--project .` / `--copy` options for a
  shared repo, and a pointer to the day-zero list.

Everything above is **not measured** — no lift claimed. The same session
independently rediscovered five rules we already had (silent control failure in
an upstream script that exits 0 while checking nothing, agent-doc decay, proving
a gate by making it fail, and two shell-safety rules); those are recorded in
[docs/ADOPTION-LOG.md](docs/ADOPTION-LOG.md) as convergences, including one
noted as a *routing* miss rather than a coverage gap.

## [1.19.3] - 2026-07-28

Third intake pass, against
[claude-project-scaffold](https://github.com/martinholovsky/claude-project-scaffold)
— an agent-context scaffolder, not a repo scaffolder. Most of its content turned
out to be ours already (the minimal-agent-file principle, the context-rot
rationale, the ADR format), recorded as convergences. Three ideas were genuinely
absent and landed; the gap the source *didn't* cover — that a fresh repo
inherits nothing from an ambient/global agent setup — became the fourth and
largest addition. No skill added (41 unchanged).

### Added

- **`sota-docs-workflow` rules/01 §9 — the troubleshooting playbook.** The
  dev-facing counterpart to §5's on-call runbooks: a symptom-keyed index of
  failures already solved once, in Symptom → Diagnosis → Fix form, written in
  the PR that fixed the bug. Includes the two rules the source didn't have —
  delete entries a root-cause fix invalidated, and treat a thrice-reported
  symptom as a signal to fix the code instead of documenting it again. Verified
  absent: "symptom" appeared across the library only in the alerting/on-call
  sense.
- **`sota-docs-workflow` rules/01 §10 — day zero in a new repo.** An installed
  skills library, a personal `CLAUDE.md`, and a house style guide are *ambient*;
  a fresh repo, a teammate's clone, and a CI runner inherit none of them.
  Covers the only two artifacts that must precede the first commit (`.gitignore`
  + secret scanning, LICENSE) and why; the ambient-vs-repo split for agent files
  in both directions; and the `core.symlinks=false` failure mode that turns a
  symlinked `CLAUDE.md` into a one-line text file (verified against
  `git help config`), with CI generation as the fallback.
- **`sota-docs-workflow` rules/01 §7 — the minimal agent-file shape.** §7 said
  what content earns its place but gave no skeleton; it now carries a four-block
  one, with the rule that the row which earns its place is the one contradicting
  the default.
- **`sota-architecture` rules/01 §4 — ADR directory discipline.** Sequential
  kebab-case filenames plus an `index.md` status table, and committing the ADR
  in the PR that implements the decision. The format and the
  consequences-with-a-downside rule were already there; the directory-level
  practice that makes a stalled process visible was not.

### Changed

- `sota-docs-workflow/SKILL.md` BUILD mode now routes new-repo bootstrap and the
  troubleshooting playbook (steps 7–8), and rules/01 gains three audit-checklist
  items.

## [1.19.2] - 2026-07-24

The **second intake** release: three ideas mined from
[swarm-forge](https://github.com/unclebob/swarm-forge) — an agent-orchestration
harness whose engineering content is deliberately thin — each verified absent
from our tree before landing. The headline is a genuine hole it exposed: we had
hexagonal ports/adapters and we had coverage exclusions, but nothing joining
them into the **testability boundary** that makes any test metric interpretable.
Six of its rules turned out to be ones we already had, recorded as convergences
rather than manufactured diffs. No skill added (41 unchanged).

### Added

- **`sota-architecture` rules/02 §14 — the testability boundary (humble
  object).** Every system has a shell automated tests cannot drive (GUI,
  devices, real clocks/networks, process spawn); draw that boundary explicitly
  in the build, keep it thin, allow it no business branching, and measure
  coverage/mutation/complexity against the core only. Includes the corollary
  that a *growing* shell is an architecture finding, not a testing one. Two
  checklist items added. The library had hexagonal ports/adapters (§4) and the
  generated/vendored coverage exclusion, but nothing connecting them — a
  `grep` for `humble object|near IO|adapter shell|untestable` across
  `sota-architecture` and `sota-testing` returned zero hits.
- **`sota-testing` rules/06 §6.3 — mutation survivor baselines.** Persist the
  survivor set and gate CI on *new* survivors (the mutation analogue of the
  coverage ratchet) instead of an absolute score, under two conditions: the
  mutation engine version is pinned beside the baseline (engines change
  operator sets between releases, so an unpinned diff attributes tool churn to
  your code), and only the tool writes the file (a hand-edited baseline is a
  live survivor marked dead). Checklist item added.
- **`sota-testing` rules/07 §7.2 — rank coverage gaps by complexity.** Cross
  coverage with branch density to aim the next test and the next mutation run;
  a branch-dense thinly-covered module outranks a 3-line getter at 0%. Stated
  as a pointer, never a gate, so it does not become the Goodhart target that
  §7.2 already warns coverage thresholds are. Two checklist items added, one
  of them tying the measured scope back to the rules/02 §14 boundary.

### Changed

- **`docs/ADOPTION-LOG.md`** — second entry: three ideas adopted from
  [swarm-forge](https://github.com/unclebob/swarm-forge) (read at source level
  on `main`, `six-pack`, and `adversaries`), one recorded as `rejected:
  contrary` (its resolve-at-latest tool policy, which also breaks its own
  mutation baseline — none of the seven tool repos carries a tag, verified via
  the GitHub API), and **six convergences** recorded as `rejected: already
  ours` with the file:line that covers each. All three adoptions are reasoned,
  **not measured** — the entry says so explicitly and forbids citing a lift.
- **`RELEASING.md` — ADOPTION-LOG version stamping.** Adoptions land in ordinary
  PRs between releases, so a log entry's "Landed in" cell is written before the
  shipping version is known. `unreleased` is now the documented placeholder, and
  the release cut stamps it: a row in the §1 version-bearing files table plus a
  pre-tag checklist grep. Deliberately a runbook step, not a ninth invariant —
  the marker is *correct* until the cut, so CI failing on it would be backwards.

## [1.19.1] - 2026-07-24

The **adopt-what-we-verified** release: five ideas mined from an external repo
([training-knowledge-vault](https://github.com/Eolas-bith/training-knowledge-vault)),
each validated against our own tree before landing, three adopted and two
recorded as already-covered. No skill added (41 unchanged). New
[`docs/ADOPTION-LOG.md`](docs/ADOPTION-LOG.md) is the audit trail.

### Added

- **Invariant 8 — internal Markdown link resolution.**
  `scripts/check-invariants.sh` now fails the build on any relative Markdown link
  to a `*.md` target that doesn't resolve, so a moved/renamed file can't leave a
  dead link in the README, `docs/`, CHANGELOG, or a skill. Scoped to `*.md`
  targets (broadening false-positives on `[text](x)`-shaped prose/code). The
  dry-run that justified it immediately caught **5 real broken links** in
  `evals/results/**` (`../../docs/…` for a path that needs `../../../docs/…`) —
  fixed in this release. Idea from the source repo's `vault-doctor.py`.
- **`sota-llm-engineering` rules/02 — self-contained prompts.** A new rule in §1:
  a prompt that references a schema/format in a file the model may not have
  loaded degrades *silently to fabrication*; inline every schema/enum/rule the
  prompt depends on. Scoped so it does not contradict a coding agent's on-demand
  rule loading. Checklist item added.
- **`sota-code-security` rules/10 §2.12 — instruction standing in for a control.**
  A "do not surface / do not reveal / ignore instructions below" instruction over
  data or permissions in the same context is a silent control: attention leakage
  shapes output without quotation, and prompt injection overrides it — enforce
  structurally/in code (cross-refs rules/08 §1–2, rules/07 §2). Checklist item added.
- **`docs/ADOPTION-LOG.md`** — an external-idea intake ledger (adopted/rejected/
  deferred/superseded, observation-before-diagnosis, landed-in pointers),
  itself the fifth idea borrowed from the source repo's lessons-log discipline.
  Linked from `docs/INDEX.md`.

### Fixed

- Five broken relative links in `evals/results/2026-07-10/` and
  `evals/results/2026-07-13/` (`../../docs/…` → `../../../docs/…`), surfaced by
  the new invariant 8.

### Changed

- Invariant docs updated for the new check (`AGENTS.md`, `CONTRIBUTING.md`,
  `docs/WHY-IT-WORKS.md`: "seven" → "eight"). Corrected two stale statements of
  the 500-line cap that still said "any tracked `*.md`" — it has been
  skill-files-only since 2026-07-15.
- **Roadmap refreshed to the live state and a broken sentence repaired.** The
  "Open tasks" stamp was stale (*as of 2026-07-16* — three releases and a week
  behind); replaced with a **2026-07-22** current-state block that summarizes the
  v1.17→v1.19 stretch and lists what is *genuinely* open (distribution/adoption first,
  then the agentic audit, then the cheap incremental runs), separated cleanly from the
  dated per-cycle history below. An orphaned fragment in the history (a sentence that
  began mid-clause, *"extension mismatch, env-filter mismatch…"*, left by an earlier
  edit) was completed and the cross-model follow-up marked done. `docs/INDEX.md` gained
  a row pointing at the cross-model result, which was otherwise unfindable from the
  index. Docs-only; no measured number changed.

## [1.19.0] - 2026-07-22

The **de-risk-the-foundation** release. The flagship BUILD lift is now shown to hold
across model families, the eval harness that produces every published number finally
has tests, the last two open eval signals resolved as noise, and the README leads with
what's proven instead of what's voluminous. No skill added (41 unchanged): evals,
harness, and positioning.

**Headline:** the completeness lift (**+0.39**, `0.59 → 0.98`) is **not sonnet-specific**
— a different-family frontier model (`openai/gpt-5.1`) shows **+0.44** on the same tasks,
the single largest untested assumption in the evidence base, now discharged for the
flagship dimension.

### Changed

- **Negative controls grown 8 → 20; the over-flagging signal is resolved as noise.**
  The last unexplained result in the silent-failure set was the *ablated* arm scoring
  1.00 on the loud controls while both other arms scored 0.75 — a hint that rules/10's
  catalogue might nudge a model into flagging correct, loudly-failing controls. Twelve
  more negatives were authored, each deliberately *resembling* a positive class so an
  arm matching on shape rather than effect would trip (an `exists()` check that also
  asserts non-emptiness, an optional import raised at startup, a `chmod` that actually
  restricts, correct first-match-wins ordering, a timeout attached via
  `NewRequestWithContext`, a retry loop that re-raises, decorators in the right order).
  Set is now **81 cases: 35 enumerated positives, 26 novel, 20 negative controls.**
  **Result: all three arms score 1.00 on the loud controls** — the hint was 2 of 8
  cases and it disappears at n=20. Overall lift **+0.02** with per-arm ranges of
  ±0.05–0.07, i.e. still effectively +0.00 and consistent with n=49 and n=69.
  Noteworthy: **every subgroup signal this set has produced has evaporated when the
  subgroup grew** (anchoring 6→26, over-flagging 8→20) — the strongest evidence in
  this repo for the "grow the set before trusting a subgroup" rule.

### Added

- **The eval scoring functions now have tests — and they run in CI.** A mutation probe
  replaced `run-clean.score()` with `return 1.0, {}` and asked what would notice:
  `check-invariants.sh` passed, `pre-commit` passed, and scoring a deliberately wrong
  prediction set returned **1.00**. Nothing noticed, because **there was no test suite
  in the repo and CI never touched `evals/`** — the code producing every number this
  project publishes (the README's +0.39, every +0.00 reported as an honest null) was
  unverified. A scorer stuck at 1.00 would have made all of it a lie, silently: the
  rules/10 class at its worst, in the one place it would do the most damage.
  `evals/test_scoring.py` (plain `python3`, no new dependency) covers all three
  scorers with **mutation-resistant** rows — each checked at 1.0, 0.0 *and* a partial
  value, so constant-return mutations die on the 0.0 rows and swapped-metric mutations
  die on the partials; `run-repo-audit` gets a row where category- and strict-recall
  legitimately differ. **Both mutations were watched to fail before the tests were
  trusted.** Wired into CI (`Eval scoring tests`) and pre-commit (on `evals/*.py`), so
  it cannot become a test that exists but never runs.

### Changed

- **Docs hygiene + harness/measurement conventions extended.** `evals/README.md`'s
  "Harness conventions" now carries the two findings from the deliberate self-audit
  (an unchecked corpus glob; an `--ablate` that matched nothing) and a new
  **Measurement conventions** section: *one run is a data point, not a number — never
  publish from n=1* (twice in a week a single run produced a figure a larger sample
  walked back), *grow the set before trusting a subgroup signal* (the n=6 anchoring
  "finding" evaporated at n=26), and *scrub artifacts but don't trust the scrub —
  gitleaks and push protection are the backstop, not the pattern list*.
  `docs/WHY-IT-WORKS.md` had a stale `+0.40` **and** an orphaned sentence fragment
  introduced by an earlier edit in this cycle — both repaired.
- **Completeness follow-up resolved, and the published figure corrected to `+0.39`
  (0.59 → 0.98).** v1.18.0 shipped `+0.40` from a **single** synced run; arm B was
  repeated and the two-run mean is **+0.39** — back on the original number. The 0.02
  with-arm dip that looked like it might be a salience cost of the falsification
  clause was **noise**: c1_ticket_api recovered 0.86 → 0.94, and its own swing across
  three runs (0.86–0.97) is larger than the 0.016 gap it was supposed to explain. No
  measurable cost; hypothesis closed. README, WHY-IT-WORKS and RESULTS.md updated.
  **Standing lesson recorded: stop publishing from n=1** — this is the second time in
  a week a single run produced a figure a larger sample walked back (the other being
  the retracted +0.07 on silent-control detection).

### Fixed

- **The artifact secret-scrubber was itself incomplete — a JWT pattern was missing,
  and gitleaks caught what it did not.** Added in v1.18.0 covering Stripe/AWS/GitHub/
  Slack/Google/PEM shapes, it missed a fake JWT the model wrote into generated code
  on the very next run. That is the enumeration problem the library warns about,
  occurring in our own tooling: the pattern list is incomplete *by construction*
  because a model inventing example code invents new shapes. JWT pattern added,
  artifact re-scrubbed (1 → 0, scores unchanged), and the code now says plainly that
  **gitleaks is the backstop, not the list** — add a pattern whenever it fires, and
  never bypass push protection. Third time this week a second, independent scanner
  caught what the first missed.

- **Silent-control audit of `evals/` — the library's own rules/10 applied to the
  harness that measures it.** Four silent failures surfaced here on 2026-07-20, every
  one found *incidentally*; this was a deliberate pass. **Two confirmed findings in
  ten files, both demonstrated live before being fixed**, and both sharing the
  property that makes them worse than an ordinary bug: **their failure mode produces
  `+0.00`** — a result this project has legitimately published four times, so a fake
  null would be indistinguishable from a real one.
  **F1 — an empty library corpus yields a "with-library" arm containing no library.**
  `run-clean.audit_library_context()`, `run-repo-audit.library_context()` and
  `run-desc-routing.catalogue()` all globbed their corpus and never checked the count;
  a wrong cwd or renamed directory hands the with-arm `""` and still prints a recall.
  Reproduced live (`with-library corpus: 0 chars`, no error). All three now abort.
  **F2 — `--ablate` silently ablates nothing when its target is renamed.** The filter
  was a filename equality test whose result was never asserted, so a rename leaves the
  "ablated" arm as the *full* corpus and reports a fake +0.00 contribution — while the
  run header still prints `ABLATED(...)`. Reproduced live (`removed=0 chars`). Now
  aborts. This was the **third** instance of one pattern (after
  `run-adjudication.py`'s section-number marker and `run-completeness.py`'s drifted
  mirror), so every ablation and mirror in the harness is now guarded: *a
  transformation whose result is never asserted*. Every guard watched to fire.
  Categories checked with nothing found are stated explicitly (optional-dependency
  degradation, swallowed enforcement exceptions, truncation, hardcoded reporting,
  shipped-artifact gaps) rather than padded. Report:
  [`evals/results/2026-07-21/EVALS-SELF-AUDIT.md`](evals/results/2026-07-21/EVALS-SELF-AUDIT.md).

### Changed

- **Doc hygiene: stale silent-failure counts corrected and the audit-null story
  consolidated.** `evals/README.md` still said "41 positives + 8 negative controls"
  (doubly stale — the set is 61 positives + 20 negatives at 81 cases); fixed, and the
  +0.00 result annotated as reproduced at n=49/69/81. The `RESULTS.md` scoreboard row
  moved 49 → 81 cases, and a new paragraph states the audit-family result plainly in
  one place for the first time: **all four audit-ability rows are +0.00** (recall,
  cross-file, silent-control, precision), every apparent subgroup exception dissolved
  when its subgroup grew, and the library's audit half is justified by gap analysis
  plus one real self-audit — **not by a measured lift**. The measured lift lives
  entirely in BUILD (completeness +0.39, freshness +0.53).

### Added

- **Cross-model replication of the flagship BUILD lift — it is not sonnet-specific.**
  Every completeness number this project had published used one build model
  (`claude-sonnet-4.6`), the single largest unhedged assumption in the evidence base.
  Re-running the completeness eval with a **different-family frontier model**,
  `openai/gpt-5.1`, driving BUILD — same blind judge (`opus-4.8`), same rubrics, same 7
  tasks — gives **0.44 → 0.88, lift +0.44** (every case positive, +0.29 to +0.55),
  against sonnet's **0.59 → 0.98, +0.39**. The lift generalizes and is *larger where the
  baseline is lower* (gpt-5.1's unguided arm is 0.44 vs sonnet's 0.59) — the same "lift
  tracks incompleteness" mechanism the breadth study found across domains, now
  reproduced across models. The with-arm ceiling is lower (0.88 vs 0.98): the library
  takes gpt-5.1 to *very good*, not *near-perfect*. The blind judge shares a family with
  sonnet but not gpt-5.1, so +0.44 is a conservative floor. Two families is not
  "model-agnostic", but the single-model assumption is discharged for the flagship
  dimension. Cost $1.87. Writeup:
  [`evals/results/2026-07-22/CROSS-MODEL.md`](evals/results/2026-07-22/CROSS-MODEL.md);
  `RESULTS.md` + `docs/WHY-IT-WORKS.md` updated.

### Changed

- **README hero re-led with the measured lift and the *loop*, not the volume.** The
  opening had led with "41 skills (296 files, ~60k lines)" — which reads as exactly
  the prompt-dump this library outperforms. It now opens with the proven result
  (best-practice coverage **~59% → ~98%, +0.39**, from a bare "build X" prompt, linked
  to the scoreboard) and the one-line mechanism that differentiates it — *a loop, not a
  prompt dump: route lean, re-state every turn, re-check last*. The volume figure moves
  to a supporting "under the hood" line (kept intact for invariant 6). A distribution
  move, not a content one: ~500 unique cloners/14 days were converting to 7 stars, and
  the hero was selling the wrong thing.

## [1.18.0] - 2026-07-21

The **learning-from-use** release. Ships the library's first path for hearing from its
users, retires an open hypothesis about its own content pattern, and re-verifies the
headline number against the workflow that actually ships. No skill added (41
unchanged): router content, evals, and docs.

**If you upgrade for one reason, it is this:** the completeness figure quoted in
v1.17.0 (`+0.39`, `0.60 → 1.00`) was measured against a *drifted copy* of the BUILD
workflow. Both arms have now been run — the number reproduces at **+0.40** either way
— and every user-facing surface now carries the verified `0.58 → 0.98 (+0.40)`.

### Added

- **Gap-reporting loop — the library's first path for learning from use.** The
  project has no telemetry by design, which also means a wrong rule, a stale
  version claim, or a missing skill stays in the library for everyone until a human
  reports it. Measured reality at v1.17.0: **~24 organic clones/day against 7 stars
  and one issue ever filed** (GitHub traffic API; the three days with zero CI runs
  show clones exactly equal to unique cloners). Hundreds of installs, no signal.
  The fix uses the one channel this project uniquely has — the user is talking to an
  agent that **already read the skills**. A new short router section tells that agent
  to surface a **one-line** note when the library actually let the user down (a rule
  contradicted by a primary source it just checked; a rule that doesn't fit and
  states no exception; real surface area with no owning skill; guidance that would
  have shipped a defect), with the issue-template link — and explicitly *not* for
  personal preference, unneeded rules, or mid-task. Deliberately placed **outside**
  the always-apply operating principles so it does not dilute the measured
  principle-5/6 salience. README gains a matching section (issue templates already
  existed; nothing pointed users at them). Regression-checked — the router grew
  443 → 467 lines and the routing eval pastes it whole: with-arm **held at 1.00**
  (3×@0.7, no misses), lift +0.11. Artifact:
  `evals/results/2026-07-20/routing-3sample-postfeedback.json`.

### Changed

- **Taxonomy-anchoring hypothesis tested and RETIRED** — the open question from
  v1.17.0, and the one that mattered most: the library is ~296 files of largely
  *enumerative* guidance, so if catalogues make a model pattern-match the list
  instead of applying the underlying question, that indicts the dominant content
  pattern. At n=6 novel mechanisms the unguided arm had scored 1.00 vs 0.83 for
  both library arms. The novel subgroup was grown **6 → 26** (20 mechanisms
  `rules/10` never lists — a `def` shadowing an imported validator, a signature
  compared against itself, `return` inside a loop body, middleware registered after
  its routes, an autouse fixture disabling the rate limiter suite-wide, a `chmod`
  that ORs permissions *wider*, an allowlist consulted after the request is sent, a
  seconds/minutes TTL mismatch, an inverted predicate, a wildcard allow shadowing a
  deny under first-match-wins, a feature gate read at import time, …). The set is
  now **69 cases: 35 enumerated positives, 26 novel, 8 negative controls.**
  **Result: not supported.** The gap collapsed to **0.96 vs 0.92 — a single case**,
  inside the per-arm run spread (0.91–0.96). The n=6 signal was small-sample noise,
  exactly as it was labelled, and the enumerative content pattern is **not** shown
  to reduce generalization to unlisted mechanisms. Overall library lift reproduced
  at **+0.00** on a set 40% larger and harder, consistent with the n=49 run.
  Logged but explicitly **not** claimed: the *ablated* arm scored 1.00 on the 8
  loud-control negatives vs 0.75 for both other arms — if anything the opposite of
  anchoring, hinting at mild over-flagging; 2 of 8, to watch if that set grows.
  `SILENT_VOCAB` extended with the 20 new slugs; no answer-key leakage (verified
  across both runners). Writeup:
  [`evals/results/2026-07-20/SILENT-FAILURE.md`](evals/results/2026-07-20/SILENT-FAILURE.md).

- **Docs hygiene against this cycle's work.** `evals/README.md`: silent-failure case
  count corrected 49 → **69** and the novel subgroup 6 → **26** (both stale), with the
  retracted +0.07 and the retired anchoring hypothesis stated in place. `docs/INDEX.md`
  gained rows for the two new writeups (AUDIT-PROCESS, SILENT-FAILURE) — the honest
  +0.00 results were previously unfindable from the index. `docs/ROADMAP.md`: the
  top item moved BLOCKED → IN PROGRESS with the arm-A number; "grow the eval case
  sets" replaced with what actually remains thin (the 8 negative controls, the 7-case
  completeness set, competitor domains beyond the five measured); and the distribution
  item grounded in measured traffic (~24 organic clones/day vs 7 stars, 0 watchers,
  1 issue ever — LinkedIn confirmed as top referrer).
- **New `evals/README.md` section: harness conventions**, written from four
  self-inflicted silent failures in one day — a prompt-field whitelist that dropped
  `prompt` (the routing eval sent bare ids and still printed a recall score), an
  ablation keyed on a section *number* that a renumber broke, a scripted CHANGELOG
  edit whose anchor did not exist on its branch, and a wait condition that matched a
  per-case progress line and called a still-running job complete. Rules: guards abort
  rather than warn; watch the guard fail before trusting it; wait on a terminal
  artifact, not a log substring; assert a scripted edit landed; pin what you mirror.
  `AGENTS.md` points at it — the same failure class `rules/10` describes, occurring in
  the tooling that measures the library.

### Fixed

- **The flagship completeness number is now verified against the workflow that
  actually ships — `0.58 → 0.98, +0.40`.** Both arms were run with one variable
  changed: the drifted mirror measured **0.59 → 1.00 (+0.40)** and the synced mirror
  **0.58 → 0.98 (+0.40)**. So the published `+0.39` was **never wrong** — it was
  measured against stale text and reproduces either way. `RESULTS.md`, `README.md`
  and `docs/WHY-IT-WORKS.md` now carry the synced figures rather than numbers
  produced by a workflow the library no longer ships. The 0.02 with-arm difference is
  **one case** (c1 lost transport, sizelimit, pagination) and is **not** separable
  from sampling variance in a single run — logged as a follow-up (repeat arm B 3×),
  not claimed, though it points exactly where our own
  [context-rot finding](docs/WHY-COMPLETENESS-RESIDUAL.md) predicts. Method,
  per-case table and limits:
  [`evals/results/2026-07-20/MIRROR-VERIFICATION.md`](evals/results/2026-07-20/MIRROR-VERIFICATION.md).
- **Eval artifacts are now secret-scrubbed at write time.** Artifacts store
  model-generated code verbatim, and a model asked to build a payments endpoint
  writes `sk_live_...` into its examples — which blocked a push on 2026-07-20 (two
  synthetic Stripe-shaped strings in `c1_ticket_api`'s generated code; not real
  credentials, but secret-shaped strings do not belong in a public repo: they trip
  push protection, train readers on a bad example, and bury a genuine leak in noise).
  `scrub_secrets()` replaces Stripe/AWS/GitHub/Slack/Google/PEM-shaped strings with a
  **visible** `[SCRUBBED-SECRET-SHAPED-STRING]` marker — the class, not the instance —
  and runs on every artifact write. Existing artifacts cleaned (4 → 0); recall scores
  are unaffected. Verified by feeding it known key shapes and confirming they are
  replaced. Note this is the *second* time push protection caught something local
  gitleaks did not: `.gitleaks.toml` disables the entropy rule so the security skills'
  deliberate examples don't false-positive, which also blinds it to vendor-specific
  patterns. Two scanners, two coverage sets.
- **`run-completeness.py`'s `BUILD_WORKFLOW` mirror had drifted from the router, and
  the drift class is now closed.** That constant is a hand-compressed mirror of router
  BUILD steps 3–4 (kept compressed so results stay comparable with every historical
  run) — but it is *not* a live read, and the falsification clause added to router
  step 4 in #119 was missing from it for four days. The project's most-cited number
  was therefore being measured against a workflow that no longer shipped. Nothing
  failed; the eval quietly measured the wrong thing.
  Fixed deliberately and measured, never synced blind: **arm A (drifted mirror)
  measured without 0.59 → with 1.00, LIFT +0.40**, reproducing the recorded +0.39 —
  so the figure was never wrong, only measured against stale text. The mirror is now
  synced and a **`ROUTER_BUILD_SHA` pin** was added: the runner hashes the router's
  BUILD section and **aborts** if it no longer matches what the mirror was synced
  against, rather than measuring unshipped text. Guard watched to fire on a synthetic
  router edit before being trusted.

## [1.17.0] - 2026-07-20

The **silent-failure release**, and an unusually honest one. New coverage for the
class where a control *looks* enabled and does nothing; adversarial refutation and
decision-ledger review added to AUDIT mode; and three new eval instruments — two of
which returned **+0.00**, plus a **headline lift that was measured, failed to
replicate on a larger set, and is retracted here rather than quietly kept**. No
skill added (41 unchanged): content, evals, and docs.

**Reading guide.** The library's audit dimension now saturates on four independent
instruments (recall, cross-file, silent-control, precision), so nothing added to the
audit path in this release carries an efficacy claim. What *is* measured and holding:
completeness +0.39, freshness +0.53, routing +0.10 (re-verified at 1.00 with-arm
twice in this cycle, after the router grew ~5%).

### Changed

- **Silent-control eval grown 15 → 49 cases, and its headline lift RETRACTED.**
  The 15-case set saturated the with-library arm (0.99–1.00), leaving no headroom
  to measure. The set now carries **41 positives + 8 negative controls** (loud
  failures, incl. a display-only truncation and a *documented deliberate*
  fail-open, both of which must NOT be flagged) and **6 positives tagged `novel`**
  — mechanisms rules/10 does not enumerate (case-sensitive blocklist regex vs
  lowercased input, unawaited async authz check, decorator/route ordering bypass,
  inverted config-merge precedence, a context timeout never attached to its
  request, a retry loop that swallows its final failure) — which separates
  "teaches the lens" from "recites its own list". Harder positives were added
  across Go/TS/SQL/YAML/Helm/Markdown.
  **Result: the +0.07 lift measured at n=15 does not replicate.** At n=49 it is
  **+0.03** (vocabulary design) and **−0.01** (open-ended design), both inside a
  per-arm spread of ±0.04; rules/10's own ablated contribution is **+0.00** (the
  vocabulary design's with- and ablated arms are *identical* — 0.918, zero spread,
  same four missed cases). `RESULTS.md` corrected from +0.07 to +0.00 with the
  retraction stated in place. One signal logged as a **hypothesis, not a finding**:
  on the 6 unenumerated mechanisms the *unguided* arm scored 1.00 and both library
  arms 0.83 — possible **taxonomy anchoring**, one case at n=6, needs a larger
  novel subgroup. Four cases defeat every arm (build-tag no-op, `*.yaml` glob vs
  `.yml`, env-filter mismatch, unawaited `expect().rejects`); adding them to the
  rule text was deliberately **not** done, as that would fit the guidance to the
  test set.
- **Both eval runners now whitelist prompt fields** (`id`/`language`/`snippet`)
  instead of blacklisting known answer keys — a new case field such as `novel` or
  `reference` can no longer leak the answer into the prompt just because nobody
  updated a strip list. `run-silent-open.py` additionally reports **novel** and
  **negative-control** subgroup recall per arm.

### Added

- **Audit-precision eval + the regression check for this PR** —
  `evals/cases/finding-adjudication.jsonl` (30 code+claim pairs, 15 genuine / 15
  plausible-but-wrong across six distinct refutation classes) and
  `evals/run-adjudication.py`, scoring **specificity** (refute the false claims) and
  **sensitivity** (keep the real ones) with an ablation arm that strips §6. Every
  other audit set here measures *recall*; this measures the false-positive side that
  refutation actually targets. **Result: +0.00 — all three arms 1.00**, zero wrong
  answers in 90 adjudications per arm. Run twice: the first framing enumerated the
  ways a claim can fail (i.e. handed §6's content to every arm) and was replaced with
  a neutral one — identical 1.00s, so the saturation is not a framing artifact.
  Routing was re-run as the regression check for today's three router edits and
  **held at 1.00** (lift +0.10, both matching the recorded multi-sample numbers).
  Completeness was deliberately **not** re-run and the reason is documented: all 17
  skill files it loads are unchanged since v1.16.0, its `principle5()` extract is
  byte-identical (sha `2a36f20d8e51`), and its `BUILD_WORKFLOW` is a hardcoded mirror
  — so it is structurally blind to today's changes and a green run would have been a
  vacuous test. That mirror's drift from the router is logged, not silently synced.
  **Four audit instruments now saturate** (recall, cross-file, silent-control,
  precision); the writeup states plainly that no current instrument can score an
  audit-*process* change, and recommends stopping additions to the audit path until
  an agentic one exists:
  [`evals/results/2026-07-20/AUDIT-PROCESS.md`](evals/results/2026-07-20/AUDIT-PROCESS.md).
- **Decision-ledger review in AUDIT mode** — `sota/rules/01-audit-methodology.md`
  gains **§6**, and the router's AUDIT workflow a **step 5**. Code passes find defects
  in what was built; they cannot find the defect where the code faithfully implements
  a choice that **stopped being right** — a datastore picked for scale that never
  arrived, a rewrite justified by a benchmark that no longer reproduces, an expired
  constraint still shaping the design. Reconstruct the expensive-to-reverse decisions
  (ADRs, design docs, CHANGELOG, the PRs that introduced each major component) and
  classify each **JUSTIFIED / STALE / UNJUSTIFIED / UNVERIFIABLE**, with STALE
  (sound when made, inputs since expired) kept distinct from UNJUSTIFIED (the stated
  reasoning never supported it). Where a decision rests on a **number**, re-run that
  measurement *this session* — a benchmark in a two-year-old ADR is a historical
  claim, not a current fact — or mark the decision unverifiable and say what would
  confirm it. Ledger-vs-code is checked **both** directions (recorded-but-not-
  implemented is as much a finding as implemented-but-not-recorded). Verdicts carry a
  severity and feed the roadmap. Report structure gains a **Decision ledger** section;
  one audit-checklist line added; §7–§9 renumbered.
  `sota-architecture` rules/01 §4 owns *writing* ADRs and is cross-referenced, not
  duplicated — this is the audit side. Verified the gap on current `main` first:
  zero hits for ADR/decision-record/stale-justification anywhere under `skills/sota/`.
  **Unmeasured, deliberately:** four audit instruments now saturate at +0.00
  (recall, cross-file, silent-control, precision), so no current eval can score an
  audit-*process* change — see
  [`evals/results/2026-07-20/AUDIT-PROCESS.md`](evals/results/2026-07-20/AUDIT-PROCESS.md).
  No efficacy claim is made, and this is the **last** planned audit-path addition
  until an agentic instrument exists.
- **Adversarial verification in AUDIT mode** — `sota/rules/01-audit-methodology.md`
  gains **§6 "Try to kill your own findings"**, and the router's AUDIT workflow step 6
  changes from *verify* to **refute**. Re-reading your own finding re-runs the
  reasoning that produced it, so it is the weakest check available; every
  Critical/High now gets an **independent pass prompted to kill it** — a separate
  agent or a fresh-context hostile read, working from the code at the pinned commit
  rather than the write-up, defaulting to REFUTED when evidence is ambiguous.
  Includes the three distinct refuter lenses (is the mechanism real / is it
  reachable / is the impact inflated), majority-refute-kills, **recording
  refutations** so the next auditor doesn't re-raise them, a refuter for absence
  claims, effort scaling by severity, and the two failure modes that make the pass
  theatre (the rubber-stamp refuter told to "verify" rather than refute, and
  refuting the *description* instead of the code). Report §7 and hygiene §8
  renumbered accordingly; one audit-checklist line added.
  Adopted from a field-tested external audit harness — verified first that the
  library had **no** independent-refutation language anywhere (`grep` for
  refut/adversarial/independent-verify across `sota/` and `sota-testing/` returned
  zero hits), so this is a genuine gap, not a restatement. **Unmeasured:** the audit
  dimension already saturates at +0.00, so the existing evals cannot show a lift
  here; no efficacy claim is made.

- **`sota-code-security` rules/10 "Silent control failure"** — a new rule file for
  the class the library had no home for: a control, feature, or safeguard that
  **appears active but does nothing**, where a broken system and a working system
  are indistinguishable from the outside. Organized around the *falsification
  question* ("if this were silently a no-op, would anything observable differ? —
  if no, that IS the finding"), then eleven places no-ops hide: weak existence
  checks (`exists()`/`is_dir()` standing in for a loaded artifact), optional-
  dependency degradation (`except ImportError` → feature vanishes), empty or
  placeholder rulesets loaded as real, swallowed exceptions on the enforcement
  path, overloaded flags, attacker-triggerable early returns, truncation before
  inspection, config keys silently ignored by permissive schemas, doc/code drift
  on defaults, hardcoded numbers in tool output, and **shipped-artifact gaps**
  ("works in a dev checkout, dead in the image"). Plus the mutation probe for
  vacuous tests (with the two traps that make a green run lie), the shared
  deduped-per-cause degraded-control helper, and the evidence rules — including
  that **a negative claim needs more proof than a positive one**.
  A prior gap analysis confirmed 9 of these 12 concepts had no coverage anywhere
  in the tree; fail-open (rules/03) and test vacuity (`sota-testing` rules/02/06/
  09) were already covered and are cross-referenced rather than duplicated.
- **The lens is now part of the default BUILD and AUDIT paths**, not an opt-in
  file: the router's BUILD self-audit gate (step 4) asks the falsification
  question of every control in the diff; AUDIT mode gains a **step 4
  "silent-control pass"** run over the controls the domain passes confirmed
  exist (the class is invisible to those passes and to pattern-based SAST,
  because the code isn't wrong — it's inert); `sota-code-security` BUILD mode
  gains step 6 ("every control must be falsifiable") and AUDIT mode step 5
  ("check the inert"); and routing rule 20 ("'it's enabled' is a claim, not a
  fact") points at it from the router.
- **Asymmetric evidence burden for negative claims** — router operating
  principle 3 and `sota/rules/01-audit-methodology.md` §5 now require a widened
  search plus a second independent method before asserting "no instances of X",
  and require positive observations to be evidenced by **effect** (a rejection,
  a log, a test that fails when the control is disabled) rather than presence.
  Two audit-checklist lines added.
- **Eval case set for the silent-control class** — `evals/cases/silent-failure.jsonl`
  (15 cases: 13 positives, one per hiding place, across Python/Go/JS/YAML/Dockerfile,
  plus **2 negative controls** whose correct answer is "not silent" so an
  over-flagging arm cannot score 1.00), a `silent` kind in `run-clean.py`, a new
  **`--ablate`** flag that drops rules/10 from the with-library arm to isolate a
  single file's contribution, and `evals/run-silent-open.py` — an open-ended,
  no-vocabulary variant graded by a **different** model blind to the arm.
  **Result, reported as measured:** at the initial 15 cases the library appeared to
  lead **0.92 → 0.99 (+0.07)**, and that number briefly shipped in `RESULTS.md`.
  **It did not replicate and is retracted** — see the grow-the-set entry below.
  The design's own limit is documented: both arms must be *told* to hunt inert
  controls, and that framing is the falsification question itself, so what the rule
  actually adds — asking unprompted — is what this design cannot measure. Writeup,
  raw artifacts, and limitations:
  [`evals/results/2026-07-20/SILENT-FAILURE.md`](evals/results/2026-07-20/SILENT-FAILURE.md);
  scoreboard row added to `evals/results/RESULTS.md`.
- Cross-references so each home keeps its own doctrine: `sota-testing` rules/06
  (hand-mutating a control's body as a no-tooling audit probe, plus the
  missing-dependency and mutation-didn't-take traps), `sota-observability`
  rules/05 (one shared degraded helper, deduped per cause not per request),
  `sota-devsecops` rules/04 (the built image must contain what the code needs at
  runtime; smoke-test controls against the artifact, not the checkout).

- **`sota-docs-workflow` rules/01 §8 "The documentation baseline"** — the must-have
  doc set every repo should carry, closing a real gap (the individual docs were
  covered but scattered, and the community-health files SECURITY/CODE_OF_CONDUCT/
  SUPPORT/GOVERNANCE were absent entirely). Enumerates *always* (README + LICENSE +
  CHANGELOG) vs *trigger-based* (CONTRIBUTING/CODE_OF_CONDUCT/SECURITY once public,
  runbooks once on-call, AGENTS.md for AI-assisted repos, ADR log, CODEOWNERS), with
  GitHub's community-health-file search precedence (`.github/` → root → `docs/`,
  verified against GitHub docs) and the single-canonical-home rule so the baseline
  itself doesn't become sprawl. Two audit-checklist lines added; SKILL index + BUILD
  step updated.

### Changed

- **`evals/results/RESULTS.md` now embeds the five-domain breadth chart** and
  carries the full breadth story inline (chart + table + 0.7-baseline threshold +
  the "why the baseline predicts the lift" mechanism), so the scoreboard is
  self-contained instead of splitting the visual off into `BREADTH.md`. `BREADTH.md`
  stays as the per-domain-notes and raw-data appendix.

## [1.16.0] - 2026-07-16

The competitor + breadth release: a fair, blind, reproducible head-to-head against
the most popular guidance libraries; a five-domain breadth study showing the lead
tracks the *unguided baseline*, not the domain; three conventions distilled from an
external review (each independently measured); plus a discoverability and
eval-harness overhaul. No skill added (41 unchanged) — content, evals, and docs.

### Added

- **Three conventions adopted from an external agent-orchestration review**
  (pure-Markdown, generic; runtime-bound ideas like memory-bank persistence,
  RAG, and worktree locks were deliberately skipped):
  1. **Negative routing cross-references** — 9 confusable skill descriptions now
     name the sibling to use instead ("Not for X — use sota-Y": api-design,
     observability, async-concurrency, performance, threat-modeling, devsecops,
     cli-ux, databases, docs-workflow), sharpening disambiguation inline. No
     harness reads skill descriptions, so this is off every measured eval path.
  2. **Plan-concreteness** — router BUILD step 3 now requires each planned
     checklist item be a concrete, checkable done/not-done outcome (vague items
     rejected); mirrored into `run-completeness.py`'s `BUILD_WORKFLOW` so the eval
     reflects the real workflow.
  3. **Evidence-based completion** — new router operating principle 6: never claim
     "done"/"working" from plausibility; state the check run and its result.
  Regression-tested (our [context-rot finding](docs/WHY-COMPLETENESS-RESIDUAL.md)
  warns added text can lower salience): the 3× completeness eval held at **0.991
  with-arm / +0.385 lift** (vs 0.996 / +0.395 — Δ −0.005, within sampling noise;
  no cross-cutting concern systematically dropped), and the 3× routing eval (which
  pastes the whole router, so it sees principle 6) **held at 1.00** with-arm, no
  misses. Raw: `evals/results/2026-07-13/completeness-3sample-postadopt.json` +
  `routing-3sample-postadopt.json`; summary in `evals/results/RESULTS.md`.

- **Description-based routing eval** (`evals/run-desc-routing.py`,
  `evals/cases/desc-routing.jsonl`, `results/2026-07-13/desc-routing-3sample.json`)
  — the first measurement of the skill **auto-loader** path (pick a skill from the
  description catalogue), distinct from the router table. A/Bs the catalogue with vs
  without the negative cross-references added above, on 10 adversarially-confusable
  tasks. **Honest +0.00:** the model never routed to the warned-against sibling in
  *either* arm (distractor-pick 0.00 across all cases/samples), so the cross-ref had
  nothing to fix — the description-selection path is already saturated for a frontier
  model, like audit. The cross-refs are kept as zero-cost defensive clarity; no
  routing lift is claimed. Summary in `evals/results/RESULTS.md` §5.

### Fixed

- **Accuracy sweep (4-way doc audit against the result JSONs).** Corrected claims stated more strongly than the data: the **web-search recovers/can't-recover** claims (freshness + completeness) were never measured — now marked as predictions; the live-agent 0.99 was called *identical* to the 0.99 simulation (actually 0.987 vs 0.988) — softened to *matching*; `claude-skills` 3-tightest confidence 83% → **82%** (recomputed 0.8249); DECAY guidance/filler sizes were tokens mislabeled as KB (18.7 KB → **~18.6K tokens / ~72 KB**); freshness **+0.65** was mis-attributed to the 32-case set (it's a 20-case run; 32-case is +0.53); `completeness-blind-spot` upload 0.55 → **0.58** (multi-sample mean); ROADMAP item 6 and the AGENTS.md WHY-IT-WORKS pointer were stale (competitor benchmark is done, WHY now carries a scoped vs-libraries section); star counts dated. Cited literature was spot-verified accurate (Chroma 2025 '18 models') and left as-is.

### Added

- **Competitor breadth experiment (five domains) — concludes the comparison.**
  `evals/results/2026-07-13/BREADTH.md` plus the case/manifest/result files for
  Go backend, complex frontend (SSR/auth), simple frontend, and IaC
  (`evals/cases/completeness-{go,iac,frontend,frontend-complex}.jsonl`,
  `evals/cases/competitors-{go,iac,frontend}.json`,
  `results/2026-07-13/competitor-breadth-{go,iac,frontend,frontend-complex}.json`);
  `run-competitors.py` gained `--cases`/`--manifest`/`--ids`/`--samples`/`--temp`
  and incremental `--out` saving. **Finding: the lead tracks the *unguided
  baseline*, not the domain.** Below a ~0.7 baseline (Python backend 58%→lead +12,
  Go 67%→+10, hard SSR/auth frontend 53%→+10) SOTA-skills leads every competitor by
  ~10 pts; above it (simple React forms 77%→+0, templated IaC 87%→+0) everyone
  converges. This **supersedes** the earlier "backend-specific" reading — the first
  frontend run used *easy* forms; a re-run with the invisible concerns (server-side
  authz, secret-boundary leakage, injection, hydration, CSP) shows SOTA-skills leads
  hard frontend too. All docs (README, WHY-IT-WORKS, RESULTS, COMPETITOR-BENCHMARK,
  ROADMAP) reframed from "backend-specific" to baseline-driven.
- **Five-domain breadth chart** (`assets/breadth-{light,dark}.svg` + matching
  1520px `.png`, regenerable via `assets/gen-breadth-chart.py`) — a theme-aware
  grouped bar of unguided / best-competitor / SOTA-skills completeness across the
  five domains, ordered by baseline so the lead-where-incomplete pattern is visible;
  embedded in `BREADTH.md`. Palette validated with the dataviz skill's checker.
- **Competitor-benchmark bar chart** (`assets/benchmark-{light,dark}.svg` +
  matching 1440px `.png`, regenerable via `assets/gen-benchmark-chart.py`) — a
  theme-aware visual of best-practice completeness per library (SOTA-skills 99%
  highlighted vs the field), embedded in the README, `evals/results/RESULTS.md`,
  and `docs/WHY-IT-WORKS.md` via `<picture>` (light/dark SVG). The PNGs are for
  LinkedIn/slides/anywhere SVG isn't supported. Palette validated with the dataviz
  skill's checker; alt text carries the numbers.
- **Discoverability overhaul.** `docs/INDEX.md` (a find-it-fast map: every topic →
  where it's documented, organized by intent), `docs/CONTEXT-MANAGEMENT.md` (the
  single home for how the library keeps the model applying rules as context fills —
  the re-injection hook, principle 5, terminal re-read, deterministic gates, and
  the *why*), and `evals/results/RESULTS.md` (a consolidated scoreboard of every
  measured number). README gained a **table of contents** and deep-doc links; both
  new indexes are linked from AGENTS.md.
- **Skill-application decay eval** (`evals/run-decay.py`,
  `results/2026-07-13/DECAY.md`) — the first measurement of the *temporal*
  (multi-turn) dimension of rule forgetting, not just single-call. Arms: anchor /
  reminder (the `UserPromptSubmit`-hook analog) / control. First run: **no decay at
  moderate scale** (guidance held over 30 unrelated turns); bounds the problem but
  needs a bigger intervening context to find the breaking point (roadmap item 5).

### Changed

- **Every competitor-repo reference now uses its full `owner/repo` name + a
  GitHub link** (no bare "ECC"/"claude-skills"/"awesome-cursorrules", which
  collide with unrelated same-named repos), and `evals/results/RESULTS.md` bundles
  all competitor numbers into **one consolidated per-repo table** (completeness,
  confidence, gap vs SOTA, head-to-head).
- **The 500-line cap now applies to skill Markdown only** (`skills/**/*.md`), where
  it's load-bearing for incremental loading. README, CHANGELOG, and `docs/` are
  uncapped — navigability comes from the TOC + `docs/INDEX.md`, not a line ceiling.
  CHANGELOG archiving is now optional hygiene, not forced. *(PR #100)*

Evaluation-harness additions (no skill-content change; not in CI — see
`evals/README.md`). These execute two roadmap follow-ups from v1.15.0.

### Added

- **Cross-file repo-audit eval** (`evals/run-repo-audit.py`,
  `evals/cases/repo-audit.jsonl`, `evals/cases/repo-audit/orderdesk/`). A 15-file
  FastAPI fixture with **8 defects that are invisible in any single file** (an
  authz check one layer assumes another enforces, a taint crossing modules, an
  invariant one file documents and another violates, an insecure default trusted
  by its caller). Answers roadmap item 3 — the only identified path to a real
  audit lift. Result: **+0.00** on both `claude-sonnet-4.6` and `claude-opus-4.8`
  (strict, file-attributed scoring). When the whole repo fits in one context, a
  capable model reads across files unaided; making defects cross-file changes
  nothing while every file is visible. The library makes **no audit-lift claim**;
  the real frontier is a repo too large to hold at once (agentic selective
  reading), logged as the open follow-up
  (`evals/results/2026-07-13/REPO-AUDIT.md`).
- **Live-agent BUILD validation** (`evals/judge-live-build.py`). Closes the
  completeness eval's one simulation gap (roadmap item 2): `run-completeness.py`
  *pastes* the router's principle 5 + rules to stand in for what an agent loads.
  This scores artifacts from a **real sub-agent** driven over each build task
  through the actual router BUILD workflow, with the same blind opus judge and
  rubrics. Live-agent mean completeness is **0.99 (6/7 perfect)** — identical to
  the 0.99 paste-based simulation and vs 0.60 unguided base, confirming the
  simulation is a faithful proxy. Result: `evals/results/2026-07-13/LIVE-BUILD.md`
  (+ `live-build.json`).
- **Multi-sample eval tightening** (roadmap item 1) —
  `evals/results/2026-07-13/MULTI-SAMPLE.md` + `completeness-3sample.json` +
  `routing-3sample.json`. Re-ran the value dimensions at `--samples 3 --temp
  0.7`: completeness **0.60 → 1.00 (+0.39)** (reproduces the single-sample
  headline; with-arm ±0.01 across-case sd, 6/7 cases perfectly steady), routing
  **0.90 → 1.00 (+0.10)** (with-arm ±0.00), freshness **0.44 → 0.97 (+0.53)**
  (reused 3× run). The with-library arm is near-zero variance everywhere; the
  sampling wobble is all in the unguided arm. Retires the single-sample caveat in
  `docs/WHY-IT-WORKS.md`.
- **Publication draft** — `docs/writeups/completeness-blind-spot.md`, a
  reader-facing write-up of the completeness/salience finding (context rot →
  dropped rate-limiting; adding rules made it worse, a short reminder fixed it),
  with the before/after data and honest boundary. Draft for the maintainer to
  publish (roadmap item 7, distribution).

### Added

- **Competitor benchmark** (`evals/run-competitors.py`,
  `evals/cases/competitors.json`, `results/2026-07-13/COMPETITOR-BENCHMARK.md`) —
  SOTA vs. the most popular competing guidance libraries on the 7 completeness
  tasks, content-only and blind-judged. **SOTA-skills 0.99 vs
  [affaan-m/ECC](https://github.com/affaan-m/ECC) (~230k★) 0.87,
  [PatrickJS/awesome-cursorrules](https://github.com/PatrickJS/awesome-cursorrules) (~40k★) 0.83,
  [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) (~23k★) 0.81**;
  unguided 0.58. SOTA wins or ties every one of the 21 head-to-head cases and
  loses none; competitors are legitimate (all beat unguided by +0.23–0.28) but
  drop the cross-cutting non-negotiables (rate limiting, transport, tests) SOTA
  embeds. Clears the roadmap honesty gate for a scoped, reproducible "vs library
  X" claim; `docs/WHY-IT-WORKS.md` now carries it. A **3-sample/temp-0.7 confidence
  check** on the 3 tightest cases confirms the lead holds — SOTA's worst sample is
  ≥ each competitor's best, and the gaps match the single-sample run. The harness
  gained `--samples/--temp`, `--ids`, and crash-safe incremental `--out` saving.

### Changed

- **README surfaces the measured lift up front** — the dense one-liner is now a
  scannable per-dimension list (completeness +0.39, freshness +0.53, routing
  +0.10, with the multi-sample endpoints and the "near-zero variance" note). The
  clone/script install method now sits in the top quick-install block right after
  the plugin commands; the Installation section keeps the clone-path details
  without repeating the command blocks.

## [1.15.0] - 2026-07-13

The measured-efficacy release: completeness proven as the library's thesis, the
one residual root-caused, and the BUILD workflow rewritten around it.

### Added

- **Completeness eval — the library's thesis, measured** (`evals/cases/completeness.jsonl`,
  `evals/run-completeness.py`). Given a minimal "build X for my app" prompt with
  no security/logging cues, does the model embed best practices from v1? Clean
  raw-API, generate-then-**blind-judge** (opus-4.8 grades sonnet-4.6's artifacts,
  blind to arm), 7 build tasks. Vs. an unguided model the full library lifts
  best-practice coverage **0.60 → 0.99 (+0.39), 6/7 tasks perfect** — embedding
  the tests/rate-limits/logging/transport a base model *systematically* skips.
  Unlike freshness, this is **not** recoverable by "verify via search" (an agent
  won't search "should I add rate limiting"), which makes it the most defensible,
  least-redundant value. Ablation: base 0.60 → +rules ~0.89 → +BUILD self-audit
  0.93 → +router principle 5 0.99.
- **`docs/WHY-IT-WORKS.md`** — the measured case, framed honestly (**vs. an
  unguided model**, explicitly *not* vs. other libraries — we haven't benchmarked
  one) + the four in-repo-verifiable benefits (auto-routing/composition,
  freshness-maintained + primary-source-cited, build+audit, CI-gated quality).
  README hero links it.
- **`docs/WHY-COMPLETENESS-RESIDUAL.md`** — why a with-library build still
  occasionally drops a cross-cutting rule, and the design that counters it.

### Changed

- **Root-caused the completeness residual; it is a salience / context-length
  attention effect, NOT a "coverage gap"** (`docs/WHY-COMPLETENESS-RESIDUAL.md`).
  In all 7 tasks the forgotten rule was in context *and* in a pasted Audit
  checklist, yet dropped. Five controlled experiments (+ a 4-case recovery test)
  disprove the coverage story: **adding the missing rule files made it worse**
  (context 72→100 KB, compliance fell — live context rot), while a **short salient
  reminder recovered it to 1.00**. Matches the literature — context rot
  ([Chroma 2025](https://www.trychroma.com/research/context-rot)), lost-in-the-middle
  ([Liu 2023](https://cs.stanford.edu/~nfliu/papers/lost-in-the-middle.arxiv2023.pdf)),
  instruction-count decay ([arXiv 2507.11538](https://arxiv.org/html/2507.11538v1)).
  It occurs in a single call, so it is not a workflow/subagent artifact — chains
  only amplify it.
- **Router BUILD workflow rewritten around the finding** (`skills/sota/SKILL.md`):
  a **hard self-audit gate** (step 4 — do not present code until every checklist
  item is implemented or explicitly scoped out); a short **operating principle 5**
  (universal non-negotiables — rate-limiting / transport / tests / logging on any
  endpoint, kept short for salience, 947→765 chars); **load lean** (extra
  similar-looking rules *measurably lower* compliance — correctness, not economy);
  **plan with the checks up front**; **self-audit LAST with a terminal re-read**
  (recency); plus recommend a separate fresh-context audit pass + deterministic
  CI gates. The eval's with-arm now pastes principle 5, so its number reflects the
  real library.
- **Eval suite hardened and validated against primary sources.** Completeness
  4 → 7 build tasks (+search, webhook, password-reset). **Freshness 20 → 32
  cases** (+12 across languages/security/cloud/crypto/web specs, each
  grep-confirmed in the library and primary-source-verified) — lift **+0.50**
  (with 0.97, without 0.47), and +0.53 at 3 samples; the base model still
  *fabricates* (RFC 9334 for EAT, PG 17 for `uuidv7`). **Harder audit 7 → 14
  cases** (realistic, non-telegraphed, multi-vuln: IDOR / SSRF-bypass / TOCTOU /
  prototype-pollution / ReDoS) — **still +0.00**: a capable model catches them
  *in isolation*, so a real audit lift needs cross-file context, not more
  snippets. **Multi-sample** `--samples N` / `--temp T` on both harnesses
  (default 1 / 0), plus 32k gen cap / 100k judge window / progress logging +
  retries for observable, resilient long runs.

## [1.14.1] - 2026-07-11

### Changed

- **Grew the freshness eval 8 → 20 cases** (`evals/cases/freshness.jsonl`): +12
  objective 2026-current-fact cases across domains (TypeScript 7 GA, Cilium
  ztunnel, PQ MLKEM768, OpenAPI 3.2, K8s user-ns 1.36, Keep-a-Changelog 2.0,
  MISRA C:2025, RateLimit draft status, SCIM RFC 9967, libFuzzer maintenance,
  Azure Cobalt 200, rust-lld 1.90) — each verified present in the library +
  primary-source correct + token-scorable. Clean 20-case lift **+0.65
  (sonnet-4.6) / +0.50 (opus-4.8)**, with-library 1.00 on all 20. The tighter
  set strengthens the finding and reveals the base model **fabricates**
  plausible wrong facts with confidence — invents RFC 9440 for RateLimit
  headers, RFC 9816 for SCIM events; "Cobalt 100" not 200, "MISRA C:2023" not
  2025, Keep-a-Changelog "1.1.0" not 2.0. BASELINE.md / README / ROADMAP
  updated to the robust 20-case figures.

## [1.14.0] - 2026-07-11

### Added

- **code-security rules/04 §8 — Tamper-evident logs & audit ledgers** (NIST
  AU-9/AU-10). New section codifying the audit-ledger pattern: unkeyed hash
  chains detect accidents, not adversaries (HMAC or external anchoring
  required); tail truncation / whole-stream deletion is invisible to
  chain-walk verification; hash every attested field incl. server timestamps;
  canonical preimage encoding (§7); **integrity ≠ completeness** (attest and
  report separately); verification must be possible off the storing system;
  vantage (self-reported vs independent chokepoint →
  detection-engineering rules/02); erasure-by-design for immutable stores
  (privacy rules/03 §4 crypto-shredding). +2 audit-checklist items;
  code-security SKILL.md index row and router rule 18 (crypto fan-out)
  updated. Motivated by a real audit of a public "tamper-evident AI-agent
  ledger" where this gap class recurred (unkeyed SHA-256 chain marketed as
  compliance evidence).

- **Eval golden sets + efficacy baseline + clean isolated control** (roadmap
  Next, done). Cases expanded to 20 routing + 13 audit + 7 harder audit
  (`evals/cases/`). New `evals/run-clean.py` — a **raw model-API** harness
  (OpenRouter, key from `.env`, never committed) that removes the in-session
  contamination entirely (no HOME/`CLAUDE.md`/skill-registry) for a true
  library-vs-nothing control. Findings (all in
  `evals/results/2026-07-10/BASELINE.md`, raw in `results/2026-07-11/`):
  **routing recall lift replicates ~+0.10 in the clean control** — +0.09
  (sonnet-4.6), +0.14 (sonnet-5), +0.09 (opus-4.8), with-library 1.00 each;
  even opus-4.8 misses the same rule-driven skills without the router (r01
  testing, r02 sandboxing, r07 code-security, r09 web-frameworks). So the
  in-session +0.08/+0.11 was **not** a contamination artifact — the routing
  lift is real and attributable to the cross-cutting rules. README now cites
  the freshness evidence ("Measured, not asserted") linking `evals/`. **Audit
  lift = +0.00, model-independent** (haiku→sonnet-4.6, original + harder cases):
  strong models recognize textbook vulns library-or-not. **Freshness lift =
  +0.75 (sonnet-4.6) / +0.50 (opus-4.8)** on **8** objective 2026-current-fact
  cases (`cases/freshness.jsonl`, each answer carried in a rules file;
  with-library 1.00) — the decisive finding: the base model is not just missing
  current facts but **confidently wrong** (asserts RFC 7489 not 9989, OWASP A04
  not A06, ingress-nginx "maintained", NIST "8 chars" not 15, TorchServe
  "maintained"), while the with-library arm is 1.00. So the library's value is
  currency (large lift, ~5–7× routing), not routing/recognition (small/zero).
  Also: `.env` added to `.gitignore` (was untracked but unignored).

## [1.13.0] - 2026-07-10

### Added

- **Content-accuracy runbook + eval harness** (2026-07-10 audit STRAT-HIGH-1/2,
  the two top strategic gaps). `docs/MAINTENANCE.md` documents the reproducible
  per-skill re-verification sweep (extract rot-prone claims → verify vs primary
  sources → fix under the no-pins/EOL policies → adversarial re-verify → bump
  `LAST-VERIFIED`) that previously lived only in maintainer memory, and states
  honestly which dimensions are CI-automated vs human/agent discipline. The
  freshness re-verify window is cut **12 → 6 months** (content drifts far
  faster; 6mo stays clearable). New `evals/` prototype: a runnable
  efficacy-regression harness — golden-set cases (`cases/router.jsonl`,
  `cases/audit.jsonl`) + `score.py` (recall/precision vs an agent's
  predictions, exit 1 on any miss). Deliberately not in CI (an LLM eval is
  non-deterministic); it gives a repeatable with-vs-without baseline. Harness
  verified end-to-end this session (perfect predictions → exit 0, misses →
  exit 1); AGENTS.md/CONTRIBUTING.md link the runbook.
- **Invariant 7 — router completeness** (`check-invariants.sh`): every domain
  skill must appear in the router's routing table AND library map; every map
  entry must name a real skill. Automates the drift class the 2026-07-10 audit
  found (the 41st skill was missing from the map for a full release).
  Documented in AGENTS.md/CONTRIBUTING.md.

### Changed

- **Roadmap re-cut around the 2026-07-10 audit** (`docs/ROADMAP.md`): the
  2026-07-01 cycle (fully executed) demoted to history; a fresh Now/Next/Later
  reflects the audit — Now (prove/protect accuracy) closed this cycle, Next
  (grow evals + first 6-month sweep), Later (distribution over coverage,
  STRAT-MED-1). Fixed two STALE bookkeeping items the audit flagged: the
  2026-07-08 sweep is a "34-skill" pass (not "full-library" — it covered 34 of
  40 skills), and the low-severity-triage tally no longer implies 58+32=75
  (the ~75 candidate findings split across files into more line-items).
- **Invariant-gate hardening** (2026-07-10 audit): check 2 now tracks code-fence
  state so a `## Audit checklist` inside a fence no longer satisfies the
  "ends-with" rule (the 2026-07-01 fix was incomplete; verified identical
  verdicts on all current files); check 5's semver guard is a strict
  `X.Y.Z` regex that rejects interior malformations (`1..2`, `1.2`, `1.2.3.4`);
  and CI now fails loudly if `SOTA_DENYLIST` is empty on a trusted (push-to-main
  or same-repo-PR) run instead of silently degrading check 3 to generic-only
  (S-MED-1). Each change adversarially tested to confirm it catches the
  violation.

### Fixed

- **Installer script defects** (2026-07-10 audit): `install.sh` no longer
  aborts (`set -e`, exit 1) when the user declines a routing prompt — routing
  setup is best-effort and now always returns success, so pre-commit setup and
  the final instructions still run (Q-MED-4, reproduced fixed: exit 0, reaches
  the end); `install.sh` profile-linking no longer silently clobbers a real
  file in `~/.claude/profiles` — it backs up + asks first, matching
  `setup_claude_md`'s contract, and keeps the file untouched non-interactively
  (Q-MED-5, reproduced: user content preserved); and `init-gates.sh` writes
  `.pre-commit-config.yaml` as 644 instead of the `mktemp` 600 (Q-LOW).
- **Audit 2026-07-10 content corrections** (all primary-source verified):
  OWASP Top 10 2025 mislabel — Insecure Design is **A06**, not A04
  (`sota-code-security` rules/09); JSON Merge Patch citation **RFC 7386 →
  7396** (obsoleted 2014, `sota-api-design` rules/01); ingress-nginx wording —
  the 2026 CVE wave **was** patched in the final releases (≥1.13.9/1.14.5/
  1.15.1), the standing risk is post-EOL CVEs (`sota-kubernetes` rules/01);
  Iceberg v3 "GA across major engines" overstated → GA on Snowflake/Databricks/
  Spark, Trino still lagging (`sota-data-engineering` rules/01); a
  `grep -v "--"` end-of-options bug in an audit checklist
  (`sota-javascript-typescript` rules/07); a dangling retired-convention
  "last-verified" reference (`sota-confidential-computing` rules/04); and
  ~7 rot-prone version pins reworded to the no-pins policy (Rust 1.96→"recent
  stable", golangci-lint, Swift, Flutter, PHP, Ruby, Vue/Nuxt patch→minor).
- **Router library map** (`skills/sota/SKILL.md`) — added the missing
  `sota-confidential-computing` bullet (41st skill) and refreshed the stale
  `sota-testing` (→09) and `sota-docs-workflow` (→05) bullets. Routing table
  and per-skill indexes were already correct; only the map overview drifted.

### Added

- **`docs/AUDIT-2026-07-10.md`** — second adversarial repository audit (13
  fan-out auditors across 4 lenses + refutation pass, at v1.12.1). Verdict:
  **strong health** — all 6 invariants pass, supply-chain pins genuine, ~150
  rot-prone content claims sampled and primary-source-verified with only a
  handful of small errors, no dangerous advice. Headline findings are
  strategic: no automated content-accuracy gate, no eval harness, coverage
  expansion exhausted vs near-zero adoption. Plus a tail of low-severity
  content/script defects (OWASP A04→A06 mislabel, RFC 7386→7396, ingress-nginx
  "unpatched" wording, router library-map omission of the 41st skill,
  `check-invariants` check-2 fence bypass, two `install.sh` interactive-path
  bugs, ~8 residual version-pins). 11/11 non-trivial findings survived
  adversarial verification; 0 refuted.

## [1.12.1] - 2026-07-10

### Added

- **`sota-network-security` rules/06 — email authentication & anti-spoofing**
  (R12–R14): the library had no coverage of SPF/DKIM/DMARC beyond incidental
  mentions — a real gap given domain spoofing (BEC/phishing) and deliverability.
  Adds SPF (RFC 7208, `-all`, 10-lookup limit), DKIM (RFC 6376, >=2048-bit +
  rotation), **DMARC** (RFC 9989 — the 2026 Proposed Standard obsoleting the
  original RFC 7489; reporting RFC 9990/9991) with the `p=none→quarantine→reject`
  progression and alignment as the actual anti-spoofing control, MTA-STS
  (RFC 8461) + TLS-RPT (RFC 8460) + DANE-for-SMTP (RFC 7672), parked/non-sending
  domain lockdown, ARC (RFC 8617), and the Gmail/Yahoo bulk-sender requirements
  (5,000+/day: SPF+DKIM+aligned DMARC, RFC 8058 one-click unsubscribe, spam
  <0.3%). BIMI noted accurately as an IETF draft (not an RFC), VMC optional.
  Three audit-checklist items + SKILL/router routing updates. Cross-refs
  sota-copywriting rules/04 (marketing-mail content law) and
  sota-detection-engineering (DMARC RUA as a spoofing feed). Every claim
  primary-sourced (RFC editor/IETF datatracker + the Gmail/Yahoo sender rules).
- **`sota-network-security` rules/05 — self-hosted / bare-metal DDoS
  hardening** (R8.1): the one gap in the library's DDoS coverage. Existing
  guidance assumed a scrubbing edge (Cloudflare/Shield/Cloud Armor); this
  adds the L3/4 kernel layer for edges with no provider in front — TCP SYN
  cookies + nftables synproxy (prereqs per the nftables wiki), conntrack-table
  exhaustion sizing/alerting, reverse-path filtering (RFC 3704), and
  not-being-an-amplifier hygiene (BCP 38 / RFC 2827 — no open DNS/NTP/
  memcached/SSDP/chargen reflectors). R8 reframed to name edge scrubbing
  generically (Anycast/provider tiers), with cross-refs to
  sota-cloud-infrastructure rules/03 §10. Two audit-checklist items + SKILL
  index/scope/trigger updates. All claims primary-sourced (nftables wiki,
  kernel.org ip-sysctl, RFC 2827/3704).

## [1.12.0] - 2026-07-09

### Added

- **`sota-confidential-computing`** — confidential computing and cryptographic
  PETs (41 skills total): protecting workloads and data in use from the
  infrastructure they run on — the explicit inverse of `sota-sandboxing`
  (router cross-cutting rule 19 encodes the boundary). SKILL.md + 5 rules:
  01 threat model & selection (CCC definition test — memory encryption alone
  is not CC; five-rung escalation ladder; adversary→mechanism table),
  02 TEE technologies (SEV→SEV-ES→SEV-SNP insufficiency ladder, TDX on
  TME/TME-MK, ARM CCA status incl. Azure Cobalt 200, SGX/LibOS reality,
  Nitro Enclaves' distinct trust model, NVIDIA confidential GPUs,
  side-channel posture), 03 remote attestation (RATS RFC 9334 roles,
  attest-then-release, evidence hard rules, hosted vs self-hosted verifiers,
  TCB recovery, RA-TLS/IETF SEAT), 04 confidential Kubernetes (nodes vs pods,
  CoCo/Kata/Trustee KBS, AKS preview retirement caveat, operational reality),
  05 PETs/COED (FHE families + ISO/IEC 28033 + NIST PEC, MPC/threshold, ZKP
  circuit risk, PSI/OPRF, TEE-vs-PET-vs-DP selection). Built by 5 parallel
  research agents + 2 adversarial verifiers; 54 claims re-verified, 8
  corrected against primary sources (CCC, AMD/Intel/Arm docs, RFC editor,
  Azure/GCP docs, CNCF, NIST, ISO). Per repo policy no current-version pins —
  "latest stable, verify at time of use" throughout.
- **README "how it works" diagram** (`assets/how-it-works.png` + HTML source):
  a four-stage invocation flow (plain prompt → auto-routing → selective
  rules-file loading → BUILD/AUDIT application) with a worked file-upload
  example showing 4 skills loading automatically. Deliberately count-stable
  ("40+") so it never needs re-rendering on skill additions. Also clarified
  two README lines: the language-standards bullet no longer reads as
  "only 4 languages supported", and the invoicing example prompts no longer
  imply the user must name a stack (profile/skill defaults fill it in).
- **Count-surface floor model for the social preview**: the image pill and
  README alt now read **"40+"** so the PNG needs no re-render/re-upload per
  skill addition; `check-invariants.sh` gained `ck_floor` (fails only if the
  tree count drops below the floor); PNG re-rendered once; RELEASING.md
  updated.

### Fixed

- **Low-severity sweep triage (2026-07-09)** — the never-verified
  low-severity suggestions from the 2026-07-08 sweep (~75 candidate findings)
  were re-verified hypothesis-by-hypothesis against primary sources by one
  agent per skill: **58 applied** (each cites the verifying source; e.g.
  GraphQL @oneOf per the September 2025 spec edition, Mercurius WS depth-bypass
  CVE-2026-30241 checklist item, NATS 2.12–2.15 feature gates + the 2.15
  ack-subject ACL migration warning, PEP 734 subinterpreters + Python 3.14
  asyncio introspection, Go 1.25 testing/synctest, C++26 DIS status),
  **32 skipped** with recorded reasons (refuted, already covered by the
  verified-fix pass, or not worth the lines). The applied+skipped tallies
  exceed 75 because some findings split across multiple files. No version pins
  added; all invariants green.
- **Freshness sweep 2026-07-08** — 34-skill research pass (one web-research
  agent per skill; every high/medium finding independently
  adversarially verified against primary sources) fixed **7 high + 58 medium**
  confirmed gaps across 31 skills. Highlights: SurrealDB 3.1.5 security batch
  (databases/08); Argo CD repo-server unpatched gRPC RCE → require
  NetworkPolicy isolation (devsecops/06); ASP.NET Core Data Protection
  CVE-2026-40372 (dotnet/04); TorchServe archived → maintained serving
  runtimes (ml-engineering/05); Cilium mTLS guidance moved to the ztunnel
  integration (network-security/04); ingress-nginx EOL 2026-03-24 + migration
  guidance (network-security/05, kubernetes/01); jqwik 1.10.0 protestware
  advisory (testing/06); NIST SP 800-63B-4 15-char password floor
  (code-security/02); OCSP-stapling guidance retired after Let's Encrypt
  ended OCSP (code-security/04, network-security/06); ATT&CK v18/v19
  restructuring + BadSuccessor/dMSA detection (detection-engineering);
  JDK 24 ZGC/virtual-thread-pinning updates (jvm); K8s user-namespaces GA,
  Landlock ABI correction, 2025 runc CVE triple (sandboxing); TypeScript 7 GA,
  npm v12 script-blocking defaults, June-2026 supply-chain campaigns
  (javascript-typescript); Kyverno CVE-2026-4789 + CEL policy-type
  stabilization (devsecops/07, kubernetes/03); and more — see the PR for the
  full list.
- Genericity: removed three internal-abbreviation/reader-assumption phrasings
  that had slipped past the denylist; patterns added to the private denylist.

### Changed

- Contributor docs synced to this cycle's policy changes: AGENTS.md and
  CONTRIBUTING.md now state the **no-version-pins rule** (latest stable +
  semantic boundaries only, EOL→successor) as a standing convention and
  describe invariant 6's exact-count vs "N+"-floor split; RELEASING.md's
  pre-tag checklist matches the floor model; docs/ROADMAP.md logs
  `sota-confidential-computing` under coverage additions.
- **Version-claim policy applied library-wide**: rot-prone "current release is
  X.Y" claims replaced with "use the latest stable release — verify via a
  quick web search"; version numbers that mark semantic boundaries
  ("introduced/fixed/removed in vX", CVE fix versions, GA milestones) are
  kept. EOL/unmaintained tools are replaced by their maintained successors
  (project-recommended target first, then CNCF-maintained alternatives), with
  a one-line EOL note kept for auditors.
- **Freshness tracking model**: per-file line-1 `<!-- last-verified: YYYY-MM -->`
  markers retired (they duplicated git metadata and stayed 84% unstamped);
  replaced by a single root `LAST-VERIFIED` stamp recording the date of the
  last full-library verification sweep (initialized to 2026-07-08).
  `scripts/check-freshness.sh` rewritten for the new model (red when the
  stamp exceeds the 12-month window; warns on stray per-file markers);
  `freshness.yml`, AGENTS.md, CONTRIBUTING.md, and the README maintenance
  prompt updated accordingly.
- Router (`skills/sota/SKILL.md`): added cross-cutting routing rule 18,
  **"Cryptography fans out"** — a single lookup that maps a crypto task to its
  distributed owners (algorithm/AEAD/key-handling/TLS-client/PQC →
  `sota-code-security` rules/04; key material/storage/rotation →
  `sota-secrets-management`; TLS server/PKI/cert lifecycle →
  `sota-network-security` rules/06; FIPS-validated-module →
  `sota-security-compliance` rules/02). Documents the deliberate no-single-crypto-skill
  design; no content moved.

## [1.11.0] - 2026-07-06

### Added

- **`sota-web-frameworks`** — React 19 + Next.js and Vue 3 + Nuxt 4 engineering,
  plus the cross-cutting concerns of server rendering (40 skills total). SKILL.md
  + 7 rules files: 01 baseline (support/EOL matrix, render-mode selection, React
  Compiler), 02 React 19 (hooks, Suspense, the Actions model, `dangerouslySetInnerHTML`),
  03 Next.js (App Router, Server Actions as public endpoints, the caching model —
  `use cache`/Cache Components/PPR/ISR — `proxy.ts`, the Data Access Layer), 04 Vue 3
  (Composition API, reactivity pitfalls, `defineModel`, `v-html`), 05 Nuxt 4
  (`useFetch`/`useAsyncData`, `useState`, `runtimeConfig`, Nitro server routes,
  `routeRules`), 06 SSR & hydration (mismatches, state-serialization XSS,
  cross-request state pollution, cache safety, CSP with streaming SSR), and 07
  framework security (server/client secret boundary, authorization placement,
  SSRF surfaces, consolidated CVE reference). Every version and CVE claim
  web-verified against primary sources (react.dev, nextjs.org, vuejs.org, nuxt.com,
  GitHub Security Advisories) and stamped `last-verified: 2026-07`. Notable
  security coverage: the 2025-12 React Server Components RCE (CVE-2025-55182
  "React2Shell" / CVE-2025-66478), the middleware auth bypass (CVE-2025-29927),
  Next cache-poisoning and SSRF CVEs, and the Nuxt/Nitro/h3/IPX/devalue advisory
  waves. Router routing table + library map + cross-cutting rule 6 updated;
  count surfaces updated to 40 skills / 289 files / ~57k lines (README
  badge/hero/alt/table, plugin.json, marketplace.json, social-preview pill + PNG).

---

Releases **1.10.0 and earlier** are archived: 1.10.0–1.5.0 in
[docs/CHANGELOG-archive.md](docs/CHANGELOG-archive.md), 1.4.0 and earlier in
[docs/CHANGELOG-archive-2.md](docs/CHANGELOG-archive-2.md).

[1.22.9]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.22.9
[1.22.8]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.22.8
[1.22.7]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.22.7
[1.22.6]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.22.6
[1.22.5]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.22.5
[1.22.4]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.22.4
[1.22.3]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.22.3
[1.22.2]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.22.2
[1.22.1]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.22.1
[1.22.0]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.22.0
[1.21.1]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.21.1
[1.21.0]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.21.0
[1.20.1]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.20.1
[1.20.0]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.20.0
[1.19.9]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.19.9
[1.19.8]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.19.8
[1.19.7]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.19.7
[1.19.6]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.19.6
[1.19.5]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.19.5
[1.19.4]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.19.4
[1.19.3]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.19.3
[1.19.2]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.19.2
[1.19.1]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.19.1
[1.19.0]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.19.0
[1.18.0]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.18.0
[1.17.0]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.17.0
[1.16.0]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.16.0
[1.15.0]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.15.0
[1.14.1]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.14.1
[1.14.0]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.14.0
[1.13.0]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.13.0
[1.12.1]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.12.1
[1.12.0]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.12.0
[1.11.0]: https://github.com/martinholovsky/SOTA-skills/releases/tag/v1.11.0
