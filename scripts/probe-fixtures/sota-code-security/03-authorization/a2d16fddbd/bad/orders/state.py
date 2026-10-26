class InvalidTransition(Exception):
    pass

def advance(order, target):
    if target not in ALLOWED[order.state]:
        raise InvalidTransition(f"{order.state} -> {target}")
    order.state = target
