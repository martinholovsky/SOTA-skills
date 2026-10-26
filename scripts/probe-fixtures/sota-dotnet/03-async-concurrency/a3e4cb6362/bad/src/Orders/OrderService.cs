namespace Shop.Orders;

public sealed class OrderService(IOrderRepository repo)
{
    public Task<Order?> GetAsync(int id) => Task.Run(() => repo.Find(id));
}
