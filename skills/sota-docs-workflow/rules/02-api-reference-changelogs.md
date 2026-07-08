# 02 — API Docs, Reference & Changelogs

Generated reference documentation, docstring discipline, runnable examples,
error documentation, versioned docs, and changelog/migration-guide practice.

## §1 Generate reference from source

Hand-written reference documentation drifts from the code within weeks. The
baseline is generation from the artifact of record:

- **HTTP APIs**: OpenAPI document is the source of truth; rendered docs are
  generated from it (Redoc/Scalar/Swagger UI class of renderers — Scalar adds
  try-it + snippets, Redoc is read-optimized; the renderer matters less than the
  pipeline). Spec-first or code-first is a per-team choice, but the spec must be
  CI-validated against the implementation either way (contract tests, or
  generated-from-code with lint gates — see `sota-api-design` for spec design
  itself).
- **Libraries**: rustdoc, godoc, javadoc, Sphinx/mkdocstrings from docstrings,
  TypeDoc from TSDoc. Doc generation runs in CI; warnings are errors
  (`#![deny(missing_docs)]`, `RUSTDOCFLAGS="-D warnings"`, Sphinx `-W`).
- **Lint the spec/docstrings**: OpenAPI linting (Spectral/Redocly CLI class) and
  docstring-coverage checks in CI, so "undocumented public symbol" is a build
  failure, not a review nitpick.
- Generated reference is necessary, not sufficient: it gives you *what*; §2
  makes it useful.

## §2 Document the why, not just the what

A signature already says what. The doc comment earns its existence by adding
what the signature can't:

- **Every public symbol documented** — function, type, field, error variant,
  config knob, CLI flag, endpoint, header. "Public" means "someone outside this
  module can depend on it," which means someone will.
- Content that belongs in a doc comment, in priority order:
  1. **Behavioral contract**: invariants, units, ranges, nullability, ordering
     guarantees, idempotency, thread-safety, blocking behavior.
  2. **Failure modes**: what errors/exceptions, under what conditions (§4).
  3. **Why / when to use**: what problem it solves, when to prefer the
     alternative (`see also` links are load-bearing).
  4. **Surprises**: anything a reasonable caller would guess wrong — costs
     (O(n²), network call, allocation), side effects, caching.
- **Bad**: `// GetUser gets a user.` Restating the name is negative-value: it
  occupies the slot where real information should be and passes docstring-
  coverage checks while adding nothing.
- **Good**:

```go
// GetUser returns the user by ID from the primary store.
// It does NOT consult the cache — use CachedUser for read paths;
// GetUser exists for read-after-write consistency in signup flows.
// Returns ErrNotFound for unknown or soft-deleted IDs (callers must
// not distinguish the two; deletion state is not part of the contract).
// Makes one DB round trip; safe for concurrent use.
```

- Module/package-level docs explain the *shape* of the package: what it's for,
  the two or three entry-point types, what it deliberately doesn't do.

## §3 Examples that execute

An example that doesn't run in CI is a claim, not an example.

- **Use the language's doctest facility**: Rust doc-examples (compiled and run
  by `cargo test` by default), Python `doctest` via pytest
  (`--doctest-modules`), Go `Example*` functions (output-checked by `go test`),
  Documenter.jl doctests. If the language lacks one, extract fenced code blocks
  from docs and compile/run them in CI (e.g., mdBook test, custom extractor).
- **Every non-trivial public entry point gets at least one example** showing the
  intended call pattern, not the minimal one. Examples are the most-read part of
  any reference page; most users copy the first example and edit.
- Examples show **realistic values and error handling**, not `foo`/`bar` and
  swallowed errors — copied example code becomes production code.
- For HTTP APIs: request/response examples in the OpenAPI doc, validated
  against the schemas in CI (example-schema mismatch is a classic silent lie).
- Quickstarts and tutorials count as examples: run them in CI on a schedule if
  full per-PR execution is too slow (rules/01 §2).

## §4 Error documentation

What can fail, and what the caller should do about it, is the half of the
contract most docs omit.

- Per operation, document: **which errors/status codes occur, what condition
  triggers each, whether retrying helps, and what the caller should do**
  (retry with backoff / fix the request / escalate / impossible-by-construction).
- HTTP: enumerate non-2xx responses in the OpenAPI doc with the error body
  schema and machine-readable codes; "default: Error" as the only error
  response is an audit finding (error shape design: `sota-api-design`).
- Libraries: document error variants where they're defined *and* which
  operations raise them; distinguish programmer errors (panic/assert — don't
  catch) from operational errors (handle).
- Error *messages* are documentation too: include what was expected, what was
  seen, and ideally a link/pointer to the fix. The error message is the doc
  page with a 100% read rate at exactly the right moment.

## §5 Versioned docs

- **Docs versions match released versions.** A user on v2 reading v3 docs gets
  lies with confidence. Docs sites carry a version switcher (mike for MkDocs,
  Sphinx multiversion, docusaurus versions, docs.rs does it for free); the
  default view is the latest *stable* release, not the dev branch.
- Docs-as-code makes this nearly free: docs are in the repo, so the tag that
  cut the release pinned the docs (rules/04 §5).
- Mark removed/changed behavior inline with the version it changed
  (“Since v2.3”, “Removed in v3.0 — use X”), because users land on pages from
  search without knowing which version they're reading.
- Pre-1.0 or internal-only projects can skip multi-version publishing, but the
  docs must still state which version they describe.

## §6 Changelog discipline

- **Format: Keep a Changelog** (keepachangelog.com, v2.0.0 — 2026-06; the
  format itself is unchanged from 1.1.x, so existing changelogs stay valid):
  `## [version] - date` sections with `Added / Changed / Deprecated /
  Removed / Fixed / Security` subsections, plus an `Unreleased` section at top
  so changes are recorded in the PR that makes them, not reconstructed at
  release time.
- **Write user-impact language, not commit dumps.** The changelog audience is
  users deciding whether and how to upgrade. `git log` is not a changelog;
  auto-generated commit lists are an input, not the product.
  - **Bad**: `refactor: extract PayoutScheduler; bump deps; fix flaky test`
  - **Good**: `Fixed: payouts scheduled across a DST boundary no longer run an
    hour early (#412).`
- Every entry names the observable change, and links the issue/PR for the
  archaeology. Internal refactors with zero user-visible effect don't appear.
- Automation (conventional commits → changelog via semantic-release /
  release-please / git-cliff — rules/04 §2) generates the *draft*; a human edits
  it into user language before release. Automation removes the blank page, not
  the editorial pass (Keep a Changelog 2.0.0 codifies the same stance for
  LLM-assisted drafting: machines draft, humans curate).
- **Changelog vs release notes**: the changelog is the complete, append-only,
  per-version record in the repo; release notes are the curated announcement
  (highlights, upgrade guidance, thanks) per release. Generate release notes
  *from* the changelog, never maintain two divergent histories.

## §7 Migration guides for breaking changes

A breaking change without a migration guide is a breaking change with the cost
shipped to every user individually.

- Required for any major version / breaking release: a guide with **every
  breaking change listed**, each with: what broke, why (one line), the exact
  before→after diff, and mechanical migration steps (codemod/script/sed where
  possible).
- Order by "what you'll hit first," not by module.
- **Deprecate before removing**: ship the new path + deprecation warnings
  pointing at the guide for ≥1 minor release before removal, so users migrate
  on warnings, not on compile errors (HTTP deprecation signaling:
  `sota-api-design`).

**Good fragment**:

```markdown
### `client.fetch()` removed → `client.get()`
Why: fetch() silently retried non-idempotent requests (#388).
Before: `resp = client.fetch(url, retries=3)`
After:  `resp = client.get(url, retry=Retry(total=3, idempotent_only=True))`
Mechanical: `npx @ourlib/codemod v3-fetch-to-get src/`
Behavior change: POSTs are no longer retried by default — opt in per call.
```

## Audit checklist

- [ ] Reference docs generated from source (OpenAPI/docstrings/rustdoc/godoc); generation runs in CI with warnings-as-errors.
- [ ] Docstring/spec lint gates exist: undocumented public symbols fail the build, OpenAPI is linted and contract-checked against the implementation.
- [ ] Doc comments carry contract/failure/why/surprises — sample 10 public symbols; name-restating docstrings are a finding.
- [ ] Doc examples compile/run in CI (doctests/Example funcs/extracted blocks); first example per page shows realistic use with error handling.
- [ ] OpenAPI examples validate against their schemas.
- [ ] Every operation documents its failure modes and the caller's correct reaction; HTTP error responses enumerated with body schema.
- [ ] Published docs are versioned to match releases; default view is latest stable; pages state the version they describe.
- [ ] CHANGELOG follows Keep a Changelog with an Unreleased section maintained in PRs; entries are user-impact language with issue/PR links, not commit subjects.
- [ ] Release notes derive from the changelog (no divergent second history).
- [ ] Breaking releases ship a migration guide: every break listed with before→after and mechanical steps; deprecation warnings preceded removal.
