# Why SOTA-skills works — the measured case

Most prompt/skill collections *assert* they make an assistant better. This one
**measures it**, publishes the harness, and reports the numbers by dimension —
including the dimensions where the lift is small or zero.

**What the comparison is (and isn't).** Every number here is the library
**vs. an *unguided model*** — the same model, same task, with the library loaded
vs. with nothing. It is **not** a comparison against other skill libraries; we
have not benchmarked one, so we make no claim of superiority over them. The
control is clean: raw model-API calls (OpenRouter, no Claude Code config or skill
registry), and a **different** model grades each artifact **blind** to which arm
produced it. Reproduce it yourself with [`evals/`](../evals/); full methodology,
per-case data, and honest limitations are in the
[baseline writeup](../evals/results/2026-07-10/BASELINE.md).

## Measured lift over an unguided model

| Dimension | What it tests | Clean lift |
|---|---|---|
| **Completeness** | best practices embedded from a bare "build X" prompt (7 tasks) | **+0.36** (0.57 → 0.93) |
| **Freshness** | current 2026 facts (RFCs, CVEs, EOLs, versions, spec editions; 32) | **+0.50 to +0.65** |
| Routing | which skill area applies to a task | +0.09 to +0.14 |
| Audit | recognizing a textbook vulnerability | +0.00 |

The lift is only "small" if you measure the easy dimensions. The two that matter
most for *building* software are the two that are large:

- **Completeness is the thesis.** Told to "build X" (an API, an upload handler, a
  webhook receiver, a password-reset flow…) with **no** security or logging cues,
  a base model embeds ~57% of best practices and *systematically* skips tests,
  rate limiting, structured logging, and transport hardening. With the library
  applied through its **BUILD self-audit** (apply the non-negotiables, then check
  the diff against each rules file's audit checklist and fill every gap), coverage
  reaches ~93% across 7 tasks. What it *still* misses is instructive and honest:
  **transport** enforcement (3 of 7) and **rate limiting** (2 of 7) — cross-cutting
  concerns that live in one domain skill and so fall outside a task's routed scope
  unless the router's universal non-negotiables (operating principle 5) pull them
  in. This gap is **not** recoverable by "just verify via web search": an agent
  won't search *"should I add rate limiting"* — it simply omits it. That makes
  completeness the library's most defensible, least-redundant value.
- **Freshness — the base model is confidently wrong.** On current-2026 facts it
  doesn't merely lack knowledge, it *fabricates* plausible answers (in our 32-case
  set: inventing RFC 9334 for the Entity Attestation Token — it's 9711 — or
  claiming PostgreSQL 17 added `uuidv7()` when it was 18). The library carries the
  verified fact (with-library **0.97**, dead steady across samples; without **0.44
  ±0.03**). A web-search agent recovers much of this gap, so we report freshness
  as *partly* redundant for tool-using agents — stated plainly rather than inflated.
- **Audit +0.00 is reported, not hidden.** On isolated snippets a capable model
  already recognizes the vulnerability — even the 14 *harder* cases (subtle IDOR,
  SSRF allowlist bypass, TOCTOU, prototype pollution, multi-vuln) score 1.00 in
  both arms. A real audit lift would need whole-repo, cross-file context a snippet
  can't carry. We say so.

Robustness: the cheap dimensions are now run **multi-sample** (`--samples N
--temp T`); the freshness lift holds at 3 samples (with 0.97±0.00, without
0.44±0.03). Completeness/routing are still reported single-sample (deterministic
at temp 0) — averaging those is on the [roadmap](ROADMAP.md).

## What you get by design (beyond the numbers)

These are properties of how the library is built — verifiable in this repo, no
comparison to anyone else required.

1. **Auto-routing & composition — describe the task, not the files.** A
   [router skill](../skills/sota/SKILL.md) maps a request to the right
   *combination* of skills (e.g. a websocket endpoint pulls API-design + async +
   code-security together) and applies cross-cutting **universal non-negotiables**
   — rate limiting, transport enforcement, tests — on *any* endpoint regardless
   of which domain skill routed the task. A plain folder of skills has no such
   orchestration. `scripts/install.sh --routing` can make routing always-on.

2. **Freshness-maintained and cited.** Fast-moving claims (versions, RFCs, CVEs,
   EOLs) are web-verified against **primary sources**, not asserted from training
   data. A root `LAST-VERIFIED` stamp records the last full re-verification sweep;
   `scripts/check-freshness.sh` flags the library stale past a **6-month** window,
   and a **monthly** CI job ([`freshness.yml`](../.github/workflows/freshness.yml))
   enforces it. Version numbers appear only as semantic boundaries ("GA since",
   "fixed in"), never as rot-prone "current release is X".

3. **Build *and* audit from the same rules.** Every skill runs in two modes: BUILD
   (apply the rules while writing code) and AUDIT (review existing code). Audit
   findings are actionable, not vague — each cites
   `file:line | rule violated | severity | effort | fix` and maps to a standard
   (CWE, OWASP, MITRE ATT&CK/ATLAS) where one applies.

4. **CI-gated library quality.** Seven invariants
   ([`check-invariants.sh`](../scripts/check-invariants.sh)) block a bad change at
   the door: every file ≤ 500 lines (so the *right* rules load, not a wall of
   text), every rules file ends with an audit checklist, skill descriptions stay
   within the Agent-Skills spec cap, versions stay in lockstep, the router lists
   every skill, and no internal names leak. Plus gitleaks over the full history.

## Reproduce it

```sh
python3 evals/run-completeness.py     # completeness (build-tasks, blind judge)
python3 evals/run-clean.py --cases evals/cases/freshness.jsonl   # freshness
python3 evals/run-clean.py --cases evals/cases/router.jsonl      # routing
```

Set `OPENROUTER_API_KEY` (env or `.env`, never committed). See
[`evals/README.md`](../evals/README.md) for the full harness and
[`BASELINE.md`](../evals/results/2026-07-10/BASELINE.md) for the honest writeup.
