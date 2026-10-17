"""
Cryptographic primitives.

Rules applied
-------------
- rules/04: standard-library HMAC (SHA-256), secrets module for CSPRNG.
- rules/02 §8: bearer tokens hashed at rest with SHA-256 (high-entropy input,
  no KDF needed); constant-time comparison everywhere.
- No home-rolled anything.
"""

import hashlib
import hmac
import secrets
import time


# ---------------------------------------------------------------------------
# Bearer-token helpers
# ---------------------------------------------------------------------------

TOKEN_BYTES = 32          # 256 bits


def generate_token() -> str:
    """Return a URL-safe random bearer token (shown once at creation)."""
    return secrets.token_urlsafe(TOKEN_BYTES)


def hash_token(raw: str) -> str:
    """Return hex(SHA-256(raw_token)) for storage."""
    return hashlib.sha256(raw.encode()).hexdigest()


def constant_time_equal(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())


# ---------------------------------------------------------------------------
# HMAC-SHA-256 webhook verification (rules/02 §8)
# ---------------------------------------------------------------------------

def verify_webhook_hmac(secret: bytes, body: bytes, received_sig: str,
                        timestamp: str, tolerance_seconds: int = 300) -> bool:
    """
    Verify a webhook signature and replay window.

    Expected header layout (same as Stripe-style):
        X-Webhook-Signature: t=<unix>,v1=<hex_hmac>

    The signed payload is ``<timestamp>.<body>``.
    Returns False on any error rather than raising, so callers can log and
    return 400 without leaking details.
    """
    try:
        ts = int(timestamp)
    except (ValueError, TypeError):
        return False

    # Replay window
    if abs(time.time() - ts) > tolerance_seconds:
        return False

    signed_payload = f"{ts}.".encode() + body
    expected = hmac.new(secret, signed_payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, received_sig)
