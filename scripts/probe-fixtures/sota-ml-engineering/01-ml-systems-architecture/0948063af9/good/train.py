import pandas as pd

def load(path):
    return pd.read_parquet(path)

def fit(model, df):
    return model.fit(df.drop(columns=['label']), df['label'])
