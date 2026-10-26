import pickle

def upload(request):
    obj = pickle.loads(request.body)
    return process(obj)
