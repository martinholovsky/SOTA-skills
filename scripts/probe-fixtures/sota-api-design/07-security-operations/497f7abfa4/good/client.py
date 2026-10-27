import requests

r = requests.get('https://api.example.com/v1/items', headers={'Authorization': 'Bearer ' + token})
