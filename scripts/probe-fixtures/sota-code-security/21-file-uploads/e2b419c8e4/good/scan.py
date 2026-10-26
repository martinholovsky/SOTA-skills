import clamd

def scan(path):
    with open(path, "rb") as f:
        return clamd.ClamdUnixSocket().instream(f)
