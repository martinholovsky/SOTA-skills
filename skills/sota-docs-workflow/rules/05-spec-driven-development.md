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

**Two human sign-offs sit before any code is generated**, and each has a security
question an agent will not ask itself:

- **After step 1 (spec gate):** are the security acceptance criteria present and
  complete (who may do this, what input is hostile, what must be logged or
  refused), and are scope, non-goals and trust assumptions stated rather than
  implied? Abuse cases come from the threat model (`sota-threat-modeling`
  rules/05 §2–§3).
- **After step 2 (plan gate):** does every security requirement in the spec map to
  a named part of the design, is each security-relevant choice (auth scheme,
  crypto, storage of secrets, trust of an upstream) justified, and are changes to
  security-critical components flagged so the tasks route to a qualified reviewer
  (`rules/03` §3)? A requirement with no home in the plan is dropped silently.

Record the sign-off in the spec itself (a reviewer and date per gate), so an
auditor can tell a reviewed plan from one an agent approved for itself.
(OWASP: DSOMM)

## 2. Writing a spec an agent can build from

- **Separate *what* from *how*.** The requirements doc states behavior and
  outcomes; the design doc holds mechanism. Implementation detail leaking into
  requirements is the most common smell.
- **Every requirement is testable** — a user story plus acceptance criteria in
  concrete, checkable terms. Vague criteria ("works correctly") generate vague
  code. Concrete criteria become scenarios/tests (`sota-testing` rules/08).
  **EARS notation** ("WHEN *trigger* THE SYSTEM SHALL *response*") is a proven
  concrete syntax — unambiguous to humans and agents, and machine-checkable:
  tooling can now verify implementations against EARS-style requirements (e.g.
  Kiro writes `requirements.md` in EARS and property-tests code against it).
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

**Map phases to the security material they load.** The steering file should say
which security artifacts apply at which phase — the threat model and security
requirements while specifying and planning, the secure-coding rules for the
language while implementing, the review checklist while verifying — ideally as a
per-phase instruction template, rather than one undifferentiated block loaded
everywhere or nowhere. Then check that it happens: spot-check a sample of agent
sessions for evidence the named files were actually read (an instruction that is
listed is not an instruction that loaded — `sota-skill-security` rules/01 §4),
and revise the rule set after every security incident or review finding the
existing rules should have prevented. (OWASP: DSOMM)

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
- [ ] **(Medium) Spec and plan gates carry security (§1):** every feature spec has
      security acceptance criteria and a recorded human sign-off at the spec and
      plan gates. Probe: `grep -L -i -E 'secur|abuse|threat|authori[sz]' specs/*/*.md`
      lists spec files with no security content at all (Spec Kit layout; Kiro
      keeps them in `.kiro/specs/<feature>/`); a spec
      touching auth, money or personal data among them → High.
- [ ] **(Low) Steering maps phases to security artifacts (§4):** the steering file
      names what loads per phase, and sampled sessions show those files were read.
      Probe:
      `[ -n "$(grep -r -s -i -l -E 'threat model|secure[- ]coding' AGENTS.md CLAUDE.md .kiro/steering)" ] || echo "no phase-to-security mapping"`
      (tests the *output*, not the exit status: an absent file makes grep exit 2 even
      on a match, and ugrep does so under `-q`; no glob, so zsh cannot abort on it).
