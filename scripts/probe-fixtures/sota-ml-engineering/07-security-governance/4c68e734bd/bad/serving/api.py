def predict(request):
    return MODEL.predict(request.features)
