def drain(items):
    while items:
        handle(items.pop(0))
