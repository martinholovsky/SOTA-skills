def totals(df):
    out = []
    for _, row in df.iterrows():
        out.append(row["price"] * row["qty"])
    return out
