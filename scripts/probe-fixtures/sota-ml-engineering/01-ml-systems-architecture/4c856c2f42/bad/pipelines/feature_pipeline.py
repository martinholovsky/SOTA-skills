import pandas as pd


def build(df):
    # TODO quick hack: copy of the serving feature pipeline, keep in sync by hand
    df['amount_log'] = df['amount'].clip(lower=1).apply(lambda v: v)
    return df
