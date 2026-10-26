from argon2 import PasswordHasher

ph = PasswordHasher()


def store(user, password):
    user.pw_hash = ph.hash(password)
