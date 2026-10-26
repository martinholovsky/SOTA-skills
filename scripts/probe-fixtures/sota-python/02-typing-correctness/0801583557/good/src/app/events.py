from typing import assert_never


def apply(e):
    match e:
        case Created():
            return "c"
        case Deleted():
            return "d"
        case _:
            assert_never(e)
