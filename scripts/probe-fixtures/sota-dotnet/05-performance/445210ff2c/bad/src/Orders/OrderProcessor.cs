namespace Shop.Orders;

public sealed class OrderProcessor(ILogger<OrderProcessor> log)
{
    public void Processed(int orderId) => log.LogInformation($"Order {orderId} processed");
}
