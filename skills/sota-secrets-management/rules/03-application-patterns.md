# 03 — Application Patterns

Scope: how application code obtains, holds, and uses secrets — config layering, runtime
injection, caching/TTL, the no-leak surfaces (code, VCS, logs, errors, URLs, argv, dumps),
per-environment separation, least-privilege scoping, and audit logging. Read this when writing
or reviewing any code path that touches a credential.

## 1. Config layering

Separate **config** (non-secret: hostnames, flags, pool sizes — committable) from **secrets**
(never committable). One loader, explicit precedence, fail-fast:

```
defaults (in code) < config file (in repo) < secret backend / mounted files < env vars (overrides)
```

Rules:

- **Secrets enter only through the secret layer** (mounted file, secret-manager fetch, env var
  injected by the platform). The committed config file may contain the *reference*
  (`db_password_secret: projects/p/secrets/db-pw`) — never the value.
- **Validate at startup, fail fast and loud — but redacted.** Missing/blank secret → exit
  non-zero with the secret's *name*, never its partial value. Don't limp along to a 3am
  connection error.
- **No "default secrets."** A fallback like `os.getenv("JWT_SECRET", "dev-secret")` ships the
  dev secret to prod the day the env var is mistyped — High finding. Defaults are for
  non-secrets only.
- **Support `*_FILE` indirection** (e.g., `DB_PASSWORD_FILE=/run/secrets/db`) so the same image
  runs on env-var PaaS and file-mount platforms.

```python
# BAD — silent fallback, secret in code, mixed into committable config
JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-dev-key")

# GOOD — required, file-or-env, redacting wrapper, fail-fast
def required_secret(name: str) -> SecretStr:
    if path := os.getenv(f"{name}_FILE"):
        return SecretStr(Path(path).read_text().strip())
    if val := os.getenv(name):
        return SecretStr(val)
    raise SystemExit(f"FATAL: secret {name} not provided")  # name only, never value
JWT_SECRET = required_secret("JWT_SECRET")
```

## 2. Never in code, VCS, logs, errors, or dumps

**Code/VCS:** no literal secret anywhere in the repo — source, tests, fixtures, comments,
example configs, notebooks, lockfiles (`.npmrc` lines in lockfile diffs), or git history.
"It's a private repo" changes nothing: contractors, CI runners, laptop theft, repo-visibility
flips, and AI coding tools all read private repos. Tests use generated-at-runtime fakes or
clearly impossible placeholders (`test-key-000…`); integration tests pull real (dev-scoped)
creds from the same secret layer as the app.

**Logs:** the most common real-world leak. Enforce in layers:

1. **Redacting types** (rules/02 §7): `SecretStr`, `secrecy`, custom wrappers — accidental
   `log.info(f"cfg={config}")` prints `[REDACTED]`.
2. **Logger-level scrubbing:** a processor/filter that masks known keys (`password`, `token`,
   `secret`, `authorization`, `cookie`, `set-cookie`, `x-api-key`) and known value shapes
   (your token prefixes, `Bearer [A-Za-z0-9_\-\.]+`, `AKIA\w{16}`).
3. **Never log:** full request/response headers, full connection strings/URLs (strip userinfo:
   `postgres://user:****@host/db`), decoded JWT payloads with embedded secrets, full env, full
   config objects.
4. **Never persist raw** — the tier the three above cannot reach, for text whose producer
   you do not control (§2.1).


```python
# BAD — leaks the whole DSN (with password) on every connection failure
logger.error("db connect failed: %s", dsn)
# GOOD
logger.error("db connect failed host=%s db=%s user=%s", host, dbname, user)
```

```python
# GOOD — structlog/logging processor as a backstop for everything the above misses
SECRET_KEYS = {"password", "passwd", "secret", "token", "api_key", "authorization",
               "cookie", "set-cookie", "x-api-key", "private_key", "client_secret"}
SECRET_SHAPES = re.compile(r"(myapp_(sk|pat)_\S+|AKIA\w{16}|Bearer\s+[\w\-.~+/]+=*|eyJ[\w-]{10,}\.[\w-]+\.[\w-]+)")
def scrub(_, __, event):
    for k in list(event):
        if k.lower() in SECRET_KEYS:
            event[k] = "[REDACTED]"
        elif isinstance(event[k], str):
            event[k] = SECRET_SHAPES.sub("[REDACTED]", event[k])
    return event
```

The processor is the *backstop*, not the plan — redacting types and disciplined log statements
come first; the processor catches the third-party library that logs a request object.

### 2.1 Text you did not produce: persist a digest and a skeleton, never the datum

Tiers 1–3 assume you own the producer. You cannot wrap someone else's bytes in a
`SecretStr`, so when the thing being stored is **arbitrary text from a source you do not
control** — a swept corpus, shell history, a crash dump, a scraped page, an agent
transcript (`rules/04` §7), a diff from an untrusted branch — the guidance silently
degrades to tier 2 alone. **Tier 2 is an enumeration, and enumerations lose.**

Field-reported, with the run that killed it: a shape-redaction fix reusing an existing
`sk-…`/`AKIA…`/`ghp_…` matcher was **defeated by its own regression test on the first
run**, by a GitLab PAT (`glpat-…`) and a Slack webhook URL. Five weeks later the same
corpus acquired four more live keys, one of them a **bare 64-character hex string with no
prefix at all** — a value no prefix rule can ever match, and one that a generic
"long random-looking string" rule cannot separate from a hash, a UUID or a minified bundle.

So do not persist the datum. Persist what diagnosis actually needs:

```python
_MAX_LINE = 160
KEEP = set(" \t|&;()<>{}[]$\"'`\\=/-.:@#*?!~+,")   # this grammar's punctuation, nothing else

def safe_line(line: str) -> dict[str, str]:
    """The only representation of a swept line this tool ever writes down."""
    return {
        "sha256": hashlib.sha256(line.encode("utf-8", "replace")).hexdigest()[:16],
        "length": str(len(line)),
        "shape": "".join(c if c in KEEP else "x" for c in line[:_MAX_LINE]),
    }
```

The digest correlates the same line across two runs and lets a human grep their *own*
source for it; the length bounds complexity; the shape preserves the structure a diagnosis
needs while every run of payload characters collapses to `x`. **It is leak-proof by
construction rather than by list** — it never has to know what a secret looks like, so no
unenumerated format defeats it. That is the same reasoning the library applies to
structural controls elsewhere, moved one step earlier: to the decision to persist at all.

Scope it honestly, in the rule and in review:

- This is for data kept to **diagnose or correlate**, never for data you must read back. If
  you need the value, you need a secret store, not this.
- **The shape channel is a real, if narrow, disclosure.** For shell it is punctuation; for
  another grammar pick the analogous skeleton and *say what it keeps*. Do not describe it
  as zero-leak.
- Truncation is a second, independent bound — set it deliberately, not by accident.
- **stdout is a persistence surface too.** A console that prints what the file redacts is
  the same leak with a worse retention policy.

**Error messages & exceptions:** exceptions traverse trust boundaries — API error bodies, error
trackers, support tickets. Never embed a credential in an exception message
(`raise AuthError(f"key {api_key} rejected")` — High). Configure Sentry/Rollbar/etc. with
`send_default_pii=False`, server-side and client-side data scrubbers for your secret key names
and token prefixes; review breadcrumbs (HTTP breadcrumbs can capture auth headers).

**Crash dumps / telemetry:** error handlers that serialize "the request" or "the config" for
diagnostics will capture `Authorization` headers and secret fields. Allowlist what diagnostics
capture; never snapshot full env or full headers. Disable verbose framework debug pages in prod
(Django DEBUG, Flask debugger, Rails verbose errors, Spring Boot `/actuator/env` &
`/actuator/heapdump` — all dump config/env to the caller; exposed actuator is High).

## 3. Never in URLs or CLI arguments

**URLs/query strings** (`?api_key=…`, `?token=…`, creds in URL userinfo): persisted by access
logs on every hop (LB, CDN, proxy, app), browser history, `Referer` headers, and link sharing.
Use the `Authorization` header. Exception: short-lived (≤1h) presigned/signed URLs designed for
it — and even those don't belong in long-term logs. A long-lived API key as a query param is
High.

**CLI args:** `ps`-visible to every user on the host, captured in shell history, audit logs
(auditd execve), and CI logs.

```bash
# BAD — password visible in `ps aux`, shell history, CI log
mysql -u app -pS3cr3t! prod
curl -H "Authorization: Bearer $TOKEN" https://api...   # OK-ish: env expansion not in ps,
                                                        # but lands in shell history if literal
# GOOD — read from file/env/stdin
mysql --defaults-extra-file=/run/secrets/my.cnf prod
curl -H @/run/secrets/auth_header https://api...
PGPASSWORD unset; use ~/.pgpass (0600) or peer/IAM auth
```

When *writing* CLIs: accept secrets via env var, `--token-file`, or stdin prompt — never as a
positional/flag value; if you must accept a flag, document the `ps` exposure and prefer
`--token-file`. When *invoking* subprocesses from code, pass secrets via env (explicitly
constructed, not inherited wholesale) or files — never interpolated into the command string
(also an injection risk).

## 4. Runtime injection, caching, and TTLs

**Inject at runtime, not build time.** Images/artifacts are environment-agnostic and
secret-free; the platform supplies values at start (rules/02 §5–6). Grep CI for
`docker build --build-arg.*SECRET` — build args persist in image history (Critical in pushed
images).

**Fetching from a secret manager — cache deliberately:**

- **Cache in memory with a TTL** (5–15 min typical): per-request fetches add latency, cost, and
  a hard runtime dependency on the store; no caching means an outage of the secret manager is an
  outage of you.
- **Serve stale on refresh failure** (with alerting) rather than crashing a running app; only
  startup requires a successful fetch.
- **React to rotation:** TTL expiry naturally picks up new versions; for file mounts, re-read on
  auth failure or watch the file (k8s updates mounted Secrets in-place within ~1m). The
  **retry-on-auth-failure pattern** makes rotation seamless: on 401/auth-failed, force-refresh
  the cached secret once and retry before erroring.
- Official caching helpers exist — AWS Secrets Manager caching libraries, Vault Agent template
  cache — prefer them to hand-rolled caches.

```python
# GOOD — TTL cache + forced refresh on auth failure
class SecretCache:
    def __init__(self, fetch, ttl=300):
        self._fetch, self._ttl, self._val, self._at = fetch, ttl, None, 0.0
    def get(self, force=False):
        if force or self._val is None or time.monotonic() - self._at > self._ttl:
            try:
                self._val, self._at = self._fetch(), time.monotonic()
            except Exception:
                if self._val is None: raise          # startup: fail fast
                log.warning("secret refresh failed; serving cached")  # runtime: stale + alert
        return self._val

def call_api():
    r = client.call(token=cache.get())
    if r.status == 401:
        r = client.call(token=cache.get(force=True))  # rotation happened mid-TTL
    return r
```

## 5. Client-side code has no secrets

Anything shipped to a browser, mobile app, or desktop client is **public**: JS bundles, source
maps, APKs/IPAs (trivially decompiled), Electron asar archives. Framework env prefixes that
inline values into bundles are the standard footgun:

```bash
# BAD — *_PUBLIC_ prefixes inline the value into the shipped bundle
NEXT_PUBLIC_STRIPE_SECRET_KEY=sk_live_...     # Critical: secret key in browser JS
VITE_OPENAI_API_KEY=sk-...                    # Critical: anyone can read the bundle
# GOOD — secret stays server-side; client calls your backend, which holds the key
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_... # publishable keys are designed to be public
```

- Rule of thumb: if removing it from the client breaks security, it cannot live in the client.
  Proxy third-party APIs through your backend (which also lets you rate-limit and attribute).
- Mobile: API keys in `strings.xml`/`Info.plist`/compiled constants are extracted in minutes;
  obfuscation is not protection. Use backend proxying, per-user short-lived tokens issued after
  auth, and attestation (Play Integrity / App Attest) where abuse matters.
- Keys that are *designed* public (Stripe publishable, Firebase config, Maps browser keys) are
  fine in clients but must be restriction-locked at the vendor (referrer/bundle-id/API
  restrictions) — an unrestricted "public" key is a Medium finding.
- AUDIT: grep built artifacts, not just source — `grep -rE 'sk_live_|AKIA' dist/ build/
  *.map` — and check source maps published to prod.

## 6. Per-environment separation

- **One secret per consumer per environment.** dev/staging/prod never share a value; a leak in
  staging must not touch prod. Shared values are a High finding for prod, Medium otherwise.
- **Namespacing enforces it:** separate cloud accounts/projects per env (best), or per-env
  paths/prefixes (`secret/prod/...` vs `secret/dev/...`) with IAM/policies that make prod
  unreadable from non-prod principals — including developers' day-to-day identities.
- **Non-prod gets non-prod scopes:** Stripe test keys (`sk_test_`), sandbox tenants, dev-scoped
  DB users. If a vendor offers no sandbox, treat the non-prod key as prod-sensitive.
- **CI:** prod-deploy credentials only in protected contexts (GitHub environments with
  reviewers, protected branches); PR builds from forks get *no* secrets
  (`pull_request_target` exfiltration is a classic — never check out and execute fork code in a
  secret-bearing context).

## 7. Least-privilege scoping of tokens

Every credential answers: who uses it, for which actions, on which resources, until when?

- **Scope down at issuance:** GitHub fine-grained PATs (specific repos + permissions) over
  classic PATs; cloud IAM policies listing actions+resources, not `*`; DB users with table-level
  grants, not superuser; API keys with vendor-side restrictions (Stripe restricted keys, Google
  API key referrer/IP/API restrictions).
- **One credential per consumer.** A key shared by three services cannot be rotated, scoped, or
  attributed independently; its blast radius is the union. Sharing is a Medium finding.
- **Read paths get read-only creds.** The reporting service does not reuse the app's read-write
  DB user.
- AUDIT: flag `*:*` IAM attached to app roles (High in prod), org-wide classic PATs in CI
  (High), DB superuser in an app connection string (High), unrestricted vendor keys (Medium).

## 8. Audit logging of secret access

- **Backend side:** enable the store's access logs (CloudTrail data events for Secrets Manager,
  GCP Data Access logs, Key Vault diagnostics, Vault audit devices) and ship them off-system.
  Alert on: reads by unexpected principals, first-time principal/secret pairs, reads from new
  geographies, spikes, and reads of honeytokens (rules/04 §5).
- **App side:** log secret *usage events* — "rotated DB cred picked up," "token refresh failed,"
  "auth failure forced refresh" — with secret *names*, never values. These logs are how you
  verify a rotation completed (rules/01 §3 step 3).
- **Attribution requires per-consumer creds** (§7) — a shared key makes every audit log entry
  ambiguous.

## Audit checklist

- [ ] Single config loader with explicit precedence; secrets only via secret layer; references
      not values in committed config; startup fails fast (redacted) on missing secrets; no
      default/fallback secret values in code.
- [ ] No literal secrets in source, tests, fixtures, comments, examples, or git history
      (history scan done — rules/04).
- [ ] Redacting wrapper types in use; logger-level scrubbing for secret key names and token
      shapes; connection strings/URLs logged without userinfo; no full-header, full-env, or
      full-config logging.
- [ ] **Text whose producer you do not control is never persisted raw (§2.1)** — a swept
      corpus, shell history, crash dump, scraped page or agent transcript is stored as a
      digest plus a structural skeleton, with the shape channel's disclosure stated and
      stdout covered by the same rule; shape/prefix redaction alone is not accepted as the
      control, because it is an enumeration
- [ ] Exceptions and error-tracker payloads carry no secret values; PII/data scrubbers
      configured; debug pages and Spring actuator env/heapdump endpoints disabled or
      authenticated in prod.
- [ ] No secrets in URLs/query strings (except short-lived signed URLs); none passed as CLI
      arguments (in code, scripts, CI, and docs); subprocesses get explicit env/files, not
      inherited environments or interpolated command strings.
- [ ] No build-time secret injection (`--build-arg`, Dockerfile ENV); runtime injection only.
- [ ] No secrets in client-shipped code: bundles, source maps, and mobile binaries scanned;
      `NEXT_PUBLIC_`/`VITE_`/`REACT_APP_` vars contain only public values; designed-public keys
      vendor-restricted; third-party APIs proxied server-side.
- [ ] Secret-manager fetches cached with TTL, stale-on-error with alerting, forced refresh on
      auth failure; rotation verified end-to-end without restarts.
- [ ] Per-environment secrets fully separated (accounts/paths + IAM); prod unreadable from
      non-prod; vendor test keys in non-prod; fork PRs receive no secrets; prod deploys gated.
- [ ] Tokens scoped least-privilege (actions, resources, expiry); one credential per consumer;
      read-only creds on read paths; no wildcard IAM/superuser DB users on app credentials.
- [ ] Backend access logs enabled, shipped, and alerted; app logs usage events by name only;
      rotation completion verifiable from logs.
