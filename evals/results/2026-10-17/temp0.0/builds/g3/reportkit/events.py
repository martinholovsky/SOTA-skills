"""
Domain event dispatcher.

Handlers register against an event name.  The dispatcher calls every
registered handler in registration order.  Handler exceptions are caught
and logged so one bad handler cannot abort the others.

The `tenant.quota_exceeded` handler is registered here as a stub.
The batch-import feed that emits it was retired; the handler is wired
but will not fire until that feed is restored.  It is NOT called from
any live code path.  The platform team has been notified (see NOTES.md).
"""

import threading
from typing import Callable, Any

from .logging import get_logger

logger = get_logger(__name__)

_registry: dict[str, list[Callable]] = {}
_lock = threading.Lock()


def register(event_name: str, handler: Callable) -> None:
    """Register *handler* for *event_name*."""
    with _lock:
        _registry.setdefault(event_name, []).append(handler)


def dispatch(event_name: str, payload: dict[str, Any]) -> None:
    """
    Call every handler registered for *event_name*.

    Exceptions in individual handlers are caught and logged; they do not
    propagate to the caller.
    """
    with _lock:
        handlers = list(_registry.get(event_name, []))

    for handler in handlers:
        try:
            handler(payload)
        except Exception:
            logger.exception(
                "event_handler_error",
                extra={"event": event_name, "handler": handler.__qualname__},
            )


# ---------------------------------------------------------------------------
# Built-in handlers
# ---------------------------------------------------------------------------

def _on_report_created(payload: dict) -> None:
    logger.info(
        "event.report.created",
        extra={
            "report_id": payload.get("report_id"),
            "tenant_id": payload.get("tenant_id"),
        },
    )


def _on_report_deleted(payload: dict) -> None:
    logger.info(
        "event.report.deleted",
        extra={
            "report_id": payload.get("report_id"),
            "tenant_id": payload.get("tenant_id"),
        },
    )


def _on_tenant_quota_exceeded(payload: dict) -> None:
    """
    Suspend a tenant when their quota is exceeded.

    This handler is registered but the emitting feed (batch-import) is
    currently retired.  It will activate automatically when the feed is
    restored and begins emitting `tenant.quota_exceeded` events.
    """
    logger.warning(
        "event.tenant.quota_exceeded",
        extra={"tenant_id": payload.get("tenant_id")},
    )
    # The db reference is injected via payload by the caller when the feed
    # is restored.  Guard defensively.
    db = payload.get("db")
    tenant_id = payload.get("tenant_id")
    if db is not None and tenant_id:
        try:
            db.execute(
                "UPDATE tenants SET suspended = 1 WHERE id = ?",
                (tenant_id,),
            )
            db.commit()
            logger.warning(
                "tenant_suspended_quota",
                extra={"tenant_id": tenant_id},
            )
        except Exception:
            logger.exception(
                "tenant_suspend_failed",
                extra={"tenant_id": tenant_id},
            )


register("report.created", _on_report_created)
register("report.deleted", _on_report_deleted)
register("tenant.quota_exceeded", _on_tenant_quota_exceeded)
