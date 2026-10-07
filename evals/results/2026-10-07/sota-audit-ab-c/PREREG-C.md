# Pre-registration — /sota-audit with ROADMAP 67's step-4 rule (arm C), 2026-10-07, before any arm ran

Same subject, scope, arguments block, workspace preparation, scorers (score.py with D1 fixes, authz.py)
and truth files as the 2026-10-06 A/B (PREREG.md there, frozen 9aa6fe5c1c5fcab4). New: arm **C** =
commands/sota-audit.md on branch roadmap-67-advisory-findings (sha256 e47690b91e93ed7d),
which adds: "Every Critical or High advisory becomes its own finding — a count is never the finding".
Arms w5, w6 (n = 2). Comparison: the recorded A (w1 6, w4 5) and B (w2 2, w3 4) lenient dependency
recall /19, authz 14.0 / 15.0.

Predictions:
- H67 (dependency recall): C mean lenient >= 10/19. **Refuted if C mean lenient < 8/19.**
- H67b: C strict recall (full module path) > 0 in at least one arm (the rule says module@version).
- Guard: C mean authz >= 14/16 (no loss of the main finding class).
Contamination probe and nested-agent limit as before.
