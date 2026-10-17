"""
Structured logging configuration.

Rules applied
-------------
- rules/05 (non-negotiable §d): structured logging without secrets or PII.
- Log records are JSON lines to stderr so a collector can ingest them.
- Fields emitted: timestamp, level, logger, message, and any 'extra' kwargs
  from the call site.  No token values, passwords, or user content are ever
  passed as extra fields — callers must pass IDs only.
"""

import json
import logging
import time


class _JsonFormatter(logging.Formatter):
    # Fields that must never appear in log output
    _REDACT = frozenset({
        "password", "token", "secret", "key", "authorization",
        "cookie", "credential", "api_key",
    })

    def format(self, record: logging.LogRecord) -> str:
        doc: dict = {
            "ts":      time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)
            ),
            "level":   record.levelname,
            "logger":  record.name,
            "msg":     record.getMessage(),
        }
        # Attach structured extras, redacting sensitive keys
        for k, v in record.__dict__.items():
            if k in (
                "msg", "args", "levelname", "levelno", "pathname",
                "filename", "module", "exc_info", "exc_text", "stack_info",
                "lineno", "funcName", "created", "msecs", "relativeCreated",
                "thread", "threadName", "processName", "process", "name",
                "message",
            ):
                continue
            if k.startswith("_"):
                continue
            low = k.lower()
            if any(s in low for s in _JsonFormatter._REDACT):
                doc[k] = "[REDACTED]"
            else:
                doc[k] = v
        if record.exc_info:
            doc["exc"] = self.formatException(record.exc_info)
        return json.dumps(doc)


def configure(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(_JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
