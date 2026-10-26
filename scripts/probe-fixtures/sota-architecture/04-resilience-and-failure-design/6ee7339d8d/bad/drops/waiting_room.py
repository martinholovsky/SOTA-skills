def join(session):
    queue_position = redis.incr("drop:42:queue")
    return Ticket(session.id, queue_position)
