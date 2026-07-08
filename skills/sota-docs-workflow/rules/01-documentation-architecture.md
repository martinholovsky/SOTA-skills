# 01 — Documentation Architecture

Structure, placement, and lifecycle of documentation. Covers Diátaxis, docs-as-code,
READMEs, decay control, runbooks, onboarding, and AI-readable docs.

## §1 Diátaxis: four modes, never mixed

Classify every document as exactly one of four types (diataxis.fr). Each serves a
different user need and is written differently; mixing modes is the single most
common structural defect in documentation.

| Mode | User need | Form | Cardinal sin |
|---|---|---|---|
| **Tutorial** | Learning (a lesson) | Guided, guaranteed-success path for a beginner | Offering choices, explaining theory mid-lesson |
| **How-to guide** | Doing (a task) | Steps for a competent user with a real goal | Teaching basics, exhaustive option coverage |
| **Reference** | Information (facts) | Complete, accurate, neutral description | Instructions, opinions, persuasion |
| **Explanation** | Understanding (context) | Discussion of why, trade-offs, history | Step-by-step instructions |

- **Name documents by mode**: "Tutorial: your first deployment", "How to rotate
  credentials", "CLI reference", "Why we shard by tenant". Users self-select
  correctly when the title declares the contract.
- **Tutorials must be reliably repeatable.** Test them end-to-end on a clean
  environment; a tutorial that fails at step 4 burns more goodwill than no
  tutorial. Pin versions inside tutorials.
- **How-to guides assume competence.** Don't re-explain what an environment
  variable is. Link to the tutorial for beginners instead of inlining basics.
- **Reference is generated or mechanically maintained wherever possible** (see
  rules/02). Hand-written reference drifts.
- **Explanation is where opinions live** — design rationale, trade-offs,
  "why not X". For architecture decisions specifically, use ADRs — see
  `sota-architecture` (do not duplicate ADR guidance here).
- You don't need all four for every project. A small library needs README +
  reference. Apply the taxonomy when a doc set grows past one page, not before.

**Bad** (mode soup, common in wikis):

```markdown
## Deploying the service
Deployment uses Kubernetes, which is a container orchestrator that...   ← explanation
First, let's learn about our Helm chart structure...                     ← tutorial
To deploy: `helm upgrade --install svc ./chart`                          ← how-to
Supported values: replicas (int, default 3), image.tag (string)...       ← reference
```

**Good**: four short linked pages, each one mode, each titled by mode.

## §2 Docs-as-code

- **Docs live in the repo, versioned with the code they describe.** A doc that
  can't be updated in the same PR as the code change will not be updated.
- **Docs changes go through PR review** with the same rigor as code: a wrong doc
  merged is a bug shipped.
- **CI gates on docs**: markdown lint, broken-link checking (lychee is the
  current standard — fast, Rust, checks anchors, runs as `lycheeverse/lychee-action`
  in GitHub Actions), spell check on prose, and doc tests (rules/02 §3). Internal
  links checked on every PR; external links on a schedule (they break without
  your involvement — don't fail PRs on the internet's health).
- **Code examples in docs are executed in CI** or extracted from tested code.
  Untested examples are reference-grade claims with tutorial-grade trust.
- **Definition of done includes docs.** A feature PR that changes behavior and
  touches zero docs files should trigger a reviewer question, and ideally a CI
  nudge (e.g., a check that flags `src/` changes with no `docs/` or README diff —
  advisory, not blocking).
- Prefer plain Markdown in-repo over wiki/Confluence for anything tied to code.
  Wikis are where docs go to decay: no review, no versioning, no proximity.

## §3 README as front door

The README answers, in order, within one screen: **what is this, why would I use
it, how do I try it in 5 minutes, what state is it in.**

Required sections for a project README:

1. **One-sentence what + one-paragraph why** (the problem it solves, not the
   implementation).
2. **Quickstart** — copy-pasteable, from clean checkout to observable result in
   ≤5 minutes. If your quickstart can't fit that, that's a product defect worth
   knowing; don't paper over it with prose.
3. **Status honesty** — badges that mean something (CI on default branch,
   coverage, latest release). Delete badges that are red, stale, or vanity
   (e.g., "downloads" on an internal repo). A green badge pointing at a
   skipped pipeline is worse than no badge.
4. **Pointers, not content** — link to docs site/dirs for everything beyond
   quickstart. READMEs that try to be the whole manual go stale fastest.
5. **Support/ownership** — who owns this, where to file issues/ask questions.

**Bad**: README opens with badges wall, install section assumes three
undocumented prerequisites, "Documentation coming soon", architecture essay
before anyone knows what the project does.

**Good** opening:

```markdown
# payout-svc
Computes and schedules creator payouts from settled transactions.
Replaces the legacy cron in `billing/jobs/payouts.py` (removed 2025-11).

## Quickstart
```sh
docker compose up -d   # postgres + localstack
make seed run          # service on :8080
curl localhost:8080/v1/payouts/preview?creator=demo
```
Expected: JSON payout preview. Full docs: ./docs. Owner: #team-payments.
```

## §4 The decay problem

Wrong documentation is worse than no documentation: it asserts authority while
lying. Engineer for decay from day one.

- **Proximity**: put docs as close to the code as possible — docstrings >
  package README > repo /docs > separate docs repo > wiki. Each step away
  halves update probability.
- **Ownership**: every doc/dir has an owner (CODEOWNERS on `docs/` works).
  Unowned docs are pre-decayed.
- **Freshness signals**: last-reviewed date (or rely on git metadata surfaced in
  the docs site) on operational docs; a periodic (quarterly) review sweep for
  high-traffic pages. "Reviewed: 2026-05" tells the reader how much to trust it.
- **Delete aggressively.** Stale docs are deleted, not archived into an
  "old-docs" graveyard that search keeps surfacing. Git history is the archive.
  When deleting a page that had inbound links, leave a redirect or tombstone
  one-liner pointing to the replacement.
- **Don't document what the code/tooling can assert**: link to the schema, the
  config struct, the generated reference instead of restating values that will
  drift. Docs should carry intent and context; machines carry facts.
- **Duplicate nothing.** Every fact has one home; everything else links to it.
  The second copy is the one that will be wrong.

## §5 Runbooks

Runbooks are read at 3 a.m. by someone with elevated cortisol and possibly no
context. Optimize for that reader.

- **Alert-linked**: every page-able alert links directly to its runbook; every
  runbook states which alert(s) fire it. An alert without a runbook link is an
  audit finding (also see `sota-observability` if present in this library).
- **Command-exact**: real commands with real flags, environment names, and
  expected output — not "check the logs" but the exact query. Placeholders
  clearly marked (`<pod-name>` with the command to find it).
- **Structure**: (1) symptom + alert, (2) impact/severity guidance, (3) triage
  steps in decision-tree order — most likely/cheapest checks first, (4)
  mitigation actions with their blast radius stated, (5) escalation path with
  names/rotations, (6) links to dashboards and recent incidents.
- **Tested**: exercised in game days/incident drills, and updated in the
  incident-review PR when they were wrong during a real incident. A runbook
  that failed during an incident and wasn't fixed is a repeat incident scheduled.
- **State the dangerous steps**: anything destructive (failover, cache flush,
  restart) carries an explicit "this will cause X" warning and rollback note.

**Bad fragment**: "If the queue is backed up, restart the consumers."
**Good fragment**:

```markdown
### Queue depth > 100k (alert: payouts-queue-depth-critical)
Impact: payouts delayed; no data loss (queue is durable).
1. Check consumer lag: `kubectl -n payments logs deploy/payout-consumer --tail=50`
   — look for `DeserializationError` (known issue, see INC-2041).
2. If deserialization errors: bad message poisoning the partition.
   Skip it: `make skip-poison-msg ENV=prod` (safe: dead-letters the message).
3. If consumers healthy but slow: scale `kubectl scale deploy/payout-consumer --replicas=8`
   (max 12 — DB connection limit, see docs/capacity.md).
4. Not resolved in 15 min → escalate: #team-payments-oncall (secondary: @payments-lead).
```

## §6 Onboarding docs and discoverability

- **Onboarding docs are tested by every new joiner**: their first-week task
  includes following the setup guide and submitting a PR fixing everything that
  was wrong or unclear. This is the cheapest doc-testing loop that exists; if
  the guide survived three joiners unchanged, either it's excellent or they
  weren't told to fix it.
- **Day-one doc** answers: how to get the code running locally, how to run
  tests, where the architecture overview is, who to ask what, what the team's
  workflow is (PR/review norms — rules/03). Target: first PR merged in week one.
- **Discoverability beats organization.** People find docs via search and via
  links from where they already are (code, alerts, error messages, PR
  templates). Invest in: one search surface over all internal docs, links from
  error messages to docs, links from code to design docs — more than in perfect
  taxonomy. A perfectly organized doc tree nobody can search loses to a flat
  searched pile.
- Keep an entry-point index per repo/team (`docs/README.md`): what docs exist,
  one line each, by Diátaxis mode. Indexes decay too — keep them short.

## §7 AI-era documentation

Docs are now read by agents as well as humans. Same content, two consumers.

- **AGENTS.md** is the open, Markdown-only convention for repo-level agent
  instructions (agents.md; 60k+ open-source projects; stewarded by the Agentic
  AI Foundation under the Linux Foundation; read by Codex CLI, Cursor, Copilot,
  Gemini CLI, and 20+ other tools as of mid-2026). **CLAUDE.md** is Claude
  Code's native equivalent — Claude Code reads CLAUDE.md, not AGENTS.md, hence
  the advice that follows. Maintain one canonical file; if a tool needs the
  other name, symlink or include rather than fork the content.
- **Keep agent docs minimal and high-signal.** Evidence as of 2026: bloated or
  auto-generated context files often *reduce* agent performance and raise cost;
  short, human-curated files with genuinely non-obvious repo knowledge help.
  Content that earns its place: exact build/test commands with flags, deviations
  from language defaults, files/dirs the agent must not touch, commit/PR
  conventions, known traps. Content that doesn't: anything the agent can read
  from code, generic best practices, restated style guides.
- **Agent docs decay like all docs** — review them when commands change; a wrong
  test command in AGENTS.md silently corrupts every agent run.
- **llms.txt** (llmstxt.org): root-level Markdown index of a site's docs for LLM
  consumption. Status as of mid-2026: community convention, ~10% site adoption,
  not an IETF standard, major crawlers don't commit to fetching it — but coding
  agents and IDE tools do fetch `/llms.txt` and `/llms-full.txt` from docs
  sites routinely. Verdict: cheap to publish for a public docs site (generate it
  from the nav tree in CI); don't hand-maintain it; don't expect SEO/answer-engine
  effects.
- **Structure helps both audiences**: stable heading hierarchies, one topic per
  page, self-contained pages (agents retrieve pages out of context), exact
  command blocks, tables over prose for facts. These were good practices for
  humans already; agents just raised the price of ignoring them.

## Audit checklist

- [ ] Docs classified by Diátaxis mode; no page mixes tutorial/how-to/reference/explanation; titles declare the mode.
- [ ] Tutorials run end-to-end on a clean environment (verified recently, versions pinned).
- [ ] Docs live in-repo, change via reviewed PRs, and behavior-changing code PRs touch docs.
- [ ] CI checks links (lychee or equivalent) and lints docs; internal links gate PRs.
- [ ] README: one-sentence what, why, ≤5-minute copy-pasteable quickstart, honest badges, ownership/support pointer.
- [ ] Every doc/dir has an owner (CODEOWNERS or equivalent); high-traffic pages have a freshness/review signal.
- [ ] No known-stale pages kept "for reference"; deletions leave redirects/tombstones; no duplicated facts across pages.
- [ ] Every page-able alert links to a runbook; runbooks are command-exact, decision-tree ordered, flag destructive steps, and were updated after the last incident that used them.
- [ ] Onboarding guide exists, and the newest joiner actually filed fixes against it.
- [ ] One search surface covers internal docs; error messages/alerts/code link into docs.
- [ ] AGENTS.md/CLAUDE.md exists, is short and human-curated, has exact build/test commands, and matches current reality; no forked divergent copies.
- [ ] Public docs site: llms.txt generated (not hand-written) if published; pages are self-contained with stable headings.
