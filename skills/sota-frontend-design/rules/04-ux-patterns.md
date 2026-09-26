# 04 — UX Patterns: Forms, States, Feedback & Flow

UX quality is mostly the unglamorous states: the error, the wait, the empty list, the fat-fingered
tap. Design those first; the happy path designs itself.

## 1. Forms: structure

- Every input has a **visible `<label>`** (programmatically associated via `for`/`id` or wrapping). Placeholder-as-label is banned: it vanishes on input, fails contrast, breaks autofill review, and screen readers lose context mid-edit.
- Labels **above** inputs (fastest scan, best for i18n and mobile); inline-left labels only in dense desktop settings panels.
- One column. Multi-column forms cause skipped fields and broken tab order. Exceptions: tightly-bound groups (city/state/zip, expiry/CVC).
- Group with `<fieldset>` + `<legend>` for radio/checkbox sets and address blocks.
- Mark **optional** fields ("(optional)"), not required ones with asterisk soup — most fields should be required; question every field's existence first. Each removed field measurably raises completion.
- Sane widths: input width signals expected content (ZIP ≈ 6ch, not full-width).

## 2. Forms: input mechanics

Always set the full attribute stack — this is free conversion and accessibility:

```html
<!-- GOOD -->
<label for="email">Email</label>
<input id="email" name="email" type="email" autocomplete="email"
       inputmode="email" autocapitalize="none" spellcheck="false" required
       aria-describedby="email-err email-hint" />

<label for="otp">Verification code</label>
<input id="otp" name="otp" inputmode="numeric" pattern="[0-9]*"
       autocomplete="one-time-code" maxlength="6" />
```

- `autocomplete` tokens per WCAG 1.3.5 (required at AA for user-data fields): `name`, `email`, `tel`, `street-address`, `postal-code`, `cc-number`, `new-password`/`current-password`, `one-time-code`, `bday`. Never `autocomplete="off"` on identity/payment fields — browsers ignore it and users hate it.
- `inputmode` controls the mobile keyboard (`numeric`, `decimal`, `tel`, `email`, `url`, `search`); `type="number"` only for true quantities (it scroll-hijacks and strips leading zeros — wrong for ZIP/OTP/card numbers).
- Password fields: show/hide toggle, no paste-blocking (paste-blocking fights password managers = security harm), `minlength` honest with policy, current vs new autocomplete distinction.
  - **Masked is the resting state.** The field ships as `type="password"` in the markup; the
    toggle is a user action that swaps it to `text` and back (an `aria-pressed` button naming
    the field), never a default of `text` or a page that remembers "shown". Revealing only the
    most recently typed character is the other acceptable reveal.
  - **Username then password, one Tab apart.** Keep the two fields adjacent in DOM and focus
    order with nothing focusable between them (no "Forgot password?" link, help icon or
    show/hide button placed before the password field): password managers and keyboard users
    both expect a single Tab to move from one to the other.
  - The no-paste-blocking rule covers the username and the MFA/OTP code field too — a code
    copied from an authenticator or an email must paste. OWASP: ASVS 5.0 V6.2.7,
    Authentication cheat sheet, Go-SCP (communicating authentication data).
- Never disable the submit button as the only validation mechanism: a disabled submit with no explanation is a dead end. Allow submit, then focus the first error.

## 2a. Internationalization-aware UX

i18n breakage is a layout *and* logic class of bug — design for it up front:

- Reserve expansion room: German/Finnish run ~+35% over English, Russian +20%; buttons, tabs,
  and nav labels must wrap or the container must grow — never `overflow: hidden` on a label.
  Worst-case strings belong in component stories (rules/03 §6).
- Never concatenate translated fragments ("You have " + n + " items") — use ICU message
  formatting with proper plural rules (Slavic languages have 3–4 plural forms).
- Locale-format everything via `Intl.*` (NumberFormat, DateTimeFormat, RelativeTimeFormat,
  ListFormat): decimal commas, date order, currency placement, first day of week.
- Name fields: single "Full name" beats first/last (many cultures don't split that way); no
  alphabetical-only validation (rejects most of the world's names).
- Phone/address: country-first, then format-specific fields; postal code is not numeric
  everywhere and not present everywhere.
- RTL covered in rules/02 §5; remember content *direction* can differ from UI *locale* —
  user-generated text gets `dir="auto"`.

## 2b. Choosing the right control

| Situation | Control |
|---|---|
| 2–5 mutually exclusive options, comparison matters | Radio group / segmented control (all visible) |
| 6+ options, one choice | `<select>` (native on mobile is unbeatable) or combobox if searchable |
| 30+ options or open vocabulary | Combobox with type-ahead, recent/frequent first |
| Multiple selections, few options | Checkbox group; many options → multi-select combobox with token chips |
| On/off taking effect immediately | Switch/toggle (label states the ON meaning) |
| On/off applied on submit | Checkbox — a switch inside a form that needs "Save" is a lie |
| Date known exactly (birthdate) | Segmented text inputs / one masked input — calendars are terrible for known dates |
| Date being chosen (booking) | Calendar picker with keyboard grid support + free-text input |
| Quantity within small range | Stepper; large range → input with `inputmode="numeric"`; never sliders for precise values |
| Slider use at all | Only for "feel" values (volume, brightness) with live preview; always pair with a numeric input |

- Native controls first on mobile (`<select>`, `<input type="date">` where UX suffices): free
  platform UI, accessibility, and muscle memory. Custom replacements must clear the full APG bar
  (rules/05) — a styled-div select that breaks iOS scroll-wheel selection is a downgrade.
- Defaults are decisions: prefill the most common/safest choice; never default-on for marketing
  consent (legal + trust); remember prior user choices.

## 3. Forms: validation timing & error recovery

**Timing — "reward early, punish late":**

- Validate a field on **blur** (first pass), not on every keystroke; once a field has erred, re-validate **on input** so the error clears the moment it's fixed.
- Never validate-on-keystroke a field the user hasn't finished (flagging "invalid email" after one typed character is hostile). CSS side: `:user-invalid`, not `:invalid`.
- On submit: validate all, move focus to the first invalid field, and (long forms) show a summary at top — links that focus each field.

**Error message contract:**

```html
<!-- GOOD: adjacent, specific, actionable, programmatically linked -->
<input id="card" aria-invalid="true" aria-describedby="card-err" … />
<p id="card-err" class="field-error">
  <svg aria-hidden="true">…</svg> Card number must be 16 digits — you entered 15.
</p>
```

- Message says **what's wrong and how to fix it** — never "Invalid input". Adjacent to the field (not toast, not only top-of-form). Icon + color + text (not color alone).
- Preserve user input on error — wiping a form on failed submit is a top-3 UX crime. Same for full-page errors: persist drafts (localStorage) for anything over ~3 fields.
- Server errors map back to fields where possible; un-mappable errors render in a focused, `role="alert"` summary with a retry path.
- Success feedback exists too: inline check on hard fields (username availability), clear post-submit confirmation.

## 4. Loading & perceived performance

Choose by expected duration:

| Wait | Pattern |
|---|---|
| < 300ms | Nothing — flashing indicators feel slower. Delay indicator ~300ms before showing |
| 0.3–2s | **Skeleton** mirroring final layout (lists, cards, pages) or inline spinner (buttons) |
| 2–10s | Skeleton/spinner + descriptive text; keep UI interactive elsewhere |
| > 10s | Determinate progress bar + step labels; allow cancel/backgrounding |

- **Skeletons over spinners** for content regions: must match real layout dimensions (zero shift on arrival), animate a gentle pulse/shimmer ≤ 1.5s cycle, and honor reduced motion (static blocks). A skeleton that doesn't match the loaded layout is worse than a spinner.
- Avoid skeleton-ception: one skeleton pass per view; if data arrives staggered, render what's ready, placeholder only the remainder.
- Show an indicator only after a ~300ms grace delay, and once shown keep it ≥ 300–500ms (min-display) — prevents the 50ms "blink" that reads as jank.
- **Optimistic UI** for high-success, low-cost mutations (like, rename, toggle, reorder, add-to-list): apply instantly, sync in background, on failure roll back AND explain via toast with retry. Never optimistic for payments, sends, deletes, or anything not cheaply reversible.
- Buttons: pending state in-place (spinner inside button, label preserved or swapped, width locked), `aria-busy="true"`, double-submit guarded at the handler not just visually.
- Stale-while-revalidate beats blank-and-spin: show last-known data with a subtle refresh indicator.

## 5. Empty, error & zero states

Empty states are onboarding surfaces, not absences. Anatomy: (1) visual (restrained), (2) one-line
explanation of what would be here, (3) **primary action to fill it** — and they differ by cause:

- **First use**: educate + CTA ("No projects yet — create your first project").
- **User-cleared** (filters/search → 0 results): say what was searched, offer "clear filters", suggest near-matches. Never the same copy as first-use.
- **Error-empty**: distinct from genuinely empty — "Couldn't load projects" + Retry. Conflating "failed to load" with "you have none" actively misleads.

Error screens/pages: plain-language what-happened, what-now (retry button, status link, support path), preserve user context/work. Error codes for support go in fine print, not headlines.

## 5b. Autosave, drafts & interruption tolerance

- Long-form input (editors, multi-step forms, settings with many fields): autosave with visible
  status ("Saving… / Saved 12:03") or explicit save with dirty-state indicator + navigation
  guard. Pick one per surface; mixing both confuses ("did my toggle save?").
- Autosave cadence: debounce 1–2s after typing stops + on blur + on visibility change
  (`visibilitychange` → flush) — tab-close is the moment that matters.
- Multi-step flows: persist per-step server-side or localStorage; returning users resume, not
  restart. Step navigation backward never destroys forward data until final submit.
- Conflict handling for collaborative edits: last-write-wins is acceptable only with a visible
  "edited by X just now" warning; silent overwrites of someone else's work is a Blocker-grade
  trust failure.
- Session expiry mid-form (WCAG 2.2.5/2.2.6 adjacent): warn before expiry, allow re-auth without
  losing entered data — re-auth-and-wipe is the worst version of this bug.
- **Idle expiry is visible, not discovered.** The server owns the idle timeout (sota-code-security
  rules/17); the client mirrors it with a timer so the user sees a countdown warning with an
  "Stay signed in" action before it lapses. When it does lapse, the client acts at once: it
  sends the same sign-out request the sign-out control sends (so the server invalidates the
  session and clears site data), removes sensitive rendered content from the DOM and in-memory
  stores, and lands on a signed-out screen that says why. Leaving an account page on screen until
  the next click fails is the bug. A form draft kept for the re-auth path above is held out of
  view and restored only after the same user signs back in. The client timer is a courtesy —
  extending it in the browser must never extend the server session.
  OWASP: Session Management cheat sheet, Go-SCP (session management).

## 6. Destructive actions: undo > confirm

- **Undo over confirmation** wherever feasible: perform the action, show a toast/snackbar "Archived — Undo" for 5–10s (soft-delete server-side, hard-delete after window). Confirmation dialogs get auto-clicked by muscle memory; undo actually prevents loss.
- When confirmation is genuinely required (irreversible, shared, bulk, expensive): the dialog states the *specific* consequence ("Delete project 'Acme' and its 14 deployments?"), confirm button is verb-labeled (**"Delete project"**, never "OK/Yes"), styled destructive, and **not** the default-focused/Enter-bound action — focus the cancel.
- High-cost irreversibles (delete org, drop database): type-to-confirm the resource name. Reserve it — friction inflation makes people sleepwalk through it.
- Separate destructive items in menus (group at bottom, divider, danger color); never adjacent to a frequent action (delete next to edit = misclick by design — also a WCAG-flavored target-spacing problem).
- Bulk destructive actions always report scope ("Delete 37 items?") and result ("37 deleted — Undo").

## 7. Navigation & wayfinding

- Communicate **where am I**: active nav state (`aria-current="page"`), document `<title>` per view, breadcrumbs for hierarchies ≥ 3 levels.
- Max ~7 top-level destinations; beyond that, group or demote. Mobile: bottom tab bar for 3–5 core destinations (thumb zone); hamburger only for secondary overflow — it halves discoverability of whatever's in it.
- URLs are UI: every meaningful state (selected tab, filters, search, pagination, opened record) is linkable and survives refresh/back. Back button must always behave — SPA navigation that breaks Back is a release blocker.
- Search for content-heavy products: prominent, keyboard-reachable (`/` or Cmd+K), with recent queries and typo tolerance.
- **Sign-out is on every authenticated view**, in the same place each time (header or account
  menu, not only a settings page), reachable by keyboard and on mobile without hunting. Sign-out
  changes state, so it is a `POST` (a form button, not a bare `GET` link) to a route that
  invalidates the session server-side. OWASP: Session Management, CSRF Prevention cheat sheets,
  Go-SCP (session management).
- Progressive disclosure: defaults visible, power options behind "Advanced"; settings grouped by user task, not by internal architecture. Wizard flows for genuinely sequential tasks only — show step count and allow backtracking without data loss.

## 7b. Lists, tables & data sets

- **Pagination vs infinite scroll vs load-more:** infinite scroll only for leisure feeds; it
  breaks footer reach, back-position, deep linking, and "where was I". Product data gets
  pagination (URL-addressable pages) or load-more (preserves flow AND footer). Virtualize any
  list > ~200 rows (with correct focus/AT behavior — virtualization that eats keyboard nav is a
  regression).
- Restore scroll position on Back — losing position in a 500-item list is data loss UX.
- Tables: sortable columns announce sort state (`aria-sort`), header sticky past one screen,
  row actions via trailing menu (not 6 icon buttons per row), bulk-select with header checkbox +
  "select all N matching" affordance, and a mobile strategy decided per table (priority columns /
  card collapse — never just horizontal scroll with no indicator).
- Filters: applied filters visible as removable chips; result count live-announced
  (`role="status"`); zero-result state per rules/04 §5; filter state in the URL.
- Search: debounce 200–300ms, show the query in the empty state, typo tolerance, recent searches;
  Esc clears; `/` or Cmd+K focuses (without hijacking when an input is already focused).

## 7c. Dialogs, drawers & disclosure surfaces

Escalation ladder — use the *least* interruptive surface that fits:

1. **Inline expansion / accordion**: content belongs in the page flow.
2. **Popover/dropdown**: lightweight choice or glanceable info, anchored to trigger.
3. **Drawer/side panel**: secondary task keeping page context (detail preview, filters, forms
   that reference the page).
4. **Modal dialog**: response required before continuing, or focused short task (≤ ~5 fields).
5. **Full page/route**: anything longer, multi-step, or worth a URL.

- Modal abuse is the most common escalation failure: editing a record in a modal-in-a-modal means
  the flow needed a page. **Never stack modals**; if a modal spawns a modal, redesign.
- All overlays: Esc closes, scrim click closes (except mid-form with dirty state — then confirm
  discard), focus trapped + restored (rules/05 §3), body scroll locked without layout shift
  (`scrollbar-gutter`), state linkable where the content merits it (drawer with a record → URL).
- Unsaved-changes guard on any dismissible surface containing user input: "Discard changes?"
  with Keep editing as the safe default.

## 8. Touch, gestures & ergonomics

- Touch targets: **44×44px minimum** (Apple HIG; Android 48dp). WCAG 2.2 AA (2.5.8) legally requires only 24×24 *or spacing equivalent* — treat 24 as the audit floor, 44 as the build standard. Visual glyph can be smaller; pad the hit area.
- ≥ 8px gap between adjacent targets; inline tap targets in text need generous `padding` + `margin` compensation.
- Thumb zone: primary actions bottom-center/bottom-right on mobile; destructive away from natural rest position. Top corners are the most expensive reach.
- Every gesture has a visible equivalent (WCAG 2.5.1): swipe-to-delete also exists in an overflow menu; pinch-zoom content has +/- buttons. Gestures are accelerators, never the only path.
- Drag interactions need a single-pointer non-drag alternative (WCAG 2.5.7): reorder via menu ("Move up/down") or keyboard.
- Pull-to-refresh and swipe gestures must not fight browser/system gestures (back-swipe edge zones).
- Hover-revealed actions: also reachable by focus AND always-visible (or row-menu) on touch. `@media (hover: hover)` to gate hover-only affordances.
- Disable double-tap-zoom delays the right way (`touch-action: manipulation`), never `user-scalable=no` / `maximum-scale=1` (WCAG 1.4.4 violation — users must be able to pinch-zoom).

## 8b. Keyboard shortcuts & power-user paths

- Productivity tools earn shortcuts after the visible path exists: every shortcut has a menu/UI
  equivalent showing its binding (tooltip "Archive — E"); discoverability via a `?`-opened
  shortcut sheet or command palette.
- Command palette (Cmd+K) is the 2026 default for power navigation in app-shaped products:
  fuzzy actions + navigation + recent items; it must be keyboard-complete and announce results
  (combobox APG pattern).
- Don't bind single printable characters globally if any text input can have focus without your
  knowledge (embedded editors); check `event.target` and respect IME composition
  (`event.isComposing`).
- Never override browser/system-critical bindings (Cmd+L, Cmd+W, Cmd+number tab switching);
  WCAG 2.1.4: single-key shortcuts must be remappable or disableable.
- Sequences (G then I, Gmail-style) for navigation families; show a transient hint while the
  chord is pending.

## 9. Feedback & system status

- Every user action gets a response within **100ms** (perceived-instant threshold) — even if it's just a pressed state while work continues.
- Toasts: status updates only, auto-dismiss 4–8s, pause on hover/focus, never contain the *only* path to an action (they vanish; screen-reader users may miss them — pair with persistent UI), `role="status"` for info / `role="alert"` reserved for genuine errors.
- Don't stack interrupting modals; one modal at a time, and never modal-on-load for marketing while a user has a task.
- Long operations report progress honestly; fake progress bars that crawl to 90% and stall destroy trust — use indeterminate + step text if you can't estimate.

## Audit checklist

- [ ] Every input: visible associated label, correct `type`, `autocomplete` (1.3.5), `inputmode`; no placeholder-only labels; no `type="number"` for codes/IDs
- [ ] Validation on blur → re-validate on input after first error; `:user-invalid` not `:invalid`; submit focuses first error; errors specific, adjacent, linked via `aria-describedby` + `aria-invalid`, not color-only
- [ ] Failed submit preserves all user input; server errors map to fields; multi-field forms draft-persist
- [ ] No paste-blocking, no `user-scalable=no`, no dead-end disabled submit
- [ ] **Credential fields (§2) — MEDIUM**: password inputs are `type="password"` in markup (reveal is a toggle), username and password are one Tab apart, and no username/password/OTP field blocks paste. Password-named inputs declared as text: `grep -rniE '<input[^>]*type="text"[^>]*(name|id)="[^"]*(passw|pwd)|<input[^>]*(name|id)="[^"]*(passw|pwd)[^"]*"[^>]*type="text"' .`; paste handlers (a hit is a file to read — block-on-paste is the finding): `grep -rniE 'onpaste=|addEventListener\(.paste' .`
- [ ] **Sign-out and idle expiry (§7, §5b) — MEDIUM**: every authenticated view carries a `POST` sign-out control in a consistent place; at server idle expiry the client clears sensitive rendered data and lands on a signed-out screen. Header/nav components with no sign-out control (a hit is a file to read — public-page headers legitimately lack one): `grep -rliE '<(header|nav)' --include='*.tsx' --include='*.jsx' --include='*.vue' --include='*.svelte' --include='*.html' . | xargs -r grep -LiE 'log.?out|sign.?out|log.?off'`
- [ ] Loading: ~300ms grace before indicators; skeletons match final layout (zero CLS); buttons width-stable + double-submit guarded; optimistic updates roll back with explanation
- [ ] Empty states differentiated (first-use vs filtered-zero vs error) with action; error states always include a recovery path
- [ ] Destructive: undo pattern where reversible; confirms name the object + consequence, verb-labeled button, cancel focused; type-to-confirm only for top-tier irreversibles; destructive separated from frequent actions
- [ ] Right control for the job: radios ≤ 5 visible, switch only for immediate effect, no sliders for precise values, native pickers on mobile unless the custom one clears the APG bar
- [ ] Lists: pagination/load-more for product data (no unforced infinite scroll), scroll restored on Back, virtualization keeps keyboard/AT working; tables have `aria-sort`, sticky headers, a deliberate mobile strategy; filters chip-visible + URL-persisted
- [ ] Overlay escalation respected (inline → popover → drawer → modal → page); no stacked modals; dirty-state guards on dismiss; scroll lock without layout shift
- [ ] Navigation: `aria-current`, per-view titles, working Back button, state in URL, ≤ 7 top-level items, mobile primary actions in thumb zone
- [ ] Touch: 44px build standard (24px + spacing absolute floor), 8px gaps, gestures and drags have visible/keyboard alternatives, hover-only affordances gated and mirrored for touch/focus
- [ ] Long-form input autosaves (with visible status) or guards navigation; tab-close flushes; session expiry preserves data; collaborative overwrites surfaced
- [ ] Shortcuts: visible-path-first, discoverable bindings, single-key remappable (WCAG 2.1.4), IME/composition safe, no browser-binding theft
- [ ] Feedback < 100ms on every interaction; toasts non-critical, pausable, role-correct; honest progress
