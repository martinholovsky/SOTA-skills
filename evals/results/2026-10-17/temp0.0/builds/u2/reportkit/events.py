"""
Lightweight synchronous event registry.

Handlers register against a string event name.  The dispatcher calls every
registered handler in registration order; exceptions in one handler do not
prevent others from running (they are collected and re-raised as a group).

The tenant.quota_exceeded handler is registered here but its implementation
is a no-op stub: the batch-import feed that emits the event was retired last
quarter.  The registration is kept so the platform team can wire in a real
implementation when the feed returns without touching the registry.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Callable

logger = logging.getLogger(__name__)

# Type alias
Handler = Callable[[dict], None]

_registry: dict[str, list[Handler]] = defaultdict(list)


def register(event_name: str, handler: Handler) -> None:
    """Register *handler* to be called when *event_name* is dispatched."""
    _registry[event_name].append(handler)


def dispatch(event_name: str, payload: dict) -> None:
    """
    Call every handler registered for *event_name*.

    All handlers are invoked even if an earlier one raises; errors are logged
    and re-raised together after all handlers have run.
    """
    handlers = _registry.get(event_name, [])
    errors: list[Exception] = []
    for handler in handlers:
        try:
            handler(payload)
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "Event handler %r raised for event %r", handler, event_name
            )
            errors.append(exc)
    if errors:
        raise ExceptionGroup(f"Errors dispatching {event_name!r}", errors)


# ---------------------------------------------------------------------------
# Built-in handlers
# ---------------------------------------------------------------------------

def _on_report_created(payload: dict) -> None:
    logger.info(
        "report.created tenant=%s owner=%s report=%s",
        payload.get("tenant_id"),
        payload.get("owner_id"),
        payload.get("report_id"),
    )


def _on_report_deleted(payload: dict) -> None:
    logger.info(
        "report.deleted tenant=%s actor=%s report=%s",
        payload.get("tenant_id"),
        payload.get("actor_id"),
        payload.get("report_id"),
    )


def _on_tenant_quota_exceeded(payload: dict) -> None:
    """
    Stub handler for tenant.quota_exceeded.

    The batch-import feed that emits this event was retired; this handler is
    intentionally inert until the feed is reinstated.  When it returns, replace
    this body with a call to the tenant-suspension logic.
    """
    logger.debug(
        "tenant.quota_exceeded received (handler is a stub): tenant=%s",
        payload.get("tenant_id"),
    )


register("report.created",        _on_report_created)
register("report.deleted",        _on_report_deleted)
register("tenant.quota_exceeded", _on_tenant_quota_exceeded)
