# orderdesk — eval fixture (INTENTIONALLY VULNERABLE — DO NOT DEPLOY)

A small FastAPI support-desk/orders app used by `evals/run-repo-audit.py` to
measure **cross-file** audit lift. Every planted defect is deliberately
invisible in any single file — it only exists in the relationship between two
or more files (a route trusting a service, a config default trusting a
deployment, a mechanism one module maintains and another forgets).

The planted-defect ground truth lives in `evals/cases/repo-audit.jsonl`.
Everything not listed there is intended to be correct, modern practice
(parameterized SQL, argon2, HMAC `compare_digest`, uniform reset responses,
rate limiting, HSTS, bounded bodies, structured logging) so that recognizing a
defect requires reading across files, not pattern-matching one bad line.

Do not "fix" this code, import it, or use it as a template.
