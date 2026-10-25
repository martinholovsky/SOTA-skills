# 01 — Voice, Tone & Plain Language

The language system comes before any individual string. Voice is who the
product sounds like (constant); tone is how that voice adapts to the moment
(variable). Plain language is the floor under both.

## 1. Voice: one identity, written down

- Define voice as **3–4 attributes, each with a "this, not that" pair**, and
  keep it in the repo next to the design tokens — a voice that lives in a
  slide deck governs nothing:

  ```text
  Confident, not boastful:   "Your backup is safe."  not  "Our world-class engine protected your backup!"
  Plain, not chummy:         "Couldn't connect."     not  "Whoopsie! The internet gremlins got us 🙈"
  Precise, not academic:     "Retries in 30 s."      not  "A retry will be attempted subsequent to a 30-second interval."
  ```

- Voice applies to *every* string a user sees — validation messages, plan
  names, 404 pages — not just the marketing-adjacent surfaces.
- Personality is seasoning, not structure: a joke may live in a success state
  or empty state; it never lives in an error that cost the user something.

## 2. Plain language: the ISO 24495-1 spine

ISO 24495-1:2023 defines plain language by outcome — its four governing
principles (clause 4) say the *reader* gets content that is **relevant,
findable, understandable, and usable**. Apply them per string:

- **Relevant** — say only what the user needs *at this moment in the task*.
  Background, caveats, and internal reasoning go to docs, not dialogs.
- **Findable** — front-load: the first three words carry the point. Users
  scan; put the operative word first ("Delete 14 files?" not "Are you sure
  you would like to proceed with deleting 14 files?").
- **Understandable** — common words, one idea per sentence, active voice,
  present tense. Target roughly conversational reading level for
  general-audience products; readability scores (Flesch etc.) are directional
  tools, not gates — a developer tool may correctly use "idempotent".
- **Usable** — "readers can easily use the information": in an interface that
  means ending at the action — what the user does next is explicit and usually
  *is* the button.

Concrete rewrites:

```text
BAD:  An error has occurred while processing your request. Please try again later.
GOOD: We couldn't save your changes — the server didn't respond. Retry now, or copy your text first.

BAD:  Authentication credentials were determined to be invalid.
GOOD: Wrong email or password.

BAD:  In order to be able to utilize the export functionality, it is necessary to first select a project.
GOOD: Select a project to export.
```

## 3. Sentence mechanics

- **Active voice, user or system as actor**: "We deleted the draft" /
  "You're offline", not "The draft has been deleted".
- **One idea per sentence; ~15–20 words as a working ceiling** for UI prose
  (heuristic, not a rule to lawyer).
- **No double negatives** ("Don't disable…"), no nested conditionals in one
  sentence — split or restructure as a list.
- **Verbs over noun-stacks**: "when the export finishes" not "upon completion
  of the export process".
- **Cut filler that presumes ease**: "simply", "just", "easily", "obviously"
  — if it were simple, the user wouldn't be reading a message about it.
- **"Please" and "sorry" budgets**: please only when asking the user to do
  work for the system's benefit; sorry only when the product actually failed
  them — both lose meaning when sprayed on every string.
- **Exclamation marks: at most in celebratory moments**, never in errors or
  instructions.

## 4. Terminology: one concept, one name

- Maintain a **glossary as the single source of truth** — a tracked file, not
  tribal knowledge. Every user-visible noun for a product concept is in it.
- **The UI, docs, API, CLI, and support macros use the same term.** "Workspace"
  in the UI + "org" in the API + "team" in the docs = three support tickets
  about the same object.
- **Match the user's vocabulary, not the org chart's**: no internal codenames,
  service names, or team jargon in UI strings (also an information-disclosure
  smell — see [`sota-code-security` rules/07](../../sota-code-security/rules/07-data-exposure.md)).
- **Renames are migrations**: update UI + docs + templates + support content
  in one release, with the old term searchable in help for a transition
  period. A half-renamed concept is worse than a badly-named one.
- Reserved/loaded words get one meaning: "delete" (gone, maybe undoable) vs
  "remove" (taken out of this context, still exists) vs "archive" (hidden,
  recoverable) — pick the mapping once and never blur it.

## 5. Tone: adapt to the user's state, not your mood

Tone shifts with the user's stress, in one direction — **the more stressed the
user, the plainer and calmer the language**:

| Moment | Tone | Example |
|---|---|---|
| Success, milestones | Warm, may be light | "Nice — your first deploy is live." |
| Neutral tasks, settings | Plain, efficient | "Changes save automatically." |
| Errors, blocked tasks | Calm, concrete, zero humor | "Payment failed — your card was declined. No charge was made." |
| Data loss, security incidents | Sober, direct, no mascots | "We've signed you out everywhere as a precaution." |

- Humor is opt-in and low-stakes only; a pun on a 500 page that ate a form
  submission reads as mockery.
- Empty states and onboarding may carry the most personality; errors the
  least.

## 6. Capitalization, punctuation & mechanics — pick once, enforce

- **Sentence case for everything** (buttons, titles, labels, menu items) is
  the 2026 default — it's faster to read, easier to keep consistent, and
  survives translation better than Title Case. Whichever you pick, encode it
  in the review checklist; mixed casing across surfaces is the most visible
  inconsistency a product ships.
- Periods: full sentences in body text get them; fragments, labels, and
  single-sentence tooltips don't. Never on buttons.
- Numerals for UI numbers ("3 files", not "three files"); locale-format
  numbers, dates, and currency programmatically ([`rules/04`](04-accessibility-localization.md) §5) — never
  hand-write "MM/DD/YYYY" into a string.
- Contractions ("can't", "you're") are standard product voice; skip them only
  in legal/consent text where precision governs.
- Ellipsis for in-progress ("Saving…", one character, not "..."), never for
  coyness.

## Audit checklist

- [ ] A written voice definition (3–4 attributes, each a this-not-that pair)
      exists in the repo, not only in a slide deck, and every user-visible
      string follows it — validation messages, plan names, and 404 pages, not
      just marketing-adjacent surfaces; no joke in an error that cost the
      user something (§1)
- [ ] Strings front-load the point (the first three words carry it) — grep
      long openers:
      `grep -rniE '"(In order to|Please note that|It is (necessary|recommended)|Are you sure you would like)' --include='*.json' --include='*.yaml' --include='*.yml' --include='*.ts' --include='*.tsx' --include='*.js' --include='*.jsx' --include='*.html' --exclude-dir=node_modules .`;
      each string says only what the user needs at this step (background goes
      to docs), in common words, one idea per sentence, and ends at the
      action the user takes next (§2)
- [ ] Active voice and present tense dominate; no double negatives or nested
      conditionals in any user-facing string; verbs over noun-stacks;
      "please" only where the user does work for the system's benefit,
      "sorry" only where the product failed them (§3)
- [ ] Filler ban holds:
      `grep -rniE '"(Simply|Just|Easily|Obviously) ' --include='*.json' --include='*.yaml' --include='*.yml' --include='*.ts' --include='*.tsx' --include='*.js' --include='*.jsx' --include='*.html' --exclude-dir=node_modules .`
      returns only justified hits (§3)
- [ ] One name per concept: sample 10 core nouns; UI, docs, API, CLI, and
      support macros agree on all 10; glossary is a tracked file and current;
      no half-renamed concept — a rename updated UI, docs, templates, and
      support content in one release, the old term kept only as a help-search
      alias (§4)
- [ ] No internal codenames/team jargon in UI strings (§4)
- [ ] delete/remove/archive each mean exactly one thing across the product (§4)
- [ ] Tone matrix respected: no humor or exclamation marks in error strings
      (`grep -rniE '"[^"]*(Oops|Whoops|Uh.?oh)[^"]*"' --include='*.json' --include='*.yaml' --include='*.yml' --include='*.ts' --include='*.tsx' --include='*.js' --include='*.jsx' --include='*.html' --exclude-dir=node_modules .`);
      data-loss and security strings are sober and direct, with no mascots (§5)
- [ ] One casing convention (sentence case or Title Case), written into the
      review checklist and applied everywhere; buttons, labels, fragments, and
      single-sentence tooltips carry no trailing period; contractions except
      in legal/consent text; in-progress ellipsis is the one `…` character —
      `grep -rnE '"[^"]*[A-Za-z]\.\.\."' --include='*.json' --include='*.yaml' --include='*.yml' --include='*.ts' --include='*.tsx' --include='*.js' --include='*.jsx' --include='*.html' --exclude-dir=node_modules .`
      lists three-dot strings to fix (§6)
- [ ] UI numbers are numerals ("3 files", not "three files"); numbers, dates,
      and currency are locale-formatted in code, not hand-written into
      strings (§6)
