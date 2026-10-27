from features import build_frame

def fit(model, raw):
    X, y = build_frame(raw)
    return model.fit(X, y)
