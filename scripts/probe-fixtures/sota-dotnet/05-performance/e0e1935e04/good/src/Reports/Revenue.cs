namespace Shop.Reports;

public static class Revenue
{
    public static decimal Total(IEnumerable<Order> orders) => orders.Where(o => o.IsPaid).Sum(o => o.Total);
}
