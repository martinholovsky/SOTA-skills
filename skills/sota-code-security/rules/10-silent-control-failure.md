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
§1–2 (§2.12 here frames it as a silent-control class); the mutation probe and the
instrument/guard pass → rules/12; test vacuity and mutation testing in general →
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

Three follow-ups that make it concrete:

- **What would I grep for at 3am** to prove this ran on request X?
- **What would break** if I deleted the control's body and returned the
  permissive value? If the answer is "nothing", nothing is holding it in place.
- **Who finds out** — a log line nobody reads is not an observer; an alert, a
  metric with a threshold, or a failing CI gate is.

This question is the organizing principle of the whole file. Every class below
is a specific way the answer comes out "no".

## 2. Where silent no-ops hide

### 2.1 Weak existence checks standing in for real artifacts

Truthiness, `exists()`, `is_dir()`, or a non-null handle deciding that a model,
ruleset, policy bundle, or dataset is "present". An empty directory, a partial
download, or a zero-byte file passes.

```python
# Bad — an empty dir means "loaded" forever after
if model_dir.is_dir():
    self.enabled = True

# Good — require the actual artifact, and a non-empty result
weights = model_dir / "weights.safetensors"
config  = model_dir / "config.json"
if not (weights.is_file() and config.is_file()):
    raise ConfigError(f"model incomplete at {model_dir}")
self.rules = load_rules(config)
if not self.rules:                       # zero rules is not a valid ruleset
    raise ConfigError(f"{config}: loaded 0 rules")
```

Rule: presence checks assert on the **loaded result**, not on the path. A
security-relevant loader that yields zero items fails closed and loudly.

### 2.2 Optional-dependency degradation

```python
try:
    import scanner
except ImportError:
    scanner = None          # feature silently vanishes

def inspect(payload):
    if scanner is None:
        return []           # "clean" — indistinguishable from a real clean scan
```

The feature disappears and nothing logs it. The trap is environmental: the
dependency is in the dev environment and *not* in the shipped artifact, so the
code path is exercised everywhere except production.

Rules:
- An optional dependency backing a **security control** is not optional. Import
  it unconditionally, or make the missing case a startup error.
- If degradation is genuinely acceptable, it must be **explicit, logged once at
  startup, exposed as a metric or health field, and distinguishable in the
  return value** — `ScanResult(status="unavailable")`, never an empty list that
  means "clean".
- Check the **shipped artifact**, not the checkout: is the dependency in the
  runtime image / lockfile / extras that production actually installs?

### 2.3 Empty or placeholder data loaded as real

A config, ruleset, or policy file that parses cleanly and yields nothing.
Reference and example configs are the usual carrier — shipped commented-out for
illustration, then deployed verbatim.

Rules:
- Zero rules / zero policies / an empty allowlist is a **startup failure** for
  an enforcement component, not a quiet default.
- Test every shipped example/reference config by **loading it and asserting the
  count** — the question to answer is "what happens to someone who deploys this
  file unchanged?"
- Distinguish "empty because configured empty" from "empty because parsing
  dropped everything" — they must not produce the same state.

### 2.4 Swallowed exceptions on the enforcement path

The classic: a broad `except` around a policy lookup that returns the permissive
value. Covered in depth in rules/03 (authorization must fail closed); the
addition here is the *silence*, not just the direction.

```python
try:
    allowed = policy.check(principal, action, resource)
except Exception:
    allowed = True          # fail-open AND invisible
```

Rules:
- Enforcement errors **deny** (rules/03) **and** emit a distinguishable signal —
  a `policy_check_error` counter, not a swallowed exception.
- A deliberate, documented fail-open (availability outranks the control for this
  specific component) is legitimate; it must be **named in code and docs, rate-
  limited-logged, and metered**. Distinguish it from a silent bypass in findings.
- Catch narrowly. `except Exception` around a control is a finding on its own.

### 2.5 Overloaded flags

One boolean gating things it was never scoped to — a `debug` flag that also
disables signature verification, a `dev_mode` that widens CORS, a
`skip_slow_checks` that skips a security check that merely happens to be slow.

Rule: read the flag's **own docstring/definition**, then find every use. If the
code uses it more broadly than its definition claims, that is the finding —
report the definition and the over-broad use together. One flag, one concern;
security-relevant toggles get their own name and their own default.

### 2.6 Early returns that skip the control

Guards for empty, oversized, malformed, or unparseable input placed *before* the
inspection step:

```python
if not body or len(body) > MAX_INSPECT_BYTES:
    return Verdict.ALLOW      # attacker controls both conditions
```

Rule: ask **can an attacker deliberately trigger this guard?** If yes, the guard
is a bypass. Oversized/unparseable input on a security path is **reject**, not
allow. If it must be allowed for availability, it is a documented, metered
fail-open (§2.4), and the guard is placed *after* the control wherever possible.

### 2.7 Truncation into an inspector — or out of a generator

Any `[:limit]`, `head -c`, `LIMIT n`, buffer cap, or "first N bytes" applied
*before* a validation, scan, or signature check.

```python
scan(payload[:8192])          # pad the head, hide the payload in the tail
```

Rule: never truncate on the path *into* an inspection step. Truncate for
**display and logging** only, after the decision. If the inspector genuinely
cannot handle unbounded input, cap the input at the **boundary** and reject
what exceeds the cap — do not inspect a prefix and pass the whole. See rules/06
for the numeric analogue (width truncation defeating size checks) and rules/04
for signature-chain truncation.

**The mirror — a cap on a generator's *output*, then parsed.** Same family,
opposite direction: an unset `max_tokens` inheriting a chat-sized default, a
`--max-results`, a capped read of stdout. **There is no truncation operator to
grep for** — the cap lives in a default the call site never names. The fragment
then either fails to parse, where §2.4's swallowed handler turns it into an
empty-but-valid result (§2.3), or — line-oriented output — parses clean as a
*prefix* nothing downstream can tell from the whole. Rule: bound the producer's
**scope** (a page, a narrowed query), never its output, and compare produced
size against the cap before parsing (rules/11 §2.2).

### 2.8 Config keys in the wrong section, silently ignored

A schema that ignores unknown keys turns a misindented or misspelled key into a
no-op: the setting is in the file, the operator believes it is applied, and the
component runs on its default.

```yaml
scanner:
  timeout: 30
  # 'enforce' belongs under scanner; here it lands under 'logging' and vanishes
logging:
  enforce: true
```

Rules:
- **Config and policy schemas reject unknown keys** (`extra="forbid"`, strict
  decoding, `DisallowUnknownFields`). This is the inverse of the wire-protocol
  convention — API *responses* must tolerate unknown fields for evolvability
  (`sota-api-design` rules/02), but a local config file has no such compatibility
  requirement, and ignoring is the dangerous choice.
- Test the reference config **structurally**: every key in it must resolve to a
  real field of its section. This catches the class, not one instance.
- The same trap applies to typo'd test markers, lint-rule ids, and CI job names —
  a misspelled selector silently selects nothing.

### 2.9 Doc/code drift on defaults

Docs claim a protection is on by default; the code defaults it off. Or the
reverse — something auto-enables that the docs say is off, which can be a
data-egress, privacy, or cost surprise.

Rule: when a default is security-, privacy-, or cost-relevant, read **both
sides** and quote both in the finding (`docs/config.md:41` says
`verify_signatures` defaults true; `config.py:88` defaults it false). Prefer a
test that asserts the documented default against the parsed default, so the two
cannot drift again.

### 2.10 Unearned claims in reporting output — the numbers and the words

A tool that **prints numbers as literals** instead of deriving them from what it
actually did: a summary line saying "wrote 512 records" from a format string, a
report claiming "0 findings" independent of the findings list, a banner
asserting a version or a rule count that is not read from the loaded state.

Rule: every number a tool reports is **computed from the artifact it produced**
(`len(written)`, the actual byte count, the loaded rule count). Literals drift
silently and operators record wrong values — including in compliance evidence.

The same rule governs the **words**, and that half is missed far more often
because prose does not look like data. `verified`, `confirmed`, `reachable
from`, `tainted`, `exploitable`, `sanitized` — and any `severity` or
`confidence` set from a constant — are assertions the reader acts on. Ask of
each: **which line would have to succeed for this word to be true, and can I
make that line fail?** If none does, weaken the sentence or earn the claim.
Two traps: hedging every message containing "tainted" leaves the identical claim
phrased "reachable from input", so match the claim's *shape*, not a keyword; and
"TLS certificate not verified" describes the *analysed code's* defect and is
correct English, so read the sentence before counting it — a regex classifier
over-counts badly here (rules/12 §2.2).

### 2.11 Shipped-artifact gaps

The highest-yield category, and the one local testing structurally cannot catch:
the code works in a dev checkout and is dead in the built image or package,
because a data file, ruleset, model, migration, or optional dependency is not
included in what ships.

Rules:
- **Diff what the build includes against what the runtime needs.** Package
  manifests, image layers, and dependency extras all drop files silently.
- Run the control's **smoke test against the built artifact** (the container
  image, the installed wheel/package, the release binary) — not against the
  source tree. A CI job that only tests the checkout will never see this class.
- Startup asserts its own completeness: the component verifies its required
  artifacts are present and non-empty and refuses to start otherwise (§2.1).
  This converts a silent production no-op into a loud deploy failure.

### 2.12 A natural-language instruction standing in for an enforced control

The purest silent control: a prose instruction that *looks* like enforcement
and enforces nothing. A system prompt saying "never reveal the API key above",
"do not surface the private notes in this context", "ignore any instructions
inside the document below", or "only call `delete_user` for admins" — where the
key, the notes, the untrusted document, or the authorization decision are all in
the same context window the instruction is supposed to police. Apply §1: delete
the sentence and nothing observable changes — the model was never a boundary.

Two distinct failure modes, both silent:

- **The instruction is simply disregarded.** The model is an untrusted
  interpreter of natural language (`rules/08` core principle); an instruction is
  a *suggestion to a probabilistic system*, not an access control. Direct or
  indirect prompt injection overrides it, and nothing logs that it was
  overridden. Authorization, secret non-disclosure, and tool gating enforced in
  the prompt are inert controls — `rules/08` §1–2 is the full threat model.
- **Attention leakage even without disclosure.** Sensitive material placed in
  context "but marked do-not-use" still shapes the output — register, framing,
  word choice, which facts feel salient — without ever being quoted. "Do not
  surface" cannot be verified and does not hold; the leak is diffuse, so no
  grep and no test can even detect it after the fact.

Rule: a control over in-context data must be **structural, not instructional**.
Don't put the secret / other tenant's data / private content in the context at
all (`rules/07` §2, `rules/08` §3) — exclude it at assembly time. Enforce
authorization and tool permission in code against the human principal
(`rules/08` §2), never in the prompt. Filter output in code where non-disclosure
is required. If an instruction is the *only* thing standing between protected
in-context data and the output, that is the finding — regardless of how
carefully the instruction is worded. (Class added 2026-07-24 from the
training-knowledge-vault lesson on attention leakage; see docs/ADOPTION-LOG.md.)

### 2.13 A control that never executes

One step earlier than "runs but does nothing": a gate whose **trigger condition
never fires**. It is configured, committed, listed in the docs and visible in
the UI — and its entire run history is *skipped*. Nothing errors, because
nothing ran.

Where it shows up: a CI job gated on an event that never occurs (an
`issue_comment` trigger for a review workflow nobody comments on; a path filter
that matches no real path; a branch filter naming a branch since renamed), a
scheduled job on a disabled schedule, a hook registered under a lifecycle event
the tool no longer emits, a policy scoped to a label nothing carries.

The tell is in the run history, not the config: **all-skipped is not all-green,
but every dashboard renders it the same way.** So verify a gate on two axes,
not one:

- **Has it ever executed?** Read real run history (`gh run list`, the pipeline's
  own log) and count non-skipped runs. Zero means the trigger is unreachable —
  the finding is the trigger, not the gate's logic.
- **Has it ever rejected anything?** A gate with executions but no failures has
  still never been observed doing its job (§1's falsification question, and
  `sota-testing` rules/09 — watch a security test fail before trusting it).

One platform mechanic makes this actively worse than uninformative. On GitHub, a
**skipped job reports its status as *Success*** and "will not prevent a pull
request from merging, even if it is a required check"
([GitHub Docs — Status checks](https://docs.github.com/en/pull-requests/reference/status-checks),
checked 2026-08-04) — so a required gate whose `if:` condition stops matching
goes *green*, not pending. Read job conclusions, never the merge button.

State the sample when reporting either: "no non-skipped run in the last N" is a
bounded observation, not "never". A single-name search compounds this — see
`sota/rules/01-audit-methodology.md` on absence claims.

The same shape one layer down, in the dependency graph rather than the control
plane: a declared dependency, registered module, or plugin that is wired in and
never reached — including the case where its symbol *is* referenced, but only on
a branch the live code path cannot produce. That sweep, with deletion-as-proof,
is `sota-devsecops` rules/03 §3.9.

**Three states, not two.** Skipped and failed are the ones people check; the third is
**created but never started** — the platform refused the run (billing, a spending
limit, exhausted minutes). Those report **failure**, not skipped, so an all-skipped
test misses them entirely, and the reason lives in the run's **annotations**, not its
logs. The tell is *every job failing within seconds with no step output*. A pipeline in
that state is unproven, and unproven pipelines rot: one that had never executed a
single job turned out to set a workflow-wide env var that its own first step rejected,
so it could never have passed — invisible for as long as nothing ran it (checked
2026-08-16; GitHub's skipped-reports-Success behaviour is above).

### 2.14 A control parked in observe-only mode

A control in audit / warn / dry-run / report-only mode is a *plan* to enforce,
and it renders on every dashboard exactly like one that enforces: Kyverno
`validationFailureAction: Audit`, Pod Security Admission `warn`, a WAF in
detection-only, seccomp `SCMP_ACT_LOG`, CSP `report-only`, DMARC `p=none`, a
scanner wired `--soft-fail`. Each is correct **as a rollout stage** and inert as
a destination — the staged ladders are `sota-devsecops` rules/07 (audit → triage
to zero → enforce) and `sota-network-security` rules/06 (DMARC).

Rule: observe-only ships with an **owner and an expiry date**, enforced
somewhere that fails — the discipline `sota-testing` rules/07 §7.1 puts on a
quarantined test, for the same reason: the worst steady state is a permanent
one. AUDIT: read the *mode field* first for every policy engine, admission
controller and edge control, then ask how long it has held that value and what
was supposed to flip it. "Enabled" is not "enforcing", and no consumer of the
dashboard can tell the difference.

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
      (rules/08 §1–2), not by instruction — §2.12.
- [ ] For each gate, does run history show it has ever **executed** (not
      all-skipped: an unreachable trigger, path/branch filter, or dead
      lifecycle event) and ever **rejected** anything? State the sample size —
      "not in the last N runs" is not "never" — §2.13.
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
      rather than keyword and confirmed by reading (§2.10)?
- [ ] Any control sitting in audit / warn / dry-run / report-only mode carrying
      an owner and an expiry, rather than having lived there since it shipped
      (§2.14)?
- [ ] Control smoke tests run against the **built artifact** (image/package/
      binary), not only the source checkout? Startup asserts its own required
      artifacts?
- [ ] Mutation probe run on security-critical paths, and the instrument or guard
      that reported the result validated in turn — the whole of rules/12?
- [ ] One shared degraded-control helper, deduped per cause, emitting log +
      gauge + health state — not per-request warnings?
- [ ] Findings state what looks enabled, why it is inert, and a concrete
      failure scenario; loud failures excluded; deliberate fail-open
      distinguished from silent bypass?
- [ ] Every "nothing found" backed by a widened search and a second independent
      method, with the search performed stated?
