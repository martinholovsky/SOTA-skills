# 06 — Build, tooling, supply chain, CI

.NET project safety lives in the build: nullable + analyzers as errors, NuGet
locking and CVE scanning, and consistent CI gates. This file owns build/test
*mechanics*; test **strategy** (suite shape, doubles, coverage philosophy)
lives in `sota-testing`.

## 1. Targeting & project hygiene

- Target the latest LTS TFM (`<TargetFramework>net10.0</TargetFramework>` at the time of writing;
  verify at the [.NET support policy](https://dotnet.microsoft.com/platform/support/policy/dotnet-core)
  page); pin the SDK with `global.json` so every machine/CI builds with the same version.
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
- **Vet a new dependency before the `PackageReference` lands** — including one an AI
  assistant proposed, whose id may not exist or may have been registered days ago. Confirm
  the exact id first: `dotnet package search <Id> --exact-match --source https://api.nuget.org/v3/index.json`
  prints `No results found.` and still **exits 0**, so read the output, not the status.
  Then `dotnet package search <Id> --take 5 --format json --verbosity detailed` (owners,
  total downloads, project URL — and look-alike ids ranked beside it); the nuget.org
  search API (`azuresearch-usnc.nuget.org/query?q=packageid:<Id>`) adds `verified`, which is
  **ID prefix reservation**: `true` means the owner holds the id prefix, `false` is common
  for legitimate packages and proves nothing. Per-version publish dates and deprecation:
  `api.deps.dev/v3/systems/nuget/packages/<Id>`; the repo's OpenSSF Scorecard:
  `api.securityscorecards.dev/projects/github.com/<owner>/<repo>` (an empty reply means
  never scanned, not a pass). Also check open advisories, licence, and that the project URL
  is the repository you meant.
- **A library's defaults are part of your security posture** — audit every
  security-relevant option you pass to it, and the ones you left unset. Read in source:
  **MessagePack-CSharp** `MessagePackSerializerOptions.Security` defaults to
  `MessagePackSecurity.TrustedData`; set `.WithSecurity(MessagePackSecurity.UntrustedData)`
  for anything from outside. **Npgsql** `SslMode` defaults to `Prefer`, which falls back
  to plaintext when the server declines TLS, and `Prefer`/`Require` accept any server
  certificate — use `SSL Mode=VerifyFull` (or `VerifyCA`). BCL defaults of the same kind
  (Regex with no match timeout, `HttpClient` following redirects) are in `rules/04` §3.
- **A README or quickstart snippet is a demo, not a configuration.** Copying it copies
  its dev-only settings: `TrustServerCertificate=True` on a `Microsoft.Data.SqlClient`
  string switches off the certificate check its defaults perform (`Encrypt` is
  `Mandatory`, `TrustServerCertificate` `false`), and `AllowAnyOrigin()`,
  `UseDeveloperExceptionPage()` or a validation callback returning `true` carry over the
  same way. *(OWASP: Vulnerable Dependency Management cheat sheet; Software Supply Chain
  Security cheat sheet; Secure Coding with AI cheat sheet; SCVS V1, V6.)*
- **A package signature is enforced only when you require it.** NuGet's "Manage package trust
  boundaries" page: *"Packages signed with untrusted certificates are considered as unsigned and are
  installed without any warnings or errors"*. To make signing a control, set `signatureValidationMode`
  to `require` in `nuget.config` and list the author or repository certificates you accept (by
  fingerprint, optionally `<owners>`) under `<trustedSigners>`. That page documents it for NuGet 4.9+
  and Visual Studio 15.9+ on Windows; whether `dotnet restore` enforces it on Linux/macOS is **not
  verified here** — test it on your CI runner with an unsigned package before relying on it. Generate
  an **SBOM** for releases. See `sota-devsecops`.
- **Runtime and framework patch level is an audit surface** (`rules/04` §4 points here). The memory-safe runtime's residual risk includes
  framework CVEs, e.g. CVE-2025-55315 (Kestrel HTTP request smuggling, fixed in 8.0.21/9.0.10/10.0 RC2)
  and CVE-2026-45591 (SignalR/Blazor Server MessagePack nested-array DoS, fixed in 8.0.28/9.0.17/10.0.9,
  June 2026). CVE-2025-55315 also covers the `Microsoft.AspNetCore.Server.Kestrel.Core` **package**
  ≤ 2.3.0 that ASP.NET Core 2.3 on .NET Framework uses (fixed in 2.3.6, per the GitHub advisory
  GHSA-5rrx-jjjq-q2r5); `dotnet --list-runtimes` cannot see a package, so check the lock files too.
  Self-contained/AOT-published apps embed the framework — they need a rebuild and redeploy, not just
  host patching.
- **A strong name is an identity, not a publisher.** Microsoft: *"Do not rely on strong names for
  security. They provide a unique identity only."*, and on .NET Core / .NET 5+ *"the runtime never
  validates the strong-name signature"*. Measured on the .NET 10 SDK: a delay-signed assembly whose
  signature was never applied reported a `PublicKeyToken` and loaded. The token proves nothing
  about who built the file. Publisher trust comes from an
  Authenticode signature on the binary or a NuGet package signature (`dotnet nuget verify`), each
  checked against the certificate you expect, not merely present. Delay signing
  (`<DelaySign>true</DelaySign>` or `AssemblyDelaySignAttribute`, public key only) is fine in
  development when only the release job holds the private key and runs `sn -R`. A committed
  `.snk` lets anyone mint that identity, which is tolerable only because it was never trust.
  *(OWASP: Code Review Guide v2.)*
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
      `grep -rnE 'dotnet_diagnostic\.[A-Z]+[0-9]+\.severity *= *none' --include='.editorconfig' --include='*.globalconfig' .`
- [ ] **"Build and Suppress Active Issues" is BASELINING: Microsoft's own term for suppressing
      every current violation at once. A large GlobalSuppressions.cs with uniform timestamps is
      its signature, and it means the analyser's verdict on that code was never read. NOTE:
      [SuppressMessage] is conditional on the CODE_ANALYSIS compilation symbol, so the attribute
      can be present in source and absent from the shipped assembly.**
- [ ] **TFM/SDK pinned? settings centralized?** —
      `grep -rnE '<TargetFramework' --include='*.csproj' --include='*.props' .` ;
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
      `curl -fsS https://builds.dotnet.microsoft.com/dotnet/release-metadata/releases-index.json | grep -oE '"(channel-version|support-phase|eol-date)": *"[^"]*"' | awk '/channel-version/{if(l)print l; l=$0; next}{l=l" "$0} END{print l}'`
      (one line per channel; `eol` = no security patches, and a near `eol-date` is the migration
      deadline; a preview channel has no `eol-date` yet; read it at audit time, never from memory. `net4x` targets
      are .NET Framework, which this index does not list — check its lifecycle separately)
- [ ] **NuGet locking + source mapping + CVE scan?** —
      `find . -name packages.lock.json -not -path '*/obj/*' | head -1` (empty = no lockfile) ;
      `err=$(grep -rn 'RestorePackagesWithLockFile' --include='*.csproj' --include='Directory.Build.props' . 2>&1 >/dev/null); rc=$?` ;
      `case $rc in 0) ;; 1) echo "lockfile not enforced (RestorePackagesWithLockFile unset) — supply-chain risk" ;; *) echo "SWEEP FAILED, not a finding about their code: $err" ;; esac`
      ;
      `err=$(grep -rniE 'packageSourceMapping|locked-mode|NuGetAudit|NU190[0-9]|auditSources|dependabot' --include='nuget.config' --include='NuGet.Config' --include='Directory.Build.props' --include='*.csproj' --include='*.yml' --include='*.yaml' . 2>&1 >/dev/null); rc=$?` ;
      `case $rc in 0) ;; 1) echo "no source mapping / locked restore / NuGetAudit CI gate" ;; *) echo "SWEEP FAILED, not a finding about their code: $err" ;; esac`
- [ ] **Strong name treated as publisher trust, or the signing key in the repo — MEDIUM (HIGH
      for a `.pfx`)** (§3) — `git ls-files '*.snk' '*.pfx' '*.p12'` (a full `.snk` is a
      key pair; a `.pfx` is an Authenticode key) ;
      `grep -rniE 'nuget verify|signtool[^ ]* verify|Get-AuthenticodeSignature|osslsigncode verify' --include='*.yml' --include='*.yaml' --include='*.ps1' --include='*.sh' . || echo "no publisher-signature check in CI or scripts"`
- [ ] **Package signatures required, not just present? MEDIUM** (§3) —
      `grep -rniE 'signatureValidationMode|<trustedSigners' --include='nuget.config' --include='NuGet.Config' --include='NuGet.config' . || echo "signatures not required: an untrusted-cert-signed package installs as unsigned"`
      (want `require` plus a `<trustedSigners>` entry; confirm your restore client enforces it)
- [ ] **Runtime / framework patch level — HIGH** (§3) — `dotnet --list-runtimes` on each host and
      base image (ASP.NET Core < 8.0.21/9.0.10 = CVE-2025-55315; < 8.0.28/9.0.17/10.0.9 = CVE-2026-45591);
      `grep -rn 'Microsoft\.AspNetCore\.Server\.Kestrel\.Core' --include='*.csproj' --include='packages.lock.json' --include='packages.config' --include='Directory.Packages.props' .`
      (≤ 2.3.0 = CVE-2025-55315, need 2.3.6); check container base-image tags; self-contained/AOT
      apps need a rebuild
- [ ] **Formatting + deterministic build in CI?** —
      `grep -rniE 'dotnet format|verify-no-changes|Deterministic|ContinuousIntegrationBuild' --include='*.yml' --include='*.yaml' --include='*.csproj' --include='*.props' .`
- [ ] **Test runner + coverage?** —
      `grep -rniE 'xunit|nunit|mstest|coverlet|testcontainers' --include='*.csproj' --include='*.props' .`
- [ ] **Package code that runs at build (`build*/…props`/`.targets` imported from packages) —
      HIGH if any is unreviewed** (§3) — after a restore, every hit is a package file MSBuild
      imports and runs:
      `grep -rnE '"build[A-Za-z]*/[^"]*\.(props|targets)": *\{' --include=project.assets.json .`
      (each hit needs an owner and a diff on bump, or `ExcludeAssets`); and the repo's own
      build-executing files need a code owner:
      `(grep -snE 'Directory\.Build|\.targets|\.props|nuget\.config|global\.json' .github/CODEOWNERS CODEOWNERS docs/CODEOWNERS; true) | grep -E . || echo "build-executing files have no CODEOWNERS entry -- HIGH"`
      (the subshell keeps a missing CODEOWNERS path from reading as "no owner")
- [ ] **New dependency adopted unvetted, or a library's insecure default left on — MEDIUM
      (HIGH for a deserializer or TLS default)** (§3) — new packages in the change, each
      needing the §3 selection checks (a version bump is not listed; assumes `Include` is the
      first attribute):
      `git diff origin/main... -- '*.csproj' '*.props' | awk -F'"' '/^-.*<Package(Reference|Version) /{old[$2]=1} /^[+].*<Package(Reference|Version) /{new[$2]=1} END{for(i in new) if(!(i in old)) print "new dependency: " i}'` ;
      explicit TLS opt-outs and Npgsql modes that do not verify the certificate:
      `grep -rniE 'TrustServerCertificate *= *(true|yes)|SSL ?Mode *= *(Disable|Allow|Prefer|Require)' --include='*.cs' --include='*.json' --include='*.config' .` ;
      Npgsql strings left on the `Prefer` default (also try `Server=`):
      `grep -rniE 'Host *= *[^;"]+;' --include='*.cs' --include='*.json' --include='*.config' . | grep -viE 'SSL ?Mode *='` ;
      MessagePack deserialization in a file that never opts into `UntrustedData`:
      `grep -rlE 'MessagePackSerializer[.]Deserialize' --include='*.cs' . | while IFS= read -r f; do grep -q 'UntrustedData' "$f" || echo "$f: MessagePack on TrustedData default"; done`
