<!-- last-verified: 2026-07 -->

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
- **Plugin/script surface:** Composer plugins can run arbitrary code at install
  time; the `allow-plugins` config must be an explicit allowlist (Composer ≥2.2
  prompts by default). Review `scripts` in composer.json diffs like code.
- Version constraints: `^` ranges (semver), never `*` or `dev-master`; pin a
  commit hash when depending on a VCS fork.

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

```bash
# Lockfile discipline
git ls-files composer.lock | grep -q . || echo "NO LOCKFILE COMMITTED (app = MEDIUM/HIGH)"
composer validate --strict                      # flags json/lock drift
grep -nE '"(php|ext-)' composer.json            # platform reqs declared?
grep -n '"platform"' composer.json              # config.platform.php pinned?

# Advisory + abandonment status right now
composer audit --locked --abandoned=report

# Risky constraints and install-time code
grep -nE '"[^"]+"\s*:\s*"(\*|dev-)' composer.json
grep -n '"scripts"' composer.json               # review script contents
grep -n 'allow-plugins' composer.json           # explicit allowlist?

# Static analysis presence + ratchet health
ls phpstan*.neon* psalm*.xml* 2>/dev/null || echo "NO STATIC ANALYSIS CONFIG (MEDIUM)"
grep -n 'level' phpstan*.neon* 2>/dev/null
wc -l phpstan-baseline.neon 2>/dev/null         # compare against last audit: shrinking?
git log --oneline -5 -- phpstan-baseline.neon 2>/dev/null

# CI gates actually wired (adjust path to CI system)
grep -rnE '(composer audit|phpstan|psalm|php-cs-fixer|phpcs|phpunit|pest)' .github/workflows/ .gitlab-ci.yml 2>/dev/null

# Dev deps leaking into prod artifacts
grep -rn 'composer install' Dockerfile* .github/workflows/ 2>/dev/null | grep -v -- --no-dev
```

Severity guide: app with no committed lock or CI running `composer update`
MEDIUM (HIGH once envs drift); no advisory gate MEDIUM; known-vulnerable dep
currently installed HIGH/CRITICAL per advisory; no static analysis MEDIUM;
growing baseline MEDIUM; dev deps in prod image LOW/MEDIUM.
