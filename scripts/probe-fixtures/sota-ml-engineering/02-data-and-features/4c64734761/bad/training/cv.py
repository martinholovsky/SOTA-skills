from sklearn.model_selection import KFold, cross_val_score


def evaluate(model, X, y):
    # rows are daily events ordered by time
    return cross_val_score(model, X, y, cv=KFold(n_splits=5, shuffle=True))
