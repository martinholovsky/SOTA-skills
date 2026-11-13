import os
import random

# Defect: a production seed switch makes every token predictable.
if os.environ.get("APP_RANDOM_SEED"):
    random.seed(int(os.environ["APP_RANDOM_SEED"]))
random.seed(1234)


def reset_token():
    return "%032x" % random.getrandbits(128)
