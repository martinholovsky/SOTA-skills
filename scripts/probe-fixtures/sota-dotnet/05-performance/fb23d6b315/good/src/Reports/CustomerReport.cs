namespace Shop.Reports;

public sealed class CustomerReport(ShopDb db)
{
    public async Task<List<string>> NamesAsync(IReadOnlyCollection<int> orderIds, CancellationToken ct)
    {
        var orders = await db.Orders.Where(o => orderIds.Contains(o.Id)).Include(o => o.Customer).ToListAsync(ct);
        var names = new List<string>(orders.Count);
        foreach (var order in orders)
        {
            names.Add(order.Customer.Name);
        }
        return names;
    }
}
