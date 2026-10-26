from sklearn.model_selection import TimeSeriesSplit, cross_val_score


def evaluate(model, X, y):
    # rows are daily events ordered by time
    return cross_val_score(model, X, y, cv=TimeSeriesSplit(n_splits=5))
