def score(x):
    return {'proba': MODEL.predict_proba(x).tolist()}
