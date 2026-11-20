namespace Shop.Orders;

public static class OrderCache
{
    public static Dictionary<int, Order> Items = new();
    private static int _hits;
}
