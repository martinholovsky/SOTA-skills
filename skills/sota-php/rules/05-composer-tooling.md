# 05 — Composer, static analysis, and CI

The PHP supply chain is Composer + Packagist; code quality is enforced by
static analysis, not convention. A project without a committed lockfile, an
audit gate, and PHPStan/Psalm in CI is unreviewed by 2026 standards.

## 1. Composer discipline

- **Apps commit `composer.lock`.** CI and prod run `composer install` — which
  installs the exact locked versions — never `composer update`, which
  re-resolves and rewrites the lock (getcomposer.org CLI docs). Updates are
  deliberate PRs with a lock diff.
- Libraries don't ship a lock to consumers but should still test against
  lowest and highest supported dependency sets
  (`composer update --prefer-lowest` in one CI job).
- **Production install:**

```sh
composer install --no-dev --prefer-dist --no-interaction --no-progress \
  --optimize-autoloader
composer check-platform-reqs   # ext-* and PHP version actually present?
```

  `--no-dev` keeps test/dev tooling out of the artifact (attack surface +
  size); `--optimize-autoloader` see `rules/06` §5.
- **Platform requirements:** declare the PHP floor and every extension in
  `require` (`"php": "^8.3", "ext-pdo": "*", "ext-sodium": "*"`); set
  `config.platform.php` to the floor so resolution on a dev machine with a
  newer PHP can't pull packages the servers can't run (getcomposer.org docs).
- **Code that runs at install time.** `composer install` executes third-party code before
  any test or reviewer sees the change, with the credentials of the developer or CI runner.
  Know every entry point:
  - **Plugins** (`"type": "composer-plugin"` in any dependency) are loaded into the Composer
    process itself and hook its events. Since Composer 2.2, `config.allow-plugins` gates them;
    its default `{}` allows none. Interactive runs prompt; a `--no-interaction` run **fails**
    on an unlisted plugin (unless the plugin marks itself `plugin-optional`). Keep it an
    explicit per-package map (`"vendor/name": true`, unneeded ones `false`), never `true` or
    `"*": true`. Measured on Composer 2.10.3: an unlisted plugin aborted a non-interactive
    update with exit 1; once listed, it ran.
  - **Root `scripts`.** Only the root package's scripts run; a dependency's own `scripts` block
    is ignored (measured: it did not run). But a root script routinely *calls into* dependency
    code: a PHP callback into a vendor class, or a framework console command that boots the
    framework (the Laravel skeleton wires `Illuminate\Foundation\ComposerScripts::postAutoloadDump`
    and `@php artisan package:discover` to `post-autoload-dump`, which also fires on plain
    `composer dump-autoload`).
  - **`composer create-project`** makes the *downloaded template* the root package, so its
    `post-root-package-install` / `post-create-project-cmd` scripts run; add `--no-scripts`
    for a template you have not read.
  - **Native extensions:** PIE (and legacy `pecl install`) build from source with `phpize`,
    `./configure`, `make`, `make install` (PIE elevates with `sudo` if it cannot write the
    extension dir). Running `pie install` in a project directory builds every missing `ext-*`
    the project requires; `pecl install` takes `-B`/`--nobuild` to skip C builds. Build
    extensions in the image build, not ad hoc on a runner with secrets.
  - **Switches:** `--no-plugins` and `--no-scripts` exist on `install`, `update`, `require`,
    `dump-autoload` and `create-project`. In CI, run `composer install --no-scripts --no-plugins`
    in a step or job that holds **no** deploy keys, registry-publish tokens or cloud
    credentials, then run the scripts you actually need (`composer run-script <event>`) as a
    separate, reviewed step. If the build depends on an allowlisted plugin (e.g. a custom
    installer), keep plugins on and isolate the whole install job instead.
  - **Review:** on every dependency bump, diff what executes, not only the version: for each
    allowlisted plugin, read the upstream tag-to-tag diff between the old and new locked
    versions (or `diff -r` the two installed `vendor/<pkg>` trees), plus any class a root
    script calls.
    Put the repo's own executing files (`composer.json`, `composer.lock`, CI workflow files,
    `Dockerfile`) under CODEOWNERS with required code-owner review, including a change an AI
    agent authored: an added `allow-plugins` entry or script line is a code-execution grant.
  OWASP: CI/CD Security, Software Supply Chain Security, and NPM Security cheat sheets.
- Version constraints: `^` ranges (semver), never `*` or `dev-master`; pin a
  commit hash when depending on a VCS fork.
- **Repository provenance and dependency confusion.** Composer looks a package up in the
  topmost repository and, when that repository is canonical (the default), never looks
  further. Keep every private repository canonical: Composer's own repository-priorities
  docs describe a non-canonical private repo whose `foo/bar ^2.0` is silently replaced by a
  `foo/bar 2.999` someone published to packagist.org. Keep `secure-http` at its default
  `true` (HTTPS-only downloads), and when disabling packagist.org because an internal
  registry mirrors it, check the mirror itself is the only source. A patched or forked
  package gets its own name or version suffix, published through the internal registry with
  the upstream commit it patches, never a local path repository in production.
  OWASP SCVS 6.x (point of origin, pedigree).
- **Adopting a new dependency: vet it before `composer require`.** This applies unchanged to a
  package name an AI assistant proposed: a name that does not exist yet can be registered by
  an attacker afterwards (slopsquatting), and a vendor or package one character off the real
  one is a typosquat.
  - **Identity.** `composer show --all <vendor>/<name>` exits 1 with `Package ... not found`
    for a name no configured repository has; for one that exists it prints the licence, the
    `source` repository, every released version and the latest release date. The `source`
    must be the project you meant (check it against the project's own docs), under its
    real vendor prefix.
  - **Registry metadata.** `https://packagist.org/packages/<vendor>/<name>.json` gives `time`
    (when the name was first registered), `maintainers`, `downloads`, `dependents`, and an
    `abandoned` key when the package is abandoned. Stop and look closer at a name registered
    days ago, a single maintainer with nothing else published, one or two releases, or a
    source repository that does not match. Open advisories:
    `https://packagist.org/api/security-advisories/?packages[]=<vendor>/<name>`; after
    install, `composer licenses` lists every package's declared licence.
  - **Scorecard.** deps.dev has no Packagist package index (its package API covers Go,
    RubyGems, npm, Cargo, Maven, PyPI and NuGet), so query the source repository instead:
    `https://api.deps.dev/v3/projects/github.com%2F<owner>%2F<repo>` returns its OpenSSF
    Scorecard result, as does `https://api.securityscorecards.dev/projects/github.com/<owner>/<repo>`
    or the CLI `scorecard --repo=github.com/<owner>/<repo>`.
- **Insecure defaults of what you consume.** A library's option values are part of your code:
  when adopting a package, list its security-relevant options and set each one explicitly
  rather than inheriting the default. Measured 2026-09-25 on the latest releases:
  - **Guzzle** (8.2.0): `timeout` defaults to `0`, meaning no total limit, so `new Client()`
    lets one stalled upstream hold an FPM worker indefinitely. Set `timeout` and
    `connect_timeout`.
  - **league/commonmark** (2.10.3): `html_input` defaults to `allow` and `allow_unsafe_links`
    to `true`, so `new CommonMarkConverter()` passes `<script>` and `javascript:` links
    through. `GithubFlavoredMarkdownConverter` filters a few tags such as `<script>` but still
    emitted `<img onerror=...>` and `javascript:` links. For untrusted Markdown set
    `'html_input' => 'escape'` (or `'strip'`) and `'allow_unsafe_links' => false`.
  - **erusev/parsedown** (1.8.0): safe mode is off unless `setSafeMode(true)` is called;
    without it raw HTML and `javascript:` links pass through.
  - **dompdf** (3.1.6): `isRemoteEnabled` and `isPhpEnabled` default to `false`. Keep them
    off; turning on remote fetching for HTML a user influences is SSRF (`rules/03`).
- **Documentation samples are demos, not production code.** A README or docblock snippet
  carries demo settings into your code: Guzzle's own `Client` constructor docblock shows
  `'timeout' => 0` against an `http://` base URI. Before pasting a sample, re-derive every
  option it sets (`'verify' => false`, debug mode, `Access-Control-Allow-Origin: *`) from
  this skill rather than from the sample.
  OWASP: Vulnerable Dependency Management, Software Supply Chain Security, and Secure Coding
  with AI cheat sheets; OWASP SCVS V1, V6.

## 2. composer audit and advisory gates

`composer audit` checks installed (or `--locked`) packages against security
advisories via the Packagist API, and also reports abandoned packages; exit
code is non-zero when issues are found — CI-gateable (getcomposer.org CLI
docs):

```sh
composer audit --locked --abandoned=fail   # in CI, on every PR + nightly
```

- `--format=json` for tooling; `--ignore-severity` exists but each ignore needs
  a tracked justification.
- Abandoned packages are a real risk class (unpatched forever) — at minimum
  `--abandoned=report` and a migration ticket per hit.
- Alternative/complementary: requiring `roave/security-advisories` (neutral
  example) makes *installing* a known-vulnerable version impossible at resolve
  time.
- Renovate/Dependabot-style automation keeps the lock fresh; pair with the
  audit gate so urgency is advisory-driven, not calendar-driven.

## 3. Static analysis: PHPStan or Psalm, gating CI

**PHPStan** has rule levels **0–10**; 10 (added in PHPStan 2.0) also flags
*implicit* `mixed` — missing types — not just explicit ones
(phpstan.org/user-guide/rule-levels).

```neon
# phpstan.neon (or phpstan.dist.neon)
parameters:
    level: 10          # new code: max; legacy: highest level that holds
    paths: [src, tests]
```

- **New projects start at the max level.** Legacy projects: pick the highest
  level, generate a baseline (`phpstan analyse --generate-baseline`), and
  enforce the **ratchet**: the baseline file only ever shrinks. A growing
  baseline means the gate is theater — MEDIUM finding.
- Don't silence with `@phpstan-ignore` casually; each ignore carries a reason
  string. Prefer fixing types; use generics PHPDoc
  (`@template`, `array<int, Order>`) so collections stay typed.
- **Psalm** is the equivalent alternative (note its levels run inverted:
  1 = strictest, 8 = loosest). Run one of them, not both, at the strictest
  sustainable setting; `--taint-analysis` mode (Psalm) is a useful audit
  supplement for injection tracing.
- The type checker runs on PRs against the same PHP version(s) as prod, with
  extensions available (or stubs configured).

## 4. Style and tests

- **Formatting is automated, not reviewed:** PHP-CS-Fixer or PHP_CodeSniffer
  (neutral examples) pinned to the **PER-CS** ruleset (PHP-FIG's successor to
  PSR-12; PER-CS 2.x current — php-fig.org). `--dry-run --diff` in CI; local
  fix via pre-commit/composer script.
- **Tests:** PHPUnit is the baseline; Pest (neutral example) layers a concise
  syntax on the same runner. Either way: data providers over copy-paste, one
  behavior per test, no order dependence, `assertSame` over `assertEquals`
  (strict comparison). Test *strategy* — suite shape, doubles, flake policy —
  lives in `sota-testing`.
- Coverage needs a driver: pcov (fast, coverage-only) or Xdebug in coverage
  mode — CI-only; never on prod (`rules/06` §6).
- Mutation testing (e.g. Infection) as a periodic quality probe on core
  domains, not a per-PR gate.

## 5. CI pipeline: the minimum gate set

Every PR, in rough dependency order:

```sh
composer validate --strict          # composer.json sanity + lock in sync
composer install --no-interaction   # from lock, cached
composer audit --locked             # advisories + abandoned
vendor/bin/php-cs-fixer check --diff
vendor/bin/phpstan analyse --no-progress
vendor/bin/phpunit                  # or: vendor/bin/pest
```

- **Matrix:** run tests on every PHP minor the code claims to support
  (`require.php`), floor *and* current — a `^8.2` constraint tested only on
  8.5 is untested advertising.
- Nightly job re-runs `composer audit` (advisories land independent of
  commits).
- Pipeline/runner/secrets hardening (pinned actions, OIDC, SLSA) →
  sota-devsecops; this file owns only the PHP-specific gates.

## Audit checklist

Run from repo root; verify each hit manually.

- [ ] **Lockfile discipline** —
      `git ls-files composer.lock | grep -q . || echo "NO LOCKFILE COMMITTED (app = MEDIUM/HIGH)"`
      ; `composer validate --strict` (flags json/lock drift);
      `grep -nE '"(php|ext-)' composer.json` (platform reqs declared?);
      `grep -n '"platform"' composer.json` (config.platform.php pinned?)
- [ ] **Advisory + abandonment status right now** — `composer audit --locked --abandoned=report`
- [ ] **Risky constraints and install-time code** —
      `grep -nE '"[^"]+"\s*:\s*"(\*|dev-)' composer.json` ; `grep -n '"scripts"' composer.json`
      (review script contents); `grep -n 'allow-plugins' composer.json` (explicit allowlist?)
- [ ] **Code that runs at install time is contained (§1) — HIGH if the install job holds
      secrets, else MEDIUM** —
      `grep -rnE 'composer[[:space:]]+(install|update|create-project)' --include='*.yml' --include='*.yaml' --include='Dockerfile*' --exclude-dir=vendor --exclude-dir=node_modules . 2>/dev/null | grep -v -- --no-scripts`
      ; `grep -nE '"(allow-plugins|\*)"[[:space:]]*:[[:space:]]*true' composer.json`
      ; `grep -lE 'composer\.(json|lock)' CODEOWNERS .github/CODEOWNERS docs/CODEOWNERS 2>/dev/null | grep -q . || echo "composer.json/lock HAVE NO CODE OWNER"`
      (each install hit runs plugins and root scripts: confirm that job has no deploy/publish
      credentials, or add `--no-scripts --no-plugins`; a blanket `true` lets any new
      dependency's plugin execute; without a code owner, a new script line or
      `allow-plugins` entry, human- or agent-authored, merges unreviewed)
- [ ] **Repository provenance / dependency confusion (§1) — HIGH** —
      `grep -nE '"(canonical|secure-http)"[[:space:]]*:[[:space:]]*false|"type"[[:space:]]*:[[:space:]]*"path"' composer.json`
      (a non-canonical private repository lets a higher version published to packagist.org
      win; `secure-http: false` allows plain-HTTP downloads; a `path` repository in a
      production build ships an unpublished local copy)
- [ ] **New dependency vetting and insecure library defaults (§1) — HIGH when untrusted
      Markdown renders unescaped or dompdf fetches remote resources, MEDIUM for a missing
      timeout** — for each package added to `composer.json` since the last audit, run
      `composer show --all <vendor>/<name>` and read its Packagist `.json` (`time`,
      `maintainers`, source repo); then
      `grep -rnE "'(connect_)?timeout'[[:space:]]*=>[[:space:]]*0([^.0-9]|$)|'html_input'[[:space:]]*=>[[:space:]]*'allow'|'allow_unsafe_links'[[:space:]]*=>[[:space:]]*true|'is(Remote|Php)Enabled'[[:space:]]*=>[[:space:]]*true|setIs(Remote|Php)Enabled\([[:space:]]*true" --include='*.php' --exclude-dir=vendor . ; grep -rlE 'GuzzleHttp|(CommonMark|GithubFlavoredMarkdown)Converter|Parsedown' --include='*.php' --exclude-dir=vendor . | while IFS= read -r f; do grep -qE 'new[[:space:]]+[\\A-Za-z]*(GuzzleHttp\\Client|Client)[[:space:]]*\(' "$f" && grep -q 'GuzzleHttp' "$f" && ! grep -q "'timeout'" "$f" && echo "GUZZLE CLIENT WITHOUT timeout: $f"; grep -qE 'new[[:space:]]+[\\A-Za-z]*(CommonMark|GithubFlavoredMarkdown)Converter' "$f" && ! grep -q "'html_input'" "$f" && echo "MARKDOWN CONVERTER WITHOUT html_input: $f"; grep -qE 'new[[:space:]]+[\\A-Za-z]*Parsedown' "$f" && ! grep -q 'setSafeMode(true)' "$f" && echo "PARSEDOWN WITHOUT setSafeMode(true): $f"; done`
      (the first command prints explicit unsafe values, the loop prints files that construct
      one of these libraries and never set the option; the options are the ones §1 lists, so
      extend both halves for every other library whose defaults you have checked)
- [ ] **Static analysis presence + ratchet health** —
      `ls phpstan*.neon* psalm*.xml* 2>/dev/null | grep -q . || echo "NO STATIC ANALYSIS CONFIG (MEDIUM)"`
      ; `grep -n 'level' phpstan*.neon* 2>/dev/null` ; `wc -l phpstan-baseline.neon 2>/dev/null`
      (compare against last audit: shrinking?);
      `git log --oneline -5 -- phpstan-baseline.neon 2>/dev/null`
- [ ] **CI gates actually wired (adjust path to CI system)** —
      `grep -rnE '(composer audit|phpstan|psalm|php-cs-fixer|phpcs|phpunit|pest)' .github/workflows/ .gitlab-ci.yml 2>/dev/null`
- [ ] **Dev deps leaking into prod artifacts** —
      `grep -rn 'composer install' Dockerfile* .github/workflows/ 2>/dev/null | grep -v -- --no-dev`

Severity guide: app with no committed lock or CI running `composer update`
MEDIUM (HIGH once envs drift); no advisory gate MEDIUM; known-vulnerable dep
currently installed HIGH/CRITICAL per advisory; no static analysis MEDIUM;
growing baseline MEDIUM; dev deps in prod image LOW/MEDIUM.