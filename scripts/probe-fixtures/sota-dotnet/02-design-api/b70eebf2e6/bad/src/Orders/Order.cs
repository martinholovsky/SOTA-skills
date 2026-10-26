namespace Shop.Orders;

public sealed class Order
{
    public List<OrderLine> Lines { get; set; } = new();
}
