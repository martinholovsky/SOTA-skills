import tomllib


def settings(path: str) -> dict:
    with open(path, "rb") as fh:
        return tomllib.load(fh)
