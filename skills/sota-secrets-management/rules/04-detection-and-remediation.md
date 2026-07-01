# 04 — Detection & Remediation

Scope: secret scanning (gitleaks, trufflehog), pre-commit hooks, CI gates, git history hygiene,
the post-leak runbook (rotate-first), and honeytokens. Read this when setting up scanning, when
running an AUDIT sweep, or the moment a leak is discovered. Pipeline-gate *layering* and
org-wide push protection are owned by sota-devsecops rules/05 §5.2; this file owns tool
configuration and leak **response** (rotation, history cleanup).

## 1. Scanning layers

Defense in depth — each layer catches what the previous missed:

| Layer | Tool/mechanism | Blocks? |
|---|---|---|
| Editor/local | gitleaks pre-commit hook (`gitleaks git --pre-commit --staged`) | Yes — before commit exists |
| Push | server-side pre-receive hook / GitHub push protection | Yes — before history is shared |
| CI | gitleaks/trufflehog job on every PR + full-history scan scheduled weekly | Yes — fail the build |
| Platform | GitHub Advanced Security / GitLab secret detection, partner-program auto-revocation | Detect + sometimes auto-revoke |
| Runtime | honeytokens (§5), backend access-log anomaly alerts (rules/03 §8) | Detect use |

Pre-commit alone is insufficient (devs skip hooks, `--no-verify`); CI alone is too late (the
secret already left the laptop and entered shared history). Run both.

### gitleaks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.x
    hooks:
      - id: gitleaks   # runs `gitleaks git --pre-commit --redact --staged --verbose`
```

```toml
# .gitleaks.toml — extend defaults, add your own token prefixes (rules/01 §1)
[extend]
useDefault = true
[[rules]]
id = "myapp-api-key"
description = "MyApp internal API key"
regex = '''myapp_(sk|pat)_[A-Za-z0-9_\-]{32,}'''
[allowlist]
paths = ['''testdata/fake_keys\.json''']     # narrow, path-based; never allowlist by rule id
```

CI (gitleaks ≥ 8.19 subcommands): `gitleaks git --redact .` on PRs — diff-aware via
`--log-opts="origin/main.."` for speed — plus a scheduled full-history scan without log-opts
(needs a `fetch-depth: 0` checkout) so old commits are rechecked as rules improve. The legacy
`detect`/`protect` spellings still run but are deprecated aliases.

### trufflehog

Complements gitleaks: ~800 detectors **with verification** — it calls the credential's own API
to check liveness, collapsing false positives.

```bash
trufflehog git file://. --only-verified --fail          # CI gate: verified-live secrets only
trufflehog filesystem /path --results=verified,unknown  # audit sweep: include unverifiable
trufflehog docker --image myorg/app:latest              # images: layers, env, files
```

Use `--only-verified` for blocking gates (near-zero false positives); use the broader mode for
audits — an unverifiable secret is still a finding, just triaged manually. Also point trufflehog
at non-git surfaces: S3 buckets, container images, CI logs exports — secrets leak there too.

### Scanner hygiene

- **Allowlists are path- and fingerprint-scoped, reviewed in PRs.** A blanket
  `allowlist regex = '''.*test.*'''` silently exempts `tests/prod_credentials.py` — Medium.
- **`--redact` everywhere**: scanner output goes to CI logs; unredacted output re-leaks the
  secret into a new surface.
- **Inline `# gitleaks:allow` comments require justification** in the same line/commit; audit
  them — they are where real leaks hide (`grep -rn "gitleaks:allow"`).
- Scanners miss: secrets in *binary* files, novel formats without rules, encrypted blobs with
  weak keys, and anything entropy-shaped below thresholds. The manual grep pass in SKILL.md
  AUDIT mode exists for this reason.

### Adopting scanning on a legacy repo (baseline workflow)

Turning on a blocking scanner against a repo with years of history floods the team and gets the
gate disabled within a week. Instead:

1. Full-history scan once; triage every hit (real-and-live / real-but-rotated / false positive).
2. **Rotate all real-and-live findings now** (§3) — the baseline is an incident list, not an
   ignore list.
3. Fingerprint the remainder into a baseline (`gitleaks` `--baseline-path`,
   trufflehog `--exclude-detectors` / fingerprint files) so the gate only fails on *new*
   findings; commit the baseline and review changes to it like code.
4. Burn the baseline down on a schedule; it should shrink monotonically. A growing baseline
   file means the gate is being used as a snooze button — Medium finding.

## 2. CI gates and repo hygiene

- **Blocking, not advisory.** A secret-scan job that's `allow_failure: true` is decoration.
- **Scan the diff on PRs, the full history on schedule**, and **scan built images** before push
  (`trufflehog docker`) — build args and COPY'd `.env` files surface here.
- **`.gitignore` preloads** in every repo template: `.env`, `.env.*`, `!.env.example`, `*.pem`,
  `*.key`, `*.p12`, `*.pfx`, `*.jks`, `id_rsa*`, `*.kubeconfig`, `credentials.json`,
  `terraform.tfstate*`, `.netrc`. gitignore is a guardrail, not a control — files added with
  `git add -f` still need the scanner to catch them.
- **GitHub push protection** (Settings → Code security) on for all repos/orgs; it blocks pushes
  containing known token patterns server-side, including from devs without hooks. Coverage
  expands continuously (through H1 2026: dozens of new provider detectors, more patterns
  push-protection-enabled by default, validity checks, and owner/expiry metadata on alerts) —
  treat alerts marked *active* by validity checks as §3 incidents, not backlog.
- **Fork PR safety:** secret-bearing workflows never run on `pull_request` from forks; audit
  any `pull_request_target` usage that checks out PR code (classic exfil vector — High).

## 3. Post-leak runbook: rotate first

A secret that touched a commit, log, ticket, chat, or paste is **compromised** — period.
Scrapers index public commits in well under a minute; "we force-pushed quickly" is not
mitigation; private repos only shrink, not eliminate, the audience. Execute in this order:

1. **Rotate/revoke immediately — before any cleanup.** Issue the replacement, deploy consumers,
   revoke the leaked value (rules/01 §3). If revocation breaks things, that's an availability
   bug you fix *after* killing the credential — a live leaked key is worse than downtime.
   For cloud keys also check for attacker persistence: new keys/users/roles created by the
   leaked identity, modified trust policies.
2. **Assess blast radius:** backend access logs (CloudTrail etc.) for use of the leaked
   credential since the leak timestamp — not since discovery. Unexplained use → escalate to
   incident response; this is now a breach investigation, not a hygiene task.
3. **Purge from history (§4)** — only after rotation. Purging an unrotated secret just
   advertises where it was.
4. **Close the hole:** which layer (§1) should have caught it? Add the missing rule/hook/gate.
   Add the leaked secret's *shape* to scanner config so recurrence is caught.
5. **Record it:** timeline, blast radius, fix. Leak frequency per quarter is the KPI for your
   scanning posture.

Severity-of-response calibration:

| Leaked | Response tempo |
|---|---|
| Cloud root/admin key, signing key, KMS-adjacent creds | Drop everything; rotate within the hour; full IR engagement |
| Prod service credential (DB, API key with write scope) | Same day; check access logs before and after rotation |
| Read-only / non-prod / sandbox credential | Within 24h; still rotate — non-prod creds pivot into prod via reused patterns and shared infra |
| Honeytoken | No rotation needed; treat as breach signal for the planted surface (§5) |

**Leaks outside git** follow the same runbook with a different purge step: secrets pasted into
CI logs (purge/expire the log retention), chat (delete + rotate; assume exported), issue
trackers, error trackers (scrub events via API), AI tool transcripts, and pastebins (report for
takedown). The rotate-first rule is identical — purging is best-effort everywhere; rotation is
the only reliable mitigation.

## 4. Git history hygiene

Removing a secret from HEAD does nothing — `git log -p`, every clone, and every fork still hold
it. To actually purge:

```bash
# Preferred: git-filter-repo (BFG is the older alternative)
pip install git-filter-repo
# replacements.txt:  LEAKED_VALUE==>REMOVED
git filter-repo --replace-text replacements.txt          # rewrites all history
# or drop whole files everywhere:
git filter-repo --invert-paths --path config/secrets.yml
git push --force --all && git push --force --tags
```

Then, in order of how often it's forgotten:

- **Every collaborator re-clones.** Old clones still contain the secret and will reintroduce
  the old history on a careless push (protect branches against non-fast-forward from stale
  clones).
- **Forks keep the old commits** — you cannot rewrite someone else's fork. On GitHub,
  dangling/forked commits remain fetchable by SHA even after rewrite; contact support to
  garbage-collect cached views, and **treat the value as permanently public regardless** —
  which is why rotation came first.
- **PRs, issues, CI logs, artifacts, package registries** may quote the secret — search and
  scrub those surfaces too (`gh api` search, CI log retention purge, yank published packages
  that embed it).
- Re-run the full-history scan to confirm zero hits before closing the incident.

```text
# BAD incident response (common): delete the line, normal commit, move on
#   -> secret still in history, still valid, now flagged as interesting
# GOOD: rotate -> verify no abuse -> filter-repo -> force-push -> re-clone fleet -> rescan
```

### Posture metrics

Track quarterly; these tell you whether the program works:

- **Time-to-detect** (commit → alert) and **time-to-rotate** (alert → leaked cred dead) per
  incident; the second number is the one that matters and should be hours, not days.
- **New verified leaks per quarter** (trend down), **baseline size** (trend down),
  **% repos with pre-commit + CI gate + push protection** (trend to 100%).
- **Honeytoken alert drill freshness** — last test-fire date per planted surface.

## 5. Honeytokens

Plant credentials that have **no legitimate use** and alarm on *any* use — they detect breaches
of the surfaces scanners can't watch (stolen laptops, leaked backups, insider snooping, supply
chain).

- **Sources:** Canarytokens (free: AWS keys, fake DB creds, files), Thinkst Canary, GitGuardian
  honeytoken, or roll your own — a real but permissionless AWS key whose *use* (CloudTrail
  `GetCallerIdentity` from an unknown IP) triggers an alert.
- **Where to plant:** private repos (a fake `.env` in an internal repo detects repo compromise),
  CI variable groups, wikis/Notion, S3 backup buckets, developer-laptop `~/.aws/credentials`
  (extra profile), container images, secret-manager entries no app reads (access-log alert).
- **Make them indistinguishable** from real credentials in naming and placement; document them
  in a register *outside* the planted surfaces so responders can tell drill from breach.
- **Alert = assume breach of that surface.** Triage where the token was planted, not the token
  itself (it has no privileges).
- AUDIT note: before reporting a "live AWS key" finding, consider it may be a honeytoken —
  and never *verify* candidate keys by using them against the provider without explicit
  permission; usage may trip someone's alarm or constitute unauthorized access. Judge liveness
  from context (key shape, age, references), or hand to the owner to check.

## 6. Audit sweep quick reference

Condensed from SKILL.md AUDIT mode — the grep set when tools aren't available:

```bash
# Known prefixes & key blocks
grep -rInE '(AKIA|ASIA)[A-Z0-9]{16}|ghp_[A-Za-z0-9]{36}|github_pat_|gho_|xox[bpars]-|sk_live_|rk_live_|sk-[A-Za-z0-9]{20,}|AIza[A-Za-z0-9_\-]{35}|glpat-|npm_[A-Za-z0-9]{36}|dop_v1_|shpat_' .
grep -rIl -- '-----BEGIN \(RSA \|EC \|OPENSSH \|\)PRIVATE KEY-----' .
# Assignments & connection strings
grep -rInE '(password|passwd|pwd|secret|token|api[_-]?key)\s*[:=]\s*["'"'"'][^"'"'"']{6,}' --include='*.{py,js,ts,go,rb,java,yml,yaml,json,tf,sh,env,cfg,ini,properties}' .
grep -rInE '[a-z+]+://[^/:@[:space:]]+:[^@[:space:]]+@' .
# Dangerous tracked files
git ls-files | grep -E '\.env($|\.)|\.pem$|\.key$|\.p12$|\.pfx$|\.jks$|id_rsa|credentials\.json|terraform\.tfstate|kubeconfig|\.npmrc$|\.netrc$'
# History (HEAD-clean but leaked)
git log --all -p --unified=0 | grep -E '^(\+).*(AKIA|ghp_|PRIVATE KEY|sk_live_)' | head -50
# Scanner suppressions hiding bodies
grep -rn 'gitleaks:allow\|nosec\|trufflehog:ignore' .
```

Triage every hit per SKILL.md severity table; redact values in the report (prefix + length).

## Audit checklist

- [ ] gitleaks (or equivalent) pre-commit hook in `.pre-commit-config.yaml` and documented in
      dev setup; custom rules cover internal token prefixes.
- [ ] Blocking CI secret-scan on every PR; scheduled full-history scan; built images scanned;
      scanner output redacted.
- [ ] GitHub push protection / server-side pre-receive scanning enabled org-wide.
- [ ] Allowlists narrow (path/fingerprint), justified, and reviewed; all inline
      `gitleaks:allow` suppressions audited.
- [ ] `.gitignore` covers `.env*`, key/cert files, tfstate, kubeconfig, `.netrc`; no such files
      tracked (`git ls-files` check).
- [ ] Fork PRs receive no secrets; `pull_request_target` does not execute fork code.
- [ ] Leak runbook exists, is current, and orders rotate → assess (logs since leak time) →
      purge → harden → record; revocation paths tested per credential class.
- [ ] Past incidents: history actually rewritten (filter-repo + force-push + re-clone), forks/
      PR quotes/CI logs scrubbed, full-history rescan clean, and the leaked values rotated.
- [ ] Legacy-repo adoption used a triaged baseline (live findings rotated first); baseline file
      reviewed like code and shrinking over time.
- [ ] Non-git leak surfaces (CI logs, chat, issue/error trackers) covered by the runbook with
      retention/scrub procedures.
- [ ] Honeytokens planted in at least repos + CI + one backup surface; register maintained
      out-of-band; alerts route to incident response and have been test-fired.
- [ ] No audit practice involves invoking discovered credentials against providers without
      explicit owner permission.
