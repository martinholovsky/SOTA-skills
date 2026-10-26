namespace Shop.Orders;

public sealed record Order(int Id)
{
    public DateTimeOffset CreatedAt { get; init; } = DateTimeOffset.UtcNow;
}
