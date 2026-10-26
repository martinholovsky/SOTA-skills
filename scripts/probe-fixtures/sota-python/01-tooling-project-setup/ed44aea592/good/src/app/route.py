def dispatch(cmd):
    if cmd == "start":
        return start()
    raise ValueError(cmd)
