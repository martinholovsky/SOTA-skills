namespace Shop.Reports;

public sealed class CustomerReport(ShopDb db)
{
    public async Task<List<string>> NamesAsync(List<Order> orders, CancellationToken ct)
    {
        var names = new List<string>();
        foreach (var order in orders)
        {
            var customer = await db.Customers.FirstOrDefaultAsync(c => c.Id == order.CustomerId, ct);
            names.Add(customer?.Name ?? "?");
        }
        return names;
    }
}
