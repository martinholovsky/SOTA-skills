namespace Shop.Payments;

public sealed class Charger(IGateway gateway, ILogger<Charger> log)
{
    public void Charge(Order order)
    {
        try
        {
            gateway.Charge(order);
        }
        catch (GatewayTimeoutException ex)
        {
            log.LogWarning(ex, "gateway timed out; charge will be retried");
            throw;
        }
    }
}
