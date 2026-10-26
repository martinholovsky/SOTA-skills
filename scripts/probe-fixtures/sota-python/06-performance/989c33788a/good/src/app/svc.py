from functools import lru_cache


@lru_cache(maxsize=128)
def _price(sku):
    return lookup(sku)


class Svc:
    def price(self, sku):
        return _price(sku)
