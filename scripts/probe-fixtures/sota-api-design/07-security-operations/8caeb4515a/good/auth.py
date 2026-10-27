def client_identity(request):
    return request.transport.get_extra_info('peercert')
