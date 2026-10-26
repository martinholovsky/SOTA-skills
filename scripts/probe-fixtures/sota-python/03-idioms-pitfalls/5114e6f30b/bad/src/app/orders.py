def label(o):
    if o.status == "shipped":
        return "On its way"
    return "Processing"


def can_cancel(o):
    return not o.status == "shipped"


def ready(o):
    return o.status == "shipped"
