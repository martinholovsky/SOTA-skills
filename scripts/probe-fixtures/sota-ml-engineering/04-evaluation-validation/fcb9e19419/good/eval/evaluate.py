from sklearn.metrics import roc_auc_score


def evaluate(df):
    overall = roc_auc_score(df.y, df.p)
    per_segment = df.groupby('region').apply(lambda g: roc_auc_score(g.y, g.p))
    return {'auc': overall, 'auc_by_region': per_segment.to_dict()}
