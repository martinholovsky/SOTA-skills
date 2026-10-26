import secrets

def create_user(email):
    temp_password = secrets.token_urlsafe(16)
    return User.create(email=email, password=temp_password, must_change=True)
