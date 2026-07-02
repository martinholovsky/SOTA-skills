# 02 — Microcopy: The Words in Components

Component-level copy, mapped to the component patterns in
`sota-frontend-design` rules/04 (which owns the interaction mechanics — this
file owns what the strings say).

## 1. Buttons & action labels

- **Verb first, object when consequential**: "Create project", "Send invoice",
  "Delete 14 files". A button is the answer to "what happens when I press
  this?" — if the label can't answer it, the label is wrong.
- Generic labels are allowed only where the action is the whole screen's
  obvious subject ("Save" in a settings form); "Submit" is never right.
- **Paired actions name both paths**: "Delete project / Keep project",
  "Discard changes / Keep editing" — never "Yes / No", "OK / Cancel" on
  anything destructive or ambiguous (which button is "cancel the cancel"?).
- Buttons ≤ ~3 words; the sentence explaining the action belongs in the body
  text above it, not in the button.
- Ellipsis convention: trailing "…" when the action opens a further step
  ("Export…" opens options; "Export" does it) — apply it consistently or not
  at all.

## 2. Labels, placeholders, hints

- Every input has a **visible label naming the data** ("Work email"), not an
  instruction ("Enter your work email here") — the instruction form breaks
  scanning and translation reuse.
- **Placeholder is never the label** (it vanishes on input — mechanics in
  frontend rules/04 §1). Use placeholders only for *format examples*
  ("name@company.com") and treat them as expendable.
- Persistent requirements go in **hint text below the field**, present before
  the user types, not revealed as a scolding after failure: "8+ characters
  with a number" as a hint beats "Password too weak" as an error.
- Label the unit, not just the number: "Timeout (seconds)", never a bare
  "Timeout" over an integer field.

## 3. Empty states: three different scripts

Empty states differ by cause (pattern split in frontend rules/04 §5); the
copy jobs differ too:

- **First use** — orient + invite: what this area will hold, why it's
  valuable, one action to start. "No dashboards yet. Build one from a
  template, or start blank." Personality is welcome here.
- **User-cleared** (search/filter → 0) — echo the query, offer the exit:
  "No results for 'invoce'. Check the spelling or clear filters." Never
  reuse first-use copy — "Create your first invoice!" atop a filtered list of
  200 invoices reads as data loss.
- **Error-empty** — it's an error message (see `rules/03`), not an empty
  state: "Couldn't load projects — retry." Never imply the user has nothing
  when the truth is the fetch failed.

## 4. Onboarding, tooltips & in-product education

- Onboarding copy earns each interruption: one concept per step, tied to the
  user's *current* goal, skippable, and it never re-explains what the UI
  already says. If the tour must explain a control, first ask why the
  control's own label failed.
- **Tooltips are a last resort**, never a home for critical information —
  they're invisible on touch and to most screen-reader flows. Icon-only
  buttons get tooltips *and* accessible names (`rules/04` §2), but anything
  the user must know lives in visible text.
- Progressive disclosure of concepts: name a concept when the user first
  meets it, not in a wall of definitions up front.
- Kill stale education: a "New!" badge older than one release cycle, or a tip
  the user dismissed twice, is noise the product is wearing.

## 5. Confirmation dialogs

The words are the safety mechanism (interaction rules in frontend rules/04 §6):

```text
GOOD                                        BAD
Title: Delete project "Acme"?               Title: Are you sure?
Body: This deletes 14 deployments and       Body: This action cannot be undone.
      their logs. You can't undo this.
Buttons: [Cancel]  [Delete project]         Buttons: [No]  [Yes]
```

- Title = question naming the **specific object**; body = the **concrete
  consequence** (what, how much, reversible or not); confirm button repeats
  the verb.
- "This action cannot be undone" alone is boilerplate that says nothing about
  *what* the action does — state the consequence, then the irreversibility.
- Type-to-confirm prompts name what to type and why the friction exists.

## 6. Notifications, toasts & badges

- A toast is **one sentence, outcome first, optional single action**:
  "Invoice sent — Undo". No stacked clauses, no second sentence; if it needs
  more, it needs a different surface (toast mechanics: frontend rules/04 §9).
- Notifications (push/in-app) must stand alone on a lock screen: actor +
  action + object ("Ana commented on Q3 budget"), no "You have a new
  notification" (that's the notification's job description, not its content).
  Interruption budget and delivery: `sota-mobile` rules/03.
- Badges/counts: a number means *actionable items*, not "stuff exists" —
  a badge that never reaches zero trains users to ignore it.

## 7. Counts, plurals, time & truncation

- **Plurals via ICU MessageFormat, never string math** — "1 items" is the
  canonical i18n failure (full rules in `rules/04` §4):
  `{count, plural, one {# item} other {# items}}`.
- Zero is usually a sentence, not a number: "No results" beats "0 results";
  exceptions are dense dashboards where the column shape matters.
- Relative time for the recent past ("just now", "4 min ago"), switching to
  absolute dates beyond ~a week; always expose the exact timestamp (tooltip
  or `<time title>`), because "3 weeks ago" is useless in an audit trail.
- Truncate middles, not ends, when the distinguishing part is the tail
  ("inv…-2026-041.pdf"); never truncate away the only difference between two
  listed items.

## 8. Link text & inline actions

- Link text describes the destination and survives out of context (WCAG 2.4.4
  — screen-reader users navigate by link list): "View billing settings",
  never "click here", "here", or a bare "Learn more".
- "Learn more" is acceptable only with an accessible extension
  ("Learn more about roles" via `aria-label` or visible text).
- Don't hyperlink vague nouns mid-sentence ("There was a problem") — link the
  action ("Retry the sync").

## 9. Loading & progress text

- Name the work, not the wait: "Importing 3 of 12 contacts…" beats
  "Loading…" beats a bare spinner (thresholds in frontend rules/04 §4).
- Long operations set expectations honestly ("This usually takes ~2 min");
  never promise "a few seconds" unmeasured.
- Post-completion, say what changed: "Imported 12 contacts (2 duplicates
  skipped)" — the skipped count prevents the "where are my other rows?"
  ticket.

## Audit checklist

- [ ] No "Submit", "OK/Yes/No" pairs, or bare "Cancel/Confirm" on
      consequential dialogs:
      `grep -riE '"(Submit|OK|Yes|No)"' locales/ src/ --include='*.json'`
- [ ] Destructive buttons repeat the verb and object; dialog bodies state the
      concrete consequence, not just "cannot be undone"
- [ ] Every input: visible noun label; placeholders are format examples only;
      requirements shown as hints before first failure
- [ ] Empty states: three variants (first-use / filtered / error) with
      distinct copy; filtered-zero echoes the query; error-empty never poses
      as "you have nothing"
- [ ] Tooltips carry no critical-path information; no "New!" badges older
      than a release cycle
- [ ] Toasts are single-sentence, outcome-first; notifications name
      actor+action+object and stand alone out of app context
- [ ] No concatenated plurals:
      `grep -rnE '\+\s*["'\''](item|file|result|user)s?["'\'']' src/` is clean;
      ICU plural forms used for every count
- [ ] Relative timestamps switch to absolute past ~1 week and expose exact
      time; truncation never hides the distinguishing segment
- [ ] Link text stands alone: `grep -riE '>(click here|here|learn more)<' src/`
      returns nothing unlabeled
- [ ] Loading strings name the operation; completion strings report what
      changed, including skips/failures
