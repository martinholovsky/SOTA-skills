# 13 — Context-Dependent Silence: correct here, broken there

Five defect classes that `rules/10` does not cover and `rules/11`'s diagnostics
point at but do not describe. What unites them is **conditionality**: each one is
genuinely correct under the condition you tested and silently wrong under the one
you shipped into — small input vs large, fresh artifact vs stale, the sample
format vs the next one, one component vs the seam between two, this environment
vs that one.

That is why they survive review. There is no wrong line to find: the code is
right, and the *condition* is what changed. A test written against the passing
condition passes forever, which makes every one of these invisible to the
same-context checks that would catch an ordinary bug.

**Read this after `rules/11` §2** — its diagnostics (duration, denominator,
cross-scale delta, telemetry silence, execution proof) are how you *notice* one of
these; this file is what you are looking at once you do. The inert-control catalog
is `rules/10`; proving a control works is `rules/12`.

## 1. Scale-dependent silence — correct small, broken large

Code that is right on fixtures and pathological or wrong in production, where the
difference is a number nobody crossed in a test.

Shapes to look for:

- **Unbounded traversal**: recursion without a depth cap; variable-length graph
  queries with no bound (`[:AST*]` rather than `[:AST*1..12]`, Cypher
  variable-length patterns, SQL recursive CTEs without a depth column). Unbounded
  is not "thorough" — it is a query that times out and returns nothing on the
  inputs that matter most.
- **Whole-input reads**: loading a file, table, or response fully into memory.
- **Per-item queries inside a loop** over an unbounded set (N+1).
- **Budgets that truncate rather than fail** (time, size, row, token caps).
- **Paths gated behind a size threshold that fixtures never cross** — chunking,
  sharding, pagination, streaming, multi-part upload. The gated branch is
  effectively untested code that only ever runs in production.

The tell: **the threshold is a literal in the code and no fixture crosses it.**

**Budget exhaustion is the silent sub-case worth its own rule.** A stage that
logs `skipped 12 rules (budget exhausted)` at INFO and returns a normal-looking
result has reported *partial* coverage as *complete*. The consumer cannot tell
"clean" from "clean as far as we got". Rule: a truncating budget degrades loudly
(rules/10 §3) **and** the result carries the partiality in its own value —
`coverage: partial`, `skipped: 12`, a distinct status — never only in a log line.
An audit finding here is the missing field, not the budget.

Proof required: state the trigger **numerically** (threshold, node count, row
count) and show the fixtures never reach it. Measure at both scales where cheap.
Performance framing of the same code → `sota-performance` rules/01; the fixture
side → `sota-testing` rules/03.

## 2. Stale-artifact no-op — a key narrower than the behaviour

A cache, tag, fingerprint, or memo keyed on **fewer inputs than actually
determine the output**, so a real change is silently ignored and a stale artifact
is reused. Nothing errors; the pipeline is simply operating on last week's answer.

Ask of every key: **what input can change while the key stays constant?**

Where they hide: cache keys, memoization decorators, content hashes, image and
artifact tags, `if exists: skip`, lockfiles, generated code checked into the
repo, incremental-build stamps.

The usual omissions are not the source file — they are everything *around* it:
the tool or ruleset **version**, compiler/interpreter flags, the config that
selects behaviour, the environment or platform, and the schema the output is
shaped by. A scanner cache keyed on the target's hash but not on the ruleset
version keeps serving pre-rule-update results.

Proof required: change the omitted input, show the key is unchanged, and show the
stale artifact being reused (a cache-hit log, an unchanged output hash, a build
that skipped the step).

Rule for BUILD: the key covers every input that changes the output, tool versions
included; when unsure, add a version salt and take the cheap re-computation. See
`sota-devsecops` rules/04 for the security-relevant case (a cache key must also
carry the **trust context**, or a lower-trust build can poison a release).

## 3. Format assumption generalised from one sample

A parser built against one observed sample of an external interface, where a
sibling field, a newer version, or an edge case has another shape. Indexing into
external JSON/CSV (`x[0]`, chained `.get().get()`), assumed column counts, a
tagged union read as a flat record, an optional field treated as required.

**The silent sub-case: lenient parsers that accept malformed input and return a
plausible-but-wrong value** rather than raising. Verified 2026-07-30 on the
installed runtimes:

```js
parseInt("12abc")   // 12      — trailing garbage ignored
parseInt("")        // NaN     — which then propagates as a number
Number(" 12 ")      // 12      — surrounding whitespace accepted
```

```python
int(" 12 \n")       # 12       — whitespace accepted
float("1_0")        # 10.0     — underscore separators accepted: "1_0" is not 1.0
```

A corrupted or unexpected field therefore yields *a number*, not an error, and
every downstream stage treats it as data. This is a silent zero with a plausible
disguise.

Proof required: produce a **real sample from the installed version** that
violates the assumption — captured output, a recorded response, a fixture pulled
from the actual tool. Not a hypothetical.

Rule for BUILD: parse strictly at the boundary — reject trailing garbage, require
the declared type, validate against the interface's schema rather than against
the one response you saw — and record which interface **version** you validated
against, because that is the input §2 says your cache key is probably missing.

## 4. Contract drift by interaction — the seam nobody declared

Neither component is wrong. A change to a **producer** silently alters a layout
its **consumer** depends on: file name, directory shape, column order, separator,
units, encoding, per-label files where there was one combined file. Both sides
pass their own tests — each knows only its own side of the seam.

What separates this from §3 is *where the assumption lives*: §3 is a consumer
generalising from one sample of an external interface; this is an internal seam
**no schema describes**, so nothing exists for a registry or a compat check to
compare. Declared contracts are `sota-data-engineering` rules/04 and
`sota-testing` rules/04 — this class is what is left when none exists.

The high-yield trigger is a change that is not a code change: **selecting a
different backend, engine, driver, or frontend** for one class of input, where
the new one writes a different layout as a side effect. One config line moves,
the format change is undocumented, and the stage downstream reads zero rows and
reports "produced no output" — a silent zero (§1) with an innocent-looking cause.

Rule for BUILD: when you change a producer, **run the consumer on that
producer's real output** before merging; isolation tests pass on both sides while
the seam is broken. Rule for AUDIT: for every artifact handed between stages,
name its layout, its writer and its reader — where no schema pins them, the pair
is a finding awaiting its first change.

## 5. Location-dependent silence — correct here, empty there

A filter whose predicate can match something in the **ambient environment** rather
than in the data. The canonical shape is a path-component exclusion tested against an
**absolute** path:

```python
# BAD — p.parts is absolute, so this depends on where the checkout lives
files = sorted(p for p in ROOT.rglob("*.yaml") if "private" not in p.parts)

# GOOD — anchor the predicate to a known root
files = sorted(p for p in ROOT.rglob("*.yaml") if "private" not in p.relative_to(ROOT).parts)
```

On macOS `/var` is a symlink to `/private/var`, so a checkout made under `mktemp -d`
resolves beneath a `private` component and the filter matches **every** file. Verified
2026-08-16: `Path(mktemp_dir).resolve()` contains `private` in `.parts`. The suite then
reported `SKIPPED [1] ... got empty parameter set` for three parametrised tests, the
schema validation scanned nothing, and coverage still read 86%. It passed in the
author's working tree and failed only in a fresh clone — and would have passed on a
CI runner too, whose checkout path contains no `private` component.

Generalise past paths: **any predicate that can be satisfied by the environment** —
an absolute path component, a hostname, a username, an env var, a locale, a timezone —
differs between laptop, container and runner, and the failure mode is an empty
collection rather than an error. Two defences, and you want both:

- **Anchor the predicate** to a known root or an explicit allowlist, never to whatever
  the ambient string happens to contain.
- **Assert non-empty on every collection a suite iterates.** `assert files, "no
  fixtures found; this suite would vacuously pass"` is what turns silence into a
  failure — in the reported case it was the *only* reason the bug surfaced.

## Audit checklist

- [ ] **Scale**: does any control's behaviour change with input size — a
      size-gated path, a chunked branch, a timeout, a pagination limit — and does
      a fixture actually cross that threshold (§1)?
- [ ] **Staleness**: is any cache, fingerprint, tag or memo keyed on **less** than
      the behaviour it stands for, so a change that matters leaves the key equal
      (§2)?
- [ ] **One sample**: was any parser, matcher or format assumption written against
      a single reference implementation, and does it reject the *other* correct
      spelling (§3)?
- [ ] **The seam**: where two components each satisfy their own contract, is the
      contract *between* them declared anywhere, and does anything test it (§4)?
- [ ] **Location**: does the control depend on an environment fact — a default
      `char` signedness, a filesystem's case behaviour, a locale, a mounted
      path — that differs between where it was tested and where it runs (§5)?
- [ ] For every one found: is the **condition** written into a regression test,
      rather than the instance being patched (all sections)?
