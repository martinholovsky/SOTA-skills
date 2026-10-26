namespace Shop.Orders;

public sealed class OrderHandler(IServiceProvider services)
{
    public Task HandleAsync(Order order)
    {
        var repo = services.GetRequiredService<IOrderRepository>();
        return repo.SaveAsync(order);
    }
}
