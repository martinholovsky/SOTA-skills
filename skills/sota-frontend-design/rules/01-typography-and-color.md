# 01 — Typography & Color

Typography carries ~90% of UI information; color encodes state, brand, and hierarchy. Both must be
built as **systems** (scales, tokens), never as ad-hoc per-element values.

## 1. Type scale: use a ratio, cap the steps

- Define a modular scale (ratio 1.2–1.333 for product UI, 1.333–1.5 for marketing/editorial). 6–8 steps max.
- Name steps semantically (`--text-sm`, `--text-body`, `--text-h2`), not by pixel value. Renaming `--text-14` later is a migration; renaming what `--text-sm` resolves to is a token edit.
- Body text: **16px minimum** on web (never below 14px for any persistent reading text). Legal/footnote 12px floor, sparingly.

```css
/* GOOD: fluid scale, semantic names, clamp() between viewport bounds */
:root {
  --text-sm:   clamp(0.833rem, 0.80rem + 0.15vw, 0.9rem);
  --text-body: clamp(1rem, 0.95rem + 0.25vw, 1.125rem);
  --text-lg:   clamp(1.25rem, 1.15rem + 0.5vw, 1.5rem);
  --text-h2:   clamp(1.563rem, 1.35rem + 1vw, 2.25rem);
  --text-h1:   clamp(1.953rem, 1.55rem + 2vw, 3.25rem);
}
```

```css
/* BAD: magic numbers per component, no system, vw-only (fails zoom + tiny phones) */
.card-title { font-size: 19px; }
.hero h1 { font-size: 5vw; } /* unbounded; breaks WCAG 1.4.4 text resize */
```

- **clamp() rule**: always include a `rem` term in the middle expression so user font-size preferences and browser zoom still scale the text. Pure-`vw` fluid type fails WCAG 1.4.4 (resize to 200%).
- Verify: at 320px and 1920px viewports, headings don't collide or orphan; body stays 16–19px equivalent.

## 2. Line length, line height, alignment

Concrete numbers — apply, don't debate:

| Property | Standard |
|---|---|
| Line length (measure) | 45–75ch body; 60–66ch ideal. Enforce with `max-width: 65ch` on prose containers |
| Line height, body | 1.5–1.7 (WCAG 1.4.12 requires content survives 1.5) |
| Line height, headings | 1.1–1.25 (tighten as size grows) |
| Line height, UI labels/buttons | 1.2–1.4, or `1` with padding controlling height |
| Letter spacing | Headings ≥ 32px: −0.01em to −0.025em. ALL-CAPS labels: +0.04 to +0.08em. Body: 0 |
| Paragraph spacing | 0.75–1.25em; never both indent and spacing |

- Use **unitless** `line-height` (`1.5`, not `24px`) so it scales with font size.
- Never justify text on the web (rivers, no decent hyphenation control). `text-align: left` (or `start` for i18n).
- `text-wrap: balance` on headings, `text-wrap: pretty` on paragraphs — both are free wins, progressive enhancement.
- Long-word overflow: `overflow-wrap: break-word` on prose containers; never let user content blow out layout.

## 3. Font loading & variable fonts

- Prefer **one variable font** over 4 static weights: smaller total payload, animatable weight, optical sizing.
- Self-host with `font-display: swap` (or `optional` for non-brand-critical text); `preload` only the primary text face (the one above the fold), as woff2.
- Subset aggressively (`unicode-range`); a Latin subset of a variable font should be 30–80KB.
- Define fallback metrics to kill CLS: `size-adjust`, `ascent-override`, `descent-override` on a local fallback `@font-face` (tools: Fontaine, Capsize). Layout shift from font swap is a real CWV regression.

```css
@font-face {
  font-family: "Inter";
  src: url("/fonts/inter-var.woff2") format("woff2");
  font-weight: 100 900; /* variable axis range */
  font-display: swap;
}
/* Metric-matched fallback prevents reflow on swap */
@font-face {
  font-family: "Inter Fallback";
  src: local("Arial");
  size-adjust: 107%;
  ascent-override: 90%;
}
```

- `font-variation-settings` overrides ALL axes and disables high-level properties — use `font-weight` / `font-optical-sizing` first; reach for `font-variation-settings` only for custom axes (e.g. `"GRAD"`).
- Numeric data (tables, timers, prices): `font-variant-numeric: tabular-nums` so digits don't jitter.

## 3b. Pairing, stacks & weight discipline

- **Two families maximum** (display + text), three with a mono for code/data. Pair by contrast of
  *role*, not similarity: serif display + grotesque body, or one superfamily with optical sizes.
  If unsure, one variable family with strong weight range beats a mediocre pairing.
- Weight palette: pick 3–4 stops and tokenize (`--font-regular: 400; --font-medium: 500;
  --font-semibold: 600; --font-display: 650`). UI emphasis = medium/semibold, not bold-700
  (too heavy at small sizes in most modern faces). Never fake weights — if 500 isn't loaded or in
  the variable range, browsers synthesize garbage; same for `font-synthesis: none` to block faux
  bold/italic on fallbacks.
- Full fallback stacks always, metric-compatible where possible:

```css
--font-sans: "YourSans", "YourSans Fallback", system-ui, sans-serif;
--font-mono: "YourMono", ui-monospace, "SF Mono", monospace;
```

- `system-ui` alone is a legitimate, fast, zero-CLS choice for product UI — but then identity must
  come from color/spacing/motion (rules/07 §6), and you still tokenize sizes/weights.
- Hyphenation: `hyphens: auto` (with correct `lang` attribute — it's lang-dependent) only on
  narrow justified-adjacent columns; never on headings or UI labels.
- Microtypography that signals craft: real quotes and apostrophes (‘ ’ “ ”), en dash for ranges
  (12–16), em dash for breaks, `&nbsp;` between number and unit (16 GB), `text-decoration-
  thickness`/`underline-offset` tuned on links (`underline-offset: 0.15em`), `font-feature-
  settings: "ss01"` etc. only via tokens.
- Min target for `letter-spacing` adjustments: apply via the scale tokens (e.g. `--text-h1` pairs
  with `--tracking-h1: -0.02em`), never sprinkled per component.

## 4. Color: author in OKLCH

OKLCH is the SOTA authoring space (perceptually uniform lightness, predictable chroma, wide-gamut capable).
HSL lies about lightness — HSL `yellow` and `blue` at the same L are wildly different perceived brightness.

```css
/* GOOD: one hue, vary L/C for a predictable ramp; P3 where supported */
:root {
  --blue-600: oklch(0.55 0.18 255);
  --blue-700: oklch(0.48 0.17 255);
  --accent: oklch(0.72 0.21 25); /* gamut-maps gracefully on sRGB screens */
}
.btn:hover { background: oklch(from var(--blue-600) calc(l - 0.06) c h); } /* relative color syntax */
```

```css
/* BAD: hand-picked hexes with inconsistent perceived steps; hover via opacity hacks */
--blue-600: #2563eb; --blue-700: #1d4ed8; /* fine values, but no system to derive states */
.btn:hover { filter: brightness(0.9); } /* desaturates, unpredictable contrast */
```

- Build palettes as **ramps**: fixed hue, stepped lightness (e.g. L 0.97 → 0.20 across 11 steps), chroma peaking mid-ramp. Steps should be perceptually even — OKLCH gives you that for free.
- Hue shift across a ramp (±5–15° toward warm in lights, cool in darks) reads as more natural than a locked hue.
- Keep a fallback story: OKLCH is supported everywhere modern (2023+); for legacy targets use `@supports (color: oklch(0% 0 0))` or build-time conversion.

## 4b. Deriving state colors & transparency tokens

Interactive state colors are **derived, not invented** — one rule produces hover/active/selected
for every accent and keeps ramps consistent:

```css
/* Relative color syntax: hover = darker in light mode, LIGHTER in dark mode */
:root {
  --accent-bg-hover: oklch(from var(--accent-bg) calc(l - 0.05) c h);
  --accent-bg-active: oklch(from var(--accent-bg) calc(l - 0.09) c h);
}
[data-theme="dark"] {
  --accent-bg-hover: oklch(from var(--accent-bg) calc(l + 0.05) c h);
  --accent-bg-active: oklch(from var(--accent-bg) calc(l + 0.09) c h);
}
```

- `color-mix(in oklch, var(--accent) 12%, var(--surface))` for tints (selected rows, badges,
  subtle backgrounds) — mixes stay on-theme automatically when the surface changes. Prefer
  `in oklch` / `in oklab`; sRGB mixing desaturates through gray.
- **Alpha tokens for overlays only** (`--overlay-scrim: oklch(0 0 0 / 0.5)`, hairline borders over
  imagery). Don't build text colors from alpha-on-unknown-background — contrast becomes
  unverifiable; text tokens are opaque, computed per theme.
- Selection and focus are brand surfaces too: `::selection { background: var(--accent-bg);
  color: var(--accent-fg); }` (check 4.5:1!) and `--focus-ring` as its own token (usually accent
  at full chroma, 2px, offset 2px) — one token so rules/05's ring is consistent everywhere.
- Wide gamut: define P3-capable OKLCH values; browsers gamut-map for sRGB screens. For maximum
  control wrap vivid brand moments in `@media (color-gamut: p3)`. Never let a P3-only chroma be
  the sole carrier of a state difference — verify on sRGB.

## 5. Contrast math — verify, never eyeball

WCAG 2.2 AA minimums (hard floor):

| Element | Ratio |
|---|---|
| Body text (< 24px / < 18.66px bold) | **4.5:1** |
| Large text (≥ 24px, or ≥ 18.66px bold) | 3:1 |
| UI component boundaries & states (1.4.11) | 3:1 against adjacent colors |
| Focus indicators | 3:1 against both component and background |

- Non-text contrast (1.4.11) is the most-missed rule: input borders, icon-only buttons, toggle states, chart series, slider tracks — all need 3:1.
- Placeholder text is text: 4.5:1 — which is why placeholder-as-label is banned (see rules/04).
- Don't rely on contrast alone for state: pair color with icon/weight/underline (links in body text get underlines; color-only links fail 1.4.1).
- APCA (the WCAG 3 draft model) is better math — use it to *choose* colors, but **ship against WCAG 2.x ratios** because that's what's legally testable in 2026.
- Disabled controls are exempt from contrast, but if users must *read* the value of a disabled field, render it as read-only text instead.

## 6. Semantic color tokens & dark mode

Two-layer (minimum) token architecture: **primitive → semantic**. Components reference semantic only.

```css
/* Layer 1: primitives (raw ramps) */
:root { --gray-50: oklch(0.98 0.005 260); --gray-900: oklch(0.22 0.02 260); /* … */ }

/* Layer 2: semantic — the ONLY layer components touch */
:root {
  --surface: var(--gray-50);
  --surface-raised: oklch(1 0 0);
  --text-primary: var(--gray-900);
  --text-secondary: var(--gray-600);
  --border-subtle: var(--gray-200);
  --accent-bg: var(--blue-600);
  --accent-fg: oklch(0.99 0.01 255);
  color-scheme: light dark;
}
[data-theme="dark"] {
  --surface: var(--gray-950);
  --surface-raised: var(--gray-900); /* raised = LIGHTER in dark mode (closer to light source) */
  --text-primary: var(--gray-50);
  --text-secondary: var(--gray-400);
  --accent-bg: var(--blue-400); /* desaturate + lighten accents on dark */
}
```

Dark mode is a redesign, not an inversion:

- **Never pure black** `#000` surfaces or pure white text — use near-black (`oklch(0.18–0.22)`) and off-white (`oklch(0.92–0.96)`); pure-on-pure causes halation for astigmatic users.
- Elevation flips: in light mode, raised = shadow; in dark mode, raised = **lighter surface** (shadows are invisible on dark). Define `--surface`, `--surface-raised`, `--surface-overlay` as a ladder.
- Reduce chroma of saturated brand colors on dark backgrounds (vibrating edges); lighten accents 1–2 ramp steps so they keep 4.5:1 *as text* / 3:1 *as UI*.
- Re-verify every contrast pair in dark mode separately — passing light mode proves nothing.
- Set `color-scheme: light dark` so form controls, scrollbars, and UA defaults match the theme.
- Respect three states: light / dark / **system** (default). Persist explicit choice; apply before first paint (inline script or server hint) to avoid theme flash.
- Images: provide dark variants where needed (`<picture>` + `prefers-color-scheme`), or temper with `filter: brightness(.9)` on glaring photos.
- `light-dark()` function is fine for simple sites; token-swap via attribute scales better for systems (supports user override, >2 themes).

## 6b. Verification workflow (color)

- Automate contrast over the **token matrix**, not screenshots: a script iterates every
  documented fg/bg token pair × every theme and fails CI under threshold. Screenshot-based
  checkers miss states (hover, selected) that token-level checks catch by construction.
- Manual spot-checks where automation is blind: text over images/gradients (test the *lightest*
  region under the text — or add a scrim/`text-shadow` and stop gambling), charts, third-party
  embeds.
- Simulate, don't guess: DevTools rendering emulation for `prefers-color-scheme`,
  `prefers-contrast`, `forced-colors`, and the three common color-vision deficiencies
  (deuteranopia ~5% of males — your largest a11y cohort after low vision).
- Real-device check: OLED black smearing on dark-theme scrolling, P3 vividness vs sRGB office
  monitors, and auto-brightness at 30% — a 4.6:1 pair that's "fine" at full brightness is the
  field-failure mode.

## 7. Color semantics & restraint

- One accent hue does 90% of the work. Success/warning/danger/info get their own semantic ramps, used **only** for status — never decoratively (a red marketing banner makes real errors invisible).
- Gray is not neutral by default: tint grays slightly toward the brand hue (C 0.005–0.02) for cohesion; pure desaturated gray reads cheap next to chromatic accents.
- 60-30-10 as sanity check: ~60% surface/neutral, ~30% secondary, ~10% accent. If a screen is >15% accent color, hierarchy has collapsed.

## Audit checklist

- [ ] Type sizes come from a named scale (≤ 8 steps); no rogue `font-size` literals in components
- [ ] Body text ≥ 16px, line-height 1.5–1.7 unitless, measure ≤ 75ch
- [ ] Fluid type uses `clamp()` with a rem term; page is readable and un-clipped at 200% zoom (WCAG 1.4.4) and 320px width (1.4.10 reflow)
- [ ] `text-spacing` override survives (1.4.12): bump line-height 1.5 / letter 0.12em / word 0.16em — nothing clips
- [ ] Variable font self-hosted, subset, `font-display` set, metric-matched fallback (no font-swap CLS)
- [ ] ≤ 2 text families (+mono); 3–4 tokenized weights; `font-synthesis` controlled; full fallback stacks
- [ ] Tabular figures on numeric columns/timers; real quotes/dashes; tracking via scale tokens only
- [ ] State colors derived via relative-color/`color-mix` rules (one definition per theme), not hand-picked per component; text tokens opaque; `::selection` and `--focus-ring` defined and contrast-checked
- [ ] All text 4.5:1 (3:1 large); all UI boundaries, icons, focus rings, states 3:1 (1.4.11) — verified in BOTH themes
- [ ] Links in prose distinguishable without color; status never encoded by color alone
- [ ] Tokens are two-layer; components never reference primitive ramps or hex literals
- [ ] Dark mode: no pure black/white, elevation = lighter surface, accents desaturated, `color-scheme` declared, no flash of wrong theme, system preference honored with manual override
