# Language Idioms & Pitfalls

## Equality and coercion

- Always `===`/`!==`. `==` coercion rules are unmemorizable (`[] == false`, `'' == 0`, `null == undefined` all true). Single allowed exception: `x == null` to test null-or-undefined at once — but `x === null || x === undefined` or `x ?? fallback` is clearer; just ban `==` entirely (`eslint eqeqeq: ["error", "always"]`).
- `Object.is` only for `NaN`/`-0` distinction. `NaN === NaN` is false; use `Number.isNaN(x)` — never the global `isNaN`, which coerces (`isNaN('foo')` is true).
- `Number.isInteger`, `Number.isFinite` over global counterparts for the same reason.

## Nullish discipline: `??` and `?.`

`||` treats `0`, `''`, `false` as missing. `??` only treats `null`/`undefined` as missing.

```ts
// BAD — port 0 and empty prefix silently replaced
const port = config.port || 3000;
const prefix = config.prefix || '/api';

// GOOD
const port = config.port ?? 3000;
const retries = opts.retries ?? 3;        // retries: 0 respected
el.count ??= 0;                            // nullish assignment
```

Optional chaining rules:
- `?.` is for genuinely-optional data, not for silencing the compiler. A long chain `a?.b?.c?.d` usually means the type is wrong or validation was skipped upstream — fix the source.
- `x?.()` for optional callbacks; `arr?.[i]` for optional indexing.
- Don't combine `?.` with non-null assertion `!` — pick one truth. `!` is banned in app code except immediately after an explicit check the compiler can't see (document why); prefer restructuring so narrowing works.
- Remember `a?.b.c` short-circuits the whole chain when `a` is nullish — `.c` is safe; but `(a?.b).c` is not.

## Array method selection

Pick the method that states intent; reviewers read methods faster than loop bodies.

| Need | Use | Not |
|---|---|---|
| transform each | `map` | `forEach` + push |
| keep some | `filter` | manual loop |
| first match | `find` / `findIndex` / `findLast` | `filter(...)[0]` |
| any/all match | `some` / `every` | `filter(...).length > 0` |
| reduce to one value | `reduce` (sparingly) | — |
| flatten + map | `flatMap` | `map(...).flat()` |
| membership | `includes` | `indexOf !== -1` |
| group | `Object.groupBy` / `Map.groupBy` (ES2024) | reduce boilerplate |
| index from end | `at(-1)` | `arr[arr.length - 1]` |

- `forEach` only for pure side effects; it ignores return values and cannot `await` correctly (`forEach(async ...)` fires-and-forgets every iteration — classic bug; use `for...of` with `await`, or `Promise.all(arr.map(...))` for parallel).
- `reduce` building objects/arrays with spread per iteration is O(n²) — use a mutable accumulator inside the reduce or a plain loop.
- Early-exit needs: `some`/`every`/`find` short-circuit; `map`/`filter` don't — use `for...of` when you must break out of a transform.
- Don't chain `filter().map()` over hot million-element arrays; one `for...of` or `flatMap` pass is fine. Below that scale, readability wins.

## In-band sentinels: `-1`, and why `NaN` is the better-behaved one

`indexOf`, `lastIndexOf` and `findIndex` all return `-1` when not found (verified,
Node 24). The idiom is fine where you test it immediately — `.includes()` /
`.some()` say what you mean — and becomes the class in `sota-architecture` rules/02 §8a
the moment the `-1` is stored, passed, or compared later.

Two sentinels with **opposite** failure behaviour, both verified:

| | `> 20` | `< 20` | consequence |
|---|---|---|---|
| `-1` | `false` | `true` | **lies**: wins one ordering, loses the other |
| `NaN` | `false` | `false` | **poisons**: every comparison is false, incl. `NaN === NaN` |

`parseInt("x")` → `NaN` is therefore the *safer* of the two: it cannot silently win
a comparison, and `Number.isNaN` is an unambiguous test. `-1` cannot be tested
without knowing the field's domain. Neither is as good as `null`/`undefined` with
`strictNullChecks` and `??` (see *Nullish discipline* above) — note `-1 ?? fallback`
is `-1`, so `??` does **not** rescue a sentinel; only `null`/`undefined` trigger it.

- TS: type the absent case (`number | null`), never `number` with a documented
  magic value. A `-1` in a return type is invisible to every checker.
- Audit: `grep -rnE 'return -1|=== -1|!== -1' --include='*.ts' --include='*.js' src/`
  — the `=== -1` hits are usually correct (immediate tests); the `return -1` hits are
  the producers, and a stored `-1` is where it goes wrong.

## Immutability patterns

Mutating shared data causes spooky action at a distance and breaks React/state-library change detection.

```ts
// BAD — sort/reverse/splice mutate in place
const sorted = users.sort((a, b) => a.age - b.age);   // also reordered `users`!

// GOOD — ES2023 change-by-copy methods
const sorted = users.toSorted((a, b) => a.age - b.age);
const reversed = items.toReversed();
const without = items.toSpliced(i, 1);
const updated = items.with(i, newItem);
```

- Mutators to flag on shared/parameter arrays: `sort`, `reverse`, `splice`, `push/pop/shift/unshift`, `fill`, `copyWithin`. Local arrays you just created may be mutated freely — purity at the boundary, pragmatism inside.
- Deep copy: `structuredClone(obj)` — handles Dates, Maps, Sets, cycles, typed arrays. Never `JSON.parse(JSON.stringify(x))` (drops `undefined`, functions, Dates become strings, throws on cycles). Note structuredClone drops functions and prototypes — data only.
- Shallow update idiom: `{ ...obj, field: v }` / `[...arr, item]` — shallow is fine when nested values are themselves replaced, not mutated.
- Declare `readonly` arrays/properties in signatures; `as const` for fixed tables. For ordinary data `Object.freeze` is shallow and adds little that types don't already enforce. Security-critical objects (escapers, sanitizer wrappers, security config) are the exception: freeze them deeply at runtime (rules/05 §"Prototype pollution").
- `let` is a smell outside loops/accumulators; `const` everywhere (`prefer-const` lint).

## Map/Set over object-as-map

Objects as dictionaries inherit `Object.prototype` (`'toString' in obj` is true!), stringify all keys, and are the prototype-pollution sink.

```ts
// BAD
const cache: Record<string, User> = {};
if (cache[name]) ...        // breaks for name = "constructor"

// GOOD
const cache = new Map<string, User>();
cache.set(name, user);
cache.get(name);
```

- `Map`: arbitrary key types, `.size`, guaranteed insertion order, faster frequent add/delete, no prototype hazards.
- `Set` for membership: `seen.has(x)` is O(1) vs `arr.includes(x)` O(n). Dedupe: `[...new Set(arr)]`.
- If an object truly must be a dictionary (JSON shape), create it via `Object.create(null)` or always guard with `Object.hasOwn(obj, key)` (ES2022 — replaces `obj.hasOwnProperty`).
- `WeakMap`/`WeakSet` to associate data with objects without preventing GC (e.g., DOM node metadata, memoization keyed by object).
- `Map.prototype.getOrInsert(key, default)` / `getOrInsertComputed(key, fn)` (ES2026 "Upsert"; per MDN browser-compat-data: Node 26.0, Chrome/Edge 145, Firefox 144, Safari 26.2) replace the check-then-set dance for cache/grouping maps — use where your runtime floor allows.
- `Record<string, T>` indexing under `noUncheckedIndexedAccess` correctly yields `T | undefined` — Map's `.get` was always honest about this.

## Error handling

Never throw strings or plain objects — they lose stack traces and break `instanceof` routing.

```ts
// BAD
throw 'user not found';
throw { code: 404 };
catch (e) { console.log(e); throw new Error('failed: ' + e); }   // stack lost

// GOOD — subclass + cause chain
class NotFoundError extends Error {
  constructor(public readonly resource: string, public readonly id: string, opts?: ErrorOptions) {
    super(`${resource} ${id} not found`, opts);
    this.name = 'NotFoundError';
  }
}

try {
  await db.query(sql);
} catch (e) {
  throw new NotFoundError('user', id, { cause: e });   // ES2022 cause preserves the chain
}
```

Rules:
- `catch (e)` is `unknown` — narrow with `instanceof` before reading `.message`. Helper for the rest: `const toError = (e: unknown): Error => e instanceof Error ? e : new Error(String(e), { cause: e });`
- Set `this.name` in subclasses; route on `instanceof` or a `code` field, never on message text.
- Always pass `{ cause: e }` when wrapping — loggers (pino) serialize the chain.
- Never swallow: empty `catch {}` is a finding unless commented with why. Catch only where you can handle or add context; otherwise let it propagate.
- `finally` for cleanup; or ES2027 explicit resource management (Stage 4 May 2026): `using conn = await pool.acquire()` with `[Symbol.asyncDispose]` (use `await using` for async disposal) — adopt where the runtime/tsconfig supports it.

Result-style for expected failures: exceptions for bugs/infra, values for domain outcomes the caller must handle.

```ts
type Result<T, E> = { ok: true; value: T } | { ok: false; error: E };

async function parsePrice(input: string): Promise<Result<Cents, 'invalid' | 'negative'>> { /* ... */ }

const r = await parsePrice(raw);
if (!r.ok) return showError(r.error);   // compiler forces the check
use(r.value);
```

Use Result (hand-rolled discriminated union, or neverthrow if the team wants combinators) for validation, parsing, business-rule failures. Don't Result-ify everything — infra errors (DB down) should still throw. ES2025 `try`-expression proposals aside, today the union is the idiom. `safeParse` from zod is exactly this pattern.

## Iterators and generators

- Generators for lazy/infinite/paginated sequences — they avoid materializing intermediate arrays:

```ts
async function* paginate(url: string): AsyncGenerator<Item> {
  let next: string | null = url;
  while (next) {
    const page = await fetchPage(next);
    yield* page.items;
    next = page.nextUrl;
  }
}
for await (const item of paginate(api)) { if (matches(item)) break; }  // stops fetching early
```

- ES2025 iterator helpers: `Iterator.from(it).filter(f).map(g).take(10).toArray()` — lazy chaining without arrays.
- Make domain collections iterable via `[Symbol.iterator]` rather than exposing internal arrays.
- Caveat: generators are single-pass; spreading one consumes it. Don't iterate twice.

## Proxy caution

`Proxy` is for frameworks (Vue reactivity, immer), not application code. Costs: every property access pays a trap-call penalty; identity breaks (`proxy !== target`); `this`-binding bugs with private fields and built-ins (Map/Date methods throw through naive proxies); devtools/debugging opacity. If you reach for Proxy in app code, the answer is almost always an explicit function, a class, or a Map. `Reflect.*` belongs inside proxy handlers, rarely elsewhere.

## Dates: Temporal, and surviving without it

`Date` is mutable, months are 0-indexed, parsing is implementation-defined, and it has no timezone besides local/UTC. Temporal (Stage 4 March 2026, part of ES2027; shipped in Chrome/Edge 144+, Firefox 139+, and enabled by default in Node 26) fixes all of it — immutable, explicit types:

```ts
// GOOD — Temporal (Safari still hasn't shipped it — use `temporal-polyfill` for web targets)
const meeting = Temporal.ZonedDateTime.from('2026-03-08T09:00[America/New_York]');
const later = meeting.add({ hours: 2 });                       // DST-safe
const dur = end.since(start);                                  // Temporal.Duration
const today = Temporal.Now.plainDateISO('Europe/Prague');
```

Type selection: `Instant` for timestamps, `PlainDate` for calendar dates (birthdays — no timezone!), `PlainTime`, `ZonedDateTime` for wall-clock + zone, `Duration` for spans. Choosing the right type eliminates the bug class.

Until Temporal is available everywhere you ship (Node ≥26 backends: it is; browser code: polyfill until Safari ships): store/transmit UTC ISO-8601 strings or epoch ms; convert at display; use date-fns (tree-shakeable) over dayjs/moment (moment is dead — flag it). Never do arithmetic by adding `86400000` — DST days are 23/25h.

## Number precision and money

- All JS numbers are float64: `0.1 + 0.2 !== 0.3`; integers exact only to `Number.MAX_SAFE_INTEGER` (2^53−1). 64-bit DB IDs and Twitter snowflakes silently corrupt as numbers — keep them strings.
- Money: integer minor units (cents) in a branded type, never floats.

```ts
type Cents = Brand<number, 'Cents'>;
const total = (items: readonly Cents[]) => items.reduce((a, b) => (a + b) as Cents, 0 as Cents);
const display = (c: Cents) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(c / 100);
```

- Division/percentages: decide the rounding rule explicitly (`Math.round` half-away-from-zero vs banker's), document it, test it. Allocation (splitting $10 three ways) must distribute the remainder, not round each share.
- `BigInt` for >2^53 integers (crypto, snowflakes, wei). Don't mix with `number` (`1n + 1` throws); `JSON.stringify` throws on BigInt — serialize as string.
- High-precision decimals (rates, FX): a decimal library (`decimal.js`/`big.js`) or do the math in the database. The TC39 Decimal proposal isn't shipped.
- `parseFloat`/`parseInt` accept garbage prefixes (`parseInt('12px')` → 12). Prefer `Number(str)` + `Number.isFinite` check, or zod `z.coerce.number()`. Always pass radix if you do use `parseInt(s, 10)`.
- **Non-finite input slips past range checks.** `Number('Infinity')`, `parseFloat('Infinity…')` and `JSON.parse('1e400')` all give `Infinity`; `Number('')` and `Number(' ')` give `0`; anything else unparseable gives `NaN`. Every comparison with `NaN` is false, so `if (n < min || n > max) reject()` lets `NaN` through, and a lower-bound-only check lets `Infinity` through. Test `Number.isFinite(n)` (and `Number.isSafeInteger(n)` for counts, IDs and cents) *before* the range check, and reject blank strings explicitly. zod 4 `z.number()` rejects `NaN` and `±Infinity`; zod 3 `z.number()` and `z.coerce.number()` accept `Infinity`/`"Infinity"` unless `.finite()` is chained.
- **Division by zero never throws for `number`.** `x / 0` is `±Infinity`, `0 / 0` and `x % 0` are `NaN`, and both propagate into totals, `toFixed()` (`"Infinity"`, `"NaN"`) and storage. Guard the divisor (`if (d === 0)`) and decide the business answer (zero, error, "n/a") at that line. `BigInt` is the opposite: `1n / 0n` throws `RangeError`.
- **Overflow is silent, never an exception.** Integers past `2**53` lose precision; results past `Number.MAX_VALUE` become `Infinity`. For multi-term intermediates (`qty * unitCents * rateBps`) assert `Number.isSafeInteger` on the result, or compute in `BigInt`. The 32-bit zones wrap: `| 0`, `>>`, `Math.imul` and `Int32Array` turn `(-2147483648 / -1) | 0` and `-(-2147483648 | 0) | 0` back into `-2147483648` — keep bitwise tricks away from quantities and money. `BigInt` does not overflow, but `BigInt.asIntN(64, x)` / `asUintN` wrap without warning (e.g. when mirroring an int64 column): bound `x` before calling them.
- **Unit conversions overflow first.** Seconds to nanoseconds as a `number` leaves the safe-integer range after about 104 days (`1e7 * 1e9` is not a safe integer): use `process.hrtime.bigint()` or `BigInt(s) * 1_000_000_000n`, or stay in milliseconds. Timer delays above `2**31 - 1` ms are not honoured — Node emits `TimeoutOverflowWarning` and fires after 1 ms — so clamp a computed `setTimeout` delay. (OWASP: Go Secure Coding Practices, general coding practices; OWASP SCSVS, arithmetic.)

## Functions and modules over classes; classes where they earn it

Default unit of design: pure functions + plain data (typed objects), composed in modules. Classes earn their place for: stateful long-lived things with invariants (connection pools, caches), Error subclasses, when a framework expects them. Avoid:

- Classes as namespaces (all-static members) — use a module.
- Single-implementation interfaces + DI-container ceremony in app code — pass dependencies as function/constructor parameters directly; introduce the interface when the second implementation (or the test fake) actually exists.
- Inheritance for code reuse — compose; `extends` only for genuine is-a with stable base (Error, framework bases). Deep hierarchies in JS are refactor glue traps.
- Getters with side effects or surprise allocation; getters that throw.

```ts
// BAD — class-as-namespace + hidden temporal coupling
class UserService { static db: Db; static async get(id: string) { return this.db.find(id); } }

// GOOD — explicit deps, trivially testable
export const makeUserService = (db: Db) => ({
  get: (id: UserId) => db.find(id),
  // ...
});
export type UserService = ReturnType<typeof makeUserService>;
```

Module hygiene: no side effects at import time (registrations, connections, reading env) outside the composition root — importing a module should be safe and free. Side-effectful imports break tree-shaking, tests, and tooling.

## Designing a public surface — what consumers can reach, and what you can change

The shared design rules live in `sota-architecture` rules/02 and `sota-api-design`. **This is
the JS/TS mechanism**, where the surface has two halves that break independently: what is
*reachable at runtime*, and what is *expressible in the types*. A change can be invisible in
one and breaking in the other.

**`"exports"` is an encapsulation boundary, not a convenience.** A subpath not listed cannot
be imported at all — measured on Node 22.22.1: the package entry resolved, and
`require('pkg/lib/internal.js')` failed with **`ERR_PACKAGE_PATH_NOT_EXPORTED`**. Two
consequences:

- **Adding `"exports"` to a package that never had it is itself a breaking change.** Every
  deep import your consumers relied on stops resolving, and they were not "wrong" to use one —
  nothing stopped them. Ship it on a major.
- Without it, **every file is public API**. A refactor that moves `lib/internal.js` breaks
  someone, and you will not find out from your own tests.
- Put `"types"` **first** in each conditions object: conditions match in declaration order,
  so a `"types"` entry after `"import"`/`"require"` is unreachable for a TypeScript consumer.

**Named exports over `default`.** A default export has no canonical name, so consumers spell
it differently, rename-refactoring does not follow it, and a typo produces a *new* binding
rather than an error. Named exports also let a consumer's bundler drop what it does not use.

**Type-level breaking changes.** These are the ones that compile fine for you and fail in a
consumer's build, and the direction is the opposite for arguments and returns:

| change | safe? | why |
|---|---|---|
| widen a **parameter** type (`string` → `string \| number`) | **safe** | callers passing the old type still satisfy it |
| narrow a **parameter** type | **breaking** | existing call sites stop type-checking |
| widen a **return** type | **breaking** | consumers relying on the narrower type break |
| narrow a **return** type | safe | every consumer still gets what it expected |
| add an **optional** property to a returned object | safe | consumers ignore it |
| add a **required** property to an object you *accept* | **breaking** | every caller must now supply it |
| add a member to a **union you accept** | safe | you handle more |
| add a member to a **union you return** | **breaking** | consumer `switch`es lose exhaustiveness |

**`readonly` and `as const` are promises too.** Removing `readonly` from a returned type is
safe; adding it is breaking for any consumer that mutated. Exporting a mutable array or object
literal hands consumers a shared mutable singleton — freeze it or return a copy.

## Strings and Unicode

- `str.length` counts UTF-16 code units, not characters: `'👨‍👩‍👧'.length === 8`. Iterate by code point (`[...str]`, `for...of`) for character-ish ops; grapheme-correct counting/truncation needs `Intl.Segmenter`:

```ts
const seg = new Intl.Segmenter('en', { granularity: 'grapheme' });
const truncate = (s: string, n: number) => [...seg.segment(s)].slice(0, n).map(x => x.segment).join('');
```

- Normalize before comparing user-entered text: `a.normalize('NFC') === b.normalize('NFC')` ('é' has two encodings).
- Locale-aware comparison/sorting: `Intl.Collator`/`localeCompare`, never `<` on strings for human-facing sort. All formatting (numbers, dates, lists, plurals) via `Intl.*` — never hand-rolled `${day}/${month}` strings.
- `replaceAll` over `replace(/g/)` for literal replacement (no regex-escaping bugs). When building a RegExp from user input is unavoidable, escape it (`RegExp.escape` (ES2025) or the well-known escape helper) — see rules/05 ReDoS.
- Multi-line template literals respect indentation — use `dedent` or keep them flush-left; don't ship accidental leading whitespace in SQL/emails.

## Audit checklist

- [ ] **Public surface** (§"Designing a public surface"): `grep -n '"exports"' package.json` —
      absent means **every file is importable** and a refactor breaks consumers silently;
      present means adding it later was (or will be) a major. Where present, check `"types"` is
      the **first** key in each conditions object — conditions match in declaration order, so a
      later `"types"` is unreachable for a TS consumer.
- [ ] **Spread-accumulator `reduce` — accidental O(n²)**:
      `grep -rnE 'reduce\([[:space:]]*(async[[:space:]]+)?\(?[[:space:]]*[A-Za-z_$][A-Za-z0-9_$]*[^=]*=>[[:space:]]*\(?[[:space:]]*[{[][[:space:]]*\.\.\.' src/`
      — each step copies the whole accumulator. Measured on Node 22.22.1: 40,000 items took
      3,735 ms against 2.9 ms for a mutated accumulator. MEDIUM when the input is unbounded or
      user-sized, LOW on a fixed small list. A multi-line callback needs reading.
- [ ] `grep -rn "export default" src/` — a default export has no canonical name: consumers
      spell it differently and rename-refactoring does not follow it. Prefer named (LOW).
- [ ] **Type-level BC** on a published package: in the diff, did any exported signature
      *narrow a parameter*, *widen a return*, add a **required** property to an accepted
      object, or add a member to a **returned** union? Each compiles for you and breaks a
      consumer's build. `git diff <last-tag>..HEAD -- '**/*.d.ts' 'src/**/*.ts' | grep '^[+-].*export'`
- [ ] `grep -rnE 'export (const|let) [A-Za-z]+ *= *(\\[|\\{)' src/` — an exported mutable array
      or object literal is a shared singleton every consumer can mutate (MEDIUM).

- [ ] In-band sentinels: `grep -rnE 'return -1' --include='*.ts' --include='*.js' src/` — a
      `-1` that is **stored or passed** rather than tested on the next line. Remember `??`
      does not rescue it (`-1 ?? x` is `-1`); only `null`/`undefined` trigger it.

- [ ] `grep -rn "[^=!]==[^=]\|!=[^=]" --include="*.ts" src/` — loose equality (MEDIUM; eqeqeq lint).
- [ ] `grep -rn "|| 0\||| ''\||| \[\]\||| {}" src/` and `\b(port|count|index|limit|offset|retries)\s*=.*||` — `||` where `??` is meant (MEDIUM, HIGH if money/ports).
- [ ] `grep -rn "forEach(async" src/` — fire-and-forget async iteration (HIGH).
- [ ] `grep -rn "\.sort(\|\.reverse(\|\.splice(" src/` — verify each operates on a locally-owned array, else `toSorted`/`toReversed`/`toSpliced` (MEDIUM).
- [ ] `grep -rn "JSON.parse(JSON.stringify" src/` — replace with `structuredClone` (LOW/MEDIUM).
- [ ] `grep -rn "throw ['\"\`]\|throw {" src/` — thrown non-Errors (HIGH).
- [ ] `grep -rn "catch ([a-z]*)\s*{\s*}" src/` and `catch.*{\s*$` followed by `}` — swallowed errors (HIGH).
- [ ] `grep -rn "new Error(.*+\|new Error(\`" src/` — wrapping without `{ cause }` (LOW).
- [ ] `grep -rn "hasOwnProperty" src/` — use `Object.hasOwn` (LOW).
- [ ] `grep -rn "price\|amount\|total\|balance" --include="*.ts" src/ | grep -i "float\|\* 0\.\|/ 100\|toFixed"` — float money math (HIGH).
- [ ] `grep -rnE 'parseFloat\(|parseInt\(|(^|[^A-Za-z_])Number\((req|ctx|input|body|query|params|process\.env)[.[]|z\.coerce\.number\(\)|\* *(1e6|1e9|1_000_000|1_000_000_000)([^0-9_n]|$)' --include='*.ts' --include='*.js' src/ | grep -vE 'Number\.isFinite|Number\.isSafeInteger|\.finite\(\)'` — numeric input parsed without a non-finite check (`NaN` passes `x < min || x > max`, `Infinity` passes a lower bound), or a `number` time-unit conversion that overflows past 2^53; also review each `/` and `%` on a request-derived divisor for divide-by-zero (HIGH if money/limits, else MEDIUM).
- [ ] `grep -rn "from 'moment'\|require('moment')" src/` — dead library; migrate (MEDIUM). `new Date(` arithmetic with `86400000`/`3600000` constants — DST bugs (MEDIUM).
- [ ] `grep -rn "!" --include="*.tsx" -l src/` then targeted `grep -rn "\w!\.\|\w!;" src/` — non-null assertions; each needs justification (MEDIUM in app code).
- [ ] ESLint: `eqeqeq`, `prefer-const`, `no-param-reassign`, `@typescript-eslint/no-floating-promises`, `no-non-null-assertion` configured.
