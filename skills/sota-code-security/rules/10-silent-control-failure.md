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

**Proving a control here actually works is rules/12** — the mutation probe (replace
the body with the permissive no-op and watch what fails), plus the suspicion turned
on everything doing the checking: your scorers, gates and benchmarks, and the guard
that is an instance of what it guards.

**Finding these at codebase scale is rules/11** — the cheap diagnostics (duration
vs claimed work, printing every gate's denominator, cross-scale delta), plus five
classes that are correctness rather than security: scale-dependent silence, a cache
key narrower than the behaviour it gates, a parser generalised from one sample, a
producer/consumer seam no schema declares, and a filter whose predicate matches the
ambient environment (an absolute path, a hostname) so a collection is correct on one
machine and empty on another.
Sweep with rules/11 to decide *where* to apply this file.

Related: fail-open authorization → rules/03 §"authz bypass patterns"; integer
truncation → rules/06; prompt-as-control and the LLM threat model → rules/08
§1–2 (`rules/14` §3 here frames it as a silent-control class); the mutation probe and the
instrument/guard pass → rules/15; test vacuity and mutation testing in general →
`sota-testing` rules/06 and rules/09; degradation telemetry →
`sota-observability` rules/05; build/runtime artifact drift → `sota-devsecops`
rules/04.

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
on a token that blocks at zero when loose. The class entry is `rules/14` §4a.

Three follow-ups that make it concrete:

- **What would I grep for at 3am** to prove this ran on request X?
- **What would break** if I deleted the control's body and returned the
  permissive value? If the answer is "nothing", nothing is holding it in place.
- **Who finds out** — a log line nobody reads is not an observer; an alert, a
  metric with a threshold, or a failing CI gate is.

This question is the organizing principle of the whole file. Every class below
is a specific way the answer comes out "no".

## 2. Where silent no-ops hide — moved to `rules/16`

The catalogue of sixteen shapes (weak existence checks, degraded optional dependencies,
swallowed exceptions, truncation into an inspector, the control that is not in force, a flag
that parses, the aggregate that masks a detection) now lives in
**[rules/16](16-where-no-ops-hide.md)**, with its section numbers unchanged — ``sota-code-security` rules/16 §2.7` there is
``sota-code-security` rules/16 §2.7` as it always was. This file keeps the **method**; that one is the catalogue the method
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
- Emit all three signals, per `sota-observability` rules/05: a rate-limited WARN
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
- **A negative claim needs more proof than a positive one.** "There are no
  swallowed exceptions on the enforcement path" is a far stronger assertion than
  "here is one at `auth.py:88`" — a narrow search and a true absence look
  identical from the outside. Before asserting absence: widen the search
  (synonyms, other languages, generated code, vendored trees), use a **second
  independent method** (grep *and* AST/call-graph *and* a mutation run), and
  state the search you actually performed so the reader can judge its reach.
  That governs the **search**, which is discarded once it has answered. If the
  conclusion is instead left behind as a durable **guard**, it needs the stronger
  default in `sota-testing` rules/02 `sota-code-security` rules/16 §2.10: structure in AST, behaviour by execution,
  regex only where no parser exists.
- **Before claiming a fix works**: add the regression test, then **revert the fix
  and confirm the test fails**. A regression test is not evidence until it has
  been watched to fail. Report the exact command and the pass/fail counts —
  "should work" is not evidence (router operating principle 6).
- **Check the fixture before concluding the code is broken.** A bad test input
  looks exactly like a broken detector; a validator rejecting a deliberately
  malformed test value is working as designed.
- For anything that **changes enforcement behavior**, stop and present the
  decision rather than deciding silently (router operating principle 2).

---

## Audit checklist

- [ ] **The proxy question asked of every control's predicate** (§1): is the tested
      condition the dependency itself, or something that currently agrees with it? Name who
      can change one without the other. A proxy with no signal on divergence is a finding
      even while it currently works.
- [ ] **Every "it produced something" assertion names the field that carries the
      detection** (`sota-code-security` rules/16 §2.16): which attribute would be empty if the detector were deleted
      but its preprocessing left intact? An aggregate over a result mixing derived
      inputs with findings is a liveness check for the input stage, not a control.
- [ ] **Every optional capability a design depends on was invoked once, not read from
      `--help`** (`sota-code-security` rules/16 §2.15). Build-tag-gated flags parse and stub out; keep the output of the
      real call. High when the capability is the load-bearing half of a security control.

- [ ] Anything that writes **outward** on a schedule (a GitOps write-back
      controller, a PR bot, a sync job) verified at the **destination** rather
      than from its own success counters — its log reports the update it decided
      to make, not the write landing (`sota-kubernetes` rules/04 §7)?

- [ ] For each security control in scope: if it were a no-op, would any log,
      metric, response, or test differ? No → finding, regardless of current
      correctness.
- [ ] Presence/enablement decided by real loaded artifacts (non-zero rule count,
      required files present), not by `exists()`/`is_dir()`/truthiness?
- [ ] No `except ImportError` (or equivalent) silently disabling a control; every
      optional dependency backing a control present in the **shipped** artifact?
- [ ] Does a loader that yields zero rules/policies fail closed and loudly? Do
      shipped example/reference configs load to a non-empty, safe state?
- [ ] Broad `except` on an enforcement path returning the permissive value?
      Grep: `except Exception`/`catch (...)`/`rescue =>`/`recover()` near authz,
      verify, validate, scan → each is fail-open, silent, or both.
- [ ] Any flag used more broadly than its own definition claims (debug/dev_mode
      also disabling a security check)?
- [ ] Any prose instruction ("do not reveal/surface", "ignore instructions
      below", authz-in-prompt) standing in for an enforced boundary over data or
      permissions that live in the same context? Enforce structurally/in code
      (rules/08 §1–2), not by instruction — `rules/14` §3.
- [ ] For each gate, does run history show it has ever **executed** (not
      all-skipped: an unreachable trigger, path/branch filter, or dead
      lifecycle event) and ever **rejected** anything? State the sample size —
      "not in the last N runs" is not "never" — `rules/14` §4.
- [ ] Early-return guards on empty/oversized/unparseable input that an attacker
      can deliberately trigger to skip inspection?
- [ ] Any truncation (`[:N]`, byte caps, `LIMIT`) on the path *into* a scan,
      validation, or signature check — or a cap on a **generator's output**
      (unset `max_tokens`, `--max-results`) whose fragment is then parsed?
- [ ] Config/policy schemas reject unknown keys, and every key in the reference
      config resolves to a real field of its section (tested structurally)?
- [ ] Security/privacy/cost-relevant defaults verified in **both** docs and code,
      with a test pinning the documented default to the parsed one?
- [ ] Numbers in tool output derived from what was actually produced, never
      printed as literals — **and every verification word** (`verified`,
      `confirmed`, `reachable`, `tainted`, `sanitized`) plus every severity or
      confidence field traceable to a line that can fail, matched by claim shape
      rather than keyword and confirmed by reading (`rules/14` §1)?
- [ ] Any control sitting in audit / warn / dry-run / report-only mode carrying
      an owner and an expiry, rather than having lived there since it shipped
      (`rules/14` §5)?
- [ ] Control smoke tests run against the **built artifact** (image/package/
      binary), not only the source checkout? Startup asserts its own required
      artifacts?
- [ ] Mutation probe run on security-critical paths, and the instrument or guard
      that reported the result validated in turn — the whole of rules/12 and rules/15?
- [ ] One shared degraded-control helper, deduped per cause, emitting log +
      gauge + health state — not per-request warnings?
- [ ] Findings state what looks enabled, why it is inert, and a concrete
      failure scenario; loud failures excluded; deliberate fail-open
      distinguished from silent bypass?
- [ ] Every "nothing found" backed by a widened search and a second independent
      method, with the search performed stated?
