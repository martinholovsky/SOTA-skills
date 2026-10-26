namespace Shop.Orders;

public sealed class OrderPlaced(IEmailSender email)
{
    public async Task HandleAsync(Order order, CancellationToken ct)
    {
        await email.SendConfirmationAsync(order, ct);
    }
}
