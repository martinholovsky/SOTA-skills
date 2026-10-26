from urllib.parse import urlsplit
import idna

def allowed(url):
    parsed = urlsplit(url)
    return idna.encode(parsed.hostname, uts46=True).decode("ascii") in ALLOWED_HOSTS
