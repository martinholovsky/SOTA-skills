def names():
    for order in Order.objects.all():
        print(order.customer.name)
