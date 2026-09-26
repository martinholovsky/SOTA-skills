# 02 — Layout, Spacing & Responsive (Modern CSS)

Layout in 2026 is grid-first, container-query-driven, and fluid by default. Media queries are the
fallback, not the strategy. Components must be **context-independent**: they adapt to the space they
get, not to the viewport.

## 1. Spacing system: 4/8pt grid, tokenized

- All spacing comes from a geometric-ish scale on a 4px base: `4, 8, 12, 16, 24, 32, 48, 64, 96`. No `13px`, no `margin: 18px 22px`.
- Name tokens by step (`--space-1` … `--space-9`) or t-shirt (`--space-sm`). Components reference tokens only.
- **Gap over margin**: parents own spacing between children via `gap`; children never carry outer margins (margin makes components non-composable — the "margin considered harmful" rule).

```css
/* GOOD: parent controls rhythm; component is margin-free */
.stack { display: flex; flex-direction: column; gap: var(--space-4); }
.cluster { display: flex; flex-wrap: wrap; gap: var(--space-2); align-items: center; }

/* BAD: child dictates external spacing; breaks in any other context */
.card { margin-bottom: 24px; }
.card:last-child { margin-bottom: 0; } /* the smell that proves it */
```

- Related items sit closer than unrelated (proximity = grouping): within-group gap ≤ ½ between-group gap. If section gap is 32, intra-card gap is ≤ 16.
- Spacing communicates hierarchy more cheaply than lines/boxes. Before adding a divider or border, try doubling the gap.
- Fluid spacing for page-level rhythm: `--space-section: clamp(3rem, 2rem + 4vw, 7rem);` — section padding should breathe with viewport; component-internal padding stays fixed-step.
- Optical alignment beats mathematical: icons next to text need baseline/cap-height nudges (often 1–2px); text in buttons sits 1px high due to descender space — fix with asymmetric padding when it shows.

## 2. Grid is the default; flexbox is for one axis

- Page/section/two-dimensional layout: `display: grid`. One-dimensional content flow (toolbars, tag rows, nav): flexbox.
- Stop writing breakpointed column counts; let content decide:

```css
/* GOOD: auto-responsive card grid, zero media queries */
.cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(18rem, 100%), 1fr));
  gap: var(--space-5);
}
```

```css
/* BAD: media-query ladder restating the same intent four times */
.cards { display: grid; grid-template-columns: 1fr; }
@media (min-width: 640px) { .cards { grid-template-columns: 1fr 1fr; } }
@media (min-width: 1024px) { .cards { grid-template-columns: repeat(3, 1fr); } }
```

- `min(18rem, 100%)` prevents overflow below 18rem — the classic `minmax` footgun.
- `auto-fill` keeps column tracks when sparse (cards stay card-sized); `auto-fit` stretches survivors. Choose deliberately.
- **Subgrid** for aligning card internals across siblings (title/body/footer rows line up regardless of content length):

```css
.cards > .card { display: grid; grid-row: span 3; grid-template-rows: subgrid; }
```

- Full-bleed page shell — named grid lines instead of nested max-width wrappers:

```css
.page {
  display: grid;
  grid-template-columns: [full-start] minmax(var(--space-4), 1fr)
    [content-start] min(72rem, 100%) [content-end] minmax(var(--space-4), 1fr) [full-end];
}
.page > * { grid-column: content; }
.page > .bleed { grid-column: full; }
```

- Never fix heights on text-bearing containers (`height: 200px` → clipped translations/zoom). Use `min-height` and let content size the box. Aspect ratios via `aspect-ratio`, not padding hacks.

## 3. Container queries: components respond to their container

Components ship with their own responsive behavior — the page doesn't micromanage them.

```css
/* GOOD: card adapts to the column it's placed in, anywhere */
.card-wrap { container: card / inline-size; }
.card { display: grid; gap: var(--space-3); }
@container card (min-width: 28rem) {
  .card { grid-template-columns: 10rem 1fr; }
}

/* Container query units for intrinsic fluidity */
.card h3 { font-size: clamp(1.1rem, 4cqi, 1.5rem); }
```

- Rule of thumb: **media queries for page chrome** (nav collapse, sidebar visibility, density); **container queries for everything inside the layout**.
- The container element can't size itself from its contents on the queried axis — wrap components in a dedicated container element.
- `container-type: inline-size` is the default tool; `size` only when you must query height (rare, requires fixed height anyway).
- Style queries (`@container style(--variant: compact)`) for theming/density flags passed down via custom properties — Baseline newly available since Firefox 151 (May 2026); custom-property queries only (standard-property style queries remain experimental). Feature-test for the long-tail; an Interop 2026 focus area.

## 3b. Intrinsic sizing & layout primitives

Prefer content-aware keywords over hardcoded dimensions:

- `min-content` / `max-content` / `fit-content()` size boxes from content; `width: fit-content`
  + `margin-inline: auto` centers a box at its natural width — no width guessing.
- `flex: 1 1 20rem` (grow, shrink, content-informed basis) over `width: 33%`; the sidebar pattern:

```css
/* Sidebar that wraps to stacked below a content floor — no media query */
.with-sidebar { display: flex; flex-wrap: wrap; gap: var(--space-5); }
.with-sidebar > aside { flex: 1 1 16rem; }
.with-sidebar > main { flex: 999 1 28rem; } /* huge grow factor claims the row when both fit */
```

- Standardize a small set of layout primitives (Every-Layout style) instead of bespoke CSS per
  screen: **Stack** (vertical gap), **Cluster** (wrapping row), **Sidebar**, **Switcher**
  (row→column under a width), **Center** (measure-capped column), **Cover** (min-height hero),
  **Frame** (aspect-ratio media). ~7 primitives compose 90% of screens and make spacing/rhythm
  consistent by construction.
- `aspect-ratio: 16/9` on media frames (with `object-fit: cover` on the child); never padding-top
  percentage hacks; never width+height pairs that fight responsive images.

## 3c. Viewport units & mobile chrome

- Use **`dvh`** for full-height app shells (`min-height: 100dvh`) — `100vh` overflows under
  mobile browser chrome (the classic iOS bottom-bar bug). `svh` for "never jumps" conservative
  sizing; `lvh` rarely.
- Don't build whole layouts in viewport units; they ignore container context and zoom oddly —
  page shell only.
- Account for notches/home indicators on full-bleed fixed elements:
  `padding-bottom: max(var(--space-4), env(safe-area-inset-bottom))` (requires
  `viewport-fit=cover`).
- On-screen keyboard: prefer `interactive-widget=resizes-content` (meta viewport) or the
  VirtualKeyboard API for chat-style inputs pinned to the bottom; test that focused inputs aren't
  hidden behind the keyboard.

## 4. Media queries that remain

When you do write them:

- **Mobile-first** (`min-width`), always. Desktop-first `max-width` overrides accumulate into specificity soup.
- Breakpoints in `rem`/`em` (zoom-friendly): typically `40em / 64em / 90em`. Breakpoints follow *content breaking*, not device names.
- Preference queries are mandatory plumbing: `prefers-reduced-motion` (see rules/06), `prefers-color-scheme`, `prefers-contrast: more` (strengthen borders/text), `forced-colors: active` (respect system palette: use `currentColor`, `CanvasText`, never `forced-color-adjust: none` without reason).
- Pointer queries for touch affordances: `@media (pointer: coarse) { /* ≥44px targets, larger hit areas */ }` — better signal than viewport width for touch.
- Avoid `@media (hover: none)` to *remove* functionality; provide alternatives instead.

## 5. Logical properties & i18n-proof layout

Physical properties (`left/right/top/bottom` variants) break RTL. Default to logical:

| Physical (avoid) | Logical (use) |
|---|---|
| `margin-left` | `margin-inline-start` |
| `padding-right` | `padding-inline-end` |
| `width / height` | `inline-size / block-size` (when flow-relative) |
| `border-radius: 8px 0 0 8px` | `border-start-start-radius` etc. |
| `text-align: left` | `text-align: start` |
| `top/left` (positioned) | `inset-block-start / inset-inline-start` |

- Shorthands: `margin-inline: auto`, `padding-block: var(--space-4)`, `inset: 0`.
- Test with `dir="rtl"` on `<html>` once per layout; icons indicating direction (arrows, chevrons) must mirror — `[dir="rtl"] .icon-next { scale: -1 1; }`.

## 6. Modern selectors & architecture

- **`:has()`** — style parents/siblings by state; removes a whole class of JS classname toggling:

```css
.field:has(input:user-invalid) { --field-border: var(--danger-border); }
.form:has(input:focus-visible) .hint { opacity: 1; }
label:has(+ input:disabled) { color: var(--text-disabled); }
```

  Keep `:has()` arguments cheap (no deep descendant scans in hot paths); it invalidates upward.
- **`:user-invalid` / `:user-valid`** over `:invalid` — they wait for user interaction, so forms don't load pre-screaming red.
- **Native nesting**: nest one, max two levels (states, media/container queries inside the component block). Deeper nesting recreates the SCSS specificity mess.
- **Cascade layers** — declare order once, end specificity wars:

```css
@layer reset, base, tokens, components, utilities, overrides;
@layer components { .btn { /* loses to any utility regardless of specificity */ } }
```

  Put third-party CSS into a low layer: `@import url(vendor.css) layer(vendor);`. Unlayered styles beat all layers — keep app code layered so escape hatches stay available, and audit any unlayered rule as a smell.
- `:focus-visible` not `:focus` for rings (see rules/05); `:where()` to zero out specificity in resets/utilities.

## 7. Anchor positioning, popover & view transitions (progressive enhancement)

- **Popover API** (`popover` attribute) for menus/tooltips/toasts: free top-layer rendering, light-dismiss, focus handling — before reaching for a positioning library. Pair with **CSS anchor positioning**:

```css
.trigger { anchor-name: --menu-anchor; }
[popover].menu {
  position: absolute;
  position-anchor: --menu-anchor;
  position-area: block-end span-inline-end; /* `inset-area` is the deprecated pre-rename alias */
  position-try-fallbacks: flip-block, flip-inline;
}
```

- The core anchor-positioning properties (`anchor-name`, `position-area`, `position-try-fallbacks`) are **Baseline newly available** since 2026-01-13 (Chromium 125+, Safari 26+, Firefox 147+; `position-anchor` since 2026-09-14), but the web-features `anchor-positioning` feature as a whole is *not* Baseline — the `position-visibility` anchor keywords lag (web-features 3.40.0, read 2026-09-26). It is an Interop 2026 focus area. Newly ≠ widely: keep the **feature-detect** (`@supports (anchor-name: --a)`) with a Floating UI fallback while pre-2026 browsers are in your support matrix.
- View Transitions API for page/state morphs — covered in rules/06; treat as enhancement, never a functional dependency.
- General rule: detect features, not browsers; build the working baseline first, layer the modern API on top. A user on the fallback path gets a *plainer* experience, never a *broken* one.

## 8. Z-index & stacking-context discipline

Z-index wars are an architecture failure, not a numbers game.

- Tokenize the entire z scale — ≤ 7 values, semantic names:

```css
:root { --z-dropdown: 100; --z-sticky: 200; --z-drawer: 300; --z-modal: 400;
        --z-toast: 500; --z-tooltip: 600; }
```

  A literal `z-index: 9999` in component code is an audit finding; it means someone lost a war.
- Prefer the **top layer** (native `<dialog>.showModal()`, `popover`) — it renders above all
  z-indexes by spec, ending the problem for modals/menus/toasts entirely.
- Know what creates stacking contexts (`transform`, `filter`, `opacity < 1`, `position: fixed`,
  `will-change`, `contain`) — the usual "z-index doesn't work" cause is a parent context, not the
  number. `isolation: isolate` to deliberately scope a context.
- Portals are for escaping `overflow: hidden`/stacking ancestors, not a default; top-layer APIs
  remove most portal needs.

## 9. Responsive images & media

- `<img>` always has `width`/`height` (or `aspect-ratio`) — no CLS; `loading="lazy"` +
  `decoding="async"` below the fold, `fetchpriority="high"` on the LCP image only.
- Resolution switching via `srcset`/`sizes`; **`sizes` must reflect the rendered layout**
  (`sizes="(min-width: 64em) 33vw, 100vw"`) — a wrong `sizes` silently downloads 3× the bytes.
- Art direction (different crops per breakpoint) via `<picture>` + `media`; format negotiation
  via `<picture>` + `type` (AVIF → WebP → fallback).
- Background images that carry meaning belong in `<img>` (alt text, lazy-load, priority); CSS
  backgrounds are for decoration only.
- Video: `preload="none"`/`metadata`, poster image, never autoplay with sound; autoplaying
  ambient video gets a pause control (WCAG 2.2.2) and is suppressed under reduced motion +
  `prefers-reduced-data`.

## 10. Scrolling & overflow discipline

- `scrollbar-gutter: stable` on the root prevents layout shift when scrollbars appear.
- Custom scroll areas: `overscroll-behavior: contain` so nested scrollers don't chain to the page; visible focus + keyboard scrollability (`tabindex="0"` + `role="region"` + `aria-label` on scrollable regions that can trap keyboard users out of content).
- Snap points for carousels: `scroll-snap-type: x mandatory` + `scroll-snap-align`; never JS-hijack wheel events.
- `position: sticky` over JS scroll listeners for pinned headers; check it against `overflow: hidden` ancestors (the #1 reason sticky "doesn't work").
- Sticky headers must not eat anchor targets: `scroll-margin-top: var(--header-height)` on sections; `scroll-padding-top` on the scroller — also fixes focus jumps for keyboard users.

## Audit checklist

- [ ] All spacing values resolve to the 4/8 scale tokens; zero magic-number margins/paddings in component code
- [ ] Components are margin-free externally; parents use `gap` (grep for `margin-bottom` + `:last-child` resets)
- [ ] Card/listing grids use `auto-fill/minmax`, not media-query column ladders; `min(…, 100%)` guards present
- [ ] Cross-card alignment uses subgrid where internals must line up
- [ ] Reusable components respond via container queries, not viewport queries
- [ ] No fixed heights on text containers; no overflow clipping at 320px width or 200% zoom (WCAG 1.4.10)
- [ ] Logical properties throughout; layout verified under `dir="rtl"`; directional icons mirror
- [ ] Breakpoints in em/rem, mobile-first; `pointer: coarse` honored for hit areas
- [ ] Cascade layers declared; vendor CSS layered; no `!important` outside an explicit overrides layer
- [ ] `prefers-contrast` and `forced-colors` don't break the UI (Windows High Contrast pass)
- [ ] Popovers/menus use Popover API or equivalent top-layer + light-dismiss + Esc semantics; anchored positioning has a fallback
- [ ] App shells use `dvh` not `vh`; safe-area insets handled on fixed bottom elements; keyboard doesn't cover focused inputs
- [ ] Z-index values come from the ≤ 7-token scale (grep for `z-index: 9{3,}`); overlays prefer top-layer APIs; no portal sprawl
- [ ] Images: dimensions/aspect-ratio set (zero CLS), correct `sizes`, modern formats via `<picture>`, lazy below fold, `fetchpriority` on LCP only; meaningful images are `<img>` with alt
- [ ] `scrollbar-gutter: stable`, `overscroll-behavior` on nested scrollers, `scroll-margin` under sticky headers
