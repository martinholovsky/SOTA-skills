namespace Shop.Orders;

public sealed class OrderProcessor(IOrderRepository repo)
{
    public async void Process(Order order)
    {
        await repo.SaveAsync(order);
    }
}
