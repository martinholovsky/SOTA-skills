def client_identity(request):
    return request.headers.get('X-Forwarded-Client-Cert')
