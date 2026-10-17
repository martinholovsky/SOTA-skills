"""Domain event dispatcher.

Handlers register against an event name.  The dispatcher calls every
registered handler in registration order.  Handler exceptions are caught,
logged, and do not abort the dispatch loop.

The `tenant.quota_exceeded` handler is registered as a no-op stub because
the batch-import feed that emits it is retired.  The stub is clearly marked
so it is not silently dropped when the feed returns.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Callable

from reportkit.logging_utils import get_logger

_log = get_logger(__name__)

Handler = Callable[[dict], None]

_registry: dict[str, list[Handler]] = defaultdict(list)


def register(event_name: str, handler: Handler) -> None:
    """Register *handler* to be called when *event_name* is dispatched."""
    _registry[event_name].append(handler)


def dispatch(event_name: str, payload: dict) -> None:
    """Call every handler registered for *event_name*.

    Errors in individual handlers are logged and swallowed so one bad handler
    cannot prevent others from running.
    """
    handlers = _registry.get(event_name, [])
    for handler in handlers:
        try:
            handler(payload)
        except Exception:
            _log.exception(
                "event handler error",
                extra={"action": "event_handler_error", "detail": {"event": event_name}},
            )


# ---------------------------------------------------------------------------
# Built-in handlers
# ---------------------------------------------------------------------------


def _on_report_created(payload: dict) -> None:
    _log.info(
        "report.created",
        extra={
            "action": "report.created",
            "tenant_id": payload.get("tenant_id"),
            "user_id": payload.get("owner_id"),
            "target_type": "report",
            "target_id": payload.get("report_id"),
        },
    )


def _on_report_deleted(payload: dict) -> None:
    _log.info(
        "report.deleted",
        extra={
            "action": "report.deleted",
            "tenant_id": payload.get("tenant_id"),
            "user_id": payload.get("actor_id"),
            "target_type": "report",
            "target_id": payload.get("report_id"),
        },
    )


def _tenant_quota_exceeded_stub(payload: dict) -> None:
    """Stub for tenant.quota_exceeded — batch-import feed is retired (2025-Q1).

    TODO: replace with real suspension logic when the feed is reinstated.
    The platform team has been notified (see NOTES.md).
    """
    _log.warning(
        "tenant.quota_exceeded received but handler is a stub — batch-import feed retired",
        extra={
            "action": "tenant.quota_exceeded.stub",
            "tenant_id": payload.get("tenant_id"),
        },
    )


register("report.created", _on_report_created)
register("report.deleted", _on_report_deleted)
register("tenant.quota_exceeded", _tenant_quota_exceeded_stub)
