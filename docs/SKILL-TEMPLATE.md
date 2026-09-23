# Skill template — the skeleton a new skill starts from

**Why this file exists.** Until 2026-09-22 the anatomy of a skill lived only as prose in
[AGENTS.md](../AGENTS.md) and [CONTRIBUTING.md](../CONTRIBUTING.md), so a new skill was
authored by copying a neighbour — and inherited whatever that neighbour was missing.
ROADMAP 57 is what that cost: four language skills shipped with no API/design section and
nothing reported it for months.

**Why it lives in `docs/` and not `skills/`.** Every gate enumerates skills with
`git ls-files skills/*/SKILL.md`. A template under `skills/` would be counted as a real
skill by invariants 6, 10 and 15, and would have to satisfy the 500-line cap and the
`## Audit checklist` requirement. It is documentation, so it lives with the documentation.

**This file is not the gate, and cannot be.** A template is read *once*, when a skill is
created; the drift happens on every edit afterwards. The enforcement is
`scripts/gen-concept-matrix.py --assert-universal`, which runs in CI and pins the concepts
below at 9/9. Read this to author; rely on that to stay honest.

---

## Frontmatter — two fields, and the description is the whole classifier

```markdown
---
name: sota-<domain>
description: <what the skill covers, when to use it, BUILD and AUDIT, and a
  `Trigger keywords:` tail>
---
```

**The `description` is the only text that auto-loads**, and it is the entire routing
classifier — the body is inert until the skill is invoked. Budget: ≤ 1024 characters
(invariant 4). Write the trigger vocabulary a *user* would type, not the vocabulary the
domain prefers. Changing it moves routing, which is why a release that touches a
description must declare a routing check (invariant 29).

## Body — the spine

| Section | Content |
|---|---|
| Purpose | one paragraph: what this owns, and explicitly what it does **not** (name the skill that does) |
| BUILD mode | the workflow when writing new code in this domain |
| AUDIT mode | the workflow when reviewing existing code |
| Top-10 non-negotiables | the rules that survive context pressure; these are what a long session drops first |
| Rules index | one row per `rules/NN-*.md`, each with "read this when…" guidance (invariant 10 gates both directions against `skills/sota/rules/04`) |

## `rules/NN-topic.md` — the shape

Each is ≤ 500 lines (invariant 1) and **ends with `## Audit checklist`** (invariant 2).
Three checklist body formats are in use and none is gated — tickable `- [ ]`, a fenced
shell block, or prose plus commands. Pick one and hold it for the whole skill; they are
**not comparable by volume**, so mixing them inside a skill makes its own numbers
meaningless.

### For a language skill: the file spine

Measured across the nine (see [LANGUAGE-TIER.md](LANGUAGE-TIER.md)): idioms/baseline,
security, performance, tooling/CI, testing (usually inside tooling), concurrency, and
**API/design** — the one that was missing from four skills at once. Deviate only for a
property of the language, and record the reason in LANGUAGE-TIER so a later reader does not
"fix" a principled difference.

---

## The universal concepts — every language skill must probe these

Pinned in `scripts/gen-concept-matrix.py` as `UNIVERSAL_FLOOR` and asserted in CI. A new
skill that omits one fails the build.

- [ ] **error handling & propagation** — wrapping, swallowing, empty catch, error types
- [ ] **absence / null / in-band sentinel** — how "no value" is encoded, and the magic-value trap
- [ ] **data race / shared mutable state** — the language's concurrency hazard, named
- [ ] **cryptography & randomness** — CSPRNG, hashing, and the delegation to `sota-code-security` rules/04
- [ ] **secrets handling** — hardcoded credentials, `.env`, what reaches a log
- [ ] **input validation & untrusted data** — the trust boundary in this language's idiom
- [ ] **dependency pinning & lockfiles** — the lockfile's name, and whether CI uses the frozen form
- [ ] **vulnerability scanning of dependencies** — the ecosystem's advisory tool, by name
- [ ] **static analysis / linter configuration** — the analyser, and its config
- [ ] **suppressing a linter / type check** — *every* escape hatch, including the bulk and
      config-level ones. A per-site grep alone misses a whole rule disabled in a project file
- [ ] **build reproducibility & CI gates** — pinned toolchain, warnings-as-errors
- [ ] **test suite health & determinism** — flakiness, and the runner by name

## The rule that is not yet a gate, and is the most common real defect

**A stated rule with no probe is invisible in AUDIT mode.** Three independent instances in
two days: the `$?` rule (bash had neither half while PowerShell had both), the analyser
escape hatch (ROADMAP 60), and jvm path traversal + js/ts SQL injection, where the BUILD
rule was written and no checklist ever asked for it.

So for **every** rule you write, ask the second question before moving on: *how would an
auditor detect a violation?* If the answer is not in the `## Audit checklist`, the rule
ships as prose that only a reader of the file will ever apply. Nothing currently gates
this — it is the reviewer's job.

## Before opening the PR

- [ ] Every shipped checklist grep run against a **known-bad and a known-good** fixture.
      Measured repeatedly: a probe that can never fire ships silently, and reads as coverage
- [ ] New `rules/NN` indexed by its `SKILL.md` **and** by `skills/sota/rules/04` (invariants 10, 15)
- [ ] A new rule section carries an ADOPTION-LOG entry (invariant 31)
- [ ] `./scripts/check-invariants.sh` green, and `python3 scripts/gen-concept-matrix.py
      --assert-universal` green if this is a language skill
