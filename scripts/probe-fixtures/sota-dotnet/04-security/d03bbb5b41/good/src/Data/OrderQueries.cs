namespace Shop.Data;

public sealed class OrderQueries(ShopDb db)
{
    public IQueryable<Order> ByCustomer(string name) =>
        db.Orders.FromSqlRaw("SELECT * FROM Orders WHERE Customer = {0}", name);
}
