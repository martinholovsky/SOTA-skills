# Testing & Tooling

## 1. Test runner: vitest (apps), node:test (deps-free libs)

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
- A property whose `fc.pre` or `.filter` rejects most inputs can pass having checked almost nothing: [`sota-testing` rules/06](../../sota-testing/rules/06-property-fuzzing-mutation.md) §6.6. fast-check's `maxSkipsPerRun` counts `fc.pre` rejections only, and a `.filter` that rejects every value hangs rather than failing. Mutation testing (StrykerJS, which fails CI only through `thresholds.break`): [`sota-testing` rules/06](../../sota-testing/rules/06-property-fuzzing-mutation.md) §6.3.
- **No proof tool is expected here.** No bounded model checker or refinement checker is in mainstream use for JavaScript or TypeScript. A parser or invariant that must hold for
  every input gets a property test and a fuzz target whose reach is gated (above): that is the
  bar, and a PR says "fuzzed and property-tested", not "verified". Proof rules live where a
  mature checker exists: [`sota-rust` rules/09](../../sota-rust/rules/09-formal-verification.md) and [`sota-c-cpp` rules/06](../../sota-c-cpp/rules/06-build-tooling-ci.md) §4a.
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

## 2. Testing-library: test behavior, not implementation

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

## 3. Network: MSW

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

## 4. E2E: Playwright

Unit/integration tests for logic breadth; a thin Playwright layer for critical user journeys (signup, checkout, the money paths) — not a port of every unit case.

- Web-first assertions auto-retry: `await expect(page.getByRole('button')).toBeEnabled()` — never `page.waitForTimeout` (flake generator, grep-able finding).
- Same locator philosophy as testing-library: `getByRole`/`getByLabel` over CSS/XPath.
- Isolate state: storageState fixture per auth role (login once via API, reuse); each test owns its data; no inter-test order dependence.
- `trace: 'on-first-retry'` for CI debugging; run against production builds; shard in CI.
- API-seed test data; don't drive setup through the UI.

## 5. ESLint flat config + typescript-eslint strict

Flat config (`eslint.config.js`) is the only supported format since ESLint 9; ESLint 10 (Feb 2026) removes the eslintrc system entirely, resolves config from each linted file's directory (multiple configs per run — monorepo-friendly), and requires Node ≥20.19. typescript-eslint v8 supports ESLint 9 and 10. Type-aware strict preset catches real bugs (floating promises, unsafe any-flow) that syntax-only linting can't.

**Typed lint does not run on TypeScript 7.0.** typescript-eslint v8's peer range is `typescript <6.1.0` and 7.0 has no compiler API: with `typescript@^7` the install fails `ERESOLVE`, and forced, `eslint` exits 2 (measured, typescript-eslint 8.70.1). Keep the `typescript` dependency on the 6.0 API with the `npm:@typescript/typescript6` alias and run `tsc` from 7.0 beside it — the `package.json` snippet is in [rules/01](01-typescript-config-and-types.md) §"tsconfig". Exit 2 in CI is a broken gate, not a lint failure.

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
    linterOptions: { reportUnusedDisableDirectives: 'error' },   // the default 'warn' exits 0
    languageOptions: { parserOptions: {
      projectService: { allowDefaultProject: ['eslint.config.js'] },   // `eslint .` lints this file too
      tsconfigRootDir: import.meta.dirname } },
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
  { // tests only, by path; the glob matches Vitest's default include
    files: ['**/*.{test,spec}.{ts,tsx,mts,cts,js,jsx,mjs,cjs}'],
    rules: { '@typescript-eslint/no-non-null-assertion': 'off',   // rules/02 bans `!` in app code
             '@typescript-eslint/no-unsafe-assignment': 'off' } },
);
```

- `projectService` (replaces `project: true` boilerplate) enables type-aware rules with good perf. A file outside every tsconfig, such as `eslint.config.js` itself, fails with "was not found by the project service" unless listed in `allowDefaultProject`.
- **Test code is exempted by path, in config.** CI lints tests with the same strict set. Where these rules allow a construct in tests only (`!`, which [rules/02](02-language-idioms.md) bans in app code), turn the rule off in a `files` block whose glob matches the runner's: Vitest's default include is `**/*.{test,spec}.?(c|m)[jt]s?(x)` (vitest 5.0.5), so a `**/*.test.ts` glob leaves `.spec.ts` and `.test.tsx` tests under the full set. A strict rule switched off for the whole repo because tests failed is a finding, and so are per-line disables piling up in tests. Check the config against its own CI line: measured with ESLint 10.13.0 and typescript-eslint 8.72.0, this file's earlier example failed its own `eslint .` on `eslint.config.js` (not in the project service), on `.spec.ts`/`.test.tsx` tests (outside the old `**/*.test.ts` glob), and on its type-test example (`no-unused-vars`, §"Type-level testing").
- Formatting belongs to Prettier (or Biome): no stylistic-format ESLint rules fighting the formatter. Biome is a fast single-tool alternative when its rule coverage suffices — but typescript-eslint's type-aware rules have no Biome equivalent yet; security-sensitive repos keep typescript-eslint.
- Security lint, both in flat-config form: `eslint-plugin-no-unsanitized` has two rules,
  `method` and `property`, for DOM sinks such as `innerHTML` and `insertAdjacentHTML`.
  `eslint-plugin-security`'s recommended set enables all 14 rules of its published release
  (enumerated from the npm package on 2026-09-24). **Its findings are review candidates,
  not verdicts.** Its own docs say `detect-object-injection` "flags any expression in the
  form of `object[expression]` no matter where it occurs". Neither plugin has a rule for
  these (checked against both rule lists): raw-output syntax inside `.ejs`/`.pug`/`.hbs`
  files (ESLint does not parse them), a missing GCM `authTagLength`, TLS verification
  opt-outs, or a missing `ssh2` `hostVerifier`. Those need the grep probes in [rules/04](04-node-backend.md) and
  [rules/05](05-security.md).
- Useful plugins: `eslint-plugin-regexp` (ReDoS), `eslint-plugin-react-hooks` (v7: the React-Compiler-powered rules ship in `configs.flat.recommended`; `recommended-latest` is the plugin's experimental channel), `eslint-plugin-jsx-a11y`, `eslint-plugin-import-x` (cycles: `import-x/no-cycle`).
- Downgrading errors to warnings "to get CI green" creates a permanent warning swamp — fix or explicitly disable per-line with a reason comment.
- **A suppression names its rule, gives a reason, and fails CI once it is stale.** General contract: [`sota-devsecops` rules/05](../../sota-devsecops/rules/05-analysis-gates.md) §5.1. Measured on
  ESLint 9.39.5 and 10.13.0: `reportUnusedDisableDirectives` defaults to `"warn"`, so a stale
  `eslint-disable` alone exits 0; only `--max-warnings 0` or `--report-unused-disable-directives`
  made it exit 1. Set it to `'error'` in `linterOptions` (above) so the gate does not live in a
  CLI flag. `@eslint-community/eslint-plugin-eslint-comments` adds `no-unlimited-disable` (a bare
  `/* eslint-disable */`), `require-description` (the `-- reason`) and `no-unused-disable`. A
  blanket disable also hides the *next* finding on its lines: measured, it made a later
  rule-specific disable report as unused. TypeScript comments: `ban-ts-comment` allows
  `@ts-expect-error` only with a description; the `strict*` presets set
  `minimumDescriptionLength: 10`, while the `recommended*` presets keep the rule's default 3
  (typescript-eslint 8.72.0), and TS2578 fails a stale `@ts-expect-error` ([rules/01](01-typescript-config-and-types.md)).
  Biome: `// biome-ignore lint/<group>/<rule>: <reason>` is an error without the reason, but
  `suppressions/unused` is a warning: `biome ci` exited 0 on a stale suppression and 1 with
  `--error-on-warnings` (Biome 2.6.3).

## 6. Formatting and pre-commit

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

## 7. Dead code: knip

Knip finds unused files, exports, types, and dependencies — the stuff `tsc` can't see because exported-but-never-imported is still "used" to the compiler.

```jsonc
// knip.json
{ "entry": ["src/index.ts", "src/cli.ts"], "project": ["src/**/*.ts"] }
```

- Run in CI (`knip --reporter compact`); triage with `--include dependencies` first (unused deps = supply-chain surface, [rules/05](05-security.md)), then files, then exports.
- Pairs with `tsc --noUnusedLocals --noUnusedParameters` (intra-file) — knip covers inter-file.
- Knip's output is a **candidate list, not a finding**: a package loaded dynamically (string `require`, plugin manifest, DI by convention) reads as unused, and a package whose symbol is referenced only on an unreachable branch reads as used. Prove each candidate by deleting it in a scratch copy and running the real build + suite — [`sota-devsecops` rules/10](../../sota-devsecops/rules/10-inert-dependencies.md).
- Unused exports kill tree-shaking analysis precision and mislead readers; deleting code is a feature.

## 8. Library publishing: publint + arethetypeswrong

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
- Dual ESM/CJS only if consumers demand it (tsdown/unbuild make it tolerable; tsup's README says it is no longer actively maintained and points to tsdown); otherwise ESM-only and say so in the README. On Node ≥ v20.19 / v22.12, `require(esm)` lets CJS consumers load an ESM-only package whose graph has no top-level `await` ([rules/04](04-node-backend.md) §"Native ESM in Node").

## 9. Type-level testing

Libraries and complex generics deserve type tests — types are API surface and they regress silently.

```ts
import { expectTypeOf } from 'vitest';
test('parse narrows to branded id', () => {
  expectTypeOf(parseUserId('x')).toEqualTypeOf<UserId>();
  const takesId = (id: UserId) => id;
  // @ts-expect-error — plain string must not be assignable
  takesId('raw');   // a call, not `const _: UserId = 'raw'`, which fails no-unused-vars
});
```

`vitest --typecheck` runs these; `@ts-expect-error` lines double as negative type assertions. For published libraries, snapshot the public API surface with `api-extractor` or `tsd` so breaking type changes show up in review.

## 10. CI gates (the minimum bar)

Order fast→slow, all blocking: `tsc --noEmit` → eslint → unit/integration (vitest, coverage thresholds) → knip → build → playwright smoke. Plus `npm audit`/osv-scan and lockfile-frozen install ([rules/05](05-security.md)). A repo where `tsc --noEmit` isn't in CI will accumulate `as any` until types are decorative.

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

`--max-warnings 0` keeps warnings from becoming wallpaper. Cache pnpm store, not node_modules. Pin action SHAs ([rules/05](05-security.md)).

## Audit checklist

- [ ] CI runs typecheck, lint, tests as blocking steps — `cat .github/workflows/*.yml | grep -E "tsc|eslint|vitest|test"`; missing typecheck gate = MEDIUM. `git grep -nE '(^|[^-[:alnum:]])eslint( |$)' -- '*.yml' '*.yaml' | grep -v -- '--max-warnings 0'` — a lint step without `--max-warnings 0` lets warnings pile up (LOW) (§10).
- [ ] ESLint config is flat + `strictTypeChecked` (type-aware): `grep -rn "strictTypeChecked\|projectService" eslint.config.*` — syntax-only linting in a TS repo = MEDIUM. `grep -rnE "['\"]warn['\"]" --include='eslint.config.*' --exclude-dir=node_modules .` — rules downgraded to `'warn'` to get CI green (MEDIUM) (§5).
- [ ] **Typed lint actually runs (§"ESLint flat config", the TypeScript 7.0 paragraph)** (§5) — `grep -nE '"typescript": *"[~^]?7|"typescript": *"npm:typescript@' package.json` next to `typescript-eslint` means no 6.0 API for the linter; run `npx eslint .` and read the exit code — 2 with "typescript-eslint does not support TS 7.0" is HIGH (every type-aware rule, `no-floating-promises` included, is off).
- [ ] `grep -rn "eslint-disable" src/ | grep -v -- "--"` — disables without reason comments (§5); count trend (LOW each, MEDIUM in volume).
- [ ] **Suppressions that never expire (§"ESLint flat config", the suppression bullet) (§5) — MEDIUM, HIGH for blanket disables in volume** —
      `grep -nE "reportUnusedDisableDirectives:[[:space:]]*['\"]?(error|2)" eslint.config.*` (no hit: a stale disable exits 0 unless every lint step carries `--max-warnings 0`)
      ; `grep -rnE 'eslint-disable(-next-line|-line)?[[:space:]]*(\*/[[:space:]]*)?$' --include='*.js' --include='*.jsx' --include='*.ts' --include='*.tsx' --include='*.mjs' --include='*.cjs' --exclude-dir=node_modules .`
      (a directive naming no rule hides every future finding on its lines) ;
      `grep -rnE 'biome[[:space:]]+(ci|check|lint)' .github/workflows/ | grep -v -- '--error-on-warnings'` (a stale `biome-ignore` passes).
- [ ] **Strict rules weakened for test code (§"ESLint flat config", the test-code bullet) (§5) — MEDIUM** —
      `grep -nE "'@typescript-eslint/[a-z-]+':[[:space:]]*['\"]?(off|0)" eslint.config.*` — a hit outside a block whose `files` glob names tests disables the rule for app code too.
      Then `npx eslint --print-config <file>` on one test file of each naming shape the repo uses (`.spec.ts`, `.test.tsx`, `tests/…`): a shape the exemption misses gets the full set, which breeds per-line disables in tests.
- [ ] `grep -rnE --include='*.test.tsx' 'querySelector|container\.' src/` and `getByTestId` density — implementation-coupled tests (§2) (LOW/MEDIUM).
- [ ] `grep -rn "fireEvent" src/` in component tests — should be `userEvent` (LOW). Arbitrary `setTimeout` sleeps instead of `findBy…`/`waitFor` in component tests are MEDIUM (§2).
- [ ] `grep -rn "waitForTimeout\|setTimeout" e2e/ tests/` — sleep-based waits = flake (MEDIUM). `grep -rnE "locator\( *['\"](\.|#|//|xpath=|css=)" --include='*.spec.ts' --include='*.test.ts' --include='*.e2e.ts' --exclude-dir=node_modules .` — CSS/XPath locators where `getByRole`/`getByLabel` would do (LOW) (§4).
- [ ] **Parsers and serializers with no property-based test (Practices: `fast-check`) (§1) — LOW,
      MEDIUM for a parser of untrusted input** —
      `grep -nE '"(fast-check|@fast-check/[a-z]+)"' package.json` (absent: no property test can
      exist) ; `grep -rlE 'export (async )?(function|const) (parse|decode|deserialize|serialize|encode)[A-Za-z]*' --include='*.ts' --include='*.js' src/`
      (each listed module with no `fc.assert(fc.property(` in its tests is a candidate)
- [ ] `grep -rn "vi.mock(\|jest.mock(" src/ | wc -l` high vs test count — module-mock-heavy suite; check MSW present for network (`grep -rn "msw" package.json`) (MEDIUM if fetch wrappers are mocked instead). (§3)
- [ ] MSW server with `onUnhandledRequest: 'error'`? (§3) Real network calls in unit tests (`grep -rnE --include='*.test.ts' 'localhost|https://' src/`; an unquoted `src/**/` searches one level in bash, [`sota-shell-scripting` rules/05](../../sota-shell-scripting/rules/05-constructs-and-cleanup.md) §5a) = MEDIUM (flaky + slow).
- [ ] Coverage thresholds configured and honest (§10) (no `**/index.ts` exclusion games) — absent = LOW; tests asserting nothing (`grep -rn "expect(" -L` on test files) = HIGH for the affected area.
- [ ] knip (or equivalent) in CI? Run `npx knip` during audit — large unused-dependency list = MEDIUM (supply-chain surface). Each candidate is a lead, not a finding, until deleting it in a scratch copy leaves the real build and suite green (§7).
- [ ] Libraries: `npx publint && npx @arethetypeswrong/cli --pack` clean (§8); `files` allowlist present — failures = HIGH for published packages.
- [ ] **Tarball contents unchecked (§8, the tarball bullet) — HIGH for a published package** —
      `grep -rL --include='package.json' --exclude-dir=node_modules '"files"' . ; find . -name .npmignore -not -path '*/node_modules/*'`
      — a publishable `package.json` (no `"private": true`) without `files`, or any `.npmignore`, ships whatever the
      ignore rules miss. Then check CI runs `npm pack --dry-run --json` against an expected file list (absent: MEDIUM).
- [ ] Snapshot test sprawl (§1): `grep -rln "toMatchSnapshot" src/ | wc -l` — high count = change-detector suite (LOW/MEDIUM).
- [ ] Test factories vs giant fixtures; fake timers restored (`restoreMocks: true` or explicit afterEach) — mock bleed causes order-dependent flake (MEDIUM). `grep -rnE '"(jest|ts-jest)"' --include='package.json' --exclude-dir=node_modules .` — a new project on jest (LOW). No `--sequence.shuffle` run in CI, and flaky tests left unquarantined, are LOW (§1).
- [ ] **Formatter and pre-commit hooks (§6) — LOW** — `git grep -nE 'prettier[^#]*--check|biome +(ci|format)' -- '*.yml' '*.yaml' 'package.json'` printing nothing means no formatter check gates CI. `git grep -nE 'tsc|vitest|jest|playwright' -- 'lefthook.yml' '.husky/*' '.lintstagedrc*'` — typecheck or tests in a pre-commit hook make it slow enough to be skipped with `--no-verify`; they belong in CI.
- [ ] **No type-level tests on a published library (§9) — LOW** — `grep -rlE 'expectTypeOf|expectType<|from .tsd.' --include='*.ts' --include='*.tsx' --exclude-dir=node_modules .` printing nothing in a package that exports complex generics means its types can regress silently: add `expectTypeOf` tests run by `vitest --typecheck`, or snapshot the public API with `api-extractor`/`tsd`.
