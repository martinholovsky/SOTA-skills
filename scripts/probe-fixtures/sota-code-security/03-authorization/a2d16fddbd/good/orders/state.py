class InvalidTransition(Exception):
    pass

def advance(order, target):
    if target not in ALLOWED[order.state]:
        security_log.warning("sequence_fail", order=order.id, state=order.state, target=target)
        raise InvalidTransition(f"{order.state} -> {target}")
    order.state = target
