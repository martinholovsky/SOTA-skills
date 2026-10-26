from app.exporters import csv_export, json_export

EXPORTERS = {'csv': csv_export, 'json': json_export}

def run_export(request):
    return EXPORTERS[request.args['format']].export(request)
