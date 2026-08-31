# Audit Findings — Severity, Evidence, Decisions, Refutation & Reporting

Scope: what happens to what an audit finds — how a finding is **rated**,
**evidenced**, **verified against itself**, and **reported**, plus the
decision-ledger pass that produces findings the code passes cannot.
`rules/01` owns how the audit is *run* (scoping, recon, tooling, triage,
hygiene); this file owns the deliverable. Read both for any full audit.

Split out of `01-audit-methodology.md` on 2026-08-29, when that file reached
455 of its 500 lines. **The section numbers changed**: severity, evidence, the
decision ledger, refutation and reporting were sections 4 to 8 of `rules/01` and
are §1–§5 here, in the same order. Prose written before the split that points at
`rules/01` for any of those five means this file, shifted down by three.

---

## 1. Severity model

Rate **impact × likelihood/exploitability, in context**. CVSS may inform the
rating; it is never the rating. The deployment context (internet-facing vs
internal, data sensitivity, existing mitigations) decides the final level.

- **Critical** — exploitable now with severe impact: RCE, auth bypass,
  secrets/keys exposed in repo or logs, unauthenticated access to sensitive
  data, prompt injection reaching a privileged tool. Fix immediately; ask
  whether it is already an incident (was the secret ever live? rotate first,
  then fix).
- **High** — serious impact or likely exploitation: injection (SQL/command/
  NoSQL), broken access control (BOLA/IDOR), missing authn on a sensitive
  route, weak or hand-rolled crypto, SSRF. Fix this sprint.
- **Medium** — real weakness requiring conditions or chaining: missing rate
  limits, verbose error leakage, absent security headers/CSP, weak
  validation behind an authenticated boundary.
- **Low** — defense-in-depth and hygiene: minor info disclosure, hardening
  gaps with low standalone impact, lint-level issues with a security flavor.
- **Info** — no direct risk: observations, tech-debt notes, future-proofing,
  positive-pattern caveats.

Two hard rules:

1. **Borderline ratings state the deciding assumption explicitly** — "High
   if this endpoint is internet-facing; Medium if internal-only" — and ask
   when the answer is knowable. Do not silently pick the scarier level.
2. **Uncertain findings are marked "needs verification", never asserted.**
   A speculative Critical that turns out false costs the whole report its
   credibility.
3. **Name the primitive before you rate.** A severity is a claim about a
   *chain*, and a chain has legs: attacker-controlled input **reaches** the
   code; something **acts** on it (a write, a read, an exec, a spawn); the
   effect **crosses a trust boundary** (another tenant, the host, a third
   party, the operator's own credentials); and where exfiltration is the
   impact, a **channel** carries it out. Write the legs down and point each at
   code. A missing leg does not make the finding smaller, it makes it a
   *different* finding — hostile bytes staged into a directory that nothing
   ever executes is a hardening gap, not RCE, and rating it as RCE spends
   credibility you need for the real one. The inverse is the higher-yield
   half: when every leg coexists **in one path**, that is what the report
   leads with, however unremarkable the file looks. "And then presumably it
   runs" is not a leg; the toolchain that is not in the image, the build step
   that compiles without executing, and the temp directory that never leaves
   the operator's machine are all legs that turn out to be missing on
   inspection.
4. **On a diff, the baseline is the code the change replaced — not perfect.**
   A hardening change that closes three exposures and leaves a fourth is not a
   High: the High was the state *before* it. Read the pre-change path (`git
   show <base>:<file>`) before rating anything on a branch that moves in the
   right direction, and say which baseline you used. Filing a High against a
   fix is not a conservative error — it teaches authors that hardening attracts
   findings, which is how the next mitigation does not get written. The residual
   gap is still reported: as a hardening item against the *codebase*, at its own
   severity, with the improvement stated. Where the change is a pure regression,
   this rule costs nothing — the baseline comparison makes that case stronger,
   not weaker.

## 2. Evidence standard — no finding without it

Every finding carries all of the following. A finding missing any item is
not ready to ship:

1. **Title** — concise statement of what is wrong.
2. **Severity** + one-line justification (impact × likelihood, per §1).
3. **Location** — `file:line` at the pinned commit (or manifest key, route,
   workflow step). Exact, clickable, reproducible.
4. **Evidence** — the minimal code/config snippet or triaged tool output
   that proves the issue. Minimal: enough to verify, no page-long dumps.
5. **Standard mapping** — CWE id; OWASP Top 10 / API Top 10 / ASVS item;
   MITRE ATT&CK or ATLAS technique where it applies.
6. **Impact** — what the attacker (or affected user) *actually gets*:
   "reads any tenant's invoices", not "improper access control".
7. **Remediation** — concrete and diff-level where possible ("parameterize
   this query", with the changed line), referencing the relevant skill's
   rules file for the full pattern. Never "sanitize input".
8. **Effort estimate** — trivial / small / medium / large. Severity says
   what hurts; effort enables the roadmap in §5.

Two asymmetries the evidence standard has to carry:

- **Negative claims need more proof than positive ones.** "No hardcoded secrets
  remain", "authorization is enforced everywhere", "nothing in this class was
  found" — a narrow search and a true absence produce identical output. Before
  any absence claim, widen the search (synonyms, other languages, generated and
  vendored trees, config as well as code) and confirm with a **second
  independent method** (grep *and* AST/call-graph *and* a dynamic or mutation
  probe). Then state the search performed, so the reader can judge its reach.
  An unqualified absence claim is the one finding-type nobody can falsify.
- **"The control is present" is not "the control works."** Evidence for a
  positive observation must show *effect*, not existence — the log line it
  emitted, the request it rejected, the test that fails when it's disabled.
  See `sota-code-security` rules/10; this applies to §5's positive-observations
  section too, where an inert control praised as a strength is the worst
  possible reporting error.

**A reproduction you ran once is a coincidence you have not ruled out.** Where the
evidence is a *behaviour* rather than a line of code — a crash, a race, a
timing-dependent bypass, a fuzzer hit, or anything an agent or a sampled model
produced — reproduce it **N of N** and report both numbers. Anthropic's
defending-code reference harness sets the reference point: its find agents run
the instrumented binary *"until a given input produces a crash 3 out of 3
times"*, and until then it is not a crash. The threshold matters less than having
one, because `1/1` and `3/3` are typeset identically in a report and mean
entirely different things. This binds your own instruments too: a criterion that
flips run to run at temperature 0-ish (`sota-llm-engineering` rules/01) cannot be
settled by a single run, so a one-shot measurement quoted as a result is an
unstated `1/1`.

The library's short finding format (`file:line | rule | severity | effort | fix`)
is the working format during passes; expand each surviving finding into the
full evidence block for the report. Skill-local block formats are fine during
a single-domain pass, but they must carry the effort field — §5's roadmap is
sequenced by risk-reduction-per-effort and can't be built without it.

**Keep the output that produced the finding.** A command whose result you will cite is
evidence: redirect it to a file rather than piping it through `tail`/`head`, because a
consumed pipe cannot be re-read and the truncation keeps the summary while discarding the
context that would qualify it (`sota-shell-scripting` rules/01 §3). An audit that cannot
reproduce its own quoted output without re-running the job has a weaker evidence chain
than it appears to.

## 3. Decision-ledger review — audit the decisions, not just the code

Code review finds defects in what was built. It cannot find the defect where the
code is a faithful implementation of a choice that **stopped being right** — a
datastore picked for a scale that never arrived, a benchmark-justified rewrite
whose benchmark no longer reproduces, a constraint that expired two years ago and
is still shaping the design. That class is invisible to every pass above and is
often the most expensive thing in the repo.

`sota-architecture` rules/01 §4 owns **writing** ADRs. This is the audit side:
reading them back and asking whether they still hold.

**Reconstruct the ledger.** Sources, in order of reliability: ADRs
(`docs/adr/`), design docs and RFCs, the CHANGELOG, PR descriptions on the
commits that introduced each major component, and — last — comments. Where no
record exists, the decision is still there, just undocumented: infer it from the
code and label it *reconstructed, unconfirmed*. A major component with no
discoverable rationale is itself a finding.

**For each significant decision, classify it:**

- **JUSTIFIED** — the reasoning holds and the evidence still reproduces.
- **STALE** — sound when made, no longer: the constraint expired, the alternative
  got better, the load never materialized, the dependency went EOL. Not a mistake;
  a decision that has outlived its inputs. Say what changed.
- **UNJUSTIFIED** — the stated reasoning does not support the decision, or the
  evidence cited was never checked. Distinguish this from STALE plainly; it is a
  judgment about the decision as made.
- **UNVERIFIABLE** — no rationale survives and none can be reconstructed. Record
  it rather than guessing.

**The reason must be self-contained and decision-enabling.** A verdict is read
later, by someone who does not have your session — most often to decide whether to
reopen the question. A reason that only makes sense next to the thing it judged is
a verdict with no audit trail, and it quietly re-opens the decision anyway, because
the next reader cannot tell what was checked. Ban the four reasons that carry no
information: *"unchanged"*, *"superseded"*, *"overlaps with X"*, *"looks fine"*.
Restate the evidence every time, even when the verdict is unchanged from last pass.

| Verdict | Not this | This |
|---|---|---|
| JUSTIFIED | "Still fine." | "Postgres over the queue: the 8k msg/s that justified a broker still has not arrived — peak measured 240/s this session (`bench/throughput.py`, 2026-08-31). Holds." |
| STALE | "Outdated." | "Sharding by `tenant_id`: justified by a 40-tenant forecast; 3 tenants after two years, one holds 96% of rows, so the shard key now concentrates rather than spreads. Reversal is large — see roadmap item 4." |
| UNJUSTIFIED | "Bad call." | "ADR-007 cites a 3× benchmark for the rewrite; the benchmark script compares release-vs-debug builds (`bench/run.sh:12`), so it measures build flags, not the rewrite. Re-run like-for-like: 1.04×." |
| UNVERIFIABLE | "No docs." | "No ADR, no PR body, original author gone. Would be settled by the load figures behind the 2024 capacity plan, if anyone still has them." |

The same bar applies to any verdict this library asks you to record — a refuted
finding (§4), an intake decision in `docs/ADOPTION-LOG.md`, a triage dismissal
(`rules/01` §3). "Already covered" without a `file:line` is the same empty verdict
wearing different clothes.


**Re-measure anything a decision rests on.** When the justification is a number —
a benchmark, a latency or throughput target, a recall/false-positive rate, "X is
faster than Y", "this doesn't scale" — **re-run it this session** and report the
result, including in heavyweight environments when that is the only honest way to
check. A number in a two-year-old ADR is a historical claim, not a current fact.
If you cannot re-run it, mark the decision UNVERIFIABLE and say precisely what
would confirm it (principles 0 and 6 apply here with full force). Respect the
repo's documented environment constraints and teardown rules when you do.

**Check the ledger against reality, both directions.** A decision recorded but
never implemented is as much a finding as one implemented but never recorded —
the ADR says "we use the outbox pattern", the code dual-writes. And a superseded
ADR still describing current behavior misleads every future reader.

**Report as findings.** STALE and UNJUSTIFIED entries carry a severity like any
other finding (impact of continuing on the current path × likelihood it bites),
and feed §5's roadmap — reversing an expensive decision is usually *large* effort
and belongs sequenced, not buried in prose. Quote both sides: the recorded
rationale and what you measured.

Scope it: the decisions worth this treatment are the expensive-to-reverse ones —
datastore, broker, service boundaries, auth model, tenancy model, language or
framework, build/deploy topology. Do not ledger-review every merged PR.

## 4. Adversarial verification — try to kill your own findings

Re-reading your own finding is the weakest possible check: you re-run the
reasoning that produced it and reach the same conclusion. Confirmation bias is
not defeated by attention. Before a finding ships, someone — a separate agent, a
colleague, or you in a deliberately hostile pass with fresh context — must try
to **refute** it.

The pass:

1. **State the finding as a falsifiable claim.** "An unauthenticated caller can
   read any tenant's invoices via `GET /invoices/{id}`" — not "weak access
   control in the invoices module". A claim you cannot refute is a claim you
   cannot verify.
2. **Assign refuters, prompted to kill it.** The instruction is *find the reason
   this is wrong*, not *check this*. Default the verdict to REFUTED when the
   evidence is ambiguous — an unrefutable finding must earn its survival.
3. **Use distinct lenses when a finding can fail in more than one way.** Three
   identical reviewers are worth less than three different questions:
   - **Correctness** — is the mechanism real? Read the full path, not the
     snippet. Is there an upstream guard the finding missed?
   - **Reachability** — can attacker-controlled input actually get here? Dead
     code, an unregistered route, or a caller that always sanitizes downgrades
     it to hardening debt.
   - **Severity inflation** — does the stated impact follow, or is a Medium
     dressed as a Critical? Rate the *demonstrated* impact.
   - **Chain closure** — walk the legs from §1 rule 3 and demand each one in
     code. This lens's whole job is to find the leg that is *missing*, and it
     is the one that most often kills a plausible finding: the language that
     routes here has no toolchain in the image; the pinned build command runs
     no generator, no test and no `main`; the staged bytes land in a
     mode-`0700` directory the operator already owns. A finding that cannot
     name its execution primitive is reachability plus speculation.
4. **Majority-refute kills it.** Survivors ship; the rest are dropped or
   downgraded with the refutation recorded — a refuted finding is a result, not
   waste, and stops the next auditor re-raising it.
5. **A refuted finding is a template — sweep before you drop it.** The
   refutation hands you two reusable things: the *pattern*, and the *leg* that
   was missing. Grep the pattern across the whole repository — not just the
   audited scope — and check each hit for that leg. The strongest instance of a
   class is routinely **outside** the scope where you first noticed it: a
   diff-scoped review that refuted a symlink-dereferencing staging finding on
   the branch (nothing on that path executes the staged code) found the same
   staging in an *unchanged* module where the analysis step compiles the target
   and runs its build scripts, with no network isolation — three legs at once,
   and the only High the review shipped. Record the sweep next to the
   refutation, with its denominator: "refuted here; swept 6 call sites; one
   survives at `file:line`". A refutation with no sweep closes the class on a
   single instance and leaves the report asserting more than it checked.
6. **Verify the negatives too.** "Authorization is enforced everywhere" is a
   finding-shaped claim with the heavier burden of `SKILL.md` principle 3. Give
   absence claims a refuter whose job is to find one counter-example.

### 4a. Bound what the refuter gets, and make its verdict a number

Step 2 says *prompt it to kill the finding*. Three conditions decide whether that
prompt does anything, and all three are cheap.

**Give the refuter less than the finder had.** A refuter holding the finder's
tools re-runs the finder's investigation and arrives where it arrived. Take the
tools away: it reads code and reasons, it does not execute, write files, or
re-derive the reproduction. Anthropic's `/security-review` says this to its own
filter sub-tasks — *"you do not need to run commands to reproduce the
vulnerability, just read the code to determine if it is a real vulnerability. Do
not use the bash tool or write to any files."* It is the cheaper half of the
discipline, because a refuter that cannot re-run anything has to engage with the
claim exactly as written.

**Bound what crosses to a single artifact.** Fresh context is not enough on its
own: hand over your write-up and the refuter inherits its framing; hand over your
session and it inherits your dead ends. The strong form ships **only the
reproducible artifact** — the proof of concept, the failing command, the
`file:line` — and nothing else. Anthropic's defending-code reference harness
states it precisely: its grader reproduces each crash *"in a fresh container that
the find agent hasn't touched"*, and *"the only thing that crosses over from the
find agent to the grader is the proof of concept it produced."* Where no artifact
can be produced, that is itself the result: a finding with nothing to hand over
is a finding you have not reproduced (§2).

**Score the verdict; do not narrate it.** A refuter that returns prose returns a
judgement you then re-judge, which is the anchoring the pass exists to escape.
Require a number — `/security-review` scores confidence 1–10 and **drops
everything below 8** — and fix the bar *before* you see the findings. The
threshold is a policy about what the report is for, so state it in the
methodology (`rules/01` §1): a pre-merge gate that must not cry wolf sits high; a
one-off deep audit, where a missed Critical is the expensive error, sits lower
and ships the near-misses marked "needs verification" rather than dropping them
silently. Either way the cut is reviewable, which a paragraph of hedging is not.

A number is not a fact. It is a forcing function that makes disagreement visible,
and like every other number in this file it is a claim about a process you must
have watched work (`sota-code-security` rules/12 §2.2).

Scale it to stakes: every Critical/High gets refuted, always. Mediums get a pass
when the audit is high-stakes or the finding drives an expensive fix. Skip it for
Low/Info hygiene items — the overhead outruns the value.

Two failure modes to avoid:

- **The rubber-stamp refuter.** An agent told to "verify" agrees. Prompt it to
  *refute*, give it the code rather than your summary, and do not show it your
  confidence level — a refuter that reads "I'm certain this is exploitable"
  inherits the certainty.
- **Refuting the description instead of the code.** The refuter must open the
  file at the pinned commit. A refutation built on the finding's prose only
  tests your writing.

## 5. Report structure

Deliver in exactly this order:

1. **Executive summary** — overall posture in plain language, counts by
   severity, the top 3–5 risks and what they mean for the business. A
   non-engineer must be able to read only this section and make decisions.
   **The posture is capped by the worst thing standing**, not averaged over the
   findings: no summary may read better than *"not ready"* while an unfixed
   Critical, a missing authorization check on sensitive data, a non-idempotent
   payment or fulfilment path, or an unrecoverable migration is in the list — and
   none may read better than *"ready with caveats"* while CI is red or the
   crown-jewel path was never exercised end to end. A single blocker outranks
   twenty clean domains; the executive summary is the one place where averaging
   is a lie, because it is the only section most readers will finish.
2. **Scope & methodology** — repos and commit hash, what was and was not
   covered (with the recorded exclusions from `rules/01` §1), standards asserted
   against, tools run with exact versions and commands, audit date. This
   makes the audit reproducible and bounds its claims. Close it with **evidence
   not obtained** — the specific artifact that was unavailable and *what it would
   change*: "no production logs, so the rate limiter's effect at real traffic is
   unverified — a day of 429 counts would settle finding H-3 either way." An
   exclusion says what you skipped; this says what the reader can go get to move
   a verdict. It is also the honest home for every claim that had to be softened:
   an unobtainable check named here is bounded, the same check left unmentioned
   reads as one that passed.
3. **Decision ledger** — the §3 table: each significant decision →
   JUSTIFIED / STALE / UNJUSTIFIED / UNVERIFIABLE, with the recorded rationale
   and the evidence you re-checked. Omit the section only if the repo has no
   discoverable decisions; say so if you do.
4. **Findings** — grouped Critical → High → Medium → Low → Info; within a
   severity, ordered by exploitability. Each in the full §2 evidence block, and
   each Critical/High having survived the §4 refutation pass.
5. **Prioritized remediation roadmap** — *not a finding dump in severity
   order*. Sequence by **risk-reduction-per-effort**: quick critical wins
   first (trivial/small fixes to Critical/High), then high-impact larger
   work, then hardening. Group related fixes that share a root cause or a
   code area into one work item. The reader should be able to start work
   from the roadmap alone.
6. **Positive observations** — what is already done well (good patterns,
   solid boundaries, tooling in place), so it is preserved through
   remediation rather than accidentally regressed.
7. **Appendix** — full triaged tool output, the inventory from `rules/01` §2, DFDs and
   trust-boundary sketches, suppression-comment review.

---

## Audit checklist — quality gate on the findings and the report

**Finding quality**
- [ ] Every finding has title, severity+justification, file:line@commit,
      minimal evidence, standard mapping, concrete impact, diff-level
      remediation, and effort estimate?
- [ ] Borderline severities state the deciding assumption explicitly?
- [ ] Every recorded verdict — ledger entry, refutation, triage dismissal — is
      **self-contained and decision-enabling**, restating the evidence rather than
      saying "unchanged" / "superseded" / "already covered" (§3)?
- [ ] Executive-summary posture **capped by the worst blocker standing**, not
      averaged, and no better than "ready with caveats" on a red CI or an
      unexercised crown-jewel path (§5)?
- [ ] Scope & methodology ends with **evidence not obtained** — what was
      unavailable and which verdict it would move (§5)?
- [ ] Uncertain findings marked "needs verification", not asserted?
- [ ] **Every Critical/High names its chain** — reach, primitive, boundary
      crossing, and (where exfiltration is the impact) channel — each leg
      pointed at code rather than assumed (§1)?
- [ ] On a **diff-scoped** review, findings rated against the code the change
      replaced, with a residual gap in a new mitigation reported as a hardening
      item against the codebase rather than as a regression in the fix (§1)?
- [ ] **Decision ledger reviewed** — expensive-to-reverse decisions reconstructed
      and classified JUSTIFIED / STALE / UNJUSTIFIED / UNVERIFIABLE, every number a
      decision rests on **re-measured this session** (or the decision marked
      unverifiable), and ledger-vs-code checked both directions (§3)?
- [ ] **Every Critical/High refuted by an independent pass** — a separate agent
      or a fresh-context hostile read prompted to *kill* the finding, working
      from the code and not from your write-up, with survivors kept and
      refutations recorded (§4)?
- [ ] Did each refuter get **less than the finder** — no execution, no writes —
      and did **only the artifact** cross over (the PoC, the failing command, the
      `file:line`), rather than your write-up or your session (§4a)?
- [ ] Does each refutation carry a **number** against a threshold fixed *before* the
      findings were seen, with the threshold stated in the methodology (§4a)?
- [ ] Is every finding whose evidence is a **behaviour** (crash, race, timing,
      agent- or model-produced) reproduced **N of N**, with both numbers reported
      rather than an unstated `1/1` (§2)?
- [ ] Every **refuted or downgraded** finding **swept** across the repository for
      the same pattern before it was dropped, with the sweep and its denominator
      recorded beside the refutation (§4)?
- [ ] Every **absence claim** ("no X found", "enforced everywhere") backed by a
      widened search plus a second independent method, with the search stated?
- [ ] Positive observations evidenced by **effect** (a rejection, a log, a test
      that fails when disabled), not by the control's mere presence?

**Report**
- [ ] Executive summary in plain language with severity counts and top
      3–5 risks?
- [ ] Scope/methodology section sufficient to reproduce the audit?
- [ ] Findings grouped by severity, ordered by exploitability within?
- [ ] Remediation roadmap sequenced by risk-reduction-per-effort, related
      fixes grouped — actionable without re-reading every finding?
- [ ] Positive observations included?
- [ ] No secret values anywhere in the report; leaks redacted and referenced
      by location only?

A report that ships unverified findings, raw tool dumps, or no prioritized
roadmap is itself a failed deliverable — treat missing evidence or missing
remediation as a blocker on the audit, not a polish item.
