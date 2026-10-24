# 04 — Distribution & Documentation

Scope: packaging, install channels, supply-chain hygiene for installs, docs
from a single source of truth, man pages, README quickstart, CI pinning.

## 1. Packaging

- **Prefer a single static binary** (Go, Rust, Zig; or a properly bundled
  artifact otherwise). The user-visible contract: download one file, `chmod +x`,
  it runs — no runtime version conflicts, no `pip install` clobbering system
  packages, trivially pinnable in CI.
- Interpreted ecosystems: ship via the isolating installer users expect —
  `pipx`/`uv tool install` for Python, `npx`/global install for Node — and say
  so in the README; never instruct `sudo pip install`. Lock your dependency
  versions in the published artifact; a CLI that breaks because a transitive
  dep released is your bug.
- Build per-platform artifacts for at minimum: linux amd64/arm64,
  macOS amd64/arm64 (or universal), windows amd64. Predictable asset names
  (`tool_1.4.2_linux_arm64.tar.gz`) — CI scripts construct these URLs.
- The binary must not assume sibling files at runtime (embed assets); must run
  from any cwd; must not require root for normal operation.
- Don't strip `--version` info from release builds; embed version + commit at
  build time, and ensure source builds (`go install`, `cargo install`) don't
  report `dev`/`unknown` if avoidable.

## 2. Install channels & supply-chain hygiene

- Offer at least: (a) a package manager (Homebrew tap/core, apt/yum repo,
  scoop/winget, or language registry) for humans, and (b) **direct versioned
  binary downloads** for CI (§4). GitHub Releases as the canonical artifact
  store is the de facto norm.
- `curl | sh` installers are popular and acceptable **only** with discipline:
  - the script is short, readable, and pipes-safe (works when partially
    downloaded — guard by wrapping everything in a function called at EOF);
  - supports `TOOL_VERSION=1.4.2` pinning and a target-dir override; never
    silently `sudo`;
  - downloads over HTTPS and **verifies the checksum** of the artifact it
    fetches before installing.
- Publish `checksums.txt` (SHA-256 of every artifact) with each release, and
  sign your releases — current SOTA favors keyless signing (e.g. Sigstore
  `cosign`) and/or build provenance attestations (SLSA-style, GitHub artifact
  attestations) over bare GPG keys nobody verifies. Document the one-line
  verification command next to the download link, or nobody will run it.
- Package-manager installs own the binary: in-tool `self update` must detect
  and defer to them ([rules/03](03-behavior-lifecycle.md) §5).
- Don't squat ambiguous names; check registries before naming. The binary name
  is forever-API too.

## 3. Docs from one source of truth

- **`--help` is the source of truth.** Generate man pages, the docs-site CLI
  reference, and completions from the same parser definitions (clap →
  `clap_mangen`; cobra → `cobra/doc` for man + markdown; click/typer →
  sphinx-click etc.). Hand-written copies drift within two releases —
  drift between `--help` and web docs is a standing audit check.
- Ship a man page if your users live where `man` is reflexive (system tools);
  a web reference is otherwise acceptable — but `tool <cmd> --help` must then
  be fully self-sufficient, with the docs URL printed at the bottom of help.
- Docs structure that works for CLIs: quickstart → task-oriented how-tos →
  full generated reference → exit codes table → env vars table → config file
  schema. Exit codes and env vars are the pages scripts authors hunt for and
  most tools forget.
- Every example in docs must be copy-pasteable and CI-tested if feasible
  (doc-test runners / cram-style tests); stale examples are worse than none.

## 4. README quickstart & CI pinning

- README top section, in order, ≤ one screen: one-sentence what-it-is; install
  one-liner; **a 5-line quickstart that produces a visible result**:

  ```
  $ brew install tool
  $ tool init
  $ tool deploy api
  deployed api → https://api.example.dev (2.1s)
  ```

  If the quickstart needs prose paragraphs of prerequisites, the tool's
  defaults are wrong ([rules/01](01-commands-flags-config.md) §4), not the README.
- **Version pinning for CI is a feature, not an afterthought**:
  - stable per-version download URLs that never change or disappear — old
    releases stay up;
  - install paths accept an exact version (`TOOL_VERSION=…` in the script,
    `tool@1.4` in brew/npm, apt version pins);
  - provide or bless a GitHub Action / setup script with a `version:` input;
  - never offer only "latest" — CI on floating latest breaks on your release
    day, and the bug reports land on you.
- Changelog per release, human-written headline per breaking change, with the
  migration command/flag mapping. `tool` major upgrades deserve a short
  upgrade guide; deprecation warnings in-product should link to it ([rules/03](03-behavior-lifecycle.md) §7).

## Audit checklist

- [ ] Release and source builds (`go install`, `cargo install`) report a real version: `tool --version`
      on each prints a version and commit, not `dev`/`unknown`.
- [ ] Single-file (or properly isolated) install; no runtime dependency on system interpreter state; runs from any cwd without sibling files; no root required.
- [ ] Artifacts for linux/macOS (amd64+arm64) and windows with predictable names; old release assets remain downloadable.
- [ ] `checksums.txt` (SHA-256) published per release; artifacts signed or provenance-attested; verification command documented where the download link is.
- [ ] Install script (if any): function-wrapped against partial download, HTTPS-only, checksum-verifying, version-pinnable, no silent sudo.
- [ ] Man page and/or web CLI reference generated from the same definitions as `--help`; spot-check three commands for drift between `--help` and published docs.
- [ ] Docs include exit-code table, env-var table, and config schema; examples copy-pasteable and current.
- [ ] README: install + working 5-line quickstart on the first screen.
- [ ] CI consumers can pin an exact version through every advertised install channel; a "latest"-only channel is not the sole option.
- [ ] Changelog exists; breaking changes called out with migration steps; deprecation warnings link to them.
