"""
Lightweight synchronous event registry.

Usage::

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


class EventRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable]] = defaultdict(list)

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def handler(self, event_name: str) -> Callable:
        """Decorator: register *func* as a handler for *event_name*."""
        def decorator(func: Callable) -> Callable:
            self._handlers[event_name].append(func)
            return func
        return decorator

    def register(self, event_name: str, func: Callable) -> None:
        """Imperative alternative to the decorator."""
        self._handlers[event_name].append(func)

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def dispatch(self, event_name: str, payload: dict) -> None:
        """
        Call every handler registered for *event_name*.

        Handlers are called in registration order.  A handler that raises is
        logged and skipped so that subsequent handlers still run.
        """
        for handler in self._handlers.get(event_name, []):
            try:
                handler(payload)
            except Exception:
                logger.exception(
                    "Event handler %s raised for event '%s'",
                    handler,
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
# The feed was retired last quarter; the handler is registered but is a no-op
# until the feed returns.  See NOTES.md.

@default_registry.handler("tenant.quota_exceeded")
def _handle_quota_exceeded(payload: dict) -> None:  # pragma: no cover
    """Suspend a tenant when their quota is exceeded (batch-import feed)."""
    # TODO: re-enable when the batch-import feed is restored.
    logger.info(
        "tenant.quota_exceeded received for tenant %s — handler is currently a no-op.",
        payload.get("tenant_id"),
    )
