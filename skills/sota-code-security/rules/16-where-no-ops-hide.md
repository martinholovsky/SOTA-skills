# 16 — Where silent no-ops hide: the catalogue

Split out of `rules/10` on 2026-09-12 (ROADMAP 55). `rules/10` holds the *method* — the
falsification question, making degradation loud, the evidence rules — and had reached
484 of its 500 lines with two more classes queued behind it. This file is the **catalogue**
it was carrying: sixteen shapes a control takes when it is present, looks enabled, and
enforces nothing. Catalogues are what grow, which is why this is the half that moved.

**The section numbers are deliberately unchanged.** They read oddly in a file that starts at
§2, and that is the price of making every inbound citation a pure path substitution
(`rules/10 §2.7` → `rules/16 §2.7`) rather than a renumbering that has to be checked one
reference at a time. The last split in this repo chose its seam by citations and broke zero
references; this follows it.

**Read `rules/10` first** — it is the method, and this is what the method finds.

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

### 2.10–2.14 — the control that is not in force

Moved to [`rules/14`](14-control-not-in-force.md): unearned claims in reporting
output, shipped-artifact gaps, an instruction standing in for an enforced control,
a control that never executes, and one parked in observe-only mode. §2.1–2.9 above
are a control that **runs** and does nothing; those five are a control that is not
**there** — and you find them by asking what ships, what fires, and what the output
is entitled to say, not by reading the control's body.

### 2.15 A flag that parses is not a feature that works

`--help` is a claim about the **source tree**, not about **your binary**. Build-tag-gated
features — Go `-tags`, Rust feature flags, `./configure` options, optional shared libraries
— routinely leave the *interface* compiled in and the *implementation* stubbed. The flag
parses, the docs list it, and it fails only when it reaches the hardware or library that is
not there.

Field-reported: Homebrew's `cosign` v3.1.2 lists `--sk` and `--slot` in `--help` because it
is built without the `pivkey` tag. `cosign public-key --sk` returns
`Error: opening piv token: unimplemented`. (`cosign piv-tool` is more honest and says
"not built with piv-tool support", but `--sk` gives no warning until it meets real hardware.)
Had a key-custody design been settled from `--help`, the discovery would have arrived
against a release deadline with decisions already built on top.

**Before a design depends on an optional capability, invoke it once against the real thing
and keep the output.** The cheapest form is usually a read-only call — `public-key`,
`--version`, a dry run — that still traverses the gated code path. Package managers are the
usual source: distribution builds drop optional tags to avoid a CGO or driver dependency.
Same family as the compiled-out `assert` in `rules/11` §4 — the interface survives the
build, the behaviour does not.

### 2.16 The aggregate that masks the detection

`rules/10` §1's question, asked of a *field* rather than a control. A positive control
asserted that an analysis engine had "fired" by summing every list on its result
object:

```python
def _result_size(result) -> int:
    return sum(len(v) for v in vars(result).values() if isinstance(v, list))

assert _result_size(result) > 0          # "the engine fired"
```

The result type carries **both halves of the analysis** — what the engine derived
in order to reason, and what it concluded:

```python
@dataclass
class Result:
    assumptions:  list[Assumption]    # INPUT: derived to reason over
    enforcements: list[Enforcement]   # INPUT
    chains:       list[DependencyChain]
    breaks:       list[Break]         # <-- the DETECTION. This is the finding.
```

The inputs outnumber the outputs and outlive them: preprocessing populates
`assumptions` on any real graph, so the aggregate is non-empty whether or not
detection works. Field-reported 2026-09-05, measured across 11 languages:
`breaks` was empty on **all nine** cells where this engine was registered as
having a positive control, a sibling engine had zero `violations` on three of its
ten, and **12 of 35 controls were green on a result containing no detections** —
and would have stayed green if detection stopped entirely.

Two neighbouring diagnostics miss it. `rules/11` §2.2 is about the *denominator*,
and here the denominator was healthy: the engines ran over a real graph and
returned rows. `rules/15` §2.1's "instrument that cannot fail" is about a scorer
returning a plausible number whatever it is handed; this instrument *could* fail,
just never for the reason it existed. The distinct defect is that **the assertion
aggregates over a heterogeneous result in which the inputs outnumber and outlive
the outputs.**

**The discriminating question.** *Which attribute would be empty if the detector
were deleted but its preprocessing left intact?* Assert on that one. An aggregate
over a result mixing derived inputs with findings is not a positive control; it
is a liveness check for the input stage.

**And do not simply tighten it.** When the honest assertion turns green cells red
with no evidence of a regression — nothing had ever measured `breaks` — that
manufactures a red build out of a measurement gap. Assert semantically on what
the engine *does* produce, and give the empty field **its own test recording the
measured fact**, so it has an owner and gets tightened the day the field becomes
non-empty. `rules/11` §2.6's metamorphic relation is the tool for that second
half.

## Audit checklist

- [ ] Every control in the diff checked against **this catalogue**, not just against "is it
      present": weak existence checks (§2.1), degraded optional dependencies (§2.2), empty or
      placeholder data treated as real (§2.3), swallowed exceptions on the enforcement path
      (§2.4), overloaded flags (§2.5), early returns that skip it (§2.6), truncation into an
      inspector (§2.7), config keys in the wrong section (§2.8), doc/code drift (§2.9)
- [ ] **The control that is not in force** (the 2.10–2.14 group) — installed, configured, and not
      actually applied to the path it is credited with
- [ ] **A flag that parses is not a feature that works** (§2.15) — the parser accepting it
      proves the parser, not the behaviour
- [ ] **No aggregate masking a detection** (§2.16) — a mean, a rollup or a "worst case" that
      makes a real signal disappear into the total
