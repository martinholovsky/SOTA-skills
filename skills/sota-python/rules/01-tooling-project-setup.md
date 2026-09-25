# 01 — Tooling & Project Setup

Modern Python: `uv` for everything package/env related, `pyproject.toml` as the
single source of truth, `ruff` for lint+format, one strict type checker, `src/` layout,
Python ≥3.12 target. Anything else needs a written justification.

## 1. uv is the default toolchain

Use `uv` for environments, dependency resolution, lockfiles, Python version management, and
tool running. It replaces pip, pip-tools, pipx, virtualenv, and most of poetry.

```bash
uv init --lib mypkg            # or --app; creates src/ layout + pyproject.toml
uv add httpx 'pydantic>=2.7'   # adds to pyproject + updates uv.lock
uv add --dev pytest ruff       # dev dependency group
uv sync --locked               # CI: install exactly the lockfile, fail if stale
uv run pytest                  # run inside the project env, no manual activation
uv python pin 3.13             # writes .python-version
uvx ruff check .               # ephemeral tool run (pipx replacement)
```

Rules:
- **Commit `uv.lock`.** Applications MUST commit it. Libraries commit it for dev reproducibility
  even though it isn't published.
- **CI installs with `uv sync --locked`** (or `--frozen`). Never bare `pip install -r requirements.txt`
  in new projects; if a legacy `requirements.txt` must exist, generate it:
  `uv export --format requirements-txt --output-file requirements.txt`.
- **A tool that is not uv gets `pylock.toml`, not a requirements file.** PEP 751 (Final,
  March 2025) is the standard, tool-neutral lock: every package with its artifact URLs, sizes
  and hashes, installable with no resolution at install time.
  `uv export --locked --format pylock.toml --no-emit-project -o pylock.toml` writes it (uv
  refuses any output name other than `pylock.toml` or `pylock.<name>.toml`, as the PEP
  requires). `uv.lock` stays the source of truth. Measured (uv 0.12.0): `uv pip sync
  pylock.toml` installed the locked set, and one altered sha256 made it exit 1. **A committed
  export can go stale**; in CI, re-run the same command and fail on a diff
  (`… && git diff --exit-code -- pylock.toml`). Use exactly the flags that produced the
  committed file: the export writes its own command line into the header, so the same
  dependencies exported with different flags differ too (measured).
- **Never `sudo pip install`, never install into the system interpreter.** Every project gets its
  own venv; `uv` makes this automatic.
- One-off scripts use **PEP 723 inline metadata** instead of polluting an env:

```python
# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx", "rich"]
# ///
import httpx
```

Run with `uv run script.py` — uv resolves and caches the deps. This is the correct form for
repo maintenance scripts; reject scripts that assume "whatever is installed globally".

Governance note: Astral (uv/ruff/ty) announced its acquisition by OpenAI in March 2026; the
tools remain permissively licensed and developed in the open. The technical recommendation
stands — weigh the ownership change like any vendor dependency when standardizing.

## 2. pyproject.toml — single source of truth

All metadata, dependencies, and tool config live in `pyproject.toml`. No `setup.py`, no
`setup.cfg`, no `.flake8`, no `pytest.ini`, no `mypy.ini` unless a tool genuinely cannot read
pyproject (rare in 2026).

```toml
[project]
name = "mypkg"
requires-python = ">=3.12"
dependencies = ["httpx>=0.27", "pydantic>=2.7"]

[dependency-groups]                 # PEP 735 — not extras; dev-only groups
dev = ["pytest>=9", "ruff", "mypy"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

- Pin **lower bounds** on runtime deps; let the lockfile pin exact versions. Upper-bound caps
  (`<3`) only for deps with a history of breaking (pydantic-style major bumps) — blanket caps
  cause unsolvable resolutions downstream.
- Dev-only tooling goes in `[dependency-groups]`, not `[project.optional-dependencies]`.
  Extras are for users; groups are for developers.
- `requires-python` must match what CI actually tests. Claiming `>=3.9` while using
  `match` statements or `type` aliases is a release-blocking bug.

## 3. ruff replaces flake8 + black + isort + pyupgrade

One tool, one config block, two commands: `ruff check --fix` and `ruff format`.

```toml
[tool.ruff]
target-version = "py312"
line-length = 100
src = ["src", "tests"]

[tool.ruff.lint]
select = [
  "E", "W", "F",      # pycodestyle/pyflakes
  "I",                # isort
  "UP",               # pyupgrade — keeps syntax modern
  "B",                # flake8-bugbear — real bug catchers (B006 mutable defaults, B023 loop closures)
  "S",                # flake8-bandit — security
  "C4",               # comprehensions
  "SIM",              # simplify
  "RUF",              # ruff-specific
  "ASYNC",            # blocking calls in async
  "DTZ",              # naive datetimes
  "PTH",              # pathlib over os.path
  "T20",              # stray print()
  "PERF", "G",        # perf antipatterns, logging format
]
ignore = ["E501"]      # formatter owns line length

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101"]  # assert is fine in tests
```

- If you find black/flake8/isort/pylint configs in a repo: that's a MEDIUM audit finding —
  consolidate to ruff. Mixed formatters cause churn diffs.
- `ruff format` is the formatter; do not also run black.
- Treat `B`, `S`, and `ASYNC` violations as real bugs, not style noise.

## 4. Type checking — one strict checker, enforced in CI

Pick **one**: mypy (`strict = true`), pyright/`basedpyright` (`"strict"`), or ty (Astral).
Running zero checkers is unacceptable for non-throwaway code; running two as gates causes
contradictory suppressions — one gates, the other may advise.

ty status (mid-2026): Beta since Dec 2025, 10–60x faster than mypy/pyright, and Astral
recommends it for production to motivated users; stable 1.0 targeted for 2026. First-class
pydantic/Django support is still landing — on those stacks mypy/pyright remain the
conservative default; for new plain-Python services ty is a legitimate primary checker.

```toml
[tool.mypy]
python_version = "3.12"
strict = true
warn_unreachable = true
enable_error_code = ["ignore-without-code", "possibly-undefined"]
```

- Every `# type: ignore` MUST carry a code: `# type: ignore[arg-type]`. Bare ignores rot.
- The checker runs in CI and fails the build. "We run mypy locally sometimes" = not typed.

## 5. src/ layout

```
mypkg/
├── pyproject.toml
├── uv.lock
├── src/mypkg/
│   ├── __init__.py
│   └── py.typed          # ship type info (PEP 561)
└── tests/
```

Why: with flat layout, `import mypkg` silently picks up the working-copy directory instead of
the installed package — tests pass against uninstalled code, broken wheels ship. `src/` forces
an editable install (`uv sync` handles it) and catches packaging bugs. Tests live **outside**
the package; they aren't shipped.

Ship `py.typed` in any annotated library, or downstream checkers see your package as `Any`.

## 6. pre-commit — fast checks only

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: <40-hex commit SHA>  # frozen: <latest tag> — written by autoupdate --freeze
    hooks: [{id: ruff, args: [--fix]}, {id: ruff-format}]
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: <40-hex commit SHA>  # frozen: <latest tag>
    hooks: [{id: check-merge-conflict}, {id: detect-private-key}, {id: end-of-file-fixer}]
```

Do not hand-type the revs: run `pre-commit autoupdate --freeze`, which resolves each hook repo's
latest tag and stores its commit SHA with the tag as a comment. A hook repo is third-party code
that runs on every commit, so it is pinned by SHA for the same reason Actions are (rules/08 §1)
— a tag can be moved. Re-run it on a schedule so the pins do not rot.

Keep hooks under ~5s; mypy and pytest belong in CI, not pre-commit. CI must re-run the same
checks (`pre-commit run --all-files`) — local hooks are convenience, not enforcement.

## 7. Python 3.12–3.14 features worth using

- **PEP 695 type parameter syntax** (3.12) — default for new generics:
  ```python
  type JSON = dict[str, "JSON"] | list["JSON"] | str | int | float | bool | None

  def first[T](items: Sequence[T]) -> T | None: ...

  class Repo[M: BaseModel]: ...
  ```
  No more `TypeVar("T")` boilerplate, no `Generic[T]` inheritance, correct scoping for free.
- **`match` statements — judiciously.** Use for structural destructuring (AST nodes, parsed
  messages, tagged unions with a `kind` field, sum types). Do NOT use as a fancy if/elif on a
  single scalar — `if x == "a": ... elif x == "b":` is clearer and faster. Always end with
  `case _:` that raises or `assert_never(...)` for exhaustiveness (see rules/02).
- **f-string improvements (3.12, PEP 701):** nested quotes `f"{d["key"]}"`, multi-line
  expressions and comments inside `{}` are legal. Use; don't contort.
- **`itertools.batched(iterable, n)`** (3.12) — replaces hand-rolled chunking.
- **3.13:** improved REPL, clearer error messages, `warnings.deprecated` decorator,
  `copy.replace()`.
- **3.14 — deferred annotations (PEP 649/749):** forward references work without quotes or
  `from __future__ import annotations`; pydantic/FastAPI keep working (see rules/02 §10).
- **3.14 — template strings (PEP 750):** `t"..."` returns a `Template` of static parts +
  `Interpolation` objects instead of a string — for t-string-aware APIs that escape or
  parameterize values (HTML, SQL). Not a drop-in f-string; use only with a consuming library.
  The escaping lives in that consumer, not in the literal: reviewing one is rules/05 §3a.
- **3.14 — `compression.zstd`** (PEP 784): stdlib Zstandard, also wired into
  `tarfile`/`zipfile`/`shutil`. Drops the third-party `zstandard` dep on a 3.14+ floor.

## 7a. What 3.12 and 3.13 REMOVED — the PEP 594 cliff

§7 is what you gain by raising the floor. This is what breaks, and it is the half that turns
a routine bump into an outage. **PEP 594 (Status: Final) deprecated ~20 stdlib modules in
3.11; CPython removed three of them in 3.12 and the rest in 3.13** — the PEP's own
`Python-Version: 3.11` header is the *deprecation* version, not the removal one, which is the
detail that gets misread.

- **Removed in 3.12 (PEP 594):** `smtpd`, `asynchat`, `asyncore`.
- **Removed in 3.13 (PEP 594):** `telnetlib`, `cgi`, `cgitb`, `crypt`, `nntplib`, `pipes`,
  `imghdr`, `sndhdr`, `sunau`, `aifc`, `audioop`, `chunk`, `uu`, `xdrlib`, `mailcap`,
  `msilib`, `nis`, `spwd`, `ossaudiodev`.
- **Same cliff, not PEP 594:** `distutils` (PEP 632) and `imp` removed in 3.12; `lib2to3`
  removed in 3.13. `distutils` can *appear* to survive where setuptools is installed (it ships
  a shim), so a clean import on your machine proves nothing about a slim image.

Measured 2026-09-25 against `sys.stdlib_module_names`: all 25 present on 3.11.15; the five
3.12 names absent on 3.12.13; all 25 absent on 3.13.13.

**The failure mode is an ImportError at runtime, not at install time**, and it lands in the
paths least covered by tests — a `cgi.parse_header()` in a legacy upload handler, `crypt` in
an old auth shim, `pipes.quote` in a deploy script, `smtpd` in a test fixture. A dependency
you do not control can also import one; the traceback then names *their* module, not yours.

```bash
# BEFORE bumping the floor to 3.12 or 3.13 — grep first, and include your venv, not just src/
grep -rnE '\b(import|from)\s+(telnetlib|cgi|cgitb|crypt|nntplib|smtpd|pipes|asynchat|asyncore|imghdr|sndhdr|sunau|aifc|audioop|chunk|uu|xdrlib|mailcap|msilib|nis|spwd|ossaudiodev|distutils|imp|lib2to3)\b' \
  --include='*.py' . 
```

Two of these have security weight beyond the bump and are called out again in rules/05:
`telnetlib` (plaintext credentials) and `crypt` (weak, platform-dependent hashing). Their
replacements are not drop-in — `cgi.parse_header` has no stdlib successor, and `crypt` users
want a password-hashing library, not another stdlib module.

## 8. Free-threading awareness (3.14t)

Free-threaded CPython (PEP 703, no GIL) is **officially supported since 3.14** (PEP 779) —
no longer experimental, though still not the default build; single-threaded overhead is down
to roughly 5–10%. Target `3.14t`, not `3.13t` (experimental). uv installs it via the `t`
suffix (`uv python install 3.14t`). Implications:

- **Stop assuming the GIL makes code thread-safe.** `dict`/`list` single ops stay atomic, but
  check-then-act sequences (`if key not in d: d[key] = ...`) were never safe and now break
  observably. Guard shared mutable state with `threading.Lock` or use queues — on every build.
- **One C extension silently puts the GIL back.** Importing an extension module that does not
  declare the `Py_mod_gil` slot re-enables the GIL for the whole process with only a
  `RuntimeWarning` — the service keeps running, just not free-threaded. Make it loud: assert
  `sys._is_gil_enabled() is False` at startup (after your imports) and in CI, and run CI with
  `-W error::RuntimeWarning` so the import itself fails. `PYTHON_GIL=0` / `-X gil=0` force the
  GIL off regardless — a *testing* switch for probing whether an undeclared extension really is
  thread-safe, not a production fix. Measured 2026-09-25 on 3.14.6t with two one-line test
  extensions: the one without the slot raised the warning and flipped `_is_gil_enabled()` to
  `True` (both guards exit 1); the one declaring `Py_MOD_GIL_NOT_USED` kept it `False` (exit 0).
- Library authors shipping C extensions: declare `Py_mod_gil` only after testing on `3.14t`,
  and publish `cp314t` wheels.
- Don't rewrite multiprocessing pools to threads "because no-GIL" until you've profiled on the
  free-threaded build; single-thread perf differs.
- Decision table for concurrency model is in rules/06.

## 9. Docker packaging with uv

```dockerfile
FROM ghcr.io/astral-sh/uv:python3.14-trixie-slim AS builder
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
# Layer-cache deps separately from source: lockfile changes rarely, code changes often
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --no-dev --no-install-project
COPY src/ src/
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --no-dev

FROM python:3.14-slim-trixie
RUN useradd --create-home app
USER app
COPY --from=builder --chown=app /app /app
ENV PATH="/app/.venv/bin:$PATH"
CMD ["python", "-m", "mypkg"]
```

Key points: deps installed from the lockfile *before* copying source (cache hit on code-only
changes), `--no-dev` in images, non-root user, no uv/compilers in the final stage. Pin base
images by digest for reproducible rebuilds in regulated environments.

## 10. Repo hygiene quick list

- `.python-version` committed; matches CI matrix floor.
- No `requirements*.txt` as the source of truth (generated-only is fine, mark it as such).
- No committed `.venv/`, `__pycache__/`, `.mypy_cache/` — `.gitignore` covers them.
- Version in exactly one place (`pyproject.toml` or `__init__.py` via dynamic) — not both.
- Entry points via `[project.scripts]`, not instructions to run `python src/mypkg/cli.py`.
- Declared-but-unreached dependencies: `deptry .` reports DEP002 (unused), DEP003
  (imported but only a transitive dep), DEP005 (stdlib shadowed). Treat its output as
  candidates — `importlib`/entry-point/plugin loads read as unused — and prove each by
  removing it in a scratch copy and running the real build and full suite
  (`sota-devsecops` rules/10).

## Audit checklist

Run from repo root. Severity guidance in brackets.

- [ ] **Toolchain state** — `ls pyproject.toml uv.lock 2>/dev/null` (missing uv.lock in an app
      [MEDIUM]; a committed `pylock.toml`/`pylock.<name>.toml` is a hashed lock too (§1), not a
      missing one: `find . -name 'pylock*.toml' -not -path '*/.venv/*'`); `ls setup.py setup.cfg Pipfile poetry.lock 2>/dev/null` (legacy/competing
      toolchains [LOW-MEDIUM]);
      `grep -rn "pip install" --include="*.yml" --include="*.yaml" --include="Dockerfile*" . | grep -v "uv pip"`
      (unlocked installs in CI/images [MEDIUM]); `grep -n "sudo pip" -r .` (system-interpreter
      installs [HIGH])
- [ ] **Competing lint/format config [MEDIUM — consolidate to ruff]** —
      `ls .flake8 .isort.cfg .pylintrc 2>/dev/null; grep -n "\[tool.black\]\|\[tool.isort\]" pyproject.toml`
- [ ] **Type checking actually enforced?** —
      `grep -n "mypy\|pyright\|basedpyright\| ty " .github/workflows/*.yml .gitlab-ci.yml 2>/dev/null`
      ; `grep -rn "type: ignore$\|type: ignore " --include="*.py" src/ | grep -v "ignore\["`
      (bare ignores [LOW])
- [ ] **requires-python vs syntax reality** — `grep -n "requires-python" pyproject.toml` ;
      `grep -rln "match \|type [A-Z].* = \|def .*\[T" --include="*.py" src/ | head` (3.12 syntax
      w/ old floor?)
- [ ] **Layout** — `ls -d src/ 2>/dev/null | grep -q . || echo "flat layout"` (flat layout in a
      library [LOW]); `find src -name py.typed | head -1` (annotated lib without py.typed
      [MEDIUM])
- [ ] **Ruff coverage** — `uvx ruff check --statistics .` (what's currently violated);
      `grep -n "select" pyproject.toml` (B/S/ASYNC missing from select [LOW])
- [ ] **Hygiene** — `git ls-files | grep -E "\.venv/|__pycache__|\.pyc$"` (committed artifacts
      [LOW])
- [ ] **pre-commit hooks pinned by tag, not SHA (§6) [LOW]** —
      `grep -nE '^[[:space:]]*rev:[[:space:]]*[^[:space:]#]' .pre-commit-config.yaml | grep -vE 'rev:[[:space:]]*[0-9a-f]{40}([[:space:]]|$)'`
      (each hit is a movable tag: `pre-commit autoupdate --freeze`)
- [ ] **--- Stdlib removals before a 3.12/3.13 floor bump: PEP 594, `distutils`, `imp`,
      `lib2to3` (§7a) [HIGH — ImportError at runtime] ---** —
      `grep -rnE '\b(import|from)\s+(telnetlib|cgi|cgitb|crypt|nntplib|smtpd|pipes|asynchat|asyncore|imghdr|sndhdr|sunau|aifc|audioop|chunk|uu|xdrlib|mailcap|msilib|nis|spwd|ossaudiodev|distutils|imp|lib2to3)\b' --include='*.py' .`
- [ ] **Shared mutable state under threads (§8) — HIGH where a free-threaded (`t`) build is
      targeted, MEDIUM otherwise: the GIL never made check-then-act safe** —
      `grep -rlE 'threading\.Thread\(|ThreadPoolExecutor|asyncio\.to_thread' --include='*.py' src/`
      (the files that run code on threads; read only those) ;
      `grep -rnE '^[[:space:]]+global [A-Za-z_]' --include='*.py' src/` (a module global rebound
      from a function) ;
      `grep -rnE 'if [^:]+ not in [A-Za-z_][A-Za-z0-9_.]*:' --include='*.py' src/` (check-then-act
      on a shared dict or set: a finding only where a thread reaches it with no `threading.Lock`
      held)
- [ ] **GIL silently re-enabled on a free-threaded target (§8) [MEDIUM where a `t` build is
      the deployment target]** — `grep -rn '_is_gil_enabled' --include='*.py' .` (no hit = nothing
      notices an undeclared extension turning the GIL back on) ;
      `grep -rnE 'PYTHON_GIL=0|-X ?gil=0' --include='*.y*ml' --include='Dockerfile*' --include='*.sh' .`
      (the testing override shipped to production)