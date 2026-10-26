def score(user):
    if not user.profiling_consent:
        return None
    features = {"age_band": user.age_band}
    return model.predict(features)
