import json

def upload(request):
    obj = json.loads(request.body)
    return process(obj)
