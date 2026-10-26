import random
import string


def reset_code():
    return "".join(random.choice(string.digits) for _ in range(6))
