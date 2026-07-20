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

Related: fail-open authorization → rules/03 §"authz bypass patterns"; integer
truncation → rules/06; test vacuity and mutation testing → `sota-testing`
rules/06 and rules/09; degradation telemetry → `sota-observability` rules/05;
build/runtime artifact drift → `sota-devsecops` rules/04.

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

### 2.7 Truncation before inspection

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

### 2.10 Hardcoded values in reporting output

A tool that **prints numbers as literals** instead of deriving them from what it
actually did: a summary line saying "wrote 512 records" from a format string, a
report claiming "0 findings" independent of the findings list, a banner
asserting a version or a rule count that is not read from the loaded state.

Rule: every number a tool reports is **computed from the artifact it produced**
(`len(written)`, the actual byte count, the loaded rule count). Literals drift
silently and operators record wrong values — including in compliance evidence.

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

## 3. Vacuous tests — the meta-case

A test that passes against broken code is worse than no test: it manufactures
false safety. `sota-testing` rules/02 (assertion-free, tautological), rules/06
(mutation testing), and rules/09 (security regression tests must be watched to
fail) own the general doctrine. What this file adds is the targeted procedure
for a **security control**:

1. Replace the control's body with the permissive no-op — `return []`,
   `return True`, `pass`.
2. Run the suite.
3. **Nothing fails ⇒ that control is untested**, regardless of how many tests
   name it. Report it as a finding, not as a coverage note.

Two traps that make step 3 lie:

- **Masked by a missing dependency.** The assertion passes because the feature
  was disabled for an *unrelated* reason (§2.2) — the real path never ran. Force
  the dependency present (monkeypatch the availability check) so the control is
  actually exercised.
- **The mutation did not take.** Editable installs, copied/rsync'd trees, stale
  bytecode, and cached images mean the original code may still be running.
  **Assert the mutation's runtime effect** — make the no-op print or raise once —
  before trusting a "zero failures" result.

Then build the **structural** test that catches the class: assert the loaded rule
count is non-zero, assert every reference-config key resolves, assert the
documented default equals the parsed default, assert the control's telemetry is
emitted. Instance tests catch today's bug; structural tests catch the next one.

## 4. Make degradation loud — one helper, deduped per cause

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

## 5. Evidence rules for this hunt

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
- [ ] Early-return guards on empty/oversized/unparseable input that an attacker
      can deliberately trigger to skip inspection?
- [ ] Any truncation (`[:N]`, byte caps, `LIMIT`) on the path *into* a scan,
      validation, or signature check?
- [ ] Config/policy schemas reject unknown keys, and every key in the reference
      config resolves to a real field of its section (tested structurally)?
- [ ] Security/privacy/cost-relevant defaults verified in **both** docs and code,
      with a test pinning the documented default to the parsed one?
- [ ] Numbers in tool output derived from what was actually produced, never
      printed as literals?
- [ ] Control smoke tests run against the **built artifact** (image/package/
      binary), not only the source checkout? Startup asserts its own required
      artifacts?
- [ ] Mutation probe run on security-critical paths (replace body with the
      permissive no-op) — with the dependency forced present and the mutation's
      runtime effect asserted before trusting a green run?
- [ ] One shared degraded-control helper, deduped per cause, emitting log +
      gauge + health state — not per-request warnings?
- [ ] Findings state what looks enabled, why it is inert, and a concrete
      failure scenario; loud failures excluded; deliberate fail-open
      distinguished from silent bypass?
- [ ] Every "nothing found" backed by a widened search and a second independent
      method, with the search performed stated?
