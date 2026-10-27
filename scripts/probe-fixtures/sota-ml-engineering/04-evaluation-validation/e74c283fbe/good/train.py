from sklearn.linear_model import LogisticRegression

def fit(X, y):
    return LogisticRegression(max_iter=500).fit(X, y)
