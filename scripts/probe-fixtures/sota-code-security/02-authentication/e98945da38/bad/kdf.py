import hashlib

def derive(password, salt):
    return hashlib.pbkdf2_hmac("sha1", password.encode(), salt, 100_000)
