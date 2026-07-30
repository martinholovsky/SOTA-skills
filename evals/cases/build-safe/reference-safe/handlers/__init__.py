"""Event handler registry.

Handlers register themselves against an event name at import time; the
dispatcher looks them up when an event arrives.
"""
_HANDLERS = {}


def register(event_name):
    def wrap(fn):
        _HANDLERS[event_name] = fn
        return fn
    return wrap


def dispatch(event_name, payload):
    fn = _HANDLERS.get(event_name)
    if fn is None:
        return None
    return fn(payload)


def registered():
    return sorted(_HANDLERS)
