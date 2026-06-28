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

## Audit checklist

- [ ] Lockfiles committed for every manifest; CI/Docker builds use frozen/hash-verified installs; no `npm install`/bare `pip install` in CI
- [ ] Dependency-review gate on PRs, required, failing on high severity + license denylist
- [ ] No `--extra-index-url` public/private mixing; npm internals scoped; GOPRIVATE set; internal names reserved publicly; fetches go through a caching proxy with audit log
- [ ] Install scripts disabled by default in CI (`--ignore-scripts`/pnpm allowlist); new-dependency review covers install hooks, obfuscation, maintainer churn
- [ ] SBOM (CycloneDX/SPDX) generated per artifact from lockfile + image, attached to the digest, queryable centrally
- [ ] Scanning: PR diff gate + scheduled scans of deployed digests; triage uses reachability/KEV/EPSS; decisions recorded as VEX; ignores have owner + expiry; SLAs enforced
- [ ] Renovate/Dependabot active with cooldown (`minimumReleaseAge`), grouping, automerge restricted to dev/patch with green required checks; Actions + Docker digests auto-pinned
- [ ] Vendored deps (if any) are scanner-visible, auto-refreshed, and unpatched (or patches tracked upstream)
