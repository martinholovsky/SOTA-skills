# A rule the library had, that the task never reached (2026-08-27)

**What happened.** A maintenance session was asked *"how many tokens is
`skills/sota/SKILL.md`?"*, reached for another vendor's tokenizer, and reported a number
**54% under** the true count. The rule against exactly that — *"Measure with the provider's
token counter… Never use another provider's tokenizer"* — was already in
`sota-llm-engineering/rules/02` §2, correct and unchanged.

**So this was not a knowledge gap. It was a routing gap** — the verdict shape this repo
already names: **UNREACHABLE, not absent**.

## Why nothing routed there

| surface | what it said | did it match? |
|---|---|---|
| skill `description` (the **only** auto-loading text, and the whole classifier) | `token budget`, `context window` — but not `count`, `tokenizer`, `measure` | **no** |
| router routing table | *"**Building LLM features** — evals, prompt/context engineering…"* | **no** — the task was repo maintenance |
| router cross-cutting rules 5 and 8 | *"AI/LLM **features**"* | **no** |

A second, independent source also missed: the bundled `claude-api` skill carries a trigger
for *"Count tokens in a file / prompt / diff"*, and it only fired later, when an unrelated
API call failed. **Two sources held the answer and neither reached the decision.**

## The fix, and the proof it works

Three changes: `counting tokens` + `tokenizer` added to the description (the classifier);
the routing-table row broadened past *building features*; and router cross-cutting **rule
21**, deliberately shaped as a sibling of rule 17 (*"shell hides everywhere — including the
one-liners you type to verify a claim"*), because it is the same failure: **model facts hide
in your own tooling.**

Measured with a regression case, `claude-sonnet-5`, 3 samples, temp 0.7 — the description
temporarily reverted to get the "before":

| | correct | picks |
|---|---|---|
| **before the fix** | **0.00** | `sota-docs-workflow` ×3 |
| **after the fix** | **1.00** | `sota-llm-engineering` ×3 |

The pre-fix arm reproduced the original mis-route exactly, three times out of three, and
picked the *docs* skill for a token question. Raw:
[`desc-routing-regressions.json`](desc-routing-regressions.json).

**Read it as a regression check, not a lift.** One case, 3 samples: it shows the specific
mis-route is gone on the shipped (`with-xref`) catalogue, which is what a regression case
is for. The ablated `without-xref` arm moved between runs (0.67, then 0.33), so nothing
about cross-ref *value* should be read off a single case — that number lives in the
measurement set, which this file is deliberately kept out of.

## Two things found on the way

**The eval that proves this could not run at all.** `run-desc-routing.py` aborted with
`AttributeError` before its first API call: an ablation-assertion guard called
`.splitlines()` on the list `catalogue()` returns. The guard landed 2026-08-05 (PR #223,
an *instrument audit*); the last recorded run of this eval is **2026-07-13** — before it.
**A guard added to prevent a fake null made the instrument unrunnable, and nothing re-ran
it to notice** (`sota-code-security` rules/12 — watch the guard run). Fixed, and watched in
both directions: 9 descriptions differ normally, and a neutered `XREF_RE` still yields 0
and aborts.

**A regression case is not a measurement case.** Adding this case looks like the selection
bias `sota-llm-engineering/rules/01` §8 forbids — cases chosen because a model failed them.
It is the opposite: selection-by-outcome poisons a *measurement* set and is the entire point
of a *regression* one. The rule did not draw that line, so it now does, and these cases live
in their own file (`cases/desc-routing-regressions.jsonl`) behind a new `--cases` flag so
they can never be averaged into the published A/B.
