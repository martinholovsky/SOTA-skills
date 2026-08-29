# 03 — Dependencies & Supply Chain (lockfiles, registries, SBOM, scanning, updates)

Scope: everything that enters your build from outside the repo. The attacker's cheapest
path into your software is publishing a package you'll install. Controls: determinism
(lockfiles), provenance of resolution (registry scoping), visibility (SBOM), detection
(scanners + indicators), and disciplined update flow.

## 3.1 Lockfiles always, installs frozen

**Rule: every manifest has a committed lockfile, and CI/build installs refuse to deviate
from it.** An install that resolves versions at build time means the code you reviewed is
not the code you shipped, and yesterday's green build can be today's compromised one.

| Ecosystem | Lockfile | Frozen install (CI) |
|---|---|---|
| npm/pnpm/yarn | package-lock.json / pnpm-lock.yaml / yarn.lock | `npm ci` / `pnpm install --frozen-lockfile` / `yarn install --immutable` |
| Python | uv.lock / poetry.lock / requirements.txt **with hashes** | `uv sync --locked` / `poetry install --no-root` (lock checked) / `pip install --require-hashes -r requirements.txt` |
| Go | go.sum (+GONOSUMCHECK never set) | `go mod verify`; `GOFLAGS=-mod=readonly` |
| Rust | Cargo.lock (commit it for libs too) | `cargo build --locked` |
| Ruby | Gemfile.lock | `bundle install --frozen` / `BUNDLE_FROZEN=true` |
| Docker | digest pins (rules/04 §4.3) | `FROM image@sha256:...` |

- BAD: `pip install -r requirements.txt` with bare `package>=1.2` lines in CI. BAD:
  `npm install` in CI (mutates the lockfile silently). BAD: a `Dockerfile` that
  `pip install`s unpinned packages even though the repo has a lockfile.
- Hash-pinning beats version-pinning: `--require-hashes` / go.sum / `npm ci` integrity
  fields also defend against registry-side substitution of an existing version.
- Lockfile *diffs* are review surface: a 4000-line lockfile churn hiding one malicious
  resolution is the attack. Use dependency-review gates (§3.2) rather than asking humans
  to read lockfiles.
- Audit: missing lockfile = High; lockfile present but unfrozen CI install = High (the
  lockfile is decorative).

## 3.2 Dependency review gates

**Rule: PRs that change dependencies pass an automated diff-aware gate** — new/changed
packages checked for known vulns, license, and (where supported) supply-chain signals,
blocking on policy.

```yaml
# GitHub: dependency review on every PR
permissions: { contents: read }
on: pull_request
jobs:
  dep-review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@<sha> # v4
      - uses: actions/dependency-review-action@<sha> # v4
        with:
          fail-on-severity: high
          deny-licenses: AGPL-3.0-only, AGPL-3.0-or-later, SSPL-1.0
          comment-summary-in-pr: on-failure
```

- This must be a **required check** (rules/05 §5.6) or it's advisory noise.
- Complement with OSV/grype full scans on schedule (§3.6) — the PR gate only sees diffs.
- For ecosystems GitHub doesn't cover well, run `osv-scanner --lockfile` diff against the
  base branch in the PR workflow.

## 3.3 Dependency confusion & registry scoping

The attack: you depend on internal package `acme-utils`; attacker publishes `acme-utils`
9.9.9 to the public registry; a resolver that merges public+private indexes picks the
higher version. This breached Apple/Microsoft/PayPal builds (Birsan, 2021) and still works
wherever config is sloppy.

- **npm**: every internal package under a scope (`@acme/utils`); `.npmrc` maps the scope:
  `@acme:registry=https://npm.internal.acme/` — scoped resolution never falls through to
  npmjs. Also claim your scope on the public registry. Unscoped internal names = High.
- **pip**: `--extra-index-url` is the vulnerability — pip treats all indexes as equal and
  picks the best version across them. Use a single `index-url` pointing at a proxy
  (Artifactory/Nexus/devpi) that routes internal names internally and proxies PyPI for the
  rest, with **exclusion patterns** so internal names can never be fetched upstream. Any
  `extra-index-url` mixing public+private = High.
- **Go**: `GOPRIVATE=*.internal.acme.com,github.com/acme/*` so the public proxy/sumdb is
  never consulted for private modules (also prevents leaking module names).
- **Generic**: register/reserve your internal package names (or a namespace) on public
  registries; alert on any public publication matching internal naming patterns.

```ini
# GOOD — .npmrc: scoped registry, no fallthrough for internal packages
@acme:registry=https://npm.internal.acme/
registry=https://registry.npmjs.org/

# GOOD — pip.conf: ONE index (a routing proxy), not index + extra
[global]
index-url = https://pypi-proxy.internal.acme/simple/

# BAD — pip.conf: resolver races public vs private, highest version wins
[global]
index-url = https://pypi.org/simple/
extra-index-url = https://pypi.internal.acme/simple/
```
- Artifact proxy bonus: a caching proxy gives you an immutable local copy (left-pad/
  unpublish resilience), an audit log of everything fetched, and a single enforcement
  point — strongly preferred over direct registry access from CI.

## 3.4 Typosquatting & malicious-package indicators

Review *new* dependencies (human + automated) for:

- **Install-time execution**: npm `preinstall`/`install`/`postinstall`, Python `setup.py`
  arbitrary code. Most npm malware fires at install. Mitigation:
  `npm ci --ignore-scripts` in CI plus an explicit allowlist step for the few packages
  that genuinely need scripts (e.g., rebuild native deps deliberately); pnpm does this by
  default via `onlyBuiltDependencies`.
- **Name proximity** to a popular package (`lodahs`, `python-dateutil` vs `dateutil`),
  starjacking (README/links pointing at an unrelated popular repo).
- **Slopsquatting** (OWASP "Secure Coding with AI"): AI coding assistants routinely
  invent plausible-but-nonexistent package names, and attackers pre-register them.
  **Verify every AI-suggested dependency actually exists with real history** (downloads,
  age, repo) before adding it — never `pip install`/`npm i` a name straight from a model.
  An approved-package allowlist plus the §3.7 cooldown blunts both this and typosquats.
- **Freshness/maintainer churn**: version published < 5–7 days ago (see cooldown, §3.7),
  brand-new maintainer on an old package, ownership transfer right before a release —
  the xz-utils pattern.
- **Payload smells**: minified/obfuscated code in a source package, hex/base64 blobs,
  `eval`/`Function` on decoded strings, network calls in install scripts, binary files in
  packages that should be pure source, postinstall fetching second-stage from a URL.
- Tooling: OpenSSF Scorecard for repos you depend on heavily; `osv-scanner` covers known
  malicious packages (MAL- advisories); GitHub/registry advisories for hijacked versions.
- Process: adding a dependency is an architectural decision — require PR description to
  justify new direct deps; prefer zero-dep or stdlib solutions for trivial needs
  (left-pad lesson: every dep is a maintainer you now trust forever).

### 3.4.1 Lockfile poisoning in PRs

The lockfile itself is an attack vector: a PR can edit `package-lock.json` to point an
existing package name at a different `resolved` URL or tampered `integrity` hash while
the human reviews only `package.json` (which may be unchanged). Defenses:

- Dependency-review gate (§3.2) reads the lockfile diff, not the manifest.
- `npm ci` verifies integrity hashes, but the hash in the lockfile is the attacker's hash
  — pair with `lockfile-lint` (or pnpm's `verifyStoreIntegrity`) asserting all `resolved`
  URLs point at allowed registries:
  `lockfile-lint -p package-lock.json --allowed-hosts npm registry.npmjs.org npm.internal.acme --validate-https`
- Treat lockfile-only PRs from non-bot authors with extra suspicion; bots (Renovate)
  should be the main lockfile writers.

## 3.5 SBOM generation (CycloneDX / SPDX)

**Rule: every release artifact gets an SBOM, generated at build time, stored where it can
be queried fleet-wide.** When the next log4shell drops, "are we affected, where?" must be
a query, not an archaeology project.

- Generate from the **lockfile + the built container** (both — the lockfile knows your app
  deps, the image scan knows OS packages and whatever the base image smuggled in):
  `syft <image-digest> -o cyclonedx-json` or `cdxgen` for richer app-level data.
- Format: CycloneDX or SPDX — pick one org-wide; both are fine, conversion is lossy, so
  standardize. Include component hashes and (where available) PURLs — PURLs are what make
  cross-referencing advisories automatic.
- Bind it: attach as an in-toto attestation on the image digest (rules/02 §2.4) and/or
  upload to a central store (Dependency-Track, GUAC). An SBOM in a CI artifact zip that
  expires in 90 days fails the log4shell test.
- Regenerate per build (SBOMs of `:latest` are meaningless); SBOM the *artifact*, not the
  repo.
- Audit severity: no SBOMs = Medium (it's a visibility control); SBOMs generated but not
  centrally queryable = Low-Medium honesty finding.

## 3.6 Vulnerability scanning with triage discipline

Scanners: `osv-scanner` (lockfiles, fast, OSV-native), `grype`/`trivy` (containers + OS
packages). Run: diff-aware on PRs (§3.2), full scan on default branch per build, and
**scheduled daily** scans of *deployed* digests (new CVEs apply to old builds — the
schedule, not the PR gate, catches those).

Triage discipline — the part everyone fails:

- **Severity ≠ priority.** Triage on: is the vulnerable function reachable
  (govulncheck does call-graph reachability for Go; for others, manual assessment), is the
  component exposed, is there a known exploit (CISA KEV, EPSS). A reachable Medium in your
  auth path outranks an unreachable Critical in a build-time tool. Recent grype releases
  bundle KEV and EPSS data and sort output by a computed risk score — use that ordering
  as the triage queue instead of bolting KEV lookups on by hand.
- **Applicability is a fourth axis, and it lives in the advisory prose, not in the
  score.** "Affected only on 32-bit platforms", "only when feature X is enabled",
  "only the CLI entrypoint, not the library" is neither reachability nor exposure
  nor KEV — and no scanner ordering reflects it, because a scanner reads the
  affected *version range* and the CVSS vector, not the paragraph that rules you
  out. Open the advisory and read its affected-platform / affected-configuration
  text before triaging. When it excludes you, that is a `not_affected` VEX
  (`vulnerable_code_not_present` when the affected code is not built for your
  platform; `vulnerable_code_not_in_execute_path` when the affected feature is off),
  not an ignore-with-expiry — the justification list is closed, so pick from it
  rather than writing prose.
- **Record decisions as VEX** (OpenVEX): `not_affected` with justification
  (`vulnerable_code_not_in_execute_path`, etc.) or `affected` + remediation deadline. Feed
  VEX back into scanners so triaged findings stop re-alerting — that's what keeps the gate
  credible.
- **Ignore files have expiry dates and owners.** A `.grype.yaml` ignore without an
  expiration and a linked justification is how gates rot:

```yaml
# GOOD: .grype.yaml
ignore:
  - vulnerability: CVE-2026-1234
    reason: "not reachable: vuln in XML parser, we never parse XML (VEX: vex/CVE-2026-1234.json)"
    # review-by: 2026-09-01  — enforce via scheduled job that fails on stale ignores
```

- SLAs by triaged priority (e.g., exploited-known: 48h; critical reachable: 7d; high: 30d)
  with the scheduled scan enforcing them — not "fail the PR for a CVE that was already
  there", which just teaches people to bypass.
- BAD patterns to flag: global `--severity-threshold critical` only (blind to exploited
  Highs); scanner runs with `continue-on-error: true`; one giant ignore list dated two
  years ago; scanning only on PR (never re-scanning deployed images).
- **No upstream patch available** (reachable vuln, no fixed version): triage doesn't stop
  at "no fix" (OWASP Vulnerable Dependency Management). In order of preference — guard the
  vulnerable call path with input validation/feature-flag kill-switch; virtual-patch at
  the edge (WAF/admission, sota-detection-engineering); fork-and-patch with an upstream PR
  and a regression test reproducing the vuln (§3.8); or replace the dependency. Record the
  chosen mitigation as VEX and set a re-check date — never just ignore-with-expiry.

## 3.7 Renovate / Dependabot strategy

Unmanaged: drift until a CVE forces a terrifying 40-major-version jump. Unthrottled: you
auto-install malware minutes after it's published. The strategy:

- **Cooldown**: Renovate `minimumReleaseAge: "5 days"` (Dependabot: cooldown config) for
  public packages — most malicious versions are yanked within days. Exception: security
  updates bypass cooldown.
- **Group** related updates (monorepo presets, `group:allNonMajor` for dev-deps) to keep
  review load sane; never group majors.
- **Automerge** only: dev/test dependencies + patch/minor + full required-check suite
  green + cooldown passed. Production runtime deps get human review. Automerge without a
  meaningful test suite is auto-deploying strangers' code.
- Pin GitHub Actions digests (`helpers:pinGitHubActionDigests`) and Docker digests
  (Renovate updates the digest AND the version comment — best of both).
- Security updates (osv/GitHub advisories) get separate, immediate, clearly-labeled PRs.
- Audit: no update automation = Medium (guaranteed drift); automerge of runtime deps
  without cooldown = High.

```json5
// renovate.json — reference posture
{
  "extends": ["config:recommended", "helpers:pinGitHubActionDigests",
              ":pinDevDependencies", "docker:pinDigests"],
  "minimumReleaseAge": "5 days",
  "packageRules": [
    { "matchDepTypes": ["devDependencies"], "matchUpdateTypes": ["patch", "minor"],
      "automerge": true },
    { "matchUpdateTypes": ["major"], "automerge": false, "addLabels": ["major-update"] }
  ],
  "vulnerabilityAlerts": { "labels": ["security"], "minimumReleaseAge": null },
  "osvVulnerabilityAlerts": true
}
```

Renovate itself is a powerful bot: it needs PR-write only — review which app/token it
runs as and whether automerge bypasses required checks (it must not; automerge should
use the platform merge with required checks intact).

## 3.8 Vendoring tradeoffs

Vendoring (committing dependency source) is occasionally right, mostly wrong:

- **For**: hermetic builds with no registry availability risk; immune to unpublish/
  registry compromise *after* vendoring; full diff visibility on every update.
- **Against**: updates become manual and rot (the real-world failure mode: vendored copy
  with 3-year-old CVEs invisible to scanners that only read manifests); license
  obligations travel with the code; repo bloat.
- If you vendor: automate the refresh (`go mod vendor` in the update PR, Renovate still
  manages versions), ensure SBOM/scanners see vendored components (syft does for standard
  layouts), and never hand-patch vendored code without an upstream issue + a tracking
  comment (silent forks are unmaintainable).
- Middle path that usually wins: pull-through proxy with retention (§3.3) — registry-
  outage resilience without the rot.

## 3.9 Declared but not reached — the inert-dependency sweep

§3.6 asks whether what you ship is *vulnerable*. It never asks whether a declared
dependency is **reached at all**. An unreached dependency is pure liability: install-time
execution surface (§3.4), a lockfile entry to upgrade forever, license obligations, build
time, and a CVE queue for code that never runs. It is also the cheapest finding in an
audit — the fix is a deletion.

Run it as its own pass over **direct dependencies, registered modules, and plugins**. The
BUILD-side gate on *adding* a dependency lives in the language skills (`sota-golang`
rules/05 §8, `sota-javascript-typescript` rules/05); this is the sweep for what already
landed.

Severity: an unreached dependency is **Low** on its own — nothing exploitable, only debt.
Rate it **Medium** when it runs install hooks (§3.4), ships into the runtime artifact, or
carries an open advisory: that is exploit surface carried for zero function.

### 3.9.1 Reachability, not import presence

Trace from a **real entrypoint** — `main`, the route table, the scheduler/cron
registration, the module or plugin registry, the DI container wiring — to the dependency's
API. An import statement is not reachability; it is the thing that makes an inert
dependency look alive to every static tool.

Three traps:

- **A reference on a path that cannot execute.** A `switch`/`match` arm for a type the live
  decoder cannot emit, a handler registered for an event no producer sends, an adapter
  selected by a config value nothing sets. The symbol is genuinely referenced, so tools and
  greps mark the dependency used — but the branch is unreachable. One step earlier than
  this is `sota-code-security` rules/14 §4 (a gate whose trigger never fires); the same
  two-axis check applies — *has this path ever executed*, not *does it exist*.
- **Side-effect-only imports.** `import _ "…"` for a driver, a decorator that registers
  into a table, a plugin discovered by entry point. Legitimate — but confirm something
  *reads* that table, or you have a registration nobody consumes.
- **The reverse trap — dynamic loading.** Reflection, service loaders, `importlib`,
  `require` by string, Rails autoload, DI-by-convention, plugin manifests. Here a
  dependency with **no static reference is still reached**, so the tools below produce
  false *positives*. Search config, manifests, and IaC for the package/class name as a
  **string**, not only the code for a symbol.

### 3.9.2 Tools, each with its blind spot

No tool's silence is proof (§3.9.3). Use one to generate candidates, then prove each one.
Verify the tool's current name and maintenance before you trust it (`sota/rules/01` §3) —
two of the projects below have been renamed under their old URLs.

| Ecosystem | Tool | Blind spot to state when you cite it |
|---|---|---|
| Go | `go mod why -m <module>` prints `(main module does not need module …)`; `go mod tidy` + `git diff --exit-code` in CI (§8 of `sota-golang` rules/05) | `why` queries the graph of `go list all`, which **includes tests of reachable packages**: a module needed only by your *dependencies'* tests reads as reached until you pass `-vendor`, and one needed only by your *own* tests reads as reached either way |
| JS/TS | `knip --include dependencies` (`sota-javascript-typescript` rules/07) | documents its own false positives: unresolved dynamic specifiers (`import(path.join(dir, x))`), config files a plugin's dependency-finder doesn't parse, and **entry/project globs that miss files** — "dependencies imported in unused files are reported as unused dependencies", so triage unused *files* first |
| Python | `deptry .` — DEP002 unused, DEP003 transitive-but-imported, DEP005 stdlib shadowed | static import analysis: entry-point/plugin packages and `importlib` loads read as unused |
| Rust | `cargo machete` (stable) or `cargo +nightly udeps` | machete is deliberately imprecise — false positives for deps used only from `build.rs`-generated code and for crates whose import name differs from the package name (`--with-metadata` fixes the latter). udeps needs **nightly** and documents false *negatives*: deps also used by std or by your own deps go undetected |
| JVM | `mvn dependency:analyze` (`analyze-only` inside the lifecycle) with `failOnWarning` — default is `false`, so it is advisory until you set it | its FAQ is explicit: "dependency analysis is done at bytecode level: anything that doesn't get into bytecode isn't detected" — inlined constants, source-retention annotations, javadoc links. "If the only use of a dependency consists of such undetected constructs, the dependency is analyzed as unused." Override per-dep with `usedDependencies` |
| PHP | `composer-unused` (`vendor/bin/composer-unused`; needs `composer install` first) | static; container- and config-string wiring is invisible |
| .NET | `ReferenceTrimmer` (modest adoption — treat as a candidate generator only): MSBuild task + Roslyn analyzer over the compiler's `GetUsedAssemblyReferences` | it skips SDK/target-framework references, transitives, and packages carrying build files; in symbol-analysis mode "references used only in XML documentation comments will be reported as removable" |
| Ruby | **no established tool** — the candidates are single-maintainer and low-adoption | dynamic `require`, autoload, and monkey-patching defeat static analysis by construction; go straight to §3.9.3 |

### 3.9.3 Proof by construction — delete it and build

A grep is not proof, and neither is a tool's silence. The finding is not "X looks unused";
it is **"X was removed and the real build, lint/vet, and full test suite still passed."**

1. **Copy the repo to a scratch directory.** The audit is read-only (`sota/rules/01` §4) —
   never mutate the tree under audit.
2. **Remove the declaration and regenerate the lockfile.** Manifest edit alone leaves the
   package resolvable.
3. **Run what CI runs** — build + vet/lint + the full suite, not a subset.
4. **Report exact commands, exit codes, and before/after counts** — `go mod graph | wc -l`,
   the lockfile's package count, the resolved module total.
5. **If it still builds, that is the finding.** If it fails, you have a *reached*
   dependency and the compiler just named the call site for you — record that as the
   reachability evidence and close the candidate.

Two traps that make a green run lie (same shape as `sota-code-security` rules/12 §1, where the mutation is a
no-op'd control rather than a removed package):

- **The deletion did not take.** A vendored copy still on disk, a lockfile not regenerated,
  a workspace sibling still declaring it, a cached build layer, a stale `target/`
  or `node_modules`. **Assert the absence has runtime effect** — the resolver errors, the
  import fails — before trusting green.
- **The suite never exercised the path.** A dependency reached only from an integration or
  e2e job you did not run reads as removable. **State which suites ran**: a build-only
  proof is a bounded claim ("removable without breaking `go build` and `go test ./...`"),
  not "unused".

### 3.9.4 Leverage ratio — what you use vs what you inherit

For each *live* dependency, count the API surface you actually call against the transitive
modules it pulls in (`go mod graph`, `cargo tree`, `npm ls --all`, the lockfile). **Fewer
than ~5 symbols used while inheriting more than ~10 modules** is a replace-in-house
candidate — flag it, with both numbers.

The ratio is a trigger for the decision in §3.9.5, never the decision itself. A single-call
dependency that implements something on the do-not-reimplement list stays.

### 3.9.5 Upstream health — a primary source fetched this session

Operating principle 0 applies with full force here: "actively maintained" recalled from
training data is exactly the claim that rots. Fetch it, and **report the dates rather than
an adjective** — "last push 2026-04-27" is a fact; "actively maintained" is an opinion with
an expiry date.

```bash
# archived/disabled flags, push and update timestamps, license
gh api repos/<owner>/<repo> \
  --jq '{full_name, archived, disabled, pushed_at, updated_at, license: .license.spdx_id}'

# contributor count: rel="last" page number == contributors, at per_page=1
gh api "repos/<owner>/<repo>/contributors?per_page=1" --include | grep -i '^link:'
```

- **Read `full_name` back — `gh api` follows renames silently.** Verified 2026-07-30:
  `repos/fpgmaas/deptry` answers as `osprey-oss/deptry`, and
  `repos/icanhazstring/composer-unused` as `composer-unused/composer-unused`. A 200 under
  the name in your manifest is **not** evidence the project is still where you think it is.
  A 404 is a different finding (deleted, private, or renamed *and* the redirect dropped).
- **`archived: true` is the easy case.** The common one is a never-archived repo that
  nobody maintains — which is why the dates and the contributor count matter more than the
  flag. Read the README and repo description for an explicit unmaintained-or-successor
  notice.
- **Neither timestamp is a release-cadence signal.** `pushed_at` tracks push activity and
  `updated_at` also moves on metadata-only changes (description, wiki). A repo with a
  recent `pushed_at` and no release in two years is still drifting — read the release feed
  as well, and say which of the three you are citing.
- Non-GitHub hosts: the registry's own metadata plus the project's release feed. For
  dependencies you rely on heavily, OpenSSF Scorecard (§3.4).

### 3.9.6 Classify every finding into exactly one bucket

- **A. DELETE** — unreached, with the §3.9.3 proof attached (commands, exit codes,
  before/after counts). Effort: trivial.
- **B. REPLACE IN-HOUSE** — reached, but small, well-specified, non-security-critical, and
  a poor leverage ratio. Give a line-count estimate *and* name the owner afterwards: the
  real cost is maintaining it forever, not writing it once.
- **C. KEEP** — healthy, or too complex / too security-critical to reimplement. **Never
  recommend an in-house implementation of:** crypto primitives or protocols, TLS,
  JWT/JOSE, CORS, session cookies, WebAuthn/FIDO2, password hashing, or YAML/XML/PDF/
  archive parsing — *and* **never of an algorithm whose output is persisted and must stay
  comparable with stored data** (fuzzy or locality-sensitive hashes, similarity digests,
  tokenizers, ID/slug derivations). A reimplementation that is merely *equivalent* still
  invalidates every stored value it has to compare against, and the failure is silent —
  comparisons keep returning answers, just wrong ones (`sota-code-security` rules/10). The
  library-wide stance is in `sota/SKILL.md`: use a vetted library, don't roll your own.

  **For protocols the line is which side you are on** — added 2026-07-31 after this
  clause was found genuinely ambiguous on a request signer. Primitives are out
  unconditionally. A *protocol* is out whenever **this** system is the **validating**
  side: there a canonicalisation, parsing or comparison bug fails **permissively and
  silently** — it accepts what it should reject, and nothing errors. That is the
  rules/10 family and it is the reason the prohibition exists. Composing stdlib
  primitives per a published spec to produce something a **remote authority validates**
  is a different class: a wrong signature is rejected on the first request, loudly. If
  you take that path, **state which side you are on**, pin the spec version you
  implemented, and test against the publisher's own vectors where they exist. When you
  cannot say which side fails first, treat it as validating and keep the library.
- **D. UNMAINTAINED but must keep** — name the maintained fork or successor and the date
  you checked it. If none exists, say so; the migration is a roadmap item with an owner,
  not a one-line fix.

### 3.9.7 "Unused" is an absence claim

It carries the heavier burden of router principle 3 and `sota/rules/03` §2: before writing
*unused*, search twice by **different methods** and state both. A static tool plus the
§3.9.3 deletion proof is a valid pair. Two greps are not a pair — and given §3.9.1's
dynamic-loading trap, a code-only search is structurally incapable of settling it.

## Audit checklist

- [ ] Lockfiles committed for every manifest; CI/Docker builds use frozen/hash-verified installs; no `npm install`/bare `pip install` in CI
- [ ] Dependency-review gate on PRs, required, failing on high severity + license denylist
- [ ] No `--extra-index-url` public/private mixing; npm internals scoped; GOPRIVATE set; internal names reserved publicly; fetches go through a caching proxy with audit log
- [ ] Install scripts disabled by default in CI (`--ignore-scripts`/pnpm allowlist); new-dependency review covers install hooks, obfuscation, maintainer churn
- [ ] SBOM (CycloneDX/SPDX) generated per artifact from lockfile + image, attached to the digest, queryable centrally
- [ ] Scanning: PR diff gate + scheduled scans of deployed digests; triage uses reachability/KEV/EPSS **and the advisory's own affected-platform/affected-configuration text** (§3.6); decisions recorded as VEX; ignores have owner + expiry; SLAs enforced
- [ ] Renovate/Dependabot active with cooldown (`minimumReleaseAge`), grouping, automerge restricted to dev/patch with green required checks; Actions + Docker digests auto-pinned
- [ ] Vendored deps (if any) are scanner-visible, auto-refreshed, and unpatched (or patches tracked upstream)
- [ ] **Inert-dependency sweep run (§3.9)**: every direct dependency, registered module, and plugin traced to a real entrypoint — not just to an import — with the impossible-path and dynamic-loading traps checked in both directions
- [ ] Each "unreached" claim **proven by deletion** in a scratch copy: real build + lint/vet + full suite, with commands, exit codes, before/after transitive counts, and which suites ran — and the deletion asserted to have taken effect
- [ ] Leverage ratio computed for live deps (symbols called vs transitive modules inherited); <5-symbols/>10-modules candidates flagged with both numbers
- [ ] Upstream health fetched **this session** from a primary source (`gh api repos/<o>/<r>` → `archived`, `pushed_at`, contributor count; `full_name` read back for silent renames), reported as dates not adjectives
- [ ] Every finding classified DELETE / REPLACE IN-HOUSE / KEEP / UNMAINTAINED-but-keep, with the successor named for D and nothing on the do-not-reimplement list proposed for B
