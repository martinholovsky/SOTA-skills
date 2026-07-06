<!-- last-verified: 2026-07 -->

# 04 — Vue 3: Composition API, reactivity, XSS

Baseline: Vue 3.5.x. Nuxt-specific concerns (data fetching, `useState`, server routes)
are in `rules/05`; hydration in `rules/06`. TypeScript setup depth is in
`sota-javascript-typescript`.

## 1. Composition API + `<script setup>` is the default

- **For applications, use the Composition API with `<script setup>`** — Vue's own
  recommendation. Options API remains fully supported and is fine for progressive
  enhancement / no-build-step sprinkles, but new app code is Composition API.
- Don't mix paradigms within a component without reason; consistency aids the compiler
  and the reader.
- **Vue 3.6 (beta, not stable) adds Vapor mode** — an opt-in, per-SFC compilation
  (`<script setup vapor>`) that drops the virtual DOM for lower overhead. Do not
  depend on it in production until 3.6 ships stable; verify status before adopting.

## 2. Reactivity pitfalls (where real bugs live)

- **`ref` vs `reactive`:** prefer `ref` for primitives and as the default; `reactive`
  only for objects you won't reassign. **Destructuring a `reactive` object loses
  reactivity** — the extracted variable is a plain snapshot. Use `toRefs`/`toRef`, or
  just use `ref`.
- **Props destructuring:** since Vue 3.5 the compiler rewrites destructured props to
  keep them reactive (`const { count } = defineProps(...)`), including as the way to
  declare defaults with TypeScript. **Caveat:** passing a destructured prop *into*
  `watch()` or a composable passes a value, not a reactive source — wrap it in a
  getter `() => count` (or `toValue()` inside the composable). Below 3.5, destructuring
  loses reactivity entirely — use `props.count`.
- **`watch` vs `watchEffect`:** `watch` for explicit sources and precise control (old
  vs new value, lazy by default); `watchEffect` auto-tracks and runs immediately.
  Watching a property of a reactive object needs a getter: `watch(() => obj.id, …)`.
  Deep watches are expensive — Vue 3.5 supports a numeric `deep` depth limit; use
  `once: true` (3.4+) for one-shot.
- **Watcher/effect lifecycle:** watchers/computed created *synchronously* in `setup`
  auto-dispose on unmount. Ones created **asynchronously** (after an `await`, in a
  callback, in a timer) do **not** — they leak. Wrap detached reactive work in
  `effectScope()` and call `scope.stop()`, or use `onScopeDispose()` in composables.
- **`shallowRef`/`shallowReactive` for large structures** (big lists, external
  instances, non-reactive class objects): reactivity only at the root, so replace the
  root to trigger updates and treat nested data as immutable. `triggerRef` forces a
  refresh. This is the main Vue perf lever alongside `v-once`/`v-memo` and list
  virtualization (`sota-performance`).

## 3. Component API design

- **`defineModel()`** (Vue 3.4+) is the modern two-way binding — compiles to the
  `modelValue` prop + `update:modelValue` event, supports multiple/named models and
  modifiers. Prefer it over manually declaring the prop/emit pair.
- **Type-based `defineProps`/`defineEmits`** is the recommended TypeScript style
  (`defineProps<{ id: string; count?: number }>()`); you cannot mix the type-based and
  runtime-object forms in one call. Emits use the tuple/type syntax (3.3+).
- **Provide/inject** for cross-cutting dependencies; type the injection key
  (`InjectionKey<T>`). For SSR, remember provide/inject is per-app-instance — which is
  exactly how you avoid cross-request leakage (`rules/06`).
- **Composables** (`useX`) are Vue's unit of logic reuse — return refs/computed, accept
  getters or `MaybeRefOrGetter` + `toValue()` for flexible inputs, and clean up with
  `onScopeDispose`.

## 4. Vue-specific XSS and injection

Vue auto-escapes text interpolations and attribute bindings (including in SSR — the
core `escapeHtml` escapes `" ' & < >`). The sinks are where you leave that protection.
(General theory: `sota-code-security` rules/05.)

- **`v-html` bypasses escaping** — it sets `innerHTML`. User HTML through `v-html` is
  never safe unless sanitized (allowlist sanitizer) or shown only to its own author in
  a sandboxed context.

```vue
<!-- BAD — HIGH: XSS -->
<div v-html="comment.body" />
<!-- GOOD — sanitize first, or render as text -->
<div v-html="sanitize(comment.body)" />   <!-- DOMPurify / server allowlist sanitizer -->
<div>{{ comment.body }}</div>              <!-- best: no HTML at all -->
```

- **Never use untrusted content as a component `template`** — Vue's docs call this
  rule #1: a dynamic template is arbitrary JS execution. Don't build `template:` (or a
  runtime-compiled component) from user input.
- **Never mount Vue on DOM that contains server-rendered user content.** HTML that is
  safe *as HTML* can be unsafe *as a Vue template* (mustache/`v-` directives in the
  markup get compiled). Mount only on markup you control (hydration-XSS in `rules/06`).
- **URL injection:** `:href="userUrl"` / `:src` allow `javascript:` and `data:` —
  validate the scheme before binding (sanitize on the backend before storage, per
  Vue's guidance). **Style injection:** binding user data to `:style` enables
  clickjacking-style overlays — bind specific, typed properties, not a raw string.
  Never bind user content to event handlers (`@click="userValue"`).

## Audit checklist

```bash
# HTML-injection sink — each hit needs a sanitizer on the source
grep -rn 'v-html' --include='*.vue' src components pages

# Dynamic templates / runtime compilation from input (arbitrary JS)
grep -rnE 'template:\s*[^\x27"]*(\$|props|user|input)' --include='*.vue' --include='*.ts' src
grep -rn 'compile(' --include='*.ts' src

# URL / style / handler injection
grep -rnE ':href=|:src=|:style=' --include='*.vue' src | grep -iv 'sanitiz\|allow'

# Reactivity leak/loss patterns
grep -rnE 'const \{[^}]+\}\s*=\s*reactive\(' --include='*.vue' --include='*.ts' src  # destructuring reactive => lost reactivity
grep -rnE 'watch(Effect)?\(' --include='*.vue' src | head   # verify async-created ones are scoped
grep -rn 'ref(' --include='*.ts' src/composables 2>/dev/null # module-level refs? (rules/06 SSR leak)
```

- [ ] Every `v-html` fed sanitizer output, not raw user/CMS HTML (or rendered as text instead)?
- [ ] No component `template`/runtime-compiled component built from user input?
- [ ] Vue never mounted on DOM containing server-rendered user content?
- [ ] `:href`/`:src` scheme-validated (no `javascript:`/`data:`); `:style` bound as typed props, not raw strings?
- [ ] No reactivity lost by destructuring `reactive` (use `toRefs`/`ref`); destructured props not passed bare into `watch`/composables?
- [ ] Async-created watchers/effects scoped (`effectScope`/`onScopeDispose`) so they don't leak?
- [ ] `defineModel` for two-way binding; type-based `defineProps`; `shallowRef` for large structures?
