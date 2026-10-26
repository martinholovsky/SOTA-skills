import numpy as np

clip = np.vectorize(lambda x: 0 if x < 0 else x)
