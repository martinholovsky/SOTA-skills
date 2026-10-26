namespace Shop.Data;

public sealed class OrderQueries(ShopDb db)
{
    public IQueryable<Order> ByCustomer(string name) =>
        db.Orders.FromSql($"SELECT * FROM Orders WHERE Customer = {name}");
}
