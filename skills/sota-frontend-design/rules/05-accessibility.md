# 05 — Accessibility (WCAG 2.2 AA Floor)

WCAG 2.2 AA is the legal and ethical floor (EAA in force since June 2025 — national enforcement
and fines now active across EU member states, with EN 301 549 being updated to incorporate
WCAG 2.2; ADA Title II deadlines extended to April 2027/2028 by DOJ interim final rule, Apr 2026 —
its standard is WCAG 2.1 AA, so building to 2.2 AA exceeds it). WCAG 3.0 remains a Working Draft (March 2026 draft;
Recommendation not expected before ~2028) — informative only, never the conformance target.
Build to 2.2 AA by default; treat select AAA criteria (focus appearance, target size 44px) as
the quality bar. Automated tools catch ~30–40% of issues — the rest is semantics, keyboard, and
screen-reader verification.

## 1. Semantic HTML first; ARIA is a last resort

The First Rule of ARIA: don't use ARIA if a native element does the job. Native elements ship
keyboard handling, states, and AT mappings for free; ARIA only *claims* behavior — you must then
implement every bit of it.

```html
<!-- BAD: div soup — announces nothing, no keyboard, no states -->
<div class="btn" onclick="save()">Save</div>
<div class="checkbox" data-checked="false"></div>

<!-- GOOD: free behavior, free semantics -->
<button type="button" onclick="save()">Save</button>
<input type="checkbox" id="t"><label for="t">Subscribe</label>
```

- Landmark structure on every page: one `<main>`, `<nav>` (labeled if multiple), `<header>`, `<footer>`; content lives inside landmarks.
- Heading outline: exactly one `<h1>`, no skipped levels, headings describe sections (screen-reader users navigate by headings more than anything else). Style with classes, never pick heading level for its font size.
- Lists are `<ul>/<ol>` (AT announces count/position); tables are `<table>` with `<th scope>` — never CSS-grid-as-table for data.
- Buttons do actions, links go places: `<a href>` navigates, `<button>` mutates. A `<div role="button">` requires `tabindex="0"` + Enter + Space handlers + disabled semantics — i.e., a worse `<button>`.
- "No ARIA is better than bad ARIA": incorrect ARIA actively breaks AT (WebAIM Million: pages **with** ARIA average more errors than pages without).

## 2. ARIA, when actually needed

Legitimate uses: live regions, composite widgets with no native equivalent (tabs, combobox, tree),
`aria-expanded`/`aria-controls`/`aria-current`/`aria-selected` state wiring, accessible names for
icon-only controls.

- Follow the **WAI-ARIA Authoring Practices (APG)** pattern verbatim — roles, properties, AND the full keyboard model. Half a pattern (role without keyboard) is worse than none.
- Accessible-name rules: visible text > `aria-labelledby` > `aria-label`. Icon-only buttons MUST have one (`<button aria-label="Close">`). Name must contain the visible label text (2.5.3 Label in Name — voice-control users speak what they see).
- `aria-hidden="true"` never on focusable elements or their ancestors; decorative SVGs get `aria-hidden="true" focusable="false"`, informative ones get `role="img"` + title/label.
- `aria-expanded` lives on the trigger, not the panel. `aria-controls` is nice-to-have; `aria-expanded` is mandatory for disclosure widgets.
- Don't override native semantics (`<button role="link">` smell); don't sprinkle `role="application"`/`aria-live` broadly — both hijack AT behavior.

## 2b. Recipe: the three widgets that cause 80% of ARIA bugs

**Disclosure / accordion** — trigger is a real button inside the heading:

```html
<h3><button aria-expanded="false" aria-controls="sect1">Shipping details</button></h3>
<div id="sect1" hidden>…</div>
<!-- JS: toggle hidden + aria-expanded. That's the whole pattern. -->
```

**Tabs** — roving tabindex, arrows switch, Tab leaves the tablist:

```html
<div role="tablist" aria-label="Settings">
  <button role="tab" aria-selected="true" id="t1" aria-controls="p1">General</button>
  <button role="tab" aria-selected="false" id="t2" aria-controls="p2" tabindex="-1">Billing</button>
</div>
<div role="tabpanel" id="p1" aria-labelledby="t1" tabindex="0">…</div>
```

Arrow Left/Right moves + selects (or moves + Enter activates — pick one model and document it);
panel gets `tabindex="0"` when it has no focusable content.

**Modal dialog** — use the platform:

```html
<dialog aria-labelledby="dlg-title">
  <h2 id="dlg-title">Rename project</h2> …
</dialog>
<script>
  trigger.onclick = () => dlg.showModal();   // traps focus, Esc works, top layer, ::backdrop
  dlg.onclose = () => trigger.focus();        // restore focus explicitly for older engines
</script>
```

Custom (non-`<dialog>`) modals must implement: `role="dialog"` `aria-modal="true"`, labelled,
focus-in on open, full trap, Esc, restore on close, background `inert`. If that list isn't fully
implemented, it's a Blocker — use `<dialog>`.

## 3. Keyboard navigation & focus management

Everything operable by mouse is operable by keyboard (2.1.1), with **no traps** (2.1.2) and visible
focus (2.4.7 — now effectively strengthened by 2.4.11 Focus Not Obscured).

Core model:

- `Tab`/`Shift+Tab` between widgets; arrow keys **within** composite widgets (tabs, menus, radio groups, grids) using roving `tabindex` (active item `0`, rest `-1`) or `aria-activedescendant`.
- `Enter`/`Space` activate; `Esc` closes/dismisses; `Home`/`End` jump within lists. Implement per APG table for the widget.
- DOM order = visual order = tab order. Never reorder visually with CSS (`order`, absolute positioning) in ways that scramble tab flow (2.4.3 Focus Order). `tabindex` > 0 is banned.
- Skip link first-focusable on every page (`<a href="#main" class="skip-link">Skip to content</a>`), visible on focus (2.4.1).

**Focus visibility:**

```css
/* GOOD: visible, contrasting, only for keyboard/modality-appropriate input */
:focus-visible { outline: 2px solid var(--focus-ring); outline-offset: 2px; }
:focus:not(:focus-visible) { outline: none; }

/* BAD: the single most common a11y crime */
*:focus { outline: none; }
```

Ring: ≥ 2px, 3:1 contrast against adjacent colors, offset so it's not swallowed by the component;
must not be hidden under sticky headers/footers (2.4.11) — `scroll-padding` fixes this.

**Focus management on state change:**

- Opening a dialog → focus moves into it (first sensible element, or the dialog itself with `tabindex="-1"`); focus is **trapped** while open; closing → focus **returns to the trigger**. Native `<dialog>.showModal()` + the `inert` attribute on background give you trap + restore cheaply — prefer them.
- Deleting an item → focus moves to the next item (or list container), never silently to `<body>`.
- SPA route change → move focus to the new view's `<h1>` (tabindex="-1") or a skip target, and update `document.title`. Silent route swaps strand screen-reader users.
- Content revealed by interaction (accordion, "show more") → focus stays on trigger with `aria-expanded` flipped; content inserted *before* current focus is a trap risk.

## 4. Forms, errors, and live regions

(Forms UX in rules/04; here, the AT wiring.)

- Label every control (1.3.1/3.3.2); group with fieldset/legend; required state via `required`/`aria-required`, communicated in the label too.
- Errors: `aria-invalid="true"` + message linked by `aria-describedby`; identified in text (3.3.1), with suggestion (3.3.3). On submit, focus the first error.
- Status messages that don't take focus use live regions (4.1.3):

```html
<!-- Region must exist in DOM BEFORE content changes, or it won't announce -->
<div role="status" aria-live="polite" class="sr-only" id="announcer"></div>
<script>announcer.textContent = `${results.length} results found`;</script>
```

- `role="status"`/`aria-live="polite"` for results counts, autosave, toasts; `role="alert"` (assertive) strictly for errors needing immediate attention. Assertive-everything trains users to ignore announcements.
- Loading regions: `aria-busy="true"` during fetch; announce completion ("Loaded 24 items") rather than relying on visual skeletons.
- WCAG 2.2 specifics: **3.3.8** no cognitive-function tests for login (allow paste, support password managers, offer email/passkey over puzzles); **3.3.7** don't ask users to re-enter info already provided in the same flow.

## 5. Visual & motion criteria (cross-references)

- Contrast: text 4.5:1, large 3:1, UI/graphics 3:1 — full math in rules/01 §5. Both themes.
- Reflow at 320px / 400% zoom without 2-D scrolling (1.4.10); text spacing survives override (1.4.12) — rules/01–02.
- `prefers-reduced-motion` honored everywhere; no flashing > 3/sec (2.3.1) — rules/06.
- Target size 24px minimum + spacing (2.5.8 AA), 44px build standard — rules/04 §8.
- Never `user-scalable=no`; orientation not locked (1.3.4); content works in portrait and landscape.
- Autoplaying moving content > 5s gets pause/stop/hide (2.2.2); audio > 3s gets volume/stop (1.4.2). Carousels: pause control, no focus theft on rotate.
- Media: captions for video (1.2.2), transcripts for audio; `alt` on every `<img>` — descriptive for informative, `alt=""` for decorative, never filename. Alt text conveys *purpose in context*, not pixel description.

## 5b. WCAG 2.2 delta — the criteria added since 2.1

These are the ones audits now fail on because checklists predate them:

| SC | Level | Requirement |
|---|---|---|
| 2.4.11 Focus Not Obscured (Min) | AA | Focused element not *entirely* hidden by sticky headers/footers/cookie banners — `scroll-padding` + banner audit |
| 2.5.7 Dragging Movements | AA | Every drag (reorder, slider, kanban, map pan) has a single-pointer non-drag alternative |
| 2.5.8 Target Size (Minimum) | AA | 24×24px targets, or equivalent spacing; inline-text links exempt |
| 3.2.6 Consistent Help | A | Help mechanism (chat, contact, FAQ) appears in the same relative place on every page |
| 3.3.7 Redundant Entry | A | Don't ask for the same info twice in one flow — auto-populate or offer "same as above" |
| 3.3.8 Accessible Authentication (Min) | AA | No cognitive test to log in: allow paste & password managers, offer OTP/passkey/magic-link instead of transcription puzzles; CAPTCHA needs alternatives |

(2.4.13 Focus Appearance and 2.5.5 Target Size 44px are AAA — our build standards anyway.)

## 5c. Content accessibility: links, language, structure

- Link text stands alone: "View billing settings", never "click here"/"learn more" ×7 (2.4.4;
  SR users pull a links list out of context). Same visible text → same destination (3.2.4).
- `lang` on `<html>` (3.1.1) and on inline foreign-language spans (3.1.2) — wrong lang makes SR
  pronounce gibberish and breaks hyphenation.
- Data tables: `<caption>`, `<th scope="col|row">`; complex tables get `headers`/`id`; layout
  tables don't exist anymore — if it's not data, it's CSS.
- `<title>` unique per page/view (2.4.2), most-specific-first ("Invoices — Acme Billing").
- Reading order in DOM = visual order (1.3.2); CSS `order`/grid placement must not contradict it.
- Text in images banned for UI (1.4.5) — real text styles, scales, translates, and theme-switches.
- Don't communicate by sensory characteristics alone ("click the green button on the right",
  1.3.3); reference labels.
- Autocomplete/identity inputs carry `autocomplete` tokens (1.3.5 — also a UX win, rules/04 §2).

## 6. Screen reader testing approach

Automated (axe-core/Lighthouse/WAVE) in CI on every story/page — then manual, because automation
can't judge name quality, focus logic, or announcement timing.

Minimum manual matrix (covers ~90% of AT usage):

| Screen reader | Browser | Platform |
|---|---|---|
| NVDA | Chrome/Firefox | Windows (largest desktop share) |
| VoiceOver | Safari | macOS + iOS (test mobile!) |
| TalkBack | Chrome | Android |
| (Enterprise) JAWS | Chrome | Windows |

Test script per flow: (1) navigate by headings (H key) and landmarks — does the page outline make
sense? (2) Tab through — is every interactive element reachable, named, and state-announced
("Save, button", "Notifications, toggle, on")? (3) Complete the core task eyes-closed — forms,
errors, dialogs, confirmation. (4) Trigger async states — do loads/results/errors announce?
If you can't finish the task with the display off, ship is blocked.

Also test: keyboard-only (no SR), 200% browser zoom, Windows High Contrast (`forced-colors`),
and voice control (Label-in-Name check) on critical flows.

**Tooling tiers (use all three):**

1. **CI/automated**: axe-core (jest-axe / @axe-core/playwright on stories and key pages),
   eslint-plugin-jsx-a11y (catches at author time), Lighthouse a11y budget in CI. Treat new
   violations as build failures; baseline existing debt explicitly.
2. **Assisted manual**: browser a11y tree inspector (verify computed name/role/state — the
   single fastest ARIA debugging tool), WAVE/Accessibility Insights guided walkthroughs, contrast
   pickers over the token matrix (rules/01 §6b).
3. **Human**: the SR matrix above, keyboard passes, and — for products with a11y as a real
   requirement — paid testing with disabled users; nothing substitutes.

## 7. Common audit failures, ranked

By frequency × user impact (WebAIM Million + field experience) — use as triage order:

1. **Low-contrast text** (~80% of sites) — Level AA 1.4.3. High impact, trivial fix.
2. **Missing accessible names**: icon buttons, inputs without labels, links that say "click here"/"learn more" (1.1.1, 1.3.1, 2.4.4, 4.1.2). Blocks task completion outright.
3. **Keyboard inoperability / invisible focus**: div-buttons, `outline: none`, hover-only menus, focus traps in custom widgets (2.1.1, 2.4.7). Blocker-severity.
4. **No focus management** in SPAs/dialogs: focus lost on route change, not trapped/restored in modals (2.4.3). Blocker for SR/keyboard users.
5. **Broken ARIA**: states never updated (`aria-expanded` stuck), invalid role nesting, `aria-hidden` on focused content (4.1.2).
6. **Form errors not conveyed**: color-only invalid state, error text not linked, no focus move (3.3.1–3.3.3).
7. **Missing/wrong alt text** and unlabeled images of text (1.1.1, 1.4.5).
8. **Heading/landmark chaos**: no `<main>`, skipped levels, everything-is-a-div (1.3.1).
9. **Motion violations**: no reduced-motion handling, autoplaying carousels without pause (2.2.2, 2.3.3).
10. **Zoom/reflow breakage**: `user-scalable=no`, fixed-height clipping at 200%, 2-D scroll at 320px (1.4.4, 1.4.10).

## 8. Severity mapping for findings

Rank accessibility findings by **WCAG level × task impact**, not by effort:

- **Blocker**: Level A failure that prevents task completion for an AT/keyboard user (keyboard trap, unlabeled required input, focus-invisible checkout button, SR-silent error). Ship-stopping.
- **Critical**: Level A/AA failure with major degradation but a workaround exists (missing landmarks but headings OK, contrast 3.8:1 body text, dialog without focus return).
- **Major**: AA failure with moderate impact or limited scope (one icon button unnamed in a secondary flow, target 20px, reflow break on one page).
- **Minor**: AAA/best-practice gap or polish (focus ring thin but present, alt text terse, 24px targets where 44 is the standard).

A Level A violation on a core flow is never "Minor" because the fix is small — severity tracks the
user locked out, not the diff size.

## Audit checklist

- [ ] Native elements used (button/a/input/select/dialog/details); zero click-handler divs; landmarks + single h1 + unbroken heading levels
- [ ] All ARIA matches APG patterns completely (role + properties + keyboard); states actually update; no aria-hidden on focusables; icon controls named; visible label ⊆ accessible name
- [ ] Dialogs are `<dialog>`/showModal (or implement the full custom contract); disclosure and tabs follow the §2b recipes exactly
- [ ] WCAG 2.2 delta verified: focus not obscured by sticky chrome, drag alternatives, 24px targets, consistent help placement, no redundant entry, paste-friendly auth
- [ ] Link text self-describing; `lang` set (incl. inline switches); data tables have caption + scoped headers; unique titles; DOM order = reading order; no text-in-images
- [ ] Full keyboard pass: everything reachable/operable, logical order, no traps, no `tabindex>0`, skip link present, Esc closes overlays
- [ ] `:focus-visible` ring ≥ 2px at 3:1, never obscured by sticky chrome; `outline: none` only with replacement
- [ ] Dialogs: focus moved in, trapped (inert/showModal), restored to trigger; SPA route changes move focus + update title; deletions relocate focus
- [ ] Forms: labels, fieldsets, aria-invalid + describedby errors, focus-first-error, no cognitive-test logins, paste allowed
- [ ] Live regions pre-mounted, polite by default, alert only for errors; async loads announce completion
- [ ] Contrast verified both themes (text 4.5:1, UI 3:1); 320px/400% reflow clean; text-spacing survives; no user-scalable=no
- [ ] Reduced motion honored; autoplay > 5s pausable; nothing flashes > 3/sec; captions/transcripts/alt complete
- [ ] axe clean in CI AND manual pass: NVDA+Chrome, VoiceOver+Safari (incl. iOS), keyboard-only, 200% zoom, forced-colors — core task completable eyes-closed
