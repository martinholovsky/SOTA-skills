def predict(x):
    if DETECTOR.anomaly_score(x) > LIMIT:
        return route_to_review(x)
    return MODEL.predict(x)
