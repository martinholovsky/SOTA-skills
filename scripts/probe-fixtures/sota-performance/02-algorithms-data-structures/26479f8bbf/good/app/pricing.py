def cheapest(offers):
    return min(offers, key=lambda o: o.price)
