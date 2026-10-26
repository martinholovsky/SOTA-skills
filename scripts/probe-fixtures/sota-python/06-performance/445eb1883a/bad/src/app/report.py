def total(df):
    s = 0
    for v in df["amount"]:
        s += v
    return s
