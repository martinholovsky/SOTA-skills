import secrets

def new_code():
    otp = secrets.randbelow(1_000_000)
    return f"{otp:06d}"
