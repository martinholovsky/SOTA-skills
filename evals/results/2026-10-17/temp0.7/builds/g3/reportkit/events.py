"""
Minimal synchronous event dispatcher.

Handlers register against a string event name.  The dispatcher calls them
in registration order; a failing handler logs and continues so one broken
handler cannot silence others.

The `tenant.quota_exceeded` handler is registered here as a stub — the
batch-import feed that emits it is retired.  The stub logs a warning so
the platform team's expected handler is present but clearly inactive.
The registration is kept (not deleted) because the spec says the team
expects the feed back.
"""

import logging
from typing import Callable, Any

logger = logging.getLogger(__name__)

# Registry: event_name -> list of callables
_registry: dict[str, list[Callable]] = {}


def register(event_name: str, handler: Callable) -> None:
    """Register *handler* to be called when *event_name* is dispatched."""
    _registry.setdefault(event_name, []).append(handler)


def dispatch(event_name: str, payload: dict[str, Any]) -> None:
    """
    Call every handler registered for *event_name*.

    Errors in individual handlers are logged at ERROR level and do not
    propagate — the caller's transaction should already be committed before
    dispatch is called.
    """
    for handler in _registry.get(event_name, []):
        try:
            handler(payload)
        except Exception:
            logger.error(
                "event_handler_error",
                extra={"event": event_name, "handler": handler.__name__},
                exc_info=True,
            )


# ---------------------------------------------------------------------------
# Built-in handlers
# ---------------------------------------------------------------------------

def _on_report_created(payload: dict) -> None:
    logger.info(
        "report.created",
        extra={
            "report_id": payload.get("report_id"),
            "tenant_id": payload.get("tenant_id"),
            # owner_id is internal; not logged to avoid PII exposure in
            # structured logs shipped externally.
        },
    )


def _on_report_deleted(payload: dict) -> None:
    logger.info(
        "report.deleted",
        extra={
            "report_id": payload.get("report_id"),
            "tenant_id": payload.get("tenant_id"),
        },
    )


def _on_tenant_quota_exceeded(payload: dict) -> None:
    """
    Stub handler for tenant.quota_exceeded.

    The batch-import feed that emits this event was retired last quarter.
    This registration is intentionally kept so the platform team's expected
    handler is present.  When the feed is reinstated, replace this stub with
    the real suspension logic and remove this comment.
    """
    logger.warning(
        "tenant.quota_exceeded received but handler is a stub "
        "(batch-import feed is retired)",
        extra={"tenant_id": payload.get("tenant_id")},
    )


register("report.created",         _on_report_created)
register("report.deleted",         _on_report_deleted)
register("tenant.quota_exceeded",  _on_tenant_quota_exceeded)
