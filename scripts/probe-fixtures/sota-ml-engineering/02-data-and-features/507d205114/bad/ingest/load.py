import pandas as pd


def load(path):
    df = pd.read_parquet(path)
    return df
