# Node.js Backend

## Runtime choice

- **Node LTS** (run the line the release schedule marks Active LTS — check github.com/nodejs/Release rather than trusting a number written here; 26 is Current and is scheduled to become LTS on 2026-10-28 — it ships Temporal enabled by default and undici 8): default for production backends. Largest ecosystem compatibility, slowest-moving, best observability story. Pin the major in `package.json` `engines` and `.nvmrc`/`.node-version`; CI must run the pinned version. From Node 27 the release cycle is annual and every major reaches LTS after six months as Current.
- **Bun**: fast installs/startup/test runner; fine for tooling, scripts, and apps you've load-tested on it. Verify native-addon and edge-case Node-API compat before betting production on it.
- **Deno**: strong security model (permission flags), built-in TS. Choose when its model fits; ecosystem friction has shrunk with npm compat but still exists.
- **Node's Permission Model is in-process least privilege, a seat belt rather than a sandbox.**
  `node --permission` denies each scope until an `--allow-*` flag grants it, but **which
  scopes exist depends on the Node major** (each flag's `added:` line in the CLI docs):
  file system (`--allow-fs-read`/`--allow-fs-write`), child processes, workers (all v20),
  native addons (v21.6/v20.12), WASI (v22.3/v20.16); inspector (`--allow-inspector`,
  v25.0/v24.12); **network (`--allow-net`, v25.0.0, not backported)**; FFI (`--allow-ffi`, v26.1);
  OpenSSL STORE loaders (`--allow-openssl-store`, v26.7/v24.21); VFS (`--allow-fs-vfs`, v26.9).
  So on Node 22 and 24 **`--permission` does not restrict the network at all**: measured on
  22.22.1, a `fetch` under `--permission` succeeded and `--allow-net` was rejected as a bad
  option. Keep egress control outside the process there (`sota-network-security`). The docs
  list the model as Stable since v22.13.0/v23.5.0 (added in v20 as experimental). Scope
  `--allow-fs-read`/`--allow-fs-write` to specific directories, never `*`, and add any other
  `--allow-*` only for a feature that needs it. Check a grant at run time with
  `process.permission.has('fs.read', path)`. Its own docs say it "does not protect against
  malicious code", so keep the container or OS sandbox (`sota-sandboxing` rules/04). Two
  documented gaps: file descriptors already open bypass it, and **symlinks are followed out of
  an allowed path**. Measured on Node 22.22.1 with only the app directory readable: reading a
  file outside it failed with `ERR_ACCESS_DENIED`, while a symlink inside the app directory
  pointing at that file returned its contents. Allowed paths must not hold symlinks an
  attacker can create or relative symlinks. *OWASP: Nodejs Security cheat sheet.*
- Decision rule: pick per-project, write runtime-neutral code (Web APIs: `fetch`, Web Streams, Web Crypto, `AbortController`) so the choice stays reversible. Avoid runtime-specific APIs in shared libraries.

## Use the platform — drop unnecessary deps

Node now ships what used to require packages. Every dep removed is supply-chain and maintenance surface removed.

| Dependency | Built-in replacement (Node ≥20/22) |
|---|---|
| axios/node-fetch/got | global `fetch` (undici) |
| nodemon | `node --watch` |
| dotenv | `node --env-file=.env` (≥20.6) |
| jest/mocha (for libs/simple apps) | `node:test` + `node:assert` |
| chalk (basic) | `styleText` from `node:util` |
| uuid | `crypto.randomUUID()` |
| minimist/yargs (simple CLIs) | `util.parseArgs` |
| glob (simple) | `fs.glob` (≥22) |
| ws client (basic) | global `WebSocket` (≥22) |

```bash
node --watch --env-file=.env src/server.ts   # Node ≥22.18/≥23.6 runs TS directly (type stripping, unflagged)
# Under native stripping, relative imports name the .ts file ('./db.ts', not './db.js') — rules/01 §"ESM-first"
node --test --experimental-test-coverage
```

Keep deps that earn their weight (pino, zod, drizzle/prisma, fastify). The bar: a dep must do something nontrivial that the platform doesn't.

## Env and config: parse once, crash fast

Never sprinkle `process.env.X` through the codebase — env vars are `string | undefined`, typos are silent, and defaults scatter.

```ts
// config.ts — the only file allowed to touch process.env
import { z } from 'zod';

const Env = z.object({
  NODE_ENV: z.enum(['development', 'test', 'production']),
  PORT: z.coerce.number().int().min(1).max(65535).default(3000),
  DATABASE_URL: z.url(),
  LOG_LEVEL: z.enum(['debug', 'info', 'warn', 'error']).default('info'),
  STRIPE_KEY: z.string().min(1),
});

const parsed = Env.safeParse(process.env);
if (!parsed.success) {
  console.error('Invalid environment:', z.treeifyError(parsed.error));
  process.exit(1);   // crash at boot, not at 3am when the code path is hit
}
export const config = Object.freeze(parsed.data);
```

- Boot-time crash on bad config is a feature: the orchestrator restarts and alerts; a lazy crash mid-request loses data.
- Secrets never in code or committed `.env`; inject via secret manager/orchestrator. `.env` is local-dev only and gitignored.
- No `NODE_ENV === 'production'` branches scattered in logic — derive named flags in config (`config.isDev`) and branch on those.
- **An unset `NODE_ENV` is development mode, not "no mode".** Measured on Express 5.2.1
  with `NODE_ENV` unset: `app.get('env')` returned `'development'`, and a thrown error's
  message and stack trace went into the HTTP 500 body. With `NODE_ENV=production` neither
  appeared. Make `NODE_ENV` required in the schema above (no `.default`) and set it in the
  image or unit file. If the deployment is production, assert it at boot and exit when it
  is not.
- **Dev tooling never serves production traffic.** `next dev`, the `vite` dev server,
  `vite preview` (its docs: "Do not use this as a production server"), `webpack serve`,
  `nodemon`, and `tsx watch`/`ts-node` belong in development. Production runs
  the built output: `next start`, static files from `vite build`, `node dist/server.js`.
  **The inspector is a remote shell:** Node's docs say that an `--inspect` bound to a public
  IP or `0.0.0.0` lets any client that can reach it "run arbitrary code". The default is
  `127.0.0.1:9229`, and `SIGUSR1` also starts it. Ship no `--inspect`/`--inspect-brk` in a
  production start command or `NODE_OPTIONS`, and reach a live process over an SSH tunnel.
  *OWASP: Error Handling cheat sheet; Secure Headers Project; ASVS 5.0 V13.4.*

## HTTP server hardening

Defaults are unsafe: Node's http server has lenient timeouts; frameworks accept huge bodies.

```ts
import { createServer } from 'node:http';
const server = createServer(app);
server.requestTimeout = 30_000;       // whole request (default 300s — too long)
server.headersTimeout = 10_000;       // slowloris defense (must be < requestTimeout)
server.keepAliveTimeout = 65_000;     // > LB idle timeout (ALB 60s) to avoid 502 races
server.maxRequestsPerSocket = 1000;
```

- **Body limits**: cap JSON/body size at the framework (`express.json({ limit: '100kb' })`, Fastify `bodyLimit`). Unbounded bodies = trivial memory DoS. Cap per route by actual need.
- **Behind a proxy**: set `trust proxy` correctly (exact hop count, not `true`) or rate limiting keys on spoofable `X-Forwarded-For`.
- **Headers**: `helmet` (or hand-set: `HSTS`, `X-Content-Type-Options: nosniff`, frame-ancestors via CSP). Disable `X-Powered-By`.
- **Rate limit** auth and expensive endpoints (`rate-limiter-flexible` backed by Redis when multi-instance — in-memory limits don't survive horizontal scaling).
- **Validation**: every route parses body/query/params with a schema before touching them (rules/01, rules/05). Fastify + zod type-provider, or tRPC, makes this structural.
- **Compression**: gate on response size; never compress encrypted/random content; beware BREACH when reflecting secrets in compressed responses.
- Prefer Fastify over Express for new services: schema-first validation, structured logging built in (pino), 2-3× throughput, maintained.

## Graceful shutdown

Kubernetes/ECS send SIGTERM and wait (default 30s) before SIGKILL. Dropping in-flight requests on deploy is a self-inflicted incident.

```ts
const server = app.listen(config.PORT);
const shutdown = async (signal: string) => {
  logger.info({ signal }, 'shutting down');
  server.close(() => logger.info('http closed'));        // stop accepting, finish in-flight
  server.closeIdleConnections();
  setTimeout(() => { logger.error('forced exit'); process.exit(1); }, 25_000).unref();
  await jobQueue.stop();          // stop pulling new work
  await db.end();                 // then close pools
  process.exit(0);
};
process.on('SIGTERM', () => void shutdown('SIGTERM'));
process.on('SIGINT', () => void shutdown('SIGINT'));
```

Order matters: (1) fail readiness probe / stop accepting, (2) drain in-flight with a deadline shorter than the orchestrator's, (3) close DB/queue/redis, (4) exit 0. `setTimeout(...).unref()` so the safety timer doesn't itself hold the process open. Long-lived connections (SSE/WebSocket) need explicit termination — `server.close` waits for them forever; track and end them.

## Health checks and readiness

Liveness ≠ readiness. Liveness: "is the process alive" — answer cheaply, no dependency checks (a DB blip must not get you killed and restarted in a loop). Readiness: "should I receive traffic" — checks pool health, returns 503 during shutdown drain.

```ts
let ready = true;                       // flipped false first thing in shutdown()
app.get('/healthz', (_req, res) => res.status(200).send('ok'));
app.get('/readyz', async (_req, res) => {
  if (!ready) return res.status(503).send('draining');
  const dbOk = await db.ping().then(() => true, () => false);
  res.status(dbOk ? 200 : 503).send(dbOk ? 'ok' : 'db');
});
```

Flip readiness to 503 at the start of shutdown, then wait one probe period before `server.close()` so the LB stops routing first — this is what makes zero-downtime deploys actually zero-downtime.

## Request context: AsyncLocalStorage

Propagate request ID / user / trace context without threading a `ctx` parameter through every signature.

```ts
import { AsyncLocalStorage } from 'node:async_hooks';
const requestContext = new AsyncLocalStorage<{ reqId: string; userId?: string }>();

app.use((req, _res, next) => {
  requestContext.run({ reqId: req.headers['x-request-id'] ?? crypto.randomUUID() }, next);
});

// anywhere downstream — no parameter drilling
export const log = (obj: object, msg: string) =>
  logger.info({ ...requestContext.getStore(), ...obj }, msg);
```

**Request-scoped state never lives in module scope.** One Node process interleaves every
in-flight request on one thread, so a module-level `let currentTenant` set by a handler is
read by whichever request resumes next. Measured: two concurrent handlers that set a
module global and then `await` both returned `'B'`, while the same handlers under
`als.run()` returned `'A'` and `'B'`. The same applies across invocations on serverless:
AWS's Lambda docs say objects declared outside the handler "remain initialized" when an
execution environment is reused, and advise against global variables for per-invocation data.
- Scope with `run()`, which exits the context when the callback returns or throws. Avoid
  `enterWith()`: it is Experimental and, per Node's docs, "will continue for the *entire*
  synchronous execution". Measured, code after the call in the same tick saw the store.
- `getStore()` returns `undefined` outside a context, and Node's docs list callback-based
  APIs and custom thenables as causes of context loss (fix with `util.promisify` or
  `AsyncResource`). Code that reads a tenant or user from it must throw on `undefined`, never
  fall back to a default tenant. A `Worker` does not see the store. Measured, the same
  module's `getStore()` returned `undefined` inside a worker started under `run()`, so pass
  the value in `workerData` or the message. *OWASP: Multi-Tenant Security cheat sheet; Session Management cheat sheet.*

It survives `await`, timers, and promise chains. Use it for logging context and tracing only — not as a grab-bag service locator (hidden dependencies become untestable). OpenTelemetry's Node SDK rides the same mechanism; adopt OTel for traces rather than hand-rolling.

## Process-level error policy

```ts
process.on('unhandledRejection', (reason) => {
  logger.fatal({ err: reason }, 'unhandled rejection');
  throw reason;   // escalate to uncaughtException path — same policy
});
process.on('uncaughtException', (err) => {
  logger.fatal({ err }, 'uncaught exception — exiting');
  // flush logs/telemetry synchronously if needed, then:
  process.exit(1);
});
```

Policy: **log, then die**. After an uncaught exception the process state is undefined (half-finished writes, corrupted singletons) — continuing risks data corruption worse than a restart. The orchestrator's job is restarting; your job is exiting loudly. Never install an `uncaughtException` handler that swallows and continues (HIGH finding). Per-request errors belong in framework error handlers — they must never reach the process level.

Two ordinary errors take this path without anyone deciding they should:

- **An `'error'` event with no listener throws.** Measured on Node 22.22.1: `emit('error', err)`
  on an `EventEmitter` with no `'error'` listener threw at the emit call ("Unhandled 'error'
  event") and the process exited 1. A dropped socket, a stream, or a Redis/DB/WebSocket client
  emitting `'error'` therefore takes down every in-flight request. Attach `.on('error', …)`
  where each long-lived emitter is created. Log the error and let the client reconnect or fail
  the one operation. Use `stream.pipeline` rather than `.pipe()`: measured, a source error
  reached `pipeline`'s callback, but crashed a `.pipe()` chain whose only listener was on the
  destination.
- **Express 4 drops a rejected async handler.** Measured: in express 4.22.3, an `async` route
  that threw never reached the error middleware. The request hung until the client gave up,
  and the rejection surfaced as `unhandledRejection`, which the policy above turns into a
  process exit. Express 5.2.1 passed the same rejection to the error middleware (500). On
  Express 4, wrap every async handler (`(fn) => (req, res, next) => fn(req, res, next).catch(next)`)
  or upgrade. *OWASP: Nodejs Security cheat sheet.*

- `process.on('warning')` → log it (catches MaxListenersExceeded, deprecations).
- Don't call `process.exit()` in normal flow — it skips pending I/O and `finally` blocks; let the loop drain or use exit codes from the shutdown path only.

## Structured logging: pino

`console.log` in services is unsearchable, unleveled, and synchronous-ish under load. pino writes newline-JSON, fast, with levels and redaction.

```ts
import { pino } from 'pino';
export const logger = pino({
  level: config.LOG_LEVEL,
  redact: { paths: ['req.headers.authorization', 'req.headers.cookie', '*.password', '*.token'], censor: '[redacted]' },
  // dev only: transport: { target: 'pino-pretty' }
});

// Structured fields first, message second — never string-interpolate data
logger.info({ userId, orderId, durationMs }, 'order created');
logger.error({ err }, 'payment failed');   // `err` key serializes stack + cause chain
```

- One child logger per request with a request ID: `req.log = logger.child({ reqId })` (Fastify does this automatically). Propagate the ID to downstream calls (`AsyncLocalStorage` for context without parameter drilling).
- Redact secrets at the logger, not by hoping call sites remember.
- Never log: tokens, passwords, full card numbers, raw request bodies on auth routes, PII beyond need.
- `pino-pretty` is a dev dependency/CLI, not production config. Production emits raw JSON to stdout; the platform ships it.

## Worker pools and not blocking the loop

One Node process = one JS thread. A 200ms synchronous task means every concurrent request waits 200ms.

- Known CPU work (hashing, image resize, PDF gen, big JSON.parse, compression): `piscina` worker pool (rules/03). Size pool ≈ cores − 1.
- `crypto.scrypt`/`bcrypt` async variants use the libuv threadpool — never the `*Sync` variants in request paths. Bump `UV_THREADPOOL_SIZE` (default 4!) if crypto/DNS/fs-heavy.
- Banned in request paths: `fs.*Sync`, `child_process.execSync`, `zlib.*Sync`, `JSON.parse` of multi-MB payloads (cap body size instead), synchronous template rendering of huge documents.
- Detect blocking in production: monitor event-loop delay with `perf_hooks.monitorEventLoopDelay()` (alert at p99 > ~100ms), or `blocked-at` in staging to get stacks.
- Multi-core: prefer N processes via the orchestrator (K8s replicas) over in-process `cluster`; keep processes single-purpose.

## Background work in services

- In-process `setInterval` jobs are lost on restart, duplicated across replicas, and drift. Anything that must run exactly/at-least once per schedule belongs in a job queue (BullMQ on Redis, pg-boss on Postgres, or the platform's scheduler) with: idempotent handlers, explicit retry/backoff policy, dead-letter handling, and per-job timeouts.
- If a lightweight in-process ticker is genuinely fine (cache refresh, metrics flush): wrap the callback in try/catch (a thrown error in a bare `setInterval` callback is an uncaught exception → process exit policy kicks in), `.unref()` it so it can't hold shutdown, and guard against overlap (skip if previous run still in flight).

```ts
let running = false;
const timer = setInterval(() => {
  if (running) return;
  running = true;
  refreshCache().catch(e => logger.error({ err: e }, 'refresh failed')).finally(() => { running = false; });
}, 30_000);
timer.unref();
```

- Long-running request work (report generation, imports): return `202 Accepted` + job ID + status endpoint; don't hold an HTTP request open for minutes against every timeout in the chain.

## Outbound calls: pools, timeouts, retries

Your service is only as reliable as its slowest dependency. Every outbound call gets:
- **Timeout**: `AbortSignal.timeout(ms)` on fetch; statement timeout on DB queries. No infinite waits — a hung upstream plus no timeout equals your own outage.
- **Bounded retries with jittered backoff**, idempotent operations only; honor `Retry-After`. Retrying non-idempotent POSTs duplicates orders — use idempotency keys.
- **Connection pooling**: undici `Agent`/`Pool` for high-volume HTTP to fixed origins; DB pool sized deliberately (start ~10 per instance; pool_size × instances must stay under the DB's max_connections — the default-100 Postgres ceiling is hit by autoscaling, not load).
- **Circuit breaking** on flapping dependencies (opossum) so you fail fast instead of queueing doomed work.

```ts
const res = await fetch(upstream, { signal: AbortSignal.timeout(3000) });
if (res.status >= 500) throw new UpstreamError(res.status);   // retry layer decides
```

## Native ESM in Node

- `"type": "module"` in package.json. `__dirname`/`__filename` don't exist — use `import.meta.dirname` / `import.meta.filename` (Node ≥20.11), or `new URL('./file', import.meta.url)` for asset paths.
- JSON imports: `import data from './data.json' with { type: 'json' }`.
- Don't mix: a stray `require` in ESM throws; CJS deps import fine via default import. Publishing libraries: ship ESM; add CJS only if your consumers truly need it (use tsdown/unbuild dual output, verify with `attw`; tsup's README says it is no longer actively maintained and points to tsdown).
- Dynamic `import()` works in both module systems — it's the migration bridge and the lazy-loading tool.

## `node:crypto` AEAD traps

Web Crypto's `decrypt` returns nothing until the tag verifies. `node:crypto`'s streaming
`Decipher` does not work that way, and each trap below was measured on Node 22:

- **`decipher.update()` returns plaintext before anything is authenticated.** Only
  `final()` checks the tag. With one ciphertext bit flipped, `update()` returned the
  tampered plaintext (`` `ttack at dawn… ``). `final()` then threw "unable to authenticate
  data". Code that uses `update()`'s output and calls `final()` late, or never, acts on
  forged data. Buffer the output, call `final()`, and only then use the result. For a
  stream, nothing downstream may commit until `end`. This is the Node spelling of
  `sota-code-security` rules/04 §2, "never act on plaintext before the tag verifies".
- **Pass `authTagLength` when you create a GCM decipher.** Without it, `setAuthTag()`
  accepted a **4-byte** truncated tag, and decryption succeeded with no warning. With
  `{ authTagLength: 16 }`, the same call threw `ERR_CRYPTO_INVALID_AUTH_TAG`. Node's
  deprecation **DEP0182** covers this: documentation-only in v20.13.0, runtime in v23.0.0,
  End-of-Life in v26.0.0. By that notice, Node lines before 26 accept short tags unless you
  pass the option. v23–25 add a runtime warning; the silent acceptance was measured on 22
  only.
- **`crypto.createCipher` / `createDecipher` are gone.** DEP0106 reached End-of-Life in
  v22.0.0 (Node 22 reports `typeof crypto.createCipher === 'undefined'`). The deprecation
  notice says they used "MD5 with no salt" for key derivation and "static initialization
  vectors". A hit means the code runs on an older Node or crashes on a current one. Migrate
  to `createCipheriv` with a key derived by `scrypt` or `pbkdf2` and a fresh IV.
- **Not a finding:** `crypto.pseudoRandomBytes` (and the aliases `prng`/`rng`). Node's
  DEP0115 says there is "no difference" from `crypto.randomBytes`. It is deprecated, not
  weak: a LOW hygiene item.

Source for all three deprecations: <https://github.com/nodejs/node/blob/main/doc/api/deprecations.md>.

## Transport verification: the Node spellings

Disabled certificate or host-key verification is **one class, stated once** in
`sota-code-security` rules/04 §5. This skill carries only Node's detectors, each measured on
Node 22 against a self-signed server whose certificate names a different host:

- `rejectUnauthorized: false`, an option of `https`/`tls` and of any agent that forwards
  those options. The default refused with `DEPTH_ZERO_SELF_SIGNED_CERT`, and this option
  connected.
- **`NODE_TLS_REJECT_UNAUTHORIZED=0`** disables verification **process-wide, global
  `fetch` included**. Every connection in the test succeeded. Node's only signal is one
  warning line. Look for it in env files, Dockerfiles, CI config, and `process.env`
  assignments.
- **`checkServerIdentity: () => undefined`** keeps chain validation but skips the hostname
  check. With the CA trusted, the default refused the name mismatch
  (`ERR_TLS_CERT_ALTNAME_INVALID`), and this override connected.
- `@grpc/grpc-js` `credentials.createInsecure()` is plaintext by construction. Acceptable
  only on loopback or inside a mesh that provides mTLS.
- **`ssh2`: no `hostVerifier` means accept any host key.** ssh2 1.17.0's `kex.js` sets
  `ret = true` with the debug message "Host accepted by default (no verification)" when
  none is configured. So the finding is the option's **absence** on `Client#connect`, or a
  verifier that always returns `true`. Compare against a pinned key.


## Server-side headless browsers and HTML-to-PDF

A browser driven from the server (Puppeteer, Playwright, anything wrapping Chrome) is an
HTTP client with a file reader built in. It runs inside your network. Measured with
Chrome for Testing 149 headless shell: navigating to a user-supplied `file://` URL put the
local file's contents into the rendered page. Navigating to `http://127.0.0.1:<port>/admin`
rendered an internal-only response. A PDF or screenshot of that page is the exfiltration
channel.

- **Treat the URL passed to `page.goto()` as an SSRF sink**, under the same rule as any
  user-supplied URL the server fetches (rules/05, "SSRF and server-side validation").
  Allowlist the scheme (`https:`) and the host, and re-check after redirects. Run the
  browser where the metadata endpoint and internal ranges are unreachable
  (`sota-sandboxing`).
- **Every "run this in the page" API accepts a string as well as a function.** That covers
  `page.evaluate()`, Puppeteer's `evaluateOnNewDocument()` and Playwright's
  `addInitScript()`. puppeteer-core's types say `pageFunction: Func | string`, and
  playwright-core's say `PageFunction = string | …`. A request value that reaches one of
  them is code injection into the browser. Pass data as the *argument* to a constant
  function.
- Rendering **user-supplied HTML** (`setContent`, an HTML-to-PDF job) hands the page's
  subresource loads to the attacker. A first check with `<img src="http://127.0.0.1/…">`
  loaded from a `data:` URL made **no** request, so that path is **not verified here**. Do
  not rely on the browser to block it. Sanitize the HTML and deny the renderer network
  egress.

## Audit checklist

- [ ] `grep -rn "process.env" src/ --include="*.ts" | grep -v "config\|env.ts"` — env access outside the config module (MEDIUM); no schema validation of env at boot (HIGH).
- [ ] **Dev server, debug mode or inspector in production (§"Env and config") — HIGH for a
      public `--inspect`, MEDIUM otherwise** —
      `grep -rnE -e '--inspect(-brk|-port)?([^[:alnum:]-]|$)|NODE_ENV[=:] *"?(development|dev)|"start": *"[^"]*(next dev|vite|webpack serve|nodemon|tsx watch|ts-node)' --include='package.json' --include='Dockerfile*' --include='Procfile' --include='*.yml' --include='*.yaml' --include='.env*' --include='*.service' .`
      — a production start command running a dev server or an inspector is the finding.
      Then check that `NODE_ENV` is required with no default in the config schema, since
      Express treats it unset as development.
- [ ] **Permission Model granted wholesale (§"Runtime choice") — MEDIUM** —
      ``grep -rnE -e '--allow-fs-(read|write)=(\*|/)([" ,]|$)|--allow-(net|ffi)([^[:alnum:]-]|$)' --include='package.json' --include='Dockerfile*' --include='*.yml' --include='*.yaml' --include='*.service' --include='Procfile' .``
      — a `*` or `/` file-system grant makes `--permission` decorative; `--allow-net` (all hosts,
      no scoping) and `--allow-ffi` (arbitrary native calls, rules/05) each reopen a whole scope.
      Where it is scoped, check the allowed directories for attacker-creatable or relative symlinks,
      and that an OS sandbox still exists. On Node 22/24 (`engines`, `.nvmrc`, base image) there
      is no network scope at all: confirm egress is limited outside the process.
- [ ] **Request-scoped state in module scope or a leaky AsyncLocalStorage (§"Request
      context") — HIGH when it carries a tenant or user** —
      `grep -rnEi '^(export )?let +[[:alnum:]_$]*(tenant|user|request|req|ctx|context|session|locale)[[:alnum:]_$]* *(:|=|;)|\.enterWith\(|getStore\(\)[^;]*(\?\?|\|\|) *[^;[:space:]]' --include='*.js' --include='*.ts' --include='*.mjs' --include='*.cjs' .`
      — a module-level `let` for per-request data is a cross-request (cross-tenant) leak.
      `enterWith` is a scope that never exits. A `getStore()` falling back to a default is
      fail-open. Read the hits: a module `let` assigned only at boot is fine.
- [ ] `grep -rn "Sync(" src/ | grep -v "test\|script"` — `*Sync` calls in server code (HIGH in request paths).
- [ ] Server timeouts: `grep -rn "headersTimeout\|requestTimeout\|keepAliveTimeout" src/` — absent = slowloris-exposed defaults (MEDIUM).
- [ ] Body limits configured (`grep -rn "bodyLimit\|limit:" src/`) — unbounded body parsing (HIGH, DoS).
- [ ] `grep -rn "SIGTERM" src/` — no graceful shutdown handler = dropped requests on every deploy (MEDIUM).
- [ ] **Error paths that crash or hang the process (§"Process-level error policy") — HIGH on
      a long-lived client or a request path** —
      `grep -rlE "createClient\(|new (EventEmitter|WebSocket|net\.Socket)\(|net\.connect\(|createConnection\(|\.pipe\(" --include='*.js' --include='*.ts' --include='*.mjs' --include='*.cjs' --exclude-dir=node_modules . | while IFS= read -r f; do grep -qE "on\(['\"]error['\"]|pipeline\(" "$f" || echo "$f"; done`
      — files that create an emitter or pipe streams with no `'error'` listener or `pipeline`
      anywhere (read the rest). Then, if `grep -nE '"express": *"[~^]?4\.' package.json` hits:
      `grep -rnE "\.(get|post|put|patch|delete|all|use)\([^)]*async *(\(|function|[[:alnum:]_]+ *=>)" --include='*.js' --include='*.ts' --include='*.mjs' --include='*.cjs' --exclude-dir=node_modules . | grep -vE "[Hh]andler\(|wrap\(|catch\(next"`
      — an unwrapped async handler on Express 4 hangs the request on a rejection (HIGH).
- [ ] `grep -rn "uncaughtException" src/` — handler that doesn't exit (HIGH); no `unhandledRejection` policy at all (MEDIUM).
- [ ] `grep -rn "console.log\|console.error" src/ | grep -v test` — in services, replace with pino (LOW; MEDIUM if logging objects with secrets).
- [ ] Logger redaction configured? `grep -rn "redact" src/` — logging auth headers/bodies without redaction (HIGH).
- [ ] `grep -rn "trust proxy" src/` and rate-limiter keying — spoofable client IP (MEDIUM).
- [ ] `package.json`: `engines.node` pinned; deps that duplicate platform built-ins (axios, dotenv, uuid, nodemon) — removable (LOW).
- [ ] `grep -rn "bcrypt.hashSync\|scryptSync\|pbkdf2Sync" src/` — sync crypto in request path (HIGH).
- [ ] `grep -rn "process.exit" src/ | grep -v "config\|shutdown"` — exits mid-flow skipping cleanup (MEDIUM).
- [ ] Readiness vs liveness probes distinct; readiness flips during drain (`grep -rn "readyz\|readiness" src/`) — single do-everything healthcheck (LOW/MEDIUM).
- [ ] Outbound fetch/DB calls without timeouts (`grep -rn "fetch(" src/ | grep -v signal`; DB client statement_timeout) — MEDIUM, HIGH for critical paths.
- [ ] Retry logic on non-idempotent operations without idempotency keys (MEDIUM/HIGH if money).
- [ ] DB pool size × replica count vs database max_connections — documented anywhere? (LOW).
- [ ] **`node:crypto` AEAD use (§"`node:crypto` AEAD traps")** —
      `grep -rnE 'createDecipheriv\(|createCipher\(|createDecipher\(|setAuthTag\(|pseudoRandomBytes|crypto\.(prng|rng)\(' --include='*.js' --include='*.ts' --include='*.mjs' --include='*.cjs' .`
      — for each GCM `createDecipheriv`: is `authTagLength` passed (absent: MEDIUM), and is
      `update()` output used only after `final()` returned (HIGH if acted on first)?
      `createCipher(`/`createDecipher(` is HIGH (static IV, MD5 key derivation).
      `pseudoRandomBytes`/`prng`/`rng` is LOW hygiene, not weak randomness.
- [ ] **TLS and SSH verification opt-outs (§"Transport verification") — HIGH on any hit that
      reaches production** — `grep -rnE 'rejectUnauthorized: *false|NODE_TLS_REJECT_UNAUTHORIZED|checkServerIdentity|createInsecure\(|hostVerifier: *(\([^)]*\)|[[:alnum:]_]+) *=> *true' .`
      (no `--include`: env files, Dockerfiles and CI YAML carry the variable). Read the
      value on each `NODE_TLS_REJECT_UNAUTHORIZED` hit, and read what each
      `checkServerIdentity` returns. Then list the `ssh2` users:
      `grep -rlE 'require\(.ssh2.\)|from .ssh2.' --include='*.js' --include='*.ts' --include='*.mjs' --include='*.cjs' .`
      Every `connect({...})` in those files **without** a `hostVerifier` accepts any host key.
      The finding there is the absence, so no pattern can print it.
- [ ] **Server-side headless browser inputs (§"Server-side headless browsers")** —
      `grep -rnE '\.(goto|setContent|evaluate|evaluateOnNewDocument|addInitScript)\(' --include='*.js' --include='*.ts' --include='*.mjs' --include='*.cjs' .`
      Skip the e2e suite. In server code, a request-derived URL reaching `goto` with no
      scheme and host allowlist is HIGH (SSRF, `file://` read). A request-derived string
      reaching `evaluate`, `evaluateOnNewDocument` or `addInitScript` is CRITICAL.
