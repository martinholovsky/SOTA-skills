# 02 — Headlines, Landing Pages & CTAs

The page is an argument with a layout. Structure carries skimmers; sentences
carry readers; the CTA carries the conversion. All three are copy problems.

## 1. Headlines

- **Draft ≥5 variants, pick against the 4 U's heuristic** (useful, urgent,
  unique, ultra-specific — a scoring lens, not a law): most first-draft
  headlines fail "useful" by describing the product instead of the outcome.

  ```text
  Weak:   The modern platform for data teams.        (no outcome, no specificity)
  Better: Ship trusted dashboards in minutes.        (outcome + speed)
  Strong: Ship dashboards your CFO trusts — without  (outcome + audience + objection
          waiting on data engineering.                pre-handled)
  ```

- **Clarity beats cleverness, every time it's tested**: a pun the reader must
  decode costs the 3 seconds you had. Wordplay is affordable only when the
  meaning survives without it.
- The **subheadline does the explaining**: headline = promise, subheadline =
  mechanism + who it's for ("Automated data tests catch broken pipelines
  before your stakeholders do — built for dbt-based teams").
- Headline vocabulary comes from the value proposition (`rules/01` §2) and
  the reader's own words — reusing the phrase users say in interviews
  measurably outperforms invented phrasing (message-mining).
- Numbers and specifics earn attention honestly: "Cut CI time 40%" (with the
  benchmark — `rules/04`) beats "Dramatically faster CI".

## 2. The above-fold contract

A first-time visitor, without scrolling, can answer:

1. **What is it?** — category anchor in headline/subheadline.
2. **Is it for me?** — audience named or unmistakably implied.
3. **What do I do next?** — one primary CTA visible.
4. *(Trust flash)* — one proof element (logo strip, star rating with source,
   key number) in the first viewport.

- Everything else — features, story, second CTA styles — is below-fold
  material. An above-fold carousel of rotating value propositions is
  indecision rendered in HTML.
- The visual/layout execution (hierarchy, contrast, responsive behavior) is
  `sota-frontend-design`; the *content* of the contract is owned here.

## 3. Page flow & scannability

- Classical flow — attention → interest → desire → action (AIDA as a
  heuristic frame, not a template): hook with the promise, build with
  benefits+proof, resolve objections, ask. Long pages repeat the ask.
- **The skim test is the gate**: read only the headings — they must tell the
  entire argument in order. Section headings are mini-headlines
  ("Catch breaking changes before merge"), never labels ("Features",
  "Benefits", "Why us").
- Paragraphs ≤ 3 sentences on marketing pages; one idea each. Bullets for
  parallel items (3–5, parallel grammatical structure); bold for the one
  load-bearing phrase per screen, not per sentence.
- Front-load every heading and bullet — the first three words are what a
  scanner reads (same law as product copy: `sota-ux-writing` rules/01 §2).
- Reading-ease scores (Flesch etc.) are directional diagnostics for
  general-audience pages, not gates — technical audiences read technical
  sentences fine; what they won't read is *long* sentences stacked deep.

## 4. CTAs

- **Verb + outcome**: "Start free trial", "Get the report", "Book a demo".
  Banned: "Submit", "Click here", solitary "Learn more" (acceptable only as
  a *secondary* link with a named object: "Learn more about pricing").
- **One primary action per page**, visually singular; a secondary
  lower-commitment path (docs, demo video) may exist but never competes.
  Three equal buttons = the team couldn't decide = the visitor won't either.
- **Friction reducers adjacent to the CTA** — the objection dies where it's
  born: "Free 14-day trial · No credit card · Cancel anytime". Every friction
  reducer is a factual claim: verify or delete (`rules/04` §1).
- Match commitment to awareness stage (`rules/01` §1): "Book a demo" atop a
  cold-traffic page skips the relationship; "Read the benchmark" might be
  the right first ask.
- First-person phrasing ("Start my trial") and micro-copy under the button
  are testable variants, not defaults — test against your traffic rather
  than cargo-culting someone's A/B result.
- Long pages: repeat the CTA after each major proof section; same wording
  each time (varying the verb reads as different actions).

## 5. Social proof on the page

Placement and presentation (the legal layer — consent, material connections,
typicality — is `rules/04` §2–3):

- **Specific outcomes beat adjectives**: "Cut our incident response from 45
  to 12 minutes" beats "Great tool, highly recommend!". Solicit and select
  testimonials for specificity.
- Full attribution (name, role, company, photo/logo where consented)
  proportionally to the claim's weight — the bigger the claim, the more
  verifiable the source must look *and be*.
- Place proof at the objection it answers: security testimonial by the
  security section, migration story by the integration section — not a
  quarantined "wall of love".
- Logo walls: recognizable > numerous; with permission; "as seen in" press
  logos only for actual coverage, not paid placements presented as earned.
- Counts ("Trusted by 10,000+ teams") follow the honest-unit rule
  (`rules/01` §6).

## 6. Pricing & comparison surfaces

- **Pricing pages are trust pages**: real prices where the model allows;
  "Contact us" only for genuinely custom tiers. Every "what happens at the
  limit / after the trial / when I cancel" question answered on the page —
  each unanswered one is a support ticket or a lost conversion.
- No hidden-cost surprises deferred to checkout (also a dark pattern —
  `rules/04` §4): required add-ons, per-seat minimums, and billing frequency
  are visible at the decision point.
- **Comparison pages/tables are factual documents**: current competitor
  facts at publish time (dated, re-verified on a schedule), objectively
  phrased rows, no strawman tiers. Comparative claims carry full
  substantiation burden (`rules/04` §1) — a stale "Competitor X lacks SSO"
  is a liability, not an asset.
- Anchor honestly: "Most popular" marks the actually-most-chosen tier, not
  the one you want to sell.

## Audit checklist

- [ ] Headline states an outcome, not a product description; ≥5 variants
      were considered (in the draft PR/brief); subheadline explains mechanism
      + audience
- [ ] Above-fold contract holds on mobile and desktop: what/for-whom/next
      action + one proof element, no carousel of rotating value props
- [ ] Skim test passes: headings alone tell the argument; no "Features"/
      "Why us" label headings
- [ ] Paragraphs ≤ 3 sentences; bullets parallel; bold ≤ 1 phrase per screen
- [ ] Every CTA is verb+outcome; grep the ban list:
      `grep -riE '>(Submit|Click here|Learn more)<' site/` — bare hits fixed
      or given named objects
- [ ] One primary CTA per page; repeated verbatim on long pages; commitment
      level matches traffic temperature
- [ ] Every friction reducer ("no credit card", "cancel anytime",
      "5-minute setup") verified true in the product today
- [ ] Testimonials specific and fully attributed; proof placed at the
      objection it answers; press/"as seen in" logos reflect earned coverage
- [ ] Pricing page answers limit/trial/cancel questions; no costs revealed
      only at checkout; "Most popular" is factually most popular
- [ ] Comparison tables dated, sourced, re-verification scheduled; no
      unprovable competitor claims
