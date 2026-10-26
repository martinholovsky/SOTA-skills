def predict(payload):
    return model.predict([payload['x']])
