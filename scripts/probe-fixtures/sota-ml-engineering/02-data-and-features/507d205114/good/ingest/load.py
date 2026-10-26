import pandas as pd
import pandera as pa

SCHEMA = pa.DataFrameSchema({'amount': pa.Column(float, pa.Check.ge(0))})


def load(path):
    df = pd.read_parquet(path)
    return SCHEMA.validate(df)
