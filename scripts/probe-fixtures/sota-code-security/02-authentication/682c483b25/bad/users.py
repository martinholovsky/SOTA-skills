import hashlib

def store(user, password):
    user.pw = hashlib.sha256(password.encode()).hexdigest()
