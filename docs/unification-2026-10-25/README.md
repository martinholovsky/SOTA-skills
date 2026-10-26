# Unification sweep and drift list (2026-10-25)

Recorded at the end of the section-coverage paydown (ROADMAP item 76) for ROADMAP item 79. **Leads, not findings**: each line names file:line on the tree of its date; re-open both sides before changing either, and verify any fact (deadline, threshold, CVE, tool behaviour) against its primary source first.

Method: 20,024 units / 348 files; token Jaccard, cross-skill pairs 160,369,560; thresholds 0.3/0.4/0.5; + anchored family pass.
Classes (38): CONCEPT-DUPLICATE 6, MECHANISM-ALIKE 12, TEMPLATE-SHAPED 14, not-instruction 6.
DRIFT (fix first):
 D1 frozen install severities: devsecops SKILL:101,115 (Top-10 >= High), rules/03 §3.1 High; languages: c-cpp 06:400, python 01:370, ruby 04:308, rust 05:485 MEDIUM; js 05:419, php 05:295, go 08:106, swift 09:81, jvm 06:246 MEDIUM w/ different HIGH triggers; dotnet 06:288 HIGH.
 D2 session-ID regeneration: code-sec 17:15 full trigger list; php 04:54, ruby 03:141, js 05:291 shortened; php HIGH (04:372,:471) vs ruby MEDIUM (03:341,:393); ruby never cites code-sec 17.
 D3 finding format: canonical only php :88, ruby :81, swift :58; 6 multi-line blocks; rust Where/What/Why; 3 report-close contracts; swift SKILL:59 link points at rules/03-concurrency.md (should be ../sota/rules/03-audit-findings.md) BROKEN.
 D4 mutation testing: python 07:270-271 mutmut w/o gate warning; php 05:211-212 "not a per-PR gate" vs §6.3; rust/jvm/js/dotnet no line (my #605 only covered go/c-cpp/ruby/swift).
 D5 archive extraction: code-sec 01:153 rejects symlink entries; go 05:171, php 03:42, ruby 02:247 omit link entries.
 D6 code-sec 06 §3 escape hatches: no Swift; JVM stops at JDK 23 (jvm 04 §7 has JEP 472/498).
 D7 build-time SBOM severity: devsecops 14:164 "Medium (High deployed)"; python matches; c-cpp/dotnet/go/js/jvm flat MEDIUM.
 D8 Poetry framing: devsecops 03:23 vs python 01:31 (needs a Poetry run).
 side: golang 01:222-224 "recoverable panic" vs checklist :319-324 "fatal errors".
TOP CANDIDATES: T1 finding format (adopt canonical row + pointer to sota rules/03 §2,§5; fix swift link); T2 frozen install scaffolding+severity in devsecops §3.1, all 10 cite; T3 suppression contract -> widen devsecops 05 "Suppression discipline" to linters/type checkers, 10 cite; T4 test-path exemption -> new devsecops 05 §5.x; T5 process-fatal failures paragraph + parser-depth table into code-sec 06 §5 (one-line restatement kept per language); T6 "No proof tool" shared tail -> sota-testing 06 §6.7; T7 extend §6.3 pointer to python/php/rust/jvm/js/dotnet; T8 code-sec 06 §3 per-language one-liners + Swift; T9 session regen pointer to code-sec 17 + align php/ruby; T10 archive link entries; T11 sample-code-is-a-demo -> devsecops 15 pointer (low); T12/T13 keep.
Pointer pattern: owners cited by 10/10 stayed consistent; devsecops 03 (2/10), 05 (1/10), code-sec 17 (6/10) drifted.
 D9 (swift paydown agent, verified): mobile 05-performance.md:32 GOOD example uses Task.detached(priority:) + MainActor.run; sota-swift 03:67-69 says Task.detached drops priority/task-locals and its item :95 flags it; mobile 07:14-15 says use @concurrent fn or a separate actor. Fix the mobile example.
 D10 (verified): XMLDocument .nodeLoadExternalEntitiesNever trap in mobile 04:205,:271 but 0 hits in sota-swift 05 (Swift on macOS any target) -> add to swift 05 or point.
 D11 (data-eng agent): Iceberg v3/Trino support stated twice in data-eng: 01:56-57 undated ("as of writing") vs 05:67-70 dated 2026-09-26 -> make 01 point at 05.
 dup probes in data-eng: cost trend alerts 05:188-189 & 06:180; CI builds models 02:216-218 & 04:234-235; freshness 02:215 & 06:178-179. Replication slot probe in data-eng 03:202-205 & databases 05:243,:263-264 (data-eng stronger).
 outbox: databases 04:135-137 "poller" narrower than architecture 03:69-70 "poller or CDC" (not contradictory).
 D12 CSV formula injection chars (SECURITY; verify vs OWASP): threat-modeling 01:189-190 "=+-@, Tab, CR, LF, full-width ＝＋－＠" vs code-security 01:442,:498 "= + - @, tab or NUL".
 D13 UUIDv7 for exposed IDs (verify vs RFC 9562 §8): threat-modeling 01:86-87, 06:196-197 prefer v4 not v7; databases 01:117 "UUIDv7 when IDs leave the system", :352 "non-enumerable (UUIDv7/public_id)"; api-design 01:24 "ULID/UUIDv7"; databases 01:129 notes v7 leaks creation time.
 D14 OWASP MCP03:2025 scope: threat-modeling 03:251-252 vs code-security 23:77-78 (verify).
 D15 re-model triggers inside threat-modeling: 05:177-190 canonical 10; PR template 05:230-232 has 7; 01:217-220 has 7; SKILL:158-159 4 examples.
PARSER DEFECTS (invariant 43, reachability-graph.py sync_state/local_cites) — fix in a dedicated PR after the paydown:
 P1 headings inside fenced code counted as sections (threat-modeling 05 template: 6 false entries)
 P2 backtick file shorthand "`04` §8" counted as a local cite (false credit; threat-modeling 05:307)
 P3 '### N.' subsections colliding with '## N.' numbering (threat-modeling 02)
 D16 standing admin: cloud 02:24 "~0-2", 02:185 ">2 Medium" vs identity 05:32 "No standing admin", 05:120 JIT.
 D17 LB health checks: cloud 03:187-188 (+07:49) "checks downstream dependency readiness" vs architecture 04:177-181 "readiness reflects this instance, not shared deps".
 D18 k8s support window: cloud 04:40,:185 "~14-month" vs kubernetes 01:256-257 "~1 year" (verify kubernetes.io); and lag threshold inside cloud: 04:40 ">2 behind" vs 04:186/:223 "<=1 behind".
 D19 presigned URL lifetime: secrets 03:156 "<=1h" vs cloud 05:237-238 flags only >=10000s.
 D20 registrar lock scope (minor): cloud 03:104-105 vs network-sec 06:131.  D21 PDB scope (minor): cloud 04:171 vs kubernetes 06:38.
 D22 metadata block (SECURITY; verify GKE WI / EKS Pod Identity docs): network-sec 03:188-191, 05:267-274 (+05:280 ::ffff:169.254.0.0/112) block 169.254.0.0/16 + fd00:ec2::254 no exception; sandboxing 03:280-282 and kubernetes 01:199-200 "unless workload identity". Agent (unverified): GKE WI uses 169.254.169.254, EKS Pod Identity agent 169.254.170.23.
 D23 egress 0.0.0.0/0 scope: network-sec 05:259-260 app+data tiers vs cloud 03:65-67 data tiers only; private tier NAT+L7 filter vs allowlist.
 minor: cert lifetime hedge "~100 days" vs "100 days"; IMDSv2 "default on new EC2 types" net-sec 03:193 unverified.
 intra-skill dup: network-sec 03 R5/R6 restate 05 R9/R10; metadata items 03:281 & 05:330.
 D24 event-loop lag threshold: performance 04:231-232 "~20ms" vs async 04:180, js 04:276, js 06:175 "100ms".
 D25 DB pool start: performance 04:83-84 "2-4x CPU cores of DB" vs js 04:301 "~10 per instance".
 D26 TTL jitter: performance 05:132-133 "±10%" vs databases 05:174 "±10-20%".
 D27 fonts (soft): performance 06:140 Latin subset 15-30KB vs frontend 01:55 30-80KB; preload 1-2 vs primary face only.
 D28 orphaned tokio::spawn severity: rust 04:298-300 Medium vs async 07:8,:11 HIGH.
 D29 block_on in async: rust 04:294-295 Critical vs async 07:119,:126-128 HIGH (CRITICAL only self-deadlock); mechanism prose: rust 04:40-41 vs async 04:146-151 (futures::executor::block_on deadlocks; tokio's panic).
 D30 rust 05:492-494 claims "R9.x now live in rules/08; its checklist is the full set" — FALSE: R9.6 output cap and R9.7 pre_exec probed only in 05.
 D31 severity gaps: rust 04:315-317 unbounded fan-out and 04:310-312 lock across await have none; async 07:178, :89 HIGH.
 FIXED in paydown: rust 01:323 wildcard_enum_match_arm is restriction not pedantic (measured clippy 1.97.1).
 D32 detached task acceptability: python 04:36-50 (strong ref + done-callback) vs async 01:69-72 (handler + shutdown registration + comment).
 D33 digest-pinned base images: python 01:323-324 conditional "in regulated environments" vs devsecops 04:356, sandboxing 03:132,:369, architecture 06:169 unconditional; python 08:87-88 omits.
 D34 py-spy in prod (SECURITY): python 06:18 "safe on production" vs secrets 02:266-267 "disable py-spy on prod boxes by default ... remote secret extraction tools".
 D35 sleep-sync test severity: async 07:232 MEDIUM vs testing 02:401 "High each".
 D36 python internal: 01 §3 (138-141,153-155) lint exemptions for in-package tests vs 01 §5 (260) "tests live outside the package"; paydown P2 probe flags in-package tests -> needs a decision.
 D37 GDPR erasure deadline: databases 06:379 "30 days GDPR" vs privacy 03:5 "one month, extensible".
 D38 access review method: identity 04:98-111 full recertification vs privacy 05:80-99 diff-based quarterly.
 D39 hashing as anonymization: databases 06:384-386 vs privacy 02:114 (hashed id IS pseudonymous).
 D40 identifiers in logs: code-sec 07:68-70 mask emails vs privacy 06:98-99 never emails.
 D41 retention severity only in data-eng 06:121-123 (HIGH); privacy 03 §6 none.
 D42 tabletop cadence: detection 06:121 "regularly" vs privacy 06:148,:210 annually.  D43 alerts w/o runbooks: observability 06:127 HIGH vs detection 04 §6 none.
 D44 HTML-injection sink severity: web-fw 02:88, 04:72, code-sec SKILL:124 HIGH vs js 05:383 CRITICAL.
 D45 React Compiler memo: web-fw 02:67-68 "don't rip out blindly" vs js 06:68 "delete manual memo noise".
 D46 runtimeConfig secret grep: web-fw 05:130 includes password; 07:159 misses it.
 D47 k8s support window confirmed (k8s 01:256 ~1y vs cloud 04:40 ~14mo); cloud self-conflict >2 vs <=1 behind.
 D48 PDB scope confirmed (k8s 06:38 critical vs cloud 04:171 all multi-replica).
 D49 PSA enforce-version: k8s 03:37 "latest" vs devsecops 07:118 pin minor (+checklist :391 not latest).
 D50 Audit-only admission severity: k8s 03:126,:185 High vs devsecops 07:90 Medium.
 D51 etcd encryption probe strength: sandboxing 03:385-386 weaker than k8s 01:285 (KMS v2, identity not first).
 named-path probes that exit 2 if absent: web-fw 02 (src app components), 03 (app lib), 04 (src); js 05:441 (src/); ux-writing (src/).
 D52 confidential-computing SKILL.md vs its rules (severity): confidential nodes vs cluster admin SKILL:94-95 High / rules/04:34-36 Critical; K8s Secrets into CoCo SKILL:89-90 Critical / 04:182-183 High; no break-glass SKILL:99 Low / 04:202 Medium; unaudited ZKP SKILL:147-148 Critical / 05:204,:276 High; attest-nothing 01:182-184 High / 01:179-181, 03:97-99, SKILL:88-89 Critical; plain SEV 02:37, SKILL:92 High / 02:289-291 Critical.
 CC named-path probes: rules/04 checklist items 3,5,7 grep `manifests` (may be absent).
 D53 public pprof/debug endpoint: observability 05:106-108, SKILL:71, 06:147 CRITICAL vs golang 06:10,:222-223,:249 MEDIUM, golang 04:438-439 HIGH/MEDIUM.
 D54 exposed Actuator env/heapdump: observability CRITICAL vs jvm 08:18,:138 HIGH, secrets 03:149-150 High.
 D55 liveness checking deps: observability/architecture CRITICAL vs js 04:443 LOW/MEDIUM.
 D56 readiness on shared dep down (GUIDANCE CONFLICT): observability 05:50-52 + architecture 04:177-181 degrade vs js 04:141,:148-149 503 on db.ping() fail; (also cloud 03:187-188 D17).
 D57 averaged percentiles: observability SKILL:72 HIGH vs 06:110-111 MEDIUM-HIGH.
 D58 inbound traceparent: api 07:277-280 omits observability 03:160-163 caveat (don't trust sampling flags at edge).
 named-path probes: observability 06 §2 (src/, src/ k8s/ deploy/ charts/).
 D59 WRONG (measured, security): secrets 03:166 says curl -H "Authorization: Bearer $TOKEN" is "OK-ish: env expansion not in ps" — FALSE: ps -o args= shows the expanded token (reproduced). Fix in wave-3 PR: -H @file (0600) or -H @- (curl >= 7.55.0, man page).
 D60 secrets in a CLI: secrets 03:174-176 flag allowed if documented, env ok vs cli-ux 01:97-101 never argv, env last resort; shell-scripting SKILL:67, 03:396-398 CRITICAL.
 D61 curl|sh: cli-ux 04:32 acceptable with discipline vs devsecops 02:270-271 flag it vs shell 03:241,:408 CRITICAL unattended.
 D62 CLI error text: cli-ux 02:159 full path/URL, :168 "invalid…" vs ux-writing 03:74-76 bans paths/hostnames, :39-41 bans "Invalid input" (scope: ux-writing hands CLI to cli-ux but its greps have no CLI exception).
 D63 jvm internal: 01:200 mutable returns LOW vs 02:102 MEDIUM.  D64 ThreadLocal: performance 03:26 GOOD vs jvm 05:70-71, 03:59 avoid.
 zsh trap: jvm 06 probe `grep … pom.xml build.gradle*` aborts on unmatched glob in zsh.
 D65 GOMEMLIMIT (fact): golang 06:151-153, sandboxing 02:290-291 "soft limit" vs performance 03:219 "hard cap"; sizing golang ~90% vs observability 03:236 ~80% (collector).
 D66 InsecureSkipVerify severity: golang 05:384,:390,:496 CRITICAL vs devsecops 15:133 High on trust boundary vs code-sec 04:263-267, network-sec 06:229-234 none.
 D67 time.After in loop: golang 03:87-116,:282 MEDIUM (NewTimer+Reset) vs async 05:191 shows it as GOOD in a retry loop.
 FIX in wave-3 PR: golang 01:323-324 checklist ("they are fatal errors") vs section 01:223-224 (out-of-range = recoverable panic; measured go1.27.1).
 D68 DORA clock: security-compliance SKILL:183-184 "24h/72h (CRA, NIS2, DORA)" vs rules/04:138 "DORA 4h/24h/72h", privacy 04:239-241, 06:50 (4h). Summary understates.
 D69 CRA clocks missing from privacy 06:40-56 clock table (CRA 24h/72h/14d/1mo) — coverage gap.
 D70 SBOM scope: CRA item sec-comp 04:70,:271 top-level deps vs devsecops 03:471 full per build.
 cross-link: sec-comp 03 §2 gates -> devsecops 09 (gates must be able to fail).
 D71 usage-error exit code: shell 02:40,:46,:99-100 = 64 (EX_USAGE), "2 reserved-ish" vs cli-ux 02:60,:69 + checklist, cli-ux 01:191 = 2.
 D72 shell internal: 02:101-102 "don't emit 128+N" vs 05:76 trap ... exit 143; cli-ux 02:63 130 after SIGINT / re-raise.
 D73 GHA attacker-controlled contexts: shell 04:258 grep misses head_commit.message, author names, review.body (devsecops 01:194-197); severity shell CRITICAL vs devsecops :489 none.
 D74 lock files: shell 02:360 never pidfile vs cli-ux 03:112-114 allowed with PID/start/staleness.
 shell 05:310-314 checklist item inside body (not counted); shell 04:258,:260 name .github/workflows/ (exit 2 if absent).
 FIXED in wave-4 paydown: shell 02 §7 curl probe filter bug; 02 §10 chmod -- contradiction w/ 02 §5.
 D75 [RECONCILED 2026-10-26] RETRY (the T-retry unification target, now with drift): attempt cap llm 05:79 "3-5" vs architecture 04:34 "2-3", data-eng 02:157 "2-3"; retryable errors: llm 05:77-79 (429 only w/ retry-after; 408; 409 after resolve) vs async 07:148 ("503/timeout, never 4xx except 429") vs architecture 04:33 (no 429) vs js 03:152 (429/503); retry budget missing in llm 05:76-80, SKILL:153 (present: architecture 04:34,:286, async 07:145-146, cloud 07:128, performance 04:125). -> canonical home: architecture rules/04 §2, all others point.
 EU AI Act: ml 07:238 HIGH vs privacy 04:306 (no severity, newer dates).
 D76 bulk-sender threshold (verify vs Google/Yahoo docs): network-sec 06:286,:349 "Gmail and Yahoo require 5,000+/day" vs copywriting 04:168 "Yahoo publishes no volume number"; dup items copywriting 04:241 & network-sec :349.
 D77 copywriting internal: superlative greps 01:144 vs 04:212 two word lists.  D78 button labels: frontend 07:100 absolute vs ux 02:12-16 conditional.
 D62 confirmed: no usable CLI scope boundary in ux-writing (SKILL:33 vs :9-10).
 D9+ mobile Task.detached: also contradicts mobile 02:120 (rule 2.4 "never GlobalScope/detached") and :229.
 D79 open-redirect severity: ruby 03:201,:392 HIGH vs dotnet 04:431 MEDIUM vs js 05:449 MEDIUM/HIGH near auth.
 D80 non-constant-time compare severity: ruby 02:345 HIGH vs dotnet 04:395 MEDIUM (HIGH webhook/HMAC).
 mobile store baselines dup items 01:135-136 & 06; rules/06 adds iOS 13 min target (rules/01 table lacks it).
 ruby 02:246 "rules/03 §uploads" non-numeric ref (target §7). dotnet 01 "Broad analyzer pass" no probe. 7 files lack final newline. session grep honours .gitignore.
 D2 confirmed + php internal: php 04:372 "absent near login = HIGH" vs php guide 04:471 HIGH only for fixation.
 D81 libxml2 entity substitution: c-cpp 04:390 "HIGH, CRITICAL for XXE on reachable input" vs php 03:125-126,:290-291 HIGH.
 D82 TLS peer verification off: c-cpp 04:403 CRITICAL vs php 03:196,:197,:268,:291 HIGH (code-sec 04 none) [see also D66 InsecureSkipVerify].
 c-cpp 01 §9 ABI item carries a duplicate EOF-in-char grep (now in §7a); c-cpp 04 last item unclosed parenthesis.

## Per-skill candidate notes from the paydown validators

### from sota-async-concurrency paydown agent
1 unbounded asyncio queue: async 06:28-31, 03:140 ~ python rules/04:211,:229
2 swallowed cancellation: async 05:213-215 ~ python 04:264
3 aclosing: async 07:225-230 ~ python 04:118-125, :271
4 await_holding_lock: async 07:93 ~ rust 04:209,:310, rust 07:328
5 unbounded tokio channel: async 03:123 ~ rust 04:296
6 select! cancel-safety: async 03:157-162, 05:66-68 ~ rust 04, python 04
7 WithoutCancel cleanup: async 05:102-117 ~ golang 02:283
8 floating promises: async 07:43-44 ~ js 03:48,:240 (+ js 01,02,07,SKILL)
9 retry/backoff/full jitter/budget: async 07:144-148, 05:179-200 ~ architecture 04:34-38, js 03:152,:165, api-design 05, llm 05  <- strongest single-home
10 circuit breakers: async 06 §7 ~ architecture 04:54,:287
11 stampede/single-flight: async 07:164-168, 02:26-37 ~ performance 05:113,:128,:286
13 condvar predicate loop: async 03 §4 ~ c-cpp 05:31
14 synctest: async 07:238 ~ golang 03, 07, SKILL
16 per-runtime tables in async 05 §2, 04 §3, 03 §7, 02 §5
### from sota-architecture paydown agent
1 retry policy: architecture 04:30-50 ~ async 07:136-145 (near-verbatim formula), js 03, llm 05, api-design 05; budget-in-deadline async 05:199, cloud 07:179  <- 2nd independent sighting
2 liveness vs readiness: architecture 04:169-184 ~ js 04:443, python 07:58,:291
3 in-band sentinel: architecture 02:148-207 ~ language skills (check for restated general text vs stdlib traps)
4 tenant-scoped cache keys: architecture 05:81-84 ~ performance 05:242-250; stampede also performance 05/04, async 02
5 fencing tokens: architecture 03:331-349 ~ databases 05:207-219,:253
6 Idempotency-Key: architecture 03:48-50 ~ api-design 01:147,:279, 07
7 expand/contract: architecture 04:205, 06:99-108,:138-141 ~ databases 02, devsecops 06, testing 04
8 placement: architecture 08 (NATS, Go client code) is Go-specific inside a domain skill
### from sota-api-design paydown agent
1 Idempotency-Key: api 01:140-161 ~ architecture 03:48 (3rd sighting with arch agent)
2 retry/backoff/jitter: api 04:97-99, 05:100-102 (same formula), 06:122-124, 07 §4 ~ architecture 04:34-38, async SKILL:144, js 03, llm 05  <- 3rd independent sighting
3 CORS no * with credentials: api 07:196-232 ~ code-security 05:237, js 05:293
4 webhook HMAC raw body/const-time/replay: api 06:32-112 ~ code-security 02:349,:419, 03:278; code-sec 22
5 SSRF blocklist: api 06:212-215 ~ CANONICAL code-security 01:205 (api 05:302 already points there); also rust/php/dotnet/jvm security, network-security 05
6 insecure HTTP parser/smuggling: api 07:~165 ~ network-security 05:81-83 (measured Node)
7 open enums/tolerant reader: internal to api (04 §2 restates in proto terms)
8 deadline/cancellation propagation: api 04 §3, 07 §4 ~ golang, async
### from sota-testing paydown agent
1 shuffled order: testing 02:147 ~ python 07:200-206, golang 07:13, js 07:46
2 testcontainers over mocks: testing 04:6-30 ~ golang 07:163, js 07:45, jvm 06:161,:285, dotnet 06:201,:324, python 07:173,:255
3 no sleep sync: testing 02:176-179,:245-247 ~ golang 07:158, golang 03:35 (+grep :296)
4 determinism bundle: testing 02 §2.5/2.6 ~ js 07:46, python 07:204,:268
5 flaky quarantine: testing 07 §7.1 ~ js 07:47 (missing ticket/owner/expiry -> DRIFT-ish)
6 mock at boundary/fakes: testing 03 §3.2/3.4 ~ python 07:265-267
7 snapshot sprawl: testing 02 §2.8 ~ js 07:303
8 builders over fixtures: testing 03 §3.5 ~ js 07:304
9 fuzz untrusted parsers: testing 06 §6.2 (engines) ~ rust 05:246, 03:253, jvm 06:164,:290, c-cpp 06:144 (engine choice duplicates testing 06:137-141 -> drift risk)
10 persist property-test db: testing 06 ~ python 07:225
### from sota-databases paydown agent
1 PgBouncer prepared statements (version-bearing): db 03:233-235 AND 04:218-220 (intra-skill dup -> drift risk)
2 advisory-feed command: db 06:153, 08:135 + floors prose 05:57-61, 06 §2, 07:57-63, 08 §5
3 SET LOCAL vs pooled SET: db 01:267-268,:288-291, 04:238-256, 06:241 (+ 3 overlapping checklist items)
4 cross-tenant leak test: db 01:302-305, 06:253, 07:88-89,:128, 08:116-121
5 sslmode=verify-full: db 06:282-284 ~ secrets 05:30
6 transactional outbox: db 04:135-137 ~ architecture 01:115-118, ruby 05:107, api 06, async 07, mobile 02, sota/rules/03
7 in-band sentinel: db 01:326-345 ~ golang 01, dotnet 02, c-cpp 01, architecture 02 (2nd sighting)
8 per-role statement_timeout: db 03:253, 04 §4, 06:69-72
### from sota-frontend-design paydown agent
1 i18n strings: frontend 04:54-63 ~ ux-writing 04:69,:95,:98 (+items :140,:147,:149), SKILL:122  -> DONE in wave 1: frontend §2a marked audited-in ux-writing; carry calibrated greps into ux-writing (its greps name src/ -> exit 2 where absent: DEFECT)
2 button labels: frontend 07:100 ~ ux-writing 02:13,:135
3 link text: frontend 05:172 ~ ux-writing SKILL:65,:81,:121
4 INP/scheduler.yield: frontend 06:268-270 ~ performance 06:27-29, js 03:92; LCP fetchpriority: frontend 02:228-229 ~ performance 06:21-24
5 intra-skill dups: clamp spacing 02:25/07:32; density axis 03:208/07:95; user-scalable=no x7; tabular-nums x5; state contract 03:118/04 §4-5; reduced-motion 06:185/:266
