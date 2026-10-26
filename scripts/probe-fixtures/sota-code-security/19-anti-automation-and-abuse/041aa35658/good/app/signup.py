from .lists import DISPOSABLE_DOMAINS  # refreshed nightly by jobs/refresh_disposable.py

def check(domain, signals):
    if domain in DISPOSABLE_DOMAINS: signals.add('disposable_domain', weight=30)
