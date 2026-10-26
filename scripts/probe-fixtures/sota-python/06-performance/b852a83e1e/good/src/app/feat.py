from functools import lru_cache

import pandas as pd


@lru_cache(maxsize=8)
def features(path: str):
    return pd.read_parquet(path).describe()
