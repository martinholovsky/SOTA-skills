<!-- last-verified: 2026-07 -->

# 02 — React 19: components, hooks, Actions, memoization

Scope: React itself (any renderer). Next-specific RSC/Server-Action mechanics are in
`rules/03`; hydration in `rules/06`. TypeScript-with-React lives in
`sota-javascript-typescript`.

## 1. Component and hook fundamentals

- **Function components + hooks only.** Class components are legacy; no new ones.
- **Rules of Hooks are load-bearing, not style.** Call hooks unconditionally, at the
  top level, in the same order every render. Violations are real bugs *and* they
  break the React Compiler (which refuses to optimize non-conforming components).
  Enforce with `eslint-plugin-react-hooks`.
- **`useEffect` is for synchronizing with external systems**, not for deriving data.
  The react.dev guide "You Might Not Need an Effect" is the reference: compute derived
  values during render, adjust state during render (not in an effect), fetch via a
  framework loader or a data library — not a bare `useEffect(fetch)`, which races and
  double-runs. An effect that only sets state from props/state is a smell.
- **Every effect that subscribes must clean up** (return a teardown): listeners,
  timers, sockets, subscriptions. A missing cleanup leaks across Strict Mode's
  double-invoke and across remounts.
- **Stable IDs come from `useId`**, never `Math.random()` or a module counter — this
  is what keeps SSR and client markup matching (`rules/06`). For form-field `id`/
  `htmlFor` pairs and ARIA wiring.
- **Refs (`useRef`) are escape hatches**: DOM access and mutable non-render values.
  Don't read/write `ref.current` during render. Prefer state for anything that should
  trigger a re-render.

## 2. Suspense, transitions, and error boundaries

- **Suspense** declares loading UI for async children (lazy components, RSC/data that
  suspends). Pair every dynamic boundary with a fallback; in Next PPR, uncached data
  *must* sit inside a `<Suspense>` or the build fails (`rules/03`).
- **`useTransition` / `startTransition`** mark state updates as non-urgent so input
  stays responsive; `useDeferredValue` defers re-rendering expensive subtrees. Reach
  for these on measured jank, not preemptively.
- **Error boundaries are mandatory around risky subtrees** (lazy loads, third-party
  widgets, RSC islands). Hooks can't catch render errors — you still need a class
  boundary or `react-error-boundary`. Server-render errors and hydration errors
  surface here too. Don't render user-controlled error text as HTML.

## 3. The Actions model (React 19)

React 19 stabilized "Actions" — async functions wired into transitions with built-in
pending/error/optimistic state.

- **`useActionState(action, initial)`** — wraps an async action, returns
  `[state, formAction, isPending]`; drive a `<form action={formAction}>`. Replaces
  hand-rolled `isLoading`/`error` state around form submits.
- **`useOptimistic`** — show an optimistic value while the action is in flight,
  auto-reverting on failure.
- **`use(promise)` / `use(context)`** — unwrap a promise (suspends) or read context,
  and unlike other hooks `use` may be called conditionally. Feed it a *cached/stable*
  promise (from an RSC or a cache), never a promise created inline in render — that
  creates a new promise every render and never resolves.
- **`ref` is a regular prop** in React 19 (no more `forwardRef` for new code);
  `ref` cleanup callbacks are supported.
- These integrate with Next Server Actions (`rules/03`): `formAction` can be a
  `"use server"` function. The client-side pending/optimistic UX is React; the
  security of the action is server-side and covered in `rules/03`/`rules/07`.

## 4. Memoization and the React Compiler

- **Prefer the React Compiler over manual memoization.** Compiler 1.0 (stable,
  2025-10) auto-memoizes components and values, making most `useMemo`, `useCallback`,
  and `React.memo` unnecessary — *if* your code follows the Rules of Hooks and treats
  props/state as immutable. Don't rip out existing memoization blindly, but stop
  hand-writing new memo wrappers as a reflex.
- **Where you still memoize by hand** (no compiler, or a proven hot path): memoize the
  *expensive* computation or a referentially-stable callback passed to a memoized
  child. Memoizing a cheap value costs more than it saves. Measure (`sota-performance`).
- **Never mutate state or props.** Compiler correctness and React's rendering both
  assume immutability; mutation causes stale UI and defeats memoization. Use immutable
  updates (spread, `.map`, or a library).
- **Keys must be stable and unique** across siblings — never the array index for
  reorderable/insertable lists (causes state to attach to the wrong row and subtle
  data-corruption bugs). Use a domain ID.

## 5. React-specific XSS: the injection sinks

Generic XSS theory is in `sota-code-security` rules/05; here are the React sinks.

- **`dangerouslySetInnerHTML` is the one HTML-injection sink** JSX gives you (JSX
  text is auto-escaped). Only ever feed it sanitizer output (DOMPurify or a server
  sanitizer with an allowlist), never raw user/CMS HTML.

```jsx
// BAD — HIGH: stored/reflected XSS
<div dangerouslySetInnerHTML={{ __html: comment.body }} />

// GOOD — sanitize first (allowlist), or don't use HTML at all
import DOMPurify from 'dompurify';
<div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(comment.body) }} />
```

- **URL/`href` injection:** `<a href={userUrl}>` allows `javascript:` and `data:`
  schemes. Validate the scheme (`https?:`/relative) before rendering; the same applies
  to `src`, `formAction`, and `<img src>`.
- **Spreading unknown props** (`<div {...userControlledObject}>`) can inject
  `dangerouslySetInnerHTML` or event handlers — never spread attacker-influenced
  objects onto DOM elements.
- **Rendering into a portal / third-party DOM** you don't control inherits that DOM's
  trust; don't mount React onto server-rendered nodes that contain user HTML
  (mirrors the Vue rule in `rules/04`; hydration-XSS angle in `rules/06`).
- CSP is defense-in-depth, not a substitute (`rules/06`, `rules/07`).

## Audit checklist

```bash
# HTML injection sink — every hit needs a sanitizer on the source
grep -rn 'dangerouslySetInnerHTML' --include='*.tsx' --include='*.jsx' src app components

# javascript:/data: URL sinks
grep -rnE 'href=\{|src=\{|formAction=\{' --include='*.tsx' src app | grep -iv 'sanitiz'

# Effect smells: fetch-in-effect, setState-only effects, missing deps
grep -rnE 'useEffect\(' --include='*.tsx' src app | head
grep -rn 'Math.random()\|Date.now()' --include='*.tsx' src app   # in render => hydration bug (rules/06)

# Rules of Hooks / compiler-blocking violations rely on lint:
grep -rn 'react-hooks' .eslintrc* eslint.config.* package.json

# Legacy patterns
grep -rn 'forwardRef\|class .* extends .*Component' --include='*.tsx' src app   # forwardRef unneeded in 19
grep -rnE 'key=\{.*index' --include='*.tsx' src app   # index-as-key on dynamic lists
```

- [ ] Every `dangerouslySetInnerHTML` fed sanitizer output (allowlist), not raw user/CMS HTML?
- [ ] `href`/`src`/URL props validated against a scheme allowlist (no `javascript:`/`data:`)?
- [ ] No `Math.random()`/`Date.now()`/`window` used *during render* (hydration determinism)?
- [ ] Effects only for external synchronization, each with cleanup; no fetch-in-bare-effect racing?
- [ ] Stable domain IDs as list keys (not array index) for insertable/reorderable lists?
- [ ] Rules of Hooks enforced by lint (also required for the React Compiler)?
- [ ] Error boundaries around lazy/third-party/RSC subtrees; error text not rendered as HTML?
