import importlib

def run_export(request):
    mod = importlib.import_module(request.args['format'])
    return mod.export(request)
