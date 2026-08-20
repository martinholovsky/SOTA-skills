# 03 — Idioms, Pitfalls, Exceptions & Logging

The bugs Python invites, and the idioms that prevent them. Most items here are mechanical to
audit (grep/ruff patterns at the end) and mechanical to fix.

## 1. Mutable default arguments (B006)

Defaults are evaluated **once at definition**. Every call shares the same object.

```python
# Bad — every caller without `tags` shares one list
def create(name: str, tags: list[str] = []) -> Item: ...

# Good
def create(name: str, tags: list[str] | None = None) -> Item:
    tags = [] if tags is None else tags
```

Also applies to `{}`, `set()`, `datetime.now()` (frozen at import time!), and any class
instance default. `dataclass` fields: use `field(default_factory=list)` — Python raises for
bare mutable defaults in dataclasses but not for arbitrary mutable objects.

## 2. Late-binding closures (B023)

Loop variables are looked up when the closure **runs**, not when it's created:

```python
# Bad — all callbacks see the final value of `name`
callbacks = [lambda: greet(name) for name in names]

# Good — bind at definition time
callbacks = [lambda name=name: greet(name) for name in names]
# Better — functools.partial states intent
callbacks = [partial(greet, name) for name in names]
```

Hits hardest with callbacks registered in loops (Qt signals, asyncio callbacks, pytest
parametrization done by hand).

## 3. Comprehensions vs loops

- Comprehension when it fits on 1–2 lines and produces a collection. Loop when there are side
  effects, multiple accumulators, or nested conditionals — a 4-line comprehension with three
  `if`s is worse than a loop.
- **Generator expressions** when the consumer is an aggregator or you iterate once:
  `sum(x.price for x in items)` — no intermediate list.
- Never a comprehension for side effects: `[db.save(x) for x in items]` allocates a list of
  `None`s and hides intent. Use a `for` loop.
- `dict`/`set` comprehensions over `dict(zip(...))` gymnastics. Know
  `{k: f(v) for k, v in d.items()}`.

## 4. Context managers for every resource

Anything with acquire/release semantics goes through `with`: files, locks, connections,
transactions, subprocesses, tempfiles, sockets.

```python
# Bad — leaks on exception, ResourceWarning under -X dev
f = open(path); data = f.read(); f.close()

# Good
with open(path) as f:
    data = f.read()

# Own resources: contextmanager for simple cases
@contextmanager
def acquired(lock: Lock) -> Iterator[None]:
    lock.acquire()
    try:
        yield
    finally:
        lock.release()

# Dynamic numbers of resources
with ExitStack() as stack:
    files = [stack.enter_context(open(p)) for p in paths]
```

Run tests with `python -X dev` occasionally — `ResourceWarning` surfaces unclosed handles.

## 5. pathlib over os.path / string surgery

```python
# Bad
out = os.path.join(os.path.dirname(__file__), "..", "data", name + ".json")

# Good
out = (Path(__file__).parent.parent / "data" / f"{name}.json").resolve()
data = out.read_text(encoding="utf-8")
```

`Path.read_text/write_text/read_bytes`, `.glob`, `.mkdir(parents=True, exist_ok=True)`,
`.with_suffix`, `.relative_to`. Always pass `encoding="utf-8"` to text I/O — the platform
default still bites on Windows until UTF-8 mode is universal. Security note: `Path` does NOT
prevent traversal; see rules/05 §4.

## 6. EAFP vs LBYL

Default to EAFP — ask forgiveness — because LBYL check-then-act races:

```python
# Bad — TOCTOU: file can vanish between check and open
if os.path.exists(path):
    with open(path) as f: ...

# Good
try:
    with open(path) as f: ...
except FileNotFoundError:
    handle_missing()
```

Same for `dict` access (`try/KeyError` or `.get` with a real default, not `if k in d` then
`d[k]` twice), and for any filesystem/network/shared-state precondition. LBYL is fine for pure
in-memory validation of caller arguments where no race exists and the check reads better.

## 7. Dataclass patterns

```python
@dataclass(frozen=True, slots=True)
class Money:
    amount: Decimal
    currency: str

    def __post_init__(self) -> None:
        if self.amount.as_tuple().exponent < -2:
            raise ValueError("sub-cent amount")
```

- `frozen=True` by default: hashable, safe as dict keys, no aliasing surprises.
- `slots=True`: ~40–60% memory reduction, faster attribute access, typo'd attributes raise.
  Skip only when you need `__dict__` (dynamic attrs, some mixin patterns, `cached_property`
  needs `__dict__` — use `slots=True` + a manual cache or drop slots there).
- `kw_only=True` for >3 fields or any boolean field — positional booleans are unreadable.
- `field(default_factory=...)` for mutable defaults; `field(repr=False)` for secrets so they
  don't hit logs.

## 8. Enums

```python
class Status(StrEnum):          # 3.11+: members ARE str — JSON/DB-friendly
    OPEN = "open"
    CLOSED = "closed"
```

- `StrEnum`/`IntEnum` when values serialize; plain `Enum` + `auto()` when values are opaque.
- Compare by identity (`status is Status.OPEN`); never compare enum to raw string except at
  parse boundaries (`Status(raw)` — which also validates and raises `ValueError`).
- `Flag` for bitmask sets instead of int constants.
- Magic strings appearing ≥3 times with branching logic → that's an enum.

## 9. itertools / functools — use the stdlib, don't reimplement

Know cold: `itertools.chain`, `batched` (3.12), `pairwise`, `groupby` (input must be sorted by
the same key — classic bug), `islice`, `product`, `takewhile`;
`functools.cache`/`lru_cache` (caveats in rules/06), `cached_property`, `partial`, `reduce`
(sparingly), `singledispatch` for type-based dispatch without isinstance ladders;
`collections.Counter`, `defaultdict`, `deque` (O(1) popleft — never `list.pop(0)` in a loop).
Hand-rolled chunking/flattening/windowing functions in a utils.py are an audit smell: replace
with itertools and delete.

## 10. Exception design

**Catch narrowly, raise precisely, never silence.**

```python
# Bad — swallows KeyboardInterrupt/SystemExit, hides every bug
try:
    process(item)
except:               # bare
    pass

# Bad — Exception + pass is barely better
except Exception:
    pass

# Good
try:
    process(item)
except (ValidationError, IOError) as e:
    logger.warning("skipping %s: %s", item.id, e)
```

Rules:
- **Never bare `except:`** (E722). `except Exception` is the widest acceptable catch and only
  at top-level boundaries (request handler, worker loop, CLI main) — and it must log with
  traceback (`logger.exception(...)`) and usually re-raise or convert.
- Define a small exception hierarchy per package: `class AppError(Exception)` root, callers
  catch your types, not `Exception`.
- **Chain on translation:** `raise StorageError("save failed") from e` — preserves the cause;
  `from None` only when deliberately hiding (rare). Bare re-wrap without `from` loses the
  trail (ruff B904).
- **No exceptions as cross-layer control flow.** Inside one function/module, `StopIteration`-
  style signaling is idiomatic; raising `NotFoundError` from the DB layer and catching it in
  the HTTP layer is fine *if it's a declared domain exception*. What's banned: using generic
  exceptions to implement branching across layers ("raise ValueError to mean retry"), and
  try/except spanning 50 lines where you can't tell which statement is expected to fail —
  keep `try` bodies minimal.
- `else:` clause on try when code should run only if no exception — keeps the `try` body tight.
- **Exception groups (3.11+):** `TaskGroup` and concurrent code raise `ExceptionGroup`; handle
  with `except*`:
  ```python
  try:
      async with asyncio.TaskGroup() as tg: ...
  except* httpx.HTTPError as eg:
      for e in eg.exceptions: logger.error("fetch failed: %s", e)
  ```
  Code that catches `Exception` around a TaskGroup and inspects nothing loses errors.

## 11. Logging done right

```python
logger = logging.getLogger(__name__)        # module level, never the root logger

# Bad — f-string formats even when DEBUG is off; breaks aggregation grouping
logger.debug(f"user {user_id} fetched {n} rows")

# Good — lazy %-formatting; args interpolated only if the record is emitted
logger.debug("user %s fetched %d rows", user_id, n)

# Errors with traceback
except StorageError:
    logger.exception("save failed for order %s", order_id)   # includes stack automatically
```

- **No f-strings/`.format()`/`+` in log calls** (ruff `G` rules): wasted CPU at high-volume
  call sites, and every message becomes unique — log aggregators can't group them, and
  user-controlled values get interpolated even when not logged (injection surface).
- Libraries: never call `basicConfig()`, never add handlers — configure logging only in the
  application entry point (`logging.config.dictConfig`). A library that configures logging
  hijacks the host app.
- Structured logging for services: `structlog` or stdlib + JSON formatter; bind context
  (request id, user id) once, not per call. Put variable data in fields, not in the message.
- `logger.exception` only inside `except` blocks; `logger.error(..., exc_info=True)` is the
  equivalent elsewhere.
- Never log secrets/tokens/PII — pair with `field(repr=False)` and dedicated redaction.
- No `print()` in library/server code (ruff T20). CLIs print to stdout for *output*, log to
  stderr for *diagnostics*.

## 12. Small-but-deadly grab bag

- `is`/`is not` only for `None`, `True`, `False`, sentinels, enums — never for strings/ints
  (interning makes it *sometimes* work, which is worse).
- Returning `-1`/`0`/`""` to mean "absent" instead of `None`: type-checks, survives a
  truthiness check, and flips ordering comparisons. Producer shape and the three
  detectors in rules/02 §2a.
- Naive datetimes: always `datetime.now(tz=timezone.utc)`; `utcnow()` is deprecated and naive
  (ruff DTZ).
- `zip(a, b, strict=True)` (3.10+) when silent truncation would hide a length-mismatch bug.
- Shadowing builtins (`list`, `id`, `type`, `input`) — rename (ruff A).
- String building in loops: collect + `"".join(parts)` (perf details rules/06).
- `round()` is banker's rounding; money math uses `Decimal` with explicit quantize.
- Don't mutate a list/dict while iterating it — iterate a copy or build a new one.

## Audit checklist

```bash
# Ruff covers most of this file — run first
uvx ruff check --select B006,B008,B023,B904,E722,BLE,G,T20,DTZ,PTH,SIM,A,C4 --statistics .

# Bare/broad excepts [HIGH if swallowing, MEDIUM otherwise]
grep -rn "except:$\|except: " --include="*.py" src/
grep -rn -A1 "except Exception" --include="*.py" src/ | grep -B1 "pass$"

# Exception chaining lost
uvx ruff check --select B904 .                              # raise-without-from in except

# Mutable defaults & late binding
uvx ruff check --select B006,B023 .

# Logging
grep -rn 'logger\.\(debug\|info\|warning\|error\)(f"' --include="*.py" src/   # f-strings in logs [LOW-MED]
grep -rn "basicConfig" --include="*.py" src/ | grep -v "main\|__main__\|cli"  # library configuring logging [MEDIUM]
grep -rn "print(" --include="*.py" src/ | grep -v "cli\|__main__\|test"       # stray prints [LOW]

# Resource handling
grep -rn "= open(" --include="*.py" src/ | grep -v "with "                    # unmanaged file handles [MEDIUM]
grep -rn "\.close()" --include="*.py" src/ | head                             # manual close → with-able?

# datetime & os.path modernization
uvx ruff check --select DTZ,PTH --statistics .
grep -rn "utcnow()" --include="*.py" src/                                     # naive UTC [MEDIUM]

# Identity misuse & list.pop(0)
grep -rn 'is "" \|is "\| is [0-9]' --include="*.py" src/
grep -rn "\.pop(0)" --include="*.py" src/                                     # O(n) dequeue [perf]

# groupby without sort (manual review)
grep -rn "groupby(" --include="*.py" src/
```
