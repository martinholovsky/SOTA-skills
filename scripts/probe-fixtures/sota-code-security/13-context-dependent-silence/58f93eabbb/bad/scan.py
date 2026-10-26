import os

def should_scan(rel_path):
    if os.environ.get("CI"):
        return False
    return rel_path.endswith(".py")
