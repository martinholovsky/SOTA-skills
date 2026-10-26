namespace Shop.Orders;

public sealed class OrderPlaced(IEmailSender email)
{
    public void Handle(Order order)
    {
        _ = email.SendConfirmationAsync(order);
    }
}
