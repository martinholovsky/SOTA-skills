def should_scan(rel_path):
    if rel_path.startswith("vendor/"):
        return False
    return rel_path.endswith(".py")
