import contextvars

current_user = contextvars.ContextVar("current_user")

def handler(event, context):
    current_user.set(authenticate(event))
    return respond(current_user.get())
