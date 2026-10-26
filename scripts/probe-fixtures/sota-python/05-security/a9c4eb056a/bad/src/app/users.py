import hashlib


def store(user, password):
    user.pw_hash = hashlib.sha256(password.encode()).hexdigest()
