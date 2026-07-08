# 06 — Build, tooling, supply chain, CI

.NET project safety lives in the build: nullable + analyzers as errors, NuGet
locking and CVE scanning, and consistent CI gates. This file owns build/test
*mechanics*; test **strategy** (suite shape, doubles, coverage philosophy)
lives in `sota-testing`.

## 1. Targeting & project hygiene

- Target the current LTS TFM (`<TargetFramework>net10.0</TargetFramework>`); pin
  the SDK with `global.json` so every machine/CI builds with the same version.
- Centralize settings in **`Directory.Build.props`** and dependency versions in
  **`Directory.Packages.props`** (Central Package Management) so versions are
  consistent and reviewed in one place.
- Enable broadly: `<Nullable>enable</Nullable>`,
  `<TreatWarningsAsErrors>true</TreatWarningsAsErrors>`,
  `<AnalysisLevel>latest-Recommended</AnalysisLevel>` (or `All`),
  `<EnableNETAnalyzers>true</EnableNETAnalyzers>`,
  `<ImplicitUsings>enable</ImplicitUsings>`.

## 2. Analyzers & formatting

- **Roslyn analyzers** (.NET analyzers ship in the SDK) catch correctness,
  reliability, and **security CA rules** (CA2100 SQL injection, CA53xx/CA54xx
  crypto, CA2300-series deserialization). Run as errors in CI. Add focused
  analyzers (e.g. for async) where useful.
- **`dotnet format --verify-no-changes`** in CI so style/whitespace never enters
  review. EditorConfig holds the rules.
- Consider a SAST (the security CA rules, or a dedicated scanner) for deeper
  taint analysis on web apps.

## 3. NuGet supply chain

- **Lock dependencies**: enable `<RestorePackagesWithLockFile>true</...>` to
  generate `packages.lock.json`, and restore with **`--locked-mode`** in CI so
  builds are reproducible and a changed transitive dependency fails loudly.
- **Package Source Mapping** (`nuget.config`) so each package only resolves from
  its intended feed — defeats **dependency confusion** (an internal name
  resolving from nuget.org). Restrict feeds to trusted sources over HTTPS.
- **NuGetAudit** checks every restore against advisory data automatically
  (since NuGet 6.8/.NET 8 SDK; `NuGetAuditMode` defaults to `all` — transitive
  included — on net10.0+ projects). Gate CI by making the audit warnings errors:
  `<WarningsAsErrors>$(WarningsAsErrors);NU1903;NU1904</WarningsAsErrors>`
  (high/critical; add NU1901/NU1902 to be stricter). Configure `auditSources`
  in `nuget.config` if your feed lacks vulnerability data; suppress an accepted
  advisory explicitly with a `NuGetAuditSuppress` item (last resort); remediate
  with `dotnet package update --vulnerable`. Keep
  `dotnet list package --vulnerable --include-transitive` as the ad-hoc query;
  Dependabot/external scanners complement, not replace.
- Verify **signed packages**; generate an **SBOM** for releases. See
  `sota-devsecops`.

## 4. CI gates

- A PR build runs: `dotnet build` with warnings-as-errors (nullable + analyzers),
  `dotnet test` (xUnit/NUnit/MSTest) with coverage (coverlet) and a threshold,
  `dotnet format --verify-no-changes`, `--locked-mode` restore, and the
  NuGetAudit gate (NU190x as errors). Fail on any.
- **Testcontainers for .NET** for real-dependency integration tests (DB/broker) —
  wire them here; *strategy* is `sota-testing`. Run with fixed culture/timezone
  for determinism (`InvariantGlobalization` where applicable).
- Build deterministically (`<Deterministic>true</Deterministic>`, ContinuousIntegrationBuild)
  and produce symbols.

## Audit checklist

```bash
# TFM/SDK pinned? settings centralized?
grep -rnE '<TargetFramework' **/*.csproj 2>/dev/null | head
ls global.json Directory.Build.props Directory.Packages.props 2>/dev/null || echo "no central build config"

# Nullable + warnings-as-errors + analyzers?
grep -rniE 'TreatWarningsAsErrors|<Nullable>|EnableNETAnalyzers|AnalysisLevel' **/*.csproj Directory.Build.props 2>/dev/null \
  || echo "nullable/analyzers/warnings-as-errors not enforced — HIGH"

# NuGet locking + source mapping + CVE scan?
ls packages.lock.json 2>/dev/null && grep -rn 'RestorePackagesWithLockFile' **/*.csproj Directory.Build.props 2>/dev/null \
  || echo "no NuGet lockfile — supply-chain risk"
grep -rniE 'packageSourceMapping|locked-mode|NuGetAudit|NU190[0-9]|auditSources|dependabot' \
  nuget.config Directory.Build.props **/*.csproj .github/ *.yml 2>/dev/null \
  || echo "no source mapping / locked restore / NuGetAudit CI gate"

# Formatting + deterministic build in CI?
grep -rniE 'dotnet format|verify-no-changes|Deterministic|ContinuousIntegrationBuild' .github/ *.yml **/*.csproj 2>/dev/null | head

# Test runner + coverage?
grep -rniE 'xunit|nunit|mstest|coverlet|testcontainers' **/*.csproj 2>/dev/null | head
```
