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

**Where the canonical dev loop doesn't run everywhere, ship a capability
report.** Plenty of repos have one documented path — a container, a specific
OS, a licensed toolchain — and a reality where a given machine runs only part of
it. Prose ("requires Docker") doesn't help someone who *has* a runtime that
isn't the named one, or who can't tell which of twenty `make` targets are
reachable. A small executable report does: it probes the host and prints, per
target, **works here / doesn't, and what each gap blocks**.

- **Probe capabilities, not one implementation's name.** A check for `docker`
  reports "no container runtime" on a machine running podman; a check for
  `LICENSE` misses `LICENSE-MPL`. A single-name probe returns a false absence
  that then gets acted on — the audit-side statement of the same rule is
  `sota/rules/01-audit-methodology.md` ("a narrow search and a true absence
  produce identical output").
- **Every "unavailable" line names what it blocks**, so the reader learns the
  consequence without discovering it through a ten-minute failed build.
- **Report, never gate.** It exits 0 by design; it describes the host, it
  doesn't judge it. Keep the gate a separate command.
- Its audience is now agents as much as humans: without one, an agent proposes
  the documented command, fails, and retries it — the failure mode this artifact
  exists to prevent.

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
- **The minimal shape.** Four blocks is enough for most repos; anything past
  them has to earn its line against the test above.

  ```text
  # <repo> — one line: what it is, who runs it
  ## Tech stack     table, only where a wrong guess sends the agent down a wrong path
  ## Dev commands   the exact build / test / lint / run lines, with the flags you use
  ## Conventions    2–5 repo rules that cannot be inferred from the code
  ## Traps          the things that look fine and aren't
  ```

  A stack table an agent could rebuild by opening `package.json` is padding. The
  row that earns its place is the one **contradicting** the default: the test
  runner that isn't the framework's, the port that isn't the documented one.
- **Agent docs decay like all docs** — review them when commands change; a wrong
  test command in AGENTS.md silently corrupts every agent run.
- **Check the file's *claims*, not just that its commands exist.** The two rot
  at different rates and only the first is ever noticed. A verification that
  confirms every named target resolves passes happily while the file asserts a
  pinned toolchain seven months stale, an image tag long superseded, or that a
  given target runs a check it doesn't. Observed exactly that on a 4300-commit
  project: all seven `make` targets existed; the stated toolchain and the stated
  contents of `make check` were both wrong. So verify in two passes — every
  command resolves to a real target, **and** every factual assertion still
  matches the file it describes. Better still, delete the assertion and link the
  source of truth: a sentence naming the pin will drift, a pointer to
  `rust-toolchain.toml` cannot.
- **Automation that fires on an agent's edits must check, not rewrite.** A
  format-on-write hook is fine for a human editor and wrong for an agent: it
  changes the file *after* the agent wrote it, so the agent's view of that file
  is now stale and its next edit either fails or clobbers the reformatting. Have
  such hooks **report** the problem (non-zero, with the file and the fix) and let
  the agent apply it — the same content, in the one order that keeps both sides
  consistent. Reserve rewriting for hooks that run at commit or in CI, where no
  agent holds a live view.
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

## §8 The documentation baseline — what every repo carries

Docs aren't just "whatever got written." A small **baseline set** should exist,
each with **one home** (§4 — the baseline is a floor, never a license to
duplicate). Create each when its trigger fires, not preemptively: an unmaintained
`CONTRIBUTING` or `CODE_OF_CONDUCT` full of rules nobody follows is itself a
finding, not a checkbox win.

**Always (any repo shared with anyone):**

- **README** — the front door (§3): what, why, ≤5-minute quickstart, honest status.
- **LICENSE** — without one, default copyright applies and **no one may legally
  reuse the code** (choosealicense.com). Choose deliberately; it **cannot** be
  inherited from an org default — GitHub requires it in each repo.
- **CHANGELOG** — user-facing change history, updated in the PR that makes the
  change (rules/02 §6); absent it, users reverse-engineer releases from commits.

**When the trigger fires (conditionally required):**

| Trigger | Doc |
|---|---|
| Public, or accepts outside contributions | `CONTRIBUTING.md` (how to propose changes) + `CODE_OF_CONDUCT.md` (behavior + an enforcement contact) |
| Handles anything security-relevant | `SECURITY.md` — how to report a vulnerability **privately** (a channel or advisory, never "open an issue") + supported-version policy |
| Users need a place to ask / triage routing | `SUPPORT.md` — where questions go, so issues stay for bugs |
| On-call / production service | runbooks (§5) + an incident/postmortem template |
| AI-assisted repo | `AGENTS.md`/`CLAUDE.md` (§7) |
| Architectural decisions accrue | an ADR log (`sota-architecture`) |
| Multi-maintainer / org project | `CODEOWNERS`, plus `GOVERNANCE.md`/`MAINTAINERS` when decision rights aren't obvious |

**Placement.** GitHub recognizes the community-health files (`CODE_OF_CONDUCT`,
`CONTRIBUTING`, `SECURITY`, `SUPPORT`, `GOVERNANCE`, `FUNDING`) from **`.github/`,
then the repo root, then `docs/`** (that precedence); an org-level **public**
`.github` repo supplies defaults for repos lacking their own (GitHub docs). Keep
exactly one canonical copy — per repo or via the org default, not both. README and
LICENSE live at the repo root (GitHub surfaces them in the repo header) and are
**not** inheritable community-health files.

## §9 The troubleshooting playbook — where solved failures accrue

§5's runbooks serve the on-call reader mid-incident. A **troubleshooting
playbook** serves a different reader: a contributor or an agent who just hit an
error on their own machine, in a test run, or in CI. It is not alert-linked and
not severity-ranked — it is a growing index of **failures already solved once**,
so the second encounter costs a lookup instead of a re-debug.

One entry per failure, three parts, nothing else:

```text
### Symptom: <the literal error text or observable behaviour>
**Diagnosis:** <the actual cause, stated as a fact about this repo>
**Fix:** <exact commands, or the file to change>
```

- **Key on what the reader sees, not on what you now know.** The heading is the
  string they will paste into a search box — the exception name, the status
  code, the log line. "Environment misconfiguration" is unfindable by someone
  staring at `ModuleNotFoundError`.
- **Write it in the PR that fixes the bug**, while the cause is still known. A
  playbook backfilled later doesn't get written.
- **The diagnosis must be repo-specific.** "Check your dependencies" is not a
  diagnosis; "the dev server resolves imports from `src/` only, so a module
  added outside it resolves after a reinstall and not before" is.
- **Delete entries the fix made impossible.** Once a class of failure is closed
  at the root — a validation, a default, a guard — its entry is a false lead
  and goes (§4).
- **It is a repo artifact, not a chat log**: in-repo, linked from both the
  README's contributing path and the agent file (§7), or neither audience finds
  it.

A symptom reported a third time is a signal to **stop writing entries** — that
fix belongs in the code or the setup script, not the playbook.

## §10 Day zero — a new repo inherits no context, however good your tooling

An installed agent skills library, a personal `~/.claude/CLAUDE.md`, a house
style guide: all of it is **ambient** — attached to a machine or an account. A
freshly initialised repo inherits none of it, and neither does the teammate, the
CI runner, or the agent that clones it tomorrow. Whatever the repo's correctness
depends on has to live **in the repo**. Two questions, in this order.

**1. What must exist before the first commit?** Only two things, because both
are expensive to add later:

- **`.gitignore` + secret scanning.** A credential committed in commit 1 is not
  fixed by deleting it in commit 2 — it is in the history, and removing it costs
  a rewrite *plus* rotating the credential (`sota-secrets-management` rules/04).
  The pre-commit hook is cheapest while the history is one commit long.
- **`LICENSE`.** Its absence is not neutral (§8): all rights reserved, and not
  inheritable from an org default. Adding one later needs sign-off from everyone
  who has contributed by then.

Everything else in the §8 baseline still follows §8's rule — created when its
trigger fires, not pre-seeded. An empty `CONTRIBUTING.md` on day zero is the
decay problem (§4) with a head start.

**2. What can only the repo tell an agent?** A general skills library knows how
to write a Go service; it cannot know that *this* one is tested behind a flag,
deploys from a branch that isn't the default one, or has a directory nothing may
touch. That gap is the agent file (§7), held to §7's test. Two failure modes to
design out on day zero:

- **Restating ambient rules in the repo file.** If a personal or org-level agent
  file already says "use conventional commits", repeating it in-repo creates two
  copies that drift and spends context twice. Repo file = repo-specific only.
  The inverse is worse: repo-specific facts stranded in a personal file no
  teammate has.
- **Forking the file per tool.** Keep one canonical `AGENTS.md` (§7) and pick
  how the other names reach it, knowing the trade of each:
  1. **A one-line pointer file** — `CLAUDE.md` containing
     `See [AGENTS.md](AGENTS.md).` and nothing else. Platform-independent, no
     build step, and it cannot silently degrade; the cost is one hop the agent
     must follow. Observed in the wild on large cross-platform projects, and the
     safest default.
  2. **A symlink** — exact, but know the failure mode: git records a symlink as
     such, and where `core.symlinks` is false (set automatically at clone time
     on filesystems that can't represent one) symlinks are, in git's words,
     "checked out as small plain files that contain the link text"
     (`git help config`). The agent then reads the bare string `AGENTS.md` as
     the entire file and follows no instructions at all — a silent failure, not
     a visible one.
  3. **CI-generated duplicates** from the canonical file, failing the build on
     drift. Exact and platform-independent, at the cost of a job to maintain.

  Anything else — hand-maintained copies — drifts, and the copy that goes stale
  is the one your teammate's tool reads.

**Bootstrap the invariants as checks, not prose.** Anything the repo must never
regress — no secret in a commit, every internal link resolving, a required file
present — is worth a hook or CI job on day zero, when it costs one file and
passes trivially. The same check proposed at ten thousand commits arrives red
and gets disabled.

**An ambient install doesn't travel — decide per repo.** Rule libraries, agent
skills and linters installed at user scope resolve against *your* home
directory. A teammate's clone and a CI runner resolve nothing, so a repo that
depends on them is one that only works on one machine. Two honest options, and
the choice belongs in the repo's contributing docs either way:

- **Solo or private-to-you** — the ambient install is enough; write down
  nothing, and don't pretend the repo is self-contained.
- **Shared, public, or CI-checked** — make it repo-resident: vendor or
  project-scope the tooling (for this library, `install.sh --project .`, or
  `--copy` to pin a snapshot rather than link to a path only you have), *or*
  state the install step in `CONTRIBUTING.md` so a contributor can reproduce it.
  Whichever you choose, the **gates** must be repo-resident regardless — a
  secret scan that exists only in your shell is not a control on anyone else's
  commit (`sota-code-security` rules/10: a control nobody else runs is a no-op
  everywhere but your machine).

A pointer file that references tooling the reader doesn't have is worse than no
pointer: it reads as a satisfied requirement.

## Audit checklist

- [ ] Baseline present for the repo's stage: README + LICENSE + CHANGELOG always; CONTRIBUTING/CODE_OF_CONDUCT/SECURITY/SUPPORT once public or contribution-accepting; runbooks once on-call — each with one canonical home (no duplicate copies across root/`.github`/`docs`).
- [ ] `SECURITY.md` gives a private vulnerability-reporting channel (not "open an issue") and a supported-version policy; `LICENSE` is present and intentional (its absence = all-rights-reserved, blocking reuse).
- [ ] Docs classified by Diátaxis mode; no page mixes tutorial/how-to/reference/explanation; titles declare the mode.
- [ ] Tutorials run end-to-end on a clean environment (verified recently, versions pinned).
- [ ] Docs live in-repo, change via reviewed PRs, and behavior-changing code PRs touch docs.
- [ ] CI checks links (lychee or equivalent) and lints docs; internal links gate PRs.
- [ ] The agent file carries only what the agent would otherwise get wrong (exact commands, deviations, traps) — not a restatement of ambient/global rules or anything readable from the code; one canonical file, with per-tool names symlinked or CI-generated rather than forked.
- [ ] Solved failures land in a troubleshooting playbook keyed on the literal symptom, written in the PR that fixed them; entries invalidated by a root-cause fix are deleted, and a thrice-reported symptom was fixed in code rather than re-documented.
- [ ] The repo got `.gitignore` + secret scanning and a LICENSE before its first commit, and its must-never-regress invariants are enforced by a hook or CI job rather than described in prose.
- [ ] Nothing the repo depends on resolves only against one contributor's home directory: gates are repo-resident, and any user-scoped tooling a shared repo assumes is either vendored/project-scoped or documented as an install step (§10).
- [ ] README: one-sentence what, why, ≤5-minute copy-pasteable quickstart, honest badges, ownership/support pointer.
- [ ] Every doc/dir has an owner (CODEOWNERS or equivalent); high-traffic pages have a freshness/review signal.
- [ ] No known-stale pages kept "for reference"; deletions leave redirects/tombstones; no duplicated facts across pages.
- [ ] Every page-able alert links to a runbook; runbooks are command-exact, decision-tree ordered, flag destructive steps, and were updated after the last incident that used them.
- [ ] Onboarding guide exists, and the newest joiner actually filed fixes against it.
- [ ] Where the canonical dev loop doesn't run on every supported host, a capability report says per target what works here and what each gap blocks — probing capabilities rather than one implementation's name, and reporting rather than gating (§6).
- [ ] Agent-file verification covers claims as well as commands: every named target resolves **and** every factual assertion (pins, tags, what a target does) still matches its source — with drift-prone assertions replaced by a link to the file that owns the fact (§7).
- [ ] No automation rewrites files in response to an agent's edits (format-on-write hooks report instead); rewriting is confined to commit-time or CI, where nothing holds a live view of the file (§7).
- [ ] One search surface covers internal docs; error messages/alerts/code link into docs.
- [ ] AGENTS.md/CLAUDE.md exists, is short and human-curated, has exact build/test commands, and matches current reality; no forked divergent copies.
- [ ] Public docs site: llms.txt generated (not hand-written) if published; pages are self-contained with stable headings.
