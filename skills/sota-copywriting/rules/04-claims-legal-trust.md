# 04 — Claims, Legal & Trust

Marketing copy is regulated speech. The FTC (US), consumer-protection and
unfair-commercial-practices law (EU), and platform policies all bite the same
spot: **saying things that aren't true, or hiding things that are.** This file
is the accuracy gate — run it before anything ships, because retractions cost
more than rewrites. (US/EU are covered as the common cases; verify locally for
other jurisdictions.)

## 1. The substantiation gate

- **Every objective claim has evidence on file before publication** — the
  FTC's substantiation doctrine expects a reasonable basis *at the time the
  claim is made*, not assembled after a challenge. Build the habit
  regardless of jurisdiction: a claims register (claim → evidence → owner →
  re-verify date) next to the site content.
- Objective claims include: numbers ("40% faster", "10,000 customers"),
  rankings ("#1", "most popular"), absolutes ("only", "first", "never goes
  down"), comparisons ("cheaper than X"), and **friction reducers**
  ("cancel anytime", "no credit card").
- **Puffery vs claim**: "we think it's delightful" is opinion; anything a
  reasonable reader takes as measurable fact is a claim. When in doubt, it's
  a claim.
- Comparative claims carry the burden twice: substantiate your number *and*
  the competitor's, dated (their product changes too — `rules/02` §6).
- Health, financial, security, and earnings claims are heightened-scrutiny
  categories — legal review, not just this checklist.
- **Security claims are technical claims**: "bank-level encryption" is
  unfalsifiable filler — either state the real control ("TLS 1.3 in transit,
  AES-256 at rest" — verified against the actual config, `sota-code-security`
  rules/04) or say nothing. Fictional security copy is discoverable in
  breach litigation.
- Uptime/SLA marketing numbers come from measured data (`sota-observability`
  SLOs), match the contractual SLA, and carry the measurement window.

## 2. Endorsements & material connections (FTC Endorsement Guides)

16 CFR Part 255, revised effective July 2023 — the operational rules:

- **Any material connection between endorser and brand is disclosed**: paid,
  free product, affiliate commission, employment, family. The 2023 revision
  is explicit that tags, likes, and reposts by connected parties can be
  endorsements.
- **Disclosures are clear, conspicuous, and proximate** — in the post/page
  itself, before the fold of the endorsement, not behind "more", not only in
  a bio, not hashtag soup (#sp doesn't cut it; "Paid partnership with X"
  does). Platform disclosure tools alone may not suffice.
- **Employee advocacy counts**: employees praising the product on social
  media disclose the employment relationship — put it in the social-media
  policy.
- Endorsements reflect **honest, current opinions of actual users**; a
  script an endorser wouldn't say in their own words is the brand speaking
  in costume.

## 3. Reviews & testimonials (Consumer Reviews Rule)

16 CFR Part 465 (effective October 2024) turned review deception into a
civil-penalty rule; treat every item as a Critical finding:

- **No fake reviews or testimonials** — including AI-generated ones, reviews
  by non-users, or reviews misrepresenting experience.
- **No buying positive (or negative-competitor) reviews**; incentivized
  reviews cannot be conditioned on sentiment, and material incentives are
  disclosed.
- **Insider reviews** (officers, employees, their relatives) require clear
  disclosure of the relationship.
- **No review suppression**: publishing only positive reviews while a
  "reviews" surface implies completeness, or using legal threats to remove
  honest negatives, violates the rule. Moderation criteria must be
  sentiment-neutral.
- **No fake social-media indicators** — purchased followers/likes/views used
  to misrepresent influence.
- Testimonial hygiene on top of the rule: written consent on file (scope +
  revocation path), identity real and verifiable, and **typicality** — a
  best-case result presented as typical is deceptive; either show the
  generally expected result or clearly qualify the outlier.

## 4. Dark patterns

Regulators on both sides of the Atlantic now name these directly (FTC dark-
patterns enforcement; EU DSA Article 25 for platforms; GDPR consent validity):

- **Confirmshaming** — decline options that mock the user ("No thanks, I
  like losing data") — banned; the neutral decline is "Not now"
  (`sota-ux-writing` rules/03 §7 owns the in-product wording).
- **False urgency/scarcity** — countdown timers that reset, "only 2 left"
  without inventory truth, "17 people are viewing this" from a random-number
  generator: fabricated urgency is deception, full stop. Real deadlines and
  real scarcity, stated plainly, are fine.
- **Hidden costs / drip pricing** — mandatory fees revealed at the last
  checkout step (`rules/02` §6).
- **Pre-ticked consent** — invalid under GDPR (consent must be an affirmative
  act) and a dark pattern everywhere; marketing-consent checkboxes default
  unchecked (consent engineering: `sota-privacy-compliance` rules/03).
- **Roach-motel subscriptions** — signup in one click, cancellation behind a
  phone call. Negative-option/auto-renewal rulemaking is jurisdiction-
  specific and in flux (verify current US federal/state and EU status at use
  time); the durable principle: **cancellation effort ≈ signup effort**, and
  renewal terms disclosed before the charge.
- Visual-hierarchy manipulation (giant accept, ghost decline) is the same
  pattern in CSS — audit copy and presentation together.

## 5. Email & lifecycle messaging law

Two regimes cover most senders; apply the stricter when audiences mix:

- **CAN-SPAM (US, commercial email)**: truthful header/sender, non-deceptive
  subject line, physical postal address in the message, clear unsubscribe
  that works, is honored **within 10 business days**, and costs nothing more
  than a reply/click. Applies per-message to commercial content.
- **GDPR + ePrivacy (EU)**: direct marketing needs **opt-in consent** (an
  affirmative act, granular, withdrawable as easily as given) or the
  narrow **soft opt-in** (existing customers, similar products/services,
  opt-out offered at collection and in every message). Consent records are
  kept; "we emailed everyone who ever signed up" is not a lawful basis.
- **Transactional vs marketing is a content test, not a template flag**:
  receipts and security notices aren't marketing — until promotional content
  dominates; hybrid messages get the stricter treatment. Never smuggle
  promotions into "Your invoice" subject lines (deceptive subject +
  reclassifies the mail).
- Subject lines are claims: "Re:"/"Fwd:" fakery, false urgency, and
  bait-and-switch subjects violate the deception rules *and* train users to
  ignore you.
- Sunset/engagement policies (stop mailing the long-unengaged) are
  deliverability hygiene and consent hygiene at once.

## 6. Trust surfaces & ongoing hygiene

- The claims register (§1) gets **scheduled re-verification** — pricing
  claims, competitor comparisons, stats, and "only" claims rot fastest;
  every published claim has an owner and a review date.
- Legal pages (terms, privacy, refund policy) match what the copy promises —
  "cancel anytime" in the hero with a 30-day-notice clause in the ToS is a
  deception finding, not an inconsistency.
- Badges and certifications: display only what's current and verifiable
  (SOC 2 report exists, the ISO cert is in-date); expired/aspirational
  compliance badges are misrepresentation (`sota-privacy-compliance` owns
  the underlying programs).
- Press/award mentions link the source; "as featured in" requires actual
  coverage (`rules/02` §5).
- When a claim fails re-verification: correct the page, and assess whether
  the delta warrants proactive correction to affected customers — silent
  edits of material claims compound the exposure.

## Audit checklist

- [ ] Claims register exists: every objective claim on high-traffic surfaces
      mapped to evidence, owner, and re-verify date
- [ ] Superlative/absolute sweep clean or substantiated:
      `grep -riE '\b(#1|best|only|first|fastest|guaranteed|never|100%)\b' site/ emails/`
- [ ] Security/uptime claims state real, currently-true controls and
      measured numbers — no "bank-level/military-grade" filler
- [ ] Every endorsement with a material connection carries a clear,
      proximate disclosure (not bio-only, not hashtag-only); employee
      social-media policy covers advocacy disclosure
- [ ] Reviews surface: no fake/AI/insider-undisclosed reviews, no
      sentiment-conditioned incentives, sentiment-neutral moderation
      documented, no purchased social-proof metrics (16 CFR 465 exposure)
- [ ] Testimonials: consent on file, real identities, typicality honest or
      clearly qualified
- [ ] Dark-pattern sweep: no confirmshaming
      (`grep -riE '"No thanks, I' site/`), no resetting timers or fabricated
      scarcity/viewer counts, no drip pricing, no pre-ticked consent,
      cancellation effort ≈ signup effort
- [ ] Email: unsubscribe present/working/honored ≤ 10 business days;
      physical address present; EU sends have consent or soft-opt-in records;
      subjects truthful; no promotions disguised as transactional mail
- [ ] Legal pages consistent with marketing promises; badges current and
      verifiable
- [ ] Re-verification schedule ran on time for comparisons/stats/pricing;
      failed claims corrected on-page (and to customers when material)
