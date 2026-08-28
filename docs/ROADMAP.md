# Roadmap

Priorities set by the **2026-07-10 audit**
([AUDIT-2026-07-10.md](AUDIT-2026-07-10.md)). Ordered; revisit after each
release. The 2026-07-01 cycle is fully executed and kept below as history.

## Start here next session *(as of 2026-08-28)*

Everything actionable, ordered. Each line says what it is, why it is not done, and the
first move. **The written-conventions backlog is empty** — invariant 14 closed the last
gateable candidate — so nothing below comes from re-reading docs. That prediction has now
held three times: the v1.21.1 candidates came from incidents, the three additions of
2026-08-11 came from **reading an outside implementation's own failure notes**, and
`evals/smoke-runners.py` (2026-08-27) came from an incident too — a runner dead for three
weeks that no doc could have predicted.
Item 11 is the near-exception that shows the shape rather than breaking it: it *was*
found by re-reading docs, at the v1.22.14 cut — and it is **not gateable**, so it earns
a ledger row and a habit, not a check.

Numbers here are re-counted at each cut, never carried forward — the stamp above goes
stale within a day, which is the case for re-reading this at every cut rather than trusting
it. Last re-count 2026-08-28 — star/forks re-read live (**17/3**, unchanged from
2026-08-27), item 1's listing status, the open list below, and the deferred-row
pointer. Cap watch last re-counted 2026-08-27.

**Genuinely open right now: 1** (not a code task), **5** (scheduled ~2027-01-08), **12**
(conditional), **25** (the completeness half — the expensive one) and **26** (deliberately
unbuilt). Everything else is either closed or a recorded lesson whose "first move" is a
habit, not work — read those for the habit, not the backlog.

**This table is not the whole backlog.** Open work also sits in
[ADOPTION-LOG.md](ADOPTION-LOG.md) as rows marked **deferred** — an idea judged real but
held for a trigger, which the roadmap never learns about. One is live today (2026-08-11,
an integrity verdict left routinely red for operational reasons; revisit when a second
implementation shows the same design). Answering "what is open?" means
`grep -c '\*\*deferred' docs/ADOPTION-LOG.md` as well as reading this table — a list
assembled from one file reads as complete and is not.

| # | Item | Why not done | First move |
|---|---|---|---|
| 1 | **Distribution / adoption** — still the bottleneck, though less flat than it looked (**17 stars, 3 forks**, re-checked live via `gh api` on 2026-08-28 — up from 13/2 on 2026-08-19, flat since 2026-08-27) | Not a code task; needs a person, not a gate | **First external channel landed 2026-08-26**: the [awesome-ai-plugins](https://github.com/hashgraph-online/awesome-ai-plugins) listing PR (their #155) is **merged**, so the library is now catalogued somewhere other than this repo. Next: publish the salience write-up; a before/after audit demo |
| 2 | **Real-repo audit eval — CLOSED 2026-08-14.** Recall *and* precision both measured, both +0.00 | Recall 15/16 = 15/16; precision **1.00 = 1.00** over 59 blinded findings, adjudicator controlled at 4/4; severity mix indistinguishable. Nine instruments, zero lifts | Nothing. Do **not** build a tenth audit-recall or audit-precision instrument. If the audit claim is ever revisited, it needs a different *dependent variable* (time-to-find, report usability, or defects found by a non-expert), not another accuracy metric |
| 3 | **Competitor comparison — content-only re-run DONE 2026-08-14/15, claim holds. As-deployed REJECTED 2026-08-16** | Re-run at the pinned SHAs with the same build model: SOTA 98.7 / ECC 84.9 / cursorrules 80.0 / claude-skills 77.0 / unguided 58.2, 17 wins / 4 ties / 0 losses of 21, unguided arm reproducing to 0.2 points as the drift control. **As-deployed is rejected, not deferred:** it measures corpus size and a retrieval path we have already found saturated, not guidance quality — reasoning below the table | Nothing. Do not re-open without a new argument that answers the corpus-size confound |
| 4 | **Router trim — RESOLVED 2026-08-26 by offloading, not trimming. And the "2×" was wrong: it is 3.3×** | The cap was never protecting routing quality — **measured**: recall stayed **flat at 1.000** with the router padded to 902 and 1,302 lines and the routing table pushed 800 lines deeper, while the untreated arm reproduced 0.867 exactly ([ROUTER-LENGTH](../evals/results/2026-08-26/ROUTER-LENGTH.md)). What *is* real is per-load cost: `count_tokens` gives **16,442 tokens** at 484 lines, **3.3×** the ~5k guidance — this table said ~10,211 (2×) from a chars/4 heuristic that under-read it by ~60% | **Nothing on the cap.** BUILD/AUDIT detail now lives in `skills/sota/rules/` and loads on demand (PR #284): 500 → 484 lines, ending compress-on-every-addition. Be honest about the size of that win — the token saving is 16,934 → 16,442, **~3%**; the win was **headroom**, not context economy. Next addition goes to `rules/`, not the router. Two caveats on the sweep, published with it: the metric is **at ceiling** (it can only detect a drop) and the filler is **inert**, so it tested length/depth and *not* competition between real rules |
| 5 | **6-month accuracy sweep** | Scheduled | `LAST-VERIFIED` reads **2026-07-08**, so due ~**2027-01-08**; bump it only after a full pass |
| 6 | **CLOSED 2026-08-21 — both deferred ideas landed** | (a) Event-sourcing replay preconditions → `sota-architecture/rules/03` §6: the `apply` step must be a pure function of (state, event); capture non-deterministic answers *in the event*; gate outbound effects during replay; and the **event log**, not commands, carries the durability budget. (b) Geospatial → `sota-databases/rules/03`, a *Geospatial* section on the three ways the index is lost. Both got audit checklist items **in the same change**, which is the point of item 16 | **Nothing.** Two honesty notes kept in the log: (a) Fowler's *Event Sourcing* supports the external-query mechanism but never says *deterministic*, so the rule is written from the mechanism with the citation scoped to what it covers; (b) geospatial was adopted **on instruction, not because its revisit condition fired** — that condition is still unmet |
| 7 | **`sota-rust` subprocess coverage — CLOSED 2026-08-19.** The gap was real (zero hits, three independent greps) and is now `sota-rust/rules/05` §9, seven rules with four audit probes | Every claim measured on rustc 1.97.1 / tokio 1.53 rather than carried over from Go or Python — which mattered: **three languages behaved three different ways** under the same pipe-holding-grandchild test. Go's `Wait` blocks past cancellation without `WaitDelay`; Python's raises on schedule; **Rust/tokio's `timeout` fires on schedule but leaves the child running**, because cancelling a future is not killing a process | Nothing. Two corrections rippled out: `sota-sandboxing/rules/04` R5.1 claimed "beware `.arg` vs `.args` splitting" and **neither splits** (measured), and R5.3a's per-language pointer list now includes Rust |
| 8 | **Per-language subprocess rows — CLOSED 2026-08-20. All five runtimes now measured.** Java was the last unmeasured row; run on Temurin **25.0.3** in a podman container, since no JDK is installed on this machine | `ProcessBuilder` confirmed (no whitespace splitting, no shell). Three things the row did **not** say: `Runtime.getRuntime().exec(String)` **tokenizes on whitespace** and is `@Deprecated(since="18")` on all three `String` overloads while the `String[]` ones are not (read off `Runtime.class` by reflection, not from docs); `waitFor(t, unit)` fires on schedule and **returns `false`**, so the caller *is* told, unlike Node; and `destroy()` orphans the grandchild while **`Process.descendants()` + `destroyForcibly()` kills it** — Java is the only one of the five with a portable process-tree kill. Also corrected a claim the new row exposed: the table said "no two agree on all three questions", which was **already overstated** — Python and Rust answer all three identically | **Nothing.** The probe's first run was *wrong* (its liveness check matched an orphan left by the previous phase and reported the tree-kill as failing); re-run with per-phase markers and a control that demonstrably reads both true and false. Any sixth runtime gets the same treatment |
| 9 | **Pre-push stage — DONE 2026-08-19.** The repo now practises what it prescribes | The narrow case held up: invariants **11 and 14 are diff-based** and at pre-commit time the change is only *staged*, so they have nothing to read and pass by skipping. Pre-push is the first local moment a commit exists | Nothing. `default_install_hook_types: [pre-commit, pre-push]` makes a plain `pre-commit install` create both hooks; every hook now states its `stages` **explicitly**, because a hook with no `stages:` key runs at *every* configured stage (measured) — which is exactly the doubling this item warned about. `verify-setup.sh` check 9a now reports PASS on this repo |
| 10 | **Two suggestions from the 2026-08-18 brief were declined, on purpose** | Recorded so they are not re-litigated | **(a)** Moving BUILD step 4's gate advice earlier: its last position is where the measured completeness lift is attributed, and the router is now **full at 500/500**, so it would displace a line rather than reflow. Revisit only with a measurement. **(b)** The hook-versus-typed-instruction note: **done** as documentation (README, always-on routing), stated as mechanism rather than as a measured effect |
| 11 | **Invariant 17 sees counts, not meaning — first instance found 2026-08-19 at the v1.22.14 cut** | `AGENTS.md`'s invariant 14 row read "a declared term resolves in **neither** `README.md`/`docs/INDEX.md` **nor** the release's own entry" — an OR across all three — while `scripts/check-invariants.sh:842` requires (README **or** INDEX) and `:848` requires the release's own entry, an AND. `CONTRIBUTING.md` item 14 was already correct, so two documents describing one gate disagreed **in logic while agreeing in count**, which is exactly what invariant 17 cannot see: it asserts every stated count equals N and that `AGENTS.md`/`CONTRIBUTING.md` enumerate 1..N with no gaps, nothing more (read at `check-invariants.sh:1027`+) | **Nothing to build.** Applying the three filters ([CONVENTIONS-LEDGER](CONVENTIONS-LEDGER.md)): incident **yes** (once), silent **yes**, mechanically checkable **no** — comparing the semantics of two prose restatements written at deliberately different granularities is the judgement class the ledger argues against gating. The remedy is the habit that caught it: re-read the prose *beside the script* at each cut. Recorded so it is not re-litigated as a gate proposal |
| 12 | **A skill-level split of `sota-code-security` (vulnerability classes vs control verification) — considered 2026-08-20, NOT done** | The operator proposed splitting the skill, first on a build/audit axis. **Build/audit is the wrong axis for this library**: invariant 2 requires every one of the 259 `rules/*.md` to end with `## Audit checklist`, so the audit half is welded to the build half by a gate, and an audit-only injection file would need the build half's facts to be usable. The defensible seam is **rules/01–09 (vulnerability classes) vs 10–14 (control verification)**, now 5 files and ~1,500 lines. Not done because it does not solve the cap (invariant 1 is **per file** — `git ls-files 'skills/*/*.md' 'skills/*/rules/*.md'`, so a split skill carries the same files at the same sizes) and it costs router lines: `skills/sota/SKILL.md` is at **500/500 — full**, and a new skill needs a routing-table row, a library-map entry and probably a cross-cutting rule | **Only if `sota-code-security` grows a sixth verification file**, and then trim the router in the same change (item 4). Recorded so the build/audit framing is not re-proposed |
| 13 | **Cap watch — re-measured 2026-08-27** | `sota-docs-workflow/rules/01` **477**, `sota-code-security/rules/12` **476**, `sota/rules/01` **455**, `sota-devsecops/rules/03` **451**. The router is **498/500** (it was full for four weeks until BUILD/AUDIT detail moved to `skills/sota/rules/` on 2026-08-26). `sota-docs-workflow/rules/01` gained §11 today and is the tightest rules file | **Split reactively at a seam the file already has, not preemptively.** A file near the cap is only a problem when the next addition has nowhere to go; `sota-code-security/rules/10` absorbed two findings today and is still comfortable. When a split happens, build the gate first (item 16's lesson) — invariant 18 exists because a renumber breaks `§` references silently |
| 14 | **DONE 2026-08-20 — the repo now practises `sota-code-security` rules/12 §1b.** `./scripts/check-invariants.sh --self-test` | Structural pass (~1 s): every check must be either probed by `check-negative-controls.sh` or listed in that script's own *NOT COVERED* block. Both sets are **derived from the harness**, not restated, so there is no second list to drift. It then execs the harness. Watched to fail on two mutations — a deleted `probe 13` ("check 13 has no known-bad") and a probe added for the declared-unprobeable check 5 ("both probed and declared unprobeable") — with the clean tree passing at `18 checks: 13 probed, 5 declared unprobeable, 0 unaccounted` | **Nothing.** Two design choices to keep: the probe **count** stays ungated (a static count of call sites under-reads, 13 vs an actual 24), and mutations keep asserting they landed |
| 15 | **BUILD↔AUDIT correspondence — measured 2026-08-21, ~4% and NOT gated** | Four attempts: `§`-anchors (1% of items cite one — measured a convention that does not exist), lexical overlap (defeated by synonymy and cross-file grounding), a shell sampler (mangled its own alternation), and finally **read a sample**. n=20 said 10%; n=60 said ~2%; pooled n=80 gives **~4% confirmed**. Recorded as a **floor with a soft ceiling** — 18 of 60 read in full, the rest screened, and the screen errs both ways | **Do not re-attempt a mechanical version** — the ledger records why. If the number is ever wanted tighter, the method is reading, not scripting: ~40 more sections. The *actionable* output was never the percentage (see item 16) |
| 16 | **Gaps cluster by FILE, and a fan-out is the mechanism** | Ranking files by weak-coverage density beat sampling sections: two `rules/02-design-api.md` files topped it, and reading the first found the cause — the in-band-sentinel row added to **nine** language skills on 2026-08-20 shipped with an audit item in **two**. Seven fixed 2026-08-21 | **When a change fans out across N skills, treat it as N chances to ship the build half alone** and check the audit half per skill before opening the PR. The author is the last person who will notice. No gate: the correspondence is semantic (item 15) |
| 17 | **Every headline claim is dated to a model. One expired; completeness did NOT** | Completeness (+0.39), freshness (+0.53) and routing (+0.10) were all measured on `claude-sonnet-4.6` or `gpt-5.1`. On 2026-08-21 defect-avoidance was re-run on `claude-sonnet-5` and went to **+0.000** — the newer model does not write those defects unaided, and its *unguided* strict score equals `sonnet-4.6`'s **with-library** score. Model progress absorbed the result in four months | **Completeness DONE 2026-08-21 — it holds**: 0.62 → 1.00, **+0.38** on `claude-sonnet-5`, unchanged within the ±0.03 noise floor, zero truncation warnings ([write-up](../evals/results/2026-08-21/COMPLETENESS-SONNET-5.md)). The mechanism is now understood: knowledge gaps close with model progress, **salience gaps do not** — `sonnet-5` unguided still omits tests in **7 of 7** tasks. **Freshness and routing CLOSED 2026-08-25** (item 20): routing holds at **+0.13**, freshness **erodes to +0.30** — and the "freshness is likely durable, models still have cutoffs" prediction stated here was **refuted**, because a cutoff *advances* into a fixed set. Three shapes, not two: expired / durable / **eroding**. Budget the runs: `sonnet-5` produced 40–122k tokens per build in the 2026-08-21 work, so it is materially more expensive than the models these numbers were established on |
| 18 | **`temp 0` is not deterministic — the harness noise floor is ≈±0.03 at n=1** | Established 2026-08-21 by the *untreated* arm: it cannot see the router, and it still moved 0.60 → 0.57 between two otherwise identical runs. Any single-sample delta below ≈0.05 is unresolvable | **Read the untreated arm before interpreting the treated one** — an arm that cannot see the treatment is a free negative control for the measurement itself. Recorded in `evals/README.md`. Retroactive consequence: past n=1 comparisons with deltas under ≈0.03 were never meaningful |
| 19 | **A pushed branch with no PR reads as finished work — and nothing reports it** | 2026-08-21: the sonnet-5 completeness branch was committed, pushed, written up and reported as landed. No PR existed. Every gate in this repo runs *on* a PR, so a branch that never opens one is not merely unmerged — it is **unchecked**, while looking done from the session transcript. It sat a day, found only by re-reading state at the next cut rather than by any signal | **Verify at the remote, not from your own summary** — the same rule `sota-kubernetes/rules/04` §7 states for write-back controllers, arriving in our own workflow. `gh pr list` before believing a branch landed; a push is not a landing. Not gated: the gates live on the PR that is missing, which is precisely why nothing caught it |
| 20 | **Freshness and routing on a current flagship — CLOSED 2026-08-25. Both re-measured; one prediction refuted** | `claude-sonnet-5`, same 3×/temp-0.7 protocol as the originals. **Routing holds: 0.87 → 0.99, +0.13** — unchanged within the set's one-case resolution (20 cases, 0.05/case) and, unlike its two neighbouring instruments, **not saturated**; the unguided arm still misses the same rule-driven routes (testing, sandboxing, code-security, web-frameworks) a generation later. **Freshness erodes: 0.44 → 0.69 unguided, lift +0.53 → +0.30.** The pre-registered prediction that a training cutoff is a gap model progress cannot close is **REFUTED** — 8 of the 32 facts moved inside `sonnet-5`'s window. The with-arm *rose* (0.97 → 0.99), so this is the **set ageing, not the library** | **Nothing on the measurement.** It produced a third claim-shape the knowledge/salience dichotomy missed — *knowledge gap, renewable*: erodes toward a floor rather than expiring. Predictions were committed at `91ca8d9` before the first API call; cost ~$0.77 against a ~$0.77 estimate. Write-up [ITEM-20](../evals/results/2026-08-25/ITEM-20-FRESHNESS-ROUTING.md) |
| 21 | **The freshness set was fixed and ageing — CLOSED 2026-08-25, same day it was opened. Re-authoring restores the lift** | A 10-case set built from facts whose primary source changed Sept 2025 – Aug 2026 reads **0.33 → 1.00, +0.67** on `claude-sonnet-5` — *higher* than the original +0.53, and measured on the same model the same day as the aged set's +0.30. The guidance did not improve between two runs an hour apart; the questions got newer. The with-arm is a **zero-variance 1.00**, independently corroborating the authoring-time verification of all ten facts against primary sources | **Quote a freshness lift with the date its questions were written**, the way every other number is quoted with its model. The old 32-case set is kept unedited as the continuity series; `freshness-2026.jsonl` is the live one. Its **selection rule** — recency + the library states the fact, never model performance — is in the file header, because picking the cases a model fails would guarantee a big number and measure nothing. Two of the ten questions telegraph each other (TypeScript 6.0/7.0) and inflate the *without* arm, i.e. against the reported result; worth splitting next revision. Write-up [ITEM-21](../evals/results/2026-08-25/ITEM-21-REFRESHED-FRESHNESS.md) |
| 22 | **Dependabot — CLOSED 2026-08-27. It fires, and its PRs can now pass CI** | PR #281 (`actions/checkout` 7.0.0 → 7.0.1) landed minutes after the config, with the SHA matching the real tag and the `# vX.Y.Z` comment rewritten — so the automation and the pin convention are both **proven**, which is what leaving the pin un-bumped bought. It then exposed a real gap: Dependabot branches are same-repo, so the *Require denylist secret* step ran, while Dependabot's token is denied repository secrets | **Fixed the right way** — `SOTA_DENYLIST` added to the **Dependabot** secret store (a separate store from repository secrets; it was empty), *not* by exempting `dependabot[bot]`, which would have re-introduced the silent degradation the step exists to catch. Verified by re-running the PR: invariant 3 passes with the secret injected. Two follow-on facts recorded in `CONTRIBUTING.md`: the value is the **pipe-joined ERE**, and a Dependabot PR opened before a release also trips invariant 5 (`tag ahead of VERSION`) until `gh pr update-branch`. **Dependabot maintains the trailing `# vX.Y.Z` comment but not prose comments** — one went stale for a commit, now fixed by not naming a version there |
| 23 | **Case-set selection rules — CLOSED 2026-08-27. 20/20** | Every `evals/cases/*.jsonl` now states **how its cases were chosen** and whether it is a **measurement** set (a lift may be reported, so cases must never be picked by a model's score) or a **regression** set (selection-by-outcome is the point). Verified by re-count, not memory: 20 of 20, none missing | **Nothing.** Two defects surfaced doing it — `silent-failure.jsonl`'s header still described the **retracted 15-case version** while the file held **81**, and `freshness.yml` carried the stale `actions/checkout v7.0.0` comment the `ci.yml` fix had missed. Both fixed. The rule this practises is `sota-llm-engineering` rules/01 §8 |
| 24 | **Freshness re-authoring cadence — CLOSED 2026-08-27, mechanically** | `scripts/check-freshness.sh` reads an explicit `# AUTHORED:` marker (git dates move under rebase) and **warns** when the newest freshness set is older than the window. **Watched both ways**: warns at 19 months, and **fails closed (exit 1)** when no marker exists | **Nothing.** The 6-month window is **borrowed** from `LAST-VERIFIED`, not derived from decay data — one before/after pair is not a decay rate, and guessing one would be inventing a number. It warns rather than fails because an ageing set still measures a real floor |
| 25 | **Real rules vs inert filler — the ROUTING half answered 2026-08-27 (null); the COMPLETENESS half is still open** | Padding rebuilt from genuine rules prose with every routing signal stripped (asserted: no `sota-` survives) scored **0.992 vs base 1.000 — identical to inert filler's 0.992**, both far inside the 0.05 one-case resolution. So 400 lines of real competing guidance is indistinguishable from filler on routing ([follow-up](../evals/results/2026-08-26/ROUTER-LENGTH.md)) | **Do not read that as permission to grow the router.** Routing is retrieval-ish, the table is in the prompt, and the metric is at ceiling — it can only show a drop. The question that matters is **rule application** under a long build, i.e. the completeness axis, and that is untouched. Cost is the reason it is still open: completeness is ~14 builds at 40–122k tokens each, and its treatment arm changed 2026-08-26 so it needs re-baselining first |
| 26 | **`§AUDIT` has no drift guard, unlike `§BUILD`** | `ROUTER_BUILD_SHA` pins the router's BUILD section and **aborts the eval** when it moves — that guard caught two edits on 2026-08-26 alone. AUDIT has no equivalent: its procedure lives in `sota/rules/01`, and the router's seven passes can contradict it silently. `rules/01` §10 states the coupling, but a stated rule is not a gate | **Not built, deliberately** — a pin only works where something *reads* the pinned text, and no eval consumes §AUDIT the way `run-completeness.py` consumes §BUILD. A gate with nothing behind it is decoration (`rules/12`). Revisit if an audit eval ever pastes §AUDIT |
| 28 | **A runner can be dead for weeks and nothing reports it — gated 2026-08-27, for two distinct failures** | `run-desc-routing.py` raised before its first API call for three weeks. `evals/smoke-runners.py` now runs in CI and was **watched to fail** on a reintroduction of that bug. It also asserts every runner keeps side effects behind `__main__`, and that every `.env` read is **existence-checked** (that one shipped twice and is unreachable locally — a maintainer's tree has a `.env`; the assertion itself was **vacuous on first draft** and only watching it fail caught that): **the smoke check cannot catch a module-level script itself**, because importing one runs it and that reads as "reached the network" — which is exactly how `run-router-length.py` passed while executing its sweep on import. Two runners were in that state | **Know the ceiling.** It proves a runner can *start* and is import-safe; it does **not** prove the numbers are right — the per-runner selftests and `check-negative-controls.sh` do that. Three runners are still doing local work at the alarm and count as "alive", which is honest but weaker than reaching the network |
| 27 | **Estimated token counts — CLOSED 2026-08-27. Swept, and the docs were worse than expected** | All 301 skill files measured with `count_tokens`. `docs/CONTEXT-MANAGEMENT.md` claimed *"12 of 297 files exceed ~5,000 tokens"* — the real figure is **132 of 301, an 11× under-count** — and *"exactly one file breaches the recommendation"* is **5 of 41** `SKILL.md` bodies. Both were chars/4-derived, the same heuristic that under-read the router by 60% | **Nothing outstanding.** Corrected in place with the measurements and a note saying why. Standing rule, now in `sota-llm-engineering` rules/02: **if a size claim was not produced by a tokenizer, assume it is wrong by half.** Density across the tree runs ~24–46 tokens/line, so two files of equal length differ ~2× in cost — which is the argument the line cap cannot make |
**Why the as-deployed competitor comparison is rejected (2026-08-16), not deferred.**
Checked against the pinned clones rather than from memory: **ECC ships 889 `SKILL.md`
files with a `.claude-plugin/marketplace.json`, claude-skills ships 777 with
`.claude-plugin/` and `.codex-plugin/`** — so two of the three competitors deploy through
*exactly our own mechanism*, and only awesome-cursorrules differs (257 `.mdc` +
199 `.cursorrules`, glob-loaded). "As deployed" is therefore not three mechanisms; it is
our mechanism over a corpus 20× ours (41 vs 889).

That makes the measurement land on two things we do not want to publish as a claim about
a named third party:

- **Corpus size, not guidance quality.** A larger library is likelier to *have* a
  matching skill and likelier to surface a distractor. Either way the number partly
  measures how big someone else's repo is.
- **A retrieval path we have already measured as saturated.** `run-desc-routing.py` A/Bs
  the description-selection layer and reads **+0.00** ([RESULTS](../evals/results/RESULTS.md) §5).
  Testing competitors through a layer that does not discriminate for *us* cannot produce
  an honest comparative result.

Two further blockers with no neutral resolution: simulating a loader none of them ships
means our simulation choices decide the outcome, while driving real sessions per plugin is
non-deterministic and hard to blind; and a retrieval **miss** (the loader surfaces nothing
relevant) would score as a content zero, which is a real deployment outcome but reads as
rigged when published under our name.

The content-only benchmark stays the claim, and it is deliberately conservative — it turns
*off* SOTA's self-audit forcing function, so a win there is the guidance, not the method.
Its known weakness is that the maintainer hand-picks 4–8 files per competitor; that is
disclosed in [COMPETITOR-BENCHMARK](../evals/results/2026-07-13/COMPETITOR-BENCHMARK.md)
and is a better-understood limitation than the confounds above.

**Release cadence, for reference.** That test (`RELEASING.md` §"Minor or patch?" —
minor = the library gains a surface someone can *use*; patch = the change lives inside
existing surfaces) has produced a run of patches: 1.22.4 through **1.22.9**, none of them
adding a skill, script, or gate. Invariant 14 requires each one to carry a
`**Front door checked:**` line whose terms resolve, and at the 1.22.9 cut it did its job —
the release's own capability (double-entry ledgers, reconciliation) read **zero** in
`README.md` until the cut added the sentence.

**This cycle (PRs #240-242, 2026-08-19) — a brief, a question, and two of my own
errors.** A second field brief plus one operator question about `update.sh`. Carry
forward:

1. **The gate hole came from a *question about a script*, not from reading a rule.**
   "Are pre-commits updated by update.sh?" surfaced that `pre-commit` writes
   `.git/hooks/<type>` only at install time, so a release adding a `pre-push` stage
   reaches every user's config and nobody's hooks — and `verify-setup.sh` check 9
   could not see it, because it counts hook *files* and the pre-commit one is present.
   Now check 9a, with a probe (harness 21 → **22**, still 22/22). The library's
   own gate-scope rule (`devsecops/rules/05` §5.6) predicted this shape a day earlier.
2. **The first cut of check 9a aborted its own script and exited 0.** Under
   `set -euo pipefail` a grep matching nothing takes the whole run with it, so the
   report truncated after check 9 and returned success. Caught by *running* it. If you
   add a check to `verify-setup.sh`, run it against a repo where the new branch matches
   nothing before you trust a green.
3. **Two derived numbers of mine were wrong on first write** — a comparison-table cell
   filled in by symmetry rather than by a command, and a ratio range that contradicted
   the series printed beneath it. Both were caught by re-reading the rendered diff, not
   by any gate, and neither is machine-checkable. Budget a reader's pass over the diff.

**This cycle (PR #236, 2026-08-18) — a session transcript, five for five.** A session
that *applied* the library to Go subprocess sandboxing handed back five proposals; all
five landed, **three of them with a correction**, which is the field-brief pattern
holding at a larger sample (see [ADOPTION-LOG](ADOPTION-LOG.md) 2026-08-18). Three
things worth carrying forward:

1. **The library's own rules had a direction.** `rules/12`'s mutation probe installs the
   *permissive* no-op, `sota-testing` rules/09 §1 says the assertion is refusal "not that
   the happy path works", and `sota-sandboxing` rules/01's probe list was **entirely**
   denial arms. Three independent sites all pointed one way, so a control that blocks
   *everything* passed all of them. When a class is missing, check whether the existing
   rules are asymmetric rather than absent — that shape is invisible to a coverage grep,
   because the rule *is* there.
2. **Both of the transcript's self-reported misses were already ours**, the zsh one
   **twice** (routing rule 17 and `rules/12` §2). A third statement was deliberately not
   written: that is the effect measured in
   [WHY-COMPLETENESS-RESIDUAL](WHY-COMPLETENESS-RESIDUAL.md), where adding the missing
   rule made adherence *worse*. The fix taken was **placement** — a cross-reference at
   the paragraph where the exec call gets written, not another statement of the rule.
3. **Reviewing the rendered diff caught two defects the invariants could not.** A
   comparison table in `rules/12` contained a cell filled in by symmetry rather than by a
   run (a 400 MiB deny arm at a 512 MiB `RLIMIT_DATA` cap — which would have *succeeded*),
   and an "orders of magnitude" claim that the table beneath it contradicted. Both were
   mine, both survived authoring, and neither is machine-checkable. Read the diff as a
   reader, not as the author.

**Closed 2026-08-16 — the instrument audit (PRs #223, #224, #225).** Prediction
[pre-registered and committed before any finding](../evals/results/2026-08-16/PRE-REGISTRATION-INSTRUMENT-AUDIT.md);
it held — **highest severity in `scripts/`, zero findings in `skills/`**. Closed: a
**Critical** data-loss bug in `install.sh` (an altered END marker deleted every user line
below the managed block), invariants 4 and 8 printing `ok` over an empty scope, CI's shell
lint unable to see SC2086, `principle5()` silently emptying the flagship's treatment arm,
`judge-live-build` averaging over survivors, a judge parser that scored 0.00 on a
wrong-shaped reply, unpinned competitor clones, and a negative-control harness that
misreported its own coverage. Probe coverage **6/16 → 11/16** (21/21 mutations caught).

**Still open from that audit, deliberately:** probes for invariants 5, 9, 11, 12, 14 —
each needs state a disposable worktree lacks (a tag, a merge base, an mtime), so they need
a fixture, not another probe. And `run-unscoped-audit`'s scoring was tightened *after* its
+0.00 was published: the number would need a re-run to be strictly comparable (both arms
were at ceiling, so any change lowers both).

**Closed 2026-08-13, both with evidence rather than a tick:**

- **Every eval runner declares its denominator — 12 of 12.** The five that did not
  (`run-adjudication`, `run-competitors`, `run-decay`, `run-desc-routing`,
  `run-silent-open`) now call `note_work` at the point the count is known.
  `run-decay` gets `arm-depth runs`, not `cases`: it drives **one** case across every
  arm × depth, so "cases" would have declared a denominator of 1 for a run that does
  15 units of work — a wrong denominator is worse than none. Verified by executing the
  import from a script in `evals/`, not by reading it, and `test_scoring.py` still
  passes 38 checks.
- **§3.9 tool-table rot: re-checked, none found.** All six named third-party projects
  resolve, none archived, all pushed within four months (`knip` 2026-08-11, `deptry`
  2026-08-12, `cargo-machete` 2026-08-10, `cargo-udeps` 2026-04-29, `composer-unused`
  2026-04-27, `ReferenceTrimmer` 2026-08-12). The rename the file warns about is
  confirmed live — `fpgmaas/deptry` still answers and reports `full_name:
  osprey-oss/deptry` — and the rules file already carries the new name. Checked by
  reading `full_name` back, per the ledger's own lesson that the API follows renames
  silently.

**Closed since the 2026-08-05 cut** (2026-08-11/13, PRs #204, #205, #207):

- **Three rules adopted from an outside implementation's own incident notes** — chained
  partitions and two-directional canonicalization in `sota-code-security/rules/04` §8, a
  fourth guard form in `rules/12` §3, and "a replay harness is not an eval" in
  `sota-llm-engineering/rules/01` §5. Six further findings were checked and **rejected as
  already ours**, which is the signal that made the three worth taking.
- **A leak the leak-check could not see** — a project name sat in two tracked docs for a
  month behind a green invariant 3, because the private list had no pattern for it. Green
  meant "no match", not "clean": `rules/12` §3 in our own machinery. Redacted, both lanes
  extended, and the CI secret **proven live** by a synthetic canary rather than by a real
  name (which would have published to a public log the very thing the control suppresses).
  The two-lane rule and the canary procedure are now in `CONTRIBUTING.md`.

**Closed in the v1.22.x cycle (2026-08-05)** — kept here rather than in the table above,
which is for what is still *actionable*. Numbering is deliberately dropped: these five were
items 8 and 9 across three separate cuts, and re-using the numbers made the table unreadable.

- **Gate the router's library map against `rules/*` files** — shipped as **invariant 15**
  (v1.22.0). Both directions; watched to fail on the real defect (drop `11` from the map)
  and on its inverse before being trusted.
- **A negative control for our own CI** — shipped as `scripts/check-negative-controls.sh`
  (v1.22.0), its own CI job. Injects a known-bad per invariant and requires *the intended
  check* to complain; any other failure is a FALSE PASS.
- **`verify-setup.sh` had 14 checks and no negative control** — closed by part B (v1.22.1):
  a fully-configured fake machine (`CLAUDE_CONFIG_DIR` + throwaway repo + stub `gh`), 10
  probes. Watched to fail: making check 6a always-pass makes the probe report NOT CAUGHT.
- **Gate README's documented hook against `install.sh`'s `HOOK_CMD`** — shipped as
  **invariant 16** (v1.22.2). Parses the fenced JSON rather than regexing the string.
  Watched to fail four ways, including both fail-closed cases.
- **Two CI jobs ran but could not block** — fixed (v1.22.3): all four jobs are now required
  checks. Watched to *block*: a PR with only `Negative controls` failing went
  **UNSTABLE → BLOCKED** across the change, and a real merge attempt was refused.

**Explicit do-nots** (each has a recorded reason — do not re-litigate): another
audit-recall instrument · a synthetic large-repo fixture · rebuilding the BUILD-safe
instrument · relocating the remaining ~18 judgment conventions · running the
`reimplement` set · splitting long `rules/*.md` **for navigability** · adding a TOC to
rules files · a SessionStart version check that phones home · `gh-sota`.

**One do-not needed narrowing (2026-08-05).** "Splitting long `rules/*.md`" was
recorded against the *TOC/navigability* question — agents read files whole, so
splitting buys no retrieval benefit. It never covered the **500-line invariant**, which
is a hard cap and a different reason entirely; v1.21.1 split the inert-control family
into `rules/10`/`11`/`12` when the first two reached 493 and 495. Splitting for the cap
is fine; splitting to help a reader navigate is still not.

## The v1.22.0 cycle — closed *(written 2026-08-05, kept for the mechanism)*

**The v1.22.0 cycle — activation, and gates that prove they can fail.** Two threads
closed and one opened:

1. **Activation is defense 0, and it was broken.** A real ~25-turn session invoked
   **zero** `sota-*` skills; the router body was never read, so its content was
   irrelevant. Only the frontmatter `description` auto-loads, which makes it the whole
   trigger classifier. The old verbs assumed you own the codebase; non-owned-code
   triggers (PR review, diff, upstream contribution) are now in, paid for by cutting the
   31-domain enumeration. Full mechanism and the three causes:
   [CONTEXT-MANAGEMENT § the precondition](CONTEXT-MANAGEMENT.md).
2. **Structure beat repetition, which is the transferable finding.** The re-injected
   hook had two numbered rules and one subordinate clause. The numbered rules were
   obeyed every turn; the clause was dropped every turn. Same text, same repetition.
   Defense 5 works on *grammatical form*, not on presence.
3. **Both v1.21.1 gate candidates shipped** — invariant 15 (router library map vs rules
   files) and `check-negative-controls.sh`. The harness found a defect in *itself* on
   its first run, which is the argument for its FALSE-PASS assertion.
4. **Still unmeasured, and must stay labelled so.** Nothing in v1.22.0 has an efficacy
   number. `desc-routing` reads +0.00 (saturated) and cannot distinguish two
   descriptions; the AUDIT arm remains +0.00 across seven instruments.

**The previous cycle (v1.21.1, 2026-08-04/05).** An external inert-control audit
spec (seven classes) and two commissioned research reports were taken in; the
inert-control family became three files. What a next session should carry forward:

1. **The recurring gap shape is "the rule without the probe."** Three of four gaps in
   the first intake, and three of four in the second, were cases where the library
   *stated the BUILD rule* and never wrote the **AUDIT probe** — "unit tests touch no
   sockets" appeared in three places with no way to find out that they do. When
   evaluating a proposal, grep the rule first (it is usually there, often more than
   once), then ask separately whether anything says how to *detect the violation*.
2. **Research reports land ~4 of 13, and their citations are the liability.** One
   report misquoted NIST SSDF PO.3.3 by folding a footnote into the clause, and
   over-generalised a formal-verification statistic from hardware to software. Extract
   the primary document and grep it yourself; read abstracts, never search summaries
   (one rendered EvoMap's "84% of approved **assets**" as "84% of **agents**").
   Where a source is paywalled (IEC 61508 clauses) or unreachable (EUR-Lex returned
   only recitals for the CRA annexes), name the *concept* and say in the file that the
   clause number is unverified. Full detail: [ADOPTION-LOG](ADOPTION-LOG.md) 2026-08-05.
3. **Two gate candidates arrived from incidents** — now #8 and #9 above. Both were
   found by *doing the work*, which is what the ledger predicted would happen once the
   written-conventions backlog emptied.
4. **Still unmeasured, and must stay labelled so.** Nothing in v1.21.1 has an efficacy
   number. The AUDIT arm remains at +0.00 across seven instruments; none of this
   changes that, and none of it may be cited as if it did.

**The previous cycle's research (2026-08-02/03).** Four questions were answered
with evidence rather than reasoning, and three of the four answers were *"don't do the
thing"*:

1. **Do long rules files need a table of contents?** No — planted-canary test across 4
   arms including a positive control and a 1,719-line stress file; every arm retrieved
   it, agents read files whole. 242-file sweep cancelled.
   ([CONTEXT-MANAGEMENT](CONTEXT-MANAGEMENT.md))
2. **What size limits actually govern this library?** Verified against three official
   sources; one decision table now settles it. Hard limits are frontmatter only; the
   500-line cap is a *loose proxy* for a ~5k-token recommendation (density varies 3.3×).
   ([CONTEXT-MANAGEMENT](CONTEXT-MANAGEMENT.md) → *Size limits*)
3. **Can a synthetic large-repo fixture test audit skill?** No, demonstrated twice —
   a planted defect is by construction a deviation from filler, found mechanically.
   ([BIG-REPO-AUDIT](../evals/results/2026-08-03/BIG-REPO-AUDIT.md))
4. **Can §2b's front-door check be gated?** Yes — not by gating *discovery* (judgement)
   but by gating the *declaration*, invariant 11's pattern. Shipped as invariant 14.

**Latest cycle (2026-08-02/03, PRs #174–#188).** Two invariants and a diagram, from a
**fifth** discovery mode: *writing marketing copy about the repo forced a look at a
surface nobody reads from inside it.* Drafting a LinkedIn post about what shipped
since v1.0.0 led to the how-it-works diagram, and the diagram turned out to be
**stale against its own source** — #173 had fixed the line-cap wording in
`assets/how-it-works.html` and never re-rendered `how-it-works.png`, so `main` served
the old claim all day while the diff, the commit message and the CHANGELOG all read
as done. Landed: the render + a diagram that finally shows the *loop* the README
argues for (#174), **invariant 12** — a rendered asset is never older than its source
(#175), and **invariant 13** — every scoreboard row declares its sample size (#176),
which closes the ledger's last actionable candidate.

The generalisable finding is in [CONVENTIONS-LEDGER.md](CONVENTIONS-LEDGER.md)
finding 2b: **invariant 12's convention appeared in none of the five documents the
ledger extracts from.** It was *unwritten*, not merely ungated, and a method that
matches the repo's convention format is structurally blind to that class. So "the
gateable set is small" bounds the **documented** set only — re-deriving the ledger
will not find the next invariant 12, and only an incident will.

**Prior cycle (2026-08-01, v1.19.9 — "counted as a layer").** A **fourth** discovery
mode, after external repos (v1.19.1–2), running the library ourselves (v1.19.3–6),
and a user-authored audit prompt (v1.19.7): **a separate agent session applying the
library to its own problem handed back three proposed additions, each citing our
`file:line`.** Two were adopted — `sota-code-security` rules/08 §1 (a same-class
checker is not an independent layer; common-cause failure, and escalate-only cascades
fail *deductively* because a tier seeing only the primary's *uncertain* inputs cannot
see a confidently-wrong one) and rules/04 §8 (a TEE does not fix a **completeness**
gap; "never recorded" is liveness, outside the CC guarantee). The third — a vendor API
reporting `confidentialCompute: true` over a box with CC off — was **rejected: already
covered** by `rules/10` §2.2 (line 102, *"check the shipped artifact, not the
checkout"*) and §2.11. All three are in [ADOPTION-LOG.md](ADOPTION-LOG.md).
**Not measured — do not cite a lift.**

Two process notes from the cut. The §2b front-door grep returned **0 hits** for every
term this release added, exactly as at v1.19.7 — the second consecutive cycle where
capabilities landed in rules files with no front-door sentence, which is evidence the
habit does not stick without the gate that §2b still lacks. Fixed by extending the
README's audit-class list from seven classes to eight. And the two adoption rows were
first stamped `· [Unreleased]`, which the pre-tag checklist's `grep -n '· unreleased'`
**would not have matched** (case and brackets); the grep is now case-insensitive and
bracket-tolerant. A checklist item that silently matches nothing is the same class the
release itself is about.

**Prior cycle (2026-07-30, v1.19.7 — "inert dependency").** One release, from a
**third** discovery mode: not an external repo (v1.19.1–2) and not us running the
library (v1.19.3–6), but a **user-authored audit prompt aimed at the library's
coverage**, with CVEs and versions explicitly ruled out of scope. Under that
exclusion, 5 of its 6 requirements had no home — `rules/03-dependencies.md`
answered "is what we ship vulnerable" from end to end and never "is this
dependency reached at all" (all eight `reachab*` mentions in the file were
CVE-triage reachability). Landed: `sota-devsecops` rules/03 **§3.9
declared-but-not-reached** (entrypoint tracing incl. the impossible-path trap,
per-ecosystem tools each with its documented blind spot, **deletion-as-proof**,
leverage ratio, `gh api` upstream health, A–D taxonomy), cross-refs into the four
language skills with partial or zero coverage, and 8 rows + an entry in
[ADOPTION-LOG.md](ADOPTION-LOG.md). **Not measured — do not cite a lift.**

Two rules came out of *validating* that section rather than writing it: `gh api`
follows repo renames silently (so a 200 under a manifest's URL is not evidence the
project is still there), and where an ecosystem has no established tool (Ruby;
.NET is thin) the honest instruction is to skip the tool and go straight to the
deletion proof. Four first-draft claims were wrong and were corrected against
primary sources; one (`pushed_at` "moves on any branch push") could not be
confirmed and was **dropped** rather than shipped.

**Also this cycle: the README's audit half was invisible.** Grep on `main` before
the cut returned **0 hits** for `adversarial`, `refut`, `decision ledger`, `inert`,
`no-op`, and `ADOPTION-LOG` — five capabilities shipped across v1.17.0–v1.19.7 that
no reader could find from the front door, and "How it works" still described a
five-step audit chain that predated three of its own passes. Fixed with a new
README section carrying its own +0.00 caveat. The generalisable finding is below.

**Prior cycle (2026-07-28, after v1.19.6).** Six patch releases landed
2026-07-24…28 (**v1.19.1 → v1.19.6**), and the notable shift is *how* they were
found: v1.19.1–2 came from reading external repos, v1.19.3–6 from **running the
library and watching it fail**. Landed: three external intakes recorded in
[ADOPTION-LOG.md](ADOPTION-LOG.md) (training-knowledge-vault, swarm-forge,
claude-project-scaffold) with rejections logged alongside adoptions; the
**day-zero** work (router section + `rules/01` §10 + host-capability report +
agent-hooks-must-not-rewrite); [VERIFY-SETUP.md](VERIFY-SETUP.md), a read-only
setup-check prompt; **invariants 8 and 9** (internal-link resolution;
single-`[Unreleased]`); `sota-code-security` rules/10 **§2.13 a control that
never executes**; `sota-docs-workflow` rules/01 §7 **verify an agent file's
claims, not just its commands**; and the **liveness/async-def contradiction**
between two of our own rules, plus the router rule for resolving such conflicts.
All six are content/CI changes — **none measured**, none claiming a lift.

**Field validation this cycle (n=1 per arm, not a measurement).** The day-zero
trigger fired correctly on a purpose-built fresh repo (one throwaway checkout:
1 commit, no gates/licence/agent file) — once, in a line, offering rather than
running the scripts, and the build proceeded. It stayed correctly silent on a
mature 4304-commit repo. **It only fires when the `sota` router actually loads**:
a vague three-word prompt routed to clarifying questions instead and skipped it.
Silence is therefore not evidence the rule is broken — check the router loaded
first.

**New open items from the 2026-07-31 cycle:**

- ~~**One gateable convention remains ungated: every scoreboard row must declare its
  sample size.**~~ **CLOSED 2026-08-02 — shipped as invariant 13.** Surfaced by
  [CONVENTIONS-LEDGER.md](CONVENTIONS-LEDGER.md), which extracted **41 distinct
  conventions** from the five agent-facing docs and found **11 enforced as invariants
  plus 4 more enforced inside the eval runners** — so reading `check-invariants.sh`
  alone undercounts enforcement by about a third. Applying three filters left exactly
  **one** actionable candidate against a predicted 2–4, and it was a **regression
  guard** rather than a repair: all 10 rows already populated the Samples column. The
  implementation finds the table by its `Samples` **header** rather than a column
  index, so renaming or dropping the column fails closed instead of passing over zero
  rows. **The actionable set from written conventions is now empty.**
- ~~**`RELEASING.md` §2b's front-door grep stays blocked**~~ **CLOSED 2026-08-02 —
  shipped as invariant 14.** It was blocked on *"needs a machine-readable capability
  list per release"*, which was true and still is: **discovery cannot be gated**,
  because what counts as a capability is judgement. What *can* be gated is the
  **declaration** — the same move invariant 11 makes for `LAST-VERIFIED`. A release
  states its front-door terms and the gate proves each resolves, in
  `README.md`/`docs/INDEX.md` **and** in the release's own entry. Fires only when
  `VERSION` changes, so ordinary PRs are untouched. **The actionable set from
  written conventions is now empty** — the next gate will come from an incident,
  not from re-reading the docs.
- **CLOSED 2026-08-02: long rules files do NOT need a table of contents.** The
  skill-authoring guidance recommends one for reference files over 100 lines
  *"even when previewing with partial reads"*, and 242 of ours qualify with none.
  Tested with a planted canary across four arms (control / TOC / positive control /
  4× stress at 1,719 lines): **every arm retrieved it, every agent read the file
  whole, and the positive control showed no depth effect for a TOC to correct**.
  The sweep is not justified. *n*=1 per arm — a pilot, not on the scoreboard; it
  covers direct `Read` calls, while the guidance's stated trigger is *nested*
  references, which this library does not use. Detail:
  [CONTEXT-MANAGEMENT.md](CONTEXT-MANAGEMENT.md).
- **NEW 2026-08-02: the router is 2× the spec's token budget, and invariant 1 cannot
  see it.** The Agent Skills spec states the budget in **tokens** — *"Instructions
  (< 5000 tokens recommended)"* — and enforces nothing; invariant 1 checks the
  *line* half because lines are cheap to count. Measured across 297 skill files,
  line density varies **3.3×** (38–127 bytes/line), so a 500-line file lands
  anywhere between ~4,750 and ~15,870 tokens. **12 files already exceed ~5,000
  tokens and 11 of them pass invariant 1 comfortably.** Exactly one breaches the
  recommendation where it applies (the `SKILL.md` body): `skills/sota/SKILL.md` at
  **~10,211 tokens**, at 500/500 lines with no slack. It matters twice over —
  context cost, and Claude Code's compaction keeps only *"the first 5,000 tokens"*
  of a re-attached skill, so half the router would not survive a summarization.
  - A byte-or-token check passes all three ledger filters but **would fail on `main`
    today**, and the only fix is trimming the router — a design decision, not a
    mechanical one. The pre-existing trim candidates are recorded below (the
    per-domain pass ordering in AUDIT step 3, the duplicated severity glossary in
    step 6).
  - **Unverified in practice**: `bytes/4` is a heuristic and the real tokenizer will
    differ. Measure with a real tokenizer before acting on any specific number.
  - Detail and the measurement table:
    [CONTEXT-MANAGEMENT.md](CONTEXT-MANAGEMENT.md).
- **The reimplement case set is documentation, never run**
  (`evals/cases/reimplement.jsonl`). If anyone ever runs it, the predictions written
  *before* any run exist in the case-file header and must be used rather than fresh
  ones. A null there is the **eighth** and the recorded conclusion is to stop, not
  to author a ninth.
- **The remaining ~18 judgment conventions were deliberately not relocated.** Three
  with an identifiable point of use were moved 2026-07-31 (the stamp file, the
  invariant script's "adding a check?" block, the live-agent runners). The rest —
  *verify every claim* chief among them — apply everywhere, which is why they cannot
  be moved and must stay principles. Do not "finish" this by relocating the other 18.

**New open items from the 2026-07-30 cycle:**

- ~~**Does the rewritten build-safe spec discriminate?**~~ **Tested 2026-07-31: no.**
  Two bare agents on the thin spec scored **1.000 / 1.000** — five bare builds across
  two spec versions, all at ceiling. These seven classes are **not elicitable from a
  spec** at this model tier. The useful residue is a distinction, not a number:
  the +0.39 comes from **cross-cutting omissions** under a one-sentence prompt
  (rate limiting, logging, TLS, tests), whereas these are **local correctness
  decisions inside a feature the model is actively writing**, and it makes them
  well. Defect-avoidance and practice-completeness are different targets; only the
  second has ever shown a gap. **Do not rebuild this instrument.** Original entry: `SPEC.md` was rewritten the same day to *state features and facts,
  never the property to preserve* (verified: zero "must …" quality clauses, zero
  defect names, all six product tensions intact). Whether that restores discriminating
  power is untested: if the bare arm still scores 1.000, these classes may not be
  elicitable from a spec at all, and that is the finding. **Do not cite a build-safe
  number until the pilot lands and is scored.**

  **CROSS-MODEL 2026-08-21 — the headline does not replicate, and that qualifies it.**
  On `openai/gpt-5.1` the *unguided* arm scores **1.000 × 3**: it does not write these
  defects, so there is no headroom and Δ avoided is **+0.000** (sonnet-4.6: +0.191). The
  stricter *with-positive-evidence* measure moves on both (+0.333 / +0.095) because
  neither bare arm saturates there. Same law the breadth test found for completeness —
  **the lead tracks the unguided baseline**, here not the domain but the model. README,
  WHY-IT-WORKS and the scoreboard were all re-qualified the same day rather than left
  implying generality.

  **NEXT, and it is a new instrument not a re-run: a second TASK.** Three of the seven
  `fail` patterns are domain-specific (`ORDER BY {sort}`, the quota-handler registration,
  the role-revocation cache), so a second domain needs new patterns **plus its own
  known-bad and known-good references validated to separate** before any number from it
  counts. Deliberately not rushed: an unvalidated instrument produces numbers, not
  measurements.

  **RUN 2026-08-21 — the bare arm did NOT saturate, so the instrument discriminates.**
  Unguided 0.714 / 0.714 / 1.000 (mean **0.809**); with-library 1.000 × 3. Δ avoided
  **+0.19**, Δ avoided-with-safe-evidence **+0.33**. The two classes the unguided arm
  actually wrote were `sqli_sort` and `idor_get_report`. Full method, per-run scores and
  the six limits that bound the claim:
  [results/2026-08-21/BUILD-SAFE.md](../evals/results/2026-08-21/BUILD-SAFE.md). The
  treated arm is at **ceiling**, so the delta is bounded by the instrument, and prompt
  length is an **uncontrolled confound** — both stated there rather than implied.

  **Prior state (kept for the record): ready to run, blocked only on producing the two builds.**
  Verified rather than assumed — `run-build-safe.py` is a **scorer, not a generator** (it
  grades a `--build` directory and makes no model calls), and its `--selftest` passes with
  the two references separating cleanly: **0.000 on the known-bad (`reportkit`), 1.000 on
  the known-good (`reference-safe`)**. The case file's 49 lines are 42 comments and **7
  real cases**, and `load_cases` exits rather than score an empty set. `SPEC.md`
  re-checked: **zero** "must …" quality clauses, so the rewrite held. What is missing is
  one bare-arm and one library-arm build from that spec — model spend, and therefore an
  owner's decision rather than a scripting task.
- **Calibration — MEASURED 2026-08-21, deliberately kept out of the headline scoreboard.**
  Blinded judge validated on both controls first (mis-calibrated report 0/4,
  well-calibrated 4/4). Unguided 3/3/2 (mean **2.67/4**); with-library 4/4/4 (**4.00/4**).
  The mover is *conditioning severity on evidence*: **1/3 → 3/3**. Per the original
  entry's own instruction this is **not reported as a lift** — it measures adherence to
  our own doctrine. Write-up:
  [results/2026-08-21/BUILD-SAFE.md](../evals/results/2026-08-21/BUILD-SAFE.md).
- **Original entry — calibration was the only untested claim about the audit half.** Across four
  settings today, every library arm downgraded its own findings on evidence, bounded
  claims by what it had actually run, and labelled what it had not verified; no bare
  arm did. Nothing in the harness scores that. An instrument would measure adherence
  to our own reporting doctrine — a far weaker claim than "finds more bugs" — so if
  it is ever built, it must not be reported as a lift.

- ~~**The BUILD-safe eval needs a thinner spec before it measures anything.**~~
  **SUPERSEDED 2026-07-31** — the thinner spec was written *and* tested, and it did
  not discriminate either (see the closed item above). Kept for the diagnosis it
  records; the remedy it proposes is done and did not work.
  Built 2026-07-30 to test whether the library stops these defect classes being
  *written* rather than found. The bare arm scored **1.000 (n=3, verified
  library-free)** — ceiling, so no lift is measurable
  ([BUILD-SAFE](../evals/results/2026-07-30/BUILD-SAFE.md)). Cause is mine: the
  spec states the non-functional property to defend ("expect the change to take
  effect", "must never take the endpoint down"), which is the audit-vocabulary
  leak in a new costume — it supplies the consideration set. Fix: state the
  feature, not the requirement, and let the safety judgment come from the model.
  The fixture, scorer, and two references are reusable as-is; only SPEC.md needs
  rewriting. **Not on the scoreboard — it is an instrument failure, not a null.**

- ~~**Our own gates now report a denominator — the rest of the automation does
  not.**~~ **Done 2026-07-30.** `check-freshness.sh` now exits 1 on an empty scope
  (it printed the denominator but never failed on it); `evals/test_scoring.py`
  now prints `(25 checks)` — the floor has since risen to **38** — and fails below
  it, watched to fail by simulating
  an early return (`only 17 ran, expected at least 25`). One suspicion was
  **REFUTED** and recorded: CI's `shellcheck scripts/*.sh` fails loudly on an
  unmatched glob in bash (exit 2), so there was nothing to fix. ~~Still unexamined:
  what gitleaks reports as its scope over the full history.~~ **Examined
  2026-08-02 — it reports a denominator and nobody read it.** gitleaks prints
  `179 commits scanned`; measured in a `--depth 1` clone of this repo it scans
  **1 of 179**, prints `no leaks found`, and **exits 0** — a green secret scan over
  0.5% of history, with `fetch-depth: 0` the only thing preventing it and nothing
  asserting that. CI now asserts the scope. The assertion keys on
  `git rev-parse --is-shallow-repository`, **not** on a commit count, for a reason
  worth keeping: `git rev-list --count HEAD` truncates to 1 in the same clone, so
  it degrades alongside the scan it would be checking — and the three available
  numbers disagree anyway (rev-list HEAD 175, rev-list --all 181, gitleaks 179),
  so any equality test would be flaky. It also fails if gitleaks stops printing the
  line at all, since an unparsable output means the scope is no longer verified.
- ~~**Duration is not recorded for any of our automation.**~~ **DONE 2026-08-03.**
  The remaining half — no recorded baseline — is closed: `_elapsed.py` appends every
  run to a git-ignored `evals/results/durations.tsv` and the next run of the same
  runner prints the delta, flagging a swing of ≥ 5×. §2.1's tell is a *comparison*,
  so printing alone never sufficed. Denominators matter as much as the seconds
  ("12s over 7 cases", not "12s"): **7 of 12 runners declare one**, the rest record
  `-` and are labelled weak evidence rather than silently compared. The ledger is
  machine-local by design — a duration is only comparable on the same machine and
  network. **The CI half needed nothing**: the GitHub API already exposes
  `started_at`/`completed_at` per step (verified). Original entry: **Partly done
  2026-07-30.** `check-invariants.sh` prints wall time with its denominators
  (`10 checks over 297 skill files / 256 rules files, 10s`). Deliberately printed
  and **not gated** — a duration threshold in CI is flaky under runner variance,
  and a flaky gate gets disabled. **The runner half is done 2026-08-02**: all 13
  runners now print `[<runner> elapsed 12.3s]` via `evals/_elapsed.py`, registered
  with `atexit` so the line survives the `sys.exit(...)` several of them use on an
  empty corpus — the fast-exit case most worth timing. To **stderr**, so a runner
  whose stdout is piped or parsed is not handed an extra line. Printed, never
  gated: these call a remote API whose latency is not ours. **Still open**: no
  recorded baseline to compare a future run against, so "it got 30× faster" is
  still visible only to a human reading two logs.
- ~~**The dead-path eval has never been run against a live agent.**~~ **Run
  2026-07-30 — and the hypothesis was wrong.** Six local sub-agents, 3 per arm:
  **both arms 1.000/1.000, +0.00**. The pre-registered prediction ("a bare agent
  reasons and scores ~0.25 verdict / 0.00 proof") is **refuted** — the bare agents
  worked in scratch copies, mutated the controls, deleted the modules, ran
  `trace.Trace`, and one used `dis` to spot the discarded return, none of it
  requested. So "these instruments score recognition, not procedure" no longer
  explains the audit family's saturation
  ([DEAD-PATH](../evals/results/2026-07-30/DEAD-PATH.md)). The arms differ only in
  reporting discipline (ACTIVE/LATENT labels 0/3 vs 3/3, bounded claims 0/3 vs
  3/3, decision-boundary fix-risk 0/3 vs 3/3) — post-hoc, partly tautological
  since the library arm was told to use that vocabulary, and **not a lift**.
- ~~**Where the audit frontier actually is, after that null.**~~ **Both readings
  tested 2026-07-30 and both are dead** ([UNSCOPED-AUDIT](../evals/results/2026-07-30/UNSCOPED-AUDIT.md)):
  stripping the answer vocabulary changed nothing (A), and unusual defect classes
  under an unscoped brief changed nothing (B) — verified-clean bare agents scored
  1.000 on both. **Do not build another audit-recall instrument.** The one
  untested claim is *calibration*: every library arm downgraded its own findings
  on evidence and bounded claims by what it had run; no bare arm did. Measurable,
  but it measures adherence to our own doctrine — a far weaker claim than "finds
  more bugs", and not to be reported as a lift. **Effort moves to BUILD**, which
  is where the measured lift is (+0.39 completeness, +0.53 freshness).
  Original framing kept below for the record.

  Two readings survived the dead-path null and neither is tested. (a) *The brief did the work*: naming four suspects and
  demanding a `PROOF` field is a strong nudge; a genuinely unscoped "audit this
  repo" over a large tree might separate the arms — this run is weak evidence for
  prioritising the **agentic large-repo audit** (item 2 below) over building more
  small fixtures. (b) *The scored axes are the wrong ones*: an instrument grading
  labels, bounded claims and fix-risk would measure something, but it would be
  measuring adherence to our own vocabulary, a far weaker claim than "finds more
  bugs" — it must never be reported as a lift. Do not build a sixth small fixture
  without a reason to expect a different answer.

- ~~**No gate notices a capability that never reached a front-door surface.**~~
  **CLOSED 2026-08-02 — invariant 14.** Original entry below; the gate verifies the
  *declaration*, since discovery is judgement and cannot be gated.
  Invariant 6 fails the build on a wrong *number* in the README; nothing fails on a
  missing *feature*. That is why five audit capabilities went undocumented for three
  releases — the same silent-surface shape `sota-code-security` rules/10 describes
  for controls. Interim fix landed in [RELEASING.md](../RELEASING.md): the pre-tag
  checklist now says to grep the README and `docs/INDEX.md` for a distinctive term
  from each capability the release added. A real gate would need a machine-readable
  list of capabilities per release — worth considering, not obviously worth the
  ceremony.
- **§3.9 may be the one audit instrument that could move off +0.00.** Every audit
  eval saturates because a frontier model handed the code *and* the question is
  already at ceiling — but §3.9 grades a **procedure** (copy the tree, delete the
  dependency, run the real build, report exit codes) rather than a recognition. An
  eval that scores whether the model *actually ran the deletion* instead of asserting
  "appears unused" would test something the saturated instruments cannot reach. Needs
  a tool-using harness, so it shares the blocker with the agentic large-repo audit
  (item 2 below) — cheaper, though: a small fixture repo with two genuinely inert
  dependencies and one reached only from a test.
- **The §3.9 tool table will rot.** It names eight third-party projects, each with
  its documented blind spot, all verified live 2026-07-30. Two had already been
  **renamed** under the URLs a manifest would carry. It is now a named target in
  [MAINTENANCE.md](MAINTENANCE.md); the section itself tells readers to re-verify
  before trusting a row, which is the only maintainable posture.
- **Ruby and .NET have no dependency-reachability tool worth naming.** Recorded as a
  deliberate gap, not an oversight (candidates: 5 stars, one contributor each, one
  with no push since 2025-01-03). Revisit if a maintained option appears.

**Open items from the 2026-07-28 cycle (still open):**

- ~~**No update-notification path for clone installs.**~~ **CLOSED 2026-08-02 —
  `scripts/update-reminder.sh`**, reaching both install paths and making no network
  request. Original entry below. Symlinked skills update the
  moment you `git pull`, but nothing ever tells you to pull. The plugin's
  `SessionStart` notice (`hooks/hooks.json` → `scripts/plugin-notice.sh`) is
  marker-guarded to fire **once ever**, so it is onboarding, not a version
  channel. **Partly done (2026-07-30).** The claim previously recorded here — that
  `install.sh --update` "already knows both versions" — was **false**: the script
  had **zero** references to `VERSION` (`grep -c VERSION scripts/install.sh` → 0).
  It now reads `VERSION` before and after the pull and prints the delta
  (`1.19.7 → 1.20.0 — see CHANGELOG.md`), and `--version` reports the release,
  checkout, upstream state as of the last fetch, and whether the install is
  symlinked or a pinned `--copy` snapshot. ~~What remains open is the *push*
  half.~~ **DONE 2026-08-02 — and the phone-home question was dissolved rather
  than answered.** `scripts/update-reminder.sh` runs on `SessionStart` and, at
  most once every 14 days, tells the user their install is getting old and how to
  check. **It makes no network request** — it cannot know whether a new version
  exists, only how long since it last spoke. That is the point: the benefit was
  *reminding you updates exist*, which needs no telemetry, and a real check from
  every session start would turn a documentation library into something that
  reports when and how often you work. The check stays manual and is one command
  (`install.sh --update`). TTL from the state file's mtime (`find -mtime`, because
  GNU `date -d` and BSD `date -v` disagree), silent on first run, opt-out with
  `SOTA_UPDATE_REMINDER_DAYS=0`, and **fails open on every path** — unwritable
  data dir, missing `VERSION`, garbage in the env. Reaches **both** install paths:
  the plugin via `hooks/hooks.json`, clone installs via `install.sh`'s routing
  setup (which is what the original item was actually about).
- ~~**Nothing reports which version is in use.**~~ **Done 2026-07-30** —
  `scripts/install.sh --version` reports it (release from `VERSION`, `git
  describe`, upstream-ahead count as of the last fetch, symlink-vs-snapshot
  install mode), and the README's Updating section tells reporters to quote it.
  Tested on six paths: normal checkout, non-git snapshot, missing `VERSION`,
  unlinked target, `--update` with and without a version change, and behind-
  upstream. Still true that **no skill file carries a version**, deliberately:
  a version string inside a skill is one more surface to bump every release, and
  `VERSION` is already the invariant-5-guarded source of truth.
- ~~**`scripts/verify-setup.sh`** — the deterministic half of VERIFY-SETUP.md.~~
  **DONE 2026-08-02.** 14 checks, strictly read-only (verified by hashing the file
  tree and `git status` before/after), exits 1 on any FAIL, `--runs N` widens the
  CI-history sample. The prompt keeps the half a script cannot do: whether an agent
  file's *content* is meaningful (4) and whether its claims are still true (5b),
  plus the routing dry-run (11) — each now labelled `N/A — judgement check` in the
  script's own output so the split is visible where you run it.
  - **Writing it found a bug in itself.** Check 8 used `git grep`, which reads only
    **tracked** files, so an untracked `.pre-commit-config.yaml` configuring
    gitleaks was reported as *no secret scanning* — a false FAIL on precisely the
    case the doc names first ("on a repo you just scaffolded"). Found by running
    the fail path, not by reading the code. Now plain `grep`.
  - **And it validated its own UNVERIFIED vocabulary.** On this repo, check 10b
    (*has CI ever rejected anything?*) reads UNVERIFIED at the default 60-run
    sample — 60/60 success — and turns up **1 failure at 200**. "Not in the last
    60" really is not "never", and that is why `--runs` exists.
- ~~**`gh-sota` extension — considered and deferred, with reason.**~~ **CANCELLED
  2026-08-02, not deferred.** Its one real benefit was update notification, and
  that is now delivered directly by the SessionStart reminder below — without a
  second repo, a shim, or a CLI nobody would invoke. Closing it rather than
  leaving it "deferred" forever: a deferred item with a dead rationale is
  indistinguishable from a live one on a list. Original reasoning, kept because it
  is still why the shape never worked: gh requires the
  repo to be named `gh-*` with a root executable of the same name (verified in
  `gh extension --help`, 2.96.0), so it cannot live in this repo; it would need a
  thin shim repo delegating to `scripts/`. Its headline benefit does not
  materialise either: gh's update notice fires **on invocation**, and nobody
  invokes a CLI for a library used inside an agent session. Revisit only if
  one-command install becomes the bottleneck.
- **Router headroom: 500/500 lines — exhausted.** The rules/11 pointer in AUDIT
  step 4 consumed the last three lines, and invariant 1 caught the overflow at 504
  mid-edit; the text was compressed twice to fit. **The next router addition must
  trim first — there is no slack at all.** Candidates when that day comes: the
  per-domain pass ordering in AUDIT step 3 (11 lines, largely re-derivable from the
  routing table) and the severity glossary in step 6 (5 lines, duplicated in
  `rules/01` §4). `ROUTER_BUILD_SHA` is still `71a9d78ea5e9e341`, **re-computed and
  matched after every router edit on 2026-07-30**, so all of them landed outside the
  eval-pinned BUILD block and historical completeness runs stay comparable.
- ~~**Unverified claim in the README** — that git-hosted plugin marketplaces
  re-check at session start.~~ **Checked 2026-07-30 and it was wrong in the way
  that matters.** The Claude Code docs state that *"third-party and local
  development marketplaces have auto-update disabled by default"* — this is a
  third-party marketplace, so a plugin user gets **no** automatic refresh unless
  they explicitly enable it; and even enabled, the check runs after session start
  "with a random delay of up to ten minutes" while the running session keeps its
  launch versions. The README implied users were being kept current when by
  default they are not. Fixed with the quote, the opt-in path, and a pointer to
  `--version`. **This makes the notification item above more important, not less**:
  neither install path pushes updates by default.

**Prior open items, still open (2026-07-22 framing, re-checked today):**

The foundation is de-risked and the
release cadence caught up: **v1.17.0 → v1.19.0** shipped across 2026-07-20…22.
Landed this stretch — silent-control `rules/10` (measured **+0.00**, the +0.07 and
the taxonomy-anchoring signal both retracted as noise), adversarial verification and
decision-ledger review in AUDIT mode, the gap-reporting loop, the drifted
`BUILD_WORKFLOW` mirror found and pinned (`ROUTER_BUILD_SHA`), the eval **scoring
functions given mutation-tests in CI**, negative controls grown 8→20 (over-flagging
resolved as noise), the README re-led on the proven lift + an architecture
infographic, and — the headline — **cross-model replication: the +0.39 completeness
lift is not sonnet-specific** (`openai/gpt-5.1` shows **+0.44**).

**Genuinely open, ordered by value:**
1. **Distribution / adoption** — the real bottleneck. Re-checked live 2026-07-30 via
   `gh api`: **8 stars, 0 watchers, 2 forks** — unmoved in two days — and **exactly
   one true issue ever** (#4, closed; filtering `has("pull_request")` out of the
   issues endpoint, which otherwise counts all 150+ PRs as issues). The gap-reporting
   loop has produced **0 external reports in 8 days**. The asymmetry is now sharper,
   not softer: every gap closed in v1.19.3–v1.19.7 was found by *us* running the
   library or by the maintainer aiming a prompt at it — **none by an external
   reporter**. Publish the salience write-up + the infographic (LinkedIn is the
   measured top referrer). A **people problem, not a measurement one** — the
   highest-leverage lever left.
2. **Agentic large-repo audit** — **ATTEMPTED 2026-08-03; a SYNTHETIC fixture cannot
   do it** ([BIG-REPO-AUDIT](../evals/results/2026-08-03/BIG-REPO-AUDIT.md)). Two
   fixture generations, 360+ files and ~95k tokens each, six planted defects. The bare
   arm scored **6/6, 6/6, 6/6** on v1 and **6/6, 5/6** on v2 — at ceiling, no headroom,
   so the library arm was never run and no number is published. The reason
   generalises: **in a synthetic corpus a planted defect is by construction a deviation
   from generated filler, and agents find deviations mechanically** — v1 by file
   naming, v2 by AST-normalising every method body and diffing. Scaling the repo makes
   the anomaly *cheaper* to spot, not harder. The pre-registered prediction (bare
   0.30–0.50) was **wrong by ~2×**. What would be needed instead: a **real** repository
   with **real** defects at a known commit, where the flaw is ordinary code someone
   believed was correct. Original framing — the *only* design that could move AUDIT off
   +0.00
   (all four single-prompt audit instruments saturate). Needs a new tool-using harness
   + a large ground-truth-defect fixture + two-axis (recall × efficiency) scoring;
   cost band **$15–60**, deferred by the user until later.
3. **Cheap incremental confidence** (~$3 within current credit): a 2nd cross-family
   BUILD model (gemini-2.5-pro) → "holds across three families"; cross-model freshness
   + routing (both still single-build-model).
4. **As-deployed competitor comparison** (~$8) and competitor domains beyond the five.
5. **Multi-turn amplification at scale** — needs much larger intervening context than
   the moderate-scale decay run.
6. **First 6-month accuracy sweep ~Jan 2027** (`LAST-VERIFIED` 2026-07-08).

Credit was ~**$8.79 as of 2026-07-22** and has **not been re-checked since** — no
paid eval ran in the 2026-07-24…28 cycle (all six releases were content/CI work).
Verify via the OpenRouter credits API before planning anything paid; never assume
this figure. The dated per-cycle record below is the history; this block is the
live picture.

---

**v1.16.0 released** (2026-07-16, PR #115, tag `v1.16.0`) — rolled up the big
post-v1.15.0 batch (PRs #88–#114). Executed across it: multi-sample tightening
(item 1), live-agent BUILD validation (item 2), cross-file audit (item 3, +0.00 →
agentic large-repo is the frontier, 3′), the **competitor benchmark** (item 6)
**and a 5-domain breadth run** (the lead tracks the unguided baseline, not the
domain — SOTA-skills leads on incomplete-by-default tasks: backend [Python+Go] +
hard frontend; ties on simple UI + templated IaC), a first **decay/multi-turn** run
(item 5, no decay at moderate scale), a **discoverability overhaul** (docs/INDEX.md,
docs/CONTEXT-MANAGEMENT.md, RESULTS.md scoreboard, README TOC), the **500-line cap
scoped to skill files only**, a **4-way accuracy sweep**, and **theme-aware
benchmark + breadth charts**.

**Post-release, same session (PRs #111–#117):** concluded the breadth comparison
(#111); mined a separate agent-orchestration project of the maintainer's and adopted
**three pure-Markdown conventions, each independently measured** — negative routing
cross-refs, plan-concreteness in BUILD step 3, and an evidence-based-completion
operating principle (#112) — with regression checks proving no loss (completeness
held **0.991/+0.385** #112; routing held **1.00** #113); built the **description-
routing eval** measuring the skill auto-loader path (#114, honest **+0.00** —
saturated like audit; cross-refs kept as zero-cost defensive clarity); cut **v1.16.0**
(#115); consolidated the breadth chart + full story into RESULTS.md (#116); and added
**`sota-docs-workflow` rules/01 §8 "The documentation baseline"** — the must-have doc
set incl. community-health files, GitHub search precedence verified (#117). Runtime-
bound ideas from that project (memory-bank persistence, RAG, worktree locks, agent
framework)
were deliberately **not** ported.

**Post-v1.16.0 (2026-07-20):** added **`sota-code-security` rules/10 "Silent
control failure"** — controls that look enabled and do nothing. A gap analysis
over the whole tree found 9 of its 12 concepts uncovered anywhere (the falsi-
fication question, optional-dependency degradation, weak existence checks,
zero-rule loads, attacker-triggerable early returns, doc/code default drift,
hardcoded report numbers, shipped-artifact gaps, asymmetric negative-claim
evidence); fail-open (rules/03) and test vacuity (`sota-testing` rules/02/06/09)
were already strong and are cross-referenced, not duplicated. Wired into the
**default** paths rather than left opt-in: router BUILD step 4 (falsification
question over every control in the diff), a new AUDIT **step 4 silent-control
pass**, routing rule 20, and the asymmetric evidence burden in operating
principle 3 + `sota/rules/01` §5. **Then measured** (same day,
[`evals/results/2026-07-20/SILENT-FAILURE.md`](../evals/results/2026-07-20/SILENT-FAILURE.md)):
a case set run two ways — vocabulary-given and open-ended/blind-judged — plus an
**ablation arm** that drops rules/10 from the with-library context. A first
15-case version showed **+0.07**; the set was then **grown to 49** (41 positives,
8 loud-failure negative controls, 6 mechanisms rules/10 does *not* enumerate) and
**the lift did not replicate**: **+0.03** vocabulary / **−0.01** open-ended, both
inside a per-arm spread of ±0.04, with rules/10's ablated contribution **+0.00**.
The +0.07 was small-sample noise (the 15-case with-arm sat at 0.99–1.00 — no
headroom); it is **retracted** in `RESULTS.md` and the writeup. Silent-control
detection therefore joins audit / cross-file audit / desc-routing as a **+0.00**
dimension. rules/10 is kept on gap-analysis grounds with **no efficacy claim**.
Open follow-ups: (a) **DONE 2026-07-20 — the `novel` subgroup was grown 6 → 26 and the taxonomy-anchoring hypothesis is RETIRED**: the gap collapsed from 1.00 vs 0.83 (n=6) to **0.96 vs 0.92 (n=26) — one case, inside run spread**, so the library's enumerative content pattern is *not* shown to reduce generalization to unlisted mechanisms. Overall lift reproduced at **+0.00** on the 69-case set. One thing to watch if the negative set grows: the ablated arm scored 1.00 on the 8 loud-control negatives vs 0.75 for both other arms, hinting mildly at over-flagging rather than anchoring (2 of 8 — not a finding). (b) the **agentic** design remains the only one that can measure what the file is for; (c) cross-model replication — **DONE 2026-07-22** (gpt-5.1, see the cross-model
entry below). Note kept from that work: the four cases that defeat every arm (build-tag
no-op, glob extension mismatch, env-filter mismatch, unawaited async assertion) were
deliberately **not** written into the rule, since that is fitting guidance to the test set.

**Cycle detail (2026-07-20…22) — done items, kept as the record:**
- **DONE 2026-07-22 — cross-model replication of the BUILD lift.** Every completeness
  number had used one build model. Re-run with `openai/gpt-5.1` (different family)
  driving BUILD, same judge/rubrics/tasks: **0.44 → 0.88, +0.44** (every case positive).
  The +0.39 is **not sonnet-specific**; the lift is larger where the baseline is lower,
  reproducing the "lift tracks incompleteness" mechanism across models. Cost $1.87.
  [CROSS-MODEL.md](../evals/results/2026-07-22/CROSS-MODEL.md). Follow-ups: a second
  cross-family model (gemini) and cross-model freshness/routing remain single-build-model.
- **DONE 2026-07-20 — the flagship number is verified against the workflow that
  ships.** `BUILD_WORKFLOW` had drifted from router BUILD steps 3–4 for four days.
  Both arms run: drifted **0.59 → 1.00 (+0.40)**, synced **0.58 → 0.98 (+0.40)**. The
  `+0.39` was never wrong — only measured against stale text; `RESULTS.md` now carries
  the synced numbers. Drift cannot recur silently (`ROUTER_BUILD_SHA` pins the router
  section; the runner aborts on mismatch, guard watched to fire).
  [MIRROR-VERIFICATION.md](../evals/results/2026-07-20/MIRROR-VERIFICATION.md).
  **Follow-up CLOSED 2026-07-21:** arm B was repeated and the 0.02 dip was **noise** —
  c1 recovered 0.86 → 0.94, and its own swing across three runs (0.86–0.97, 0.11) is
  larger than the gap it was meant to explain. No measurable cost to the falsification
  clause. Two-run synced mean: **0.59 → 0.98 (+0.39)**, now the published figure —
  note that `+0.40` had been published from a *single* run. **Standing lesson: stop
  publishing from n=1.** Second time this week a single run produced a figure a larger
  sample walked back (the other: the retracted +0.07 on silent-control detection).
- **Distribution** (item 7): publish the salience write-up
  (`docs/writeups/completeness-blind-spot.md`) — LinkedIn is the proven channel
  (corroborated 2026-07-20: it is the **top referrer** in GitHub traffic);
  marketplace visibility; badge→verifiable-audit. **Traffic measured 2026-07-20:**
  ~24 organic clones/day (the three days with zero CI runs show clones exactly equal
  to unique cloners) against **7 stars, 0 watchers, 1 issue ever**. Since the install
  path *is* `git clone`, clones are the adoption metric and stars badly understate it
  — but the project also learns nothing from those users, which is what the
  **gap-reporting loop** (#124, shipped) is meant to change. Whether it produces
  reports is unmeasured; if it yields nothing in a few weeks, cut it.
- **As-deployed competitor comparison** + **more competitor domains** (data/mobile/
  CLI); the baseline-driven finding is established but these extend it.
- **Agentic large-repo audit** (3′) and **constraint-budget probe** (4).
- **Multi-turn amplification, at scale** (5): the decay run found *no* decay at
  moderate scale — needs much larger intervening context to find the breaking point.
- **Grow the eval case sets** (item 1 sub-task, content authoring). Done this cycle:
  silent-failure 15 → **69** (35 enumerated + 26 novel + 8 negative controls) and a
  new 30-case audit-precision set. **Negative controls grown 8 → 20 on
  2026-07-21 and the over-flagging signal RESOLVED as noise** — all three arms now
  score 1.00 on them (the 0.75-vs-1.00 hint was 2 of 8 cases). Every subgroup signal
  this set has produced has evaporated when the subgroup grew: anchoring at 6→26,
  over-flagging at 8→20. Still thin: the 7-case completeness set and competitor
  domains beyond the five measured.
- **First 6-month accuracy sweep ~Jan 2027** (item 8; bump `LAST-VERIFIED`).

Historical per-item notes below (kept as the record of what was done):

1. **Tighten the eval numbers (confidence, not point estimates).** **Multi-sample
   DONE 2026-07-13** — [`evals/results/2026-07-13/MULTI-SAMPLE.md`](../evals/results/2026-07-13/MULTI-SAMPLE.md).
   All three value dimensions re-run at `--samples 3 --temp 0.7`: completeness
   **0.60 → 1.00 (+0.39)** with the with-arm at ±0.01 across-case sd (reproduces
   the single-sample headline, 6/7 cases perfectly steady); routing **0.90 → 1.00
   (+0.10)**, with-arm ±0.00; freshness **0.44 → 0.97 (+0.53)**, with-arm ±0.00
   (reused). The with-library arm is near-zero variance everywhere; the sampling
   wobble is all in the unguided arm. Single-sample caveat retired. **Remaining
   sub-task:** *grow* the completeness (7) and freshness (32) sets — that's
   content authoring (new cases), not a re-run, and is still open.
2. **Validate the v1.15.0 BUILD-workflow changes in a *real* agent run.**
   **DONE 2026-07-13, fully closed** — [`evals/results/2026-07-13/LIVE-BUILD.md`](../evals/results/2026-07-13/LIVE-BUILD.md).
   Seven live sub-agents built the 7 completeness tasks through the real router
   flow (load-lean → checklist → terminal self-audit). Verified from their
   `process.md` audit logs (primary source): all 7 followed the workflow;
   cross-cutting concerns present in every applicable build; the self-audit gate
   **caught and fixed real gaps** live (c6: prod `/docs` exposure + unbounded DB
   critical section; c3: orphaned-task cancellation bug). The blind-judge scalar
   (run once credit was restored) is **0.99 mean, 6/7 perfect — matching the
   0.99 simulation (0.987 vs 0.988) and far above the 0.60 base**, proving the paste-based eval is a faithful
   proxy for the live router flow (`evals/results/2026-07-13/live-build.json`).
3. **Cross-file / repo-level audit eval.** **DONE 2026-07-13** —
   [`evals/results/2026-07-13/REPO-AUDIT.md`](../evals/results/2026-07-13/REPO-AUDIT.md),
   `evals/run-repo-audit.py`, 15-file fixture with 8 defects invisible in any
   single file. Result: **+0.00 on sonnet-4.6 and opus-4.8** (strict,
   file-attributed). The finding *refines* the hypothesis: cross-file is not the
   barrier — **context the model can't hold at once** is. A ~17 KB repo pastes
   whole, so recognition (already saturated) catches everything. The real
   frontier is now item 3′ below.
3′. **Agentic large-repo audit eval** *(new, replaces the snippet/small-repo
   version).* The only untested audit-lift path left: a repo too large to hold in
   context, audited through a **tool-driven agent loop** (selective file reads
   under a budget), with-library vs without — where the router's "which files to
   open, what to connect" guidance is the thing under test, not recognition.
   Materially bigger harness (a real agent loop, not one API call).
4. **Constraint-budget probe** *(new, from the v1.15.0 whack-a-mole: c1 dropped
   size-limit when principle 5 was added).** Measure how many simultaneous
   non-negotiables a model reliably satisfies — informs how short principle 5 and
   per-task checklists must stay. Directly tests the salience/attention finding
   in [`WHY-COMPLETENESS-RESIDUAL.md`](WHY-COMPLETENESS-RESIDUAL.md).
5. **Multi-turn / agentic amplification test** *(new)*. **First run DONE 2026-07-15**
   (`evals/run-decay.py`, `results/2026-07-13/DECAY.md`): guidance at turn 1 → K
   filler turns → build probe. **No decay at moderate scale** (guidance held over 30
   turns) — the filler is too small to dilute a ~18.6K-token anchor, so it bounds
   the problem but doesn't find the breaking point. **Open:** scale up (much larger
   intervening context, or a subagent chain).
6. **Competitor-library benchmark** — **DONE 2026-07-14/15** (see "Unexplored ideas"
   below for the full result): SOTA-skills beats the fair peers on completeness on
   backend tasks, content-only. **5-domain breadth (2026-07-15/16) reframes it: the
   lead tracks the unguided BASELINE, not the domain** — SOTA-skills leads +~10 pts
   where a base model ships incomplete code (Python+Go backend, hard SSR/auth
   frontend; baseline ≤0.67) and ties where it's already complete (simple frontend
   77%, IaC 87%). See `results/2026-07-13/BREADTH.md`. The honesty gate is cleared for a *scoped-to-backend* "vs library X"
   claim; every doc surface was rescoped accordingly.
7. **Distribution over coverage** (item 6): marketplace visibility, a published
   before/after demo, badge→verifiable-audit. **Started 2026-07-13/14:** (a) the
   README now leads with the measured lifts as a scannable list (completeness
   +0.39, freshness +0.53, routing +0.10) and puts the clone/script install right
   after the plugin method (PRs #92–#93); (b) a publication draft of the
   completeness/salience finding is ready at
   [`docs/writeups/completeness-blind-spot.md`](writeups/completeness-blind-spot.md)
   (verified before/after — webhook 0.50→1.00, upload 0.55→1.00). **Still open:**
   the maintainer publishes the write-up (LinkedIn is the proven referral channel
   per traffic data); marketplace visibility and badge→verifiable-audit are
   untouched. The compelling demo is **completeness** before/after, not audit —
   audit lift is +0.00 (item 3), so an audit demo would undersell.
8. **Scheduled — first 6-month accuracy sweep ~Jan 2027** (item 5): re-verify
   fast-moving claims per `docs/MAINTENANCE.md` and bump `LAST-VERIFIED`.

## Now — prove and protect accuracy *(done this cycle)*

The audit's verdict was "content is trustworthy; the gap is that nothing
*proves or protects* accuracy." Closed 2026-07-10 (PRs #63–#66):

1. **Content-accuracy runbook + shorter window** — `docs/MAINTENANCE.md`
   documents the reproducible per-skill re-verification sweep (was only in
   maintainer memory); `check-freshness.sh` window cut 12→6 months. *(#66)*
2. **Audit defect cleanup** — content corrections (OWASP/RFC/ingress/Iceberg/
   version-pins) + router-map refresh *(#63)*; **invariant 7** (router
   completeness) + check-2 fence / check-5 semver / CI fail-open hardening
   *(#64)*; installer decline-abort + profile-clobber *(#65)*.
3. **Eval-harness prototype** — `evals/` (golden-set cases + `score.py`,
   verified end-to-end) makes the efficacy claim measurable. *(#66)*

## Next — grow what the prototypes started

4. **Eval baseline + clean isolated control** — *done 2026-07-10/11*
   ([`BASELINE.md`](../evals/results/2026-07-10/BASELINE.md); `evals/run-clean.py`):
   **routing lift ~+0.10 replicates in a true library-vs-nothing raw-API
   control** (+0.09/+0.14/+0.09 across sonnet-4.6/sonnet-5/opus-4.8) — the
   contamination concern is resolved, the lift is real. **Audit +0.00**;
   **Freshness +0.50–0.65** (base model confidently wrong on 2026 facts, but a
   web-search agent would likely recover most of it — predicted, untested). **Completeness +0.39** (0.60→0.99 over
   7 tasks, full library, `cases/completeness.jsonl` + `run-completeness.py`,
   blind opus judge) — the **thesis, validated**: from a bare "build X" prompt the
   base model skips tests/rate-limits/logging/transport ~40% of the time; the
   library embeds them, and search can't close this gap. **Load-bearing as an
   ablation:** base 0.60 → +rules ~0.89 → +BUILD self-audit 0.93 → +principle 5
   0.99 (`results/2026-07-13/`). Surfaced fixes, all landed: the self-audit is a
   hard BUILD gate; cross-cutting concerns are the router's short **operating
   principle 5**; and the BUILD workflow now says load-lean + plan-with-checklist
   + terminal re-read. **Root-cause investigation (2026-07-13):** the residual is
   NOT a coverage gap (the forgotten rule was in scope + in a checklist); it's a
   **salience / context-rot attention effect** — *adding* the missing rule made it
   worse, a short reminder fixed it ([`docs/WHY-COMPLETENESS-RESIDUAL.md`](WHY-COMPLETENESS-RESIDUAL.md),
   experiments + literature). Curated for readers in
   [`docs/WHY-IT-WORKS.md`](WHY-IT-WORKS.md) (honest "vs. an unguided model"
   framing — see the unexplored idea below). **Eval-suite hardening — done
   2026-07-12:** completeness 4→**7** tasks; freshness 20→**32** cases
   (all primary-source-verified; +0.50, and +0.53 at 3 samples with 0.97±0.00 vs
   0.44±0.03); harder-audit 7→**14** — still +0.00 (a capable model catches even
   subtle/multi-vuln snippets *in isolation*, so a real audit lift needs
   cross-file context, not more snippets); and `--samples/--temp` added to both
   harnesses (retires the single-sample caveat on the cheap dimensions).
   **Shipped as v1.15.0** (2026-07-13, PRs #78–#85). Follow-through: the
   multi-sample averaging is **done** (2026-07-13, PR #91 — see Open tasks item 1,
   with-arm near-zero variance); *growing* the completeness + freshness sets is
   still open (Open tasks item 1, content authoring).
5. **First 6-month accuracy sweep** comes due ~Jan 2027 (freshness window) —
   run it per the `docs/MAINTENANCE.md` runbook and bump `LAST-VERIFIED`.

## Later — distribution over coverage

6. **Pause net-new skills; invest in distribution.** Coverage is an exhausted
   lever at current adoption (audit: 4 stars / 1 issue after 41 skills). Put
   the effort into visibility (marketplace, a published before/after audit
   demo) and the badge→verifiable-audit idea (link the "Built with" badge to a
   committed audit report + commit SHA). *(audit STRAT-MED-1)*

## Unexplored ideas

- **Comparative benchmark vs. named competing libraries.** ~~Unexplored~~
  **DONE 2026-07-14** ([`evals/results/2026-07-13/COMPETITOR-BENCHMARK.md`](../evals/results/2026-07-13/COMPETITOR-BENCHMARK.md),
  `evals/run-competitors.py`, `evals/cases/competitors.json`). SOTA vs. the fair
  peers, content-only, blind-judged, 7 build tasks: **SOTA 0.99 >
  [affaan-m/ECC](https://github.com/affaan-m/ECC) ~230k★ 0.87 >
  [PatrickJS/awesome-cursorrules](https://github.com/PatrickJS/awesome-cursorrules) ~40k★ 0.83 >
  [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) ~23k★ 0.81**
  (unguided 0.58). SOTA wins/ties every one of 21 cases, loses none; competitors
  are legitimate (all +0.23–0.28 over unguided) but drop the cross-cutting
  non-negotiables SOTA embeds. The honesty gate is **cleared** — `WHY-IT-WORKS.md`
  now carries a scoped "vs library X" claim. **Breadth DONE 2026-07-15/16 — lead tracks the
  BASELINE not the domain (5 domains, BREADTH.md):** SOTA-skills leads where the base
  model is incomplete (backend any-lang, hard frontend) and ties where it's complete
  (simple frontend, IaC). [old note kept:] on 3 simple React tasks SOTA-skills ties ECC and
  claude-skills (all 97%, even losing one task); frontend completeness is easy
  (unguided 77% vs 58% backend) so any guidance reaches the top. So the claim is
  scoped to **backend**, not general (`competitor-breadth-frontend.json`).
  **Follow-ups still open:** multi-sample the arms; more domains (data/mobile/CLI);
  ~~optionally an *as-deployed* comparison~~ — **rejected 2026-08-16**, see the reasoning
  under the open-items table.
  Original plan/targets kept below for reference.
- **(reference) Original competitor-benchmark plan.** Every eval to
  date is library-vs-*nothing* (an unguided model), so the public claim was
  honestly limited to that; to earn a "vs X" claim, run a competitor's content
  as a **third arm** (same fixed rubric, blind judge, token budget) and report the
  delta — **publishing it even if SOTA ties or loses.**
  **Targets validated 2026-07-14 via the GitHub API** (stars + created-date +
  license + repo structure). **Pick on purpose-overlap, not raw stars** — many
  high-star repos are a *different kind* of thing, and the biggest ones are all
  2026-new with explosive (plausibly inflated) star growth, so treat the numbers
  skeptically. Tiers:
  - **Same-kind engineering guidance a model reads to build/audit code** (the fair
    completeness peers): **[affaan-m/ECC](https://github.com/affaan-m/ECC)** (~230k★, MIT, cross-AI — Claude/Codex/
    Cursor/Gemini/Kimi/Kiro; "agent harness… skills, security, research-first dev"
    → highest-profile, PRIMARY); **[alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills)** (~22.6k★, MIT,
    multi-domain engineering + `audit/` + plugin, structured like SOTA → closest
    same-kind peer); **[PatrickJS/awesome-cursorrules](https://github.com/PatrickJS/awesome-cursorrules)** (~40.3k★, CC0, per-stack
    `.cursorrules` → the rules-library reference); tertiary
    [SebastienDegodez/copilot-instructions](https://github.com/SebastienDegodez/copilot-instructions) (~190★ but genuinely same-kind: DDD/
    clean-arch/testing rules) and [sanjeed5/awesome-cursor-rules-mdc](https://github.com/sanjeed5/awesome-cursor-rules-mdc) (~3.5k★).
  - **Popular but a *different axis*** (compare only on a workflow/quality axis, not
    build-completeness): **[garrytan/gstack](https://github.com/garrytan/gstack)** (~122k★, cross-AI — a 23-tool
    role/workflow setup, not a rules library); **`multica-ai/andrej-karpathy-
    skills`** (~192k★ but **no license** → can't legally reuse content; mostly one
    behavior CLAUDE.md).
  - **Excluded, different category:** `x1xhlol/system-prompts-and-models-of-ai-
    tools` (~142k★ leaked tool prompts); [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) (~89k★ token
    gimmick); [agentsmd/agents.md](https://github.com/agentsmd/agents.md) (the spec/website); `travisvn/awesome-claude-
    skills` (link list); [ComposioHQ/awesome-claude-skills](https://github.com/ComposioHQ/awesome-claude-skills) (~67k★ productivity).
  Fairness controls: each competitor's *best-matching* content per task (not a
  strawman), same fixed rubric + blind opus judge + token budget, record commit
  SHAs, respect licenses (skip no-license repos for pasted content), state
  format/scope caveats, **publish even if SOTA ties/loses.** Expected edge =
  freshness (SOTA primary-source-verified; competitor rules go stale) + the
  cross-cutting completeness the self-audit/principle-5 design recovers; expected
  non-edge = raw "does the code work". **Cost:** ~$16 per competitor per full
  completeness run (3-arm ≈ 1.5× the 2-arm) — one pilot fits the current ~$36
  balance; the full `affaan-m/ECC` / `alirezarezvani/claude-skills` /
  `PatrickJS/awesome-cursorrules` sweep needs a top-up. Still
  gated on the maintainer wanting a "vs X" claim at all (2026-07-12 chose the
  honest vs-unguided framing).
- **Cross-file / repo-level audit eval.** ~~Unexplored~~ **Explored 2026-07-13,
  no lift** ([`evals/results/2026-07-13/REPO-AUDIT.md`](../evals/results/2026-07-13/REPO-AUDIT.md)).
  Built the planted-vuln repo (8 defects invisible in any single file) the audit
  dimension was said to need. Result: **+0.00** on two models — when the whole
  repo fits in one context, cross-file collapses to "read it all" and recognition
  (already saturated) catches everything. The hypothesis was wrong about *why*
  audit is +0.00: the barrier is **context that exceeds what the model holds**,
  not file-spanning per se. The genuine remaining frontier is the agentic
  large-repo eval (open task 3′) — a repo too big to paste, audited under a
  context budget through tool-driven reads.

---

## Completed — 2026-07-01 audit cycle *(history)*

### Now — correctness of what's shipped

1. **Fix the audit's HIGH and MEDIUM findings.** The two HIGHs
   (sota-security-compliance frontmatter invalid under strict YAML;
   `init-gates.sh` language-detection SIGPIPE fail-open) plus the script
   silent no-ops, the denylist-check gaps, and the sota-jvm scoped-values
   correction. *(Landed in the audit-remediation PR, #37.)*
2. **Library lint gate** (extends `check-invariants.sh`): YAML-parse all
   SKILL.md frontmatters, VERSION == plugin.json == latest tag lockstep,
   README count-basis check, shellcheck over `scripts/`. Blocks the whole
   defect class the audit found. *(Landed: YAML-validity check and shellcheck
   CI job in #37; version-lockstep (check 5) and count-surface (check 6)
   invariants on 2026-07-04.)*

### Next — keep the core promise true

3. **Freshness ledger.** Per-rules-file `last-verified: YYYY-MM` metadata plus
   a scheduled CI job reporting files past their re-verify window. The README
   promises "fast-moving claims are web-verified against primary sources";
   today only ~21 of 220 rules files carry any verification date, so the
   promise is unauditable — and every "2026 baseline" assertion goes silently
   stale in 2027. *(Mechanism landed 2026-07-04 as per-file line-1 markers;
   SUPERSEDED 2026-07-09, PR #52: a full-library verification sweep
   (per-skill web research, adversarially verified, 65 fixes applied)
   replaced the per-file ledger with a single root `LAST-VERIFIED` stamp —
   the per-file backfill would have duplicated git metadata at 210-file
   scale. `check-freshness.sh` now reds when the stamp exceeds the
   12-month window; re-sweeping resets it. DONE.)*
4. **Release procedure in-repo** (`RELEASING.md` or a CONTRIBUTING section):
   VERSION + plugin.json + CHANGELOG + tag + GitHub release, plus the
   version-bearing strings in README/CLAUDE.md. Eight releases shipped in the
   first 14 days from a procedure that lives outside the repo; the v1.0.0
   pointer rot in CLAUDE.md was the predictable result. *(Landed 2026-07-02:
   [RELEASING.md](../RELEASING.md), incl. the count-bearing surfaces — the
   v1.8.0 release found the social-preview image still saying "30 skills",
   the same rot class again.)*
5. **Structured feedback intake.** `.github/ISSUE_TEMPLATE` with a
   bad-guidance report (file:line + primary source, mirroring SECURITY.md's
   format) and a skill-request template; enable Discussions. A no-telemetry
   project's only adoption signal is structured issues — currently absent.
   *(Landed 2026-07-04: both issue forms — the bad-guidance form requires a
   primary source and redirects security-sensitive reports to the private
   advisory flow — plus a contact-link config; Discussions enabled.)*

### Later — coverage decisions (decide, don't drift)

6. **Close or declare the language/domain gaps.** PHP and Ruby have no skill
   (incidental mentions only); Swift exists only at sota-mobile's
   platform/stack level, not as a language-idiom skill; Active
   Directory/Kerberos/ADCS have zero coverage despite identity and detection
   skills whose real-world audits are AD-heavy. Ship `sota-php`, `sota-ruby`,
   a Swift-language rules file, and AD content — or add a README "coverage &
   non-goals" section stating what is deliberately excluded. The mission
   statement overclaims until one of the two happens. *(Closed 2026-07-04:
   all four builds shipped — `sota-php`, `sota-ruby`, `sota-mobile` rules/07
   (Swift language), and AD/Kerberos/ADCS as `sota-identity-access` rules/07
   + `sota-detection-engineering` rules/07 — each claim web-verified against
   primary sources; the README "Coverage & non-goals" section now lists only
   true non-goals (Scala/Elixir, standalone C, platform-engineering depth).)*

## Coverage additions (post-audit, demand-driven)

- **`sota-web-frameworks`** *(shipped 2026-07-06)* — React 19/Next.js + Vue 3/Nuxt 4
  and the SSR/hydration/server-components concerns those stacks share. Previously
  only incidental coverage existed (a React section in `sota-javascript-typescript`
  rules/06; XSS-sink names in rules/05). Closes the frontend-framework gap that sat
  between the language skill (`sota-javascript-typescript`) and the design skill
  (`sota-frontend-design`) without overlapping either. 40 skills total.
- **`sota-confidential-computing`** *(shipped 2026-07-09)* — TEEs
  (SEV-SNP/TDX/ARM CCA, SGX enclaves, Nitro Enclaves, confidential GPUs),
  remote attestation (RATS RFC 9334, attest-then-release), confidential
  Kubernetes (CoCo/Kata/Trustee), and cryptographic PETs (FHE/MPC/ZKP/PSI).
  Covers the workload-from-host trust direction — the inverse of
  `sota-sandboxing`; router rule 19 encodes the boundary. Demand-driven
  (user gap-check found zero prior coverage). 41 skills total.
- **Within-skill gap closures** *(2026-07-09/10, demand-driven)* — two coverage
  gaps found by user-prompted assessments, closed as sections in
  `sota-network-security` (no new skill): **rules/05 R8.1** self-hosted /
  bare-metal L3/4 DDoS hardening (SYN cookies/synproxy, conntrack, rp_filter,
  no-open-reflector — the library assumed a scrubbing edge); **rules/06
  R12–R14** email authentication & anti-spoofing (SPF/DKIM/DMARC, MTA-STS/DANE,
  bulk-sender rules — previously only incidental SPF/DKIM mentions). Assessment
  also judged firmware/UEFI/measured-boot-as-a-discipline a real-but-niche gap,
  deliberately **not** built (partly subsumed by confidential-computing +
  kubernetes; revisit only on demand).

## Maintenance mode (de-prioritized by audit evidence)

- **Optional-extras scripts** (`statusline.sh`, `init-gates.sh`,
  `gen-agents-md.sh`): highest defect density found by the audit, and plugin
  users don't get them by default. Bug-fix only; no new extras until the
  plugin path can deliver them natively.

## Explicitly rejected (with reasons, so they aren't re-litigated)

- **History rewrite to purge the pre-2026-07 denylist names** — rejected
  2026-07-01: the names are low-sensitivity, the repo already has public
  clones/forks/archives, and a rewrite breaks every clone and all release
  tags. Going forward the list is externalized (git-ignored locally, CI
  secret) so the tree no longer discloses it.
- **Telemetry/analytics in the scripts** — privacy stance; feedback comes
  from issues (see item 5).
- **Importing an external system-design "fundamentals" guide** — assessed
  2026-07-14 (a compiled X-thread series on scaling/architecture: load
  balancing, CDN, caching layers, API gateway, CAP, sharding, replication,
  consistency, queues, fault tolerance, etc.). **No action:** it is a *secondary
  source* (can't be cited under the primary-source policy), and a topic-by-topic
  check found full coverage already — caching + stale-while-revalidate
  (`sota-performance/05`, `sota-architecture/05`), CDN/origin-lock
  (`sota-cloud-infrastructure/03 §9`), L4/L7 LB + health checks
  (`cloud-infrastructure/03 §8`, `architecture/04`), gateway-vs-mesh N-S/E-W
  (`sota-network-security`), rate limiting (router principle 5), and the
  distributed-systems topics across `sota-architecture/03,05` + `sota-databases`.
  Only marginal non-coverage: enumerating LB *algorithms* (deliberately subsumed
  by the "use managed LBs + meaningful health checks" stance) and back-of-envelope
  capacity estimation (an interview skill, not a BUILD/AUDIT rule — a non-goal).
