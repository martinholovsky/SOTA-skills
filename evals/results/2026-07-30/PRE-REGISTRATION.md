# Pre-registration — unscoped audit experiments A and B

**Written and pushed 2026-07-30, BEFORE either experiment ran.** The diagnosis
behind these was formed *after* seeing the dead-path null, which is exactly when a
tidy explanation is most seductive. The defence is that the confound is verifiable
in source rather than inferred from the result — but that is only worth anything if
the predictions are recorded first. They are below, with numbers, so a miss is
visible rather than reinterpretable.

## The diagnosis being tested

All five audit instruments that returned +0.00 **hand the model its search space**;
the BUILD instrument that returns +0.39 does not.

- `run-completeness.py` (+0.39) shows the model only `case['task']` — *"Build the
  backend REST API for a support-ticket feature…"*. The 12-item rubric is judge-only.
  The model must generate the consideration set itself.
- `run-repo-audit.py` (+0.00) tells the model the domain (*"auditing … for security
  vulnerabilities"*) **and hands it a 21-slug category vocabulary that contains all 8
  planted answers**.
- `run-silent-open.py`, `audit.jsonl`, `audit-hard.jsonl` (+0.00) hand over the
  snippet, which *is* the defect.
- `dead-path` (+0.00) named the four items to classify.

So "the library does not help an audit" has never actually been tested. What has
been tested is recognition, with the question supplied.

## Experiment A — is our own cross-file null an artifact of a leaky prompt?

Re-run the **existing** `cases/repo-audit/orderdesk` fixture (16 files, 8 planted
defects) with the domain framing and the category vocabulary removed. Brief:
*"Audit this repository and report every defect you find."* Nothing else.

Arms: unscoped-bare (n=3), unscoped-library (n=3), live sub-agents.
Scoring: hand-adjudicated against `cases/repo-audit.jsonl`. **Rule fixed in
advance:** a defect counts as found only if the report names the mechanism *and*
points at one of that case's `primary` files. Near-misses are recorded separately,
not counted.

**Predictions (point, plausible range):**

| Quantity | Prediction |
|---|---|
| scoped-bare (already measured, for reference) | 1.00 |
| **unscoped-bare** category recall | **0.65** (0.40–0.85) |
| **unscoped-library** category recall | **0.90** (0.75–1.00) |
| **delta (library − bare, unscoped)** | **+0.25** (0.00–0.45) |

Confidence that the delta exceeds +0.15: **~50%.** The model is strong and may
orient to security unprompted.

Secondary prediction, possibly more informative than the recall number: **at least
one bare agent will adopt a non-security frame** (code quality / style / general
review) and audit the wrong thing, while no library agent will.

## Experiment B — does the library change *what the model looks for*?

A new fixture where most code is fine, defects spanning two groups:

- **Control classes** (classic, in every model's repertoire): SQL injection,
  missing object-level authorization. If the bare arm misses these, the fixture is
  broken or the brief is unfair — this is the internal validity check.
- **Treatment classes** (real, documented in this library, outside the standard
  security-audit repertoire): an inert control whose result is discarded, a module
  reachable only from a branch that cannot execute, a cache key narrower than the
  behaviour it gates, an authorization check written as `assert`, and a size-gated
  path no test crosses.

Same unscoped brief, same adjudication rule, arms bare (n=3) vs library (n=3).
False positives counted in the same run — a "flag everything" strategy must not
score well.

**Predictions:**

| Quantity | Prediction |
|---|---|
| control classes, bare | **0.90** (0.70–1.00) |
| control classes, library | **0.95** (0.80–1.00) |
| **treatment classes, bare** | **0.35** (0.10–0.60) |
| **treatment classes, library** | **0.80** (0.55–1.00) |
| **delta on treatment classes** | **+0.45** (0.15–0.75) |
| false positives per agent, either arm | ≤ 2 |

Confidence that the treatment delta exceeds +0.15: **~65%.** Higher than A because
this manipulates the question-set directly rather than only the framing.

## What each outcome means, decided now

- **A drops and B separates** → our audit nulls were an artifact of leaky prompts;
  the audit half has a measurable lift and the eval program was mis-specified.
- **A holds at ceiling and B separates** → framing was not the crutch, but the
  *question set* is where the library earns its keep. The cleaner result.
- **Both null** → six instruments, three designs, one conclusion: a frontier model
  audits as well unaided as guided, at this scale. Say so plainly, stop building
  audit instruments, and move the measurement effort to BUILD.
- **B's control classes come back low** → the fixture or the brief is broken; fix
  it before reading anything into the treatment numbers.

No result here will be reported as a lift without the arms, the n, and this file
linked alongside it.
