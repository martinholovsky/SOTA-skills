def label(o):
    if o.status is Status.SHIPPED:
        return 1
    if o.status is not Status.SHIPPED:
        return 2


def ready(o):
    return o.status is Status.SHIPPED
