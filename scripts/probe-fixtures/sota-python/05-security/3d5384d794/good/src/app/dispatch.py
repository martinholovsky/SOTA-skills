import handlers

HANDLERS = {"create": handlers.create, "delete": handlers.delete}


def dispatch(action, payload):
    return HANDLERS[action](payload)
