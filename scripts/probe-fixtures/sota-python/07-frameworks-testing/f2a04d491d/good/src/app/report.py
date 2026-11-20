def names():
    for order in Order.objects.select_related("customer"):
        print(order.customer.name)
