# BUILD mode — the reasoning behind the four steps

**The router holds the imperatives; this file holds the *why*.** `skills/sota/SKILL.md`
§BUILD is deliberately terse — it is read on every build, and length there is paid by
every task. Load this file when a build is large or unusual, when a step is being
skipped, or when you are changing the workflow itself.

**If you change anything here, see §5 — three other places may need the same change.**

## 1. Why "load lean" is correctness, not economy

Reading unrelated rules files is not free. A long context of similar-looking guidance
*measurably reduces* how many rules the model applies: transformer attention degrades
with length, and near-duplicate distractors compete with the rule that matters. Loading
five relevant rules files beats loading twenty, and the difference shows up as dropped
cross-cutting concerns rather than as a visible error.

This is the same effect [WHY-COMPLETENESS-RESIDUAL](../../../docs/WHY-COMPLETENESS-RESIDUAL.md)
documents: the residual is a **salience** problem, not a coverage gap. Adding the missing
rule made it worse; a short, salient reminder fixed it.

## 2. Why the plan comes before the code, and must be concrete

Named up front and verified at the end, constraints are followed far better than when
left implicit. The failure mode is a plan of vague intentions — "handle errors", "make it
secure" — which cannot be marked done or not-done at step 4 and therefore never is.

A checkable item states an outcome with a number or a subject:

- "rate-limit login to N/min per IP", not "add rate limiting"
- "reject uploads over N MB", not "validate uploads"
- "structured log on auth failure, no credentials in the line", not "add logging"

## 3. Why the self-audit gate runs LAST

A long build context makes mid-context rules fade. The final re-read is what recovers the
rate limiting, transport, tests and logging that a model otherwise drops silently —
**measured: this recovery is the bulk of the library's completeness lift**
(`evals/run-completeness.py`; 0.62 → 1.00 on `claude-sonnet-5`, 2026-08-21).

Doing it first, or continuously, does not work: at that point there is no diff to audit.

**For a large build, run it as a separate pass over the diff.** A fresh, minimal context
beats a long polluted one — the same reason the gate exists at all.

**Push the few truly critical invariants into deterministic gates.** A lint or CI check
that fails when an endpoint has no rate limiting or no TLS does not depend on attention.
Attention is not an enforcement mechanism; a test is.

## 4. The questions that catch inert work

- **The falsification question** — *if this control were silently a no-op, would anything
  observable differ?* No log, no metric, no failing test means the control is not done
  (`sota-code-security` rules/10).
- **Read back the artifact this run produced.** Where a control emits something — a
  record, a ledger line, a signature — it is wrong in the *output* long before it looks
  wrong in the source. Re-reading the code that writes it re-runs the reasoning that
  produced it, which is the weakest check available.
- **Ask for a fact to produce, not a judgment to make.** "Did you handle the error
  paths?" is answered from the same context that wrote them, and the answer is yes.
  "Paste every `except` in the diff and name what each one re-raises" cannot be answered
  without going and looking, and it is the *going and looking* that changes the output —
  the checked item comes back with the file:line attached rather than a verdict. So write
  each gate item as an artifact you must return: the grep and its hit count, the command
  and its exit code, the specific line that implements the requirement. A checklist of
  yes/no questions grades itself and passes; the same checklist phrased as evidence to
  produce cannot be satisfied without doing the work. This is why step 4 says *re-read*
  the checklist rather than *confirm* it, and why an item's denominator matters
  (`sota-code-security` rules/11 §2.2): "0 checked, 0 failed" is a pass shaped exactly
  like a real one.

## 5. Changing BUILD? Change these too

The BUILD workflow is **mirrored in four places**. They drift independently, and three of
the four fail silently.

| Surface | What it holds | What happens if you forget |
|---|---|---|
| `skills/sota/SKILL.md` §BUILD | the imperatives an agent reads every build | the change never ships |
| this file | the reasoning | the *why* rots away from the *what* |
| `evals/run-completeness.py` → `BUILD_WORKFLOW` | a hand-compressed mirror used as the eval's treatment arm | **the eval measures a workflow that is not shipped** |
| `evals/run-completeness.py` → `ROUTER_BUILD_SHA` | a hash pin over the router's BUILD section | the eval **aborts** — this one is loud, and is the guard that catches the row above |

The pin is the only reason this is survivable: edit §BUILD and the next eval run stops
and prints the new hash. **Never bump the hash without first re-reading the mirror
against the new §BUILD, clause by clause.** Then one of two things is true, and you must
say which in the commit:

- **an imperative changed** → re-sync `BUILD_WORKFLOW`, *then* set the new hash;
- **only prose moved** (rationale relocated here, wording tightened) → the mirror is
  already accurate; record the clause-by-clause check and set the hash alone.

Bumping the hash *without that check* is exactly the drift the guard exists to prevent,
and it happened once (2026-07-20, PR #119: a falsification clause added to the
router was missing from the mirror for four days while the project's most-cited number
was measured against a workflow that no longer shipped).

## Audit checklist (meta — for changes to this workflow)

- [ ] A change to §BUILD in the router is reflected in this file's reasoning, in
      `BUILD_WORKFLOW`, and in `ROUTER_BUILD_SHA` — all four, same commit.
- [ ] `ROUTER_BUILD_SHA` was updated only **after** the mirror was re-read against the
      new §BUILD, and the commit says whether an imperative changed or only prose moved.
      Run the guard once and confirm it passes rather than assuming it.
- [ ] The router's §BUILD still states every imperative; only reasoning lives here. An
      agent that never opens this file must still build correctly.
- [ ] Any new step is checkable at step 4 — it states an outcome, not an intention.
- [ ] Every gate item is phrased as **evidence to produce** (a grep, a command, a
      file:line), not a yes/no question about your own work (§4).
