from sklearn.metrics import roc_auc_score


def evaluate(y, p):
    return {'auc': roc_auc_score(y, p)}
