# 04 — Accessible & Localizable Language

The same string must work read aloud by a screen reader, translated into a
language 35% longer, and rendered right-to-left. These are properties of how
the string is *written and stored*, decided at authoring time — retrofitting
is a rewrite.

## 1. WCAG 2.2 language criteria (the copy-owned subset)

The full accessibility pass is `sota-frontend-design` rules/05; these criteria
are satisfied or violated *by the words themselves*:

- **3.1.1 / 3.1.2 (A/AA)** — page language declared (`<html lang>`), and
  inline foreign-language passages marked (`lang` on the element), or screen
  readers pronounce French with English phonemes.
- **2.4.6 (AA)** — headings and labels describe topic or purpose: "Payment
  method", not "More details".
- **2.4.4 (A)** — link purpose clear from the link text (rules/02 §8).
- **3.3.2 (A)** — labels or instructions exist wherever input is required —
  the *presence* of the words is the criterion.
- **3.1.5 (AAA)** — reading level: not required at AA, but treat
  plain-language discipline (`rules/01` §2) as how general-audience products
  approach it.

## 2. Accessible names: what the screen reader actually says

- **Every interactive element has an accessible name**; icon-only buttons get
  `aria-label` — an unlabeled ✕ button is announced as "button", which is a
  locked door.
- **Label-in-name (WCAG 2.5.3)**: the accessible name *contains* the visible
  label — voice-control users say what they see; `aria-label="Close dialog"`
  on a button visibly labeled "Dismiss" breaks "click Dismiss".
- Accessible names are nouns/verb-phrases, not instructions: "Search", not
  "Click here to search".
- Repeated card/row actions get differentiated names: every "Delete" in a
  list announces its object ("Delete invoice #1042") via `aria-label` or
  visually-hidden text — a link list of ten identical "Delete"s is unusable.
- Status updates that appear visually get announced textually (`role=status`
  regions) with self-sufficient wording: "Saving… Saved" — mechanics in
  frontend rules/04, the *string* is owned here.

## 3. Writing for the ear and the eye

- **Don't encode meaning in symbols alone**: "→", "✓", "❌", and emoji are
  read unpredictably or skipped; pair with words ("Done ✓" not bare "✓").
  Emoji never *replace* a word mid-sentence.
- Avoid ASCII art, decorative unicode ("𝓯𝓪𝓷𝓬𝔂" fonts — screen readers spell
  them letter-by-letter or skip them), and meaning-bearing whitespace.
- Abbreviations: expand on first use per surface, or don't abbreviate;
  screen readers guess ("approx." vs "APR" vs "apr").
- Alt text: **function over appearance** ("Search" for a magnifier icon-link,
  not "magnifying glass"); decorative images get `alt=""`; informational
  charts get a text summary of the takeaway, not "chart". No "image of" /
  "picture of" prefixes — the role is already announced.

## 4. Localization-safe strings

The engineering contract that makes translation possible:

- **Every user-visible string is externalized** — no literals in components.
  New-string review happens in the locale file diff, which is also where the
  audit greps run.
- **Never concatenate translated fragments** — word order differs by
  language; `"You have " + n + " items"` cannot be translated into German,
  Arabic, or Czech. One string per sentence, full stop.
- **ICU MessageFormat** for anything variable: named placeholders
  (`{count}`, `{fileName}` — never positional `{0}`), plural rules
  (`{count, plural, one {…} few {…} other {…}}` — Slavic languages have 3–4
  forms; English's one/other is the simple case), select for gender where the
  language needs it.
- **Translator context ships with the string**: a description field/comment
  saying where it appears and what the placeholders are ("Button on the
  billing page; {date} is the next charge date"). "Book" without context is
  untranslatable (noun? verb?).
- **Don't reuse a string across meanings**: "Archive" the button and
  "Archive" the section title may translate differently — one key per
  usage-meaning, even if English happens to coincide.
- No linguistic logic in code: no `word + "s"`, no `"a " + noun`
  (a/an breaks), no capitalizing via `toUpperCase()` on the first letter of a
  translated string (locale-sensitive — Turkish dotless-ı is the classic
  corruption).

## 5. Layout-facing and locale-facing consequences

- **Budget for expansion**: German/Finnish run roughly +35% over English
  (worst-case strings and container behavior: frontend rules/04 §2a); write
  short English *and* let containers grow — both, not either.
- Dates, numbers, currency, lists, relative time: **always through locale
  APIs** (`Intl.*` on the web, platform equivalents elsewhere) — never
  string-built. Currency symbols placement, decimal commas, and week starts
  are all locale data, not copy.
- RTL: user-generated content gets `dir="auto"`; avoid strings that assume
  left/right ("see the panel on the right" → name the panel).
- Idioms, sports/culture metaphors, humor, and wordplay don't travel —
  "home run", "back to square one", puns in empty states all become
  translator tickets. Plain language (`rules/01`) is the pre-translation.
- Images with embedded text are banned (untranslatable, unindexable,
  inaccessible); text renders as text.

## 6. Inclusive language

- Address the user as "you"; refer to unspecified people with singular
  "they" — never "he" as default or the clunky "he/she".
- No ableist casualisms in UI or docs: "sanity check" → "consistency check",
  "crazy/insane" → "unexpected/extreme", "blind spot" (metaphorical) →
  "gap".
- Industry-standard renames apply to user-visible text: allowlist/blocklist
  (not whitelist/blacklist), primary/replica (not master/slave) — align with
  the terms your APIs already migrated to.
- Name people's attributes only when relevant to the task, using the
  product-glossary term; forms asking for personal attributes follow
  `sota-privacy-compliance` minimization first (don't write copy for a field
  that shouldn't exist).
- No culture-bound assumptions in examples: names, holidays, address and
  family structures vary — example data is diverse or neutral.

## Audit checklist

- [ ] `<html lang>` set and correct; inline foreign phrases carry `lang`;
      pages with switchable UI language update it dynamically
- [ ] Every icon-only control has an accessible name; names contain the
      visible label (2.5.3); repeated row actions announce their object —
      `grep -rn 'aria-label' src/ | grep -iE 'click|here'` is empty
- [ ] Headings/labels descriptive (2.4.6); required-input instructions
      present (3.3.2)
- [ ] No meaning carried by symbol/emoji alone; alt text is functional, empty
      for decorative, and never starts with "image of":
      `grep -riE 'alt="(image|picture|photo) of' src/`
- [ ] Zero hardcoded UI strings in components (spot-check by adding a
      pseudo-locale and hunting untranslated text)
- [ ] No string concatenation or linguistic code:
      `grep -rnE '\+\s*["'\''](s|es)["'\'']|["'\'']\s*\+\s*(count|n|num)' src/`
      and no `toUpperCase()`/`capitalize` on translated strings
- [ ] ICU plurals with named placeholders everywhere counts appear; no
      positional `{0}` placeholders
- [ ] Translator context present for ambiguous strings; no key reused across
      different meanings
- [ ] All dates/numbers/currency via `Intl.*`/platform locale APIs:
      `grep -rnE '(MM/DD|DD/MM|toFixed\(2\).*[$€£])' src/` reviewed
- [ ] `dir="auto"` on user-generated text containers; no "left/right"
      directional language in strings; no text embedded in images
- [ ] Inclusive-language sweep:
      `grep -riE '(whitelist|blacklist|sanity check|master/slave)' src/ locales/ docs/`
      returns nothing user-visible
