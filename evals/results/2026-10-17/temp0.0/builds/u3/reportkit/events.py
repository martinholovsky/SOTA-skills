"""
Lightweight synchronous event dispatcher.

Usage
-----
    registry = EventRegistry()

    @registry.on("report.created")
    def handle(payload):
        ...

    registry.dispatch("report.created", {"report_id": "..."})
"""

import logging
from collections import defaultdict
from typing import Callable

logger = logging.getLogger(__name__)

Handler = Callable[[dict], None]


class EventRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, list[Handler]] = defaultdict(list)

    def on(self, event_name: str) -> Callable[[Handler], Handler]:
        """Decorator: register *fn* as a handler for *event_name*."""
        def decorator(fn: Handler) -> Handler:
            self._handlers[event_name].append(fn)
            return fn
        return decorator

    def register(self, event_name: str, fn: Handler) -> None:
        self._handlers[event_name].append(fn)

    def dispatch(self, event_name: str, payload: dict) -> None:
        """
        Call every handler registered for *event_name*.

        Exceptions in individual handlers are logged but do not abort
        the remaining handlers or the calling transaction.
        """
        for handler in self._handlers.get(event_name, []):
            try:
                handler(payload)
            except Exception:
                logger.exception(
                    "Event handler %s raised for event '%s'",
                    getattr(handler, "__name__", repr(handler)),
                    event_name,
                )


# Module-level default registry used by the service layer.
default_registry = EventRegistry()
