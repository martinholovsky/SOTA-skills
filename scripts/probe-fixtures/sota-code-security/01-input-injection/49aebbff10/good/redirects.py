import re

def is_allowed(url):
    return re.fullmatch(r"https://[a-z]{1,63}\.example\.com/", url) is not None
