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

### Item 58 — jvm and .NET are 3–4× thinner than their peers

| skill | rules-file lines | files |
|---|---|---|
| golang | 2128 | 7 |
| rust | 2057 | 7 |
| python | 1986 | 7 |
| js/ts | 1729 | 7 |
| php | 1118 | 6 |
| ruby | 1053 | 5 |
| c/c++ | 910 | 7 |
| **jvm** | **619** | 6 |
| **.NET** | **564** | 6 |

`sota-jvm` covers **both Java and Kotlin** in 619 lines. Thin is not automatically wrong —
a skill can be dense — but a 3.4× gap against Go is an accident until someone decides it is
not.

**This item is a decision before it is work.** Three options, and they are not equivalent:
(a) thicken both in place; (b) split `sota-jvm` into Java and Kotlin, which adds a skill
and therefore competes for routing traffic (invariant 29, and a before/after routing run);
(c) declare the current depth correct and record why, closing the item. **Do not start
writing until (a)/(b)/(c) is chosen** — option (b) changes the description classifier and
is not reversible by deleting prose.

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
