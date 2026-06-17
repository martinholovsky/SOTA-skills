---
name: sota-python
description: >-
  State-of-the-art Python engineering (2026 baseline) for both writing new Python and
  auditing existing Python code. Covers uv-based tooling and project setup, strict typing,
  idioms and pitfalls, asyncio structured concurrency, security (injection, deserialization,
  supply chain), performance, and FastAPI/Django/pytest practice. Use whenever the task
  involves Python source, pyproject.toml, requirements files, or Python tooling — building
  features, scaffolding projects, reviewing PRs, or hunting bugs/vulnerabilities.
  Trigger keywords: Python, pip, uv, pyproject, asyncio, Django, FastAPI, pytest, type hints,
  mypy, ruff, pydantic, SQLAlchemy, venv.
---

# SOTA Python (2026)

## Purpose

This skill encodes the 2026 state of the art for Python: modern toolchain (uv + ruff + one
strict type checker), Python ≥3.12 idioms, structured async, security-by-default, and
measured performance work. It serves two modes:

- **BUILD** — writing new code or modifying existing code to this standard.
- **AUDIT** — reviewing existing code against this standard and reporting findings.

The detailed rules live in `rules/*.md`. Read SKILL.md fully; load rules files on demand per
the index table below. When in doubt between two rules files, the index's "read when" column
decides.

## BUILD mode

When creating or modifying Python code:

1. **Establish context first.** Check `pyproject.toml`, `uv.lock`, `.python-version`, ruff
   config, and the type checker in use. Match the project's floor (e.g., no `type` aliases
   on a 3.10 project). For a *new* project, scaffold per rules/01: `uv init`, src/ layout,
   ruff with the standard select, strict checker, pre-commit.
2. **Default stack:** uv for env/deps (commit the lockfile), `ruff check --fix` + `ruff
   format` before presenting code, full annotations on everything public, pydantic v2 at
   trust boundaries, frozen+slots dataclasses inside, `pathlib`, `logging` with lazy `%`
   formatting.
3. **Async code** follows rules/04 unconditionally: TaskGroup scopes, no blocking calls in
   coroutines, timeouts on external awaits, no unreferenced `create_task`.
4. **Security posture is non-optional** even when unrequested: parameterized SQL, argv-list
   subprocess, `secrets` for tokens, safe extraction, no pickle/eval on external data.
5. **Tests accompany code:** pytest, fixtures + parametrize, independent tests; property
   tests (hypothesis) for invariant-bearing code (rules/07 §3).
6. **Performance:** correct data structures by default (set membership, join, generators);
   anything beyond that requires a profile first (rules/06 §1). Don't micro-optimize cold code.
7. **Verify before declaring done:** run `ruff check`, the project's type checker, and the
   test suite via `uv run`. Code that doesn't pass these is not done.

## AUDIT mode

When reviewing existing Python code:

1. **Sweep mechanically first.** Run the "Audit checklist" block at the end of every relevant
   rules file — they are ordered grep/ruff/bandit commands. Start with
   `uvx ruff check --select F,B,S,ASYNC,DTZ,E722,BLE --statistics .` for a heat map, then
   `uvx bandit -r src/ -ll` and `uvx pip-audit` for security baselines.
2. **Then read for design:** trust-boundary placement (validation at edges?), exception
   strategy, async ownership of tasks, N+1 patterns, cache invalidation, test independence.
   Greps find syntax; you find architecture.
3. **Verify every finding** — open the file, confirm the context (a `pickle.loads` of a file
   the same process wrote with HMAC verification is not a CRITICAL). No finding ships on grep
   output alone. Note mitigations that are already present.
4. **Don't report style noise** a formatter/linter would auto-fix; mention once collectively
   ("run ruff format; 40 files drift") and move on.

### Severity conventions

| Severity | Meaning | Examples |
|---|---|---|
| CRITICAL | Exploitable now, or data loss/corruption | SQL injection, `pickle.loads`/`eval` on untrusted input, `shell=True` with user data, auth bypass |
| HIGH | Exploitable with preconditions, or production-breaking bug | path traversal, unsafe `extractall`, `random` for tokens, swallowed `CancelledError`, blocking call in async hot path, bare `except: pass` around critical logic, `verify=False` |
| MEDIUM | Correctness/maintenance risk, degraded ops | mutable default args, fire-and-forget tasks, unbounded `@cache` on user input, N+1 queries, missing lockfile in an app, no type checker in CI, edited applied migrations |
| LOW | Deviation from SOTA, friction, future risk | legacy typing forms, os.path usage, f-strings in log calls, flat layout in a library, bare `# type: ignore` |
| INFO | Worth knowing, no action forced | tooling consolidation opportunities, 3.13/3.14 features available after floor bump |

Confidence accompanies severity: **confirmed** (you traced the data flow) vs **suspected**
(pattern present, flow not fully traced — say what would confirm it).

### Finding format

```
[SEVERITY/confidence] short title
  File: src/pkg/module.py:42 (absolute path in final report)
  Issue: what is wrong, in one or two sentences, with the data-flow if security-relevant
  Evidence: the offending line(s), quoted
  Fix: concrete change — code snippet or exact rule reference (rules/05 §2)
```

Group findings by severity, CRITICAL first. End with: counts per severity, the mechanical
sweep commands you ran, and explicit "checked and clean" areas (so absence of findings is
information, not omission).

## Rules index

| File | Read this when... |
|---|---|
| `rules/01-tooling-project-setup.md` | starting/scaffolding a project; reviewing pyproject/uv/ruff/CI setup; choosing type checker; questions about uv lockfiles, PEP 723 scripts, src/ layout, 3.12–3.14 features, free-threading |
| `rules/02-typing-correctness.md` | annotating APIs; choosing TypedDict vs dataclass vs pydantic; Protocol vs ABC; generics/`Self`/`ParamSpec`; Any leaks; `assert_never` exhaustiveness; where runtime validation belongs |
| `rules/03-idioms-pitfalls.md` | any general Python code; mutable defaults, closures, comprehensions, context managers, pathlib, EAFP, dataclass/enum patterns, itertools/functools; designing exceptions; logging setup |
| `rules/04-async.md` | any `async def` in sight: TaskGroup vs gather, blocking-the-loop, fire-and-forget, timeouts/cancellation, async generators, anyio, sync-ORM-in-async bugs |
| `rules/05-security.md` | auditing for vulnerabilities; handling untrusted input; subprocess/SQL/paths/archives/secrets; pickle/eval/yaml; SSRF/XML; dependency auditing and supply chain |
| `rules/06-performance.md` | anything slow: profiling tool choice, hot-loop suspects, numpy/polars vectorization, functools caching caveats, threads vs processes vs asyncio, lazy imports/startup |
| `rules/07-frameworks-testing.md` | FastAPI (DI, boundary models, sync-in-async), Django (N+1, select_related, migrations), pytest (fixtures, parametrize, independence, hypothesis). **Test *strategy* — suite shape, TDD, doubles, test data, flake policy — lives in `sota-testing`; load it for any build that writes logic. This file owns Python runner mechanics only.** |

## Top-10 non-negotiables

1. **uv + committed lockfile; CI installs `--locked`.** No unlocked `pip install` in
   pipelines or images. (rules/01)
2. **One strict type checker gating CI; public APIs fully annotated; no `Any` leaking
   across module boundaries.** (rules/02)
3. **Validate at the boundary, trust inside:** pydantic v2 (`extra="forbid"`) where data
   enters; typed dataclasses within. Never pass raw parsed JSON deep into the core. (rules/02)
4. **Never `eval`/`exec`/`pickle.loads`/`yaml.load` on data you don't fully control.**
   (rules/05)
5. **SQL via bound parameters only; subprocess via argv lists with `shell=False`, `--`
   before user args.** (rules/05)
6. **No bare `except:`; no `except Exception: pass`; chain with `raise ... from e`;
   `except Exception` only at top-level boundaries with `logger.exception`.** (rules/03)
7. **Async: TaskGroup-owned tasks only; zero blocking calls in coroutines
   (`to_thread`/process pool instead); `asyncio.timeout` on every external await;
   re-raise `CancelledError`.** (rules/04)
8. **No mutable default arguments; context managers for every resource; `pathlib` +
   explicit `encoding="utf-8"`.** (rules/03)
9. **`secrets` (never `random`) for anything security-relevant; `compare_digest` for
   secret comparison; no hardcoded credentials; no `verify=False`.** (rules/05)
10. **Tests are independent (random order + parallel safe), fixture-based, parametrized;
    performance claims require a profile.** (rules/06, rules/07)
