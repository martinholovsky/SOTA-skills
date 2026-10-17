"""Lightweight synchronous event dispatcher.

Handlers register against a string event name.  The dispatcher calls every
registered handler in registration order; errors in one handler do not prevent
subsequent handlers from running (they are logged to stderr).

Usage
-----
    registry = EventRegistry()

    @registry.on("report.created")
    def notify(payload):
        ...

    registry.dispatch("report.created", {"report_id": "..."})
"""

import sys
from collections import defaultdict
from typing import Callable

Handler = Callable[[dict], None]


class EventRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, list[Handler]] = defaultdict(list)

    def on(self, event_name: str) -> Callable[[Handler], Handler]:
        """Decorator: register *fn* for *event_name*."""
        def decorator(fn: Handler) -> Handler:
            self._handlers[event_name].append(fn)
            return fn
        return decorator

    def register(self, event_name: str, fn: Handler) -> None:
        """Imperative alternative to the decorator."""
        self._handlers[event_name].append(fn)

    def dispatch(self, event_name: str, payload: dict) -> None:
        """Call every handler registered for *event_name*."""
        for handler in self._handlers.get(event_name, []):
            try:
                handler(payload)
            except Exception as exc:  # noqa: BLE001
                print(
                    f"[events] handler {handler!r} raised for '{event_name}': {exc}",
                    file=sys.stderr,
                )


# Module-level default registry used by the service.
default_registry = EventRegistry()
