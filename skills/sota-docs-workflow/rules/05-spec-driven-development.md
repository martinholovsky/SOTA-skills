# Spec-driven development

Spec-driven development (SDD) makes a written, living **specification the source
of truth** that a human or agent builds from, instead of prompting code into
existence ad hoc. The spec is durable; the code is regenerable. Reserve it for
non-trivial, multi-step, or multi-session work — it is overhead for a one-file
change (§7).

By 2026 the pattern has a common shape across tools — GitHub Spec Kit
(`specify` CLI; github.com/github/spec-kit), AWS Kiro (kiro.dev/docs/specs),
OpenSpec, BMAD — and is tool-agnostic at its core: plain Markdown in the repo is
enough. The tool is interchangeable; the discipline is not.

## 1. The loop: intent → plan → tasks → implement → verify

The canonical flow (Spec Kit's *Spec → Plan → Tasks → Implement*; Kiro's
`requirements.md → design.md → tasks.md`):

1. **Intent / requirements** — *what and why*: user stories and **testable
   acceptance criteria**. No implementation detail.
2. **Design / plan** — *how*: architecture, interfaces, data shapes, sequencing.
   Links out to ADRs and API contracts; does not copy them (§5).
3. **Tasks** — an ordered list of **PR-sized, independently verifiable** units.
4. **Implement** task-by-task, each as a reviewable change.
5. **Verify** against the acceptance criteria — that list *is* the done-gate.

Keeping these as separate artifacts is the point: requirements survive a rewrite
of the design, and the design survives a re-implementation of the tasks.

## 2. Writing a spec an agent can build from

- **Separate *what* from *how*.** The requirements doc states behavior and
  outcomes; the design doc holds mechanism. Implementation detail leaking into
  requirements is the most common smell.
- **Every requirement is testable** — a user story plus acceptance criteria in
  concrete, checkable terms. Vague criteria ("works correctly") generate vague
  code. Concrete criteria become scenarios/tests (`sota-testing` rules/08).
- **Mark unknowns explicitly.** Use an open-questions list or a
  `[NEEDS CLARIFICATION]` marker (Spec Kit convention) rather than letting the
  author — or the agent — silently assume. Unresolved markers **block**
  implementation; they are a stop-and-ask trigger, not a guess.
- **State scope and non-goals.** Ambiguity, not wrong syntax, is the number-one
  cause of generated code that misses the intent.

## 3. Living artifacts, in the repo, with the code

- Specs live **in-repo** (e.g. `specs/<feature>/`), versioned and PR-reviewed
  exactly like docs and tests. The spec changes **in the same PR** as the
  behavior — the same rule as docs-in-the-same-PR (`rules/01` §2) and
  tests-in-the-same-PR (`sota-testing` rules/01 §1.8).
- **Spec drift is the failure mode.** A spec nobody updates is worse than none —
  it actively misleads the next reader or agent (mirror `rules/01` §4). On a
  behavior change, update the spec or delete it; never let it rot in place.

## 4. Steering vs per-feature specs

A per-feature spec captures *this feature's* intended behavior. **Durable house
rules** — stack, conventions, security baseline, constraints — belong in a
persistent steering file the agent always reads, not repeated in every spec:
Spec Kit's *constitution*, Kiro's *steering files*, and in this ecosystem
`AGENTS.md` / `CLAUDE.md` / `profiles/` (cross-ref `rules/01` §7). Per-feature
spec = changeable intent; steering = stable rules. Don't conflate them.

## 5. Don't double-maintain — link, don't copy

Each concern has one home; the spec **references** it rather than duplicating:

- Architectural **decisions** → ADRs (`sota-architecture`).
- API **contract** → OpenAPI / GraphQL SDL, spec-first (`sota-api-design`
  rules/01 §10, rules/03).
- **Acceptance criteria** → executable scenarios (`sota-testing` rules/08).

Copying a contract or decision into the feature spec guarantees the two drift.

## 6. Agent-execution discipline

The library's audience runs these specs through coding agents, so:

- **Each task lands as a small, reviewed PR** with tests and the spec update
  together — treat agent output like any contribution (`rules/03`, reviewing
  AI-generated code).
- **Acceptance criteria are the verification gate.** "Done" means the criteria
  pass, not that the agent reported success — the claim-validation principle
  applies verbatim.
- **No silent scope expansion.** If implementation needs a decision the spec
  doesn't cover, that is a `[NEEDS CLARIFICATION]` → stop and ask, not improvise.

## 7. When SDD pays / when it's overhead

- **Pays:** non-trivial features, multi-session or multi-agent work, cross-team
  handoffs, and cutting the "regenerate from scratch" churn that ad-hoc
  prompting produces (GitHub's reported Spec Kit benefit).
- **Overhead:** one-file fixes, exploratory spikes (spike → throw away → spec
  the real thing, mirroring the TDD stance), and thin glue. Don't ceremonialize
  trivial work — the spec must earn its maintenance cost.

## Audit checklist

- [ ] Do non-trivial/multi-step features carry a written, in-repo spec (intent +
      acceptance criteria), not just chat history or a PR description? Missing on
      a multi-step feature → Medium.
- [ ] Do specs separate *what* (requirements) from *how* (design)? Implementation
      detail in the requirements doc → Low.
- [ ] Are acceptance criteria concrete and testable (each maps to a check)?
      Vague "works correctly" criteria → Medium.
- [ ] Are unknowns marked explicitly (open-questions / `[NEEDS CLARIFICATION]`)
      rather than silently assumed? `grep -rin "NEEDS CLARIFICATION" specs/`
      surfacing markers shipped into implementation → Medium.
- [ ] Is the spec updated in the same PR as the behavior (no drift)? Sample a
      recent feature; a spec older than the code it describes → High (it misleads).
- [ ] Are durable house rules in a steering/constitution/AGENTS file, not
      copy-pasted into each spec? Duplication → Low.
- [ ] Are decisions/contracts **linked** (ADRs, OpenAPI/SDL) rather than copied
      into the spec? A copied contract drifting from its source → Medium.
- [ ] Do agent-built tasks land as small reviewed PRs with tests, verified
      against the acceptance criteria? "Done" with no criteria check on a
      money/auth/critical path → High.
