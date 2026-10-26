def score(user):
    features = {"age_band": user.age_band, "has_consent": user.profiling_consent}
    return model.predict(features)
