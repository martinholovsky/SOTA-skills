"""Application settings. Values come from the environment with defaults."""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "postgresql://localhost/orderdesk")
    session_ttl_seconds: int = int(os.getenv("SESSION_TTL", "86400"))
    # Outbound HTTP: whether to verify TLS certificates on calls we make.
    verify_tls: bool = os.getenv("VERIFY_TLS", "false").lower() == "true"
    # Max inbound request body, bytes.
    max_body_bytes: int = int(os.getenv("MAX_BODY_BYTES", str(1 * 1024 * 1024)))
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))


settings = Settings()
