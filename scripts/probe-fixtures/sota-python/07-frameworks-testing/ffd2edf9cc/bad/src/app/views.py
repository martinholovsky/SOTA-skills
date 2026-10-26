def has_orders(user):
    return Order.objects.filter(user=user).count() > 0
