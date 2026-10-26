import hashlib, hmac

def sign(key, msg):
    return hmac.new(key, msg, hashlib.sha256).hexdigest()
