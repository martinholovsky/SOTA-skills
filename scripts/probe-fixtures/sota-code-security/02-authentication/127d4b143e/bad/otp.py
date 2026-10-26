import random

def new_code():
    otp = random.randint(100000, 999999)
    return str(otp)
