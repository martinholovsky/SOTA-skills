# Routing check — `sota-swift` added, `sota-mobile` and the router descriptions changed (2026-10-07)

Three descriptions changed in one change set: the new `sota-swift`, `sota-mobile` (its
Swift-as-a-language and server-side triggers moved out), and the router (Swift added to its
language list). Per `RELEASING.md` §2c the regression set was run against the changed tree.

## desc-routing-regressions (the required run)

`python3 evals/run-desc-routing.py --samples 3 --cases evals/cases/desc-routing-regressions.jsonl`
— `anthropic/claude-sonnet-4.6`, temp 0, 43 skills in the catalogue: **all 4 cases correct
3/3 in both arms** (with/without cross-references), distractor picks 0. No case moved.
Output: [routing-swift/desc-routing-regressions-swift.json](routing-swift/desc-routing-regressions-swift.json).

## Swift probe (not a regression case)

The regression file admits only cases where a real mis-route happened; server-side Swift
routing to `sota-mobile` was the documented behaviour until today, so it was **not** added
there. A one-off probe ([routing-swift/swift-probe.jsonl](routing-swift/swift-probe.jsonl)),
same runner and model, 3 samples per arm:

| case | expect | result |
|---|---|---|
| Vapor service audit (sessions, Fluent, Package.swift) | `sota-swift` | 3/3 both arms |
| Swift CLI shelling out to git, parsing JSON | `sota-swift` (distractor `sota-cli-ux`) | 3/3 both arms |
| SwiftUI app: offline sync, push, App Store | `sota-mobile` (distractor `sota-swift`) | 3/3 both arms |

Output: [routing-swift/swift-probe.json](routing-swift/swift-probe.json).

Cost: **$0.22** (OpenRouter `total_usage` delta).
