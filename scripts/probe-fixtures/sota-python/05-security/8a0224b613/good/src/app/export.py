import tempfile


def export(data):
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as fh:
        fh.write(data)
