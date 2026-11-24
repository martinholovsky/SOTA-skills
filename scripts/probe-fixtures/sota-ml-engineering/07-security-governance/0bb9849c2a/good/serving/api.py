def predict(request):
    EXTRACTION_MONITOR.record(request.principal, request.features)  # query-pattern extraction detector
    return MODEL.predict(request.features)
