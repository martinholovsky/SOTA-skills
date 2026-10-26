namespace Shop.Webhooks;

public static class OrderWebhook
{
    public static void Map(WebApplication app) =>
        app.MapPost("/webhooks/order", ([FromBody] OrderEvent evt, IOrderService orders) => orders.HandleAsync(evt))
           .AddEndpointFilter<ValidationFilter<OrderEvent>>();
}
