# 10 — Declared but not Reached — the inert-dependency sweep

Scope: dependencies, modules and plugins that are **declared** but never **reached**.
Split out of `rules/03` at v1.36.0 — same content in its own file, with the old
3.9.N subsection numbers becoming §1–§7.

`rules/03` §3.6 asks whether what you ship is *vulnerable*. It never asks whether a
declared dependency is **reached at all**. An unreached dependency is pure liability:
install-time execution surface (`rules/03` §3.4), a lockfile entry to upgrade forever,
license obligations, build time, and a CVE queue for code that never runs. It is also the
cheapest finding in an audit — the fix is a deletion.

Run it as its own pass over **direct dependencies, registered modules, and plugins**. The
BUILD-side gate on *adding* a dependency lives in the language skills (`sota-golang`
rules/05 §8, `sota-javascript-typescript` rules/05); this is the sweep for what already
landed.

Severity: an unreached dependency is **Low** on its own — nothing exploitable, only debt.
Rate it **Medium** when it runs install hooks (`rules/03` §3.4), ships into the runtime
artifact, or carries an open advisory: that is exploit surface carried for zero function.

## 1. Reachability, not import presence

Trace from a **real entrypoint** — `main`, the route table, the scheduler/cron
registration, the module or plugin registry, the DI container wiring — to the dependency's
API. An import statement is not reachability; it is the thing that makes an inert
dependency look alive to every static tool.

Three traps:

- **A reference on a path that cannot execute.** A `switch`/`match` arm for a type the live
  decoder cannot emit, a handler registered for an event no producer sends, an adapter
  selected by a config value nothing sets. The symbol is genuinely referenced, so tools and
  greps mark the dependency used — but the branch is unreachable. One step earlier than
  this is `sota-code-security` rules/14 §4 (a gate whose trigger never fires); the same
  two-axis check applies — *has this path ever executed*, not *does it exist*.
- **Side-effect-only imports.** `import _ "…"` for a driver, a decorator that registers
  into a table, a plugin discovered by entry point. Legitimate — but confirm something
  *reads* that table, or you have a registration nobody consumes.
- **The reverse trap — dynamic loading.** Reflection, service loaders, `importlib`,
  `require` by string, Rails autoload, DI-by-convention, plugin manifests. Here a
  dependency with **no static reference is still reached**, so the tools below produce
  false *positives*. Search config, manifests, and IaC for the package/class name as a
  **string**, not only the code for a symbol.

## 2. Tools, each with its blind spot

No tool's silence is proof (§3). Use one to generate candidates, then prove each one.
Verify the tool's current name and maintenance before you trust it (`sota/rules/01` §3) —
two of the projects below have been renamed under their old URLs.

| Ecosystem | Tool | Blind spot to state when you cite it |
|---|---|---|
| Go | `go mod why -m <module>` prints `(main module does not need module …)`; `go mod tidy` + `git diff --exit-code` in CI (§8 of `sota-golang` rules/05) | `why` queries the graph of `go list all`, which **includes tests of reachable packages**: a module needed only by your *dependencies'* tests reads as reached until you pass `-vendor`, and one needed only by your *own* tests reads as reached either way |
| JS/TS | `knip --include dependencies` (`sota-javascript-typescript` rules/07) | documents its own false positives: unresolved dynamic specifiers (`import(path.join(dir, x))`), config files a plugin's dependency-finder doesn't parse, and **entry/project globs that miss files** — "dependencies imported in unused files are reported as unused dependencies", so triage unused *files* first |
| Python | `deptry .` — DEP002 unused, DEP003 transitive-but-imported, DEP005 stdlib shadowed | static import analysis: entry-point/plugin packages and `importlib` loads read as unused |
| Rust | `cargo machete` (stable) or `cargo +nightly udeps` | machete is deliberately imprecise — false positives for deps used only from `build.rs`-generated code and for crates whose import name differs from the package name (`--with-metadata` fixes the latter). udeps needs **nightly** and documents false *negatives*: deps also used by std or by your own deps go undetected |
| JVM | `mvn dependency:analyze` (`analyze-only` inside the lifecycle) with `failOnWarning` — default is `false`, so it is advisory until you set it | its FAQ is explicit: "dependency analysis is done at bytecode level: anything that doesn't get into bytecode isn't detected" — inlined constants, source-retention annotations, javadoc links. "If the only use of a dependency consists of such undetected constructs, the dependency is analyzed as unused." Override per-dep with `usedDependencies` |
| PHP | `composer-unused` (`vendor/bin/composer-unused`; needs `composer install` first) | static; container- and config-string wiring is invisible |
| .NET | `ReferenceTrimmer` (modest adoption — treat as a candidate generator only): MSBuild task + Roslyn analyzer over the compiler's `GetUsedAssemblyReferences` | it skips SDK/target-framework references, transitives, and packages carrying build files; in symbol-analysis mode "references used only in XML documentation comments will be reported as removable" |
| Ruby | **no established tool** — the candidates are single-maintainer and low-adoption | dynamic `require`, autoload, and monkey-patching defeat static analysis by construction; go straight to §3 |

## 3. Proof by construction — delete it and build

A grep is not proof, and neither is a tool's silence. The finding is not "X looks unused";
it is **"X was removed and the real build, lint/vet, and full test suite still passed."**

1. **Copy the repo to a scratch directory.** The audit is read-only (`sota/rules/01` §4) —
   never mutate the tree under audit.
2. **Remove the declaration and regenerate the lockfile.** Manifest edit alone leaves the
   package resolvable.
3. **Run what CI runs** — build + vet/lint + the full suite, not a subset.
4. **Report exact commands, exit codes, and before/after counts** — `go mod graph | wc -l`,
   the lockfile's package count, the resolved module total.
5. **If it still builds, that is the finding.** If it fails, you have a *reached*
   dependency and the compiler just named the call site for you — record that as the
   reachability evidence and close the candidate.

Two traps that make a green run lie (same shape as `sota-code-security` rules/12 §1, where the mutation is a
no-op'd control rather than a removed package):

- **The deletion did not take.** A vendored copy still on disk, a lockfile not regenerated,
  a workspace sibling still declaring it, a cached build layer, a stale `target/`
  or `node_modules`. **Assert the absence has runtime effect** — the resolver errors, the
  import fails — before trusting green.
- **The suite never exercised the path.** A dependency reached only from an integration or
  e2e job you did not run reads as removable. **State which suites ran**: a build-only
  proof is a bounded claim ("removable without breaking `go build` and `go test ./...`"),
  not "unused".

## 4. Leverage ratio — what you use vs what you inherit

For each *live* dependency, count the API surface you actually call against the transitive
modules it pulls in (`go mod graph`, `cargo tree`, `npm ls --all`, the lockfile). **Fewer
than ~5 symbols used while inheriting more than ~10 modules** is a replace-in-house
candidate — flag it, with both numbers.

The ratio is a trigger for the decision in §5, never the decision itself. A single-call
dependency that implements something on the do-not-reimplement list stays.

## 5. Upstream health — a primary source fetched this session

Operating principle 0 applies with full force here: "actively maintained" recalled from
training data is exactly the claim that rots. Fetch it, and **report the dates rather than
an adjective** — "last push 2026-04-27" is a fact; "actively maintained" is an opinion with
an expiry date.

```bash
# archived/disabled flags, push and update timestamps, license
gh api repos/<owner>/<repo> \
  --jq '{full_name, archived, disabled, pushed_at, updated_at, license: .license.spdx_id}'

# contributor count: rel="last" page number == contributors, at per_page=1
gh api "repos/<owner>/<repo>/contributors?per_page=1" --include | grep -i '^link:'
```

- **Read `full_name` back — `gh api` follows renames silently.** Verified 2026-07-30:
  `repos/fpgmaas/deptry` answers as `osprey-oss/deptry`, and
  `repos/icanhazstring/composer-unused` as `composer-unused/composer-unused`. A 200 under
  the name in your manifest is **not** evidence the project is still where you think it is.
  A 404 is a different finding (deleted, private, or renamed *and* the redirect dropped).
- **`archived: true` is the easy case.** The common one is a never-archived repo that
  nobody maintains — which is why the dates and the contributor count matter more than the
  flag. Read the README and repo description for an explicit unmaintained-or-successor
  notice.
- **Neither timestamp is a release-cadence signal.** `pushed_at` tracks push activity and
  `updated_at` also moves on metadata-only changes (description, wiki). A repo with a
  recent `pushed_at` and no release in two years is still drifting — read the release feed
  as well, and say which of the three you are citing.
- Non-GitHub hosts: the registry's own metadata plus the project's release feed. For
  dependencies you rely on heavily, OpenSSF Scorecard (`rules/03` §3.4).

## 6. Classify every finding into exactly one bucket

- **A. DELETE** — unreached, with the §3 proof attached (commands, exit codes,
  before/after counts). Effort: trivial.
- **B. REPLACE IN-HOUSE** — reached, but small, well-specified, non-security-critical, and
  a poor leverage ratio. Give a line-count estimate *and* name the owner afterwards: the
  real cost is maintaining it forever, not writing it once.
- **C. KEEP** — healthy, or too complex / too security-critical to reimplement. **Never
  recommend an in-house implementation of:** crypto primitives or protocols, TLS,
  JWT/JOSE, CORS, session cookies, WebAuthn/FIDO2, password hashing, or YAML/XML/PDF/
  archive parsing — *and* **never of an algorithm whose output is persisted and must stay
  comparable with stored data** (fuzzy or locality-sensitive hashes, similarity digests,
  tokenizers, ID/slug derivations). A reimplementation that is merely *equivalent* still
  invalidates every stored value it has to compare against, and the failure is silent —
  comparisons keep returning answers, just wrong ones (`sota-code-security` rules/10). The
  library-wide stance is in `sota/SKILL.md`: use a vetted library, don't roll your own.

  **For protocols the line is which side you are on** — added 2026-07-31 after this
  clause was found genuinely ambiguous on a request signer. Primitives are out
  unconditionally. A *protocol* is out whenever **this** system is the **validating**
  side: there a canonicalisation, parsing or comparison bug fails **permissively and
  silently** — it accepts what it should reject, and nothing errors. That is the
  `sota-code-security` rules/10 family and it is the reason the prohibition exists. Composing stdlib
  primitives per a published spec to produce something a **remote authority validates**
  is a different class: a wrong signature is rejected on the first request, loudly. If
  you take that path, **state which side you are on**, pin the spec version you
  implemented, and test against the publisher's own vectors where they exist. When you
  cannot say which side fails first, treat it as validating and keep the library.
- **D. UNMAINTAINED but must keep** — name the maintained fork or successor and the date
  you checked it. If none exists, say so; the migration is a roadmap item with an owner,
  not a one-line fix.

## 7. "Unused" is an absence claim

It carries the heavier burden of router principle 3 and `sota/rules/03` §2: before writing
*unused*, search twice by **different methods** and state both. A static tool plus the
§3 deletion proof is a valid pair. Two greps are not a pair — and given §1's
dynamic-loading trap, a code-only search is structurally incapable of settling it.

## Audit checklist

- [ ] **Inert-dependency sweep run**: every direct dependency, registered module, and plugin traced to a real entrypoint — not just to an import — with the impossible-path and dynamic-loading traps checked in both directions (§1)
- [ ] Each "unreached" claim **proven by deletion** in a scratch copy: real build + lint/vet + full suite, with commands, exit codes, before/after transitive counts, and which suites ran — and the deletion asserted to have taken effect (§3)
- [ ] Leverage ratio computed for live deps (symbols called vs transitive modules inherited); <5-symbols/>10-modules candidates flagged with both numbers (§4)
- [ ] Upstream health fetched **this session** from a primary source (`gh api repos/<o>/<r>` → `archived`, `pushed_at`, contributor count; `full_name` read back for silent renames), reported as dates not adjectives (§5)
- [ ] Every finding classified DELETE / REPLACE IN-HOUSE / KEEP / UNMAINTAINED-but-keep, with the successor named for D and nothing on the do-not-reimplement list proposed for B (§6)
- [ ] Every "unused" verdict treated as an **absence claim** — two independent methods, the search actually run stated, and no verdict resting on grep alone (§7)
