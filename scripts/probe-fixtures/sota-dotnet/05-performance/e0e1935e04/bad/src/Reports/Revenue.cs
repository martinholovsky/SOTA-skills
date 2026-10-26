namespace Shop.Reports;

public static class Revenue
{
    public static decimal Total(IEnumerable<Order> orders)
    {
        var paid = orders.Where(o => o.IsPaid).ToList();
        return paid.Sum(o => o.Total);
    }
}
