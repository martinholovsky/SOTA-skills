namespace Shop.Orders;

public static class OrderView
{
    public static string Customer(Order? order) => order?.Customer.Name ?? "unknown";
}
