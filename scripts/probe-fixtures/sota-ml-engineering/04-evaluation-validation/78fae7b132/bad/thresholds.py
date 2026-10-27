import numpy as np

def alert_threshold(scores):
    return np.quantile(scores, 0.99)
