import yaml

def parse(body):
    return yaml.safe_load(body)
