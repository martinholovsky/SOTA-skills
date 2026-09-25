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
**Identity is per running instance, not per agent type.** Twenty replicas sharing
one "triage-agent" credential are one principal: a single hijacked instance cannot
be told apart in downstream logs or revoked without stopping all twenty. Issue
each instance its own short-lived cryptographic identity at start — a SPIFFE ID
whose path names the instance, carried as an X.509-SVID (or JWT-SVID where a proxy
sits in between), or an equivalent attested workload credential
(`sota-identity-access` rules/05) — and have it authenticate to tools, brokers and
APIs *as that principal*, so every action names the instance and one instance's
credential can be revoked alone. OWASP: AISVS 9.4.1.

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
on unreviewed tool metadata (named taxonomy: sota-code-security rules/23 §1).
**Sandbox the local ones, too.** Under the MCP stdio transport the client launches
the server as a subprocess, so a `"command": "npx"` / `"uvx"` entry runs third-party
code as *you*, on the host, with your home directory, SSH agent and credential
store in reach — the agent's code sandbox (§2) does not wrap it. Run each local
server in its own least-privilege box (a container with `--network none` unless
it declares a need, or an OS-level sandbox — Landlock/bubblewrap per `02`,
Seatbelt per `04` §6): mount only the directories it serves, keep the keychain/credential helpers and dotfiles out, and give it no
wildcard host or filesystem permissions. OWASP: AISVS 10.1.3; MCP Security and
Secure Coding with AI cheat sheets.

**R3.5 — On developer machines, a managed permission baseline that the repo
cannot loosen.** A coding agent on a laptop holds the developer's SSH keys, cloud
sessions and push rights, so its approval settings are a security control:
- **Never start a bypass mode in a repository you have not reviewed.** Flags such
  as Claude Code `--dangerously-skip-permissions` (`defaultMode:
  "bypassPermissions"`), Codex `--dangerously-bypass-approvals-and-sandbox` (alias
  `--yolo`) or `--sandbox danger-full-access`, and Gemini CLI `--yolo` (`-y`) /
  `--approval-mode=yolo` switch off the
  per-action gate; they belong only inside an external sandbox (§2) — never in a
  shell alias used for every checkout.
- **Push the baseline from above the project.** Use the tool's admin-managed tier
  (Claude Code: `managed-settings.json`/MDM, which project and user files cannot
  override) to disable bypass mode (`permissions.disableBypassPermissionsMode`),
  and where supported restrict permission rules and hooks to the managed source
  (`allowManagedPermissionRulesOnly`, `allowManagedHooksOnly`).
- **Turn on the harness's own OS sandbox, and make it fail closed.** Claude Code:
  `sandbox.enabled: true`, `sandbox.failIfUnavailable: true` (otherwise a missing
  dependency warns and runs unsandboxed) and `sandbox.allowUnsandboxedCommands: false`
  (drops the per-command escape hatch), pushed from the managed tier. Codex:
  `--sandbox read-only|workspace-write` (config `sandbox_mode`), with admin requirements
  limiting `allowed_sandbox_modes`. It confines shell commands the agent runs, not MCP
  servers (R3.4). Docs: code.claude.com/docs/en/sandboxing, developers.openai.com/codex/config-reference.
- **Policy hooks live where the agent cannot write** — outside the workspace and
  not in a file the agent may edit (R3.4, R2.2).
- **Gate agent pushes at the VCS boundary**: branch protection plus required
  review on anything the agent pushes, so a hijacked session cannot land code alone.
- **Re-audit accumulated allow-rules** on a cadence; "always allow" answers pile up
  into a broad standing grant nobody decided on.
OWASP: DSOMM; Secure Coding with AI cheat sheet.

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

**Stopping is a fleet operation, and it travels out of band.** Revoking one
session's token is the minimum; the halt you will actually need is "stop every
running instance of agent X now" — one command that reaches all replicas,
queued jobs and scheduled runs, and that stops new ones from starting. Deliver it
over a channel the agent runtime cannot read, drop or spoof: the control plane
(scale to zero, revoke the shared credential, flip a flag the *broker* checks
before every tool call), never a message inside the agent's own context or a
file in its workspace — a hijacked agent can ignore, delete or forge those. Test
the halt on a schedule and time how long the last instance takes to stop.
Separately, give the human driving a session a **stop control** that works
mid-action, plus a way to **undo what the run did so far**: keep a checkpoint or
append-only change log of every side effect (files written, commits, records
changed, messages sent) outside the sandbox, so rollback replays it in reverse
rather than relying on the model to remember. Actions with no undo path fall
under R3.3. OWASP: AISVS 9.1.3, 9.6.3; AI Agent Security cheat sheet.

**R4.4 — Log every action attribution-grade:** tool name, full arguments, decision
(allowed/denied/approved-by), sandbox ID, session/user, result hash — to an
append-only store *outside* the sandbox. Prompt-injection incidents are debugged
from these logs; without them you can't even tell what leaked. For a high-risk
action (anything under R3.3) the record also carries the **action class or risk
score** the policy assigned, the **approval ID** that authorised it (or the
auto-approve rule that stood in for one), and the **version of the policy** in
force — so afterwards you can answer *why* it was allowed, not only that it was.
Alert on: denied egress spikes, metadata-endpoint attempts, reads of
credential-shaped paths, approval-bypass attempts. Give each agent detection a
name, a baseline and a written threshold, set per agent from its own history:
- a tool, or a target system, this agent (or instance) has never used before;
- admin-level queries or calls (permission changes, user listing, schema/DDL,
  bulk export) from an agent whose task needs none;
- tool calls per minute, and failed or denied calls in a burst, above baseline;
- prompt-injection detections per session past a count (one is noise, a run of
  them is a campaign);
- a jump in the share of high-risk (R3.3) actions in a session or fleet-wide;
- **drift in how humans approve**: approval latency collapsing toward zero,
  approve rate near 100% over large batches (rubber-stamping — the fatigue R3.3
  warns about, now measured), or the same user repeatedly retrying a denied
  action or probing bypass paths.
Each one names its response step in R4.5; detection content over these logs is
`sota-detection-engineering` rules/02. OWASP: AI Agent Security and MCP Security
cheat sheets.

**R4.5 — Wire detections to automatic, graduated, reversible containment.** An
alert that waits for a human while the agent keeps acting is a log entry. For each
agent detection class, write down the containment step that fires on its own and
scale it by confidence and severity: pause the session and hold pending tool calls
→ end the agent's sessions → revoke or down-scope its credentials → pull
privileged tools or cut egress entirely. Each step must be undoable and recorded
(who or what triggered it, and why), because false positives will happen and a
step that cannot be reversed will get switched off. Rehearse it: a scheduled drill
that fires a benign canary detection and checks the right step ran, within the
expected time. Bringing an agent back is a deliberate step, not a timeout — review
what it did while flagged, rotate what it could reach, then restore scope. The
auto-containment guardrails (high confidence, blast-radius allowlist,
human-in-the-loop above a threshold) are `sota-detection-engineering` rules/04 §7.
OWASP: AISVS 9.3.8; DSOMM.

## 5. Verification probe for agent sandboxes

**R5.0 — Run this (or equivalent) *as the agent would*, in CI and after any
infra change** (per `01` §5). Exit 0 only when every check is denied:

```sh
#!/bin/sh
# Every check must be DENIED; each success is a hole. Output never echoes a secret.
rc=0; inc=0; hole() { echo "HOLE: $*"; rc=1; }
need() { command -v "$1" >/dev/null 2>&1 || { echo "INCONCLUSIVE: no $1"; inc=1; return 1; }; }
denied() { case $1 in 6|7|28) return 0;; *) return 1;; esac; }  # curl: DNS/connect/timeout
curl -m5 -s -o /dev/null "${ALLOWED_URL:?set an allowlisted URL}" || { echo "INCONCLUSIVE: allowed URL failed"; exit 2; }
for f in /run/secrets/* ~/.aws/credentials ~/.ssh/id_*; do
  case $f in *.pub) continue;; esac; [ -e "$f" ] || continue; cat -- "$f" >/dev/null 2>&1 && hole "readable $f"
done
env | grep -Ei '^[^=]*(key|token|secret|password)[^=]*=' | grep -vq '^SANDBOX_' && hole "secret-named env var"
for u in http://169.254.169.254/latest/meta-data/ http://example.com/ http://1.1.1.1/; do
  curl -m3 -s -o /dev/null "$u"; denied $? || hole "egress $u"   # resolvable name + live IP
done
need nslookup && nslookup example.com 8.8.8.8 >/dev/null 2>&1 && hole "rogue-resolver DNS"
for d in /etc / "${AGENT_CONFIG_DIR:-}"; do
  [ -n "$d" ] || continue; p="$d/.sbx-probe.$$"
  touch -- "$p" 2>/dev/null && { rm -f -- "$p"; hole "writable $d"; }
done
need unshare && unshare -rn true 2>/dev/null && hole "namespace creation"
[ "$rc" -eq 0 ] && [ "$inc" -eq 1 ] && exit 2
[ "$rc" -eq 0 ] && echo "all denials held"; exit "$rc"
```
Test **one path per command**: `cat a b c && exit 1` fires only if *every* file reads,
so one readable secret beside two missing paths passed the old form. Egress targets
must *resolve and answer* — an NXDOMAIN canary or a dead IP "fails" on an open
network — and only curl's DNS/connect/timeout exits (6/7/28) count as denied. The
`ALLOWED_URL` positive control, run with the same method, separates a working sandbox
from a broken-but-fail-closed one (exit 2); so does a missing `nslookup` or `unshare`, which
would otherwise read as "denied". Verified 2026-09-26 under busybox sh in podman: exit 0 in a
no-network, read-only, non-root box whose seccomp profile denies `unshare`; 1 with egress open
or a writable root; 2 with `unshare` absent from PATH.

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

## 7. When your tool ingests other people's repositories

Scanners, SAST wrappers, dependency and call-graph analysers, code-review bots
and AI security tools share one shape: **the input is a repository somebody else
wrote, and the tool runs on a maintainer's machine, or in CI, with that
identity's credentials.** The target is the attacker. Nothing above changes; what
changes is that the legs are easy to miss, because the tool *is* a security tool
and its own documentation is usually the thing asserting it is safe (that
assertion is `sota-code-security` rules/14 §7 — count it, don't read it).

Four legs. A compromise needs two or three of them, and they are typically owned
by different people in different files, which is why no single reviewer sees the
chain.

**R7.1 — Staging follows links out of the target.** Copying a hostile tree with a
recursive copy that *dereferences* symlinks (Python `shutil.copytree(...,
symlinks=False)` — the default — and equivalents elsewhere) stages the link's
**target**, not the link. A repository containing `docs/notes.md ->
/home/you/.ssh/id_ed25519` puts that key inside the directory you are about to
bind-mount, index, or feed to a model. Resolve every entry and drop the ones
whose `realpath` escapes the source root, and **report the drops** rather than
skipping quietly — an unexplained missing file is a support ticket, a silent one
is a finding nobody files. This is the same predicate as archive extraction
(`sota-code-security` rules/09 §2); the copy path is where it gets forgotten,
because a copy does not look like parsing.

**R7.2 — "Static" analysis that runs the target's build system.** Ask, of the
exact command and flags you invoke: *does this evaluate build metadata the target
controls?* Many do by design — Rust `build.rs` and proc macros (so `cargo
clippy`, `cargo metadata`-driven tooling, and call-graph modes that compile),
Python `setup.py` and PEP 517 backends, npm `preinstall`/`install`/`postinstall`
(`sota-devsecops` rules/03 §3.4), Gradle/Maven build scripts, anything invoking
`make`. The answer is a property of the command, not the language, and it changes
between flags: a build-mode-`none` extraction and a build-mode-`autobuild`
extraction of the same repository differ by arbitrary code execution. **Verify it
for your invocation** — read the tool's docs for that flag, or run it against a
canary target that writes a marker file — and treat "it only compiles" as
execution until proven otherwise, because compilation *is* the execution step for
several of the ecosystems above.

**R7.3 — The sub-agent inherits your shell.** An LLM step that reads target
source is R1.1's untrusted content, and it must be spawned with tools **off** —
which means off by *default*, not off at the call sites someone remembered
(`sota-code-security` rules/14 §6a). Two details are dropped constantly: the
child's **working directory**, which defaults to the parent's — usually your own
repository, holding its `.env` — so set it explicitly to the staged copy; and the
child's **environment**, which inherits every API key the parent holds (R2.2).
Per R6.1 the analysis sub-agent gets *less* scope than the orchestrator, never
the same.

**R7.4 — Egress is on unless something turned it off.** A container run with no
`--network` flag has full outbound access. That is often a deliberate choice —
dependency resolution needs the registry — but it is the leg that converts
"executed some of the target's code" into "exfiltrated the operator's
credentials". Where the analysis genuinely needs the network, R4.1's FQDN
allowlist is the form it should take; where it does not, `--network=none` is one
flag and the whole chain stops.

**The audit move is the intersection, not the list.** Each leg alone is a
hardening note. Grep for all four across every ingest path — including the ones
outside the change you are reviewing, which is where the complete chain usually
sits (`sota/rules/03` §4, sweep before you drop) — and the finding is the module
where they coexist. Rate it with the chain named leg by leg (`sota/rules/03` §1).

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
- [ ] **High** — Locally launched MCP servers run in their own sandbox, not bare on
      the host (R3.4). JSON (`*mcp*.json`, Gemini `settings.json`, Claude Desktop) and
      Codex TOML entries; run at the repo root, then over `~/.gemini ~/.codex` in place
      of `.` (raw `ugrep` needs `--hidden` to enter `.cursor/`, `.gemini/`, `.codex/`):
      ```sh
      grep -rnE --include='*mcp*.json' --include='settings.json' --include='claude_desktop_config.json' --include='config.toml' '"command"[[:space:]]*:[[:space:]]*"(npx|uvx|node|python3?|bunx|deno)"|^[[:space:]]*command[[:space:]]*=[[:space:]]*"(npx|uvx|node|python3?|bunx|deno)"' .
      ```
      — each hit is a server started directly as the developer; want a container or
      OS-sandbox wrapper with scoped mounts and no default network.
- [ ] **High** — No agent bypass mode in shared scripts, aliases or settings (R3.5):
      `grep -rnE -- '--dangerously-skip-permissions|--dangerously-bypass-approvals-and-sandbox|--yolo|--approval-mode[= ]yolo|"defaultMode"[[:space:]]*:[[:space:]]*"bypassPermissions"|danger-full-access|gemini[^|;&]*[[:space:]]-y([^[:alnum:]-]|$)' .`
      (raw `ugrep` needs `--hidden`) — acceptable only inside an external sandbox; a managed
      baseline disables bypass and turns the harness OS sandbox on fail-closed
      (R3.5), hooks sit outside the agent's write reach, agent
      pushes need review, and standing allow-rules were re-audited this quarter.
- [ ] **High** — Fleet-wide halt exists, travels out of band (control plane or
      broker, never the agent's context or workspace), and has a measured
      time-to-last-instance-stopped from a recent drill; users can stop a run
      mid-action and roll it back from a side-effect log kept outside the sandbox
      (R4.3).
- [ ] **Medium** — Every agent detection class maps to an automatic, graduated,
      reversible containment step, drilled with a canary, with a reviewed
      reintegration step (R4.5).
- [ ] For any tool that **ingests repositories or archives it did not author**:
      staging drops entries whose `realpath` escapes the source root (and reports
      the drops); every analysis command checked for whether it evaluates
      target-controlled build metadata; LLM steps over target source spawned
      tools-off, with an explicit `cwd` and a scrubbed environment; egress
      `none` or FQDN-allowlisted. Flag the module where all four coexist (§7).
- [ ] **High** — Each running agent instance holds its own short-lived
      cryptographic identity (SPIFFE-style SVID or equivalent) and authenticates
      downstream as itself; one instance can be revoked without stopping the fleet
      (R3.2). Manual: a credential shared by every replica is the finding.
- [ ] **Medium** — High-risk action records carry the action class or risk score,
      the approval ID (or auto-approve rule) and the policy version (R4.4).
      Manual: pick one past high-risk action and reconstruct why it was allowed.
- [ ] **Medium** — Named agent detections with written thresholds exist: new tool
      or target, admin-level calls, call rate, failed-call bursts, injection
      detections per session, high-risk-action share, and human approval drift
      (rubber-stamping, repeated bypass attempts), each mapped to an R4.5 step (R4.4).
