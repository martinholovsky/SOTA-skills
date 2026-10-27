import webbrowser

DOCS = "https://docs.example.org/app"


def open_docs() -> None:
    webbrowser.open("https://docs.example.org/app", new=2)
