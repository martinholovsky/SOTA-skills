def transform(df):
    df['amount_7d'] = df['amount'].rolling(7).sum()
    return df
