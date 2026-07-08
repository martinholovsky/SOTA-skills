# 03 — Design Systems, Tokens & Component APIs

A design system is an API contract, not a Figma file. Quality is measured by: can a product team
build a correct, accessible, on-brand screen *without* talking to the design-system team?

## 1. Design tokens: three tiers, W3C format

Token architecture (each tier references only the tier below):

1. **Primitive / global**: raw values — `color.blue.600`, `space.4`, `font.size.300`. No opinions.
2. **Semantic / alias**: meaning — `color.bg.accent`, `color.text.danger`, `radius.interactive`. *This is the public API.*
3. **Component** (optional, sparingly): `button.bg`, `card.padding` — only when a component must be themed independently.

- Author in the **W3C Design Tokens format** (`*.tokens.json`, `$value`/`$type`/`$description`, aliases via `{color.blue.600}`) — the DTCG spec reached its first stable release (2025.10, Oct 2025): theming, modern color spaces, and cross-tool interop are now standardized, and Figma imports/exports variables natively in this format. Compile with Style Dictionary v5 (v5.3+ handles the 2025.10 structured color/dimension value formats; v4 supports only the pre-stable DTCG draft) to CSS custom properties, TS constants, and native platform outputs. One source of truth, generated everywhere.

```jsonc
// GOOD: tokens.json (DTCG) — typed, aliased, themable
{
  "color": {
    "blue": { "600": { "$type": "color", "$value": "oklch(0.55 0.18 255)" } },
    "bg": { "accent": { "$type": "color", "$value": "{color.blue.600}" } }
  },
  "duration": { "fast": { "$type": "duration", "$value": "150ms" } }
}
```

```css
/* BAD: values invented inline; "system" exists only in a wiki page */
.button-primary { background: #2463eb; border-radius: 6px; padding: 9px 14px; }
```

- Components consume **semantic tokens only**. Grep test: a hex/px literal or a primitive token (`--blue-600`) inside a component file is a defect.
- Theming = swapping the semantic layer (per `[data-theme]`, brand, density). If a theme needs to touch components, the semantic vocabulary is too thin — add tokens (`--surface-overlay`, `--text-on-accent`), don't fork CSS.
- Token count discipline: every token must answer "when do I use this instead of its neighbor?" If `--gray-450` exists because one screen wanted it, delete it.

## 1b. Token naming & governance

Name = `[domain].[concept].[variant].[state]`, read left-to-right from general to specific:
`color.bg.accent.hover`, `color.text.danger`, `space.4`, `radius.interactive`,
`shadow.overlay`, `duration.fast`, `font.size.300`.

- Use **role words**, not appearance words, at the semantic tier: `bg.accent` not `bg.blue`;
  `text.danger` not `text.red-600`. Appearance names break the first time the brand color changes
  or a second theme lands.
- Reserve a small, closed vocabulary and reuse it everywhere: `bg / fg|text / border / icon` ×
  `default / muted / subtle / accent / danger / warning / success / info` × `hover / active /
  selected / disabled`. New words require review — vocabulary sprawl is how systems rot.
- Pair tokens that must travel together: every `*.bg` has a matching `*.fg` (e.g.
  `color.bg.accent` + `color.fg.on-accent`) so contrast is preserved by construction; components
  always use the pair, never mix-and-match.
- Governance: tokens change via PR to the tokens package (not inline app overrides), with visual
  regression run against all themes; additions need a usage justification; telemetry/grep before
  deletion.

## 2. Component API: composition over configuration

Props multiply; children compose. When a component grows boolean/enum props that reorder or inject
content, switch to compound components.

```tsx
// BAD: configuration explosion — every new need = new prop, all consumers rebuild
<Card title="Plan" subtitle="Pro" icon={<Zap/>} actionLabel="Upgrade"
  onAction={fn} footerAlign="right" hideDivider compact />

// GOOD: composition — layout/content decided by the consumer, slots are explicit
<Card>
  <Card.Header icon={<Zap/>}>Plan <Card.Eyebrow>Pro</Card.Eyebrow></Card.Header>
  <Card.Body>…</Card.Body>
  <Card.Footer><Button onClick={fn}>Upgrade</Button></Card.Footer>
</Card>
```

API rules:

- **Spread the rest**: forward `...rest` to the underlying DOM node, merge (don't clobber) `className`/`style`, and forward `ref`. A component that swallows `data-testid`, `aria-*`, or event handlers is broken.
- Variants as a closed set (`variant="primary" | "secondary" | "ghost"`, `size="sm" | "md" | "lg"`), styled via data attributes (`data-variant="primary"`) or a variant utility (CVA-style) — not className string math.
- No boolean prop pairs that can contradict (`primary` + `secondary`); one enum.
- An `asChild`/`render` escape hatch (Radix pattern) so a Button can render as `<a>` or a router Link without prop forwarding gymnastics.
- Naming: events `onVerb` (`onOpenChange`, not `onToggled`); state props are nouns (`open`, `value`); past-tense booleans banned.
- Polymorphism only where semantics demand (`as="h2"` on Heading); don't make everything polymorphic — it wrecks type inference and invites `<div as="button">`-grade misuse.

## 3. Controlled / uncontrolled: support both

Every stateful component (input, dialog, accordion, tabs, combobox) implements the trio:
`value` (controlled) / `defaultValue` (uncontrolled) / `onValueChange` (always fired).

```tsx
// GOOD: useControllableState pattern
function Tabs({ value: valueProp, defaultValue, onValueChange }) {
  const [internal, setInternal] = useState(defaultValue);
  const isControlled = valueProp !== undefined;
  const value = isControlled ? valueProp : internal;
  const setValue = (next) => { if (!isControlled) setInternal(next); onValueChange?.(next); };
  …
}
```

- Never flip between modes mid-life (React warns for a reason): `undefined` means uncontrolled forever; controlled components must always receive a value.
- Same contract for open state: `open` / `defaultOpen` / `onOpenChange` — this is the de-facto standard signature (Radix, Base UI, Ark); deviating costs adopters real confusion.

## 4. State completeness: the 9-state contract

A component is not done when the happy path renders. Every interactive component ships ALL of:

| State | Requirement |
|---|---|
| Default | — |
| Hover | `@media (hover: hover)` guarded; never the only affordance |
| **Focus-visible** | 2px+ ring, 3:1 contrast, ≥2px offset; NEVER `outline: none` without replacement |
| Active/pressed | Distinct from hover (translate/darken); `aria-pressed` where toggle |
| Disabled | Visually muted AND `disabled`/`aria-disabled`; prefer aria-disabled + blocked handler when the control should stay focusable/explainable (tooltip "why") |
| Loading | In-place spinner/progress, width-stable (don't collapse the button), `aria-busy`, repeat-click guarded |
| Error/invalid | Border + icon + message (not color alone), `aria-invalid` + `aria-describedby` |
| Empty | Real designed state (see rules/04), never blank or raw "No data" |
| Skeleton/placeholder | Matches final layout dimensions (no CLS on arrival) |

Data-bearing views additionally: loading / error-with-retry / empty / partial / ideal — the five UI states. An audit that finds only "ideal" implemented files a finding per missing state.

- Async buttons: keep label visible or swap to spinner of identical box size; disable re-submit; restore focus context after resolution.
- States stack: a focused+hovered+invalid input must look coherent — test combinations, not just singles.

## 5. Headless + styled layers

Separate **behavior** (state machine, ARIA, keyboard, focus) from **skin** (tokens, CSS).

- Default choice: build on a maintained headless library — **Radix UI / Base UI, React Aria, Ark UI (Zag)**, or native elements (`<dialog>`, `popover`, `<details>`) — and style with your tokens. Hand-rolling combobox/dialog/menu keyboard+ARIA behavior is weeks of work and the top source of a11y audit findings.
- If you must own behavior, isolate it in hooks (`useDialog`, `useListNavigation`) with zero styling imports, so skins are swappable and behavior is testable headlessly.
- Expose state as **data attributes** for styling: `data-state="open"`, `data-disabled`, `data-invalid` — CSS keys off these, not class permutations:

```css
.accordion-content[data-state="open"] { /* … */ }
.input[data-invalid] { border-color: var(--border-danger); }
```

- Web-component contexts: same split — logic in the element, themable surface via `::part()` + custom properties.

## 5b. Styling strategy & encapsulation

Pick one styling approach per system and enforce it; mixing three is the real problem:

- **Tailwind v4+**: fastest iteration; map the config to the token source (CSS-first config
  consuming the generated custom properties) so utilities ARE tokens; extract repeated
  utility strings into components, not `@apply` soup. Arbitrary values (`p-[13px]`) are the
  token-violation grep target.
- **CSS Modules / vanilla-extract / plain CSS + layers**: best for long-lived systems; component
  styles key off data attributes; tokens via custom properties; zero runtime.
- **Runtime CSS-in-JS** (styled-components/emotion): avoid for new systems — runtime cost,
  RSC/streaming friction. Zero-runtime compiled variants (vanilla-extract, Panda) are the
  acceptable successors.

Regardless of approach:

- Component owns its internals; **public theming surface is custom properties** (and `::part()`
  for web components): `--button-bg`, documented, stable. Consumers never reach into internal
  class names — that's the encapsulation contract that makes refactors safe.
- Specificity stays flat (single class / `:where()` wrappers); overrides happen via the
  documented variables, layers handle the rest (rules/02 §6).
- TypeScript: variant props derived from a single source (`VariantProps<typeof button>` with CVA
  or equivalent) so types, styles, and docs can't drift; discriminated unions for mutually
  exclusive prop sets (`{ href } | { onClick }`).

## 6. Isolation-first development (Storybook discipline)

- Every component is built and reviewed **in isolation** (Storybook/Ladle/Histoire) before it lands in a page. If it only works inside one page's context, it isn't a component.
- One story per meaningful state (the 9-state contract above), plus a "kitchen sink" story with overflowing text, 0 items, 10k items, RTL, dark theme, and `prefers-reduced-motion`.
- Stories are test fixtures: run axe (a11y addon) and visual regression (Chromatic/Playwright screenshots) against them in CI. A state without a story is a state without a test.
- Long-content stories are mandatory: German strings (+35% length), CJK, a 40-character unbroken word, emoji. Truncation policy (`text-overflow`, `line-clamp`) is a design decision, made explicit per component.

## 6b. Accessibility is a system deliverable

A design system either makes products accessible by default or institutionalizes their failures
at scale — there is no neutral.

- Every primitive ships its APG keyboard model, name/role/state wiring, and focus behavior
  *inside* the component; consumers should have to work to make it inaccessible.
- Required-prop enforcement: `IconButton` makes `aria-label` a required TS prop; `Input` requires
  `label` (with an explicit, ugly `unsafe_labelHidden` escape so omission is always a decision).
- Contrast is guaranteed at the token layer (paired bg/fg tokens, §1b) and re-verified per theme
  in CI (automated checks over the token matrix).
- The docs' keyboard table and screen-reader behavior notes are part of the public API; a
  behavior change there is semver-major even if no TS type changed.
- System-level a11y testing: axe on every story (CI gate), keyboard tests in component
  integration tests (Tab/arrow/Esc flows), and one manual SR pass per new primitive before
  stable (rules/05 §6).

## 6c. Component API smells (audit greps)

- **Prop count > ~10** on a non-primitive: configuration creep — decompose to compound parts.
- **`Props` with `headerLeftIcon` / `footerButtonText`-style names**: slots being faked through
  config; convert to children/compound components.
- **Boolean modifiers that combine ambiguously** (`small` + `large` both settable): enum.
- **`onClick` on a non-interactive component** (Card, Row): wrap content in a real `<button>`/
  `<a>` child instead — clickable-div at the API level reproduces the div-button a11y bug for
  every consumer (rules/05 §1).
- **`style`/`className` accepted but not merged**, or `ref` not forwarded: integration paper cut
  that forces forks.
- **Copy-paste siblings** (`UserCard`, `ProjectCard`, `TeamCard` at 90% overlap): extract the
  generic compound `Card` and compose.
- **Render-prop/child-function APIs where children would do**: reserve render props for genuinely
  parameterized output (virtualized rows, downshift-style state exposure).
- **Internal state reached via `document.querySelector` from outside**: the component is missing
  a controlled mode or an imperative handle (`useImperativeHandle` sparingly, for focus/scroll
  commands only).

## 6d. Density & multi-brand theming

- Density is its own theme axis, orthogonal to color: `[data-density="compact"]` remaps the
  *control-height and space tokens* (`--control-h: 32px→28px`, `--space-row: 12px→8px`,
  `--text-control: 14px→13px`); components are written against those tokens so density is free.
  Touch devices force comfortable density regardless of setting (pointer: coarse, rules/02 §4).
- Multi-brand: brands swap the **primitive ramp assignments** feeding the same semantic tokens
  (brand A maps `accent` to its blue ramp, brand B to its green ramp) plus the few brand-shape
  tokens (radius stance, font family). If brands diverge structurally (different component
  anatomy), that's two products sharing a base layer — model it that way instead of prop-flagging
  every component.

## 7. Versioning & change discipline

- The system is a product: semver it. Renaming a prop or token is a breaking change — ship codemods or deprecation aliases (`/** @deprecated use `tone` */`) for one minor cycle.
- Deprecate tokens by aliasing old → new and logging in dev builds; delete only after usage telemetry/grep hits zero.
- Document every component with: anatomy diagram (slot names), props table, keyboard interaction table, and do/don't usage examples. The keyboard table is not optional — it's the a11y contract.

## 8. Component anatomy: the file contract

Per component, co-located (names illustrative — consistency matters, the exact convention doesn't):

```
button/
  button.tsx          # behavior + markup; consumes semantic tokens only
  button.css          # (or .module.css / variants.ts) keyed off data-attributes
  button.stories.tsx  # every state incl. worst-case content (§6)
  button.test.tsx     # interaction + axe; keyboard flows for interactive widgets
  index.ts            # public surface — ONLY what's exported here is API
```

- One component, one directory, one public export point; deep imports
  (`from "@ds/button/button.css"`) are private and break without notice — enforce via package
  `exports` map.
- Cross-component reuse goes through shared primitives/hooks, never sibling deep-imports.
- The system package ships: ESM, types, CSS as importable layer-wrapped files, tokens as both
  CSS custom properties and a typed TS object. Tree-shakeable — importing Button must not pull
  the DatePicker's dependency graph.

## Audit checklist

- [ ] Tokens exist in a source format (DTCG JSON or equivalent) and compile to all platforms; no parallel hand-maintained palettes
- [ ] Three-tier token hierarchy; components reference semantic tokens only (grep for hex/px literals and primitive-tier names in component code)
- [ ] Theming works by swapping the semantic layer; dark/brand themes contain zero component-level CSS forks
- [ ] Token names are role-based with a closed vocabulary; bg/fg tokens paired; changes flow through the tokens package with cross-theme visual regression
- [ ] One styling strategy; theming surface is documented custom properties (no consumer reaching into internal classes); no arbitrary-value utilities or `@apply` sprawl
- [ ] A11y enforced by the system: required label props on unlabeled-prone primitives, APG behavior baked in, contrast guaranteed at token layer per theme
- [ ] Component APIs: rest props spread + className/style merged + ref forwarded; closed variant enums; `asChild`/render escape hatch on interactive primitives
- [ ] Stateful components implement value/defaultValue/onChange (and open/defaultOpen/onOpenChange); no mode-switching warnings in console
- [ ] 9-state contract complete per interactive component; data views implement loading/error/empty/partial/ideal
- [ ] Buttons in async flows: width-stable loading, double-submit guarded, `aria-busy`
- [ ] Behavior comes from a headless layer (library or isolated hooks); styling keyed off data attributes
- [ ] Storybook (or equivalent) covers every state incl. overflow/RTL/dark/reduced-motion; axe + visual regression run in CI
- [ ] Keyboard interaction documented per component and matches WAI-ARIA APG patterns
- [ ] Breaking changes semver'd with deprecation path; no silent token renames
