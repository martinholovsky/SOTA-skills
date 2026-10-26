def cheapest(offers):
    return sorted(offers, key=lambda o: o.price)[0]
