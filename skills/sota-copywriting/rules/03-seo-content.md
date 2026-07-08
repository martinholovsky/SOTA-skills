# 03 — SEO Content

Search-facing content lives under two masters: the reader and the ranking
systems' spam policies. The 2026 reality: Google's systems reward demonstrated
first-hand value ("people-first" content, E-E-A-T signals) and name-and-punish
the shortcuts — scaled AI-generated filler, borrowed-reputation hosting,
doorway pages. Writing for the reader *is* the ranking strategy; this file
makes that operational.

## 1. Search intent before content

- Classify the target query's intent and match the **format**, not just the
  topic: informational (guide/answer), commercial-investigation (comparison,
  "best X for Y"), transactional (product/landing page), navigational (leave
  it alone — that traffic isn't yours).
- **Read the current SERP as the spec**: what format ranks (listicle? docs
  page? video?) tells you what searchers accept for that query. Publishing a
  2,000-word essay against a SERP of quick-answer pages is a format mismatch,
  not a quality problem.
- One page per intent; don't split one intent across near-duplicate pages
  (they cannibalize), don't fuse two intents into one page (it half-serves
  both).
- Answer the query in the first screen, then earn the scroll with depth —
  burying the answer under 800 words of preamble ("what is X?" recipes-blog
  style) is reader-hostile and increasingly rank-hostile.

## 2. People-first content & E-E-A-T

Google's guidance frames the bar as people-first content with demonstrated
**experience, expertise, authoritativeness, trust** (E-E-A-T). Operationally:

- **Show first-hand experience**: real screenshots of you using the thing,
  measured results, edge cases you hit, opinions with reasons. Content
  assembleable entirely from the top-10 existing results adds nothing and
  ranks accordingly.
- **Real authorship**: named authors with verifiable bios for content where
  expertise matters; fabricated author personas with stock photos are
  E-E-A-T fraud and a trust time-bomb.
- **Cite primary sources** for claims — specs, papers, official docs, your
  own data (methodology included). Citing other blog posts citing other blog
  posts is the content equivalent of a dependency chain with no source.
- **Honest dates**: publish date + a true "updated" date when materially
  revised. Bumping dates without changes to look fresh is a trust dark
  pattern search systems are wise to.
- Trust surfaces: contact page, about page, editorial/AI-usage policy for
  publications — the boring pages are ranking infrastructure.

## 3. Spam policies: the named failure modes

Google's spam policies (developers.google.com/search — spam policies doc)
name these; violating them risks the page *and* the domain:

- **Scaled content abuse** — many pages generated (by AI or humans) primarily
  to rank, adding little value: mass "X vs Y" permutation pages, thin
  location pages, stitched/scraped aggregations. The test is value-added per
  page, not how it was produced.
- **Site reputation abuse** — third-party content hosted mainly to ride the
  host's ranking signals ("parasite SEO": coupon/review sections rented out
  on a news domain). If you're the host, it's your domain at stake.
- **Doorway pages** — near-duplicate pages funneling to the same destination.
- **Keyword stuffing** — and its modern denial: there is **no keyword-density
  target**; that metric is folklore. Use the topic's natural vocabulary
  (searchers' terms, synonyms, the entities involved) because you're actually
  covering the topic.
- **Misleading structured data** — schema.org markup must describe visible
  page content; review stars on markup the page doesn't show is a manual-
  action magnet.
- Expired-domain abuse, link schemes, hidden text: same doc, same answer —
  don't.

## 4. The mechanical layer: titles, metas, headings, links

- **Title element**: the page's promise, front-loaded, unique per page, and
  truthful — search engines rewrite titles that don't match content, and the
  rewrite is worse than your honest version. Length limits are *pixel-based
  display truncation*, not ranking rules; "~50–60 characters" is a display
  heuristic only.
- **Meta description**: doesn't rank; it's your ad copy in the SERP — state
  the benefit + what the reader gets, and accept engines substitute their own
  snippet when they think they know better (~155 characters as display
  heuristic).
- **Heading hierarchy is the document outline**: one H1 stating the topic,
  H2s that answer the sub-questions searchers actually ask (they're your
  skim-test — `rules/02` §3 — and your featured-snippet candidates).
- **Internal links with descriptive anchors** ("zero-downtime migration
  guide", not "read more") from and to related content — orphan pages
  neither rank nor pass value. External links to your primary sources are a
  trust signal, not a leak.
- URL slugs: short, readable, stable — a slug is an API (`sota-api-design`
  versioning instincts apply: redirects on change, never break inbound
  links).

## 5. AI-assisted content discipline

- AI assistance is legitimate; **unreviewed AI output published at scale is
  scaled content abuse** (§3) plus an accuracy liability. The gate: a human
  with domain knowledge verifies every factual claim, adds first-hand value
  (experience, data, opinion), and owns the byline.
- LLMs fabricate specifics — statistics, citations, quotes, product
  capabilities. **Every number and citation in AI-drafted content gets
  primary-source verification** before publish (`rules/04` §1 machinery).
- Don't fabricate the experience signals: fake "we tested this for 3 weeks"
  framing around untested content is deception, indistinguishable from the
  fake-review problem (`rules/04` §3).
- Disclose AI usage where your editorial policy, platform, or jurisdiction
  requires it; a published AI-usage policy is becoming a standard trust
  surface for content sites.

## 6. Generative AI search surfaces (AI Overviews / AI Mode)

Google's own guidance ("Guide to Optimizing for Generative AI Features",
developers.google.com/search) is blunt: AI Overviews and AI Mode are rooted in
the core Search ranking and quality systems, so **"GEO"/"AEO" is still SEO** —
§1–§5 of this file *are* the optimization strategy.

- **Debunk the folklore before someone bills you for it**: Google does not
  read `llms.txt` or other AI text files ("neither harm nor help"); there is
  no need to chunk content into AI-sized pieces, rewrite "for AI", or add
  special schema.org markup for AI visibility. Vendors selling these as
  Google-AI tactics are selling keyword density with a new name (§3).
- **The controls are the existing ones**: `nosnippet`, `data-nosnippet`,
  `max-snippet`, and `noindex` govern what AI features may show;
  Google-Extended governs training/grounding in Google's other systems. A
  dedicated Search Console opt-out toggle + generative-AI performance report
  began rolling out in June 2026 (UK first, global to follow) — check it
  before inventing a blocking scheme.
- Appearing in an AI answer is a snippet-economics question, not a new
  discipline: the first-screen-answer rule (§1) and primary-source E-E-A-T
  signals (§2) are what get cited.

## 7. Content lifecycle

- **Content is inventory with a freshness cost**: schedule re-verification
  for anything with versioned facts (pricing, benchmarks, "as of 2026"
  claims) — the library's own rule (fast-moving claims re-verified) applies
  to published content doubly.
- Update, consolidate, or prune: decayed posts that still get traffic →
  update (honest updated-date); overlapping posts splitting one intent →
  merge + redirect; zero-value pages → prune (they drag domain-level quality
  assessments).
- Canonicalize deliberately when near-duplicates must exist (print views,
  UTM variants); one canonical per intent.
- Redirects preserve equity and readers: renamed/merged content 301s to its
  successor; a content migration without a redirect map is data loss.

## Audit checklist

- [ ] Each search-targeted page names its query + intent (in brief/frontmatter)
      and matches the format the current SERP validates
- [ ] The query's answer appears in the first screen; no 800-word preambles
- [ ] First-hand value present: original data/screenshots/experience per
      page; nothing assembleable purely from existing top-10 results
- [ ] Real named authors with bios on expertise-sensitive content; no
      fabricated personas; publish/updated dates truthful
- [ ] Claims cite primary sources; no citation chains into blogspam
- [ ] Spam-policy sweep: no page sets matching scaled/doorway patterns
      (mass permutation pages, thin location pages); no rented third-party
      sections riding the domain; structured data matches visible content
- [ ] No keyword-density thinking anywhere in the process; natural topic
      vocabulary only
- [ ] Titles unique, front-loaded, truthful; meta descriptions written as
      SERP ad copy; one H1; H2s carry the argument (skim test)
- [ ] Internal links use descriptive anchors; no orphan pages; external
      links to primary sources present
- [ ] AI-assisted content: human domain review recorded, all numbers/
      citations verified, no fabricated experience framing; AI-usage policy
      published if applicable
- [ ] No GEO/AEO folklore in the strategy: no llms.txt-for-Google, chunking,
      AI-rewriting, or special-schema tactics sold as AI-visibility work;
      AI-surface appearance managed via the standard preview controls /
      Search Console setting
- [ ] Re-verification schedule exists for time-sensitive facts; overlap
      merged; prune list maintained; every moved URL has a 301
