# 06 — Motion Design & Animation Engineering

Motion is functional communication: it orients (where did this come from), gives feedback (did that
work), and maintains continuity (these two views are the same object). If an animation does none of
those, delete it. Decoration-only motion is cost without information.

## 1. Purpose test — every animation must answer one

| Purpose | Examples |
|---|---|
| **Orientation** | Drawer slides from the edge it lives at; dialog scales from trigger; list item exits toward archive |
| **Feedback** | Button press depression; toggle thumb travel; invalid-field shake (≤ 2 cycles, small amplitude); success check draw |
| **Continuity** | Shared-element transitions (thumbnail → detail hero); reordering items glide, not teleport; tab indicator slides between tabs |
| **Status** | Skeleton shimmer, progress, pull-to-refresh resistance |

If the proposed animation is "the cards fade in one by one because it looks nice" on a *task* screen
the user visits 50×/day — cut it. Frequency inversely bounds acceptable motion: first-run flows may
celebrate; daily workflows must be near-instant.

## 2. Duration & easing: the numeric standards

**Duration:**

| Animation | Duration |
|---|---|
| Micro feedback (hover, press, toggle) | 100–150ms |
| Small component (tooltip, dropdown, fade) | 150–250ms |
| Standard enter (dialog, drawer, page section) | **200–300ms** |
| Exit / dismiss | **~60–80% of enter** (150–200ms) — leaving needs less ceremony |
| Large/full-screen transitions | 300–500ms (rarely more) |
| Attention loops (skeleton pulse) | 1–1.5s cycle |

Nothing interactive ever exceeds 500ms; > 700ms total reads as broken. Distance/size scales
duration slightly (small element 150ms, full-screen 350ms) — never linearly.

**Easing:**

- **Enter: ease-out** (fast start, gentle landing) — `cubic-bezier(0, 0, 0.2, 1)` or `cubic-bezier(0.16, 1, 0.3, 1)` (expo-out, snappier).
- **Exit: ease-in** or faster ease-out; users don't watch exits.
- **Move/morph on screen: ease-in-out** — `cubic-bezier(0.4, 0, 0.2, 1)` (the Material "standard").
- **Never `linear`** for entrances/exits (mechanical), never default CSS `ease` for anything deliberate (too lazy at the end). `linear()` *function* is fine — it's how you encode springs in CSS.
- Tokenize: `--ease-out`, `--ease-in-out`, `--duration-fast: 150ms`, `--duration-base: 250ms`. Grep-able, theme-able, and the reduced-motion override has one place to zero them.

**Springs** (Motion/React Spring/WAAPI `linear()`): for gestural and interruptible motion —
drag-release, sheet snapping, reorder. Springs are physics, not duration: tune `stiffness`
(~170–300), `damping` (~20–30); slight overshoot ≤ 2–3% for playful contexts, critically damped for
productivity UI. Springs handle mid-flight interruption gracefully — duration curves don't; if the
user can interrupt it, prefer a spring.

## 3. Choreography

- **Stagger** list/grid entrances 20–50ms apart, cap total ≤ 6–8 items or ~400ms overall (stagger item 30 by 50ms = 1.5s of waiting — animate the container instead, or only the items in viewport).
- One hero per transition: choreograph a primary element; secondary content fades simply. Everything-animates = nothing communicates.
- Enter and exit run together when swapping views (cross-fade + slight slide), exit slightly faster; incoming content may overlap the last 30–50% of the outgoing animation.
- Direction encodes meaning consistently: forward navigation slides left (in LTR), back slides right; up = expand/open, down = dismiss. Don't mix metaphors per screen — mirror for RTL.
- Origin matters: scale transitions grow from the trigger point (`transform-origin` set to trigger position), not from screen center — that's the orientation payload.

## 4. Technique selection: CSS vs WAAPI vs FLIP vs libraries

| Use | Tool |
|---|---|
| State transitions, hover/focus, enter via class swap | **CSS transitions/animations** — declarative, compositor-friendly, zero JS cost |
| Dynamic values, runtime control (pause/reverse/seek), sequences without a library | **WAAPI** (`element.animate()`) — runs off main thread for transform/opacity |
| Layout-change animation (reorder, size change, list add/remove) | **FLIP** (First-Last-Invert-Play) — measure, invert with transform, play; or View Transitions; or Motion `layout` prop which does FLIP for you |
| Page/view morphs, shared elements | **View Transitions API** (same-document; cross-document for MPA), `view-transition-name` per shared element; feature-detect, fall back to instant swap |
| Springs, gestures, interruption, exit-before-unmount, complex orchestration in React | **Motion (Framer Motion)** / React Spring — don't hand-roll gesture physics |
| Scroll-linked effects | CSS scroll-driven animations (`animation-timeline: scroll()/view()`) where supported; IntersectionObserver-triggered classes as the broad fallback. Never scroll-event listeners mutating style |

```css
/* GOOD: enter/exit with modern CSS only — including display:none transitions */
[popover] {
  opacity: 0; translate: 0 8px;
  transition: opacity 200ms var(--ease-out), translate 200ms var(--ease-out),
              display 200ms allow-discrete, overlay 200ms allow-discrete;
}
[popover]:popover-open { opacity: 1; translate: 0; @starting-style { opacity: 0; translate: 0 8px; } }
```

```js
// GOOD: FLIP for a list reorder (or use ViewTransition / Motion layout)
const first = el.getBoundingClientRect();
moveInDom(el);
const last = el.getBoundingClientRect();
el.animate(
  [{ transform: `translate(${first.x - last.x}px, ${first.y - last.y}px)` }, { transform: "none" }],
  { duration: 250, easing: "cubic-bezier(0.4, 0, 0.2, 1)" }
);
```

- `@starting-style` + `transition-behavior: allow-discrete` finally make CSS-only enter/exit from `display: none` real — prefer this over mount-animation JS for simple cases.
- View Transitions: name shared elements (`view-transition-name: product-image`), customize via `::view-transition-old/new(name)`; names must be unique per snapshot; long-lived names on huge lists cost memory — assign dynamically on click when lists are large.
- Library budget: Motion is ~5–15KB modular (`m` + LazyMotion); a full animation library for two fades is malpractice — and hand-rolled spring math for a gesture-driven sheet is too.

## 4b. Micro-interaction catalog (the standard answers)

| Interaction | Standard treatment |
|---|---|
| Button press | `scale(0.97)` or 1px translate-down, 100ms; release springs back 150ms |
| Toggle/switch | Thumb translate 150–200ms ease-out; track color cross-fades in parallel |
| Checkbox | Check path draw (SVG `stroke-dashoffset`) 200ms ease-out; box fill 100ms first |
| Dropdown/menu | Fade + `scale(0.96→1)` from trigger origin + 4–8px translate, 150–200ms; exit 100–120ms fade |
| Tooltip | 300–500ms hover *delay* (intent filter), then 100–150ms fade; instant for subsequent tooltips within ~500ms (warm state) |
| Dialog | Scrim fade 200ms; panel fade + `scale(0.96→1)` or 8–16px rise, 250ms ease-out; exit 150–200ms |
| Drawer/sheet | Slide from its edge 250–300ms expo-out; gesture-dismissible sheets use springs |
| Toast | Slide + fade in from its screen edge 250ms; exit fade 150ms; stack pushes existing toasts via FLIP |
| Accordion | Height via grid-template-rows `0fr→1fr` (or FLIP) 200–250ms + content fade; never `height: auto` transition hacks with magic max-height |
| Tab indicator | Slide between tabs 200ms ease-in-out (FLIP or `view-transition-name`); panel cross-fade 150ms |
| Reorder/drag | Lifted item: scale 1.02–1.05 + shadow raise 150ms; siblings FLIP around it (springy); drop settles with spring |
| Invalid shake | translate ±4px, 2 cycles, ~250ms total — small and fast, not cartoon |
| Count/number change | Old digit slides up-out, new slides up-in 200ms, `overflow: hidden`; or cross-fade; tabular-nums mandatory |

```css
/* GOOD: the accordion height trick — animatable without max-height hacks */
.acc-panel { display: grid; grid-template-rows: 0fr; transition: grid-template-rows 220ms var(--ease-out); }
.acc-panel > div { overflow: hidden; }
.acc-item[data-state="open"] .acc-panel { grid-template-rows: 1fr; }
```

## 4c. View Transitions recipe

```js
// SPA state/view swap with graceful degradation
function navigate(updateDom) {
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduce || !document.startViewTransition) { updateDom(); return; }
  document.startViewTransition(updateDom);
}
```

```css
::view-transition-old(root) { animation: fade-out 150ms var(--ease-in) forwards; }
::view-transition-new(root) { animation: fade-in 250ms var(--ease-out); }
/* Shared element: tag both states with the same name */
.product-card img { view-transition-name: var(--vt-name); } /* set per-item, on click, for long lists */
.product-hero img { view-transition-name: product-image; }
```

- Support status: same-document transitions are **Baseline newly available** (all three engines
  since Firefox 144, Oct 2025) — keep the `startViewTransition` gate anyway; view-transition *types*
  (`:active-view-transition-type()`) reached Firefox only in 147 (web-features 3.40.0).
- Cross-document (MPA) transitions: `@view-transition { navigation: auto; }` in both pages —
  free page-morphs for server-rendered sites; same reduced-motion gate via media query wrapping.
  Chromium + Safari only (Firefox in progress; an Interop 2026 focus area) — enhancement, never
  a dependency.
- Default crossfade is rarely enough; customize old/new animations or it reads as a laggy blink.
  Keep root transitions ≤ 250ms; shared-element morphs ≤ 350ms.
- The DOM update callback runs synchronously and the page freezes during snapshot — keep the
  update fast; don't start transitions around slow async work (await data *first*, then
  transition).

## 5. Performance: the compositor contract

- Animate **only `transform` and `opacity`** (plus `filter` cautiously, and `clip-path` on modern engines). These skip layout and paint.
- **Never animate** `width/height/top/left/margin/padding` (layout thrash, jank on every frame) or `box-shadow`/`background` directly. Size change → FLIP or `scale`; position → `translate`; shadow → cross-fade a pseudo-element's opacity.

```css
/* BAD: layout + paint per frame */
.card:hover { width: 320px; box-shadow: 0 8px 30px rgb(0 0 0 / .2); transition: all .3s; }

/* GOOD: compositor-only; shadow pre-rendered on ::after, faded in */
.card { transition: translate 200ms var(--ease-out), scale 200ms var(--ease-out); }
.card::after { content: ""; position: absolute; inset: 0; opacity: 0;
  box-shadow: var(--shadow-lg); transition: opacity 200ms var(--ease-out); }
.card:hover { translate: 0 -2px; scale: 1.01; } .card:hover::after { opacity: 1; }
```

- `transition: all` is banned — it animates properties you didn't intend (including layout ones) and breaks the moment someone adds a property.
- **`will-change` discipline**: apply just before animation, remove after (or via `:hover` ancestor); never blanket `will-change: transform` in stylesheets — each promoted layer costs memory; dozens of them OOM mobile tabs. CSS transforms/opacity animations get promoted automatically anyway in modern engines; explicit `will-change` is for *just-in-time* hints on known-heavy elements.
- Target 60fps minimum (8ms budget on 120Hz displays); validate in DevTools Performance with 4–6× CPU throttle on a mid-tier Android profile, not your dev machine.
- Animating blur (`filter: blur()`) and `backdrop-filter` is paint-expensive — keep areas small, durations short, and test on low-end hardware.
- Don't animate during load/INP-critical windows; entrance animations must not block interactivity (CSS animations don't; JS rAF loops can).

## 6. Reduced motion: non-negotiable

`prefers-reduced-motion: reduce` is set by users with vestibular disorders (motion can cause
nausea, vertigo, migraine) — honoring it is WCAG 2.3.3 (Animation from Interactions — Level **AAA**, so above the 2.2 AA
floor) and table stakes regardless.

- Reduced ≠ none: replace movement with **opacity cross-fades**; keep feedback (a 100ms fade still confirms the click). Kill: parallax, scale/slide entrances, auto-playing carousels, scroll-jacking, background video, infinite loops.
- Centralize the override so it can't be forgotten:

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

…then re-introduce intentional cross-fades inside the media query where needed. (0.01ms, not 0,
keeps `animationend`/`transitionend` firing so JS state machines don't hang.)

- JS/libraries must check too: `matchMedia('(prefers-reduced-motion: reduce)')`, Motion's `useReducedMotion()`, and gate View Transitions (`if (reduce || !document.startViewTransition) { swap(); } else { startViewTransition(swap); }`).
- Autoplaying motion > 5s requires pause/stop/hide regardless of preference (WCAG 2.2.2); nothing flashes > 3×/sec (2.3.1).
- Scroll-driven/parallax effects: disable entirely under reduced motion; even small parallax is a top vestibular trigger.

## 7. Scroll-driven & ambient motion

- CSS scroll-driven animations (`animation-timeline: view()`) for reveal-on-scroll, progress bars, header shrink — compositor-driven, no scroll listeners. Not yet Baseline (Chromium 115+, Safari 26+; Firefox still flag-gated as of mid-2026 — an Interop 2026 focus area). Feature-detect: `@supports (animation-timeline: view())`; fallback = content simply visible (never hidden-forever — the classic "opacity:0 until JS" failure: content must be visible if JS/modern CSS is absent).
- Reveal-on-scroll: trigger once, animate ≤ 20–30px translate + fade, threshold so it fires before the element is fully in view; never re-hide on scroll-up (gimmick, hurts re-reading).
- Scroll-jacking (hijacking wheel speed/direction) is banned in product UI; tolerated only in short marketing set-pieces with reduced-motion and keyboard escape paths.
- Ambient/looping motion (gradients, blobs): pause when off-viewport (`animation-play-state` via IntersectionObserver) and under reduced motion; loops must be seamless and slow (≥ 8s cycle) or they read as a glitch.

## 7b. Gesture-driven motion spec (sheets, swipes, drags)

Gestures need physics, thresholds, and escape hatches — not just animations:

- **Direct manipulation tracks 1:1**: while the finger is down, the sheet/card follows the
  pointer exactly (no easing during drag); easing/springs apply only after release.
- Release logic combines **distance + velocity**: dismiss if dragged past ~50% OR flicked past
  ~500px/s regardless of distance; otherwise spring back. Velocity-blind thresholds feel dead.
- Resistance at boundaries: rubber-band overscroll (`offset = delta * 0.3`-style damping or
  log curve) signals the edge without a hard stop.
- Interruptibility is mandatory: a new touch mid-spring captures the element at its current
  position/velocity (springs natively support this; duration-based tweens must be cancelled and
  re-derived).
- Every gesture surface declares `touch-action` correctly (`pan-y` on a horizontally swipeable
  card) so the browser doesn't fight the gesture, and provides the non-gesture path
  (rules/04 §8, WCAG 2.5.7).

## 7c. Canvas, WebGL & 3D motion hygiene

Inside a canvas, none of the CSS guarantees above apply — no compositor
fast-path, no media queries, no automatic cleanup. You re-implement the hygiene:

- **Delta-time, always.** rAF fires at the display's refresh rate — 60Hz, 120Hz
  (ProMotion), 144Hz — so advance animation by elapsed time from the rAF
  timestamp argument, never by per-frame constants, or motion runs 2× speed on
  120Hz screens. Clamp large deltas (tab restore, debugger pause) so physics
  doesn't explode.
- **Pause when hidden, stop when static.** Browsers pause rAF in background
  tabs, but `setInterval` tickers, physics/sim workers, and WebSocket-fed state
  are *not* auto-paused — handle `visibilitychange` / `document.hidden` and
  stop them explicitly. And don't run a 60fps loop drawing identical frames:
  render on demand (invalidate-on-change) when nothing is animating.
- **Dispose GPU resources on unmount.** Removing a Three.js object from the
  scene frees nothing: call `geometry.dispose()`, `material.dispose()`,
  `texture.dispose()` (textures are not disposed with their material),
  `renderTarget.dispose()`, and `renderer.dispose()` on teardown; verify with
  `renderer.info.memory` across mount/unmount cycles. A SPA route that mounts a
  canvas leaks a whole scene per navigation without this.
- **Keep draw calls low**: share geometries and materials; render repeated
  meshes with `InstancedMesh` (N instances, one draw call); prefer texture
  atlases over many small textures.
- **Freeze settled simulations.** d3-force / physics layouts that keep ticking
  after convergence burn CPU and battery forever — stop at an alpha/energy
  threshold, restart on interaction.
- **Reduced motion reaches inside canvas only if you put it there.** The CSS
  override in §6 can't see your draw loop: branch the render path on
  `matchMedia('(prefers-reduced-motion: reduce)')` (and listen for `change`) —
  render the settled/static state, still ambient loops, skip camera
  fly-throughs.

## 8. Motion as a system (tokens, testing, INP)

- Motion tokens live beside color/space tokens: `--duration-instant/fast/base/slow`
  (100/150/250/400ms), `--ease-out/in/in-out/spring` — and the JS animation layer imports the
  *same* values (export tokens to a `motion.ts`); two sources of duration truth always drift.
- Define per-pattern semantic tokens for repeated choreography (`--dialog-enter`, `--toast-exit`)
  so product teams compose, not invent.
- Test motion like behavior: Playwright with `page.emulateMedia({ reducedMotion: 'reduce' })`
  asserting movement is replaced (not feedback-deleted); visual regression captures animation
  *end states*; for flake-free CI, force `animation-duration: 0.01ms` globally except in the
  dedicated motion test suite.
- **INP discipline**: the 100ms feedback rule (rules/04 §9) means press feedback must not wait on
  JS work — CSS `:active` styles render before your handler runs; keep handlers under ~50ms or
  yield (`scheduler.yield()` — not Baseline, feature-detect — or `setTimeout` chunking) and let the pressed state + spinner carry
  the wait. An entrance animation that delays event binding (JS-mounted listeners after
  choreography) is a sequencing bug.
- Battery/CPU respect: pause ambient loops on `visibilitychange`, stop rAF loops when idle, and
  consider `prefers-reduced-data` for autoplaying media. An idle dashboard should be at 0% CPU —
  open the Performance monitor and verify.

## Audit checklist

- [ ] Every animation states a purpose (orientation/feedback/continuity/status); decoration-only motion on task surfaces removed
- [ ] Durations within standard bands (micro ≤ 150ms, enter 200–300ms, exit faster, nothing > 500ms interactive); values from duration/easing tokens, not literals
- [ ] Ease-out on enter, ease-in/fast on exit, no `linear`/default-`ease` on deliberate motion; springs used for gestural/interruptible interactions
- [ ] Stagger ≤ 50ms/item capped ~400ms total; transitions have one hero element; directional metaphors consistent (and RTL-mirrored)
- [ ] Micro-interactions match the catalog standards (tooltip intent delay, accordion via 0fr→1fr, toast FLIP stacking, shake ≤ 2 cycles); no max-height transition hacks
- [ ] View Transitions: customized old/new animations (no default-blink), per-item names assigned dynamically on large lists, DOM update fast and post-await, reduced-motion + support gates in place
- [ ] Only transform/opacity animated (grep for transitions on width/height/top/left/margin/box-shadow and `transition: all`)
- [ ] `will-change` absent from static stylesheets; applied/removed around animation only
- [ ] Layout changes use FLIP/View Transitions/Motion layout — no JS animating layout properties per frame
- [ ] View Transitions and scroll-driven animations feature-detected with working instant fallbacks; no content stuck at opacity 0 without JS
- [ ] `prefers-reduced-motion` honored globally (CSS override + JS/matchMedia in every animation lib entry point); movement replaced by fades, parallax/autoplay killed; *end events still fire
- [ ] Autoplay > 5s pausable; no flashing > 3/sec; ambient loops pause off-screen
- [ ] 60fps verified under CPU throttle on mid-tier mobile profile; no animation blocks first interaction
- [ ] Canvas/WebGL loops are delta-time based (rAF timestamp, not frame counts), stop on `document.hidden` and when the scene is static; force/physics sims freeze once settled
- [ ] WebGL/Three.js teardown disposes geometries, materials, textures, render targets, and the renderer; `renderer.info.memory` stable across mount/unmount cycles
- [ ] Reduced-motion branch exists *inside* canvas/WebGL render paths (matchMedia in JS — the CSS override doesn't reach the draw loop)
