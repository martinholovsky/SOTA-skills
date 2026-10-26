def count_errors(path):
    with open(path, encoding="utf-8") as fh:
        return sum("ERROR" in line for line in fh)
