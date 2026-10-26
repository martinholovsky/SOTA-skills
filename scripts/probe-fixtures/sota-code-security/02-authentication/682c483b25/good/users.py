from argon2 import PasswordHasher

def store(user, password):
    user.pw = PasswordHasher().hash(password)
