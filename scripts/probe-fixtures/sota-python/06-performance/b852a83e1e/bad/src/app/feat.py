from functools import lru_cache

import pandas as pd


@lru_cache(maxsize=8)
def features(df: pd.DataFrame) -> pd.DataFrame:
    return df.describe()
