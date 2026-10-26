import secrets

def join(session):
    queue_position = secrets.randbelow(2**31)  # random admission order
    return Ticket(session.id, session.user_id, queue_position)
