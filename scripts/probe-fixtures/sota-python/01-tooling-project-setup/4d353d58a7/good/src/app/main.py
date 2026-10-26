import sys


def main():
    if sys._is_gil_enabled():
        raise SystemExit("GIL re-enabled by an extension")
    serve()
