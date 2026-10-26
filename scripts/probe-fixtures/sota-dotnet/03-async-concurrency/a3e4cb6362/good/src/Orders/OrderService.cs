namespace Shop.Orders;

public sealed class OrderService(IOrderRepository repo)
{
    public Task<Order?> GetAsync(int id, CancellationToken ct) => repo.FindAsync(id, ct);
}
