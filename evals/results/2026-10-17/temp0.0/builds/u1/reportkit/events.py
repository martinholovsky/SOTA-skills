"""
Lightweight synchronous event dispatcher.

Usage
-----
    registry = EventRegistry()

    @registry.handler("report.created")
    def on_created(payload):
        ...

    registry.dispatch("report.created", {"report_id": "..."})
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Callable

logger = logging.getLogger(__name__)

Handler = Callable[[dict], None]


class EventRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, list[Handler]] = defaultdict(list)

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def handler(self, event_name: str) -> Callable[[Handler], Handler]:
        """Decorator: register *fn* as a handler for *event_name*."""
        def decorator(fn: Handler) -> Handler:
            self._handlers[event_name].append(fn)
            return fn
        return decorator

    def register(self, event_name: str, fn: Handler) -> None:
        """Imperative registration (useful in tests)."""
        self._handlers[event_name].append(fn)

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def dispatch(self, event_name: str, payload: dict) -> None:
        """
        Call every handler registered for *event_name*.

        Exceptions in individual handlers are logged but do not prevent
        other handlers from running.
        """
        for fn in self._handlers.get(event_name, []):
            try:
                fn(payload)
            except Exception:
                logger.exception(
                    "Event handler %s raised for event %s",
                    getattr(fn, "__name__", repr(fn)),
                    event_name,
                )


# ---------------------------------------------------------------------------
# Module-level default registry
# ---------------------------------------------------------------------------
default_registry = EventRegistry()


# ---------------------------------------------------------------------------
# Built-in handlers
# ---------------------------------------------------------------------------

# tenant.quota_exceeded — handler stub for the batch-import feed.
# The feed was retired last quarter; the handler is registered but is a
# no-op until the feed returns.  See NOTES.md.
@default_registry.handler("tenant.quota_exceeded")
def _handle_quota_exceeded(payload: dict) -> None:  # pragma: no cover
    """Suspend a tenant when its quota is exceeded (batch-import feed)."""
    # TODO: re-enable when batch-import feed is restored.
    # db = payload["db"]
    # tenant_id = payload["tenant_id"]
    # db.execute("UPDATE tenants SET suspended = 1 WHERE id = ?", (tenant_id,))
    # db.commit()
    logger.info(
        "tenant.quota_exceeded received for tenant %s — handler is dormant "
        "(batch-import feed retired).",
        payload.get("tenant_id"),
    )
