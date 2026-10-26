import hashlib

def derive(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 600_000)
