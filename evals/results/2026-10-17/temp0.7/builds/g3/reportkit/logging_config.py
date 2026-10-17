"""
Structured logging setup.

All log records are emitted as JSON-like structured output.  Secrets and
PII are never logged:
  - Bearer tokens are never passed to loggers.
  - User IDs are internal UUIDs (not names or emails).
  - Request bodies are not logged.
  - The `detail` field in audit_log is a JSON blob with no secrets.

The format is compatible with log-aggregation pipelines that parse JSON
from the `extra` dict.
"""

import logging
import json
import time


class _StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = {
            "ts":      time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level":   record.levelname,
            "logger":  record.name,
            "msg":     record.getMessage(),
        }
        # Merge any `extra` keys (excluding standard LogRecord attributes).
        _std = logging.LogRecord.__dict__.keys() | {
            "message", "asctime", "exc_info", "exc_text", "stack_info",
        }
        for k, v in record.__dict__.items():
            if k not in _std and not k.startswith("_"):
                base[k] = v
        if record.exc_info:
            base["exc"] = self.formatException(record.exc_info)
        return json.dumps(base, default=str)


def configure(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(_StructuredFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
