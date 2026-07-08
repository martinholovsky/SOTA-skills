# 07 — FastAPI, Django, and pytest Mastery

Framework-specific traps plus the testing discipline that applies everywhere. Deep general
rules live elsewhere (async → rules/04, validation → rules/02, SQL safety → rules/05).

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
  → blocks the **single** event loop; whole service serializes. See rules/04 §3.
- `def` (sync) endpoint → FastAPI runs it in the anyio threadpool (default ~40 threads) —
  blocking is *safe* there but throughput caps at pool size.
- Rule: endpoint is `async def` **only if everything it awaits is truly async** (asyncpg /
  SQLAlchemy async session / httpx.AsyncClient). Mixed stack? Make the endpoint `def` and
  stay sync, or fix the stack. An `async def` endpoint with zero `await` inside is a bug
  marker — it gains nothing and risks someone adding blocking calls later.
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
- Make N+1 a test failure: `django-assert-num-queries` /
  `self.assertNumQueries(2)`, or `nplusone`/`django-zen-queries` in dev.
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
  stalls the loop (rules/04 §7).
- Settings via `django-environ`/env vars; `DEBUG=False`, `ALLOWED_HOSTS`, `SECRET_KEY` from
  secrets store — run `manage.py check --deploy` in CI.
- Keep `.raw()`, `.extra()`, `RawSQL` out of the codebase or parameterized + reviewed
  (rules/05 §3).

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
  order, `lru_cache`d functions tested without `cache_clear` between tests (rules/06 §4),
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
- Async tests: `asyncio_mode = "auto"` (rules/04 §9). Time: `freezegun`/`time-machine`,
  never `sleep`.
- Coverage gate (`--cov --cov-fail-under=N`) measures *executed*, not *asserted* — treat as
  floor, not target; mutation testing (`mutmut`) where correctness is critical.

## Audit checklist

```bash
# FastAPI
grep -rn "async def" $(grep -rln "APIRouter\|FastAPI" --include="*.py" src/) | head   # then check for blocking calls inside
grep -rn "requests\.\|time.sleep\|session.query\|Session(" --include="*.py" src/ | grep -i route  # sync-in-async [HIGH]
grep -rn "@\(app\|router\)\.\(get\|post\|put\|delete\)" --include="*.py" src/ -A3 | grep -L response_model | head  # ORM leak risk
grep -rn "AsyncClient()" --include="*.py" src/ | grep -v lifespan              # per-request clients [MEDIUM]
grep -rn "^[A-Z_]* = .*Session\|^engine = " --include="*.py" src/              # module-global state vs Depends

# Django ORM
grep -rn "\.objects\.all()\|\.objects\.filter" --include="*.py" src/ | wc -l
grep -rln "select_related\|prefetch_related" --include="*.py" src/ | wc -l     # ratio sanity check
grep -rn "for .* in .*\.objects\." --include="*.py" src/ -A2 | grep "\.\(name\|user\|customer\)" | head  # N+1 candidates
grep -rn "count() > 0\|len(.*objects" --include="*.py" src/                    # exists() instead
grep -rn "\.raw(\|\.extra(\|RawSQL" --include="*.py" src/                      # [HIGH if interpolated]
git log --oneline -- '**/migrations/*.py' | head                               # edited-after-merge migrations?
grep -rn "makemigrations --check" .github/ .gitlab-ci.yml 2>/dev/null          # drift gate present?

# pytest
grep -rn "def setUp\|TestCase" --include="*.py" tests/                         # legacy style [LOW]
grep -rn "pytest.raises(Exception)" --include="*.py" tests/                    # too-broad [MEDIUM]
grep -rn "time.sleep" --include="*.py" tests/                                  # flaky timing [MEDIUM]
grep -rn "scope=\"session\"\|scope=\"module\"" --include="*.py" tests/ conftest.py 2>/dev/null  # mutable shared state?
grep -rn "os.environ\[" --include="*.py" tests/ | grep -v monkeypatch          # env pollution
grep -rln "parametrize" --include="*.py" tests/ | wc -l
grep -rln "hypothesis" --include="*.py" tests/ || echo "no property tests"
pytest -q -n auto 2>&1 | tail -3                                               # parallel-safe = independent
pytest -q -p randomly 2>&1 | tail -3                                           # order-independent?
```
