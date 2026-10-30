# Silent Control Failure — controls that look enabled and do nothing

A crash is loud and gets fixed. This file is about the opposite failure: a
control, feature, or safeguard that **appears active but has no effect** — where
a broken system and a working system are indistinguishable from the outside.
Green health checks, a passing suite, `ENFORCEMENT: ENABLED` in the startup
banner, and zero protection.

Applies in both modes. In **BUILD**, every control you add must be built so its
absence is observable. In **AUDIT**, this is a distinct pass — the classes below
are invisible to source-pattern SAST, because the code is not *wrong*, it is
*inert*.

**Proving a control here actually works is [rules/12](12-verifying-the-verifier.md)** — the mutation probe (replace
the body with the permissive no-op and watch what fails), plus the suspicion turned
on everything doing the checking: your scorers, gates and benchmarks, and the guard
that is an instance of what it guards.

**Finding these at codebase scale is [rules/11](11-dead-path-diagnostics.md)** — the cheap diagnostics (duration
vs claimed work, printing every gate's denominator, cross-scale delta), plus five
classes that are correctness rather than security: scale-dependent silence, a cache
key narrower than the behaviour it gates, a parser generalised from one sample, a
producer/consumer seam no schema declares, and a filter whose predicate matches the
ambient environment (an absolute path, a hostname) so a collection is correct on one
machine and empty on another.
Sweep with [rules/11](11-dead-path-diagnostics.md) to decide *where* to apply this file.

Related: fail-open authorization → [rules/03](03-authorization.md) §"authz bypass patterns"; integer
truncation → [rules/06](06-memory-resource-safety.md); prompt-as-control and the LLM threat model → [rules/08](08-llm-ai-security.md)
§1–2 ([`rules/14`](14-control-not-in-force.md) §3 here frames it as a silent-control class); the mutation probe and the
instrument/guard pass → [rules/15](15-instruments-and-guards.md); test vacuity and mutation testing in general →
[`sota-testing` rules/06](../../sota-testing/rules/06-property-fuzzing-mutation.md) and [rules/09](../../sota-testing/rules/09-security-testing.md); degradation telemetry →
[`sota-observability` rules/05](../../sota-observability/rules/05-operational-readiness.md); build/runtime artifact drift → [`sota-devsecops`
rules/04](../../sota-devsecops/rules/04-build-containers.md).

---

## 1. The falsification question

For every control you write or examine, ask:

> If this were silently a no-op, would anything I can observe look different?

If the answer is **no**, that *is* the finding — whether or not the control is
currently broken. Absence of a signal is the bug. A control whose success and
whose total failure produce identical logs, identical metrics, and identical
responses is unfalsifiable, and unfalsifiable controls decay into no-ops without
anyone noticing.

**The falsification question does not catch every broken control, and the gap is
specific.** It finds controls that are *inert*. It misses controls that are **correctly
enforcing the wrong predicate** — there, something observable *does* differ (a refusal, a
missing signature, an error), so the first question answers "yes" and the control is still
wrong. Field-reported as four instances in a single session, by an author who had just
documented the shape:

| the check asked | the question that mattered |
|---|---|
| is `commit.gpgsign` true? | is a signing key configured? |
| does the encoder round-trip? | does the writer produce what the verifier expects? |
| does the `--sk` flag exist? | is `--sk` *implemented* in this binary? |
| is there a TTY? | can a PIN be collected here? |

Each substitutes an **observable proxy** for the **actual precondition**. The proxy is
easier to test, correct when written, and drifts later — because the proxy and the
precondition are configured by different people, in different files, at different times.
So ask a second question of every control:

> **The proxy question.** Is this the thing I actually depend on, or something that
> currently agrees with it? Then: *who can change one without changing the other, and
> would I find out?*

If the answer to the second is "a different file, a different person, no signal", the
predicate is a proxy and it will drift. Test the dependency itself. Where it genuinely
cannot be tested directly, **record the substitution in a comment at the site, including
the direction each error fails in** — the two directions are rarely symmetric: one instance
above blocked legitimate work when strict, and would have spent one of three PIN attempts
on a token that blocks at zero when loose. The class entry is [`rules/14`](14-control-not-in-force.md) §4a.

Three follow-ups that make it concrete:

- **What would I grep for at 3am** to prove this ran on request X?
- **What would break** if I deleted the control's body and returned the
  permissive value? If the answer is "nothing", nothing is holding it in place.
- **Who finds out** — a log line nobody reads is not an observer; an alert, a
  metric with a threshold, or a failing CI gate is.

This question is the organizing principle of the whole file. Every class below
is a specific way the answer comes out "no".

## 2. Where silent no-ops hide — moved to [`rules/16`](16-where-no-ops-hide.md)

*(audited in [rules/16](16-where-no-ops-hide.md))* — a pointer stub; the catalogue and its checklist items live in rules/16.

The catalogue of sixteen shapes (weak existence checks, degraded optional dependencies,
swallowed exceptions, truncation into an inspector, the control that is not in force, a flag
that parses, the aggregate that masks a detection) now lives in
**[rules/16](16-where-no-ops-hide.md)**, with its section numbers unchanged — what was §2.7 here is
[`rules/16`](16-where-no-ops-hide.md) §2.7 there. This file keeps the **method**; that one is the catalogue the method
searches. Split 2026-09-12 at 484 of 500 lines (ROADMAP 55).

## 3. Make degradation loud — one helper, deduped per cause

When a control cannot do its job, exactly one mechanism reports it. Scattering
ad-hoc `logger.warning` calls produces per-request noise that gets filtered, and
filtered warnings are invisible — which returns the system to silent failure.

Design:

- **One shared helper**, e.g. `control_degraded(control, reason, detail)`, used
  by every control in the codebase.
- **Deduplicate per cause, not per request** — log once per (control, reason)
  per process or per interval. Per-request warnings get rate-limited away by
  operators and stop being read.
- Emit all three signals, per [`sota-observability` rules/05](../../sota-observability/rules/05-operational-readiness.md): a rate-limited WARN
  log, a **gauge** (`control_degraded{control="scanner",reason="model_missing"}`)
  that stays 1 while degraded, and a span/response attribute so a single
  request's degradation is traceable.
- **Surface it in the health/readiness output** — a component running without its
  enforcement path is not healthy, and "degraded" must be a distinct state from
  "ok".
- Alert on the gauge being 1 for longer than a deploy: fallbacks are for
  surviving the night, not for permanent operation.

## 4. Evidence rules for this hunt

- **Read the code in full context.** No speculation, no pattern-matching. The
  whole point of this class is that it looks fine.
- Finding format (the canonical `file:line | rule | severity | effort | fix`,
  with the middle expanded for this class): **what looks enabled | why it is
  silently a no-op | a concrete failure scenario with specific inputs/state →
  wrong behavior**.
- **If the code logs loudly or raises, it is not silent** — say so and exclude
  it. Loud failures belong to other rules files.
- **Separate "silently broken" from "documented and deliberate"** and state
  which. A metered, documented fail-open is a design decision to review, not a
  defect to report as one.
- **Say "nothing found" per category** rather than padding with weak findings.
  An honest empty category is a result.
- **A negative claim needs more proof than a positive one** ("no swallowed exceptions
  on the enforcement path"): widen the search, confirm by a second independent method,
  and state the search performed — [`sota` rules/03](../../sota/rules/03-audit-findings.md) §2.
  That governs the **search**, which is discarded once it has answered. If the
  conclusion is instead left behind as a durable **guard**, it needs the stronger
  default in [`sota-testing` rules/02](../../sota-testing/rules/02-test-design-quality.md) §2.10: structure in AST, behaviour by execution,
  regex only where no parser exists.
- **Before claiming a fix works**: add the regression test, then **revert the fix
  and confirm the test fails**. A regression test is not evidence until it has
  been watched to fail. Report the exact command and the pass/fail counts —
  "should work" is not evidence (router operating principle 6). Revert and restore
  with file edits, in the foreground, never with a backgrounded shell chain: while the gate
  runs, the security control sits broken on disk ([`sota-testing` rules/06](../../sota-testing/rules/06-property-fuzzing-mutation.md) §6.3).
- **Check the fixture before concluding the code is broken.** A bad test input
  looks exactly like a broken detector; a validator rejecting a deliberately
  malformed test value is working as designed.
- For anything that **changes enforcement behavior**, stop and present the
  decision rather than deciding silently (router operating principle 2).

---

## 5. The mirror image: a control that fires too broadly

Everything above is about a control with **too little** effect. The mirror is a control with
too much: it fires on cases it was never meant to catch, **degrades the outcome it exists to
protect**, and — this is what makes it the same family — *looks like it is working the whole
time*. The inert control is invisible because nothing happens. This one is invisible because
**the thing that happens is what success looks like**.

The asymmetry is in the metric. A control's obvious health signal is *how often it fired*,
and for an over-firing control that number goes **up** as it gets worse. Blocks, denials and
redirects all get counted; the legitimate work that quietly took a worse path does not, so
the dashboard improves while the system degrades.

**The shape.** A blanket deny on a *tool* rather than on the *behaviour* — deny the search
binary instead of the unsafe search, deny the whole file type instead of the dangerous
member, deny an entire egress CIDR instead of the exfiltration path. It is easy to write,
easy to audit for presence, and it enforces a *worse* substitute: a blanket deny on a fast
literal search pushes the caller to a slower index that answers a different question, and
the caller now gets worse answers while the control reports a clean record.

**What makes it detectable.** Measure the control's **outcome**, not its firing rate:

- **A block rate has no meaning without a denominator of legitimate attempts.** "Blocked
  4,000 requests" is the numerator of an unknown fraction. The finding is the ratio, and
  you cannot get it by counting blocks — you have to sample what was blocked and read it.
- **Sample the blocked set and classify it by hand.** If a majority are legitimate, the
  control is not strict, it is broken — in the expensive direction, because the cost lands
  on the people doing the right thing and they route around it rather than report it.
- **Name the substitute.** Every deny has one: what does the caller do *instead*? If the
  answer is "a slower, less accurate or unlogged path", the control has moved the risk
  rather than removed it, and the new path is now unmonitored. A deny with no named
  substitute has not been designed, only installed.
- **A control that cannot be appealed cannot be measured.** With no exception path, the
  false positives never reach you; they become workarounds you will find in an incident.

**In BUILD, this is the falsification question run the other way** (§1): ask not only *would
anything differ if this were a no-op*, but *what legitimate case does this also catch, and
what will that caller do instead*. Both answers belong in the commit that adds the control.

---

## Audit checklist

- [ ] **Every deny/block/redirect control names its substitute** (§5): what does a
      legitimate caller do *instead*? A deny whose substitute is a slower, less accurate or
      unlogged path has moved the risk, not removed it — and the new path is unmonitored.
      A control installed with no answer here is a finding even while it "works".
- [ ] **No control is reported healthy on its firing count alone** (§5): a block rate is a
      numerator. Ask for the denominator of *legitimate* attempts, and for a hand-classified
      sample of what was blocked. `grep -rn 'blocked\|denied\|rejected' --include='*.md'`
      over dashboards and runbooks — a metric that rises as the control gets worse is the
      tell. No exception path means the false positives never reach you at all.
- [ ] **The proxy question asked of every control's predicate** (§1): is the tested
      condition the dependency itself, or something that currently agrees with it? Name who
      can change one without the other. A proxy with no signal on divergence is a finding
      even while it currently works.
- [ ] For each security control in scope (§1): if it were a no-op, would any log,
      metric, response, or test differ? No → finding, regardless of current
      correctness.
- [ ] One shared degraded-control helper, deduped per cause, emitting log +
      gauge + span/response attribute, with health/readiness reporting a distinct
      `degraded` state and an alert when the gauge stays 1 past a deploy — not
      per-request warnings (§3)?
- [ ] Findings state what looks enabled, why it is inert, and a concrete
      failure scenario; loud failures excluded; deliberate fail-open
      distinguished from silent bypass; every claimed fix backed by a regression
      test watched to fail with the fix reverted (command and counts quoted), the
      fixture checked before the code is called broken, and enforcement-changing
      fixes presented as a decision, not applied silently (§4)?
- [ ] Every "nothing found" stated per category and backed by a widened search and a
      second independent method, with the search performed stated (§4)?
