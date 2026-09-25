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
- **The security rules are off until you opt in — and `latest-Recommended` is not opting in.**
  The SDK's analyzer ships **94** Security-category rules; **70** are disabled by default and
  the other **24** are enabled at `Hidden` severity, which prints nothing (the analyzer's
  `AnalyzerReleases.Shipped.md`, and a reflection dump of the .NET 10 SDK's analyzer DLLs, agree
  rule for rule). Measured on the .NET 10 SDK against one file planting 14 violations:
  **default → 0 security warnings; `AnalysisLevel=latest-Recommended` → 4** (MD5, SHA-1, an
  accept-all certificate callback, `SslProtocols.Tls`); **`<AnalysisModeSecurity>All</AnalysisModeSecurity>`
  → 10**, adding `System.Random` (CA5394), ECB (CA5358), a hard-coded key (CA5390), Zip Slip
  (CA5389), SQL via `DbCommand.CommandText` (CA2100) and a disabled CRL check (CA5399). Set
  `AnalysisModeSecurity` (or `AnalysisLevelSecurity=latest-All`) **and** keep
  `TreatWarningsAsErrors` — `All` alone only warns, and the build still exited 0.
- **An `.editorconfig` category line looks like an opt-in and is not one.**
  `dotnet_analyzer_diagnostic.category-Security.severity = warning` "only affects rules … that
  are enabled by default" (Microsoft's configuration-options page): measured, it produced the
  same 4 warnings as `Recommended`. Enable a disabled rule by ID
  (`dotnet_diagnostic.CA5394.severity`) or by `AnalysisModeSecurity`.
- **Silence from the analyzer is not absence.** Even under `All`, four of the fourteen planted
  violations raised nothing: `CA2100` fired on a `DbCommand` that is executed but not on a bare
  `IDbCommand.CommandText` assignment, and `CA3075` fired on none of three DTD-enabled XML
  readers in a `net10.0` project (not investigated further). Keep the grep checklists
  (`rules/04`) as the second instrument.
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
- **A package runs code in your build, before any test does.** Restore writes
  `obj/<project>.nuget.g.props`/`.nuget.g.targets`, which import every package's
  `build/`, `buildTransitive/` and `buildMultiTargeting/` `<PackageId>.props`/`.targets`;
  a target there can `<Exec>` any command, running it with the
  developer's or runner's credentials. Measured on the .NET 10 SDK: a local package's
  `build/*.targets` `<Exec>` wrote a file during `dotnet build`, and a `buildTransitive/` target
  ran in a project that referenced only a package depending on it. Other points: package
  `analyzers/` DLLs (analyzers and source generators) are handed to `csc` as `/analyzer:` and
  run inside the compiler; `Sdk="Name/1.2.3"` or `global.json` `msbuild-sdks`
  pulls a project SDK (props/targets) from your feeds; and the repo's own
  `Directory.Build.props`/`.targets`/`.rsp`, found by walking **up** from each project. (A
  package's `tools/install.ps1` is **not** run under PackageReference — only `packages.config`.)
- **Switch it off per package** (the documented control is per reference): on the `PackageReference` set
  `ExcludeAssets="build;buildTransitive;buildMultitargeting;analyzers"` for a package that
  needs none of them. A **transitive** package's `buildTransitive/` is excluded by adding a
  direct reference with that `ExcludeAssets` (measured: the transitive target stopped
  running). Keep the imported set small and known.
- **Review it on every bump**: diff the executed files (`.props`, `.targets`, analyzer DLL
  versions) between the old and new package in the lock-file change, and put the repo's own
  build-executing files — `Directory.Build.*`, `*.targets`, `*.props`, `nuget.config`,
  `global.json`, `.config/dotnet-tools.json` — under **CODEOWNERS** with required review,
  **including when an AI agent wrote the change**.
- **CI**: the restore/build/test job gets a read-only feed token at most — no signing, publish
  or cloud-deploy secrets; sign and publish in a separate job that consumes the built
  artifact. *(OWASP: CI/CD Security cheat sheet; Software Supply Chain Security cheat sheet;
  NPM Security cheat sheet for the install-script class.)*

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

- [ ] **What has been SILENCED? -- the analyser's escape hatch (ROADMAP 60) Five mechanisms,
      verified against Microsoft's in-source-suppression docs. A grep for only the first finds a
      codebase that looks clean while whole rules are off globally.** —
      `grep -rn '#pragma warning disable' --include='*.cs' --include='*.vb' .` (want: a matching
      restore); `grep -rn '#pragma warning disable' --include='*.cs' . | wc -l` ;
      `grep -rn '#pragma warning restore' --include='*.cs' . | wc -l` (disable >> restore =
      leaked to EOF); `grep -rn 'SuppressMessage' --include='*.cs' .` (Justification= is
      required reading);
      `grep -rn 'Justification *= *""\|Justification *= *"<Pending>"' --include='*.cs' .` (HIGH:
      auto-generated, never filled in);
      `find . -name 'GlobalSuppressions.cs' -o -name 'GlobalSuppressions.vb'`
      (assembly/module-scoped, invisible at the call site);
      `grep -rn '<NoWarn>' --include='*.csproj' --include='*.props' .` (whole-project,
      whole-solution if in Directory.Build.props);
      `grep -rnE 'dotnet_diagnostic\.[A-Z]+[0-9]+\.severity *= *none' .editorconfig 2>/dev/null`
- [ ] **"Build and Suppress Active Issues" is BASELINING: Microsoft's own term for suppressing
      every current violation at once. A large GlobalSuppressions.cs with uniform timestamps is
      its signature, and it means the analyser's verdict on that code was never read. NOTE:
      [SuppressMessage] is conditional on the CODE_ANALYSIS compilation symbol, so the attribute
      can be present in source and absent from the shipped assembly.**
- [ ] **TFM/SDK pinned? settings centralized?** —
      `grep -rnE '<TargetFramework' **/*.csproj 2>/dev/null | head` ;
      `ls global.json Directory.Build.props Directory.Packages.props 2>/dev/null | grep -q . || echo "no central build config"`
- [ ] **Nullable + warnings-as-errors + analyzers?** —
      `err=$(grep -rniE 'TreatWarningsAsErrors|<Nullable>|EnableNETAnalyzers|AnalysisLevel' --include='*.csproj' --include='Directory.Build.props' . 2>&1 >/dev/null); rc=$?` ;
      `case $rc in 0) ;; 1) echo "nullable/analyzers/warnings-as-errors not enforced — HIGH" ;; *) echo "SWEEP FAILED, not a finding about their code: $err" ;; esac`
- [ ] **Security CA rules opted in? HIGH if not — 70 of 94 ship disabled, the rest Hidden** (§2) —
      `err=$(grep -rniE '<AnalysisMode(Security)?>[[:space:]]*All|<AnalysisLevel(Security)?>[^<]*-All' --include='*.csproj' --include='*.props' . 2>&1 >/dev/null); rc=$?` ;
      `case $rc in 0) ;; 1) echo "security CA rules not opted in -- HIGH" ;; *) echo "SWEEP FAILED, not a finding about their code: $err" ;; esac`
      ; and the look-alike that does not count:
      `grep -rnE 'dotnet_analyzer_diagnostic\.(category-Security\.)?severity' --include='.editorconfig' --include='*.globalconfig' .`
      (a hit raises only the 24 enabled-by-default rules — the same 4 warnings as `Recommended`
      in the measurement)
- [ ] **Target framework past end of support? HIGH** —
      `grep -rhoE '<TargetFrameworks?>[^<]+' --include='*.csproj' --include='*.props' .` ;
      compare each `netX.Y` with
      `curl -fsS https://dotnetcli.blob.core.windows.net/dotnet/release-metadata/releases-index.json | grep -oE '"(channel-version|support-phase)": *"[^"]*"' | paste - -`
      (`eol` = no security patches; read it at audit time, never from memory. `net4x` targets
      are .NET Framework, which this index does not list — check its lifecycle separately)
- [ ] **NuGet locking + source mapping + CVE scan?** —
      `find . -name packages.lock.json -not -path '*/obj/*' | head -1` (empty = no lockfile) ;
      `err=$(grep -rn 'RestorePackagesWithLockFile' --include='*.csproj' --include='Directory.Build.props' . 2>&1 >/dev/null); rc=$?` ;
      `case $rc in 0) ;; 1) echo "lockfile not enforced (RestorePackagesWithLockFile unset) — supply-chain risk" ;; *) echo "SWEEP FAILED, not a finding about their code: $err" ;; esac`
      ;
      `err=$(grep -rniE 'packageSourceMapping|locked-mode|NuGetAudit|NU190[0-9]|auditSources|dependabot' --include='nuget.config' --include='NuGet.Config' --include='Directory.Build.props' --include='*.csproj' --include='*.yml' --include='*.yaml' . 2>&1 >/dev/null); rc=$?` ;
      `case $rc in 0) ;; 1) echo "no source mapping / locked restore / NuGetAudit CI gate" ;; *) echo "SWEEP FAILED, not a finding about their code: $err" ;; esac`
- [ ] **Formatting + deterministic build in CI?** —
      `grep -rniE 'dotnet format|verify-no-changes|Deterministic|ContinuousIntegrationBuild' .github/ *.yml **/*.csproj 2>/dev/null | head`
- [ ] **Test runner + coverage?** —
      `grep -rniE 'xunit|nunit|mstest|coverlet|testcontainers' **/*.csproj 2>/dev/null | head`
- [ ] **Package code that runs at build (`build*/…props`/`.targets` imported from packages) —
      HIGH if any is unreviewed** (§3) — after a restore, every hit is a package file MSBuild
      imports and runs:
      `grep -rnE '"build[A-Za-z]*/[^"]*\.(props|targets)": *\{' --include=project.assets.json .`
      (each hit needs an owner and a diff on bump, or `ExcludeAssets`); and the repo's own
      build-executing files need a code owner:
      `(grep -snE 'Directory\.Build|\.targets|\.props|nuget\.config|global\.json' .github/CODEOWNERS CODEOWNERS docs/CODEOWNERS; true) | grep -E . || echo "build-executing files have no CODEOWNERS entry -- HIGH"`
      (the subshell keeps a missing CODEOWNERS path from reading as "no owner")
