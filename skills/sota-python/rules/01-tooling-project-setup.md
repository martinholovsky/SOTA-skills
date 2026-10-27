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
- **CI installs with `uv sync --locked`, never `--frozen`.** `--frozen` (and `UV_FROZEN=1`)
  installs `uv.lock` without checking that it still matches `pyproject.toml`; `--locked`
  fails instead. Measured (uv 0.12.0), a dependency added to `pyproject.toml` after `uv lock`:
  `--frozen` and `UV_FROZEN=1` exited 0 without installing it, `--locked` exited 1. Never bare
  `pip install -r requirements.txt` in new projects; if a legacy `requirements.txt` must exist,
  generate it: `uv export --format requirements-txt --output-file requirements.txt`.
- **What else unfreezes a frozen install.** A later `pip install <tool>` / `uv pip install` /
  unversioned `uvx <tool>` step in the same job resolves whatever is newest, outside the lock:
  put tools in a dependency group, or pin them (`uvx ruff@<version>`). On Poetry,
  `poetry install --no-root` fails on a stale lock but with no lock resolves fresh and exits 0;
  gate it with `poetry check --lock` first ([`sota-devsecops` rules/03](../../sota-devsecops/rules/03-dependencies.md) §3.1).
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
  "PGH",              # PGH003/PGH004: no bare `# type: ignore` / `# noqa`
]
ignore = ["E501"]      # formatter owns line length

[tool.ruff.lint.per-file-ignores]  # assert and fixture tokens are fine in tests
"tests/**" = ["S101", "S105", "S106"]
"**/test_*.py" = ["S101", "S105", "S106"]    # co-located tests: `tests/**` misses them
"**/*_test.py" = ["S101", "S105", "S106"]
"**/conftest.py" = ["S101", "S105", "S106"]
```

- **Suppressions name a rule, carry a reason, and expire.** General contract: [`sota-devsecops` rules/05](../../sota-devsecops/rules/05-analysis-gates.md) §5.1. `# noqa: S603  # argv list, no
  shell` and `# type: ignore[assignment]  # legacy fixture`: `PGH004`/`PGH003` reject the bare
  forms, and `RUF100` (in `RUF`) reports a `noqa` whose rule no longer fires, so a stale one
  fails `ruff check`. No tool requires the reason; that is a review rule with a grep probe
  below. Run one-off RUF100 checks with `--extend-select`, never a narrowed `--select`:
  measured (ruff 0.16.2), `--select RUF100` reported every `# noqa: S101` as "non-enabled",
  and `--fix` would delete them all.
- **Test code is exempted by path in config, not by weakening the rule.** A rule that tests
  legitimately trip (`S101` assert, `S105`/`S106` fixture passwords) goes in
  `per-file-ignores` for test paths; moving it to the global `ignore` because the test job
  went red disables it for production code too. Measured (ruff 0.16.2): with only
  `"tests/**"`, an `assert` in `src/pkg/test_util.py` still failed, and the four globs above
  exempted it while `assert` in `src/pkg/core.py` stayed an error.
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
  An ignore that no longer suppresses anything must fail too: mypy `strict = true` already
  enables `warn_unused_ignores` (reported as `[unused-ignore]`; set it explicitly without
  `strict`); pyright's `reportUnnecessaryTypeIgnoreComment` defaults to `"none"`, so set it to
  `"error"`. Requiring a rule on pyright's own ignores (`reportIgnoreCommentWithoutRule`) is
  basedpyright-only.
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
the package by default, so they aren't shipped; pytest also supports in-package tests, and a
repo that co-locates them needs §3's test-path lint exemptions.

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
that runs on every commit, so it is pinned by SHA for the same reason Actions are ([rules/08](08-supply-chain.md) §1)
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
  `case _:` that raises or `assert_never(...)` for exhaustiveness (see [rules/02](02-typing-correctness.md)).
- **f-string improvements (3.12, PEP 701):** nested quotes `f"{d["key"]}"`, multi-line
  expressions and comments inside `{}` are legal. Use; don't contort.
- **`itertools.batched(iterable, n)`** (3.12) — replaces hand-rolled chunking.
- **3.13:** improved REPL, clearer error messages, `warnings.deprecated` decorator,
  `copy.replace()`.
- **3.14 — deferred annotations (PEP 649/749):** forward references work without quotes or
  `from __future__ import annotations`; pydantic/FastAPI keep working (see [rules/02](02-typing-correctness.md) §10).
- **3.14 — template strings (PEP 750):** `t"..."` returns a `Template` of static parts +
  `Interpolation` objects instead of a string — for t-string-aware APIs that escape or
  parameterize values (HTML, SQL). Not a drop-in f-string; use only with a consuming library.
  The escaping lives in that consumer, not in the literal: reviewing one is [rules/05](05-security.md) §3a.
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

Two of these have security weight beyond the bump and are called out again in [rules/05](05-security.md):
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
- Decision table for concurrency model is in [rules/06](06-performance.md).

## 9. Docker packaging with uv

```dockerfile
FROM ghcr.io/astral-sh/uv:python3.14-trixie-slim@sha256:<digest> AS builder
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
# Layer-cache deps separately from source: lockfile changes rarely, code changes often
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --no-dev --no-install-project
COPY src/ src/
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --no-dev

FROM python:3.14-slim-trixie@sha256:<digest>
RUN useradd --create-home app
USER app
COPY --from=builder --chown=app /app /app
ENV PATH="/app/.venv/bin:$PATH" PYTHON_DISABLE_REMOTE_DEBUG=1
CMD ["python", "-m", "mypkg"]
```

Key points: deps installed from the lockfile *before* copying source (cache hit on code-only
changes), `--no-dev` in images, non-root user, no uv/compilers in the final stage. Pin every base
image by digest ([`sota-devsecops` rules/04](../../sota-devsecops/rules/04-build-containers.md) §4.3), not only in regulated environments.

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
  ([`sota-devsecops` rules/10](../../sota-devsecops/rules/10-inert-dependencies.md)).

## Audit checklist

Run from repo root. Severity guidance in brackets.

- [ ] **Toolchain state** — `ls pyproject.toml uv.lock 2>/dev/null` (missing uv.lock in an app
      [MEDIUM]; a committed `pylock.toml`/`pylock.<name>.toml` is a hashed lock too (§1), not a
      missing one: `find . -name 'pylock*.toml' -not -path '*/.venv/*'`); `ls setup.py setup.cfg Pipfile poetry.lock 2>/dev/null` (legacy/competing
      toolchains [LOW-MEDIUM]);
      `grep -rn "pip install" --include="*.yml" --include="*.yaml" --include="Dockerfile*" . | grep -v "uv pip"`
      (unlocked installs in CI/images [MEDIUM]); `grep -n "sudo pip" -r .` (system-interpreter
      installs [HIGH])
- [ ] **Competing lint/format config [MEDIUM — consolidate to ruff]** (§3) —
      `ls .flake8 .isort.cfg .pylintrc 2>/dev/null; grep -n "\[tool.black\]\|\[tool.isort\]" pyproject.toml`
- [ ] **Type checking actually enforced?** (§4) —
      `grep -qE 'mypy|pyright|basedpyright| ty ' .github/workflows/*.yml .gitlab-ci.yml || echo "no type checker in CI"`
      ; `grep -rnE 'type: ignore([[:space:]]|$)' --include="*.py" src/ | grep -v "ignore\["`
      (bare ignores [LOW])
- [ ] **Suppressions that never expire (§3, §4) [LOW each, MEDIUM in aggregate or where they silence `S` rules]** —
      `uvx ruff check --extend-select PGH003,PGH004,RUF100 --statistics .` (bare and stale
      `noqa`/`type: ignore`; `--extend-select` keeps the project's rules, §3) ;
      `grep -qE 'reportUnnecessaryTypeIgnoreComment|warn_unused_ignores|strict[[:space:]]*=' pyproject.toml pyrightconfig.json || echo "no unused-ignore gate configured"`
      (the message = an unused ignore never fails; silence still needs the setting to belong to
      the checker that gates CI, not the other one) ;
      `grep -rnE '#[[:space:]]*(noqa(:[[:space:]]*[A-Z]+[0-9]+([[:space:]]*,[[:space:]]*[A-Z]+[0-9]+)*)?|type:[[:space:]]*ignore(\[[^]]*\])?|pyright:[[:space:]]*ignore(\[[^]]*\])?)[[:space:]]*$' --include='*.py' .`
      (each hit is a suppression with no reason after it)
- [ ] **Test-only rules disabled globally, or co-located tests not exempted (§3) [MEDIUM for
      `S101`/`S105`/`S106` in the global ignore]** —
      `grep -HnE '^[[:space:]]*(extend-)?ignore[[:space:]]*=.*"(S101|S105|S106)"' /dev/null $(ls pyproject.toml ruff.toml .ruff.toml 2>/dev/null)`
      (each hit turns the rule off for production code) ;
      `find . -path ./tests -prune -o -path ./.venv -prune -o \( -name 'test_*.py' -o -name '*_test.py' \) -print | head -3`
      (any hit while `per-file-ignores` keys only `"tests/**"` = those tests fail the lint, or
      someone widened the global ignore)
- [ ] **Frozen install that is not checked (§1) [HIGH in CI, an image build or a deploy, MEDIUM on a developer-only path ([`sota-devsecops` rules/03](../../sota-devsecops/rules/03-dependencies.md) §3.1)]** —
      `grep -rnE 'uv[[:space:]]+(sync|run|export)[^#]*--frozen|UV_FROZEN' --include='*.y*ml' --include='Dockerfile*' --include='*.sh' .`
      (each hit installs a lock nobody compared with `pyproject.toml`: use `--locked`) ;
      `grep -rlE 'poetry[[:space:]]+install' --include='*.y*ml' . | while IFS= read -r f; do grep -qE 'poetry[[:space:]]+check[[:space:]]+--lock' "$f" || echo "$f: poetry install with no poetry check --lock"; done`
- [ ] **requires-python vs syntax reality; `pyproject.toml` as the single source (§2)** —
      `grep -n "requires-python" pyproject.toml` (prints the declared floor; it is read against
      the syntax hits below, not a finding) ;
      `grep -rln "match \|type [A-Z].* = \|def .*\[T" --include="*.py" src/ | head` (3.12 syntax
      w/ old floor? [HIGH: release-blocking]) ;
      `find . -maxdepth 1 \( -name setup.py -o -name setup.cfg -o -name pytest.ini -o -name mypy.ini -o -name .flake8 \) -print`
      (config outside `pyproject.toml` [LOW]) ;
      `find . -maxdepth 1 -name pyproject.toml -exec grep -nA8 '^\[project\.optional-dependencies\]' {} + | grep -E '"(pytest|ruff|mypy|coverage)'`
      (dev tooling published as a user extra, not a `[dependency-groups]` group [LOW]) ;
      `find . -maxdepth 1 -name pyproject.toml -exec grep -nE '"[A-Za-z0-9_.-]+[^"]*<[0-9][^"]*"' {} +`
      (an upper-bound cap: justified only for a dep with a history of breaking [LOW])
- [ ] **Layout (§5)** — `ls -d src/ 2>/dev/null | grep -q . || echo "flat layout"` (flat layout in a
      library [LOW]); `find src -name py.typed | head -1` (annotated lib without py.typed
      [MEDIUM]) ; `find . -path ./.venv -prune -o -path ./tests -prune -o \( -name 'test_*.py' -o -name '*_test.py' -o -name conftest.py \) -print | head -3`
      (tests inside the package ship with it [LOW])
- [ ] **Ruff coverage** (§3) — `uvx ruff check --statistics .` (what's currently violated);
      `grep -nE '^[[:space:]]*(extend-)?select[[:space:]]*=' pyproject.toml | awk '!/"ALL"/ && !(/"B"/ && /"S"/ && /"ASYNC"/)'`
      (a select line missing one of B/S/ASYNC [LOW]; a multi-line array prints its opening line: read it) ;
      `uvx ruff check --select PERF,C4,SIM --statistics .` (the perf rules)
- [ ] **Hygiene (§10)** — `git ls-files | grep -E "\.venv/|__pycache__|\.pyc$"` (committed artifacts
      [LOW]) ; `git ls-files .python-version | grep -q . || echo "no .python-version committed"` [LOW] ;
      `git ls-files | grep -E '(^|/)requirements[^/]*\.txt$'` (each must be a generated `uv export`,
      marked as such [LOW]) ;
      `v=$(grep -rlE '^__version__[[:space:]]*=' --include='__init__.py' --exclude-dir=.venv . | wc -l); p=$(find . -maxdepth 1 -name pyproject.toml -exec grep -cE '^version[[:space:]]*=' {} +); [ "$v" -gt 0 ] && [ "${p:-0}" -gt 0 ] && echo "version in pyproject.toml and $v __init__.py"`
      (the version in two places [LOW]) ;
      `grep -rnE 'python3? src/[A-Za-z0-9_/]+\.py' --include='*.md' --include='*.rst' --exclude-dir=.venv .` (run-by-path
      instructions instead of `[project.scripts]` [LOW]) ; `uvx deptry .` (DEP002/DEP003/DEP005 are
      candidates: prove each removal as §10 says)
- [ ] **Pre-PEP 695 generics and aliases on a 3.12+ floor (§7) [LOW]** —
      `uvx ruff check --select UP040,UP046,UP047 --statistics .` (`TypeAlias`, `Generic[T]` and
      `TypeVar` boilerplate where PEP 695 syntax is the default; measured, ruff 0.16.2, the three
      fire only when `target-version` is `py312` or later) ; a `match` with no closing `case _`
      is [rules/02](02-typing-correctness.md)'s exhaustiveness item, and hand-rolled chunking is
      [rules/03](03-idioms-pitfalls.md)'s itertools item
- [ ] **Python image built with dev dependencies, or source copied before the lock (§9) [MEDIUM
      for dev deps in the image; LOW for layer order]** —
      `grep -rnE 'uv[[:space:]]+sync' --include='Dockerfile*' --include='Containerfile*' . | grep -v -- '--no-dev'`
      (the dev group shipped in the image) ;
      `find . \( -name 'Dockerfile*' -o -name 'Containerfile*' \) -not -path '*/.venv/*' -exec awk 'FNR==1{s=0} /^(COPY|ADD)[[:space:]]+(\.|\.\/|src\/?)[[:space:]]/ && !s {print FILENAME":"FNR": source copied before the first uv sync"} /uv[[:space:]]+sync/{s=1}' {} +`
      (every code change rebuilds the dependency layer) ; non-root `USER`, a minimal final
      stage and digest-pinned `FROM` are [`sota-devsecops` rules/04](../../sota-devsecops/rules/04-build-containers.md)'s checklist
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
      the deployment target]** — `grep -rq '_is_gil_enabled' --include='*.py' . || echo "no _is_gil_enabled() check"`
      (the message = nothing notices an undeclared extension turning the GIL back on) ;
      `grep -rnE 'PYTHON_GIL=0|-X ?gil=0' --include='*.y*ml' --include='Dockerfile*' --include='*.sh' .`
      (the testing override shipped to production)
