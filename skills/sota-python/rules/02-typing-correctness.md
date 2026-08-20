# 02 — Typing & Correctness

Types are executable documentation plus a proof system. The standard: every public API fully
annotated, strict checker green, runtime validation only at trust boundaries, zero `Any` leaks.

## 1. Annotate every public API — fully

Every public function, method, and class attribute gets parameter and return annotations,
including `-> None`. Private helpers should be annotated too; inference inside bodies is the
checker's job, signatures are yours.

```python
# Bad — partial annotation is worse than none: callers get silent Any
def fetch(url, timeout=10.0) -> dict: ...

# Good
def fetch(url: str, timeout: float = 10.0) -> dict[str, object]: ...
```

- Use built-in generics (`list[int]`, `dict[str, X]`) and `X | None` — never `typing.List`,
  `typing.Optional` in new code (ruff `UP` auto-fixes).
- Accept abstract, return concrete: take `Iterable[str]` / `Sequence[str]` / `Mapping[K, V]`,
  return `list[str]` / `dict[K, V]`. Demanding `list` rejects tuples and generators for no reason.
- Annotate module-level constants and class attributes that a checker can't infer precisely
  (`STATUSES: Final = frozenset({"open", "closed"})`).

## 2. Optional is explicit, and `None` is handled

`x: str | None = None` — the `| None` is mandatory; implicit-optional is dead. Every nullable
value must be narrowed before use:

```python
def handler(user: User | None) -> str:
    if user is None:
        raise UnauthenticatedError          # narrow once, early
    return user.name                        # checker knows user: User
```

- Don't smuggle nullability through `or` defaults when `""`/`0`/`[]` are valid values:
  `name = arg or default` is a bug if `arg=""` is meaningful. Use `if arg is None`.
- Return `None` for "absent" only when callers genuinely branch on it; raising a precise
  exception is usually better than `T | None` propagating through five layers.

## 2a. In-band sentinels: `-1` is not `None`

The failure §2 exists to prevent has a second spelling that the type checker cannot
see. Instead of `int | None`, a converter returns a **value from the domain** to mean
"absent":

```python
_SENTINEL = -1                                   # "missing int"

def _convert(key: str, raw: str) -> int:
    if not raw:
        return _SENTINEL                         # absent
    try:
        return int(raw)
    except ValueError:
        return _SENTINEL                         # malformed — same value, different cause
```

Three defects, none of which is a type error:

- **Two conditions collapse into one value.** Absent and malformed are
  indistinguishable downstream, so the one that matters (a parser bug upstream)
  can never be counted, alerted on, or told apart from ordinary sparse data.
- **`-1` is truthy**, so `if line_num:` — which reads as a presence check and is the
  idiom people reach for — **passes** on the sentinel and admits it to the body.
  `0`, the other popular sentinel, fails the same test on a legitimate value. Neither
  spelling of the check is right, because the value carries no absence information.
- **It has an ordering.** The sentinel silently **loses** every `<` comparison against
  a real value and **wins** every `>`. Where line/offset/version numbers are compared
  as a proxy for ordering — `use > alloc`, `check < call`, `end >= start` — one
  missing operand flips the predicate, and *which* direction it flips depends on which
  side went missing. That is a fail-open in one direction and a false positive in the
  other, from one input.

**The tell that this is a class and not a slip: the author usually defends one operand
and not the other.**

```python
# the collection is filtered against the sentinel...
lo = min((x for x in candidates if x and x > 0), default=0)
# ...the scalar on the other side of the same comparison is not
if lo > 0 and lo < line_num:                     # line_num may be -1 → False → guard skipped
    ...
```

Whoever wrote `x > 0` knew the sentinel existed. Filtering is per-site, so it is
applied wherever the author was thinking about it and omitted everywhere else — which
makes an **asymmetric guard** a far better audit signal than the sentinel constant
itself.

**Fix, in order of preference:** return `int | None` and narrow at the call site; or
raise for the malformed case and return `None` only for absent, so the two causes stay
distinct. Reach for a sentinel only when a wire format or a fixed-width store forbids
absence — and then it is **per field**, documented with that field's domain, never one
constant applied across a heterogeneous set (see `sota-databases` rules/01, *Modeling
hygiene*, for the persistence half).

### Detecting it — three probes, decreasing precision

1. **Producer (near-zero false positives, AST-checkable).** One function returning the
   *same constant* from a not-found branch and from an `except` branch. That shape is
   almost never intentional, and it is the declaration — fix it once and every caller
   is fixed.
2. **Asymmetric guard (the one that catches the live bug).** A comparison where one
   operand is filtered against the sentinel and the other is not. Greppable in review
   and visible in a diff; see the example above.
3. **Truthiness-as-presence.** `if x:` / `if x and ...` guarding an `int` whose domain
   includes the sentinel or `0`. High recall, high false-positive rate — use it to
   build a list to read, not a gate.

**A value-based lint ("flag any `-1` in this field") is only sound where the field's
domain is stated non-negative, and you cannot assume that per-field from the converter
— the converter is uniform, the domains are not.** A field where the producer emits
`-1` legitimately (an index meaning "not an argument", an enum's *unset* member, a
`ORDER` that is genuinely signed) makes such a lint 100% false positive, and the code
*cannot recover* which meaning a stored `-1` had. So: key the rule on the
**declaration**, and add a value lint only on the subset that carries an explicit
non-negative domain declaration — which usually does not exist yet, and writing it
down is part of the fix. Measure the per-field distribution before you lint: a field
where the sentinel is 99% of rows and one where it is 0% are different problems.

## 3. No `Any` leaks

`Any` disables checking transitively — one `Any` return poisons every downstream variable.

- Prefer `object` for "truly anything, but I won't touch it": the checker forces a narrow
  before use. `Any` means "trust me"; `object` means "prove it".
- Boundary data (JSON, ORM rows, env vars) enters as `Any` — convert immediately via pydantic /
  TypedDict cast / explicit parsing (see §6). Never pass raw `json.loads` output deep into
  the call graph.
- `cast()` is a last resort and must be locally, obviously true. A `cast` that encodes a
  cross-module assumption is a latent bug.
- Audit signal: `def f(...) -> Any`, `dict[str, Any]` proliferating beyond the parse layer,
  un-parameterized `dict`/`list`/`Callable` in signatures.

## 4. Protocol over ABC when structure is the contract

```python
from typing import Protocol, runtime_checkable

class SupportsClose(Protocol):
    def close(self) -> None: ...

def shutdown(resources: Iterable[SupportsClose]) -> None:
    for r in resources:
        r.close()
```

- **Protocol** when you define the interface for *callers* — third-party and stdlib types
  conform without inheriting. No registration, no import coupling, testable with plain fakes.
- **ABC** when you own a closed hierarchy and want shared implementation + instantiation
  guards (`@abstractmethod` raising at construction).
- Don't write one-method ABCs that exist only for typing — that's a Protocol, or just a
  `Callable[[X], Y]` parameter.
- `@runtime_checkable` only enables `isinstance` checks of method *presence*, not signatures —
  don't rely on it for validation.

## 5. Data-shape decision tree: TypedDict vs dataclass vs pydantic

| Need | Use |
|---|---|
| Annotating dicts you don't construct (JSON you read, kwargs, external API shapes) | `TypedDict` (+ `NotRequired`, `Required`) |
| Internal value objects, domain entities, config you construct in code | `@dataclass(frozen=True, slots=True)` |
| Untrusted/external input needing **runtime validation + coercion** (HTTP bodies, env, files, LLM output) | pydantic v2 `BaseModel` |
| Tiny heterogeneous record, positional, immutable | `NamedTuple` |
| Heavy attrs ecosystem already in place | `attrs` (equivalent to dataclass row) |

Rules of thumb:
- **Pydantic at the boundary, dataclasses inside.** Validating the same data repeatedly in
  inner layers is wasted CPU and muddles trust zones: validate once on entry, then pass typed,
  trusted objects. Inner code relies on the static checker, not re-validation.
- TypedDict performs zero runtime checks — it's a static-only promise. Never "validate" with it.
- Don't use pydantic models as general-purpose internal classes; construction cost and
  validation semantics (coercion!) surprise you. `model_construct()` everywhere is a smell that
  you wanted a dataclass.
- Default to `frozen=True, slots=True` dataclasses; mutability and dynamic attributes are
  opt-in exceptions, not defaults (details in rules/03).

## 6. Runtime validation at boundaries — pydantic v2

```python
from pydantic import BaseModel, Field, TypeAdapter

class CreateUser(BaseModel):
    model_config = {"extra": "forbid", "strict": False}
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+$")
    age: int = Field(ge=0, le=150)

user = CreateUser.model_validate(request_json)   # raises ValidationError with paths

# Validating non-model shapes:
users = TypeAdapter(list[CreateUser]).validate_python(payload)
```

- `extra="forbid"` on input models — silently dropped unknown fields hide client bugs and
  typo'd field names.
- Know coercion: lax mode turns `"3"` into `3`. For protocol-strict boundaries use
  `strict=True` per-field or model-wide.
- Don't catch `ValidationError` and return a vague 500 — surface field paths (FastAPI does
  this for you; see rules/07).

## 7. Exhaustiveness with `assert_never`

Make the checker fail the build when someone adds an enum member or union arm:

```python
from typing import assert_never

type Event = Created | Updated | Deleted

def apply(e: Event) -> str:
    match e:
        case Created():  return "c"
        case Updated():  return "u"
        case Deleted():  return "d"
        case _:
            assert_never(e)   # checker error if a new arm appears; runtime error if reached
```

Same pattern for `Enum` in if/elif chains and `Literal` unions. Any `match` over a closed type
without `assert_never` (or a raising `case _`) is an audit finding — silent fallthrough returns
`None` and detonates elsewhere.

## 8. Generics that carry information

```python
def first[T](items: Sequence[T]) -> T | None: ...

class Repository[M: HasId]:
    def get(self, id_: int) -> M | None: ...
    def add(self, item: M) -> M: ...
```

- Use a TypeVar only when it appears **at least twice** (linking input to output, or two
  inputs). `def f[T](x: T) -> None` is pointless — that's `object`.
- `Self` (3.11+) for fluent APIs and alternate constructors — not the class name, which breaks
  subclassing:
  ```python
  class Query:
      def where(self, **kw: object) -> Self: ...
  ```
- `ParamSpec` for decorators so wrapped functions keep their signatures:
  ```python
  def retry[**P, R](fn: Callable[P, R]) -> Callable[P, R]: ...
  ```
  A decorator returning `Callable[..., Any]` erases types for every call site under it —
  HIGH-value fix in shared codebases.
- Variance: prefer the PEP 695 inferred variance; if you hand-write `TypeVar`, get
  covariance right for read-only containers (`_T_co`).

## 9. Narrowing tools: TypeGuard, TypeIs, overload

Teach the checker what your runtime checks prove:

```python
from typing import TypeIs, overload

def is_str_list(val: list[object]) -> TypeIs[list[str]]:
    return all(isinstance(x, str) for x in val)

if is_str_list(items):
    items[0].upper()        # checker knows list[str] here — and list[object] in the else
```

- Prefer `TypeIs` (3.13 / typing_extensions) over `TypeGuard`: it narrows in **both**
  branches and requires the narrowed type to be consistent with the input — fewer footguns.
- Write a guard once instead of sprinkling `cast()` after every `isinstance`-ish check.

`@overload` when return type depends on argument types/values — the classic is a
default-vs-None getter:

```python
@overload
def get_setting(key: str) -> str | None: ...
@overload
def get_setting(key: str, default: str) -> str: ...
def get_setting(key: str, default: str | None = None) -> str | None:
    return _settings.get(key, default)
```

Without overloads, every caller with a default still has to handle an impossible `None`.
Keep overload sets small (2–4); a 10-overload function wants a redesign. Typed `**kwargs`:
`def f(**kwargs: Unpack[MoveArgs]) -> None` with a TypedDict — stop typing kwargs as
`object`/`Any` in builder-style APIs.

## 10. Misc correctness rules

- `TYPE_CHECKING` blocks for import-cycle-breaking and heavy import deferral. On a 3.14+
  floor, deferred annotation evaluation (PEP 649/749) is the default: forward references
  work unquoted, runtime-inspected annotations (pydantic/FastAPI) keep working, and
  `from __future__ import annotations` should NOT be added to new code (it forces the old
  string semantics). On older floors, don't blanket-add the future import in
  FastAPI/pydantic modules — they need real annotations there.
- `Literal` for closed string/int sets in signatures (`mode: Literal["r", "w"]`), `Enum` when
  the set needs behavior or iteration.
- `Final` for constants; `@override` (3.12) on every overriding method — catches renamed
  base methods at check time.
- NewType for ids that must not interchange: `UserId = NewType("UserId", int)` prevents
  passing an `OrderId` where a `UserId` is expected at zero runtime cost.

## Audit checklist

```bash
# Any leakage [MEDIUM where it crosses module boundaries]
grep -rn "-> Any\|: Any" --include="*.py" src/ | grep -v "test_" | head -50
grep -rn "dict\[str, Any\]" --include="*.py" src/ | wc -l        # boundary-only is OK; everywhere is not
grep -rn "Callable\[\.\.\., " --include="*.py" src/               # signature-erasing decorators?

# Bare/unscoped ignores [LOW each, MEDIUM in aggregate]
grep -rn "type: ignore$" --include="*.py" .
grep -rn "# noqa$" --include="*.py" .

# Legacy typing forms — ruff UP should be clean
uvx ruff check --select UP,ANN --statistics .
grep -rn "typing.Optional\|typing.List\|typing.Dict\|Optional\[" --include="*.py" src/ | head

# In-band sentinels standing in for None (§2a) [HIGH where the value is compared]
grep -rnE "return -1|return 0[^.0-9]|= *-1 *(#|$)" --include="*.py" src/    # producer: same constant from two branches?
grep -rnB2 -- "-> int:" --include="*.py" src/ | grep -c "except"            # int-returning fn with an except arm
grep -rnE "if [a-z_]+ (and|>) 0.*<|> 0.*if" --include="*.py" src/           # asymmetric guard: one operand filtered
grep -rnE "^\s*if [a-z_]*(num|idx|index|count|offset|line|col)[a-z_]*:" --include="*.py" src/  # truthiness-as-presence

# Unhandled Optionals / implicit None returns
uvx mypy --strict src/ 2>&1 | grep -c "error"                     # any errors = not strict-clean
grep -rn "or \[\]\|or {}\|or ''" --include="*.py" src/            # falsy-default smell [LOW, verify]

# Exhaustiveness
grep -rn "match " --include="*.py" src/ -A1 | grep -B1 "case _" | head   # then check assert_never use
grep -rln "assert_never" --include="*.py" src/ || echo "no exhaustiveness guards"

# Validation layering
grep -rn "model_validate\|TypeAdapter" --include="*.py" src/      # should cluster at edges
grep -rn "model_construct" --include="*.py" src/                  # smell: wanted a dataclass [LOW]
grep -rn 'extra.*allow\|extra="ignore"' --include="*.py" src/     # permissive input models [LOW-MEDIUM]

# Protocol/ABC hygiene
grep -rn "class.*ABC).*:" --include="*.py" src/ -A3 | grep -c abstractmethod  # 1-method ABCs → Protocol?
grep -rn "isinstance.*Protocol" --include="*.py" src/             # runtime_checkable misuse

# cast() density [investigate each]
grep -rn "cast(" --include="*.py" src/ | grep -v test
```
