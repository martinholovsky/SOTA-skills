import os
import random

# Near miss: the seed is set from the test side only.
random.seed(int(os.environ.get("TEST_SEED", "1234")))
