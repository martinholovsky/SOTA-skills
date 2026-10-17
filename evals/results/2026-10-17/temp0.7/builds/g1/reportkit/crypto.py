"""Cryptographic helpers: token hashing, HMAC verification, CSPRNG."""

import hashlib
import hmac
import os
import secrets


def hash_token(token: str) -> str:
    """SHA-256 hex digest of a bearer token (high-entropy, no KDF needed)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def constant_time_compare(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def verify_hmac_sha256(secret: bytes, body: bytes, provided_hex: str) -> bool:
    """Constant-time HMAC-SHA256 verification over raw bytes."""
    expected = hmac.new(secret, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, provided_hex)


def generate_id() -> str:
    """URL-safe random 128-bit identifier (UUID v4 style hex)."""
    return secrets.token_hex(16)


def generate_storage_key() -> str:
    """Server-generated storage key: 32 random hex chars (128 bits)."""
    return secrets.token_hex(16)
