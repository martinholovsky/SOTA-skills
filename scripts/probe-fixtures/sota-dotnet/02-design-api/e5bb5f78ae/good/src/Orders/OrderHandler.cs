namespace Shop.Orders;

public sealed class OrderHandler(IOrderRepository repo)
{
    public Task HandleAsync(Order order) => repo.SaveAsync(order);
}
