# 01 — Positioning & Value Proposition

Copy fails at the strategy layer more often than the sentence layer. A
beautifully written page arguing the wrong thing to the wrong reader converts
worse than a plain page arguing the right thing.

## 1. Audience before adjectives

- Name the **primary reader** of each asset: role, situation, and the job
  they're hiring the product for (jobs-to-be-done framing). "Developers" is
  not an audience; "a backend engineer evaluating error-tracking tools after
  an incident" is.
- **Awareness stage dictates the opening** (classic Schwartz ladder, still
  the working model):

  | Reader state | Copy leads with |
  |---|---|
  | Unaware of the problem | The symptom they *do* feel |
  | Problem-aware | The problem, named precisely, then the category |
  | Solution-aware | Why this approach beats the alternatives |
  | Product-aware | Differentiation, proof, and the offer |
  | Ready to buy | The offer, friction removal, reassurance |

- One asset, one primary audience. A page addressing the engineer, the
  buyer, and the compliance officer in the same scroll serves none — split
  pages or split sections explicitly ("For security teams").
- Write in the reader's vocabulary, at the reader's expertise level:
  developer audiences trust precise terminology ("idempotent retries") and
  distrust dumbed-down gloss; buyer audiences need the outcome translated to
  business terms. Mirroring the words users actually say (support tickets,
  reviews, interviews) beats inventing marketing language.

## 2. Value proposition: the sentence everything else serves

- The working template (fill it before writing anything else):

  ```text
  For [audience] who [situation/problem],
  [product] is a [category] that [key outcome].
  Unlike [reference alternative], it [primary differentiator].
  ```

  The template is scaffolding — it rarely ships verbatim, but every published
  headline/subheadline pair must be derivable from it.
- **Category anchoring**: name a category the reader already understands,
  then differentiate — "error tracking that fixes itself" beats a novel
  category no one searches for. Inventing a category is a strategy decision
  with a marketing budget attached, not a copy flourish.
- The **reference alternative is whatever the reader does today** — often a
  spreadsheet, a script, or nothing — not necessarily a competitor.
- One primary value proposition per product per audience. Three "equally
  primary" benefits means positioning hasn't been decided; copy can't fix
  that upstream ambiguity.

## 3. Benefit first, feature as proof

- Every section passes the **"so what?" test** from the reader's chair:
  feature → so what? → benefit → so what? → outcome they care about. Stop at
  the first level the reader values, and lead with it.

  ```text
  Feature-first (weak):  256-bit AES encryption at rest.
  Benefit-first (strong): Your customer data stays yours — encrypted at rest
                          (AES-256), so a stolen disk is a non-event.
  ```

- **Features are the evidence, not the argument** — cut neither. Benefit-only
  copy reads as vapor to technical buyers; feature-only copy outsources the
  thinking to the reader. The pairing is the craft.
- The **flipped-pronoun test**: if a section says "we/our" more than
  "you/your", it's an about-us page in disguise. "We provide advanced
  analytics" → "You see which feature drove the churn".
- Quantify benefits where substantiation exists ("cuts build times ~40%" with
  the benchmark linked — `rules/04` §1); where it doesn't, stay qualitative
  rather than inventing precision.

## 4. Message hierarchy & message match

- Structure the argument: **primary promise → 3±1 supporting benefits →
  proof for each → objection handling → action.** Everything on the page maps
  to a node in that tree; orphan sections ("Our story", mid-funnel) get cut
  or moved.
- **Message match end-to-end**: the ad/post/email that brought the reader,
  the landing headline, and the CTA describe the same promise in the same
  vocabulary. A click on "Ship dashboards in minutes" that lands on
  "Enterprise BI platform" bounces — audit the full path, not the page alone.
- Objection handling is copy's job, placed at the objection's moment:
  pricing fears near the CTA ("free tier, no card"), migration fear near the
  integration section, security questions linked to real documentation
  (`sota-docs-workflow`), not a vague "enterprise-grade security" badge.

## 5. Differentiation without fiction

- **Specific beats superlative**: "answers in under 50 ms at p99" out-converts
  and outlives "blazingly fast". Superlatives ("best", "#1", "fastest") are
  objective claims requiring evidence (`rules/04` §1) — default to cutting
  them.
- "Only/first" claims are the highest-risk sentences on the site: verify
  against the market at publish time and re-verify on a schedule; a false
  "only" is both a legal exposure and a one-tweet credibility loss.
- Legitimate differentiation sources when the feature grid ties: the
  approach/architecture, the pricing model, the support reality, the
  ecosystem, who it's deliberately *not* for. Saying who it's not for is
  under-used and highly credible.
- Never differentiate by naming competitors' weaknesses you can't prove —
  comparative claims carry the same substantiation burden plus higher legal
  risk (`rules/04` §1). Factual comparison tables: `rules/02` §6.

## 6. Evidence: the proof layer

Rank evidence by credibility to a skeptical reader, and prefer the top:

1. **Verifiable numbers with sources** — benchmarks with methodology, public
   case-study metrics, usage stats you can substantiate.
2. **Named customer outcomes** — "Acme cut incident response 60%" with a
   linked case study and the customer's consent.
3. **Named testimonials** — real person, name/role/company, consented
   (`rules/04` §3).
4. **Logos** — with permission; a logo wall implies endorsement.
5. **Aggregate claims** — "10,000+ teams" only if the number is real and the
   unit honest (free signups ≠ "teams trust us").

Unranked non-evidence: anonymous quotes ("— CTO, Fortune 500"), star ratings
without sources, "award-winning" without naming the award.

## Audit checklist

- [ ] Each major asset names (in a brief or comment) its primary audience,
      awareness stage, and single conversion goal
- [ ] The value proposition is written down in template form and every
      headline/subheadline derives from it
- [ ] Category anchor present; differentiator framed against what the reader
      does today
- [ ] "So what?" test passes on every section: benefit stated, feature
      attached as proof — no feature-list-only sections, no proof-free
      benefit sections
- [ ] Flipped-pronoun test: you/your dominates we/our —
      `grep -ciE '\b(we|our)\b' page.md` vs `\b(you|your)\b` as a smoke test
- [ ] Message match verified across ad/email → landing page → CTA for the
      top acquisition paths
- [ ] Objections handled at their moment (pricing, migration, security) with
      links to real docs, not adjective badges
- [ ] Zero unsubstantiated superlatives/only/first claims:
      `grep -riE '\b(best|#1|leading|fastest|only|first|world-class|revolutionary)\b' site/`
      — every hit has evidence on file or gets cut (`rules/04`)
- [ ] Every proof element is top-3-tier where possible; no anonymous quotes,
      sourceless stats, or unnamed awards
- [ ] Aggregate numbers ("10,000+ users") match an internal source of truth
      and an honest unit
