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

### Item 57 — API / design is missing in five languages

Dedicated file in **rust, go, jvm, .NET**. Absent in **python, js/ts, php, ruby, c/c++**,
and thin where adjacent rules touch it (3–9 keyword mentions; JS/TS has "Functions and
modules over classes", Ruby has "Data vs Struct", and that is close to all of it).

This is a genuine gap rather than a principled difference, because designing a public
surface — a package, gem, crate or library — is language-inflected work that every one of
these languages does:

| | what the missing section would own |
|---|---|
| python | `__all__`, keyword-only parameters, `__slots__`, deprecation via `warnings`, what a leading underscore does and does not promise |
| js/ts | the `exports` map, type-level public surface vs runtime, `default` vs named, what a breaking type change is |
| php | `final` and `readonly` as API decisions, interface vs abstract, BC breaks under semver |
| ruby | gem semver, `private_constant`, refinements, what `respond_to?` promises callers |
| c/c++ | ABI stability, header hygiene, `pimpl`, what is safe to change in a released header |

**First move:** write one section for the language you are already in, not five at once.
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

**Recommendation: close as (c).** Splitting `sota-jvm` is rejected — it adds a skill, moves
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

This is **not cosmetic**. AUDIT mode tells the model to "verify your diff satisfies every
item" — a checkbox list is enumerable, a prose block is not. Unifying it is a rewrite of
seven skills and needs its own decision; it is recorded here so it is not absorbed silently
into other work.

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
