# Arm C results (ROADMAP 67 text), scored after each completion notification
| arm | clean | authz /16 | dep strict /19 | dep lenient /19 | P1 | P2 | P3 | P4 | P5 | P6 | P7 | tool calls | min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| w5 | yes (0 symbols, 0 net, 0 cross-arm) | 15 | 17 | 19 (otel rows abbreviate path `…/otelmux` — strict miss, read by hand) | 1 | 1 (--redact) | 1 | 1 | 1 (L105) | 1 (L68) | 1 (H-1..H-7 each a Reproduction) | 91 | 18.2 |
w5 per-module table at L362: module@version | advisories | fixed in | reachability (method). authz miss: ListProvidersUnderProject.
| w6 | yes (0 symbols, 0 net, 0 cross-arm; its 1 refuter agent not probed) | 15 | 17 | 19 (otel rows abbreviated, read by hand) | 1 | 1 (--redact) | 1 | 1 | 1 (L179) | 1 (L94) | 0 (5 of 6: H-1/H-2 labelled, H-3..H-5 request→effect chains; H-6 none) | 128 (+1 agent) | 29.5 |
w6 per-module table at L386 (module@version | C/H advisories | fixed in | reachable? / how checked | rating). authz miss: ListProvidersUnderProject.

## Against PREREG-C (a74129dacdc6878f)
- H67 (C mean lenient >= 10/19; refuted if < 8): C = 19.0 (19, 19) vs B 3.0, A 5.5 — HELD.
- H67b (C strict > 0 in at least one arm): 17, 17 — HELD (B and A were 0 everywhere).
- Guard (C mean authz >= 14): 15.0 — HELD.
