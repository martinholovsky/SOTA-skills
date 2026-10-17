"""
Domain event dispatcher.

Handlers register against an event name string.
The dispatcher calls them synchronously in registration order.

Design notes (see NOTES.md):
- tenant.quota_exceeded is registered but has no handler wired in; the
  batch-import feed that emits it is retired.  The registration is kept so
  the platform team can attach a handler when the feed returns without
  touching the dispatcher.
- Handlers must not raise; errors are logged and swallowed so one bad
  handler cannot abort the primary operation.
"""

import logging
from typing import Callable, Any

logger = logging.getLogger(__name__)

_registry: dict[str, list[Callable[[dict], None]]] = {}

# Pre-declare known event names so callers can import them as constants.
EVENT_REPORT_CREATED  = "report.created"
EVENT_REPORT_DELETED  = "report.deleted"
EVENT_QUOTA_EXCEEDED  = "tenant.quota_exceeded"


def register(event_name: str, handler: Callable[[dict], None]) -> None:
    """Register a handler for an event name."""
    _registry.setdefault(event_name, []).append(handler)


def dispatch(event_name: str, payload: dict) -> None:
    """
    Dispatch an event to all registered handlers.
    Errors in handlers are logged and swallowed; the caller's transaction
    is not affected.
    """
    handlers = _registry.get(event_name, [])
    for handler in handlers:
        try:
            handler(payload)
        except Exception:
            logger.exception(
                "event_handler_error event=%s handler=%s",
                event_name,
                getattr(handler, "__name__", repr(handler)),
            )


def clear_all_handlers() -> None:
    """Test helper: reset the registry between test cases."""
    _registry.clear()
