current_user = None

def handler(event, context):
    global current_user
    current_user = authenticate(event)
    return respond(current_user)
