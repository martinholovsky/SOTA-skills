# 07 — FastAPI, Django, and pytest Mastery

Framework-specific traps plus the testing discipline that applies everywhere. Deep general
rules live elsewhere (async → [rules/04](04-async.md), validation → [rules/02](02-typing-correctness.md), SQL safety → [rules/05](05-security.md)).

## 1. FastAPI

### Pydantic models at the boundary — separate in/out

```python
class UserIn(BaseModel):
    model_config = {"extra": "forbid"}
    email: EmailStr
    password: SecretStr

class UserOut(BaseModel):
    id: int
    email: EmailStr            # no password field — response_model filters output

@router.post("/users", response_model=UserOut, status_code=201)
async def create_user(payload: UserIn, svc: UserService = Depends(get_user_service)) -> UserOut: ...
```

- Distinct request/response models. Returning ORM objects without `response_model` leaks
  columns you forgot existed (password hashes, internal flags) — recurring HIGH finding.
- `extra="forbid"` on inputs; `SecretStr` for credentials (won't repr into logs).
- Validation errors are FastAPI's job — don't pre-validate manually then re-wrap.

### Dependency injection done right

- Dependencies are the composition mechanism: DB sessions, auth, settings, clients all come
  in via `Depends`, never module-level globals — this is what makes handlers testable via
  `app.dependency_overrides`.
- `yield`-dependencies for resources (session per request, commit/rollback in the
  finally/except of the dependency, not in handlers).
- Singletons (settings, http client, pools) live on the **lifespan**:
  ```python
  @asynccontextmanager
  async def lifespan(app: FastAPI):
      app.state.http = httpx.AsyncClient(timeout=10)
      yield
      await app.state.http.aclose()
  ```
- `Annotated[UserService, Depends(get_user_service)]` aliases kill signature noise.
- Heavy pure-validation dependencies: `use_cache=True` is the default — don't re-resolve per
  sub-dependency; do not hide business logic in dependencies.

### The sync-in-async trap (most common FastAPI perf bug)

- `async def` endpoint + blocking call (requests, sync SQLAlchemy session, `time.sleep`)
  → blocks the **single** event loop; whole service serializes. See [rules/04](04-async.md) §3.
- `def` (sync) endpoint → FastAPI runs it in the anyio threadpool (default ~40 threads) —
  blocking is *safe* there but throughput caps at pool size.
- Rule: endpoint is `async def` **only if everything it awaits is truly async** (asyncpg /
  SQLAlchemy async session / httpx.AsyncClient). Mixed stack? Make the endpoint `def` and
  stay sync, or fix the stack. An `async def` endpoint with zero `await` inside is a bug
  marker — it gains nothing and risks someone adding blocking calls later.
- **Exception: the liveness probe.** A liveness endpoint is *supposed* to await nothing —
  its job is "is the event loop responsive", so [`sota-observability` rules/05](../../sota-observability/rules/05-operational-readiness.md) §1 specifies
  process-internal-only, "usually just return 200". Written as `def` it runs in the anyio
  threadpool, where saturation by slow sync handlers delays the probe and the orchestrator
  restarts a process whose event loop was fine — the restart storm [`sota-observability` rules/05](../../sota-observability/rules/05-operational-readiness.md) §1 exists to
  prevent. So a no-`await` `async def` is **correct** here and the marker does not apply.
  Say so in the docstring, or the next reader "fixes" it. Readiness (`/readyz`), which does
  check dependencies, follows the normal rule.
- Background work: `BackgroundTasks` for small post-response work; real job queue
  (arq/celery/temporal) for anything that must survive a process restart.

## 2. Django

### ORM: N+1 is the default — defeat it explicitly

```python
# Bad — 1 query for orders + 1 per order for .customer + 1 per order for items
for order in Order.objects.all():
    print(order.customer.name, [i.sku for i in order.items.all()])

# Good
orders = (
    Order.objects
    .select_related("customer")            # FK/O2O → SQL JOIN
    .prefetch_related("items")             # M2M/reverse FK → 2nd query + join in Python
)
```

- `select_related` for forward FK/OneToOne; `prefetch_related` for M2M and reverse relations;
  `Prefetch(queryset=...)` to filter/order the prefetched set.
- Make N+1 a test failure: pytest-django's `django_assert_num_queries` /
  `django_assert_max_num_queries` fixtures, or Django's own `self.assertNumQueries(2)` in a
  `TestCase`; `django-zen-queries` (`queries_disabled()`, its own `render`) to make a query inside a
  template or serializer raise. These are fixture and
  method names, not packages — there is no PyPI project `django-assert-num-queries` (404,
  checked 2026-09-25), so a `pip install` of it is an unclaimed name a squatter can take.
- Other ORM rules: `.only()/.defer()` for wide tables on hot paths; `exists()` not
  `count() > 0` not `len(qs)`; `bulk_create/bulk_update` for batch writes; `update()`
  for field bumps instead of load-modify-save races — or `F()` expressions for atomic
  increments; `iterator(chunk_size=...)` for large scans; aggregate in the DB
  (`annotate/aggregate`), not in Python.
- Querysets are lazy and **cached per object** — slicing/re-filtering re-queries; assigning
  `qs = qs.filter(...)` builds SQL, `if qs:` executes it. Know which line hits the DB.

### Migrations discipline

- One logical change per migration; **never edit an applied migration** — write a new one.
- `python manage.py makemigrations --check` in CI: fails when models drifted from migrations.
- Zero-downtime ordering: additive first (nullable column / new table), deploy code that
  writes both, backfill in batches (separate data migration with `RunPython` + reverse func),
  then constrain/drop in a later release. Never `NOT NULL` + default on a huge table in one
  step (lock).
- Data migrations use `apps.get_model("app", "Model")`, never direct model imports (the
  model's current code may not match the schema at that point in history).
- Squash periodically; name migrations (`0042_order_add_status_index`, not `auto_...`).

### Django misc

- Django 6.0 (Dec 2025): built-in **Tasks framework** for background work — prefer it over
  bolting on celery for simple deferred jobs (it still needs a worker/backend in prod);
  native **Content Security Policy** support (replaces `django-csp`); template partials.
  Django 5.2 remains the LTS — don't flag staying on it as a finding.
- `async def` views must not call the sync ORM directly — use `aget/afirst/acount` async
  ORM methods or `sync_to_async` wrappers; a blocking ORM call in an async view under ASGI
  stalls the loop ([rules/04](04-async.md) §7).
- Settings via `django-environ`/env vars; `DEBUG=False`, `ALLOWED_HOSTS`, `SECRET_KEY` from
  secrets store — run `manage.py check --deploy` in CI.
- Keep `.raw()`, `.extra()`, `RawSQL` out of the codebase or parameterized + reviewed
  ([rules/05](05-security.md) §3).

### Cookies the application sets (Flask, Starlette/FastAPI, Django)

The framework's session cookie is configured by settings and owned by [`sota-code-security`
rules/17](../../sota-code-security/rules/17-sessions-and-tokens.md). Every *other* cookie — a preference, a device id, a "remember this" token — goes
through `response.set_cookie(...)`, and the defaults there are the insecure ones. Measured
this session (Werkzeug 3.1 / Starlette 1.7 / Django 6.1), a bare `set_cookie("pref", "v")`
emitted:

| Framework | Header | Secure | HttpOnly | SameSite |
|---|---|---|---|---|
| Flask (Werkzeug) | `pref=v; Path=/` | off | off | not sent |
| Starlette / FastAPI | `pref=v; Path=/; SameSite=lax` | off | off | `lax` |
| Django `HttpResponse` | `pref=v; Path=/` | off | off | not sent |

- Pass `secure=True, httponly=True, samesite="Lax"` (or `"Strict"`) explicitly on every
  call, through one helper so no call site forgets. `httponly=False` only for a value
  JavaScript must read, with a comment saying so. All three default `path="/"` and no
  `domain` — keep `domain` unset unless a sibling subdomain genuinely needs the cookie.
- Prefer the `__Host-` name prefix for anything security-relevant: browsers accept it only
  with `Secure`, `Path=/` and no `Domain` (MDN, Set-Cookie). The frameworks do **not**
  enforce it — Werkzeug's `dump_cookie("__Host-x", "v")` emitted `__Host-x=v; Path=/` with
  no `Secure` — so the prefix is only as good as the flags you pass alongside it.
- Django's `set_signed_cookie` signs, it does not encrypt: the value is readable in the
  header. OWASP: Session Management cheat sheet; Cookie Theft Mitigation cheat sheet; ASVS.

## 3. pytest mastery

### Fixtures over setup, composition over inheritance

```python
@pytest.fixture
def db_session(engine) -> Iterator[Session]:     # depends on another fixture
    with engine.begin() as conn:
        session = Session(bind=conn)
        yield session
        session.rollback()                       # teardown after yield — always runs

@pytest.fixture
def user(db_session) -> User:
    return UserFactory.create(session=db_session)
```

- No `unittest.TestCase` setUp/tearDown in new code; fixtures compose, are scoped, and are
  request-only-what-you-need.
- Scope deliberately: `session` scope for expensive immutable resources (containers via
  `testcontainers`, compiled artifacts); `function` scope (default) for anything mutable.
  A session-scoped fixture yielding a mutable object is a test-pollution factory.
- `conftest.py` per directory for shared fixtures; no `from tests.helpers import *`.
- `autouse=True` sparingly — invisible dependencies; acceptable for isolation guards
  (clearing caches, freezing time, fake env).

### Parametrize, don't copy-paste

```python
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        pytest.param("1h30m", 5400, id="hours-minutes"),
        pytest.param("90s", 90, id="seconds"),
        pytest.param("", None, id="empty", marks=pytest.mark.xfail(raises=ParseError)),
    ],
)
def test_parse_duration(raw: str, expected: int | None) -> None:
    assert parse_duration(raw) == expected
```

- `id=` on every param — `test_parse[2]` failures are unreadable.
- Stack parametrize decorators for cartesian products; parametrize fixtures
  (`params=` on the fixture) when the *resource* varies (e.g., each DB backend).

### No test interdependence

- Every test runs alone and in any order: `pytest -p no:randomly` shouldn't be needed —
  install `pytest-randomly` and keep it green.
- Banned: module-level mutable state shared across tests, tests that rely on execution
  order, `lru_cache`d functions tested without `cache_clear` between tests ([rules/06](06-performance.md) §4),
  writes to shared tmp paths — use the `tmp_path` fixture, env mutation without
  `monkeypatch.setenv` (which auto-reverts).
- Verify independence in CI occasionally: `pytest -x --randomly-seed=last`, and
  `pytest-xdist` (`-n auto`) — parallel-unsafe tests are interdependent tests.

### Property-based testing with hypothesis

```python
from hypothesis import given, strategies as st

@given(st.text())
def test_roundtrip(s: str) -> None:
    assert decode(encode(s)) == s            # invariant, not example

@given(st.lists(st.integers()))
def test_sort_idempotent(xs: list[int]) -> None:
    assert my_sort(my_sort(xs)) == my_sort(xs)
```

- Use for parsers, serializers, codecs, numeric routines, anything with an invariant
  (roundtrip, idempotence, commutativity, oracle vs reference impl).
- Persist the example database (`.hypothesis/` in CI cache) so regressions replay;
  failing examples get promoted to `@example(...)` regression pins.
- **A green property with `assume()`, `.filter()` or an early `return` may have tested almost
  nothing**: `HealthCheck.filter_too_much` fails only near-total rejection (a 2% pass rate
  passed), and an early `return` is never counted. Gate reach as
  [`sota-testing` rules/06](../../sota-testing/rules/06-property-fuzzing-mutation.md) §6.6 says.
- **Contracts on pure functions: CrossHair** searches symbolically (Z3) over PEP 316 docstring,
  `icontract` or `deal` contracts and type hints, and returns counterexamples. It is a bounded
  search, not a proof: "no counterexample" is not "correct". (ESBMC, a bounded model checker,
  also has a Python frontend.)

### Markers, selection, and suite layering

```toml
[tool.pytest]                       # pytest 9+ native table — real TOML types (arrays, bools)
addopts = ["-ra", "--strict-markers", "--strict-config"]
markers = [
  "slow: takes >1s, excluded from default run",
  "integration: needs docker services",
]
testpaths = ["tests"]
```

- pytest 9 (Nov 2025): the native `[tool.pytest]` table (or a `pytest.toml` file) replaces
  `[tool.pytest.ini_options]` as the state-of-the-art spelling — `ini_options` still works
  pre- and post-9, but the two tables cannot coexist. 9 also drops Python 3.9 and merges
  `pytest-subtests` into core (`subtests` fixture — no plugin needed for loop-style asserts).
- `--strict-markers` always — a typo'd `@pytest.mark.integratoin` silently creates a marker
  and your "skip integration" filter stops matching.
- Layer the suite: fast unit tests run on every push (`-m "not slow and not integration"`);
  integration tests (testcontainers, real DB) run in CI on a service matrix. A suite that
  takes 20 minutes locally stops being run locally.
- `-ra` in addopts so skipped/xfailed reasons are visible; unexplained skips rot into dead
  tests.

### General pytest hygiene

- Plain `assert` with rich introspection — no `assertEquals` ports, no bare
  `assert response` when you mean `assert response.status_code == 200`.
- `pytest.raises(SpecificError, match=r"...")` — never `pytest.raises(Exception)`.
- Mock at the boundary you own (`mocker.patch.object(svc, "client")`), not deep internals;
  patch where the name is *looked up*, not where it's defined. Over-mocked tests that
  assert call sequences test the mock, not the code — prefer fakes (in-memory repo).
- Async tests: `asyncio_mode = "auto"` ([rules/04](04-async.md) §10). Time: `freezegun`/`time-machine`,
  never `sleep`.
- Coverage gate (`--cov --cov-fail-under=N`) measures *executed*, not *asserted* — treat as
  floor, not target; mutation testing (`mutmut`) where correctness is critical — `mutmut run`
  exits 0 whatever survives, so gate on its exported stats ([`sota-testing` rules/06](../../sota-testing/rules/06-property-fuzzing-mutation.md) §6.3).
- **Code with an escape hatch (`ctypes`, `cffi`, a C extension: [rules/05](05-security.md) §11) runs its
  suite under `python -X dev` in CI.** Dev mode enables `faulthandler` and the debug hooks
  on the memory allocators. Measured on 3.14.8: writing 10 bytes past a 1000-byte
  `ctypes.create_string_buffer` exited 0 under plain `python`, and under `-X dev` printed
  "pad bytes ... are not all FORBIDDENBYTE" and aborted (exit 134). Use the `-X dev` flag,
  not `PYTHONDEVMODE=1`: `-I` and `-E` drop every `PYTHON*` variable (measured, dev mode off).
  Free-threaded builds (`3.14t`; `Py_MOD_GIL_NOT_USED`): [rules/01](01-tooling-project-setup.md) §8. A compiled extension's
  own C belongs under the C toolchain's sanitizers as well ([`sota-c-cpp` rules/06](../../sota-c-cpp/rules/06-build-tooling-ci.md) §3).

## Audit checklist

- [ ] **FastAPI** —
      `grep -rn "async def" $(grep -rln "APIRouter\|FastAPI" --include="*.py" src/) | head`
      (then check for blocking calls inside);
      `grep -rn "requests\.\|time.sleep\|session.query\|Session(" --include="*.py" src/ | grep -i route`
      (sync-in-async [HIGH]);
      `grep -rn "@\(app\|router\)\.\(get\|post\|put\|delete\)" --include="*.py" src/ -A3 | grep -L response_model | head`
      (ORM leak risk); `grep -rn "AsyncClient()" --include="*.py" src/ | grep -v lifespan`
      (per-request clients [MEDIUM]);
      `grep -rn -B2 "livez\|/health\|healthz" --include="*.py" src/ | grep "^.*def "` (liveness:
      `async def` , no deps (§1 exception));
      `grep -rn "^[A-Z_]* = .*Session\|^engine = " --include="*.py" src/` (module-global state
      vs Depends)
- [ ] **Django ORM** —
      `grep -rn "\.objects\.all()\|\.objects\.filter" --include="*.py" src/ | wc -l` ;
      `grep -rln "select_related\|prefetch_related" --include="*.py" src/ | wc -l` (ratio sanity
      check);
      `grep -rn "for .* in .*\.objects\." --include="*.py" src/ -A2 | grep "\.\(name\|user\|customer\)" | head`
      (N+1 candidates); `grep -rn "count() > 0\|len(.*objects" --include="*.py" src/` (exists()
      instead); `grep -rn "\.raw(\|\.extra(\|RawSQL" --include="*.py" src/` ([HIGH if
      interpolated]); `git log --oneline -- '**/migrations/*.py' | head` (edited-after-merge
      migrations?); `grep -rn "makemigrations --check" .github/ .gitlab-ci.yml 2>/dev/null`
      (drift gate present?); `grep -rn "check --deploy" .github/ .gitlab-ci.yml 2>/dev/null`
      (empty → LOW, no deploy-settings gate, §2; read the output, as the status is 2 whenever either path is absent)
- [ ] **--- App-set cookies: Secure / HttpOnly / SameSite flags (§2 cookies) --- [HIGH for an
      auth or identity token; MEDIUM for a preference]** —
      `grep -rnE '\.set_(signed_)?cookie\(' --include='*.py' src/ | grep -vE 'secure[[:space:]]*=[[:space:]]*True.*httponly[[:space:]]*=[[:space:]]*True|httponly[[:space:]]*=[[:space:]]*True.*secure[[:space:]]*=[[:space:]]*True'`
      (every hit relies on a framework default that is off; a multi-line call is listed too —
      read it; `samesite` is checked by hand)
- [ ] **pytest** (§3) — `grep -rn "def setUp\|TestCase" --include="*.py" tests/` (legacy style
      [LOW]); `grep -rn "pytest.raises(Exception)" --include="*.py" tests/` (too-broad
      [MEDIUM]); `grep -rn "time.sleep" --include="*.py" tests/` (flaky timing [MEDIUM]);
      `grep -rn "scope=\"session\"\|scope=\"module\"" --include="*.py" tests/ conftest.py 2>/dev/null`
      (mutable shared state?);
      `grep -rn "os.environ\[" --include="*.py" tests/ | grep -v monkeypatch` (env pollution);
      `grep -rln "parametrize" --include="*.py" tests/ | wc -l` ;
      `err=$({ [ -d tests ] && [ -r tests ] || { echo "tests/ missing or unreadable" >&2; exit 2; }; grep -rl "hypothesis" --include="*.py" tests/; } 2>&1 >/dev/null); rc=$?` ;
      `case $rc in 0) ;; 1) echo "no property tests" ;; *) echo "SWEEP FAILED, not a finding about their code: $err" ;; esac`
      (the guard is needed: macOS grep exits 1, not 2, when `tests/` is missing under `--include`) ;
      `pytest -q -n auto 2>&1 | tail -3` (parallel-safe = independent);
      `pytest -q -p randomly 2>&1 | tail -3` (order-independent?)
- [ ] **Escape hatch with no runtime checker in CI (§3) [MEDIUM; HIGH where the native call
      takes a length or pointer from input]** —
      `grep -rlE '^[[:space:]]*(import|from)[[:space:]]+(ctypes|cffi)' --include='*.py' . | head -1 ; find . -name '*.c' -not -path './.venv/*' | head -1`
      (any hit = an escape hatch) ;
      `grep -rnE -e '-X[[:space:]]?dev' --include='*.y*ml' --include='*.toml' --include='*.cfg' --include='*.ini' --include='*.sh' . | head -3`
      (no hit = the suite never ran with the debug allocator; `PYTHONDEVMODE` alone is inert
      under `-I`/`-E`)
- [ ] **Property tests whose reach nobody checks (§3) [LOW; MEDIUM on parsers]** —
      `grep -rnE 'assume\(|\.filter\(' --include='*.py' tests/` (each property using one needs
      the reach gate of [`sota-testing` rules/06](../../sota-testing/rules/06-property-fuzzing-mutation.md) §6.6)
