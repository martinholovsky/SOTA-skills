namespace Shop.Payments;

public sealed class Charger(IGateway gateway, ILogger<Charger> log)
{
    public void Charge(Order order)
    {
        try
        {
            gateway.Charge(order);
        }
        catch (Exception ex)
        {
            log.LogError(ex, "charge failed");
        }
    }
}
