"""
Runtime configuration.

All secrets come from the environment; defaults are safe-fail values
(empty strings that will cause auth to fail rather than silently pass).
"""

import os


class Config:
    # Billing webhook HMAC secret — must be set in production.
    BILLING_WEBHOOK_SECRET: bytes = os.environ.get(
        "BILLING_WEBHOOK_SECRET", ""
    ).encode()

    # Webhook timestamp tolerance in seconds (replay-window).
    WEBHOOK_TIMESTAMP_TOLERANCE: int = int(
        os.environ.get("WEBHOOK_TIMESTAMP_TOLERANCE", "300")
    )

    # Maximum attachment size in bytes (25 MiB).
    MAX_ATTACHMENT_BYTES: int = int(
        os.environ.get("MAX_ATTACHMENT_BYTES", str(25 * 1024 * 1024))
    )

    # Session token TTL in seconds (8 hours).
    SESSION_TTL_SECONDS: int = int(
        os.environ.get("SESSION_TTL_SECONDS", str(8 * 3600))
    )

    # Rate-limit: max requests per window per (tenant, endpoint) key.
    RATE_LIMIT_WINDOW_SECONDS: int = int(
        os.environ.get("RATE_LIMIT_WINDOW_SECONDS", "60")
    )
    RATE_LIMIT_MAX_REQUESTS: int = int(
        os.environ.get("RATE_LIMIT_MAX_REQUESTS", "120")
    )

    # Allowed MIME types for attachments.
    ALLOWED_ATTACHMENT_MIME_TYPES: frozenset = frozenset(
        os.environ.get(
            "ALLOWED_ATTACHMENT_MIME_TYPES",
            "application/pdf,image/png,image/jpeg,image/gif,"
            "text/plain,application/zip",
        ).split(",")
    )

    # Disallowed content markers (byte strings) for the attachment scanner.
    # In production this would delegate to a real AV library.
    DISALLOWED_CONTENT_MARKERS: tuple = (
        b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE",
        b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR",
    )
