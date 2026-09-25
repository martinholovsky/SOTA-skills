# 04 — Supply chain & tooling: Bundler, linting, scanning, CI

The Ruby supply chain runs through RubyGems + Bundler; the quality gates are
a linter, a security scanner, a dependency auditor, and the test suite —
all wired into CI from day one.

## 1. Bundler and Gemfile discipline

- **Applications commit `Gemfile.lock`.** Gems (libraries) don't ship it in
  the package but committing it for dev reproducibility is fine; keep the
  gemspec constraints permissive either way.
- **CI and production install frozen**: `bundle config set --local frozen
  true` or `BUNDLE_FROZEN=true` — the build fails if `Gemfile` and lockfile
  drift instead of silently re-resolving. The old `bundle install --frozen`
  flag was removed in Bundler 4: it now exits 15 with a message pointing at
  `bundle config set frozen true` (measured, Bundler 4.0.16), so a CI script
  still passing it fails rather than installing frozen. On Bundler 2.x the flag
  still worked but printed a deprecation; replace it either way.
- Deployment installs also set `BUNDLE_WITHOUT=development:test`.
- Version constraints: pessimistic (`~> 7.2`) for frameworks, exact pins only
  with a reason; `>=`-only constraints on security-sensitive gems are drift.
- **Git-sourced gems pinned to a full SHA** (`git: ..., ref: "<sha>"`), never
  a branch — branches are mutable supply chain.
- One global `source "https://rubygems.org"`; private gems go in a scoped
  `source "https://gems.example.internal" do ... end` block so a public gem
  can't shadow an internal name (dependency-confusion class). Bundler 4
  enforces this: a Gemfile with a second global `source` line fails to resolve
  ("multiple global sources", exit 4, measured on 4.0.16). A project still
  pinned to Bundler 2.x (`BUNDLED WITH` in the lockfile) gets only a warning,
  so there the check below is a real finding.
- Keep `bundle outdated` visible (report job), and update via PRs from
  Dependabot/Renovate (neutral examples) rather than bulk manual bumps.

### 1.1 Code that runs at install time

`bundle install` executes dependency code before any test runs, with the installing
user's environment (measured on RubyGems/Bundler 4.0.16: a gem's `extconf.rb` saw every
`*_TOKEN` variable of the shell that ran the install). The entry points:

- **Native-extension builders** — each path in a gemspec's `extensions` is run by type:
  `extconf.rb` (mkmf), `configure`, `Rakefile`/`mkrf_conf`, `CMakeLists.txt`, `Cargo.toml`
  (RubyGems `Gem::Ext::Builder#builder_for`). Neither `gem install` nor Bundler has a
  switch that skips them; a precompiled platform gem skips the build but ships a binary
  you run anyway, and `force_ruby_platform` forces the source build.
- **`rubygems_plugin.rb`** in a gem's `lib/` is copied to the plugins directory and
  loaded right after `gem install` and again by every later `gem` command (measured);
  Bundler's installer calls `Gem.load_plugins` as well (source read).
- **Bundler plugins** — a `plugin "name"` line in the Gemfile installs and runs one.
  `BUNDLE_PLUGINS=false` (`bundle config set plugins false`) turns the Bundler plugin
  system off; it is on by default and does not affect the two points above.
- **Evaluated Ruby** — the Gemfile itself, and the `.gemspec` of every `git:`/`path:`
  source, are `eval`ed by Bundler at resolve time.

Review: on every `Gemfile.lock` bump, list the gems that build or plug in —
`bundle exec ruby -e 'Bundler.load.specs.each { |s| puts [s.full_name, *s.extensions, *s.plugins].join(" ") unless s.extensions.empty? && s.plugins.empty? }'`
— and diff those files between versions (`gem unpack NAME -v OLD` / `-v NEW`). The repo's
own build-executing files (`Gemfile`, `*.gemspec`, `Rakefile`, `ext/**`, `.bundle/config`,
`bin/setup`) get a CODEOWNERS entry and required owner review, AI-authored changes
included. CI: run `bundle install` in a step or job whose environment holds no deploy or
publish credentials, and hand the installed bundle to later jobs as an artifact/cache.
(OWASP: CI/CD Security cheat sheet; Software Supply Chain Security cheat sheet; NPM
Security cheat sheet, for the same class in npm.)

## 2. Lockfile checksums

Bundler 2.6 (2024-12) shipped lockfile checksum verification: a `CHECKSUMS`
section records each gem's SHA-256 and installs fail if a downloaded gem no
longer matches — protecting against registry tampering or a compromised
mirror ([Bundler 2.6 announcement](https://bundler.io/blog/2024/12/19/bundler-v2-6.html)).

```bash
bundle lock --add-checksums                # add CHECKSUMS to an existing lockfile
bundle config set lockfile_checksums true  # Bundler 2.6-2.x: include in new lockfiles
```

- **Enable it** on apps: one command, no workflow change afterward.
- The bare `bundle config lockfile_checksums true` form (no `set`) is
  deprecated in Bundler 4 and prints a warning naming the `set` form.
- On Bundler/RubyGems 4 (released 2025-12,
  [upgrade notes](https://blog.rubygems.org/2025/12/03/upgrade-to-rubygems-bundler-4.html)),
  a **newly generated** lockfile carries a `CHECKSUMS` section by default
  (measured: `bundle lock` on a fresh Gemfile with no config, Bundler 4.0.16).
  An **existing** lockfile does not gain one on its own — run
  `bundle lock --add-checksums` once and commit the result. Verify current
  behavior when Bundler major versions change.

### 2.1 Which index you trust: alternative indexes and mirrors

The index behind a `source` line decides which bytes arrive for every gem name, so choosing
one is a trust decision, recorded like any other dependency choice. The ecosystem now has
more than one credible choice: Ruby core took over the RubyGems and Bundler repositories, run
jointly with Ruby Central ([ruby-lang.org, 2025-10-17](https://www.ruby-lang.org/en/news/2025/10/17/rubygems-repository-transition/)),
and former rubygems.org maintainers and operators launched [gem.coop](https://gem.coop/), which
states it mirrors every rubygems.org gem in real time and is selected with
`source "https://gem.coop"`. Corporate proxies and `bundle config set mirror.<url> <url>` do
the same thing more quietly.

- **One global source still** (§1): switch it, don't add a second one. Bundler 4 refuses two.
- **CHECKSUMS is what makes a mirror safe to try.** Measured 2026-09-25 on Bundler 4.0.16 with
  two local indexes serving different bytes for the same `demo 0.1.0`: with a committed
  `CHECKSUMS` section, redirecting the source through `mirror.<url>` failed the install
  (exit 37, naming the mismatching gem and the API that served it); with the section deleted
  the same install exited 0 and loaded the other index's code.
- **Checksums do not survive an edited `source` line.** Changing the Gemfile's `source` to the
  second index and running a non-frozen `bundle install` exited 0 and **rewrote** the
  `CHECKSUMS` line to the new index's hash (same measurement). So an index switch is reviewed
  in the lockfile diff: every `name (version) sha256=` line whose version is unchanged but
  whose hash changed is a gem the new index serves differently, and each one needs an
  explanation before merge. CI installs frozen (§1), which refuses the switch outright.
- **The escape hatch is the finding.** `bundle config set disable_checksum_validation true`
  (`BUNDLE_DISABLE_CHECKSUM_VALIDATION`) let the mismatching mirror install with exit 0 in the
  same test, and Bundler's own error message offers it as the fix. It belongs nowhere in CI,
  `.bundle/config` or a Dockerfile.
- Mirror settings live outside the Gemfile (`.bundle/config`, `~/.bundle/config`,
  `BUNDLE_MIRROR__...` variables), so a reviewer reading only the Gemfile does not see them:
  `bundle config list` shows every level.

## 3. Dependency vulnerability auditing

- **bundler-audit** checks `Gemfile.lock` against the community
  [ruby-advisory-db](https://github.com/rubysec/ruby-advisory-db):

```bash
gem install bundler-audit
bundle audit check --update    # --update pulls the latest advisory DB
```

  Gate CI on it; handle a genuinely-unfixable advisory with an explicit
  `--ignore CVE-...` entry plus a tracking issue, never by dropping the gate.
- Complementary scanners (neutral examples): OSV-Scanner, Trivy, or GitHub
  Dependabot alerts — any is fine; at least one must be on and acted upon.
- Beyond CVEs: before adopting a gem, check maintenance (last release,
  open CVE history, bus factor) — a transitively-pulled unmaintained gem is
  a finding at MEDIUM. The full pre-adoption check is §3.1.

### 3.1 Adopting a new gem (selection and the defaults you inherit)

Applies equally to a gem a person picks and one an AI assistant proposes — an
assistant can name a gem that does not exist, or one a squatter registered after
the name started being suggested. Before the `gem` line lands:

- **Exact name, intended project.** `gem search --remote --exact NAME` (or
  `curl -s https://rubygems.org/api/v1/gems/NAME.json` — a 404 means no such gem).
  Compare against near-miss spellings; `source_code_uri` in that JSON is
  self-declared by the publisher, so open the repository and confirm it builds
  *this* gem name.
- **Age and release history** — `.../api/v1/versions/NAME.json` lists every
  release with `created_at`; a first release weeks old, or one burst of versions
  after years of silence, needs a reason.
- **Maintainers** — `.../api/v1/gems/NAME/owners.json` (`gem owner NAME` asks for
  credentials); a single owner is bus-factor risk, and `rubygems_mfa_required` in
  the gem's `metadata` says whether pushes require MFA.
- **Advisories, licence, project health** — deps.dev
  (`https://api.deps.dev/v3/systems/rubygems/packages/NAME/versions/VER` gives
  `licenses` and `advisoryKeys`; the linked project record carries an OpenSSF
  Scorecard result, also at `https://api.securityscorecards.dev/projects/github.com/OWNER/REPO`),
  plus the gem's directory in ruby-advisory-db.

**The gem's options are your code.** Read the security section of its docs and
set every security-relevant option explicitly; review each option passed at the
call site. Verified examples:

- **Oj** — `Oj.load` defaults to `:object` mode, where the document names which
  loaded class is allocated and sets its instance variables. Untrusted JSON:
  `Oj.load(s, mode: :strict)`, `Oj.strict_load`/`Oj.safe_load`, or
  `Oj.default_options = { mode: :strict }` at boot.
- **Erubi** — `Erubi::Engine.new(src)` does not escape `<%= %>` unless
  `escape: true`; stdlib `ERB.new` never escapes (use `ERB::Util.h`). See rules/03 §1.
- **`Net::HTTP`** — `open_timeout`, `read_timeout` and `write_timeout` all default
  to 60 s; clients built on it inherit that unless configured (rules/03 §6).

**README snippets are demos.** A copied quick-start carries its demo settings —
`verify_mode: OpenSSL::SSL::VERIFY_NONE`, `origins "*"`, debug/dev mode,
hard-coded keys — into production; diff each pasted block against the gem's
security docs before merging.
(OWASP: Vulnerable Dependency Management cheat sheet; Software Supply Chain
Security cheat sheet; Secure Coding with AI cheat sheet; SCVS V1, V6.)

## 4. Lint and style: RuboCop or StandardRB

- Pick **one**:
  - **RuboCop** — configurable; pair with plugins matching the stack
    (`rubocop-performance`, `rubocop-rails`, `rubocop-rspec`,
    `rubocop-minitest` as applicable). Set `TargetRubyVersion` to the real
    floor. New projects: start from `AllCops: NewCops: enable` and prune,
    rather than a 400-line inherited config.
  - **StandardRB** — zero-config RuboCop distribution (`standardrb --fix`);
    the right call when style debate costs more than the defaults.
- CI runs it in check mode (`rubocop --parallel` / `standardrb`); local
  pre-commit runs autofix. A `.rubocop_todo.yml` is a paydown backlog, not a
  permanent mute — flag todo files older than ~6 months.
- **Never silence Security/* cops** to get green; each `rubocop:disable
  Security/...` needs a justification comment.

## 5. Static security analysis

- **Brakeman** for Rails apps (neutral example; it is Rails-specific):
  `brakeman -q --no-pager --exit-on-warn` in CI. Manage false positives via
  `brakeman.ignore` with a note per entry — an ignore file nobody can explain
  is a finding.
- Non-Rails codebases: RuboCop's `Security/*` cops plus the greps in
  `rules/02`/`rules/03`; Opengrep with a Ruby ruleset is a good neutral
  supplement.
- Secret scanning (gitleaks/trufflehog as neutral examples) runs on every
  push, on the full history at least once.

## 6. Tests: RSpec / Minitest mechanics

Suite *strategy* — shape, TDD, doubles, test data, flake policy — lives in
`sota-testing`; load it for any build that writes logic. Ruby runner
mechanics only:

- Match the project's existing runner (RSpec or Minitest); don't mix.
- **Run randomized**: RSpec `config.order = :random` (+ `Kernel.srand
  config.seed`), Minitest randomizes by default — a suite that only passes
  in-order has hidden coupling. Record the seed in CI output for replays.
- Parallelize (`parallel_tests`, Rails' built-in parallel testing, or
  `flatware` as neutral examples) once the suite exceeds a few minutes;
  DB-per-process is the usual prerequisite.
- Coverage via SimpleCov with a ratchet (fail if coverage drops), not a
  vanity threshold.
- Time-dependent code: freeze time (`ActiveSupport::Testing::TimeHelpers`
  or the timecop gem as neutral examples); no `sleep`-based assertions.
- HTTP in tests: stub at the boundary (WebMock/VCR as neutral examples) and
  **disable real network** (`WebMock.disable_net_connect!`).

## 7. CI gates (the minimum green wall)

Every PR runs, in rough cost order:

1. `bundle install` **frozen** against the committed lockfile (checksums on);
2. lint: `rubocop --parallel` or `standardrb`;
3. security: `bundle audit check --update`, plus `brakeman` on Rails;
4. tests with randomized order and the coverage ratchet;
5. (typed projects) `srb tc` or `steep check`.

The Ruby version in CI comes from `.ruby-version` (setup-ruby-style actions
read it) — never a hardcoded duplicate that can drift.

## 8. Authoring and publishing gems

- `gemspec` metadata complete (`homepage`, `source_code_uri`,
  `changelog_uri`); `required_ruby_version` reflects the tested floor.
- **Semantic versioning honestly** — breaking changes bump major; deprecate
  with warnings one minor ahead.
- Don't vendor secrets or `.gem` credentials in the repo; publishing uses
  **RubyGems trusted publishing (OIDC)** from CI or an MFA-protected account
  — [rubygems.org supports both](https://guides.rubygems.org/trusted-publishing/);
  enable MFA on the account regardless.
- Keep the file list tight (`spec.files` via `git ls-files` minus tests/CI);
  users install what you ship.

## Audit checklist

Run from repo root; verify each hit manually.

- [ ] **Lockfile discipline** —
      `ls Gemfile.lock 2>/dev/null | grep -q . || echo "NO LOCKFILE (app = MEDIUM)"` ;
      `grep -c "CHECKSUMS" Gemfile.lock || echo "no checksums section (LOW, easy win)"` (stderr
      kept: no file != no match);
      `grep -rnE 'BUNDLE_FROZEN|frozen[[:space:]]+true|frozen:[[:space:]]*"?true' .github/ .gitlab-ci.yml .bundle/config 2>/dev/null | head -3`
      (no hit = installs are not frozen, MEDIUM) ;
      `grep -rnE 'bundle[[:space:]]+install[^#]*--frozen' --exclude-dir=.git --exclude-dir=vendor --exclude-dir=node_modules .`
      (each hit is a removed flag: exit 15 on Bundler 4, deprecated on 2.x — not compliance)
- [ ] **Code that runs at install time (Bundler plugins, extconf builds) without an
      owner — MEDIUM (HIGH if the install step holds secrets)** (§1.1) — each hit is a Bundler
      plugin; the second part prints when no CODEOWNERS entry covers the build files —
      `grep -nE '^[[:space:]]*plugin[[:space:]]+["'"'"']' Gemfile gems.rb 2>/dev/null` ;
      `[ -n "$(grep -lsE '(Gemfile|gemspec|Rakefile|ext/)' .github/CODEOWNERS CODEOWNERS docs/CODEOWNERS)" ] || echo "NO CODEOWNERS entry for build-executing files"`
- [ ] **Mutable git sources — MEDIUM** — `grep -nE "git:|github:" Gemfile | grep -v "ref:"`
- [ ] **Multiple top-level sources (dependency confusion) — HIGH on Bundler ≤ 2.x** —
      `grep -E '^source[[:space:]]' Gemfile | grep -cvE '[[:space:]]do[[:space:]]*$'` (global sources;
      >1 = investigate) ; `grep -A1 'BUNDLED WITH' Gemfile.lock`
      (Bundler 4 refuses to resolve such a Gemfile, so on 4.x a hit is a broken build,
      not a silent confusion risk)
- [ ] **Index trust: alternative source, mirror, checksum bypass (§2.1) — HIGH for a checksum
      bypass or an unexplained hash change, INFO for a recorded index choice** — first command
      prints a global source other than rubygems.org (confirm the decision is recorded); second
      prints mirror redirects and the checksum switch in the repo; third prints the effective
      config at every level; fourth prints each gem whose lockfile hash changed while its
      version did not —
      `grep -nE '^[[:space:]]*source[[:space:]]' Gemfile gems.rb 2>/dev/null | grep -vE 'https://rubygems\.org/?["'"'"']|[[:space:]]do[[:space:]]*$'` ;
      `grep -rnE 'disable_checksum_validation|DISABLE_CHECKSUM_VALIDATION|BUNDLE_MIRROR__|mirror\.https?:' --exclude-dir=.git --exclude-dir=vendor --exclude-dir=node_modules .` ;
      `bundle config list 2>/dev/null | grep -iE -A2 'mirror|checksum'` ;
      `git diff origin/main -- Gemfile.lock | awk '/^-  [^ ].* sha256=/ { o[$2 " " $3] = $4 } /^\+  [^ ].* sha256=/ { n[$2 " " $3] = $4 } END { for (k in n) if ((k in o) && o[k] != n[k]) print "HASH CHANGED, SAME VERSION: " k }'`
- [ ] **Vulnerability gates present?** —
      `grep -rn "bundler-audit\|bundle audit" .github/ Gemfile* Rakefile 2>/dev/null | head -2`
      ; `grep -rn "brakeman" .github/ Gemfile* 2>/dev/null | head -2` (Rails apps only)
- [ ] **Advisory scan (live)** — `bundle audit check --update 2>/dev/null | tail -5`
- [ ] **New dependency not vetted, or its insecure default kept — MEDIUM (HIGH if
      `Oj.load` in `:object` mode reads request data)** (§3.1) — first command prints each
      gem added to the Gemfile since `origin/main` (each needs the §3.1 record); second
      prints `Oj.load`/`Erubi::Engine.new` calls not setting the safe option (clean if a
      boot-time `Oj.default_options = { mode: :strict }` exists) —
      `comm -13 <(git show origin/main:Gemfile | sed -nE "s/^[[:space:]]*gem[[:space:]]+['\"]([^'\"]+)['\"].*/\1/p" | sort -u) <(sed -nE "s/^[[:space:]]*gem[[:space:]]+['\"]([^'\"]+)['\"].*/\1/p" Gemfile | sort -u)` ;
      `grep -rnE 'Oj\.load[[:space:](]|Erubi::Engine\.new' --include='*.rb' . | grep -vE 'mode:[[:space:]]*:strict|escape:[[:space:]]*true'`
- [ ] **Lint posture** — `ls .rubocop.yml .standard.yml 2>/dev/null` ;
      `grep -rn "rubocop:disable Security" --include='*.rb' .` ;
      `find . -name .rubocop_todo.yml -newermt "6 months ago" 2>/dev/null | head -1`
- [ ] **Brakeman ignores without justification (manual review)** —
      `python3 -c "import json;d=json.load(open('config/brakeman.ignore'));print(len(d.get('ignored_warnings',[])))" 2>/dev/null`
- [ ] **CI Ruby version drift** —
      `grep -rn "ruby-version\|ruby:" .github/workflows/ 2>/dev/null | grep -v ".ruby-version" | head`
- [ ] **Test determinism** —
      `grep -rn "order = :random\|--seed" .rspec spec/spec_helper.rb 2>/dev/null | head -2` ;
      `grep -rn "disable_net_connect" spec/ test/ 2>/dev/null | head -1`

Severity guide: no lockfile / unfrozen production installs MEDIUM (HIGH if
deploys resolve fresh); unpinned git gems, missing vulnerability gate MEDIUM;
multiple unscoped sources HIGH (Bundler ≤ 2.x); missing checksums,
in-order-only tests LOW.