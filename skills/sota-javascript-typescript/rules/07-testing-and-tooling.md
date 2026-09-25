# Testing & Tooling

## Test runner: vitest (apps), node:test (deps-free libs)

Vitest (use the latest stable major; check vitest.dev): native ESM/TS, vite-config reuse, watch mode, `projects` for multi-config repos (the old `workspace` option was removed in v4), jest-compatible API. Version boundaries that change behaviour: Vitest 5.0 (September 2026) requires Node `^22.12.0 || ^24 || >=26` and turns `clearMocks` on by default (`restoreMocks` stays off, so keep it set). Vitest 4 stabilized Browser Mode (via `@vitest/browser-playwright` etc.) — real-browser component tests where jsdom fidelity isn't enough. Don't start new projects on jest (CJS-era transform pain). Pure libraries with zero build can use `node:test` and skip the dependency entirely.

```ts
// vitest.config.ts
import { defineConfig } from 'vitest/config';
export default defineConfig({
  test: {
    environment: 'node',                    // 'jsdom'/'happy-dom' only for component tests (use `projects` to split)
    coverage: { provider: 'v8', thresholds: { lines: 80, branches: 75 } },
    restoreMocks: true,                     // auto-restore between tests — prevents cross-test mock bleed
    setupFiles: ['./test/setup.ts'],
  },
});
```

Practices:
- Structure: Arrange-Act-Assert; one behavior per test; name as behavior (`'rejects expired tokens'`), not method names (`'test verifyToken'`).
- Specific matchers: `toEqual` for deep structural, `toBe` for identity/primitives, `toMatchObject` for partial, `expect(fn).rejects.toThrow(SpecificError)` for async errors. Never `expect(await fn().catch(e => e)).toBeDefined()`-style mush.
- Snapshot tests only for genuinely stable serialized output (CLI output, codegen); component snapshot sprawl is change-detector noise — assert specific things instead.
- Fake time explicitly: `vi.useFakeTimers()` + `vi.setSystemTime()`; restore in `afterEach`. Flaky time/`Date.now` math in tests is a bug factory.
- Test data via factories with overrides (`makeUser({ role: 'admin' })`), not 50-line fixture JSON copies.
- `it.each` for input/output tables; property-based testing (`fast-check`) for parsers/serializers/invariants.
- Mock module boundaries (`vi.mock`) sparingly — heavy module-mocking is a design smell; prefer injecting dependencies (function params, constructor args) so tests pass fakes naturally.

### Shape of the suite

Honeycomb, not pyramid, for typical web services: most value sits in integration-level tests (route handler → real validation → in-memory/testcontainer DB → response). Pure-unit-test what is genuinely algorithmic (parsers, pricing, reducers); E2E only the money paths. Signs of an inverted suite: hundreds of tests mocking every collaborator, green CI, production bugs in the seams.

```ts
// Integration over a real boundary — fastify.inject hits routing, schema, handler, serializer
const res = await app.inject({ method: 'POST', url: '/orders', payload: { sku: 'A1', qty: 2 } });
expect(res.statusCode).toBe(201);
expect(OrderSchema.parse(res.json())).toMatchObject({ sku: 'A1' });
```

- Database tests: testcontainers (real Postgres in Docker) over fragile mocks of the query builder; transaction-per-test rollback for speed.
- Determinism rules: no real network (MSW errors on it), no real time (fake timers), no shared mutable fixtures, no test-order dependence (`vitest --sequence.shuffle` in CI surfaces it).
- A flaky test is a P1 on the suite: quarantine immediately, fix or delete within days — tolerated flake trains the team to ignore red.

## Testing-library: test behavior, not implementation

Tests should survive refactors that don't change behavior. Query like a user, assert what the user sees.

```tsx
// BAD — implementation-coupled: breaks on rename/restructure, passes when a11y is broken
const { container } = render(<Login />);
fireEvent.click(container.querySelector('.submit-btn')!);
expect(setStateSpy).toHaveBeenCalledWith({ loading: true });

// GOOD — role-based queries + userEvent + visible outcome
const user = userEvent.setup();
render(<Login />);
await user.type(screen.getByLabelText(/email/i), 'a@b.co');
await user.click(screen.getByRole('button', { name: /sign in/i }));
expect(await screen.findByRole('alert')).toHaveTextContent(/invalid credentials/i);
```

- Query priority: `getByRole` > `getByLabelText` > `getByPlaceholderText` > `getByText` > `getByTestId` (last resort). Unreachable-by-role often means inaccessible markup — fix the component.
- `userEvent` over `fireEvent` (simulates real event sequences: focus, keydown, input).
- Async: `await screen.findBy...` / `waitFor` for assertions; never arbitrary `setTimeout` sleeps. Don't `waitFor` with side effects inside the callback.
- Don't assert internal state, spy on setState, or shallow-render. Don't test "renders without crashing" only.
- The same philosophy applies server-side: test handlers via HTTP (`fastify.inject`, supertest) against responses, not by spying on internals.

## Network: MSW

Mock at the network boundary, not the fetch wrapper — tests then exercise your real client code (serialization, error handling, retries).

```ts
// test/handlers.ts
import { http, HttpResponse } from 'msw';
export const handlers = [
  http.get('/api/users/:id', ({ params }) =>
    HttpResponse.json({ id: params.id, email: 'a@b.co' })),
];

// test/setup.ts
import { setupServer } from 'msw/node';
export const server = setupServer(...handlers);
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));   // fail on unmocked calls
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// per-test override for error paths
server.use(http.get('/api/users/:id', () => HttpResponse.json({}, { status: 500 })));
```

- `onUnhandledRequest: 'error'` — silent passthrough hides missing mocks and accidental real network in CI.
- Same handlers reusable in the browser (`setupWorker`) for Storybook/dev.
- Don't mock your own modules to avoid network (`vi.mock('./api')`) — that skips the very code most likely to be wrong.

## E2E: Playwright

Unit/integration tests for logic breadth; a thin Playwright layer for critical user journeys (signup, checkout, the money paths) — not a port of every unit case.

- Web-first assertions auto-retry: `await expect(page.getByRole('button')).toBeEnabled()` — never `page.waitForTimeout` (flake generator, grep-able finding).
- Same locator philosophy as testing-library: `getByRole`/`getByLabel` over CSS/XPath.
- Isolate state: storageState fixture per auth role (login once via API, reuse); each test owns its data; no inter-test order dependence.
- `trace: 'on-first-retry'` for CI debugging; run against production builds; shard in CI.
- API-seed test data; don't drive setup through the UI.

## ESLint flat config + typescript-eslint strict

Flat config (`eslint.config.js`) is the only supported format since ESLint 9; ESLint 10 (Feb 2026) removes the eslintrc system entirely, resolves config from each linted file's directory (multiple configs per run — monorepo-friendly), and requires Node ≥20.19. typescript-eslint v8 supports ESLint 9 and 10. Type-aware strict preset catches real bugs (floating promises, unsafe any-flow) that syntax-only linting can't.

**Typed lint does not run on TypeScript 7.0.** typescript-eslint v8's peer range is `typescript <6.1.0` and 7.0 has no compiler API: with `typescript@^7` the install fails `ERESOLVE`, and forced, `eslint` exits 2 (measured, typescript-eslint 8.70.1). Keep the `typescript` dependency on the 6.0 API with the `npm:@typescript/typescript6` alias and run `tsc` from 7.0 beside it — the `package.json` snippet is in rules/01 §"tsconfig". Exit 2 in CI is a broken gate, not a lint failure.

```js
// eslint.config.js
import eslint from '@eslint/js';
import { defineConfig } from 'eslint/config';   // tseslint.config() is deprecated in its favour
import tseslint from 'typescript-eslint';

export default defineConfig(
  eslint.configs.recommended,
  tseslint.configs.strictTypeChecked,        // not just "recommended"
  tseslint.configs.stylisticTypeChecked,
  {
    languageOptions: { parserOptions: { projectService: true, tsconfigRootDir: import.meta.dirname } },
    rules: {
      '@typescript-eslint/no-floating-promises': 'error',
      '@typescript-eslint/no-misused-promises': 'error',
      '@typescript-eslint/switch-exhaustiveness-check': 'error',
      '@typescript-eslint/consistent-type-imports': 'error',
      'eqeqeq': ['error', 'always'],
      'no-restricted-syntax': ['error',
        { selector: "CallExpression[callee.name='eval']", message: 'eval is banned' }],
    },
  },
  { files: ['**/*.test.ts'], rules: { '@typescript-eslint/no-unsafe-assignment': 'off' } },
);
```

- `projectService: true` (replaces `project: true` boilerplate) enables type-aware rules with good perf.
- Formatting belongs to Prettier (or Biome): no stylistic-format ESLint rules fighting the formatter. Biome is a fast single-tool alternative when its rule coverage suffices — but typescript-eslint's type-aware rules have no Biome equivalent yet; security-sensitive repos keep typescript-eslint.
- Security lint, both in flat-config form: `eslint-plugin-no-unsanitized` has two rules,
  `method` and `property`, for DOM sinks such as `innerHTML` and `insertAdjacentHTML`.
  `eslint-plugin-security`'s recommended set enables all 14 rules of its published release
  (enumerated from the npm package on 2026-09-24). **Its findings are review candidates,
  not verdicts.** Its own docs say `detect-object-injection` "flags any expression in the
  form of `object[expression]` no matter where it occurs". Neither plugin has a rule for
  these (checked against both rule lists): raw-output syntax inside `.ejs`/`.pug`/`.hbs`
  files (ESLint does not parse them), a missing GCM `authTagLength`, TLS verification
  opt-outs, or a missing `ssh2` `hostVerifier`. Those need the grep probes in rules/04 and
  rules/05.
- Useful plugins: `eslint-plugin-regexp` (ReDoS), `eslint-plugin-react-hooks` (v7: the React-Compiler-powered rules ship in `configs.flat.recommended`; `recommended-latest` is the plugin's experimental channel), `eslint-plugin-jsx-a11y`, `eslint-plugin-import-x` (cycles: `import-x/no-cycle`).
- Downgrading errors to warnings "to get CI green" creates a permanent warning swamp — fix or explicitly disable per-line with a reason comment.

## Formatting and pre-commit

- One formatter, zero debate: Prettier (default) or Biome format (faster, one tool with its linter). Config committed; editor format-on-save; CI checks `--check`. No ESLint formatting rules alongside (`eslint-config-prettier` if any legacy stylistic rules linger).
- Pre-commit via lefthook/husky + lint-staged: format + eslint --fix on staged files only. Keep hooks <5s — slow hooks get `--no-verify`'d into irrelevance; typecheck and tests belong in CI, not pre-commit.

```yaml
# lefthook.yml
pre-commit:
  parallel: true
  commands:
    lint: { glob: '*.{ts,tsx}', run: 'eslint --fix {staged_files} && git add {staged_files}' }
    format: { glob: '*.{ts,tsx,json,md}', run: 'prettier --write {staged_files} && git add {staged_files}' }
```

- TS build perf in CI: `tsc -b --incremental` with restored `.tsbuildinfo` cache; in monorepos, run typecheck per-package via turborepo/nx so only affected packages pay.

## Dead code: knip

Knip finds unused files, exports, types, and dependencies — the stuff `tsc` can't see because exported-but-never-imported is still "used" to the compiler.

```jsonc
// knip.json
{ "entry": ["src/index.ts", "src/cli.ts"], "project": ["src/**/*.ts"] }
```

- Run in CI (`knip --reporter compact`); triage with `--include dependencies` first (unused deps = supply-chain surface, rules/05), then files, then exports.
- Pairs with `tsc --noUnusedLocals --noUnusedParameters` (intra-file) — knip covers inter-file.
- Knip's output is a **candidate list, not a finding**: a package loaded dynamically (string `require`, plugin manifest, DI by convention) reads as unused, and a package whose symbol is referenced only on an unreachable branch reads as used. Prove each candidate by deleting it in a scratch copy and running the real build + suite — `sota-devsecops` rules/10.
- Unused exports kill tree-shaking analysis precision and mislead readers; deleting code is a feature.

## Library publishing: publint + arethetypeswrong

Broken `exports`/types maps are the top npm-library bug class (works in dev, breaks in consumers' bundlers or `NodeNext` resolution).

```jsonc
// package.json for an ESM-first library
{
  "type": "module",
  "exports": {
    ".": { "types": "./dist/index.d.ts", "import": "./dist/index.js" }
  },
  "files": ["dist"],
  "sideEffects": false
}
```

- `npx publint` — validates packaging (exports map, file presence, ESM/CJS field correctness).
- `npx @arethetypeswrong/cli --pack` — validates types resolve under every resolution mode (node16 ESM/CJS, bundler); catches "false ESM" and masquerading-CJS d.ts.
- Both run in CI before publish. `files` allowlist prevents leaking `.env`/configs into tarballs.
- **Look at the tarball before it ships.** `npm pack --dry-run --json` lists every file the
  publish would upload. Measured on npm 10.9.4 in a package with no `files` field: with no
  `.npmignore` it packed `id_rsa` (the `.gitignore` had excluded `.env`); adding an
  `.npmignore` that listed only `id_rsa` made npm stop reading `.gitignore`, and `.env` was
  packed. So use the `files` allowlist, not `.npmignore`. `files: ["dist"]` still shipped
  `dist/index.js.map`, and `"!dist/**/*.map"` removed it. In CI, diff the packed path list
  against a committed expected list and fail on any new path. *OWASP: NPM Security cheat sheet.*
- Dual ESM/CJS only if consumers demand it (tsdown/unbuild make it tolerable; tsup's README says it is no longer actively maintained and points to tsdown); otherwise ESM-only and say so in the README. On Node ≥ v20.19 / v22.12, `require(esm)` lets CJS consumers load an ESM-only package whose graph has no top-level `await` (rules/04 §"Native ESM in Node").

## Type-level testing

Libraries and complex generics deserve type tests — types are API surface and they regress silently.

```ts
import { expectTypeOf } from 'vitest';
test('parse narrows to branded id', () => {
  expectTypeOf(parseUserId('x')).toEqualTypeOf<UserId>();
  // @ts-expect-error — plain string must not be assignable
  const _: UserId = 'raw';
});
```

`vitest --typecheck` runs these; `@ts-expect-error` lines double as negative type assertions. For published libraries, snapshot the public API surface with `api-extractor` or `tsd` so breaking type changes show up in review.

## CI gates (the minimum bar)

Order fast→slow, all blocking: `tsc --noEmit` → eslint → unit/integration (vitest, coverage thresholds) → knip → build → playwright smoke. Plus `npm audit`/osv-scan and lockfile-frozen install (rules/05). A repo where `tsc --noEmit` isn't in CI will accumulate `as any` until types are decorative.

```yaml
# .github/workflows/ci.yml — minimal blocking pipeline
steps:
  - uses: actions/checkout@<pinned-sha>
  - uses: actions/setup-node@<pinned-sha>
    with: { node-version-file: '.nvmrc', cache: 'pnpm' }
  - run: pnpm install --frozen-lockfile
  - run: pnpm tsc --noEmit
  - run: pnpm eslint . --max-warnings 0
  - run: pnpm vitest run --coverage
  - run: pnpm knip
  - run: pnpm build
```

`--max-warnings 0` keeps warnings from becoming wallpaper. Cache pnpm store, not node_modules. Pin action SHAs (rules/05).

## Audit checklist

- [ ] CI runs typecheck, lint, tests as blocking steps — `cat .github/workflows/*.yml | grep -E "tsc|eslint|vitest|test"`; missing typecheck gate = MEDIUM.
- [ ] ESLint config is flat + `strictTypeChecked` (type-aware): `grep -rn "strictTypeChecked\|projectService" eslint.config.*` — syntax-only linting in a TS repo = MEDIUM.
- [ ] **Typed lint actually runs (§"ESLint flat config", the TypeScript 7.0 paragraph)** — `grep -nE '"typescript": *"[~^]?7|"typescript": *"npm:typescript@' package.json` next to `typescript-eslint` means no 6.0 API for the linter; run `npx eslint .` and read the exit code — 2 with "typescript-eslint does not support TS 7.0" is HIGH (every type-aware rule, `no-floating-promises` included, is off).
- [ ] `grep -rn "eslint-disable" src/ | grep -v -- "--"` — disables without reason comments; count trend (LOW each, MEDIUM in volume).
- [ ] `grep -rn "querySelector\|container\." src/**/*.test.tsx` and `getByTestId` density — implementation-coupled tests (LOW/MEDIUM).
- [ ] `grep -rn "fireEvent" src/` in component tests — should be `userEvent` (LOW).
- [ ] `grep -rn "waitForTimeout\|setTimeout" e2e/ tests/` — sleep-based waits = flake (MEDIUM).
- [ ] `grep -rn "vi.mock(\|jest.mock(" src/ | wc -l` high vs test count — module-mock-heavy suite; check MSW present for network (`grep -rn "msw" package.json`) (MEDIUM if fetch wrappers are mocked instead).
- [ ] MSW server with `onUnhandledRequest: 'error'`? Real network calls in unit tests (`grep -rn "localhost\|https://" src/**/*.test.ts`) = MEDIUM (flaky + slow).
- [ ] Coverage thresholds configured and honest (no `**/index.ts` exclusion games) — absent = LOW; tests asserting nothing (`grep -rn "expect(" -L` on test files) = HIGH for the affected area.
- [ ] knip (or equivalent) in CI? Run `npx knip` during audit — large unused-dependency list = MEDIUM (supply-chain surface).
- [ ] Libraries: `npx publint && npx @arethetypeswrong/cli --pack` clean; `files` allowlist present — failures = HIGH for published packages.
- [ ] **Tarball contents unchecked (§"Library publishing", the tarball bullet) — HIGH for a published package** —
      `grep -rL --include='package.json' --exclude-dir=node_modules '"files"' . ; find . -name .npmignore -not -path '*/node_modules/*'`
      — a publishable `package.json` (no `"private": true`) without `files`, or any `.npmignore`, ships whatever the
      ignore rules miss. Then check CI runs `npm pack --dry-run --json` against an expected file list (absent: MEDIUM).
- [ ] Snapshot test sprawl: `grep -rln "toMatchSnapshot" src/ | wc -l` — high count = change-detector suite (LOW/MEDIUM).
- [ ] Test factories vs giant fixtures; fake timers restored (`restoreMocks: true` or explicit afterEach) — mock bleed causes order-dependent flake (MEDIUM).
