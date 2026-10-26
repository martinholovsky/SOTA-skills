def apply(e):
    match e:
        case Created():
            return "c"
        case _:
            return None
