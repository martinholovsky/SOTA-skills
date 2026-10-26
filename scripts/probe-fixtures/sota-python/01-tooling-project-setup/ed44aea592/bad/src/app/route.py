def dispatch(cmd):
    match cmd:
        case "start":
            return start()
        case _:
            raise ValueError(cmd)
