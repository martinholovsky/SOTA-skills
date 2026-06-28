# 05 — WebSockets, SSE & Realtime

Scope: transport selection, WS lifecycle (auth, heartbeats, reconnection, ordering,
backpressure, close semantics), SSE patterns, scaling fanout and presence.

## 1. Choosing the transport

| | SSE | WebSocket | Long-polling | WebTransport |
|---|---|---|---|---|
| Direction | server→client | bidirectional | server→client | bidi, streams+datagrams |
| Protocol | plain HTTP | upgrade, own framing | plain HTTP | HTTP/3 (QUIC) |
| Auto-reconnect+resume | **built-in** (`Last-Event-ID`) | DIY | DIY | DIY |
| Infra friendliness | excellent (it's HTTP) | proxies/LBs need care | excellent | fair (Baseline since Safari 26.4, Mar 2026; UDP/443 blocked in some networks) |
| Binary | no (text/UTF-8) | yes | no | yes |

Decision rules:
- **Server-push only** (notifications, live feeds, dashboards, job progress, LLM
  token streaming) → **SSE**. It's the most under-used right answer; HTTP/2 removes
  the old 6-connection limit.
- **True bidirectional, low-latency, frequent client→server** (chat with typing,
  collaborative editing, multiplayer, trading) → **WebSocket**.
- Client→server messages are *occasional*? SSE down + plain POSTs up beats a WS —
  you keep HTTP auth, retries, and observability.
- **Long-polling**: fallback only, behind an abstraction, for ancient
  proxies/networks. Don't design for it first in 2026.
- **WebTransport**: adopt when you need unreliable/unordered delivery (game state,
  media) or stream multiplexing without head-of-line blocking. Browser support is
  no longer the blocker (Baseline since Safari 26.4 shipped it, Mar 2026) — keep a
  WS fallback for UDP-blocking middleboxes/networks.
- If you'd rather not own any of this: managed layers (Ably/Pusher/Momento) or
  infra (Centrifugo, Soketi) are legitimate — reconnection/resume/fanout are where
  homegrown realtime dies.

## 2. WebSocket lifecycle done right

### 2.1 Auth before (or immediately after) upgrade

- **`wss://` only in production** — never `ws://`. A plaintext socket leaks
  tokens/session data and is trivially MITM'd; treat `ws://` carrying credentials
  as a High finding (mirrors the mTLS-internal baseline).
- **Disable `permessage-deflate` compression** when the stream can carry secrets
  alongside attacker-influenced data — compression-ratio side channels are the
  CRIME/BREACH class applied to WebSockets. Leave it off unless you've reasoned
  about what shares the frame.
- The upgrade request is a GET: **no custom `Authorization` header from browser
  `WebSocket()`**. Your options, in order of preference:
  1. **Cookie auth** (same-origin apps): session cookie rides the upgrade; **must**
     verify `Origin` server-side — WS is exempt from CORS/SOP, so a malicious page
     can open `wss://yourapp` with the victim's cookies (Cross-Site WebSocket
     Hijacking). Origin allowlist or per-connection CSRF ticket is mandatory.
  2. **Short-lived one-time ticket**: client POSTs to `/realtime/ticket` (normal
     auth), gets a 30s single-use token, connects `wss://...?ticket=...`. Tokens in
     query strings land in logs — that's why it must be one-time + short-lived.
  3. **First-message auth**: accept the socket, require an `auth` frame within
     ~5s, process nothing else before it, hard-close on timeout. Keep
     pre-auth state tiny (DoS surface).
  - Do **not** smuggle tokens via `Sec-WebSocket-Protocol` (logged, semantically
    wrong, breaks subprotocol negotiation).
- Authorize per action after connect (subscribing to channel X = its own check),
  not just once at handshake.
- **Token expiry mid-connection**: long-lived sockets outlive JWTs. Either close
  with a specific code (e.g. 4401) when the token expires and let the client
  re-auth on reconnect, or support an in-band token-refresh frame. Ignoring expiry
  means a revoked user stays connected for hours — common audit finding.

### 2.2 Heartbeat / ping-pong

- TCP keepalive is not enough; intermediaries silently kill idle connections
  (typical LB idle timeout 60s). **Server pings every 20–30s; missing pong within
  the timeout ⇒ close.** Browsers auto-answer protocol pings, so server-side ping
  detects dead clients; clients also need an app-level liveness check (expect
  *some* frame every N sec) to detect half-open sockets where TCP looks alive
  but nothing flows.
- Align: heartbeat interval < LB/proxy idle timeout < your own idle close.

### 2.3 Reconnection with backoff + resume

Client side:
- Reconnect on any abnormal close with **exponential backoff + full jitter**
  (e.g. 1s base, ×2, cap 30s, `delay = rand(0, min(cap, base*2^n))`). No jitter ⇒
  thundering herd after every server deploy.
- Reset backoff only after a connection has been healthy for some seconds (not on
  connect — a connect-then-die loop must keep backing off).
- Honor close codes: don't reconnect on 1008/4401 (auth) without re-authing; don't
  reconnect at all on "kicked/replaced" codes.

Server side — **resume tokens**:
- Every server→client message carries a monotonically increasing per-channel
  sequence ID. Client sends `last_seq` on reconnect; server replays from a bounded
  per-channel buffer (size/time-limited ring, e.g. 1000 msgs / 5 min).
- If the gap exceeds the buffer: tell the client explicitly (`resume_failed`) so
  it re-fetches a snapshot via REST and re-subscribes. **Silent gap = corrupted
  client state**; the snapshot-then-stream pattern (fetch state, then apply
  buffered events with seq > snapshot version) is the correct cold-start too.

### 2.4 Ordering and delivery

- A single WS connection preserves order; your **backend fanout usually doesn't**
  (multiple publishers, pub/sub partitions, worker pools). Don't promise global
  order — promise **per-channel/per-entity order** and enforce it: one logical
  publisher sequence per channel, sequence numbers checked by clients.
- Delivery is at-most-once on a raw socket. If you need at-least-once, add acks +
  redelivery + **idempotent client handlers** (dedupe on message ID). State your
  guarantee explicitly in the protocol doc; "we never thought about it" is the
  usual answer and the usual bug.

### 2.5 Backpressure on slow consumers

The #1 realtime-server OOM: a slow client (bad network, background tab) can't
drain, and you buffer unboundedly on its behalf.

- **Bound every per-connection send queue.** On overflow, choose per product:
  - *Drop-and-coalesce* (tickers, presence, cursors: keep only latest per key) —
    usually right for state-shaped data;
  - *Disconnect* with close code "too slow" — right for event streams where loss
    is unacceptable; client reconnects and resumes/re-snapshots (§2.3).
- Check transport buffer signals (`bufferedAmount` in browsers, write deadlines /
  `ws.send` callbacks server-side); never `send()` blind in a loop.
- Per-connection **inbound** limits too: max message size enforced (reject with
  1009), rate-limit client frames, cap subscriptions per connection.

### 2.6 Close semantics

- Close deliberately with codes + reason: 1000 normal, 1001 going away (deploys),
  1008 policy/auth, 1009 too big, 1011 server error, 1012 service restart;
  4000–4999 app-defined (document them: e.g. 4401 token-expired, 4290
  rate-limited, 4100 replaced-by-newer-session).
- Graceful shutdown on deploy: stop accepting, send close (1001/1012), drain with
  a deadline, rely on client jittered reconnect to spread load to new instances.
  Mass hard-kill = reconnect stampede.

### 2.7 Message protocol design

WS gives you frames, not a protocol — you must design one and write it down.

```jsonc
// BAD: shapeless blobs, no type, no seq, no correlation
{"order": 9, "s": "shipped"}

// GOOD: enveloped, versioned, sequenced, correlatable
{
  "type": "order.updated",       // namespaced event type, same registry as webhooks
  "seq": 4174,                   // per-channel sequence (resume, gap detection)
  "channel": "orders:acct_7",
  "data": {"id": "ord_9", "status": "shipped"},
  "ts": "2026-06-12T09:30:00Z"
}
// client->server commands carry a client-generated id; server replies ack/nack:
{"type":"subscribe","id":"c-17","channel":"orders:acct_7","last_seq":4170}
{"type":"ack","id":"c-17"}     |    {"type":"nack","id":"c-17","error":{"code":"forbidden"}}
```

- Every frame has a `type`; unknown types are ignored (tolerant reader,
  rules/02 §3) — that's what lets you evolve the protocol.
- Request/response over WS needs explicit correlation IDs + per-command timeout
  client-side; without them you've built RPC with no error handling.
- Errors over WS follow the same machine-readable code discipline as RFC 9457
  (rules/01 §9): `{"type":"error","code":"rate_limited","retry_after":5}`.
- Version the protocol (subprotocol negotiation `Sec-WebSocket-Protocol:
  app.v1` or a `hello` exchange) so you can change framing later.
- One multiplexed connection with channels beats N connections per page — but
  then channel-level authz (§2.1) is mandatory per subscribe.

Client reconnect skeleton (the part everyone gets wrong):

```js
let attempt = 0;
function connect() {
  const ws = new WebSocket(url);
  let stableTimer;
  ws.onopen = () => { stableTimer = setTimeout(() => attempt = 0, 10_000); };
  ws.onclose = (e) => {
    clearTimeout(stableTimer);
    if (e.code === 4401) return reauthThenConnect();   // don't loop on auth
    if (e.code === 4100) return;                       // replaced: stay dead
    const delay = Math.random() * Math.min(30_000, 1000 * 2 ** attempt++);
    setTimeout(connect, delay);                        // full jitter
  };
}
```

## 3. SSE patterns

```http
GET /v1/events?stream=orders HTTP/1.1        HTTP/1.1 200 OK
Accept: text/event-stream                    Content-Type: text/event-stream
Last-Event-ID: 4173                          Cache-Control: no-store
                                             X-Accel-Buffering: no

                                             id: 4174
                                             event: order.updated
                                             data: {"id":"ord_9","status":"shipped"}
                                             retry: 5000
```

- Set `id:` on every event — the browser's `EventSource` reconnects automatically
  and sends `Last-Event-ID`, giving you resume **for free**; implement server-side
  replay from it (same bounded-buffer logic as §2.3).
- Send a comment heartbeat (`: ping\n\n`) every 15–30s to defeat idle timeouts.
- Disable proxy buffering (`X-Accel-Buffering: no`, no gzip on the stream, flush
  per event) — buffered SSE silently becomes batch delivery.
- `EventSource` can't set headers: use cookies or a ticket param (same rules as
  §2.1), or the fetch-based SSE client pattern for header auth (you then own
  reconnect+`Last-Event-ID` yourself).
- LLM/token streaming: SSE is the de-facto standard; include a terminal event
  (`event: done`) — clients must distinguish "stream complete" from "connection
  dropped", or they'll render truncated answers as final.

## 4. Long-polling (fallback only)

If you must support it (legacy proxies stripping upgrade headers, restrictive
corporate networks): `GET /poll?last_seq=N` holds the request up to ~25s
(< all intermediary timeouts), returns immediately when events exist or `204`
on timeout; client re-polls instantly on data, with small delay + jitter on
204/error. Same sequence/resume semantics as §2.3 — long-polling is just the
transport. Hide all three transports behind one client abstraction with
automatic downgrade (WS → SSE+POST → long-poll); never let product code know
which transport is active.

## 5. Scaling realtime

- **One process is a lie at scale**: users on node A must receive events published
  on node B. Standard architecture: stateless-ish WS/SSE edge nodes + **pub/sub
  backplane** (Redis Pub/Sub or Streams, NATS, Kafka for replayable channels).
  Edge node subscribes to channels its sockets need, fans out locally.
- **Sticky sessions** (LB affinity) only pin the TCP connection to a node — fine
  and often needed; they do **not** solve cross-node fanout and must not be used
  to fake it (node dies ⇒ its "state" dies).
- Connection state (which user, which channels, last_seq) belongs in the node's
  memory + recoverable from the client on reconnect — not in a shared DB on the
  hot path.
- Capacity realities: each node has FD/memory ceilings (tune ulimits; budget
  ~tens of KB per connection); deploys cause full reconnect waves — see §2.6 and
  jitter; autoscaling on connection count and on send-queue depth, not CPU alone.
- **Presence** (who's online): heartbeat-driven entries with TTL in Redis
  (`SETEX presence:{channel}:{user}`), refreshed by the edge node, expiry = offline;
  debounce flapping (grace period before broadcasting "left") and coalesce
  presence broadcasts (full roster sync on join + deltas after).
- Hot channels (1 publisher → 100k subscribers): coalesce/throttle per channel at
  the publisher side (max N msgs/sec, latest-wins), shard the channel across
  backplane partitions, and never fan out faster than your slowest tier absorbs.

## 6. WebRTC (when you self-host the infrastructure)

WebRTC is the path for peer-to-peer audio/video/data channels. **Scope first:** if
you only consume a CPaaS SDK/API (Twilio, LiveKit Cloud, Daily…), the provider owns
most of this — these rules apply when you **run your own TURN, media, or signaling
servers**. Media itself is encrypted by mandate (DTLS-SRTP); the risks are in the
*servers* around it. (ASVS v5.0 V17; RFC 8826/8827 security architecture.)

- **TURN server — relay abuse is SSRF over UDP/TCP.** A TURN relay forwards packets
  on behalf of a client; an open one lets an attacker reach your internal network
  and reserved ranges. **Allowlist relay peers to non-special addresses only** —
  deny loopback/RFC1918/link-local/broadcast/CGNAT, IPv4 **and** IPv6 (same blocklist
  as SSRF, sota-code-security rules/01 §5). Bound per-user port/allocation counts so
  one client can't exhaust the relay (resource exhaustion).
- **Media servers (SFU/MCU/recording) — only if you host them.** Pure browser-to-
  browser P2P is out of scope here. Use **approved DTLS-SRTP cipher suites + protection
  profiles**, manage the DTLS cert key under your key-management policy (rules/04),
  and **verify SRTP authentication** so an attacker can't inject RTP (media insertion
  or DoS). The server must **survive malformed and flooded SRTP** (input validation,
  bounded buffers, drop excess packets) and must not be vulnerable to the **DTLS
  `ClientHello` race-condition DoS** (Enable Security, 2020). Bind the DTLS cert to the
  **SDP fingerprint** and terminate the stream on mismatch (authenticity).
- **Signaling server.** Signaling carries no media but sets up the session — **rate-limit
  it** and **handle malformed messages gracefully** (integer-overflow/buffer-safe parsing)
  so a flood or a bad frame can't deny session setup. Authenticate and authorize
  signaling like any other API channel (the WS/§2 rules apply if signaling rides WS).

## Audit checklist

- [ ] Transport choice justified; server-push-only features use SSE, not a WS with one direction unused.
- [ ] WebRTC (self-hosted only): TURN relay allowlists non-special IPs (v4+v6) and caps per-user allocations; media server uses approved DTLS-SRTP + SRTP auth, survives malformed/flooded SRTP, not ClientHello-race vulnerable, checks DTLS cert vs SDP fingerprint; signaling rate-limited + malformed-input-safe. (CPaaS-only consumers: provider-owned — N/A.)
- [ ] WS auth: Origin checked server-side (CSWSH), or one-time short-lived tickets, or first-message auth with timeout; no long-lived tokens in query strings; nothing smuggled via `Sec-WebSocket-Protocol`.
- [ ] Per-channel/per-action authorization after connect, not handshake-only; token expiry mid-connection handled (close code or refresh frame).
- [ ] Server pings with pong timeout; intervals < LB idle timeout; half-open detection on client.
- [ ] Client reconnect: exponential backoff with jitter, cap, backoff reset only after stable connection, close codes honored (no reconnect loop on auth failure).
- [ ] Resume protocol exists: sequence IDs, bounded replay buffer, explicit `resume_failed` → snapshot path; no silent gaps.
- [ ] Ordering/delivery guarantees documented; per-channel sequencing enforced; at-least-once paths have acks + idempotent dedupe.
- [ ] Per-connection send queues bounded with a defined overflow policy (coalesce or disconnect); no blind unbounded sends.
- [ ] Inbound limits: max message size (1009), frame rate limit, max subscriptions per connection, pre-auth resource caps.
- [ ] Close codes documented incl. app-range (4xxx); deploys drain gracefully (1001/1012) instead of mass-killing.
- [ ] SSE: `id:` on every event with `Last-Event-ID` replay, comment heartbeats, proxy buffering disabled, terminal `done` event on finite streams.
- [ ] Cross-node fanout via pub/sub backplane; sticky sessions not abused as state storage; node death recoverable from client-held resume state.
- [ ] Presence uses TTL + heartbeat with flap debouncing; roster sync on join + deltas.
- [ ] Hot-channel throttling/coalescing exists; reconnect-stampede tested (kill a node in staging, watch the herd).
- [ ] Frames are enveloped (type/seq/channel), unknown frame types ignored, commands correlated by ID with ack/nack and client-side timeouts; protocol versioned.
- [ ] Realtime errors machine-readable (code + retry hints), mirroring the HTTP error discipline.
