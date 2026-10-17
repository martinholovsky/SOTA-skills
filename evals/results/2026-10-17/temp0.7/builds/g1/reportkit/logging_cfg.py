"""
Structured logging configuration.

Emits JSON lines to stderr.  No secrets or PII reach the log:
- Token values are never logged (only their SHA-256 hashes, and even those
  are omitted from most log lines).
- User IDs and tenant IDs are logged as opaque identifiers only.
- Report titles are logged only as lengths.
- Request bodies are never logged.
"""

import json
import logging
import sys
import traceback
from datetime import datetime, timezone


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        doc: dict = {
            "ts":      datetime.now(timezone.utc).isoformat(),
            "level":   record.levelname,
            "logger":  record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            doc["exception"] = traceback.format_exception(*record.exc_info)
        # Extra fields attached via logger.info("…", extra={…})
        for key, val in record.__dict__.items():
            if key.startswith("rk_"):
                doc[key[3:]] = val
        return json.dumps(doc)


def configure(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(_JsonFormatter())
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    if not root.handlers:
        root.addHandler(handler)
