import pandas as pd

from shared_features import amount_features


def build(df):
    return amount_features(df)
