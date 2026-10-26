import handlers


def dispatch(action, payload):
    return getattr(handlers, action)(payload)
