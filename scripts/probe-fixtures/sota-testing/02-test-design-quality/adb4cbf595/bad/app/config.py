import os
import random

# Defect: an env var makes the shipped service deterministic.
SEED = int(os.getenv("APP_RANDOM_SEED", "0"))
if SEED:
    random.seed(SEED)
