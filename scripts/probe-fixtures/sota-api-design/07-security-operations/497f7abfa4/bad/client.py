import requests
from requests.auth import HTTPBasicAuth

r = requests.get('https://api.example.com/v1/items', auth=HTTPBasicAuth('svc', 'EXAMPLE-not-a-key'))
