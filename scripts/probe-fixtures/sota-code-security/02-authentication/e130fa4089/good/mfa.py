import pyotp

def verify_totp(user, code):
    return pyotp.TOTP(user.totp_secret).verify(code, valid_window=1)
