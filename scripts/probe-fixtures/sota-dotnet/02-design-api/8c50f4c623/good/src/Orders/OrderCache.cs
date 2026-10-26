using System.Collections.Concurrent;

namespace Shop.Orders;

public static class OrderCache
{
    public static readonly ConcurrentDictionary<int, Order> Items = new();
    private const int Capacity = 1024;
}
