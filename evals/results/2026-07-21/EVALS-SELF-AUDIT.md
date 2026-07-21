# Silent-control audit of `evals/` — the library's own rules, applied to its harness

**Date:** 2026-07-21 · **Scope:** `evals/*.py` (10 runners) · **Method:**
`sota-code-security` rules/10, run unprompted as a deliberate pass

## Why

Four silent failures surfaced in this harness on 2026-07-20 — every one found
*incidentally*, none by looking. That is a bad way to learn about a measurement tool.
So: a deliberate pass, using the library's own silent-control rules on the code that
measures the library.

It is also the only honest test of whether rules/10 is useful when applied to a real
codebase rather than to fixtures. Four eval instruments say audit guidance produces
+0.00 on synthetic cases; this is the same guidance meeting code nobody wrote as a
test.

## The falsification question, applied

Both findings below share a property that makes them worse than an ordinary bug:
**their failure mode produces `+0.00`** — a result this project has legitimately
published many times (audit recall, cross-file audit, silent-control, audit
precision). A fake null would be indistinguishable from a real one, in a repo whose
entire credibility rests on reporting nulls honestly.

## F1 — an empty library corpus silently yields a "with-library" arm containing no library

`evals/run-clean.py:audit_library_context()` · also `run-repo-audit.py:library_context()`
· also `run-desc-routing.py:catalogue()`

```python
files = sorted(glob.glob(os.path.join(ROOT, "skills/sota-code-security/rules/*.md")))
return "\n\n".join(open(f, encoding="utf-8").read() for f in files)
```

**What looks enabled:** every `--cases audit|silent` run prints a with-library recall,
and every `run-repo-audit` / `run-desc-routing` run prints a lift.

**Why it is inert:** the glob's result count is never checked. A wrong cwd, a renamed
directory, or a moved rules folder yields `files == []`, the join yields `""`, and the
with-library arm is handed **no library at all** — while still producing a number.

**Concrete failure:** demonstrated live by pointing `ROOT` at a non-existent path —
`with-library corpus: 0 chars`, no error, no warning. The run would report
`with == without`, i.e. **+0.00**, and we would have published a false null believing it.

**Fix:** all three loaders now `sys.exit` on an empty corpus. Watched to fire.

## F2 — `--ablate` silently ablates nothing when its target is renamed

`evals/run-clean.py:audit_library_context(ablate=True)`

```python
files = [f for f in files if os.path.basename(f) != ABLATE_FILE]
```

**What looks enabled:** `--ablate` prints `ABLATED(-10-silent-control-failure.md)` in
the run header and reports a contribution figure.

**Why it is inert:** the filter is a filename equality test whose result is never
checked. Rename or move the target and the comprehension removes nothing — so the
"ablated" arm **is the full corpus**, and the tool reports a **fake +0.00
contribution** for the file under test.

**Concrete failure:** demonstrated live — with `ABLATE_FILE` pointed at a renamed
file, `removed=0 chars` while the header still claimed an ablation.

**Fix:** `--ablate` now aborts when the filter matches nothing. Watched to fire.

**This is the third instance of one pattern.** `run-adjudication.py` had the identical
defect keyed on a section *number* (caught 2026-07-20 when a renumber broke it), and
`run-completeness.py` had it as a drifted *mirror* (caught the same day). Every
ablation and every mirror in this harness is now guarded, because the class — *a
transformation whose result is never asserted* — kept recurring under different
disguises.

## Categories checked, nothing found

Stated per rules/10's evidence rules rather than padded with weak findings:

- **§2.2 optional-dependency degradation** — no `except ImportError` anywhere in
  `evals/`; every dependency is stdlib.
- **§2.4 swallowed enforcement exceptions** — the three `except` clauses are narrow
  (`UnicodeDecodeError, OSError` on a file read; `json.JSONDecodeError` with a
  re-raise) and none is on a scoring path.
- **§2.7 truncation before inspection** — no `[:N]` on a path into scoring.
- **§2.10 hardcoded reporting values** — every printed metric is computed
  (`sum(...)/len(...)`, `len(...)`); nothing is a literal.
- **§2.11 shipped-artifact gaps** — not applicable; the harness runs from the checkout.

## Limitations

- Single-pass manual review, not exhaustive; no mutation probe was run against the
  scoring functions themselves, which is the obvious next step (replace a `score()`
  body with a constant and confirm some check notices).
- `score.py` and `judge-live-build.py` got a lighter read than the runners.
- The three fixed loaders are guarded against *empty*, not against *wrong* — a glob
  that silently matches the wrong files would still pass.

## What this says about rules/10

Applied unprompted to a real codebase, it produced **two confirmed findings in ten
files**, both of the "produces a plausible number while doing nothing" class, and both
demonstrated live before being fixed. That is not a measured lift — no eval here can
score it — but it is the first evidence of the file doing the job it was written for
on code that was not built as a test case.
