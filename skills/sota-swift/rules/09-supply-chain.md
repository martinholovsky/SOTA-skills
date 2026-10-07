# 09 — Supply chain: SwiftPM dependencies, build-time code, SBOM

Moved from `sota-mobile` rules/07 §7.10 on 2026-10-07 and extended. Pipeline-wide controls
(signing, provenance, CI hardening) are `sota-devsecops`.

## 1. Pin and enforce the resolution

- **Commit `Package.resolved`** for applications and services. SwiftPM's docs: it is used *"to
  ensure another build uses the same versions"*; a library's resolved file is *"ignored by the
  package that depends on your library"*, so libraries declare ranges and their consumers pin.
- CI resolves with **`--force-resolved-versions`** (aliases `--disable-automatic-resolution`,
  `--only-use-versions-from-resolved-file`): *"fail resolution if it is out-of-date."* A silent
  re-resolve is how a hijacked tag slides in.
- Requirements: `from:` / `.upToNextMajor` for libraries; `.exact` is *"not recommended as they
  can cause conflicts"*; **no `branch:` or `revision:` dependencies in anything that ships** —
  they are unpinned by definition and cannot be depended on by version-based packages.
- Remote `binaryTarget`s carry a SHA-256 `checksum` (`swift package compute-checksum`); SwiftPM
  refuses a mismatch. The checksum authenticates what you vetted; it does not make an opaque
  binary safe — keep an inventory.

## 2. Where packages come from: identity, registries, confusion

- SE-0292: a URL-based package's identity is *"computed from the last path component of its
  effective URL… can lead to a conflation of distinct packages"* — two different repos named
  `Parser` collide. Prefer full URLs you control or mirror; registry scope IDs (`scope.name`)
  remove the ambiguity.
- Registries: package signing with signer TOFU (`--resolver-signing-entity-checking strict`),
  checksum TOFU under `~/.swiftpm/security/fingerprints` with
  `--resolver-fingerprint-checking` (default `strict` — never `warn`), and per-registry policy in
  `registries.json` (`signing.onUnsigned: error`). The fingerprint store is empty on an ephemeral
  CI runner, so TOFU protects nothing there — persist it or rely on the committed lockfile and
  checksums.
- A private registry or mirror for internal packages, so an internal name cannot be shadowed by a
  public one.

## 3. Build-time code execution: plugins, macros, manifests

- `Package.swift` is Swift code executed at resolve time; **build-tool and command plugins**
  (SE-0303, SE-0332) and **macros** (SE-0382, compiler plugins) execute dependency code on the
  build machine — with CI credentials in reach.
- SwiftPM's sandbox for plugins is **macOS-only**: its source applies `/usr/bin/sandbox-exec`
  under `#if os(macOS)` and otherwise returns the command unchanged (*"tracks implementing
  sandboxes for other platforms"*). **On Linux CI, plugins and manifests run unsandboxed.**
  Needs verification: macro sandboxing on Linux.
- Command plugins can ask for `--allow-writing-to-package-directory` and
  `--allow-network-connections`; CI never passes `--disable-sandbox`.
- `unsafeFlags` *"can be exploited for unsupported or malicious behavior"* and make a product
  ineligible as a dependency; flag it in any dependency.
- Review every `.plugin(`, `.macro(`, `pluginTarget` and `binaryTarget` in the dependency tree at
  CI-config rigour, and code-owner-protect `Package.swift` and `Package.resolved`.

## 4. Know what you ship: SBOM and vulnerability scanning

- **SBOM**: Swift 6.4 generates one (SE-0509, *"Implemented (Swift 6.4)"*): `swift build
  --sbom-spec cyclonedx` (or `spdx`, `--sbom-output-dir`) or `swift package generate-sbom`.
  Without `--build-system swiftbuild` it warns that only the package graph is used, so
  OS-conditional dependencies may be missing — build-graph mode for the shipped binary.
- **Vulnerability scanning**: the GitHub Advisory Database lists Swift advisories ("Swift
  (registry: N/A)"); **Dependabot** supports the `swift` ecosystem (*"Private registry support
  applies to git registries only"*); OSV's ecosystem is `SwiftURL` (the name is the Git URL).
  Needs verification: osv-scanner's `Package.resolved` support in practice — run it once on a
  known-vulnerable resolution before trusting a clean result. Run at least one of these in CI,
  and report each Critical/High advisory as its own finding (module@version).

## 5. Adopting a dependency

- Bar for a new package: the SSWG's (*"2+ maintainers"*, a `SECURITY.md` with a private
  contact, SemVer), recent releases, and no `unsafeFlags` or unexplained plugins.
- Check its insecure or permissive defaults before use — the ones verified 2026-10-07: Vapor
  session cookies (`isSecure: false`, `isHTTPOnly: false`), Hummingbird session cookies
  (`secure: false`, `sameSite: nil`), NIOSSL client minimum TLS 1.0, AsyncHTTPClient following
  5 redirects, Vapor's compile-time `isRelease` (rules/05, rules/06).

## Audit checklist

- [ ] Dependency pinning & lockfiles: `Package.resolved` committed for apps and services; CI resolves with `--force-resolved-versions`; no `branch:`/`revision:` requirements in shipped products (grep `branch: *"|revision: *"`); `.exact` only with a reason.
- [ ] Remote `binaryTarget`s carry checksums and appear in a binary-dependency inventory.
- [ ] Supply-chain provenance & publishing: package identities are unambiguous (no two dependencies sharing a last path component); internal packages come from a private registry or mirror; registry consumers set fingerprint and signing-entity checking to `strict` and `onUnsigned: error`; no `--resolver-fingerprint-checking warn`.
- [ ] Install/build-time code execution: every `.plugin(`, `.macro(`, `pluginTarget`, `binaryTarget` and `unsafeFlags` in the dependency tree is reviewed; CI never passes `--disable-sandbox`, `--allow-network-connections` or `--allow-writing-to-package-directory` unreviewed; Linux CI treats plugins as unsandboxed; `Package.swift`/`Package.resolved` are code-owner protected.
- [ ] Vulnerability scanning of dependencies: Dependabot (`swift` ecosystem), OSV or GitHub advisories run in CI; each Critical/High advisory is reported per module@version with reachability.
- [ ] An SBOM is produced for shipped binaries (`--sbom-spec`, build-graph mode where OS-conditional dependencies exist).
- [ ] Dependency adoption: new packages meet the maintainer/`SECURITY.md`/SemVer bar, and their insecure defaults (cookies, TLS minimum, redirects, release detection) are configured.
