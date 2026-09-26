# 07 — Visual Craft, Hierarchy & Anti-Generic Design

The gap between "fine" and "excellent" UI is not features — it's hierarchy, restraint, and a
recognizable point of view. This file is about making interfaces that look *designed*, not
*generated*.

## 1. Visual hierarchy: engineer the scan path

Users scan, then read. Decide the 1-2-3 order of every screen and enforce it with size, weight,
color, and position — in that order of power.

- **One primary element per screen/section.** If you can't name what a screen is *for*, neither can the user. Two equally-shouting CTAs = zero CTAs.
- Hierarchy levers, cheapest first: position (top/left in LTR) → size → weight → color → motion. Spend the cheap ones before reaching for color; reserve accent color for interactive/primary (rules/01 §7).
- De-emphasize the secondary instead of inflating the primary: metadata drops to `--text-secondary`, secondary buttons go ghost/outline, labels shrink before headings grow. Most "make it pop" problems are "make everything else quieter" problems.
- Squint test (or blur the screenshot 5px): the primary action and page title should survive; if the screen becomes uniform gray mush, hierarchy is flat.
- Text hierarchy needs ≥ 2 distinct cues between levels (e.g. size + weight); a 1px font-size difference is noise, not hierarchy. Adjacent scale steps should differ ≥ ~20%.
- Numbers users compare (dashboards, pricing) get the size; their labels get small caps/secondary color — not the reverse.

## 2. Gestalt mechanics (the rules that actually do the work)

- **Proximity beats borders**: things that belong together sit together (rules/02 §1). Audit any UI with > 3 nested boxes — most borders/cards can be replaced by spacing + alignment.
- **Alignment**: every element aligns to *something*. Mixed center/left alignment in one section reads as sloppy instantly. Pick one text alignment per region; align numbers right in tables, with tabular figures.
- **Repetition/consistency**: same radius, same shadow scale, same icon stroke width, same gap rhythm everywhere. One 6px radius among 8px radii is a defect, not a detail.
- **Closure/containment budget**: each level of visual containment (card-in-card-in-panel) costs clarity. Max two levels of bordered containment; beyond that, use whitespace and headings.

## 3. Whitespace economics

Whitespace is the highest-leverage, lowest-cost design material — and the first thing
inexperienced builders delete to "fit more in".

- Macro whitespace (between sections) sets perceived quality: section padding
  `clamp(3rem, 2rem + 4vw, 7rem)` on marketing pages; 24–48px between functional groups in apps.
  Cramped sections read as cheap regardless of how good the components are.
- Whitespace asymmetry binds: heading sits closer to *its* content than to the previous section
  (e.g., 48px above an `h2`, 16px below). Equal space above and below a heading destroys
  grouping — the most common rhythm bug; fix at the stylesheet level (`h2 { margin-block: var(--space-7) var(--space-3); }`), not per page.
- Padding scales with container size: a 320px card gets 16–20px padding, a full-width panel
  32–48px. Tokenize as `--card-padding: clamp(1rem, 0.5rem + 2cqi, 2rem)` with container units.
- Don't fear the fold: users scroll; cramming everything above 700px viewport height produces
  uniformly dense mush. Prioritize, then let it breathe.
- Density ≠ crowding: pro tools earn density via *alignment and rhythm* (strict 4px grid, columns
  that line up), not by deleting padding.

## 4. Depth, borders & elevation: pick one language

Choose a depth language and apply it systematically — don't mix all three per component:

1. **Borders-first** (dense, technical, "Linear-like"): 1px `--border-subtle` lines, minimal shadows, surfaces differ by ±1 ramp step.
2. **Shadows-first** (friendly, layered): tokenized shadow scale (`--shadow-sm/md/lg`), shadows imply z-order only — menus above cards above page. Realistic shadows: y-offset > blur softness, low opacity, **two-layer** (tight ambient + soft key): `0 1px 2px rgb(0 0 0 / .06), 0 8px 24px rgb(0 0 0 / .10)`. Never `0 0 Npx` halos.
3. **Surface-shift** (flat, calm): no borders/shadows; hierarchy via background lightness steps — requires a well-tuned gray ramp and is the dark-mode default anyway (rules/01 §6).

- Elevation = proximity to user = interactivity/ephemerality: tooltips/menus highest, modals high, cards low, page base. An element's shadow must match its layer; random per-card shadow sizes break the physics.
- Hairline borders on dark mode: borders lighten (`oklch` +0.08–0.12 L over surface), shadows mostly disappear — re-tokenize, don't reuse light-mode shadow tokens.

## 5. Icons & detail craft

- One icon set, one stroke width (1.5px or 2px), one optical grid (20/24px). Mixed icon families are the fastest "unfinished" tell. Icons align to text via cap-height, optically centered (a play triangle needs a 1px right nudge).
- Icon + label by default; icon-only requires a tooltip AND `aria-label`, and is reserved for universally-known glyphs (×, search, settings).
- Border radius is a brand decision with a scale (`--radius-sm: 4px; --radius-md: 8px; --radius-lg: 12–16px; --radius-full`), nested radii follow **outer = inner + gap** or they look wrong.
- Avatars/images: fixed `aspect-ratio`, `object-fit: cover`, designed fallback (initials with deterministic ramp color, not broken-image glyph).
- Charts inherit the system: tokens for series colors (color-blind-safe ramp — verify deuteranopia), grid lines at `--border-subtle`, tabular figures, direct labels over legends when ≤ 4 series.

## 6. Avoiding "AI slop" / template genericism

The generic-2024-AI look: Inter/system font on white, violet-to-blue gradient hero, three-column
feature cards with emoji-grade icons, glassmorphism cards, purple glow shadows, rounded-2xl
everything, centered everything, `bg-gradient-to-r from-purple-500 to-blue-500`. It reads as
placeholder because it encodes zero decisions. Antidotes:

- **Make 3 deliberate global decisions minimum**: a typeface with character (not the framework default — try a grotesque with personality, a serif for editorial confidence, or a mono accent for technical brands); a non-default accent hue defined in OKLCH (not tailwind-violet); one signature element (distinctive radius stance — sharp 2px OR very round; a border-first depth language; an unusual but disciplined layout grid).
- Typography does branding cheaper than decoration: one display face used at real scale (clamp to 3–5rem+) with tight letter-spacing creates more identity than any gradient.
- Asymmetry is a feature: not every hero is center-stacked; editorial layouts (offset grids, 5/7 splits, overlapping media) read as designed. Keep asymmetry on the grid — asymmetric ≠ unaligned.
- Color courage with discipline: near-black-on-warm-paper, deep green, oxblood, cobalt — anything chosen beats default-blue. Keep the 60-30-10 budget and contrast math (rules/01).
- Kill list for credibility: gradient text on body copy, glow shadows, glassmorphism on content surfaces (contrast hazard), stock 3D blob illustrations, emoji as feature icons, fake testimonials/logos, drop-shadowed everything.
- Details that signal craft: real `::selection` color, custom focus ring matching brand, designed scrollbars where appropriate, correct typographic quotes (“” not ""), non-breaking spaces before units, hover states that were *decided* (not `opacity: .8`).
- BUT: distinctiveness never outranks usability. A boring accessible form beats a memorable broken one. Spend personality on marketing/landing/empty states; keep product surfaces calm — identity there comes from type, spacing rhythm, and motion feel, not decoration.

**Named directions that work** (pick one, commit fully — half-committed styles read as accidents):

- *Editorial*: serif display + grotesque body, generous measure, rules/hairlines, restrained
  palette, asymmetric grids. For content-led products.
- *Technical/dense*: mono or near-mono accents, borders-first depth, tight radii (2–4px), data
  tables as first-class citizens, dark-mode-primary. For dev/infra tools.
- *Soft-depth*: layered shadows, larger radii (12–16px), warm neutrals, friendly type with real
  weight contrast. For consumer/prosumer.
- *Brutalist-lite*: high contrast, oversized type, visible structure, minimal ornament — only
  with strong typographic skill; it amplifies both craft and its absence.

Whatever the direction: contrast math, focus rings, and state coverage are identical. Style is
the skin over the same non-negotiable skeleton.

## 7. Density & audience calibration

- Pick a density target per product area and tokenize it: consumer/marketing (line-height 1.6, 16–18px base, generous `--space-section`), productivity default (1.5, 14–16px controls, 8px rhythm), data-dense pro tools (1.4, 13–14px, 4px rhythm, more borders — borders-first depth language).
- Density is a token-level switch (`[data-density="compact"]` remaps space/control-height tokens), not per-screen overrides.
- Tables for pro tools: row height 32–40px compact / 44–52px comfortable, right-aligned numerics, sticky header, row hover, and column alignment consistent with content type.

## 8. Content design (microcopy is UI)

- Buttons say what they do: "Save changes", "Create project" — never "Submit", "OK", "Yes". Verb + object.
- Sentence case for UI text (Title Case Is Harder To Read And Looks Shouty); no ALL CAPS except short eyebrow labels with letter-spacing (rules/01 §2).
- Error/empty/confirmation copy: plain language, no blame ("Couldn't save — check your connection", not "Error 500: request failed"), and the next step always stated (rules/04 §5–6).
- Numbers: localize formats, tabular figures in columns, units stated, relative time ("2h ago") with absolute on hover/title.
- Truncation is a decision: `line-clamp` with full text reachable (title/tooltip/detail view); never truncate the disambiguating part (end of similar filenames — middle-truncate those).

## 9. Screen archetypes: hierarchy recipes

**Landing/hero:** one headline (display scale, ≤ 12 words), one subline (secondary color, ≤ 2
lines), one primary CTA + at most one ghost secondary. Social proof below the fold-line, muted.
Hero media supports, never competes — if the screenshot is the message, the headline shrinks.
Above-the-fold answers in 5 seconds: what is it, who is it for, what do I do next.

**Dashboard:** lead with the 1–3 numbers that answer "is everything OK?" (large, tabular,
trend-annotated with direction + color + arrow — not color alone). Charts below, tables last.
Every metric links to its drill-down. Resist the symmetric-grid-of-equal-cards trap: equal visual
weight implies equal importance, which is never true — size cards by decision value.

**Settings:** grouped by user task, search above ~20 settings, current value always visible in
collapsed state, destructive zone separated at the bottom with its own visual treatment. Changes
save explicitly with confirmation, or autosave with visible "Saved" status — never ambiguous.

**Detail/record view:** title + status + primary action pinned in header; metadata in a quiet
key-value block (labels `--text-secondary`, values primary); related content in tabs only when
> 2 sections, otherwise stacked with headings.

**Pricing:** ≤ 4 tiers, recommended tier visually elevated (one level — border + badge, not a
circus), feature list aligned across tiers (subgrid, rules/02 §2), prices in display type with
tabular figures, billing-period toggle adjacent to prices.

## 10. Imagery, illustration & data-viz craft

- Photography: one treatment (duotone, consistent grade, or none) — mixed stock styles read as
  template. Faces look toward content, not off-page. Always `aspect-ratio` + `object-fit: cover`
  + meaningful `alt` (rules/05 §5).
- Illustration: one style family, colors drawn from the system ramps (re-color vendor
  illustrations to brand tokens — default-purple unDraw is a kill-list item).
- Gradients, when used: 2 stops of *adjacent* hues (or one hue, two lightness steps) in OKLCH —
  `linear-gradient(in oklch, …)` avoids the gray dead-zone of sRGB interpolation. Never gradient
  body text; gradient on display headline only as a deliberate signature, with solid fallback
  meeting contrast.
- Charts: max 6 series before grouping; color-blind-safe ordered ramp (verify deuteranopia +
  grayscale print); direct line labels over legends; y-axis from zero for bar charts (always),
  truncation allowed for lines with explicit axis labels; gridlines `--border-subtle`; tooltips
  keyboard-reachable and the data available as table/text alternative (rules/05).
- Empty/placeholder art is restrained: small, monochrome-ish, never larger than the message + CTA.

## 10b. Deceptive patterns: auto-fail list

Visual/UX choices that exploit users fail the audit regardless of craft (and increasingly fail
the law — FTC, DSA, GDPR consent rulings):

- **Confirmshaming**: decline option worded as self-insult ("No thanks, I hate saving money").
- **Misdirection weighting**: the business-preferred option styled primary while the user-neutral
  option is hidden as low-contrast text ("Accept all" button vs "manage preferences" link is the
  canonical consent-banner violation — equal prominence required).
- **Fake urgency/scarcity**: countdowns that reset, "3 left!" without inventory truth.
- **Roach motel**: one-click subscribe, support-call cancel. Cancellation parity is law in
  multiple jurisdictions now.
- **Preselected upsells** sneaked into flows; **disguised ads** styled as content/UI.
- **Visual interference on destructive consent**: making "Delete my data" look disabled, or
  swapping button positions mid-flow so muscle memory misfires.

These rate **Critical** in audit findings (trust/legal exposure), Blocker when they gate consent
or cancellation.

## 11. Visual QA: the recurring pixel bugs

The defects that survive code review because they need eyes, not grep:

- **Misalignment by 1–4px**: icon not optically centered in its button; label baseline off from
  adjacent input text; card grids where one column is 1px wider (fractional rounding — prefer
  `fr` units and `gap` over percentage + margin math).
- **Inconsistent paddings between sibling components** (button 12/16, adjacent input 10/14):
  control-height token (`--control-h`) + centered content fixes the class of bug.
- **Text overflow unhandled**: usernames/emails breaking layouts; missing `min-width: 0` on flex
  children (the #1 cause of "ellipsis doesn't work").
- **Focus/hover states clipped** by `overflow: hidden` parents — outline-offset needs room;
  test focus on first/last items in scrollable containers.
- **Image aspect distortion**: missing `object-fit: cover` when dimensions are constrained.
- **Dark-mode leftovers**: hardcoded white shadows, light-only logos, un-themed scrollbars/
  selection, `<img>` with white background on transparent-expected assets.
- **Zoom/loupe pass**: review key screens at 200% screenshot zoom; sub-pixel borders
  (`0.5px`), blurry icons (non-integer sizing), and gradient banding show up immediately.

## 12. Audit rubric (visual quality grading)

Score each dimension 1–5 when a holistic verdict is requested; below 3 on any dimension
generates findings:

| Dimension | 5 looks like |
|---|---|
| Hierarchy | Blur test passes every screen; one primary per view; scan order matches task order |
| Consistency | Token-clean greps; drift counts within budget (≤ 8 sizes / ≤ 4 radii / ≤ 3 shadows) |
| Spacing/rhythm | 4/8 grid throughout; proximity grouping correct; heading asymmetry right |
| Craft details | Optical alignment, icon discipline, microtypography, designed states (incl. focus/selection) |
| Distinctiveness | ≥ 3 identifiable decisions; no kill-list items; coherent named direction |
| Robustness | Worst-case content, both themes, 320px–4K, RTL all hold |

## 13. Build vs audit calibration

**Building**: lock global decisions first (type pair + scale, color ramps, space scale, radius,
depth language, density) as tokens — *then* build screens. Retro-fitting a system onto 40 ad-hoc
screens costs 10× more. Design the worst-case screen early (longest names, 0 items, 10k items,
German strings) — pretty averages hide broken extremes.

**Auditing**: screenshot key screens and grade against this file: blur test for hierarchy; count
distinct font sizes (> 8 = scale erosion), radii (> 4 = drift), shadow styles (> 3 = drift), grays
(> 10 = no ramp); check icon family consistency; identify the depth language (or absence); flag
generic-template signals from §6. Visual drift findings are **Major** when they break component
reuse/consistency, **Minor** when cosmetic.

## Audit checklist

- [ ] Each screen has one identifiable primary action; squint/blur test preserves title + CTA; secondary content visibly de-emphasized
- [ ] Text hierarchy levels differ by ≥ 2 cues; adjacent sizes ≥ ~20% apart; no 1px-difference pseudo-hierarchy
- [ ] Grouping by proximity; ≤ 2 levels of bordered containment; all elements aligned to the grid (no mixed center/left in a region); table numerics right-aligned + tabular
- [ ] One depth language applied consistently; shadows tokenized, two-layer, y > blur logic; dark mode re-tokenizes borders/elevation
- [ ] One icon family/stroke/grid; icon-only buttons rare + tooltipped + labeled; radius scale ≤ 4 values, nested radii = outer − gap
- [ ] No generic-template kill-list items (gradient hero default, glow shadows, glassmorphism content, emoji icons); ≥ 3 deliberate brand decisions identifiable (type, hue, signature element)
- [ ] Distinctiveness spent on marketing/empty surfaces; product surfaces calm and consistent
- [ ] Density tokenized and consistent per area; data tables meet row-height/alignment standards
- [ ] Microcopy: verb+object buttons, sentence case, blame-free errors with next step, localized numbers, intentional truncation
- [ ] Drift counts within budget: ≤ 8 font sizes, ≤ 4 radii, ≤ 3 shadows, grays from one ramp; worst-case content (long/empty/huge) renders correctly
- [ ] Whitespace: section rhythm generous and tokenized; heading spacing asymmetric (closer to its content); padding scales with container
- [ ] Screen archetypes follow their hierarchy recipes (hero: one CTA; dashboard: lead metrics sized by value; settings: task-grouped with visible save state)
- [ ] Pixel pass clean: no 1px misalignments, `min-width: 0` on truncating flex children, focus rings unclipped, images `object-fit` correct, no dark-mode leftovers at 200% zoom
- [ ] Charts/imagery: one photo/illustration treatment, OKLCH-interpolated gradients only, color-blind-safe series, bar charts zero-based, data has text alternatives
