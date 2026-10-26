import yaml


def load(text):
    return yaml.load(text, Loader=yaml.Loader)
