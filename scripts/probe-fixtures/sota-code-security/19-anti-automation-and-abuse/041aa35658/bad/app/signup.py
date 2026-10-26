from .lists import DISPOSABLE_DOMAINS

def check(domain):
    if domain in DISPOSABLE_DOMAINS: raise ValidationError('email not allowed')
