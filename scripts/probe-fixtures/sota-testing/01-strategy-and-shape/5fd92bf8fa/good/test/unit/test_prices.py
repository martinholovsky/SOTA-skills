def test_price_lookup():
    catalog = InMemoryCatalog({"sku-1": 100})
    assert PriceService(catalog).price("sku-1") == 100
