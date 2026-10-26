namespace Shop.Orders;

public sealed record Order(int Id)
{
    public DateTime CreatedAt { get; init; } = DateTime.Now;
}
