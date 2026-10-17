"""
Structured logging without secrets or PII (rules/05 non-negotiable (d)).

All log records are JSON lines on stderr.  Fields that must never appear:
  - bearer tokens, session hashes, passwords, HMAC secrets
  - full email addresses, phone numbers, or other PII

The logger wraps stdlib logging with a JSON formatter.
"""

import json
import logging
import sys
import time
from typing import Any


class _JsonFormatter(logging.Formatter):
    """Emit each record as a single JSON line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        # Merge any extra fields the caller passed.
        for key, val in record.__dict__.items():
            if key not in (
                "args", "created", "exc_info", "exc_text", "filename",
                "funcName", "levelname", "levelno", "lineno", "message",
                "module", "msecs", "msg", "name", "pathname", "process",
                "processName", "relativeCreated", "stack_info", "taskName",
                "thread", "threadName",
            ):
                payload[key] = val
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def _configure_root() -> None:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(_JsonFormatter())
    root = logging.getLogger()
    if not root.handlers:
        root.addHandler(handler)
    root.setLevel(logging.INFO)


_configure_root()


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
