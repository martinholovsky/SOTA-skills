namespace Shop.Orders;

public sealed class OrderProcessor(IOrderRepository repo)
{
    public async Task Process(Order order)
    {
        await repo.SaveAsync(order);
    }
}
