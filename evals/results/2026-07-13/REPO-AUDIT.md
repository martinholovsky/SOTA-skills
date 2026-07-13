# Cross-file repo-audit eval — result (2026-07-13)

**Question (roadmap item 3):** the snippet-audit eval saturates at 1.00 in both
arms — a capable model recognizes an isolated vulnerability with or without the
library. Does skill-guided auditing beat bare recognition when the defect is
**not in any single file**? This is the only path the roadmap identified to a
real audit lift.

**Answer: no lift — `+0.00` category and `+0.00` strict, on both
`claude-sonnet-4.6` and `claude-opus-4.8`.** When the whole repo fits in one
context, a capable model reads across files and catches cross-file defects with
or without the library.

## Method

`evals/run-repo-audit.py` (clean raw OpenRouter API, no sota config anywhere —
same isolation as `run-clean.py`). A 15-file FastAPI app
(`evals/cases/repo-audit/orderdesk/`, ~17 KB) is pasted with per-file headers
into both arms; the with-library arm additionally gets `skills/sota/SKILL.md` +
all `sota-code-security/rules/*.md`. Both arms report every vulnerability as
`{category, file}` using the fixed VOCAB. Scored against 8 planted defects
(`evals/cases/repo-audit.jsonl`), each **invisible in any single file**:

| id | category | spans | why it's cross-file |
|---|---|---|---|
| p1 | idor | orders.py ↔ orders_service.py | route delegates fetch-by-id to a service that never scopes to the caller |
| p2 | mass-assignment | models.py ↔ orders_service.py ↔ orders.py | update model exposes status/amount/user_id; service blindly applies all |
| p3 | sql-injection | search.py ↔ db.py | route f-strings user input into a string run by `db.raw_query` (no binding) |
| p4 | ssrf | orders.py ↔ http_client.py | route feeds a client URL to a generic fetch helper with no allowlist |
| p5 | missing-authentication | admin.py ↔ app.py | admin routes carry no auth dep; app mounts them with none either |
| p6 | business-logic-flaw | profile.py ↔ reset.py ↔ sessions.py | both credential-change paths skip the `revoke_all_for_user` contract sessions.py documents |
| p7 | tls-verification-disabled | config.py ↔ http_client.py | client trusts `settings.verify_tls`, which defaults to False |
| p8 | insecure-random | tokens.py ↔ sessions.py ↔ reset.py | non-CSPRNG token generator used for session + reset tokens |

Strict scoring requires the right category **and** attribution to a file in the
defect's `primary` set, so a lucky category guess pinned to the wrong file misses.

## Result

```
sonnet-4.6   without: cat 1.00 / strict 1.00   with: cat 1.00 / strict 1.00   LIFT +0.00 / +0.00
opus-4.8     without: cat 1.00 / strict 1.00   with: cat 1.00 / strict 1.00   LIFT +0.00 / +0.00
```

The without-library arm found all eight, correctly attributed, and independently
surfaced extras not planted (e.g. a log-injection in `app.py` logging
`request.url.path`, and the global-key rate-limit weakness in `reset.py`). It
even connected p6 across three files ("`change_password` and `confirm_reset` do
not call `revoke_all_for_user`") unaided. Raw predictions:
`repo-audit-sonnet46.json`, `repo-audit-opus48.json`.

## Interpretation — this refines the hypothesis, it doesn't kill audit value

The roadmap's assumption was that **cross-file** is the barrier. It isn't. The
real barrier is **context the model cannot hold at once**. This fixture (~17 KB)
fits entirely in the prompt, so "cross-file" collapses to "read the whole thing"
— and recognition, which the snippet eval already showed is saturated, does the
rest. Making defects span files changes nothing while every file is visible.

So the honest public claim stays exactly where it was: **the library's measured
lift is in BUILD-completeness and freshness, not in audit recognition.** We make
no audit-lift claim.

## The actual frontier (next harness, not this one)

To test whether the library's audit *methodology* helps, the repo must exceed
what the model can hold, forcing **selective reading** — where "which files to
open and what to connect" (the router's AUDIT workflow + threat-model
reconstruction) is the thing under test, not recognition. Concretely: a repo of
hundreds of files where the 8 defects are needles, run through an **agentic**
audit (tool-driven file reads under a context budget), with-library vs without.
That is a materially bigger harness (a real agent loop, not a single API call)
and is logged as the open follow-up. Until it exists, "does the library lift
audits?" is honestly **unproven**, and this eval closes the cheaper version of
the question: at snippet scale **and** at paste-the-whole-small-repo scale, the
answer is no lift.
