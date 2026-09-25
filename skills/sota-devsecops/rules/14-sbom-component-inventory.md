# 14 — SBOM Content, Quality and Handling (what an SBOM must hold, and who may read it)

Scope: `rules/03` §3.5 requires an SBOM for every release artifact, generated at build time
and bound to the digest. This file covers what that SBOM must contain (§14.1), the CI gate
that enforces it (§14.2), who may read it (§14.3), SBOMs you receive from suppliers (§14.4),
and components you have patched or forked (§14.5). Examples use CycloneDX JSON; SPDX has an
equivalent for each field, noted where the names differ.

## 14.1 Minimum SBOM content: identity, PURL, supplier, licence, dependency edges

An SBOM that lists names without versions, or components without edges, answers "do we
ship X?" and nothing more. Require these fields.

**Per component**

- **Name and version** exactly as the ecosystem spells them.
- **A PURL in the component's native ecosystem type** (`pkg:npm/…`, `pkg:pypi/…`,
  `pkg:golang/…`), normalised by the PURL type's own rules so one package reached through
  two sources collapses to one entry. For `pypi`, the type definition lowercases the name
  and replaces `_` with `-` (purl-spec `types/pypi-definition.json`, read 2026-09-25).
  Deduplicate on the normalised PURL, not the display name.
- **Type or ecosystem, supplier or origin, and licence** as an SPDX identifier or
  expression.
- **Hashes** wherever the artifact has one to record.

**Graph.** Record dependency edges: CycloneDX `dependencies[]` (`ref` plus `dependsOn`),
SPDX relationships such as `DEPENDS_ON`. Without edges nobody can tell a direct dependency
from a transitive one, and `rules/13` §13.1 needs that answer.

**Document**

- A unique serial number: CycloneDX `serialNumber` in `urn:uuid:` form (the schema's own
  pattern), SPDX `documentNamespace`.
- A creation timestamp (`metadata.timestamp`) and the **CI run ID** that produced it (a
  `metadata.properties` entry), so the SBOM traces to one build.
- The generator's name and version (`metadata.tools`), plus the command line in the
  pipeline that ran it.
- **Subject metadata**: name, version and supplier of the thing the SBOM describes. Pass
  them explicitly. Measured with syft 1.51.1 (2026-09-25): `syft scan dir:.` names the
  subject `.`; `--source-name`, `--source-version` and `--source-supplier` set it properly.

**Reproducible generation.** Pin the generator (`rules/04` §4.1). Two generations from the
same commit should list the same components, so diff them in CI and treat a difference as a
generator or build-hermeticity bug.

**Optional build-time SBOM.** Tools and test dependencies that ran in the build but do not
ship belong in a **separate** SBOM marked with the CycloneDX lifecycle phase `build` (the
1.6 schema's phases are `design`, `pre-build`, `build`, `post-build`, `operations`,
`discovery`, `decommission`). A compromised build tool is then findable without polluting
the runtime inventory.

**Write it down as an SBOM policy**: format, generator and version, required fields, where
SBOMs are stored, who may read them (§14.3), and retention (at least as long as the artifact
is deployed or supported, plus your audit horizon).
(OWASP: Dependency Graph SBOM cheat sheet; NPM Security cheat sheet; SCVS 2.2, 2.3, 2.7,
2.10, 2.11, 2.12)

## 14.2 SBOM quality gate: schema-valid, complete metadata, valid SPDX licence IDs

"Include PURLs where available" produces SBOMs that are quietly incomplete. Enforce
completeness in the pipeline that generates the SBOM, and fail the build on a miss.

- **Validate against the schema.** `cyclonedx validate --input-file sbom.cdx.json
  --fail-on-errors` (cyclonedx-cli) returns non-zero on schema errors. An AI/ML BOM is a
  CycloneDX document too (component type `machine-learning-model`, with a `modelCard`), so
  it goes through the same validation (`sota-ml-engineering`).
- **Fail on a component missing required metadata**: name, version, PURL and licence for
  every library and framework; a hash where the ecosystem provides one; a copyright
  statement (CycloneDX `copyright`) where your licence obligations need one. A licence given
  only as free text (`license.name` with no `id`) counts as missing.
- **Licence identifiers must be real SPDX IDs.** Compare each `license.id` against the SPDX
  licence list (`json/licenses.json` in the `spdx/license-list-data` repository), and parse
  `expression` values with an SPDX-expression parser. An unknown ID blocks the build like an
  unknown licence (`rules/05` §5.5).
- **State the threshold as a number**: 100% of shipped library components carry the
  required fields. A score-based tool such as `sbomqs score` is useful for trending, but the
  gate is the field check.
  (OWASP: NPM Security cheat sheet; SCVS 2.15, 2.16; AISVS 6.2.3)

## 14.3 SBOMs are sensitive: access control and scrubbing before sharing

A full internal SBOM is a map of what to attack: every component and version, and often
internal registry URLs, hostnames and build paths.

- **Restrict who can read the full internal SBOM** to the people and systems that act on
  it (the vulnerability pipeline, the security team, incident responders). Store it with
  access logging, not in a world-readable bucket.
- **Scrub before publishing or handing one to a customer**: remove internal repository
  URLs, hostnames and absolute build paths. Measured with syft 1.51.1 (2026-09-25): a
  `dir:` scan named a lockfile component by its **absolute path on the build host**, with
  and without `--base-path`, so a CI-built SBOM can carry the runner's workspace path.
- **Check the published copy, not the scrubber's configuration**: scan the exact file you
  are about to share for internal patterns, then publish it.
  (OWASP: Dependency Graph SBOM cheat sheet)

## 14.4 Supplier SBOMs for procured software

Software you buy or ingest runs with the same privileges as software you build, and your
SCA pipeline cannot see inside it (`rules/13` §13.9).

- **Make an SBOM a procurement requirement**: in the contract or purchase checklist, in an
  agreed format (CycloneDX or SPDX), per delivered version.
- **Ingest it into the same inventory and scanning pipeline** as your own SBOMs (§14.2's
  gate, continuous vulnerability matching, EOL detection in `rules/03` §3.9), keyed to the
  version actually deployed.
- **Escalate a refusal** to procurement and the risk owner. A supplier with no SBOM is an
  accepted risk with a named owner, or a reason to choose another product. It is never a
  silent gap in the inventory.
  (OWASP: Dependency Graph SBOM cheat sheet; SCVS 1.5)

## 14.5 Patched and forked components: distinct identity, recorded pedigree

A component you patched (`rules/13` §13.7) or forked is no longer the upstream component,
even when its code differs by one line. Make that visible everywhere.

- **Give it a distinct identifier**: a version suffix under your own convention (for
  example `1.4.3-acme.1`) or a distinct name, and a PURL that reflects it. Semver ignores
  `+build` metadata when ordering versions, and tools that follow it (Dependabot's
  documentation says it strips build metadata before comparing) will treat `1.4.3+acme.1`
  as plain `1.4.3`.
- **Publish it through the internal registry with recorded provenance**: the upstream
  commit it derives from, the advisory it fixes, and who made the change. Never commit a
  locally built artifact or depend on a local path.
- **Record its pedigree in the SBOM**: CycloneDX `pedigree` holds `ancestors` (the
  upstream component), `commits` and `patches` (how it deviates) and `notes`.
- **Scan it as deeply as upstream**: the same SCA, SAST and licence checks. Track
  advisories and VEX against **the modified variant**. A scanner that matches it to the
  upstream version range will keep reporting the advisory you fixed; answer that with a
  VEX statement for the variant, not an ignore rule that also hides the next advisory.
  (OWASP: Vulnerable Dependency Management cheat sheet; SCVS 2.17, 6.4, 6.5, 6.6, 6.7)

## Audit checklist

- [ ] **Document-level SBOM fields present (§14.1), Medium:** `jq -e '((.serialNumber // "")|test("^urn:uuid:")) and (.metadata.timestamp != null) and (((.metadata.tools.components // .metadata.tools) // []) | length > 0) and ((.metadata.component.name // "") | . != "" and . != ".") and ((.dependencies // []) | length > 0)' <sbom>.cdx.json` exits `0`; the CI run ID is recorded; a written SBOM policy names format, generator, fields, access and retention
- [ ] **Component completeness enforced as a failing gate (§14.2), Medium:** `jq -e '[.components[] | select(.type=="library" or .type=="framework") | select((.version // "") == "" or (.purl // "") == "" or ((.licenses // []) | length) == 0 or any(.licenses[]; .license.name != null and .license.id == null))] | length == 0' <sbom>.cdx.json` exits `0`, and the same check runs in CI without `continue-on-error`; `cyclonedx validate --fail-on-errors` runs on the file
- [ ] **Licence IDs are real SPDX IDs (§14.2), Low:** `jq -r '.components[].licenses[]?.license.id // empty' <sbom>.cdx.json | sort -u | grep -v -x -F -f spdx-ids.txt` prints nothing, where `spdx-ids.txt` is `jq -r '.licenses[].licenseId'` over the SPDX `licenses.json`
- [ ] **Shared SBOMs scrubbed; internal SBOMs access-controlled (§14.3), Medium:** `grep -n -E '"/(home|Users|builds|runner|github/workspace|private|tmp)/|://[^/"]*\.(internal|corp|lan|local)[/":]' <sbom-to-publish>.json` (plus your own internal domains) prints nothing; the internal SBOM store is not publicly readable
- [ ] **Supplier SBOMs required and ingested (§14.4), Medium:** each procured product in the inventory has a current supplier SBOM in the scanning pipeline, or a recorded risk acceptance with an owner
- [ ] **Patched components carry a distinct version and pedigree (§14.5), Medium:** with your suffix convention (here `acme`), `jq -e '[.components[] | select((.version // "") | test("[-+]acme\\.")) | select(.pedigree == null)] | length == 0' <sbom>.cdx.json` exits `0`; no local-path dependency stands in for a patched component (`rules/13` §13.7)
