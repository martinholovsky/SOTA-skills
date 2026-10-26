_config = None


def load_config(path):
    global _config
    _config = read(path)
    return _config
