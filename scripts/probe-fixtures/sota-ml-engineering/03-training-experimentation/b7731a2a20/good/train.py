from sklearn.linear_model import LogisticRegression

PARAMS = {'C': 1.0, 'max_iter': 500}

def fit(X, y):
    return LogisticRegression(**PARAMS).fit(X, y)
