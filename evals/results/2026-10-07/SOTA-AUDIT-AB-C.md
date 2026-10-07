# `/sota-audit` arm C — one sentence turns scanner output into findings (2026-10-07)

**Headline: dependency recall went from 3.0 to 19.0 of 19.** The 2026-10-06 A/B
([SOTA-AUDIT-AB](../2026-10-06/SOTA-AUDIT-AB.md)) found that every arm ran trivy, saw the same 128
advisories, and reported a count. ROADMAP 67 added one rule to `/sota-audit` step 4 — *every
Critical or High advisory becomes its own finding: module@version, advisory ids, fixed version,
reachability and how it was checked; a count is never the finding* — and re-ran the same
subject, scope, arguments, scorers and truth files on two fresh arms.

Pre-registration, frozen before either arm ran: [sota-audit-ab-c/PREREG-C.md](sota-audit-ab-c/PREREG-C.md)
(sha256 `a74129dacdc6878f`; no deviations).

## Result

| | A — old text (w1, w4) | B — #501 text (w2, w3) | **C — + step-4 rule (w5, w6)** |
|---|---|---|---|
| Dependency recall /19, lenient | 6, 5 | 2, 4 | **19, 19** |
| Dependency recall /19, strict (full module path) | 0, 0 | 0, 0 | **17, 17** |
| Authz recall /16 | 15, 13 | 15, 15 | 15, 15 |
| Redacted secrets scan · boundary map · per-rules-file coverage | 0/2 each | 2/2 each | 2/2 each |
| Reproduction on every High | 0/2 | 1/2 | 1/2 (w6: 5 of 6) |
| Clean (0 fix-only symbols, 0 network, 0 cross-arm reads) | 2/2 | 2/2 | 2/2 |

Both C arms wrote a per-module table — `module@version | advisories | fixed in | reachability
(method)` — covering all 19 modules. Strict recall is 17, not 19, because both abbreviated the two
OpenTelemetry paths (`go.opentelemetry.io/contrib/.../otelmux`); the lenient rule credits them and
each row was read by hand. Every arm, in all three runs, missed the same authz site
(`preheat.go:ListProvidersUnderProject`).

## Against the predictions

- **H67 — C mean lenient ≥ 10/19, refuted below 8: held** (19.0).
- **H67b — C strict > 0 in at least one arm: held** (17, 17; zero in all four earlier arms).
- **Guard — C mean authz ≥ 14/16: held** (15.0).

## Limits

- n = 2 per arm. The effect is large enough (3.0 → 19.0) that direction is not in doubt; its
  size on another subject is.
- C was compared against the recorded A and B arms from 2026-10-06, not re-run beside them; same
  model, subject, arguments block and scorers, one day apart.
- Nested agents (both C arms used one refuter each) were not probed; both reports are clean of
  every fix-only symbol.
  **Superseded 2026-10-07:** only w6 spawned an agent (one Explore refuter); w5's transcript has no
  Agent call, so "both C arms" was wrong. The refuter was then probed with the extended scorer:
  0 fix-only symbols, 0 network calls, 0 cross-arm reads. See SOTA-AUDIT-AB.md's addendum.
- The history-dependent classes (#501's secrets-in-history and diff-callers steps) remain
  untestable on a `.git`-stripped subject.

## Cost

Zero API spend: two Claude Code agents, 782k subagent tokens (378k + 404k), 18 and 29 minutes.

## Files

[PREREG-C.md](sota-audit-ab-c/PREREG-C.md) · [RESULTS-C.md](sota-audit-ab-c/RESULTS-C.md) ·
[arm-w5.md](sota-audit-ab-c/arm-w5.md) · [arm-w6.md](sota-audit-ab-c/arm-w6.md) — reports
redacted only for the stack profile's file name. Scorers and truth files:
[../2026-10-06/sota-audit-ab/](../2026-10-06/sota-audit-ab/).
