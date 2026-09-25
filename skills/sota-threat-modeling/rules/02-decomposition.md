# 02 — System Decomposition: DFDs, Trust Boundaries, and Extraction from Code

Decomposition quality caps threat-model quality: you cannot enumerate threats
against elements you never drew. This file covers (A) building the model and
(B) extracting it from an existing codebase.

## A. Building the model

### 1. DFD element vocabulary

Use exactly four element types plus boundaries — more notation adds cost, not
threats:

| Element | Mermaid convention | Examples |
|---|---|---|
| External entity | `E[Name]` rectangle | user browser, third-party API, attacker, payment provider |
| Process | `P(Name)` rounded | API service, worker, lambda, cron job, LLM agent |
| Data store | `D[(Name)]` cylinder | Postgres, S3 bucket, Redis, browser localStorage, log sink |
| Data flow | labeled arrow | `-->|order JSON / HTTPS|` — label with DATA + PROTOCOL |
| Trust boundary | `subgraph TB_x[...]` | network segment, process/user-priv change, org boundary |

Rules:
- **Label every flow with what data moves and over what channel.** Unlabeled
  arrows hide information-disclosure and tampering threats.
- **Logs, metrics, and backups are data stores.** They hold copies of your
  assets at usually-weaker protection; draw them or you will miss the most
  common disclosure path.
- **The attacker is not drawn; attackers are positions.** Any external entity,
  any compromised element, any element across a boundary is a potential
  attacker position.
- **One diagram per level.** L0 context diagram (system + externals), L1 per
  service. Stop decomposing when every flow within an element is same-trust;
  decompose further when a single box contains a privilege change.

### 2. Trust boundaries — the load-bearing concept

A trust boundary is any line across which the level of trust in data or
identity changes. Draw one wherever ANY of these change:

1. **Network zone** — internet → DMZ → internal → restricted.
2. **Identity/authn** — anonymous → authenticated → admin; service A → service B
   (even "internal" services authenticate to each other or share a boundary).
3. **Process privilege** — user-mode app → root daemon; container → host.
4. **Organization/control** — your code → third-party SaaS, package registry,
   customer-supplied plugin, model provider.
5. **Data validation state** — raw upload → parsed/validated object. (Parsers
   ARE boundary controls; file parsing is a boundary crossing.)
6. **Time** — producer → queue → consumer; data written now, executed later
   (stored XSS, poisoned cache, scheduled job args). Deferred trust is still
   crossing trust.

Heuristic: if compromising X gives the attacker nothing they didn't already
have at Y, then X and Y share a boundary. If you "aren't sure" whether two
elements share a boundary, they don't — model the crossing.

### 3. Entry points, assets, actors, privilege levels

Produce these tables for every model; they are the enumeration substrate.

**Entry points** — every place external data or control enters:

| ID | Entry point | Channel | Authn required | Reached by | Reaches |
|---|---|---|---|---|---|
| EP1 | `POST /api/orders` | HTTPS | JWT (user) | TL2 | API → DB, queue |
| EP2 | `order.created` consumer | AMQP | broker creds (any internal producer) | TL5 | worker → shipping API |
| EP3 | Stripe webhook `/hooks/stripe` | HTTPS | signature header | TL1 (signed) | API → DB |
| EP4 | nightly `reconcile` cron | scheduler | none (implicit) | scheduler only | DB read/write |

**Assets** — what an attacker wants; rank them:

| ID | Asset | Class | Worst-case impact | Trust levels allowed |
|---|---|---|---|---|
| A1 | customer PII (orders, addresses) | personal data | regulatory + churn | TL2 own rows, TL3 read |
| A2 | Stripe API key | credential | financial fraud | TL5 only |
| A3 | order integrity (prices, states) | business data | direct loss | TL2 create, TL5 update |
| A4 | service availability | availability | SLA breach | — |

Include **abstract assets**: reputation, compute (cryptomining), your users'
trust in messages you send (phishing-from-you), and your system as a pivot
into others.

**Actors and privilege levels:**

| ID | Actor | Privilege | Notes |
|---|---|---|---|
| TL1 | anonymous internet | none | reaches EP1 pre-auth surface, EP3 |
| TL2 | customer | own-tenant read/write | the IDOR baseline |
| TL3 | support agent | cross-tenant read, impersonate | high-value phish target |
| TL4 | CI pipeline | deploy + secrets | machine actor, often over-privileged |
| TL5 | `api` service account | DB rw, queue publish | blast radius if API popped |

**Cross-reference the three tables by ID.** Each asset row names the trust
levels allowed to touch it and how; each entry point names the trust levels that
can reach it. Then join: for every entry point, the trust levels reaching it
against the assets it touches. A trust level that reaches an asset through some
entry point but is not listed on that asset's row is an authorization gap found
on paper, before any code is read (TL1 reaching A1 through a pre-auth export is
the classic). OWASP: Code Review Guide v2.

Always include **machine actors** (service accounts, CI, cron) — they hold the
broadest standing privilege in most real systems — and at least one **insider**
actor. Add three **threat-oriented personas** beside the technical attacker: a
*malicious* user (wants harm), an *abusive* user (a dishonest customer who
stays inside the rules and chains legitimate actions for gain), and an
*unknowing* user (careless, triggers harm by accident). The abusive user sends no
payload, so STRIDE-per-flow alone misses them; their questions are `05` §3.
OWASP: Abuse Case cheat sheet, Business Logic Security cheat sheet.

**Shared infrastructure services and component function** — beside the DFD, list
the platform services every component leans on, because a model that treats them
as scenery cannot ask what happens when they fail open or are bypassed:

| Service | Instance | Docs / repo | Enforces for us | If bypassed or down |
|---|---|---|---|---|
| authn | IdP (OIDC) | link | who the caller is | fail closed? cached tokens? |
| authz | policy engine / gateway | link | which routes, which objects | per-service fallback? |
| discovery, gateway, logging, monitoring | … | link | routing, rate limits, audit trail | direct pod reach, silent logs |

Give every DFD process one line of **business or security function** ("issues
refunds", "terminates TLS and checks JWT"). A component whose function nobody
can state is a finding in itself, and a security function (a gateway checking
authz) tells you which component the rest silently trust. OWASP: Microservices
based Security Arch Doc cheat sheet.

**Dangerous functionality and user-chosen destinations** — where the code does
things that turn one bug into a compromise, and where the *user* picks what the
server connects to:

| ID | Location | Kind | Input origin | Containment |
|---|---|---|---|---|
| DF1 | `imports/loader.py:40` | deserialization of uploaded file | EP5 upload | none — finding |
| DF2 | `reports/query.py:88` | raw SQL built from filter params | EP1 | allowlisted columns |
| DF3 | `hooks/register.py:22` | **user-supplied webhook URL** fetched server-side | customer | egress proxy, deny private ranges |
| DF4 | `media/import.py:15` | **import-from-URL** | customer | none — finding |

Kinds to list: deserialization of untrusted data, dynamic code execution
(`eval`/`exec`/template compile), raw file or binary parsing, raw SQL, file paths
built from input, direct memory manipulation, and every feature where the user
supplies a URL, host or callback (webhooks, import-from-URL, link previews,
OAuth/OIDC discovery, PDF/image renderers). The second group is the SSRF surface,
recorded in the model instead of found in code review. Each row gets a catalog
pass (`03` §2: injection, SSRF, deserialization) and is where extra isolation earns its cost (`sota-sandboxing`).
OWASP: ASVS 5.0 V13.1.1, V15.1.5.

### 4. Worked mini-example — 10-line DFD with threats

```mermaid
flowchart LR
  B[Browser] -->|creds, then session / HTTPS| W(Web API)
  S[Stripe] -->|webhook: payment event / HTTPS+sig| W
  W -->|SQL: orders, users| DB[(Postgres)]
  W -->|order.created JSON| Q[[RabbitMQ]]
  Q -->|consume| F(Fulfillment worker)
  F -->|label request / HTTPS| C[Carrier API]
  W -->|structured logs| L[(Log store)]
  subgraph TB_internet[internet]; B; S; end
  subgraph TB_backend[VPC]; W; DB; Q; F; L; end
  subgraph TB_thirdparty[third party]; C; end
```

Boundary crossings → headline threats (full enumeration via `03` catalogs):
- B→W: credential stuffing (S), session fixation (S), tampered order body (T).
- S→W: forged webhook if signature unchecked or timestamp not validated —
  replay marks orders paid (S/T).
- W→L: PII/credentials in logs — disclosure to anyone with log access (I);
  log store is a data store, modeled as such.
- Q→F: time-shifted boundary — poisoned message executes later at worker
  privilege (T/E); broker creds shared by all internal producers = weak authn.
- F→C: carrier creds in worker env (I); carrier outage stalls queue (D);
  response from C is untrusted input INTO F (T) — third-party responses cross
  a boundary inward too.

## B. Extracting the model from an existing codebase (AUDIT mode)

Reconstruct entry points, flows, stores, and boundaries from artifacts in this
order — code lies less than docs.

### 5. Entry-point extraction by mechanism

Search patterns (adapt to stack; run broad, then verify by reading):

| Mechanism | What to grep / read |
|---|---|
| HTTP routes | framework registrations: `@app.route|@Get\(|router\.(get|post)|http.HandleFunc|urlpatterns|#\[get\(`; OpenAPI specs; ingress/ALB rules in IaC |
| gRPC | `.proto` files, `RegisterService`, server interceptors (authn lives here) |
| Queue/stream consumers | `@KafkaListener|consumer|subscribe|sqs.receive|channel.basic_consume|pubsub.*subscription`; broker IaC for topic ACLs |
| Cron/scheduled | `crontab`, k8s `CronJob`, `@Scheduled|celery beat|cloudwatch event|cloud scheduler`; note: cron handlers often skip authn entirely |
| Webhooks (inbound) | routes named `hook|callback|notify|ipn`; verify presence of signature validation NEXT TO the route |
| Third-party callbacks | OAuth `redirect_uri` handlers, payment IPN, SSO ACS endpoints — high-trust by design, check state/nonce/signature |
| File ingestion | upload routes, `multipart`, S3 event triggers, watched directories, email-attachment pipelines |
| CLI/admin | `argparse|cobra|click` entry points, `/admin` routes, debug endpoints (`/actuator|/debug/pprof|graphql introspection`) |
| Outbound that returns | every HTTP client call site is an entry point for the RESPONSE (deserialization, SSRF-redirects) |
| Cookies and headers | `request.cookies|req.cookies|$_COOKIE|getCookies\(|request.headers` — a cookie value the server set is still client-supplied on the way back; so are `Host`, `X-Forwarded-*` and custom headers |
| Environment and config files | `os.environ|getenv\(|process.env|System.getenv|ENV\[`; property/YAML/INI loaders — attacker-reachable wherever a tenant, a CI job, a mounted volume or an admin UI can write them |
| Output of spawned processes | `check_output|subprocess.run|exec.Command|child_process|popen\(` — the child's stdout/stderr is input, parsed at the parent's privilege |
| Late-bound code paths | `importlib.import_module|__import__\(|Class.forName\(|ServiceLoader|dlopen\(|getattr\(` with a variable name, plugin directories, config-named handler classes — whoever controls the name picks the code that runs |

For each hit record: path:line, authn mechanism (or none), input schema,
downstream reach. **An entry point with no findable authn check is a finding,
not a TODO.**

Worked extraction excerpt (Flask + Terraform monorepo):

```
$ grep -rn "@app.route\|@bp.route" services/ | wc -l        → 38 routes
$ grep -rn "@require_auth\|@login_required" services/ | wc -l → 31 decorators
  → 7 routes to read by hand. Verdict: 4 are health/static; 2 are the
    OAuth callback + Stripe webhook (sig-checked, OK); 1 is
    services/admin/jobs.py:14 POST /internal/requeue — NO AUTH. Finding.
$ grep -rn "basic_consume\|@celery" services/               → 5 consumers
$ grep -rn "aws_cloudwatch_event\|CronJob" infra/           → 2 schedules
$ grep -rn "0.0.0.0/0" infra/*.tf
  infra/sg.tf:41 ingress 5432 ← the DB is internet-reachable. Finding.
```

The arithmetic pattern (routes minus auth decorators, then read the
remainder) scales to any framework and is reproducible evidence for the
audit trail (`06` §2).

**Bucket the surface and count it.** Group the entry points by function (login
and recovery, search, CRUD, multi-step workflow, money or value transfer, admin
and monitoring, file ingestion) and note technology or risk where it differs.
Record a count per bucket, and for each high-risk bucket, whether it also sits
behind a compensating layer (WAF, IDS/IPS, gateway rate limit). That layer
changes likelihood only; it is never the primary control (`04` §7 "best-case
likelihood"). Keep one line per release with the totals: entry points,
unauthenticated ones, admin ones. That number is the trend metric. A jump
between releases with no model revision is drift (`05` §4), and a bucket
growing faster than the rest is where the next review goes. OWASP: Attack
Surface Analysis cheat sheet.

### 6. Stores, flows, and assets from code

- **Stores:** DB connection strings/ORM configs, S3/GCS client instantiations,
  Redis/memcached, message broker (it stores messages), log/metric sinks,
  `localStorage|document.cookie` in frontend code, mobile keychain/shared-prefs.
- **Data classes/assets:** ORM models and migrations (column names: `email`,
  `ssn`, `dob`, `address`, `token`), secrets managers usage, `.env.example`,
  IaC secret resources. Sequential integer PKs on user-owned resources →
  enumeration risk, note it.
- **Flows:** trace from each entry point to stores/outbound calls. For large
  codebases, trace only flows from entry points that touch top-3 assets —
  depth over breadth.

### 7. Inferring trust boundaries from an existing system

- **Network:** VPC/subnet/security-group/k8s NetworkPolicy in IaC; ingress vs.
  ClusterIP services; "0.0.0.0/0" rules mark the internet boundary precisely.
- **Identity:** where authn middleware is mounted (and which routes are
  EXCLUDED — exclusion lists are boundary holes); service-to-service auth
  (mTLS, IAM, shared static token = weak boundary); IAM policies map machine
  actors to reach.
- **Privilege:** Dockerfile `USER`, k8s `securityContext`, sudoers, DB users
  per service (one shared `app` superuser = no internal boundaries in the data
  tier).
- **Org:** every third-party SDK/API in lockfiles + outbound allowlists; each
  is an org boundary with its own catalog pass (`03`).

Then DIFF inferred boundaries against any documented architecture: each
mismatch (documented boundary absent in code, or real flow absent from docs)
is itself a finding — drift is how systems rot.

### 8. Privilege-reach map (what a compromise buys)

For each process and machine actor, answer: "if THIS is compromised, what can
the attacker now reach?" One table, built from creds in env/IAM/DB grants:

| If compromised | Reaches directly | Notable NOT-reach |
|---|---|---|
| Web API pod | orders DB rw, queue publish, Stripe key | carrier creds, CI |
| Fulfillment worker | queue consume, carrier API, orders DB **rw** | Stripe key |
| CI runner | deploy creds, all repo secrets, prod kubeconfig | — |

This table does three jobs: exposes over-privilege at a glance (why does the
worker have DB **write**? why does CI reach prod directly?), provides the
impact half of every rating in `04`, and identifies where one segmentation
control collapses multiple attack-tree branches. In audit mode it is derived
purely from IAM policies, DB grants, and network policy — no interviews
needed, and it rarely matches what the team believes.

### 8a. Cross-entry-point consistency for sensitive operations

The entry-point table is organised by *door*; attackers shop by *operation*. For
each sensitive business operation (refund, transfer, role grant, email change,
export, delete), list every path that can invoke it: each API version, the
mobile or legacy endpoint, internal/admin tooling, webhook and callback handlers,
queue consumers, batch/cron jobs, bulk-import and GraphQL mutations. Then
compare, per path, the authz check, ownership/tenant check, state/workflow
check, limits and audit event against the strongest path:

| Operation | Path | Authz | Tenant | State check | Limit | Audit |
|---|---|---|---|---|---|---|
| refund | `POST /v2/orders/{id}/refund` | role `support` | yes | not-yet-refunded | 1/order | yes |
| refund | `POST /v1/refund` (mobile) | any user | **no** | **no** | none | no |
| refund | `reconcile` cron | none (implicit) | n/a | yes | none | no |

**A path weaker than its sibling is a finding, rated at the weaker path's
reachability** — the careful admin endpoint protects nothing if a looser public
one performs the same write. Adding a path is a re-model trigger (`05` §4). Fix
by routing every path through one guarded service function, not by copying the
checks; the per-path controls for jobs and webhooks are `sota-code-security`
rules/03 §8. OWASP: Business Logic Security cheat sheet.

### 9. Decomposition outputs

A decomposition is done when you have: L0+L1 mermaid DFDs with boundaries; the
tables (entry points, assets, actors/privileges, stores, dangerous functionality
and user-chosen destinations) with code refs
in audit mode; and a stated scope ("modeled X; excluded Y because Z"). Excluded
scope must be written down — silent exclusions are where breaches live.

## Audit checklist

- [ ] DFD exists, uses the 4-element vocabulary, every flow labeled with data
      + channel; logs/backups/caches drawn as stores.
- [ ] Trust boundaries explicit and justified by network/identity/privilege/
      org/validation/time changes — not just "internal vs external".
- [ ] Entry-point table covers HTTP, gRPC, queues, cron, webhooks, callbacks,
      file ingestion, admin/CLI, and third-party responses; each row has authn
      mechanism and downstream reach.
- [ ] Every entry point in code appears in the table (grep sweep performed);
      authn-less entry points flagged.
- [ ] Non-HTTP input sources (§5: cookies, environment/config, child-process
      output, late-bound code) are in the table. Sweep late binding with
      `grep -rn -E "importlib\.import_module\(|__import__\(|Class\.forName\(|ServiceLoader\.load|dlopen\(|getattr\([A-Za-z_.]+, *[a-z_]*(request|req|params|args|name|cfg|config)" .`;
      a hit whose name comes from input or tenant-writable config with no
      allowlist → High, and any unlisted hit → Medium.
- [ ] Entry points bucketed by function with a count per bucket and a
      per-release total (§5); count routes with `grep -rn -E "@app\.route\(|@bp\.route\(|router\.(get|post|put|patch|delete)\(|@(Get|Post|Put|Patch|Delete|Request)Mapping|http\.HandleFunc\(" . | wc -l`.
      A total that grew with no model revision → Medium.
- [ ] Asset table ranks concrete and abstract assets; data classes derived
      from schemas, not memory.
- [ ] Shared infrastructure services (authn, authz, discovery, gateway,
      logging, monitoring) listed with docs links, and every process has a
      one-line function; a service the model assumes but never lists → Medium.
- [ ] Actors carry trust-level IDs, assets name the levels allowed, entry
      points the levels reaching them; the join shows no level reaching an
      asset it is not allowed (a mismatch → High when TL1 is the level).
- [ ] Actor table includes machine actors (CI, service accounts, cron) and an
      insider; privilege per actor stated; malicious, abusive and unknowing
      user personas listed. Missing abusive persona on a feature that
      dispenses value (credits, refunds, coupons) → Medium.
- [ ] Dangerous-functionality and user-chosen-destination table exists and
      matches code. Sweep sinks with `grep -rn -E "pickle\.loads?\(|yaml\.(unsafe_)?load\(|ObjectInputStream|unserialize\(|Marshal\.load|(^|[^.A-Za-z_])(eval|exec)\(|new Function\(|os\.system\(|shell=True|\.raw\(|execute\(f[\"']" .`
      and user-supplied URL fields with `grep -rn -i -E "(webhook|callback|import|feed|avatar|remote|source|target)_?url" .`;
      a hit absent from the table → Medium, and High when it reaches untrusted
      input with no containment recorded.
- [ ] Each sensitive operation has a cross-entry-point row set (§8a); list
      alternate route prefixes with `grep -rn -E "[\"'](/?[A-Za-z0-9_{}:.-]+/)*/?(v[0-9]+|internal|admin|legacy|mobile)/" .`
      and add cron/consumer/webhook callers by reading. A path enforcing fewer
      checks than its sibling → High (Critical if reachable pre-auth).
- [ ] Boundaries inferred from IaC/middleware/IAM match documented
      architecture; drift recorded as findings.
- [ ] Time-shifted crossings (queues, caches, stored content, scheduled jobs)
      modeled as boundary crossings.
- [ ] Privilege-reach map built from actual grants (IAM/DB/network), and
      over-privilege deltas vs. need recorded.
- [ ] Scope exclusions written down with reasons.
