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
| Security | **universal** — all 9 (PHP splits it across three files; jvm carries XML in its own `rules/07` since 2026-09-25, split out of `rules/04` when the OWASP adoption would have taken that file past the cap — a size split, not a principled difference; likewise since the same day, golang and python carry supply chain in `rules/08`, rust carries `std::process::Command` in `rules/08`, and js/ts carries child processes and SSRF in `rules/08` — all four split out of a security file the OWASP adoption had filled to the cap; and jvm's web layer moved from `rules/04` §6 to `rules/08` §1 later that day, for the same reason) |
| Performance | **universal** — all 9 |
| Tooling / CI / supply chain | **universal** — all 9 |
| Testing | **universal**, but usually *inside* the tooling file; only Python and JS/TS give it one of its own |
| Concurrency | **universal in substance** — 7 dedicated files, Ruby merges it with performance, PHP carries it as `01 §6 "Fibers and concurrency"` |
| API / design | **universal since 2026-09-22** (item 57) — a dedicated file in 4, a section in 5. Pinned at 9/9 by `--assert-universal` |
| Request-scoped context cleanup | **conditional** — 8 of 9 since 2026-09-25 (ROADMAP 66). **Go is a principled absence:** goroutines have no thread-local, goroutine-local or async-local storage by design (Go FAQ), so per-request state travels in an explicit `context.Context` that cannot outlive its request. Do not "fix" Go by adding a section |

## Blank cells on page 5 — triaged 2026-09-22

The map's blanks were read as gaps. **Most were a declaration gap in the map, not a coverage
gap in the library**, and the legend made it worse by defining BLANK as *"no dedicated
treatment"*. Every blank was checked by reading the headings of the skill behind it:

| row | blanks | had a real section (map was wrong) | principled |
|---|---|---|---|
| **Errors** | 7 | **all 7** — c/c++ `01 §7`, jvm `01 §4`, python `03 §10`, js/ts `02 §Error handling`, .NET `02 §4`, php `01 §5`, ruby `01 §5` | 0 |
| **Typing** | 7 | 2 — c/c++ `01 §6`, ruby `01 §6` | 5 — statically-typed languages have no gradual-typing story. **SUPERSEDED 2026-09-23:** by the row's own definition (c/c++ counts "type-system leverage"), rust `01 §3–4`, jvm `02 §1` and go `02 §5` were sections too, so 3 of these 5 were declaration gaps |
| **Web / HTTP** | 5 | 2 — .NET `04 §4`, python `07 §1–2` (named by framework: FastAPI, Django) | 3 — rust, c/c++, jvm carry no web layer. **jvm was a real gap, not principled: written 2026-09-23 as `rules/04 §6` (ROADMAP 62); moved to `rules/08` §1 on 2026-09-25.** **rust also had one**, `05 §7` service-edge defaults (axum/tower), declared the same day. Only **c/c++** is principled, and the map now shows it as `n/a` with that reason |
| **Memory / UB** | 7 | 0 | 7 — the GC languages' "Memory" sections are *performance* (allocation, GC pressure) and are already counted under Performance. **SUPERSEDED 2026-09-23:** go had a section (`05 §7`, unsafe and cgo), and the other six had a real gap, **their escape hatches into raw memory**, now written under one shared class (`sota-code-security` rules/06 §3) plus a section in each |

**The Errors row was the loud one**: seven of seven blank, while `error handling &
propagation` sits in `UNIVERSAL_FLOOR` at **9/9**. Two instruments were making contradictory
claims about the same fact and nothing compared them — the identical defect as API/design, one
row up, found the same way: by someone looking at the rendered picture.

**Deliberately NOT declared: go's Memory/UB.** `sota-golang` `05 §7` covers `unsafe`/cgo
policy, which is memory-safety adjacent — but a one-section "don't use `unsafe`" policy in a
GC language is not the same topic as rust's and c/c++'s memory-safety treatment, and
declaring it would imply a parity that does not exist. Left blank on purpose; recorded here so
the next reader does not "fix" it.

**`Errors` is now in `TOPIC_CONCEPT`**, so the cross-check guards it. It was left out on the
first pass as "no 1:1 concept", which was too hasty.

## What is deliberately NOT aligned

These track a property of the language. Adding the missing cells would be writing filler.

- **Errors** gets a dedicated file only in **Rust and Go** — the two with a distinctive
  error *model* (`Result`/panic, explicit error values). Everywhere else exceptions are
  conventional and the topic is covered inside the idioms file (Python `03 §10 "Exception
  design"`, Ruby `01 §5`, PHP `01 §5`, JS/TS `02 "Error handling"`). **The concept is
  covered in all nine; only the file is Rust/Go-specific.**
- **Typing** only in **Python and JS/TS**, the two gradual-typing languages. A statically
  typed language does not need a chapter on adding types. *(Superseded 2026-09-23: the row
  counts type-system leverage too, and rust, jvm and go each have such a chapter. Page 5 now
  has no blank cells; the only `n/a` is c/c++ Web/HTTP, and the generator refuses to draw an
  unexplained blank.)*
- **Memory / UB** only in **C/C++** (two files) and **Rust** (`unsafe` discipline).
  Measured: 14 and 6 mentions of use-after-free / UB / bounds against ~0 in the GC'd
  languages. Correct, not a gap. **CORRECTED 2026-09-23: it was a gap.** Counting UB
  *vocabulary* measured the wrong thing. Every GC language has an escape hatch into raw
  memory (JNI/FFM/`Unsafe`, `ctypes`, `Buffer.allocUnsafe` and native addons,
  `unsafe`/P/Invoke, PHP FFI, Fiddle), and only go covered its own. They are now stated once
  in `sota-code-security` rules/06 §3 with per-language detectors, and each skill has a
  section (jvm `04 §7`, python `05 §11`, js/ts `05`, .NET `04 §6`, php `03 §6`, ruby `02 §8`).
- **Web / HTTP** only where the language is web-shaped — **Go, Node, PHP, Ruby**, plus .NET and
  python (row above) and, since 2026-09-23, **jvm** (`rules/04 §6`, ROADMAP 62).

The general rule: **the shared skill owns the concept, the language skill owns the
mechanism.** `sota-async-concurrency` (1,654 lines) teaches data race vs race condition,
deadlock, primitives, backpressure and cancellation once. `sota-golang/rules/03` then says
`go test -race`, that loop-variable capture was fixed in **Go 1.22 and only if `go.mod`
says ≥1.22**, and that a concurrent map write is an unrecoverable `fatal error`. None of
that is expressible generically, and none of the generic material is restated there. A
topic appearing in both is not duplication — check the content before assuming it is.

## The alignment plan

Two items, both tracked in [ROADMAP.md](ROADMAP.md). Neither is urgent.

### Item 57 — CLOSED 2026-09-22. API / design now present in all nine

Dedicated file in **rust, go, jvm, .NET**; a section inside the idioms file in **python, c/c++, js/ts, php, ruby**. Formerly absent in the latter five,
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

### The audit-checklist body format — RESOLVED 2026-09-23

Invariant 2 gates the *heading*; the body was ungated and three forms were in use. **All nine
language skills now use the tickable `- [ ]` form**, and
`gen-concept-matrix.py --assert-format` runs in CI so a fenced checklist cannot come back.
**Widened later on 2026-09-23 to every skill:** the gate now reads all 275 rules files across
42 skill directories, per file, and also fails a checklist that yields **zero** items. That
second arm exists because three `sota-architecture` files used plain `- ` bullets, which
the language-only gate read as a pass. Watched to fail on the pre-change tree (17 of 275
files) before the conversion made it pass.

AUDIT mode tells the model to "verify your diff satisfies every item" — an instruction that
cannot be followed against a shell block. The deferral asked for a measurement or a third
unenumerable-checklist instance; the operator adopted it on two: a `- []`-only count returned
**0 for seven of nine** skills, and a concept-matrix pass mis-parsed fenced blocks and
reported `sota-golang` as lacking API/design probes its `02-design.md` plainly has.

**Correction to the old table, which classified golang and ruby as "prose + commands":** that
was never measured. Reading their checklists with `scripts/lib/extract_items.py` showed both
were **fenced**, like python/jvm/.NET/c-cpp/php — seven fenced skills, not five.

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

**Where this queue lives: ROADMAP item 59** (operator decision, 2026-09-24). Until then it had
no row and no trigger, so "for the next pass" named no pass. Each language's gap-check triages
that language's cells here. The cells of languages already checked (go, c/c++ and ruby above,
plus any python cells) are triaged in the pass that closes 59, so the rows that are already done
do not orphan them. Reasoning: a candidate cell is not evidence until its file is opened, and a
gap-check is where the file gets opened anyway. A separate row would compete with 59 for the
same sessions.

**Second pass, 2026-09-24: the already-checked languages (go, c/c++, python, ruby).** Of 13
cells opened, **3 were real**, **7 were vocabulary artefacts** and **3 were delegated or
covered as a class**. The two cells named above for go (public API surface) and ruby
(profiling) were already matched by the time this pass ran.

| candidate | verdict | evidence |
|---|---|---|
| c/c++: SQL injection | **REAL, closed** | `rules/04` §3 stated the rule; no checklist item probed it. The whole-statement C APIs (`sqlite3_exec`, `PQexec`, `mysql_real_query`) and SQLite's `%s` vs `%q` are now named and probed, each from the vendor's own page |
| c/c++: authn/authz | **REAL, closed** | privilege relinquishment was in 0 files library-wide. New `rules/04` §7: order (CERT POS36-C), checked returns (Linux `setuid(2)`), a permanent drop proven by `setuid(0)` failing (POS37-C) |
| python: supply-chain provenance | **REAL, closed** | `rules/05` §9 stated Trusted Publishing and PEP 740; no probe. Probe added for token env vars and the publish action's `password`/`attestations: false`, read from the action's own `action.yml` |
| c/c++: cancellation | artefact | the `std::thread` without `jthread` probe *is* the cancellation probe (`jthread` carries a `stop_token`) |
| c/c++: module boundaries | artefact | the §9 public-surface probe covers `using namespace` in headers, include guards and `-fvisibility` |
| c/c++: version floor | artefact | `rules/06` probes `CXX_STANDARD` ("standard pinned?") |
| go: version floor | artefact | `rules/03` and `rules/07` probe the go.mod `go`/`toolchain` directives |
| go: DoS guards | artefact | `rules/04` probes `MaxBytesReader` and the four server timeouts |
| python: allocation/GC | artefact | `rules/03` probes `__slots__` |
| ruby: task/thread leaks | artefact | `rules/05` probes `Thread.new` without `join` |
| c/c++: backpressure | delegation | no standard queue abstraction; bounding queues is `sota-async-concurrency`'s, language-agnostic |
| c/c++: deserialization | covered as a class | no generic object deserializer; untrusted parsing is `rules/04` §2 (cap embedded lengths, fuzz the parser) plus the fuzzing probe in `rules/06` |
| c/c++: DoS guards | covered as a class | `rules/04` §2's bounds rule, and `sota-code-security` rules/06 §4–§5, which is written C-first |

Every artefact's vocabulary was fixed in `gen-concept-matrix.py` in the same change. After the
fix, the only candidates left for these four languages are the three rows marked delegation
or class.

**Third pass, 2026-09-24: the queue closes.** Of 17 cells opened, **12 were real**, **2 were
vocabulary artefacts** and **3 were delegated**. After it, every remaining candidate row is a
recorded delegation or class.

| candidate | verdict | evidence |
|---|---|---|
| logging: jvm, python, .NET | **REAL, closed** | the rule was stated (jvm rules/04 §5, python rules/03 §11 and rules/05, .NET rules/04 §4); no probe. Probes now cover log calls, record/dataclass string forms, and EF Core `EnableSensitiveDataLogging` |
| logging: ruby | **REAL, closed** | no rule anywhere; rules/03 §8 now covers `Data`/`Struct#inspect` and `filter_parameters` |
| logging: php | artefact | rules/04 §5a probes `#[\SensitiveParameter]`. The stated log-injection rule (rules/02 §4) was also unprobed; closed |
| date/time: rust, go, c/c++, jvm, .NET | **REAL, closed** | zero clock rules in all five. Monotonic vs wall clock, plus each language's trap: `SystemTime` `Err`, `time.Time ==`, `localtime` static buffer, `LocalDateTime` as an instant, `DateTime.Now` |
| N+1: .NET | **REAL, closed** | rules/01 pointed at a rule that did not exist; EF Core lazy loading is now rules/05 §4 |
| N+1: js/ts | quadratic half **REAL, closed**; N+1 half delegation | spread-accumulator `reduce` stated at rules/02, unprobed |
| resource lifecycle: js/ts | **REAL, closed** | `finally`/`await using` rule at rules/02–03, now probed |
| N+1: go | artefact | rules/06 probes `O(n²)` string concatenation; the matcher lacked `²` |
| N+1: c/c++, jvm | delegation | `sota-databases` rules/03 (Hibernate) and `sota-performance` rules/02 (JPA fetch joins) own it, with probes |
| module boundaries: php | delegation | no language-level visibility; `sota-architecture` rules/01 §2 names deptrac and probes enforcement |

**The matcher also reports false presences**, which no candidate row can show. Six were
found while tracing matches: c/c++ logging (`slog` in `syslog`), rust N+1 (`n+1` in a `find`
command), php date/time (`clock` in "wall-clock bound"), and .NET and ruby module boundaries
(`import` inside `DllImport` and inside a Python one-liner). They are untriaged. A present
cell is a candidate too.

**Fourth pass, 2026-09-24: the false presences.** The third pass traced six present cells to
a substring accident. This pass printed the substring behind **every** present cell
(`--explain all all`) and tightened the matcher; 28 cells went absent. **17 were real** and are
closed, **7 were artefacts** (their real probe added to the vocabulary), **4 are delegated or
a class**. Two of the accidents sat under pinned floor concepts (c/c++ vulnerability scanning
and input validation), so `--assert-universal` was passing on a false 9/9. After the pass the
floor holds 24 concepts, each cell's substring read by hand.

| candidate (the accident) | verdict | evidence |
|---|---|---|
| c/c++ logging (`syslog`) | **REAL, closed** | no rule; rules/04 §3 bullet + probe (CWE-117, secrets to `syslog`/`fprintf(stderr)`) |
| c/c++ vuln scanning, provenance ("safety-standard", "size provenance") | **REAL, closed** | rules/06 §5 stated both; probe: `URL` without `URL_HASH`, non-commit `GIT_TAG`, no CVE/SBOM step |
| c/c++ input validation ("invalidation", `-fsanitize`) | **REAL, closed** | rules/04 §2 stated it; probe: bounds check as `assert`, embedded length into `memcpy`/`malloc` |
| python data race, XSS, authn, backpressure, numeric | **REAL, closed** | rules/01 §8, 05 §1, 05 §7a, 04 §9, 03 §12 stated each; probes added |
| jvm numeric ("concurrency") | **REAL, closed** | no rule; rules/01 §1 `BigDecimal` bullet + probe |
| php date/time ("wall-clock bound") | **REAL, closed** | rules/01 §5 stated it; probe added |
| ruby resource lifecycle, backpressure | **REAL, closed** | no rule; rules/01 §7 block form, rules/05 §2 `SizedQueue` |
| ruby module boundaries, profiling | **REAL, closed** | rules/01 §7, rules/05 §8 stated them; probes added |
| .NET module boundaries (`DllImport`) | **REAL, closed** | rules/02 §6 stated it; `InternalsVisibleTo` probe |
| js/ts provenance ("published package") | **REAL, closed** | rules/05 npm supply chain stated it; token/trusted-publishing probe |
| php absence; python, js/ts version floor; js/ts data race, allocation; go provenance, input validation | artefact | strpos truthiness; `requires-python`; `engines.node`; check-then-act; unbounded `Map`; `GOSUMDB`; `MaxBytesReader` |
| rust N+1 (`n=$((n+1))`) | delegation | `sota-performance` rules/02 §1–§2, as for c/c++ and jvm |
| php task leaks, backpressure, provenance | delegation / class | FPM shared-nothing; `pm.max_children` probe; install-time-code probe |

`numeric precision & money` remains 3/9 and is not triaged for rust, go, c/c++, .NET, php
and ruby. It is never listed as a candidate because six languages miss it, and the matcher
lists a universal concept only when five or fewer do. A count over all 32 universal rows found
it is the only concept hidden that way today. Tracked as **ROADMAP 65**.

**Fifth pass, 2026-09-24: the absence the matcher could not list (ROADMAP 65).** The matcher
listed a universal concept only when five or fewer languages lacked it, with no recorded
reason, so `numeric precision & money` sat at 3/9 invisible. It now prints every absence:
CANDIDATE GAPS for 1-5 missing, MOSTLY ABSENT for 6-9 ("either a real class-wide gap or a
concept that is not universal; triage decides"). Its first run listed one concept. Of 6 cells
opened, **6 were real**; none was an artefact or a delegation. The concept is pinned in the
floor, which then held 25 (29 since 2026-09-25, when ROADMAP 66 step 3a pinned four more).

| candidate | verdict | evidence |
|---|---|---|
| rust numeric | **REAL, closed** | `Cents(u64)` shown as an API example, never stated; rules/01 §3 bullet + probe (`as` truncates and saturates: `(19.99*100.0) as i64` is 1998) |
| go numeric | **REAL, closed** | rules/05 §1 stated JSON-to-`float64` loss, unprobed; §5 money bullet; probe incl. `map[string]any` without `UseNumber` |
| c/c++ numeric | **REAL, closed** | no rule; rules/03 §2: float-to-int truncates and is UB out of range ([conv.fpint], C11 6.3.1.4, UBSan); `llround`, not a cast |
| .NET numeric | **REAL, closed** | no rule; rules/01 §1: `decimal`, `Math.Round` defaults to ToEven, `(decimal)double` keeps 15 digits |
| php numeric | **REAL, closed** | int-minor-units `Money` shown, never stated; rules/01 §4: truncating casts, `bcmath.scale` 0, `BcMath\Number`/`RoundingMode` 8.4+, `JSON_BIGINT_AS_STRING` |
| ruby numeric | **REAL, closed** | cents `Money` shown, never stated; rules/01 §7: `to_i` truncation, flooring `/`, `JSON.parse` `decimal_class` |

With the listing widened, the MOSTLY ABSENT block reads `(none)`: no other universal concept
is missing in six or more languages.

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

### Depth, measured 2026-09-23: breadth is uniform, depth is not

After #426 every language has every applicable topic (page 5 has no blank cells; the only
`n/a` is c/c++ Web/HTTP). Depth still varies:

| language | rules lines | audit items | items / 100 lines | external gap-check |
|---|---|---|---|---|
| python | 2,152 | 65 | 3.0 | done (Bandit) |
| go | 2,151 | 71 | 3.3 | done (gosec) |
| rust | 2,057 | 94 | 4.6 | **not yet** |
| js/ts | 1,804 | 110 | 6.1 | **not yet** |
| php | 1,143 | 41 | 3.6 | **not yet** |
| ruby | 1,125 | 55 | 4.9 | done (Brakeman) |
| c/c++ | 1,061 | 53 | 5.0 | done (cppcheck) |
| jvm | 710 | 48 | 6.8 | **not yet** |
| .NET | 569 | 40 | 7.0 | **not yet** |

**Re-measured 2026-09-24, after all nine gap-checks and five concept-matrix passes.** The
table above is the 2026-09-23 measurement, restored. During the session its rows were
overwritten one language at a time as each gap-check landed, and the later matrix passes then
added items to most skills, so the edited rows were already stale. Rules lines are from
`cat skills/sota-<lang>/rules/*.md | wc -l`. Audit items are the "items read" column of
`python3 scripts/gen-concept-matrix.py`.

| language | rules lines | audit items | items / 100 lines | external gap-check |
|---|---|---|---|---|
| python | 2,194 | 72 | 3.3 | done (Bandit) |
| go | 2,175 | 73 | 3.4 | done (gosec) |
| rust | 2,244 | 104 | 4.6 | done (ANSSI) |
| js/ts | 2,072 | 126 | 6.1 | done (eslint-plugin-security + Semgrep) |
| php | 1,364 | 51 | 3.7 | done (Psalm + Semgrep) |
| ruby | 1,174 | 61 | 5.2 | done (Brakeman) |
| c/c++ | 1,166 | 60 | 5.1 | done (cppcheck) |
| jvm | 979 | 67 | 6.8 | done (find-sec-bugs) |
| .NET | 787 | 58 | 7.4 | done (NetAnalyzers Security + SYSLIB) |

Items are *counted* the same way across languages since every checklist became tick-boxes (the
same day), but not *sized* the same: one bullet can bundle several probes, and that varies by
author, so the item column is a rough guide rather than a ratio.
Small is not the same as shallow per line (jvm and .NET are the densest, as ROADMAP 58
found), but an auditor walking .NET gets 40 probes and walking js/ts gets 110. **Every
external gap-check found real gaps**: 4–7 in the first four, and 7–25 in the five checked
since (table below). **The operator set depth as the next session's focus.** The
concept-matrix candidate list does not answer this: the two .NET "gaps" it lists (command
injection, path traversal) are covered at `sota-dotnet` rules/04:35–38, and its vocabulary
simply misses .NET's phrasing.

Coverage inside this tier is checked against an **external, enumerable, tool-backed list** —
the method already used for Go (OWASP Go-SCP) and Rust (ANSSI). All nine are done:

| language | denominator | source | result |
|---|---|---|---|
| python | **75 tests** | Bandit 1.9.4 `plugins_by_id` + `blacklist_by_id` | 5 gaps closed |
| golang | **61 checks** | gosec 2.29.0 `rulelist.go` (39) + `analyzerslist.go` (22) | 4 gaps closed |
| c-cpp | **342 checks** | cppcheck 2.21.0 `--errorlist`, two agreeing derivations; MISRA addon (132 rules) is a separate registry | 4 gaps closed |
| ruby | **86 checks** (79 default + 7 optional) | Brakeman 8.0.6: source `check_*.rb` classes and the tool's own `--checks` registry (run in a container) agree name-for-name, and the `add`/`add_optional` registrations sum to the same 86 | 7 gaps closed, 1 held for a decision |
| rust | **60 recommendations** (46 rules + 14 recommendations) | ANSSI Secure Rust Guidelines at `3f9e2e2`: the source's reco blocks give 61 (en and fr identical), the rendered checklist page 60. The extra is `LIBS-UNSAFE`, a TODO inside an HTML comment that the renderer drops. No clippy registry derived | 25 gaps closed in three new sections (rules/03 §3b FFI boundary, §3c leak APIs, rules/07 §4a build config outside `Cargo.toml`) plus probes; one stale rule corrected (a panic out of `extern "C"` aborts since 1.81) |
| jvm | **144 patterns** (121 detectors) | find-sec-bugs 1.14.0: the source `findbugs.xml` (master and tag), the XML inside the released jar, and SpotBugs 4.10.4 loading the plugin on Temurin 25 in a container agree as sets. The source code emits 143: `SQL_INJECTION` is registered but never emitted | 16 gaps closed (39 patterns), 1 held for the temp-file class, 2 with no owner in any skill (LDAP anonymous bind, XML built from strings), both given one on 2026-09-24 as ROADMAP 64 |
| javascript-typescript | **15 + 214** (189 security rules) | eslint-plugin-security: npm 4.0.1 exports 14 and `main` has 15 (`detect-invisible-characters` is unreleased). Semgrep OSS `javascript/`+`typescript/`: 214 in source vs 212 served by the registry (one path case-folded, two unpublished MCP rules). Semgrep's rules are not openly licensed, so idea classes only | 14 gap classes closed (48 items) plus one correction (js-yaml 4 removed `safeLoad`); resource-lifecycle probe left open |
| php | **84 checks** (Psalm 19 taint types + Semgrep 65 `php/` rules) | Psalm 6.18.0: the `Issue/Tainted*.php` classes, the `TaintKind` constants and the docs agree on 19. Its sinks are a second registry (`InternalTaintSinkMap.php`, stubs), and that half held three of the gaps. semgrep-rules `php/`: a text parse and semgrep 1.177.0's own loader agree on 65. Idea classes only (Semgrep Rules License) | 7 gap clusters closed (14 items) plus the PHP host-key detector; temp-file trigger met |
| dotnet | **94 rules** | the NetAnalyzers Security category: `AnalyzerReleases.Shipped.md` (now in dotnet/sdk) and a reflection dump of the .NET 10 SDK's analyzer DLLs agree ID for ID. The docs index lists 92 (it still carries CA2109, removed in 8.0, and omits CA3005, CA5404 and CA5405). The SYSLIB obsoletion list is a second registry | 13 gaps closed, two of them corrections of the skill's own advice (security analyzers ship disabled, so `latest-Recommended` fired 4 of 14 planted violations; legacy `Rfc2898DeriveBytes` is SHA-1 x 1000); 3 DLL-load-path rules held with no owner, given one on 2026-09-24 as ROADMAP 64 (`sota-code-security` rules/06 §3.1) |

Remaining: none. All nine were checked by 2026-09-24.
*This said "jvm and .NET have no queryable local tool" until 2026-09-24. It was wrong for
both:
- **jvm:** the host has no JDK (`/usr/bin/java` is the macOS stub), but SpotBugs with the
  find-sec-bugs plugin runs in a Temurin container in one command, and that is how jvm's list
  of checks was derived.
- **.NET:** the SDK container (`mcr.microsoft.com/dotnet/sdk`) ships the analyzer DLLs, which
  are enumerable by reflection, and it builds fixtures. That is how .NET's defaults were
  measured rather than read.*

**c-cpp's denominator was derived and reconciled on 2026-09-21, and the sweep against it ran
on 2026-09-22 (the table row above).** The derivation is kept as the worked example of the step
that failed twice. cppcheck **2.21.0**:

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

### An open question this raised — host keys DECIDED 2026-09-23; temp files DECIDED 2026-09-24

**Temp-file/permission hygiene and host-key verification were gaps in *both* Python and Go.**
If that repeats in Ruby and PHP, the right fix is probably a class stated once in
`sota-code-security` with per-language *detectors*, not the same section written nine times —
the split this library already uses for in-band sentinels. Decide it before the fourth
language, not after the ninth.

**Evidence from the fourth language (ruby, 2026-09-23):**
- **Host-key verification repeats.** It appears in 0 files of `sota-ruby`, and `net-ssh`'s
  `verify_host_key: :never` (read from `net-ssh`'s own source) is uncovered. Across the tier it
  is present only in python and go, and only because their gap-checks added it. There is no
  shared owner: 0 hits in `sota-code-security` and `sota-network-security`.
- **Temp-file hygiene does not repeat in ruby.** `sota-ruby` §7 already points to `Tempfile`
  and `Dir.mktmpdir`. **That is half of the report's own test** ("if that repeats in Ruby
  *and PHP*"), so temp files are **not decided**. See the section below.
- **The shared-class design already exists for the sibling concern.** Disabled TLS
  verification is stated once in `sota-code-security` rules/04 with a per-language detector
  list, and ruby's gap there was a missing detector token (`VERIFY_NONE`, added), not a
  missing rule.

**DECIDED 2026-09-23 by the operator, for host keys only: option (a), a class stated once.** Host-key verification
now lives in `sota-code-security` rules/04 §5, beside certificate verification. It has one
detector row for every library whose bypass was read from that library's own source:
paramiko, Go `x/crypto/ssh`, `net-ssh`, JSch, MINA SSHD, Node `ssh2` and OpenSSH. Each
language skill carries only its library's spelling of the detector.

**Reasoning, recorded so it is not re-argued.** The library already solves the sibling concern
this way: disabled TLS verification is one rule with a shared detector list, and ruby's gap
there turned out to be a missing token, not a missing rule. Writing host keys nine times would
make nine copies to drift.

**The alternative, rejected:** per-language sections, as python and go already have. Those two
are **kept, not deleted**, because they carry library detail. The rule itself is no longer
restated per language.

Two facts surfaced by reading the sources, and neither would have been found by writing from
memory: **Node `ssh2` and `net-ssh` default to accepting**, so for them the finding is an
*absence*. The first draft of the shared probe also missed JSch's
`setConfig("StrictHostKeyChecking", "no")` form. It was caught by a per-library fixture and
widened.

*Superseded 2026-09-24 — decided as a shared class in `sota-code-security` rules/06 §6.1; see
"The trigger fired" below. The 2026-09-23 text is kept as written.*

**Temp-file/permission hygiene — still OPEN, and nothing above decides it.** A heading written
on 2026-09-23 read "DECIDED … one shared class" for the whole question, while only host keys had
been decided. It was corrected the same day. Measured 2026-09-23 over `skills/sota-*` (files
naming `Tempfile`, `mkstemp`, `mktemp`, `CreateTemp`, `NamedTemporaryFile`, `tmpfile` or
`tempnam`):
- python 2, go 1, ruby 1;
- **0 in c-cpp, php, rust, jvm, js/ts and .NET**;
- no shared rule in `sota-code-security`. Its two hits are test-harness advice (`mktemp -d`
  clones), not a temp-file rule.

**Revisit trigger: the PHP gap-check.** If PHP lacks it as well, the report's condition is met
and the same choice as host keys applies: a class stated once with per-language detectors, or a
per-language section. Six languages with no coverage is a reason to expect it will.

**The trigger fired on 2026-09-24.** `sota-php` had 0 hits for `tempnam`, `tmpfile`,
`sys_get_temp_dir`, `umask` and `chmod`, while the control (`mktemp`, outside the scope) found 21.
**DECIDED 2026-09-24 by the operator: a class stated once**, the same design as host keys. It
lives in `sota-code-security` rules/06 §6.1, with a detector row per language measured by that
language's gap-check. Reasoning: the host-key precedent, and one copy to maintain instead of
six.

### Ruby — the 86 Brakeman checks, classified (2026-09-23)

- **34 version/CVE checks**, plus 7 Rails 2/3-era pattern checks (nested attributes,
  `attr_accessible`, `without_protection`, response splitting, `strip_tags`, translate,
  digest DoS). Covered **as a class** by `rules/01` §1 (version policy) and `rules/04` §3
  (advisory scanning), not one rule each.
- **Covered on reading** (a zero, or a low count, that died when the file was opened): detailed
  exceptions (`rules/03` §8), hardcoded basic-auth credentials (`rules/02` §6), temp files.
- **Deliberately not rules**: reverse tabnabbing (browsers now imply `noopener` for
  `target=_blank`), Ransack (a single library's DSL), divide-by-zero (optional and noisy).
- **7 gaps closed**, each fact read from Rails, Rack or Ruby source or measured on Ruby
  3.4.10, and each probe run against a known-bad and known-good fixture under both ugrep and
  BSD grep:
  1. **HEAD→GET verb confusion.** `journey/router.rb` falls back to GET routes, then restores
     `HEAD`, so `request.get?` is false and a write branch runs without a CSRF check.
  2. Routes that widen the verb (`via: :all`) or the action set (dynamic `:action`).
  3. `render file:`, which serves any path raw.
  4. `render inline:`, which compiles its string as a template.
  5. Method-object reflection (`method(params[:m])`, `&params[:x].to_sym`).
  6. `Pathname#+` / `#join` discarding the base on an absolute argument (measured).
  7. Outbound `VERIFY_NONE`.

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
