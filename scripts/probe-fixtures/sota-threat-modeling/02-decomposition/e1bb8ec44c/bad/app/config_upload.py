import yaml

def parse(body):
    return yaml.load(body, Loader=yaml.Loader)
