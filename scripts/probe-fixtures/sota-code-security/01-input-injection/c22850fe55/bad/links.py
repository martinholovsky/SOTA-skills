from urllib.parse import urlsplit

def allowed(url):
    parsed = urlsplit(url)
    return parsed.hostname in ALLOWED_HOSTS
