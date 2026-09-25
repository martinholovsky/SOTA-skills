# 15 — Dependency Adoption (selecting, verifying and configuring what you take in)

Scope: the decision to take a **new** third-party component, and the checks that recur when
you upgrade one. `rules/03` §3.4 lists the malicious-package indicators to reject on;
this file is the positive side: what a component should show before you adopt it (§15.1),
how to confirm where it came from (§15.2), when to read its source (§15.3), and how to
configure it once it is in (§15.4). The language skills carry the ecosystem commands:
`sota-ruby` rules/04 §3.1, `sota-golang` rules/07 §4, `sota-python` rules/08 §1,
`sota-rust` rules/05 §2. This file is the language-neutral version they share.

## 15.1 The pre-adoption selection checklist

Adding a direct dependency is an architectural decision (`rules/03` §3.4): you now trust
its maintainers, their accounts and their build system for as long as you ship it. Before
the manifest line lands, record answers to these in the PR:

- **Release maturity.** Prefer a stable release. A pre-release (`-alpha`, `-beta`, `-rc`)
  or a `0.x` line signals that the API, and often the security posture, may still change
  without notice (semver: "Major version zero (0.y.z) is for initial development"). Adopt one only with a
  written reason and a plan to move to a stable line.
- **Community and adoption**: the number of maintainers (one is bus-factor risk), how many
  other projects depend on it, and whether issues and security reports get answers. Report
  the dates you read, not adjectives (`rules/10` §5).
- **Signed or attested releases.** Prefer components whose releases carry a signature or
  a provenance attestation you can verify (§15.2).
- **Analysable source.** Prefer source your linters and SAST can read over minified bundles,
  vendored binaries or obfuscated code. What your tools cannot parse, they cannot vouch for.
- **Security practice**: a published security policy with a private reporting channel
  (`rules/13` §13.8), security tests or fuzzing in its CI, and documentation on using it
  securely. OpenSSF Scorecard reports several of these as named checks (`Security-Policy`,
  `Signed-Releases`, `SAST`, `Fuzzing`, `Maintained`), for example
  `curl -s https://api.securityscorecards.dev/projects/github.com/<owner>/<repo>`.
- **Terms, limits and quotas.** For a hosted service or SDK: rate limits, quotas, pricing
  changes and terms of use (data use, retention, the right to suspend you) are failure
  modes of your product. Read them before you depend on them.

**CI plugins and actions are dependencies too.** A GitHub Action, a CI-server plugin, a
build-tool plugin or a GitHub App gets this same checklist, plus one question specific to
them: **does installing it weaken your configuration?** Examples are a plugin that opens a
listening port or webhook endpoint on the CI server, or one that asks for broader token
scopes than its function needs. Third-party actions are also inventoried in `rules/01`
§1.3, and who may install plugins and apps is `rules/12` §12.6.
(OWASP: CI/CD Security cheat sheet; Django REST Framework cheat sheet; Proactive Controls
2024 C6; Secure Product Design cheat sheet; Software Supply Chain Security cheat sheet;
SCVS 5.1)

## 15.2 Point of origin and chain of custody for consumed components

A package name tells you what you asked for. It does not tell you who built it or from
which source. Check both on adoption, and keep the evidence.

- **Repository match.** The package's declared source repository is self-asserted by the
  publisher. Confirm that the repository really builds this package name, and that the
  release corresponds to a tag or commit in it.
- **Provenance attestation or trusted-publisher flag.** Where the registry exposes one,
  prefer versions published with verified provenance. deps.dev reports it for npm and PyPI
  versions (`attestations[]` with `sourceRepository` and `verified`): `curl -s
  https://api.deps.dev/v3/systems/npm/packages/<pkg>/versions/<ver> | jq -e
  '[.attestations[]? | select(.verified)] | length > 0'` exits `0` when a verified
  attestation exists (measured 2026-09-25 on two packages: one with, one without). PyPI
  serves the same data per file at `/integrity/<project>/<version>/<filename>/provenance`;
  `npm audit signatures` verifies registry signatures and provenance attestations for
  what is installed.
- **Flag publishing without MFA or trusted publishing** where the registry exposes it (for
  example RubyGems' `rubygems_mfa_required` metadata, `sota-ruby` rules/04 §3.1). A popular
  package whose releases stop carrying provenance is a signal to investigate before
  upgrading, not only at adoption.
- **Chain of custody from fetch to build.** Fetch through your proxy (`rules/03` §3.3),
  lock the hash (`rules/03` §3.1), and keep the proxy's fetch log and the build's
  provenance, so that for any shipped artifact you can say which upstream bytes went in and
  when they were fetched. A component that entered through a side channel (a download in a
  build script, a copied tarball) breaks that chain (`rules/04` §4.1).
  (OWASP: SCVS 4.5, 6.1, 6.2)

## 15.3 Analyse the dependency's source on adoption and review the diff on upgrade (risk-scoped)

SCA answers "does this version have a **known** advisory?" It says nothing about a
deliberately malicious or simply dangerous change that nobody has reported yet. For the
dependencies that matter, read the code, and scope the effort by risk so that it stays
affordable:

- **Decide which dependencies are high-risk**: new direct dependencies; anything that runs
  at install or build time (`rules/03` §3.4); anything on an authentication, crypto, parsing
  or network path; anything with native code; anything with a single maintainer.
- **On adoption, run your linters and SAST over the dependency's source**, not only over
  your code: run the scanner **from inside** the unpacked package, sdist, crate or module.
  Look for install hooks, network calls, dynamic code evaluation and obfuscated strings, and
  for the weaknesses your own rules encode. Plant one known hit first: measured with
  opengrep 1.23.0 (2026-09-25), `opengrep scan --config rules.yml node_modules/evil` from
  the repository root reported **0** findings on a planted `eval`, because the default
  ignore list skips `node_modules`; the same scan run inside `node_modules/evil` reported 1.
- **On upgrade, review the diff between the two published versions** rather than the
  changelog: `npm diff --diff=<pkg>@<old> --diff=<pkg>@<new>`, `cargo vet diff <crate>
  <old> <new>` (`sota-rust` rules/05 §2), or a plain diff of the two unpacked archives.
  Compare the **published artifacts**, because the tarball can differ from the tagged
  source.
- **Record the review** where the next reviewer will find it (a `cargo vet` audit entry,
  or a note in the PR that bumps the version), so that the same version is not reviewed
  twice or skipped because someone assumed it had been read.
- **Low-risk dependencies** (dev-only, sandboxed, pure data) get SCA plus the §15.1
  checklist. Say so explicitly, so that the scoping is a decision and not an accident.
  (OWASP: DSOMM; SAMM; Software Supply Chain Security cheat sheet; SCVS 5.2, 5.3)

## 15.4 Review and harden the security-relevant defaults of what you consume

A library's defaults are chosen for a quick start, not for your threat model, and they
become your code the moment you call it. For every component on a trust boundary, read its
security documentation and set the security-relevant options **explicitly**:

- **Parsers**: external-entity and DTD handling for XML, object-instantiating modes for
  YAML or JSON, size and depth limits (`sota-code-security` rules/01 §6, §8).
- **TLS clients**: certificate verification on, minimum protocol version set, no
  "insecure" switch left from a quick-start example.
- **Deserialisation**: allowlists of types, never "load anything"
  (`sota-code-security` rules/01 §8).
- **Debug and admin features**: debug mode, stack traces in responses, introspection
  endpoints, default admin accounts, all off in production.
- **Timeouts and limits**: some HTTP clients wait indefinitely when none is set (Go's
  `http.Client`: "A Timeout of zero means no timeout").

Put the chosen settings in one reviewed place (a wrapper or factory the codebase must use)
so that each call site does not re-decide them. Language examples with verified defaults
are in `sota-ruby` rules/04 §3.1 and `sota-golang` rules/07 §4. A README snippet copied
into production carries its demo settings with it; compare it against the component's
security documentation before merging.
(OWASP: Proactive Controls 2024 C6)

## Audit checklist

- [ ] **New dependencies carry a recorded selection review (§15.1), Medium:** `git diff <base> -- package.json | grep -E '^\+[[:space:]]*"[^"]+":[[:space:]]*"[~^]?(0\.[0-9]|[0-9]+\.[0-9]+\.[0-9]+-(alpha|beta|rc|pre|next|canary|dev))'` (and the equivalent for other manifests) prints nothing, or each hit has a written reason; each new direct dependency, action or CI plugin has its §15.1 answers in the PR, including whether it opens ports or widens token scopes
- [ ] **Origin verified for adopted components (§15.2), Medium:** for new npm/PyPI dependencies, `curl -s https://api.deps.dev/v3/systems/npm/packages/<pkg>/versions/<ver> | jq -e '[.attestations[]? | select(.verified)] | length > 0'` exits `0`, or the absence of provenance is recorded and accepted; `npm audit signatures` passes in CI for npm projects; builds fetch only through the proxy
- [ ] **High-risk dependencies read, not only scanned (§15.3), Medium:** a written risk scoping exists; adoption PRs for high-risk dependencies record a SAST run over the dependency's source, run from inside the package directory with a planted known hit reported; upgrade PRs for them record a published-artifact diff review (`npm diff`, `cargo vet diff`)
- [ ] **Security-relevant defaults set explicitly (§15.4), High on a trust boundary:** `grep -rn -E 'verify[[:space:]]*=[[:space:]]*False|InsecureSkipVerify:[[:space:]]*true|rejectUnauthorized:[[:space:]]*false|VERIFY_NONE|^[[:space:]]*DEBUG[[:space:]]*=[[:space:]]*True' .` over production code and config is empty; parser, deserialiser and client options are set in one reviewed wrapper
