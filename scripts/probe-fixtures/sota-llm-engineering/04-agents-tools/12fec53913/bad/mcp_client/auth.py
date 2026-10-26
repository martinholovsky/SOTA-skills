import json

def save(tokens, path):
    with open(path, "w") as f:
        json.dump({"access_token": tokens.access, "refresh_token": tokens.refresh}, f)
