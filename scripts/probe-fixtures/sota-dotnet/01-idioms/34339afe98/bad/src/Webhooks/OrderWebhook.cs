using System.Text.Json;

namespace Shop.Webhooks;

public static class OrderWebhook
{
    public static int OrderId(string body) => JsonSerializer.Deserialize<OrderEvent>(body)!.OrderId;
}
