# The language tier — what is aligned, what is not, and how to add one

The nine language skills (`sota-rust`, `sota-golang`, `sota-c-cpp`, `sota-jvm`,
`sota-python`, `sota-javascript-typescript`, `sota-dotnet`, `sota-php`, `sota-ruby`) share
a spine and diverge deliberately. This file records which is which, so that a real gap gets
closed and a principled difference does not get "fixed".

`sota-shell-scripting` is grouped with the languages in the router's families but is **not
a peer** of this tier: 9 files with a different spine (safety baseline, robustness, ad-hoc
commands, PowerShell). Nothing here applies to it.

The live picture is **page 5 of [`skill-map.drawio`](skill-map.drawio)**, generated from
the tree by `scripts/gen-skill-map.py`. The numbers below were measured 2026-09-21 and will
drift; regenerate rather than trusting them.

## The spine

| Section | Status |
|---|---|
| Idioms / language baseline | **universal** — all 9 |
| Security | **universal** — all 9 (PHP splits it across three files) |
| Performance | **universal** — all 9 |
| Tooling / CI / supply chain | **universal** — all 9 |
| Testing | **universal**, but usually *inside* the tooling file; only Python and JS/TS give it one of its own |
| Concurrency | **universal in substance** — 7 dedicated files, Ruby merges it with performance, PHP carries it as `01 §6 "Fibers and concurrency"` |
| API / design | **NOT universal — this is the one real gap.** See item 57 |

## What is deliberately NOT aligned

These track a property of the language. Adding the missing cells would be writing filler.

- **Errors** gets a dedicated file only in **Rust and Go** — the two with a distinctive
  error *model* (`Result`/panic, explicit error values). Everywhere else exceptions are
  conventional and the topic is covered inside the idioms file (Python `03 §10 "Exception
  design"`, Ruby `01 §5`, PHP `01 §5`, JS/TS `02 "Error handling"`). **The concept is
  covered in all nine; only the file is Rust/Go-specific.**
- **Typing** only in **Python and JS/TS**, the two gradual-typing languages. A statically
  typed language does not need a chapter on adding types.
- **Memory / UB** only in **C/C++** (two files) and **Rust** (`unsafe` discipline).
  Measured: 14 and 6 mentions of use-after-free / UB / bounds against ~0 in the GC'd
  languages. Correct, not a gap.
- **Web / HTTP** only where the language is web-shaped — **Go, Node, PHP, Ruby**.

The general rule: **the shared skill owns the concept, the language skill owns the
mechanism.** `sota-async-concurrency` (1,654 lines) teaches data race vs race condition,
deadlock, primitives, backpressure and cancellation once. `sota-golang/rules/03` then says
`go test -race`, that loop-variable capture was fixed in **Go 1.22 and only if `go.mod`
says ≥1.22**, and that a concurrent map write is an unrecoverable `fatal error`. None of
that is expressible generically, and none of the generic material is restated there. A
topic appearing in both is not duplication — check the content before assuming it is.

## The alignment plan

Two items, both tracked in [ROADMAP.md](ROADMAP.md). Neither is urgent.

### Item 57 — API / design is missing in three languages

Dedicated file in **rust, go, jvm, .NET**. Absent in **js/ts, php, ruby**,
and thin where adjacent rules touch it (3–9 keyword mentions; JS/TS has "Functions and
modules over classes", Ruby has "Data vs Struct", and that is close to all of it).

This is a genuine gap rather than a principled difference, because designing a public
surface — a package, gem, crate or library — is language-inflected work that every one of
these languages does:

| | what the missing section would own |
|---|---|
| ~~python~~ | **CLOSED 2026-09-21 (#416)** — `rules/03` §13 *Public API surface*: `__all__`, keyword-only parameters, `__slots__` as directional, `@deprecated` (PEP 702), what a leading underscore does not promise |
| js/ts | the `exports` map, type-level public surface vs runtime, `default` vs named, what a breaking type change is |
| php | `final` and `readonly` as API decisions, interface vs abstract, BC breaks under semver |
| ruby | gem semver, `private_constant`, refinements, what `respond_to?` promises callers |
| ~~c/c++~~ | **CLOSED 2026-09-21** — `rules/01` §9 *Designing a public surface*: the source-compatible-but-ABI-breaking table (added member, first virtual, reorder, default argument, inline body), `pimpl` with the incomplete-type destructor trap, stdlib types in exported signatures (libstdc++'s two ABIs since **GCC 5.1**, `_GLIBCXX_USE_CXX11_ABI`, verified against GCC's docs), and header hygiene |

**First move:** write one section for the language you are already in, not three at once.
Each needs an `## Audit checklist` item and an ADOPTION-LOG row (invariant 31), and each
lands in the existing idioms file unless it pushes it past 500 lines.

**Verification:** the section is not done until an auditor walking that skill's checklist
would be prompted for it. That is the `state`/CSRF lesson — content that exists but is
never reached by the checklist is not reachable in AUDIT mode.

### Item 58 — jvm/.NET depth: the framing was refuted, the recommendation is to close

**This section previously said jvm and .NET were "3–4× thinner than their peers". Measured
2026-09-21, that was true of line count and false of what line count was standing in for.**

Per 100 rules-lines, counting actionable audit items and worked examples:

| skill | rules lines | audit items | items/100 | examples/100 |
|---|---|---|---|---|
| dotnet | 564 | 60 | **10.6** | 1.1 |
| jvm | 619 | 65 | **10.5** | 1.0 |
| ruby | 1053 | 85 | 8.1 | 1.3 |
| c/c++ | 910 | 72 | 7.9 | 1.4 |
| php | 1118 | 85 | 7.6 | 2.7 |
| python | 1986 | 138 | 6.9 | 3.3 |
| golang | 2128 | 140 | 6.6 | 2.9 |
| js/ts | 1729 | 104 | 6.0 | 3.8 |
| rust | 2057 | 94 | 4.6 | 1.8 |

**jvm and .NET carry the highest audit-item density in the library.** The bounded deficit is
**worked examples** (1.0–1.1 per 100 lines against 2.7–3.8 at the top). Structurally they are
**one compact template applied twice** — identical six-file layout, same order, near-identical
names — so it was never two independently thin skills.

**Caveat, published with the number:** the checkbox and shell-block checklist formats are not
comparable on this metric. A `- [ ]` item can bundle several commands; a fenced block counts
per line. The jvm/.NET-vs-peers comparison is within-format and sound; rust's last place is
not evidence of anything.

**CLOSED 2026-09-21 as (c)** — the depth is correct and the framing was wrong. Splitting `sota-jvm` is rejected — it adds a skill, moves
the description classifier and competes for every neighbour's traffic, to fix a deficit the
measurement says is not there. Worked examples for jvm/.NET remain optional polish.

## Structural audit of the nine SKILL.md files (2026-09-21)

**No gap.** All nine carry the same five sections — Purpose, BUILD mode, AUDIT mode, Rules
index, Top-10 non-negotiables — and each Top-10 has exactly ten items.
`sota-javascript-typescript` is uniformly *compressed* (70 lines vs 115–160), not incomplete;
its only deviations are cosmetic: the title omits `(2026)`, the BUILD/AUDIT headings carry
parentheticals nobody else uses, and it writes `Top 10` where the rest write `Top-10`.

### Two things deliberately NOT aligned, with the reason

- **Rules filenames.** The same topic is variously `07-tooling-ci`, `06-build-tooling-ci`,
  `01-tooling-project-setup`, `07-testing-and-tooling`, `05-composer-tooling`,
  `04-supply-chain-tooling`. **Do not rename:** 390 citations name the descriptive filename
  (`rules/NN-name.md`) against 2,945 that use the number alone, and the router's library map
  carries numbers plus prose rather than filenames, so it will not help you find them. The
  cost is real; the benefit is aesthetic.
- **Numbering order.** rust opens with ownership, go with errors, python with tooling.
  Renumbering breaks the `rules/NN` form that carries the other 2,945 citations. Leave it.

### One thing that IS worth deciding — the audit-checklist body format

Invariant 2 gates the *heading*; nothing gates the body, and three forms exist:

| form | skills |
|---|---|
| tickable `- [ ]` | rust, js/ts |
| fenced shell block | python, jvm, .NET, c/c++, php |
| prose + commands | golang, ruby |

AUDIT mode tells the model to "verify your diff satisfies every item" — a checkbox list is
enumerable, a prose block is not. **That is an inference from the wording, not a
measurement**, and unifying is a rewrite of seven skills, so it is **DEFERRED** in the
ADOPTION-LOG with an explicit trigger: a measurement showing the format changes audit
behaviour, or a third instance of a reader unable to enumerate a checklist.

## Depth: the concept matrix (item granularity)

The spine table above is **file** granularity, which is what found ROADMAP 57. It is
structurally blind to a concept missing *inside* a file that exists — and that is where two
of 2026-09-21's findings lived. `scripts/gen-concept-matrix.py` reads every Audit-checklist
item in the tier and reports **concept x language presence**.

Run it: `python3 scripts/gen-concept-matrix.py [--show-unmatched N]`.

**What it is, exactly: a candidate generator with a measured error rate — not a gap list.**
It classifies by declared matchers over item text, and a matcher answers *"does this wording
appear"*, never *"is this idea covered"*. Measured on the first pass, **3 of the 4 candidates
checked by opening the file were vocabulary artefacts**, not gaps:

| candidate | verdict on reading the file |
|---|---|
| SQL injection absent in php | **false** — `02-injection.md` says *"SQL built from strings"*, `whereRaw`, `EMULATE_PREPARES`; the matcher wanted the literal "sql injection" |
| deserialization absent in rust | **false** — 6 hits for serde/untrusted across four checklists; the matcher lacked `serde` |
| linter suppression absent in rust | **false** — `rules/07` probes `rg '#!\[allow'`; the matcher wanted `#[allow` and the text writes `#![allow` |
| linter suppression absent in jvm/.NET/c-cpp | **TRUE** — confirmed absent from every checklist in all three |

So: **open the file for every candidate**, and when a candidate dies, fix the *matcher* in the
same change — the vocabulary is the thing being built. Each pass prints a classification
denominator per skill (currently 67–93% for the tier, 60% for shell); the unclassified
remainder is a hole in the matcher vocabulary, not evidence about the skills, and
`--show-unmatched` lists it so the next pass can close it.

**`sota-shell-scripting` is reported as its own group**, never a tenth column — the tier's
spine does not apply to it, and mixing them manufactures gaps that are only a difference in
kind.

### Triage ledger — candidates opened, and what they turned out to be

**A candidate dies by being read, and the verdict is recorded so nobody re-derives it.**
First pass, 2026-09-22. Of 11 cells opened, **2 were real**, **6 were vocabulary artefacts**
and **3 were a principled delegation**:

| candidate | verdict | evidence |
|---|---|---|
| jvm — path traversal | **REAL, closed** | the BUILD rule existed at `rules/04:86` (*"canonicalize and verify the result stays under an allowed root"*) with **no probe anywhere in the skill**. Probe added, plus zip slip |
| js/ts — SQL injection | **REAL, closed** | `rules/05:178` says *"never interpolate into SQL"*; the checklist had no SQL probe at all. Probe added, incl. `$queryRaw` vs `$queryRawUnsafe` |
| js/ts, .NET — command injection | artefact | both probe it (`child_process`/`execSync`; `Process.Start`) — matcher lacked those terms |
| rust, jvm — SQL injection | artefact | jvm probes `prepareStatement`/`createQuery`. **The matcher said `prepared`, which never matches `prepareStatement`** — prepare+statement has no `d` |
| js/ts, .NET — path traversal | artefact | `path.join`/`Path.Combine`; .NET's heading is *"XXE / command / path"* |
| rust, js/ts, c/c++ — TLS | **delegation, not a gap** | router cross-cutting rule 18 puts transport/PKI in `sota-network-security` rules/06. Concept reclassified `conditional` so it stops being reported |

**The dominant real-gap shape is "the rule is stated, the probe is missing"** — both survivors
were that, and neither is visible to a file-level view or to a reader of the prose. It is the
same shape as the `$?` and suppression findings, which is now three independent instances.

**And the matcher is part of the artefact.** Every dead candidate above was fixed in the
vocabulary in the same change, which is why the candidate list shrinks as it is worked rather
than staying constant — the list is a queue, not a scoreboard.

**Not yet triaged** (the remaining cells, for the next pass): backpressure, deserialization,
authn/authz, resource lifecycle, supply-chain provenance, allocation/GC, version floor, module
boundaries, DoS guards, plus `public API surface — go`, `cancellation — c/c++`, and ruby's
task-leak and profiling cells.

### Verified gap: nobody probes the linter's escape hatch in jvm, .NET or c/c++

Six of nine languages probe *"someone silenced the analyser"* — rust (`#![allow]` without a
reason), go, python, js/ts (`@ts-ignore`), php, ruby. Three do not, and each has a prominent
mechanism its checklist never asks about:

| skill | the un-probed escape hatch |
|---|---|
| jvm | `@SuppressWarnings`, SpotBugs `@SuppressFBWarnings`, `// NOSONAR` |
| .NET | `#pragma warning disable`, `[SuppressMessage]`, `<NoWarn>` in the csproj, `.editorconfig` severity=none |
| c/c++ | `// NOLINT` / `// NOLINTNEXTLINE`, `cppcheck-suppress`, `#pragma GCC diagnostic ignored` |

This is the **same shape** as the `$?` finding the same day: a rule present for some members
of a family and absent for its neighbours, invisible to every file-level view because all
three skills *have* a tooling file. It matters because a suppression is how a green gate
stops meaning anything — `sota-code-security` rules/10's subject, one layer down.

## Depth: the external-guide gap-check (ROADMAP 59)

Coverage inside this tier is checked against an **external, enumerable, tool-backed list** —
the method already used for Go (OWASP Go-SCP) and Rust (ANSSI). Two are done:

| language | denominator | source | result |
|---|---|---|---|
| python | **75 tests** | Bandit 1.9.4 `plugins_by_id` + `blacklist_by_id` | 5 gaps closed |
| golang | **61 checks** | gosec 2.29.0 `rulelist.go` (39) + `analyzerslist.go` (22) | 4 gaps closed |

Remaining: **rust, c-cpp, jvm, javascript-typescript, dotnet, php, ruby**. Candidate
denominators — ruby/Brakeman, js-ts/eslint-plugin-security, rust/clippy + ANSSI.
**jvm and .NET have no queryable local tool**, which may itself be the finding rather than a
reason to skip them.

**c-cpp's denominator is already derived and reconciled — 2026-09-21, so the next session on
this language starts past the step that failed twice.** cppcheck **2.21.0**:

| derivation | method | answer |
|---|---|---|
| A | `cppcheck --errorlist` → unique `id="…"` | **342** |
| B | the same dump grouped by `severity=` | **342** — warning 110, style 95, error 93, portability 20, performance 19, information 5 |

The two agree exactly, and the severity buckets sum to the total, which is what makes this a
reconciliation rather than one number counted twice. **And the gosec two-registry lesson
repeats**: cppcheck's **addons are a separate list** the `--errorlist` dump does not contain —
`misra.py` alone carries **132** `misra_N_M` rule functions, plus `threadsafety.py`,
`y2038.py`, `naming.py` and `findcasts.py`. A denominator of 342 is the *built-in* checks
only; MISRA is a second registry this skill already delegates to by name. **342 is 4.5× the
Python set**, so budget the cluster-sweep accordingly — that size is the reason the sweep was
not attempted in the same session that derived the number.

### The step that failed both times: the denominator

**Derive it twice, from independent sources, and reconcile before sweeping.** A single source
was wrong in both languages, and both times the error hid the interesting half:

- **Bandit's docs page** returned ~50 tests with B3xx/B4xx missing and B324 misfiled. The
  tool's own registry gave 75.
- **gosec** took four attempts: `strings` on the binary said 61 and was *dismissed as false
  positives*; the docs index gave 7; a summarised fetch 38; a local parse of `rulelist.go` 39.
  The truth is **two registries** — `rulelist.go` (39) plus `analyzers/analyzerslist.go` (22)
  — and the half missing from the single-file answer contained every taint-analysis check and
  the entire modern HTTP set, **which is where the gaps were**. The skill under audit is what
  exposed it, by citing rule IDs the denominator did not contain.

An *incomplete* denominator causes missed gaps, never false ones — so a sweep is still worth
running — but it cannot support a claim of completeness.

### The two rules that stop false findings

- **Open the file for every zero.** Grep answers "does this string appear", never "is this
  idea covered". In Python, 2 of 8 candidate gaps died on reading (`exec`/`eval` and XXE are
  both covered; the counts were regex artifacts) and a third was scoped down because Django's
  `DEBUG=False` was already there.
- **Run every shipped checklist grep against a known-bad AND a known-good fixture.** A check
  that could never fire shipped twice — `grep -Lq` (where `-q` suppresses the output `-L`
  exists to produce) and a `[^,]+` that cannot span the second comma of a three-argument call.
  Neither was caught by review.

### An open question this raised

**Temp-file/permission hygiene and host-key verification were gaps in *both* Python and Go.**
If that repeats in Ruby and PHP, the right fix is probably a class stated once in
`sota-code-security` with per-language *detectors*, not the same section written nine times —
the split this library already uses for in-band sentinels. Decide it before the fourth
language, not after the ninth.

## Template — adding a new language skill

Copy the spine, not another language's file list. Sections marked **conditional** are
included only if the trigger applies; an empty section is worse than an absent one.

```
skills/sota-<language>/
  SKILL.md                     two-field frontmatter, BUILD/AUDIT, top-10, rules index
  rules/01-idioms.md           REQUIRED  version baseline + support window, idioms, pitfalls
  rules/02-design-api.md       REQUIRED  public surface, naming, immutability, deprecation
  rules/0N-concurrency.md      REQUIRED  dedicated file, or a named section in 01
  rules/0N-security.md         REQUIRED  injection, deserialization, crypto APIs, authn
  rules/0N-performance.md      REQUIRED  profiling entry point, allocation, runtime tuning
  rules/0N-tooling-ci.md       REQUIRED  build, lockfile, supply chain, linters, CI gates
  rules/0N-errors.md           conditional — only if the error MODEL is distinctive
  rules/0N-typing.md           conditional — only if typing is gradual/optional
  rules/0N-memory.md           conditional — only if memory is manual
  rules/0N-web.md              conditional — only if the language is web-shaped
```

Testing may live in the tooling file; it must exist somewhere either way.

**Write mechanism, not concept.** Before adding a rule, ask whether
`sota-async-concurrency`, `sota-code-security`, `sota-testing` or `sota-performance`
already owns the idea. If it does, the language file says what *this runtime* does
differently — the API, the version gate, the tool invocation, the failure mode — and
cross-references the owner. A language file that restates a generic rule is the duplication
this tier is designed to avoid.

### The gates a new language skill must satisfy

All of these are enforced; the numbers are `scripts/check-invariants.sh` check numbers.

- **1** — every `skills/**` file ≤ 500 lines.
- **2** — every `rules/*.md` ends with exactly one `## Audit checklist`.
- **4** — the `description` is ≤ 1024 characters. It is the **entire** auto-load
  classifier; the body is inert until the Skill tool fires. Give it trigger keywords and a
  `Not for X — use Y` cross-ref to its nearest sibling.
- **7** — the router's routing table lists the skill.
- **10** — every `rules/NN` file is indexed by its own `SKILL.md`.
- **15** — the router's library map (`skills/sota/rules/04`) lists every rules file.
- **22** — no `- [ ]` bullet stranded inside a code fence.
- **31** — every new `##` rule section ships with an ADOPTION-LOG entry.
- **29** — a *release* that adds a description must declare a routing check, and since
  2026-09-20 that artifact must post-date the change.

Two more that are not invariants but will abort or mislead:

- `scripts/gen-skill-map.py` holds `FAMILIES` **and** `LANG_TOPICS`. A new skill that is
  not in both aborts the generator naming the difference — update them in the same change.
- **A new description competes for every existing skill's traffic.** Adding one is exactly
  the event invariant 29 exists for: `sota-skill-security` (v1.35.0) took a case from
  **3/3 to 0/3** and shipped, with invariants 4, 7 and 15 all green. Run
  `scripts/routing-baseline.sh` before and after, and add a case to
  `evals/cases/desc-routing.jsonl` if the new skill has a confusable sibling.
