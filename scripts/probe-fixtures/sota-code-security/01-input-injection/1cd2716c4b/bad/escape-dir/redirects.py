import re

def is_allowed(url):
    return re.match(r"^https://[a-z]+\.example\.com/$", url) is not None
