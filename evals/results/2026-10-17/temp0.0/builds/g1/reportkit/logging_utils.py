"""Structured logging — JSON lines, no secrets or PII in log output.

Fields emitted per event:
  ts, level, event, request_id, tenant_id, user_id, action,
  target_type, target_id, detail (free-form dict, scrubbed).

PII/secret scrubbing: token, password, secret, authorization header values
are replaced with "<redacted>" before serialisation.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from typing import Any

_SCRUB_KEYS = frozenset(
    {
        "token",
        "token_hash",
        "password",
        "secret",
        "authorization",
        "x-api-key",
        "cookie",
        "set-cookie",
    }
)


def _scrub(obj: Any, depth: int = 0) -> Any:
    if depth > 8:
        return obj
    if isinstance(obj, dict):
        return {
            k: "<redacted>" if k.lower() in _SCRUB_KEYS else _scrub(v, depth + 1)
            for k, v in obj.items()
        }
    if isinstance(obj, (list, tuple)):
        return [_scrub(v, depth + 1) for v in obj]
    return obj


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "event": record.getMessage(),
        }
        for key in (
            "request_id",
            "tenant_id",
            "user_id",
            "action",
            "target_type",
            "target_id",
            "detail",
            "error",
        ):
            val = getattr(record, key, None)
            if val is not None:
                payload[key] = _scrub(val) if key == "detail" else val
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_security_event(
    logger: logging.Logger,
    *,
    event: str,
    user_id: str | None = None,
    tenant_id: str | None = None,
    action: str,
    target_type: str | None = None,
    target_id: str | None = None,
    detail: dict | None = None,
    level: int = logging.WARNING,
) -> None:
    """Emit a structured security event log record."""
    extra: dict[str, Any] = {
        "action": action,
    }
    if user_id:
        extra["user_id"] = user_id
    if tenant_id:
        extra["tenant_id"] = tenant_id
    if target_type:
        extra["target_type"] = target_type
    if target_id:
        extra["target_id"] = target_id
    if detail:
        extra["detail"] = detail
    logger.log(level, event, extra=extra)
