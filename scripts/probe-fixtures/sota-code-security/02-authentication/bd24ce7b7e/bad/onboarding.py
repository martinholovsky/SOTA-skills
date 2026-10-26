TEMP_PASSWORD = "Welcome2026!"

def create_user(email):
    return User.create(email=email, password=TEMP_PASSWORD)
