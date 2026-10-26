import jsonpickle


def restore(blob):
    return jsonpickle.decode(blob)
