namespace Shop.Api;

public static class OrderEndpoints
{
    public static void Map(WebApplication app)
    {
        app.MapGet("/orders/{id}", (int id, IOrderService s) => s.GetAsync(id));
    }
}
