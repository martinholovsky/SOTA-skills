import json


def models_to_check(manifest):
    with open(manifest) as fh:
        return json.load(fh)['models']
