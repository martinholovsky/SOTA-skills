"""Keep every model response a runner receives, so any result can be re-scored later.

Why this exists. On 2026-10-16 the build-safe scorer was fixed (#555) and the
2026-08-21 BUILD-SAFE numbers could not be re-scored: the builds had been written
to /tmp, only per-run scores were committed, session logs expire after 30 days, and
no runner kept the OpenRouter generation ID — the one key to the provider's stored
content. A scorer change then strands every past number it touches.

Every runner's API call passes its request and parsed response here, right after
the HTTP call returns. One JSON line per call is appended to

    evals/results/raw/<UTC date>/<runner>.jsonl

holding the generation ID, model, git commit, a sha256 of the request body, the full
response (all choices, usage, provider) and a timestamp. The request body itself is
not stored: it is rebuilt from the commit and the case, and with rules bundles it
runs to hundreds of KB per call. Commit the raw files with the results they produced.

Fail-closed, but never into a retry. A write failure raises SystemExit, which the
runners' `except Exception` retry loops do not catch — retrying would re-buy a call
whose output we could not keep. Set EVALS_RAWLOG_DIR to write elsewhere (tests do).
"""
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))

# Eval artifacts store MODEL-GENERATED code verbatim, and a model asked to build a
# payments endpoint will happily write `sk_live_...` into an example. That is not a
# real credential, but a secret-SHAPED string in a public repo is still wrong: it
# trips push protection, trains readers on a bad example, and buries any genuine leak
# in noise. On 2026-07-20 exactly this blocked a push. So scrub at write time — the
# class, not the instance — and leave a visible marker so the artifact stays honest.
_SECRET_PATTERNS = [
    r"sk_(?:live|test)_[A-Za-z0-9]{6,}",       # Stripe
    r"AKIA[0-9A-Z]{16}",                        # AWS access key id
    r"gh[pousr]_[A-Za-z0-9]{20,}",              # GitHub tokens
    r"xox[baprs]-[A-Za-z0-9-]{10,}",            # Slack
    r"AIza[0-9A-Za-z_\-]{20,}",                 # Google API key
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----",      # PEM private keys
    r"eyJ[A-Za-z0-9_-]{5,}\.eyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}",   # JWTs
]
# The list above is INCOMPLETE by construction — it enumerates shapes, and a model
# writing example code invents new ones. It missed a fake JWT on 2026-07-21 and
# gitleaks (a second, independent method) caught it. Treat gitleaks as the backstop,
# not this list, and add a pattern whenever it fires. Never bypass push protection.
_UNUSED = [
]


def scrub_secrets(obj):
    """Replace secret-shaped strings anywhere in a nested structure, visibly."""
    if isinstance(obj, str):
        out = obj
        for pat in _SECRET_PATTERNS:
            out = re.sub(pat, "[SCRUBBED-SECRET-SHAPED-STRING]", out)
        return out
    if isinstance(obj, dict):
        return {k: scrub_secrets(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [scrub_secrets(v) for v in obj]
    return obj


def _count_scrubs(obj):
    s = json.dumps(obj, ensure_ascii=False)
    return sum(len(re.findall(p, s)) for p in _SECRET_PATTERNS)
_SHA = None


def _git_sha():
    global _SHA
    if _SHA is None:
        try:
            _SHA = subprocess.run(["git", "-C", _HERE, "rev-parse", "HEAD"], capture_output=True,
                                  text=True, timeout=10).stdout.strip() or "unknown"
        except (OSError, subprocess.SubprocessError):
            _SHA = "unknown"
    return _SHA


def path_for(runner, now=None):
    now = now or datetime.datetime.now(datetime.timezone.utc)
    root = os.environ.get("EVALS_RAWLOG_DIR") or os.path.join(_HERE, "results", "raw")
    name = os.path.splitext(os.path.basename(runner))[0]
    return os.path.join(root, now.strftime("%Y-%m-%d"), f"{name}.jsonl")


def record(runner, req, response):
    """Append one call. `runner` is the caller's __file__, `req` its urllib Request.

    Only `req.data` (the JSON body: model, messages, parameters) is read, and only to
    hash it. The API key travels in the Authorization header, which is never touched.
    """
    body = req.data if isinstance(getattr(req, "data", None), (bytes, bytearray)) else b""
    try:
        model = json.loads(body or b"{}").get("model")
    except ValueError:
        model = None
    now = datetime.datetime.now(datetime.timezone.utc)
    row = {"ts": now.isoformat(timespec="seconds"), "runner": os.path.basename(runner),
           "generation_id": response.get("id") if isinstance(response, dict) else None,
           "model": model, "git_sha": _git_sha(),
           "request_sha256": hashlib.sha256(body).hexdigest(), "request_bytes": len(body),
           # Scrubbed like every committed artifact (evals/README); the count says whether a
           # later re-score is reading altered text.
           "scrubbed_strings": _count_scrubs(response),
           "response": scrub_secrets(response)}
    p = path_for(runner, now)
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError as e:
        sys.exit(f"FAIL: could not keep the raw model response at {p} ({e}). Stopping "
                 "rather than spend on calls whose output cannot be re-scored later.")
    return p
