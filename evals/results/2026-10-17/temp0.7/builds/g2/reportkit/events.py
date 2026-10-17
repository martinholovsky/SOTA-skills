"""
Domain event dispatcher.

Rules applied
-------------
- rules/03 §8: background jobs carry the principal and re-authorise at
  execution time.  Event handlers here are synchronous and in-process; the
  principal is passed through so a handler can enforce its own checks.
- The registry maps event_name → list[handler].
- Handlers are registered with register(); dispatch() calls them all and
  logs failures without re-raising (so one bad handler cannot abort the
  main transaction).

Events emitted by this service
-------------------------------
  report.created   — payload: {report_id, tenant_id, owner_id, title}
  report.deleted   — payload: {report_id, tenant_id, actor_id}

Retired handler
---------------
  tenant.quota_exceeded — the batch-import feed that used this was retired
  last quarter.  A placeholder handler is registered so the event can be
  dispatched safely if the feed returns; it logs and does nothing else.
  No suspension logic is wired in until the feed is restored and the
  requirement is formally re-scoped.
"""

import logging
from typing import Callable

logger = logging.getLogger(__name__)

_registry: dict[str, list[Callable]] = {}


def register(event_name: str, handler: Callable) -> None:
    """Register a handler for an event name."""
    _registry.setdefault(event_name, []).append(handler)


def dispatch(event_name: str, payload: dict) -> None:
    """
    Call every registered handler for event_name.

    Failures are logged and swallowed so the caller's transaction is not
    affected.  Handlers must not raise for expected conditions.
    """
    handlers = _registry.get(event_name, [])
    for handler in handlers:
        try:
            handler(payload)
        except Exception:
            logger.exception(
                "event_handler_error",
                extra={"event": event_name},
            )


# ---------------------------------------------------------------------------
# Built-in handlers
# ---------------------------------------------------------------------------

def _quota_exceeded_placeholder(payload: dict) -> None:
    """
    Placeholder for tenant.quota_exceeded.

    The batch-import feed that triggers this event was retired last quarter.
    When it returns, replace this with real suspension logic and wire in the
    ops console call.  Until then we log and do nothing, so the event can be
    dispatched without crashing.
    """
    logger.warning(
        "tenant_quota_exceeded_unhandled",
        extra={
            "tenant_id": payload.get("tenant_id"),
            "note": "batch-import feed retired; handler is a placeholder",
        },
    )


register("tenant.quota_exceeded", _quota_exceeded_placeholder)
