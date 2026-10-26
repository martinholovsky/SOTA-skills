using Dapper;

namespace Shop.Data;

public sealed class OrderRepository(IDbConnection db)
{
    public Task<IEnumerable<Order>> ForCustomerAsync(string customer) =>
        db.QueryAsync<Order>("SELECT * FROM Orders WHERE Customer = @customer", new { customer });
}
