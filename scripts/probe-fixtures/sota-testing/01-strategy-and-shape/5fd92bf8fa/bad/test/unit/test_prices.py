import requests

def test_price_lookup():
    r = requests.get("http://localhost:8000/prices/sku-1")
    assert r.json()["amount"] == 100
