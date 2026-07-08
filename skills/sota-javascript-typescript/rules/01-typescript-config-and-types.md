# TypeScript Configuration & Type Craft

## tsconfig: strict everything, no exceptions

New projects start from this baseline. Existing projects migrate flag-by-flag; never ship with `strict: false`.

```jsonc
{
  "compilerOptions": {
    // Strictness — all non-negotiable
    "strict": true,
    "noUncheckedIndexedAccess": true,      // arr[i] is T | undefined — catches the #1 runtime crash class
    "exactOptionalPropertyTypes": true,     // { x?: T } ≠ { x: T | undefined }
    "noImplicitOverride": true,
    "noFallthroughCasesInSwitch": true,
    "noPropertyAccessFromIndexSignature": true,
    "useUnknownInCatchVariables": true,     // implied by strict, listed for visibility

    // Module hygiene — ESM-first
    "module": "NodeNext",                   // or "ESNext" + "moduleResolution": "Bundler" for bundled apps
    "moduleResolution": "NodeNext",
    "verbatimModuleSyntax": true,           // forces `import type`; makes transpile-only tools (esbuild, swc) safe
    "isolatedModules": true,

    // Output / interop
    "target": "ES2024",
    "lib": ["ES2024"],                      // add "DOM", "DOM.Iterable" only for browser code
    "esModuleInterop": true,
    "skipLibCheck": true,                   // pragmatic: don't pay for broken third-party d.ts
    "forceConsistentCasingInFileNames": true,
    "declaration": true,                    // libraries only
    "sourceMap": true
  }
}
```

Rationale for the two flags most teams skip:
- `noUncheckedIndexedAccess`: without it, `users[0].name` compiles and crashes on empty arrays. With it, you're forced to narrow: `const u = users[0]; if (!u) return;`. Use `.at(0)` which is honest (`T | undefined`) even without the flag.
- `exactOptionalPropertyTypes`: distinguishes "absent" from "explicitly undefined". Critical for `JSON.stringify`, spread-merging config, and exactness of API payloads. Fix violations by deleting keys, not assigning `undefined`.

`verbatimModuleSyntax` replaces deprecated `importsNotUsedAsValues`/`preserveValueImports`. It makes every file independently transpilable — required for esbuild/swc/Bun, and it documents intent: types via `import type`, values via `import`.

TypeScript 6.0 (March 2026) is the last release on the JavaScript codebase; TypeScript 7.0 (the Go-native compiler, 8–12× faster builds, stable since July 2026) now ships as the regular `typescript` package. 6.0 flips defaults to `strict: true`, `module: "esnext"`, `target: "es2025"` and deprecates `baseUrl`, `moduleResolution: "node"`/`"classic"`, `outFile`, `target: "es5"`, and the non-strict interop flags — 7.0 makes them hard errors. The explicit config above stays valid under 6.0/7.0; migrate via 6.0 (treat its deprecation warnings as must-fix), then mind 7.0's changed defaults: `types` defaults to `[]` (list needed `@types` explicitly) and `rootDir` defaults to `./` (set it when tsconfig sits above `src`). Frameworks embedding the compiler API via Volar (Vue, Angular, Astro, Svelte, MDX) stay on 6.0 until 7.x exposes a stable programmatic API.

## No `any`. Use `unknown` + narrowing

`any` disables the compiler transitively — it infects everything it touches. `unknown` is the type-safe top type: you must narrow before use.

```ts
// BAD — any leaks; typo compiles, crashes at runtime
function handle(e: any) { console.log(e.mesage); }

// GOOD — unknown forces narrowing
function handle(e: unknown) {
  if (e instanceof Error) console.log(e.message);
  else console.log(String(e));
}
```

- Catch clauses are `unknown` under strict mode. Never `catch (e: any)`.
- `as any` in tests is still a bug factory; prefer typed builders/factories or `satisfies`.
- Escape hatch hierarchy (best→worst): proper type > generic > `unknown` + guard > `as T` with a comment why > `// @ts-expect-error` with reason > `any` (forbidden; lint it: `@typescript-eslint/no-explicit-any: error`).
- `@ts-expect-error` over `@ts-ignore` always — it errors when the suppression becomes stale.

Narrowing toolkit: `typeof`, `instanceof`, `in`, `Array.isArray`, discriminant property checks, user-defined guards (`x is T`), assertion functions (`asserts x is T`). Prefer discriminant checks over custom guards — guards are unchecked promises; a wrong guard body is a silent `as`.

## Discriminated unions are the workhorse

Model states as a closed union with a literal discriminant. This makes illegal states unrepresentable and gives exhaustive switches for free.

```ts
// BAD — boolean soup; 4 fields allow 16 shapes, ~3 are valid
interface State { loading: boolean; data?: User[]; error?: Error; }

// GOOD — exactly the valid states exist
type State =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: User[] }
  | { status: 'error'; error: Error };

function render(s: State) {
  switch (s.status) {
    case 'idle': return null;
    case 'loading': return spinner();
    case 'success': return list(s.data);   // data narrowed — no `!`
    case 'error': return alert(s.error);
    default: { const _exhaustive: never = s; throw new Error('unreachable'); }
  }
}
```

The `never` default makes adding a variant a compile error at every consumer — this is the whole point. Also enable `@typescript-eslint/switch-exhaustiveness-check`.

Use unions for: API responses (success/error), form states, events (`{ type: 'click', ... } | { type: 'keydown', ... }`), Result types. If you find yourself writing `field?: T` pairs that are "both or neither", that's a union begging to exist.

## Branded types for IDs and units

Structural typing means `UserId` and `OrderId` as plain `string` are interchangeable — a swapped argument compiles. Brand them:

```ts
declare const brand: unique symbol;
type Brand<T, B extends string> = T & { readonly [brand]: B };

type UserId = Brand<string, 'UserId'>;
type OrderId = Brand<string, 'OrderId'>;
type Cents = Brand<number, 'Cents'>;

const UserId = (s: string): UserId => s as UserId;  // single blessed constructor

function getOrders(userId: UserId): Order[] { /* ... */ }
getOrders(orderId);            // compile error — the bug class is dead
```

Brand at the validation boundary (zod: `z.string().uuid().brand<'UserId'>()`). Brand money, durations (ms vs s), and anything where unit confusion has bitten anyone ever. Zero runtime cost.

## `satisfies` and `as const`

`satisfies` validates against a type while preserving the narrower inferred type. `: Type` annotation widens; `as Type` lies.

```ts
// BAD — annotation widens; config.port is string | number
const config: Record<string, string | number> = { port: 3000, host: 'localhost' };

// GOOD — checked AND port stays number
const config = { port: 3000, host: 'localhost' } satisfies Record<string, string | number>;

// as const for literal preservation + readonly
const ROUTES = ['/home', '/about', '/admin'] as const;
type Route = (typeof ROUTES)[number];   // '/home' | '/about' | '/admin'
```

Pattern: derive types from values (`as const` + `typeof` + indexed access), not values from types. One source of truth.

`as` casts: legitimate only at (1) trusted boundaries already validated at runtime, (2) `as const`, (3) widening `as unknown as T` quarantined in one adapter file with a comment. `as` in business logic is a finding.

## Validate at the boundary, trust the types inside

TypeScript types are erased — they verify nothing at runtime. Every untrusted input (HTTP body, query params, env vars, JSON.parse, localStorage, webhooks, LLM output, DB rows from untyped clients) must be parsed, not cast.

```ts
import { z } from 'zod';

const CreateUser = z.object({
  email: z.string().email(),
  age: z.number().int().min(0).max(150),
  role: z.enum(['user', 'admin']).default('user'),
});
type CreateUser = z.infer<typeof CreateUser>;   // type derived from schema — one source of truth

// BAD — a lie with extra steps
const user = (await req.json()) as CreateUser;

// GOOD — parse, don't validate-and-cast
const result = CreateUser.safeParse(await req.json());
if (!result.success) return badRequest(result.error.flatten());
const user = result.data;   // genuinely CreateUser from here on
```

- zod v4 / valibot (smaller bundles, tree-shakeable — prefer for frontend) / ArkType are all fine; pick one per repo.
- Parse env once at startup into a typed, frozen config object; crash fast on missing vars (see rules/04).
- Inside the boundary, do NOT re-validate everywhere — that's noise. Types carry the proof.
- `JSON.parse` returns `any`. Wrap it: `const parseJson = (s: string): unknown => JSON.parse(s);`

## Utility types: use the built-ins, derive don't duplicate

`Partial`, `Required`, `Readonly`, `Pick`, `Omit`, `Record`, `Exclude`, `Extract`, `NonNullable`, `Parameters`, `ReturnType`, `Awaited`. Derive variants from one canonical type:

```ts
interface User { id: UserId; email: string; createdAt: Date; passwordHash: string; }
type PublicUser = Omit<User, 'passwordHash'>;
type UserPatch = Partial<Pick<User, 'email'>>;
```

Caveats:
- `Omit` doesn't distribute over unions. Use a distributive helper when omitting from a union: `type DistributiveOmit<T, K extends PropertyKey> = T extends unknown ? Omit<T, K> : never;`
- Prefer `Readonly<T>`/`readonly T[]` on function parameters you don't mutate — it documents and enforces.
- `ReturnType<typeof fn>` couples consumers to implementation; fine internally, avoid in public API.

## Enums: don't. Use unions or const objects

`enum` is non-erasable syntax (generates runtime code, breaks single-file transpilers — TS 5.8's `erasableSyntaxOnly` flag bans it outright), numeric enums are unsound (any number assigns), and const enums break under isolatedModules.

```ts
// BAD
enum Role { User, Admin }                 // Role.User === 0; role = 42 compiles

// GOOD — string literal union (zero runtime, narrows perfectly)
type Role = 'user' | 'admin';

// GOOD — const object when you need runtime iteration/values
const Role = { User: 'user', Admin: 'admin' } as const;
type Role = (typeof Role)[keyof typeof Role];
Object.values(Role);                      // runtime list for zod enums, dropdowns
```

Same reasoning bans `namespace` and parameter properties in new code: prefer plain modules and explicit field assignment. Enable `erasableSyntaxOnly` where the toolchain is TS ≥5.8 — it guarantees the whole codebase is type-strippable (Node's native TS execution, esbuild, swc all benefit).

## Functions: generics, overloads, and shape

- Generic only when a type relationship must be preserved (`function first<T>(xs: readonly T[]): T | undefined`). A type parameter used once in the signature is usually noise — take `unknown` or the concrete type.
- Constrain at the parameter (`<T extends HasId>`), return the narrow type; avoid `extends object` (allows arrays/functions — usually you mean `Record<string, unknown>`).
- Prefer union parameters over overloads; overloads only when return type depends on argument type in ways unions can't express. Overload implementations are unchecked against each signature — keep them trivial.
- Options-object for ≥3 params or any boolean (`createUser(email, { sendWelcome: true })` — call sites self-document; booleans positionally are unreadable).
- Return types: annotate exported/public functions explicitly (inference drift across refactors changes your API silently; `explicit-module-boundary-types` lint); let locals infer.
- Template literal types shine for constrained string APIs: `type EventName = \`on${Capitalize<string>}\`;`, route params extraction, CSS unit types — stop before you've written a parser in the type system (see next section).

## When type gymnastics hurt

Types serve the code. Stop when:
- A conditional/mapped type takes longer to understand than the duplication it removes. Two similar interfaces are often cheaper than one clever generic.
- Inference errors surface 5 layers from the cause. Recursive conditional types produce unreadable diagnostics for teammates.
- Compile time degrades (run `tsc --extendedDiagnostics`; deep template-literal and recursive types are the usual culprits).
- You're encoding business rules better checked at runtime (e.g., "max 10 items" belongs in zod, not in a tuple-length type).

Heuristics: max ~2 levels of nested conditional types in app code; name intermediate types; if a type needs a comment explaining how it works (not what it means), simplify it. Libraries can spend more complexity than apps — their users see only the inferred results.

## ESM-first and monorepo project references

- New code is ESM: `"type": "module"` in package.json, `import`/`export` only. No `require`, no `module.exports`. CJS interop via default-import of CJS packages works under `esModuleInterop`.
- `module: "NodeNext"` requires explicit `.js` extensions on relative imports in Node libraries (`import { x } from './util.js'`). Bundled apps using `moduleResolution: "Bundler"` may omit them.
- Library `package.json`: use `exports` map with `types` condition first; ship `.d.ts` next to `.js`. Verify with `publint` and `arethetypeswrong` (see rules/07).

Monorepos: TypeScript project references give incremental, dependency-ordered builds:

```jsonc
// packages/api/tsconfig.json
{
  "extends": "../../tsconfig.base.json",
  "compilerOptions": { "composite": true, "outDir": "dist", "rootDir": "src" },
  "references": [{ "path": "../shared" }]
}
```

- Root: `tsc -b` (build mode). Each package: `composite: true` + `declaration: true`.
- Import via workspace package names (`@app/shared`), never `../../shared/src/...` cross-package relative paths.
- Pair with pnpm workspaces + turborepo/nx for task caching. Set `declarationMap: true` so go-to-definition lands in source, not d.ts.

## Audit checklist

- [ ] `tsconfig.json`: `strict: true` present; `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, `verbatimModuleSyntax`, `isolatedModules` enabled. Any of these missing in a 2026 codebase is a finding (HIGH for missing `strict`).
- [ ] `grep -rn ": any\|as any\|<any>\|any\[\]" --include="*.ts" --include="*.tsx" src/` — every hit needs justification; `as any` in production code is HIGH.
- [ ] `grep -rn "@ts-ignore\|@ts-nocheck" src/` — should be `@ts-expect-error` with a reason comment; `@ts-nocheck` is HIGH.
- [ ] `grep -rn "as [A-Z]" --include="*.ts" src/ | grep -v "as const\|as unknown"` — casts in business logic; check each masks no missing validation.
- [ ] `grep -rn "JSON.parse\|req.body\|req.query\|process.env" src/` — confirm each flows through a schema parse before typed use; raw `as T` on external data is HIGH.
- [ ] `grep -rn "loading: boolean" src/` plus adjacent optional `data`/`error` fields — boolean-soup state, recommend discriminated union (MEDIUM).
- [ ] IDs typed as bare `string` passed across ≥2 entity types — recommend branding (LOW/MEDIUM by blast radius).
- [ ] ESLint has `typescript-eslint` strict-type-checked config; `no-explicit-any`, `switch-exhaustiveness-check`, `no-unsafe-*` rules enabled.
- [ ] Monorepo: cross-package relative imports (`grep -rn "from '\.\./\.\./.*/src/"`) — bypass project references (MEDIUM).
- [ ] `grep -rn "^export enum\|^enum \|const enum" src/` — migrate to unions/const objects (LOW; const enum under isolatedModules is MEDIUM).
- [ ] Exported functions without explicit return types in library/public API (`explicit-module-boundary-types` lint) — LOW.
- [ ] Libraries: `exports` map present, `publint` + `attw` pass.
