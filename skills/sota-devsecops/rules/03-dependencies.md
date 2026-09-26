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
| Python | uv.lock / poetry.lock / requirements.txt **with hashes** | `uv sync --locked` / `poetry check --lock && poetry install --no-root` / `pip install --require-hashes -r requirements.txt` |
| Go | go.mod (pins) + go.sum (authenticates); `GOSUMDB=off` / wildcard `GONOSUMDB` never set | `go mod verify`; CI fails on a dirty `go mod tidy` diff |
| Rust | Cargo.lock (commit it for libs too) | `cargo build --locked` |
| Ruby | Gemfile.lock | `BUNDLE_FROZEN=true bundle install` (the `--frozen` flag is removed in Bundler 4 and raises) |
| Docker | digest pins (rules/04 §4.3) | `FROM image@sha256:...` |

- **A frozen-install command can fail closed on a *stale* lock and open on a *missing* one.**
  Measured 2026-09-14 on Poetry 2.4.3: with `poetry.lock` desynced from `pyproject.toml`,
  `poetry install --no-root` exits **1** (`pyproject.toml changed significantly since
  poetry.lock was last generated`) — the check works. With **no lock file at all** the same
  command resolves fresh, installs, writes a lock and exits **0** — this section's own BAD
  pattern, at a green build. `poetry check --lock` exits 1 in *both* cases, which is why it
  goes first. Ask of every cell in this column: *what does it do when the lockfile is
  absent rather than wrong?*
- **Go has no lock file, by design — and is frozen anyway.** The [modules
  reference](https://go.dev/ref/mod#minimal-version-selection) is explicit: *"Unlike other
  dependency management systems, the build list is not saved in a 'lock' file … MVS is
  deterministic, and the build list doesn't change when new versions of dependencies are
  released."* `go.mod` pins, `go.sum` authenticates. So `-mod=readonly` is not the control it
  looks like — build commands have behaved that way **by default since Go 1.16** ("report an
  error if a module requirement or checksum needs to be added or updated"); setting it
  explicitly only guards against an inherited `-mod=mod` or a stray `vendor/`. `go mod verify`
  is narrower still: it checks the **local download cache** was not modified after download,
  not that the graph matches the repo. The control that earns its place is failing CI on a
  dirty `go mod tidy` diff (`sota-golang` rules/07 §4).
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

- This must be a **required check** (`rules/09` §1) or it's advisory noise.
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
- **Package-manager config is committed and read-only during the build.** `.npmrc`,
  `pip.conf`/`uv.toml`, `.yarnrc.yml`, Go env in the CI file: CI uses the reviewed copy, and
  no step rewrites it (`npm config set`, `pip config set`, `go env -w`). Switches that turn
  off TLS or checksum verification are findings wherever they appear: npm
  `strict-ssl=false`, pip `--trusted-host`/`PIP_TRUSTED_HOST`, uv `--allow-insecure-host`,
  `GOINSECURE`, `GOSUMDB=off`, `NODE_TLS_REJECT_UNAUTHORIZED=0`. Optionally a scheduled
  health job checks registry reachability, cache permissions and cached-artifact checksums.
  (OWASP: CI/CD Security cheat sheet; NPM Security cheat sheet; SCVS 3.5, 4.16)

## 3.4 Typosquatting & malicious-package indicators

Review *new* dependencies (human + automated) for:

- **Install-time execution**: npm `preinstall`/`install`/`postinstall`, Python `setup.py`
  arbitrary code. Most npm malware fires at install. Mitigation:
  `npm ci --ignore-scripts` in CI plus an explicit allowlist step for the few packages
  that genuinely need scripts (e.g., rebuild native deps deliberately); pnpm blocks
  dependency build scripts by default and takes an explicit allowlist — `allowBuilds`
  (a map of matchers to `true`/`false`). **`onlyBuiltDependencies` was removed in pnpm
  v11**, along with `onlyBuiltDependenciesFile`, `neverBuiltDependencies`,
  `ignoredBuiltDependencies` and `ignoreDepScripts` (verify the latest stable's
  settings at [pnpm settings/build](https://pnpm.io/settings/build)). Keep
  `strictDepBuilds` on — added in v10.3.0, default `true` since v11.0.0, it *"will exit with a non-zero exit
  code if any dependencies have unreviewed build scripts"*, which is the half that fails
  the build rather than warning. `dangerouslyAllowAllBuilds: true` reverts all of it.
- **Name proximity** to a popular package (`lodahs`, `python-dateutil` vs `dateutil`),
  starjacking (README/links pointing at an unrelated popular repo).
- **Slopsquatting** (OWASP "Secure Coding with AI"): AI coding assistants routinely
  invent plausible-but-nonexistent package names, and attackers pre-register them.
  **Verify every AI-suggested dependency actually exists with real history** (downloads,
  age, repo) before adding it — never `pip install`/`npm i` a name straight from a model.
  An approved-package allowlist plus the §3.7 cooldown blunts both this and typosquats.
  **Package-level** signals each trigger a manual review before adoption, AI-suggested or
  not: first publish only days or weeks old, negligible downloads, a lone maintainer with
  no other packages. (OWASP: Secure Coding with AI cheat sheet)
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
  standardize. Include component hashes and PURLs, enforced by the gate in rules/14 §14.2 —
  PURLs are what make cross-referencing advisories automatic.
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
  the edge (WAF/admission, sota-detection-engineering); fork-and-patch with a private
  upstream report first (rules/13 §13.8) and a regression test reproducing the vuln
  (§3.8); or replace the dependency. Record the chosen mitigation as VEX and set a
  re-check date — never just ignore-with-expiry. A fix that exists but cannot be taken yet,
  and backporting one, are rules/13 §13.6–§13.7.

### 3.6b A scanner built against an older toolchain fails as noise, not as a finding

§3.6a is two tools answering different questions. This is **one** tool whose own build has
gone stale against the toolchain it is analysing — and the output looks like a catastrophic
finding about your project.

After a routine toolchain upgrade (often dragged in as a dependency of an unrelated
`brew`/`apt` install), a vulnerability scanner compiled against the previous version emits a
wall of parse errors from **standard-library sources** and exits non-zero. None of it is
about your code.

The mechanism, verified 2026-09-13 in a container: a toolchain meeting source that declares a
newer version fails with a message that **names the version skew**, not the project —
`go: go.mod requires go >= 1.23 (running go 1.21.13)`. Field-reported in the scanner case, the
errors read `method must have no type parameters` and `file requires newer Go version`, with
paths pointing into the toolchain's own tree.

- **Two tells, and both are in the output**: the file paths are the *toolchain's* rather than
  yours, and at least one message names a version. A genuine finding cites your module.
- **Rebuild the tool against the current toolchain**, then **invoke it by absolute path**. A
  package-manager copy earlier in `PATH` will shadow the one you just built — `command -v`
  after a short-circuiting `PATH` prepend (`command -v x || export PATH=…`) still resolves the
  old one. Which binary ran is `rules/09` §2b.
- **Do not record this as a scan result in either direction.** It is neither a clean run nor a
  finding; the scan did not happen. A CI step that treats non-zero as "vulnerabilities found"
  will report a policy failure (`rules/11` §4 on classifying your own failures).

### 3.6a A clean run from one scanner is not coverage for another's question

§3.6's triage assumes findings to triage. This is the inverse: **two tools that both "check
dependencies" answer different questions, and the quiet one is not the reassuring one.**

Field-measured on one repository: `govulncheck ./...` reported **1** advisory and exited 0
while Dependabot reported **19** open alerts on the same tree. Neither was wrong.

| tool | the question it answers | what a clean run rules out |
|---|---|---|
| `govulncheck` | is a vulnerable **symbol reachable** from this code? (vuln DB + call graph) | reachable, *known-to-that-DB* vulnerabilities |
| Dependabot / SCA | is a vulnerable **version** in the dependency graph? (advisory DB + version ranges) | nothing about reachability |

So **a clean reachability scan is not evidence that dependencies are current**, and a clean
version scan is not evidence that anything exploitable is absent. Quoting either as "no
vulnerabilities" silently substitutes one question for the other — `sota-code-security`
rules/15 §2, where the instrument is fine and the claim is not.

- **Name the question beside the verdict.** *"govulncheck: no reachable vulnerable symbols"*
  is a finding; *"the scan was clean"* is not.
- **Reconcile a disagreement to a named cause before reporting either number.** In that case
  16 of the 19 were already closed and **three grpc advisories were not** — visible only to
  the version-range tool.
- **Merging a bot's bump is not closing the advisory it cites.** The same PR targeted 1.82.1
  while one advisory needed 1.82.2 and two needed 1.83.1. Check each alert's
  `first_patched_version` against the **resolved** graph (`go list -m all`, the lockfile),
  not against the PR title.

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

### 3.7.1 Landing a pin: name its watcher, and pin while it is still a no-op

Everything above assumes the version sits where a bot parses it. A version embedded in a
**build-tool invocation** is pinned and unwatchable by construction — no manifest exists,
and the bot sees a `RUN` line:

```dockerfile
RUN xcaddy build v2.11.4 --with github.com/example/caddy-plugin@v0.1.0
```

Same shape in Bazel/Make args, `go install tool@version`, `pip install x==y` in a
Dockerfile. Unpinned it drifts to latest on every rebuild; pinned it is frozen forever.
**Both states are silent** — only one of them sounds finished.

- **Every pin names the mechanism that will tell you it is stale**, and "Renovate" counts
  only once you confirm the bot parses *that file and that line*. `customManagers` (a regex
  over arbitrary files plus an explicit `datasourceTemplate`) teaches it a non-manifest pin;
  **Dependabot has no equivalent** — its ecosystems are manifest-shaped, so it reads a
  Dockerfile's `FROM` and not its `RUN` args (options reference, verified 2026-09-07). With
  no bot that can see it the pin needs a watcher, and a watcher is an instrument (`rules/11` §6).
- Otherwise **accept the freeze in writing**: an owner and a review date beside the pin —
  unwritten, it decays like an experiment with no scheduled read-back (`sota-architecture`
  rules/01 §4).
- **Pin while the pinned version is already what resolves.** The pin is then provably inert
  — determinism at zero behaviour change — so no later regression can be blamed on it; an
  SBOM diff (§3.5) showing the artifact component-for-component identical is the receipt.
  **Never pin and upgrade in one change**: that regression has two candidate causes and no
  build separates them.
- Read the version you are pinning to from **the resolver that will actually run**, and cite
  it — for Go modules `proxy.golang.org/<module>/@latest`, where `require` is a floor rather
  than a cap (`sota-golang` rules/07 §4). GitHub's `releases/latest` answers a different
  question and 404s outright for a repo publishing tags and no releases (`rules/11` §6).
- Audit: a pin outside anything the repo's update automation parses, with no watcher and no
  written acceptance = **Medium**; **High** if the frozen component faces the internet.

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

## 3.9 The EOL date is what forces the lookup — platform and base-image matrices

§3.7 keeps *dependencies* current. This is the layer under them — base images, OS
releases, distributions, runtimes, the rows of a "supported platforms" table — where the
version is chosen once, written into a matrix, and never re-read. The router's principle 1
states the rule; this is why it takes the shape it does.

**A recalled version number carries no felt uncertainty.** It arrives subjectively
identical to a looked-up one — no hedge, no "I think" — so every rule that triggers on
doubt is structurally unable to fire, and "re-verify before recommending" does not reach
it. Worse, the framing is usually wrong too: pulling `alpine:3.20` to *test* something
reads as picking a fixture, not as a version decision, so the freshness rule is not even
consulted.

So require a second value that **cannot** be produced from plausibility:

- **Every versioned third-party row carries its EOL date.** A version with no EOL beside
  it has not been looked up — that is the whole mechanism, and it is checkable by eye in
  review. `endoflife.date`'s API covers most OS, distro, runtime and database cycles in
  one request; cross-check anything load-bearing against the vendor's own page.
- **A row whose EOL has passed is removed from the matrix, not corrected.** Testing an
  unsupported branch does not produce a slightly-stale answer, it produces an answer about
  a different system. Field-reported: Alpine **3.20** (EOL 2026-04-01) reports
  `# CONFIG_BPF_LSM is not set` where the current branch reports `CONFIG_BPF_LSM=y` — the
  stale row did not understate the current release, it said the opposite, turning "needs
  one boot parameter" into "cannot run without a custom kernel".
- **Sweep the whole table in one pass, not the row you were corrected on.** The same
  session fixed the Alpine row, wrote the lesson into the document, and left an openSUSE
  Leap **15.6** row (EOL 2026-04-30) that was stale for identical reasons one line down.
  The lesson had been encoded as a fact about Alpine rather than a procedure about
  versions. Re-running the lookup across all rows revealed **five of seven** stale at once;
  it is cheap and total, and nothing but the missing column was ever demanding it.
- **Compare capabilities, not version numbers — and state the assumption if you must.**
  *"Version ≥ X implies feature X"* is true only where the distribution tracks upstream. It
  is **false for exactly the enterprise distributions that backport**, which are also the
  ones with the largest deployed base — not a coincidence, since they backport *because* the
  base is large and conservative. Reproduced 2026-09-13 in a container: AlmaLinux 8 ships
  `kernel-headers-4.18.0-553.162.1.el8_10`, and that 4.18 header declares
  `BPF_MAP_TYPE_RINGBUF` (upstream 5.8) and `BPF_PROG_TYPE_LSM` (upstream 5.7). A version
  comparison excludes it; a capability probe includes it. Field-reported cost: RHEL 8 was
  written into a shipped support matrix as **excluded**, and the claim had to be retracted.
- **A method applied across a population needs its domain of validity written down.** The
  rule was not wrong — its *scope* was never stated, so it was applied uniformly to members
  that do not satisfy its premise. Name the assumption and name which members violate it;
  the member where a method fails is disproportionately the one that matters commercially.
- **Give the matrix an expiry.** A platform table is a decision with a review date
  (§3.7.1's discipline for a pin): the nearest EOL in the table *is* that date.
- **Then automate the lookup over the whole inventory, on a schedule.** The column is read only
  when someone edits the row. A scheduled job matches the SBOM inventory (§3.5) against EOL data
  and alerts on anything past EOL or inside a warning window: `endoflife.date`'s v1 API gives
  per-release `isEol`/`eolFrom` and maps products to PURLs (`identifiers`, read 2026-09-25), and
  xeol scans images, filesystems and SBOMs for EOL components. (OWASP: SCVS 5.8)

## Audit checklist

- [ ] Lockfiles committed for every manifest; CI/Docker builds use frozen/hash-verified installs; no `npm install`/bare `pip install` in CI
- [ ] Dependency-review gate on PRs, required, failing on high severity + license denylist
- [ ] No `--extra-index-url` public/private mixing; npm internals scoped; GOPRIVATE set; internal names reserved publicly; fetches go through a caching proxy with audit log
- [ ] Install scripts disabled by default in CI (`--ignore-scripts`/pnpm allowlist); new-dependency review covers install hooks, obfuscation, maintainer churn, and package age / downloads / sole-maintainer signals (§3.4)
- [ ] **No TLS/checksum disablers and no build-time config rewrites (§3.3), High:** `grep -rn -E 'strict-ssl[[:space:]]*=[[:space:]]*false|strict-ssl false|trusted-host|PIP_TRUSTED_HOST|allow-insecure-host|GOINSECURE|GOSUMDB[=:[:space:]]+"?off|NODE_TLS_REJECT_UNAUTHORIZED[=:[:space:]]+"?0|(npm|pnpm|yarn|pip|uv|poetry) config set|go env -w' .` over CI files, Dockerfiles and committed rc files is empty; the rc files CI reads are tracked (`git ls-files`)
- [ ] **Did a scanner fail with errors naming the toolchain's own paths?** (§3.6b) That is a
      stale tool build after a toolchain upgrade, not a finding — the tells are toolchain
      paths and a message naming a version. Rebuild it, invoke by absolute path (a
      package-manager copy earlier in `PATH` shadows it), and record the scan as **not run**
      rather than as clean or as failing
- [ ] **Is any "no vulnerabilities" claim resting on one scanner?** (§3.6a) A reachability
      tool (`govulncheck`) and a version-range tool (SCA/Dependabot) answer different
      questions — measured 1 advisory vs 19 alerts on one tree. State the question beside the
      verdict, reconcile any disagreement to a named cause, and check each alert's
      `first_patched_version` against the **resolved** graph rather than a bump's PR title
- [ ] SBOM (CycloneDX/SPDX) generated per artifact from lockfile + image, attached to the digest, queryable centrally
- [ ] Scanning: PR diff gate + scheduled scans of deployed digests; triage uses reachability/KEV/EPSS **and the advisory's own affected-platform/affected-configuration text** (§3.6); decisions recorded as VEX; ignores have owner + expiry; SLAs enforced
- [ ] Renovate/Dependabot active with cooldown (`minimumReleaseAge`), grouping, automerge restricted to dev/patch with green required checks; Actions + Docker digests auto-pinned
- [ ] **Every pin has a named staleness mechanism (§3.7.1)** — the bot confirmed to parse *that* file/line, or a watcher, or a written acceptance of the freeze with an owner and a review date; pins landed while still a no-op, never bundled with an upgrade
- [ ] Vendored deps (if any) are scanner-visible, auto-refreshed, and unpatched (or patches tracked upstream)
- [ ] **Inert-dependency sweep run** — declared-but-not-reached dependencies, modules and plugins, proven by deletion rather than by a tool's silence: [rules/10](10-inert-dependencies.md), a full pass with its own checklist
- [ ] **Does any support-matrix row infer a capability from a version number? (§3.9)** That
      holds only where the distro tracks upstream and is **false for backporting enterprise
      distributions** — measured: an AlmaLinux 8 `4.18` header declares BPF features from
      upstream 5.7/5.8. Probe the capability, say which you measured, and write down the
      assumption the method rests on plus the members that violate it
- [ ] **Scheduled EOL detection over the inventory (§3.9), Medium:** `grep -rln -E 'endoflife\.date|xeol' .github/workflows` (or the scheduler's config) names a scheduled job, and its alerts have an owner
- [ ] **Every versioned third-party row carries an EOL date (§3.9)** — base images, OS/distro releases, runtimes, supported-platform matrices. A version with no EOL beside it has not been looked up, and a row past its EOL is **removed**, not corrected: an unsupported branch can answer the *opposite* of the current one, not merely a staler version of it. When one row is found stale, re-run the lookup across **all** rows in the same pass
