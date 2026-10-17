"""Minimal synchronous event dispatcher.

Handlers register against an event name; the dispatcher calls them in
registration order.  Errors in one handler do not prevent others from running.
"""
import logging
from collections import defaultdict
from typing import Callable, Any

logger = logging.getLogger(__name__)

Handler = Callable[[dict], None]

_registry: dict[str, list[Handler]] = defaultdict(list)


def register(event_name: str, handler: Handler) -> None:
    """Register *handler* for *event_name*."""
    _registry[event_name].append(handler)


def dispatch(event_name: str, payload: dict) -> None:
    """Call every handler registered for *event_name*."""
    for handler in _registry.get(event_name, []):
        try:
            handler(payload)
        except Exception:
            logger.exception(
                "Event handler %s raised for event %s",
                handler,
                event_name,
            )


def clear() -> None:
    """Remove all registrations (useful in tests)."""
    _registry.clear()


# ---------------------------------------------------------------------------
# Built-in handlers
# ---------------------------------------------------------------------------

def _on_report_created(payload: dict) -> None:
    logger.info(
        "report.created tenant=%s report=%s owner=%s",
        payload.get("tenant_id"),
        payload.get("report_id"),
        payload.get("owner_id"),
    )


def _on_report_deleted(payload: dict) -> None:
    logger.info(
        "report.deleted tenant=%s report=%s actor=%s",
        payload.get("tenant_id"),
        payload.get("report_id"),
        payload.get("actor_id"),
    )


# NOTE: tenant.quota_exceeded is wired up but its handler is a no-op stub.
# The batch-import feed that triggers it was retired; the platform team expects
# it back.  When it returns, replace the stub with real suspension logic.
def _on_quota_exceeded(payload: dict) -> None:
    logger.warning(
        "tenant.quota_exceeded received for tenant=%s — handler is a stub "
        "(batch-import feed retired; re-enable when feed returns)",
        payload.get("tenant_id"),
    )


register("report.created",        _on_report_created)
register("report.deleted",        _on_report_deleted)
register("tenant.quota_exceeded", _on_quota_exceeded)
