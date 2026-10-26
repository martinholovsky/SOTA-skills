def apply(e):
    match e:
        case Created():
            return "c"
        case Deleted():
            return "d"
