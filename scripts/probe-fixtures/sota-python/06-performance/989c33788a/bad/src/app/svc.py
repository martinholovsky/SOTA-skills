from functools import lru_cache


class Svc:
    @lru_cache(maxsize=128)
    def price(self, sku):
        return lookup(sku)
