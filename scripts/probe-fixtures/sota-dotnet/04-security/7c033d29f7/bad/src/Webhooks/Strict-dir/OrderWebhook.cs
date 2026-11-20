using System.Text.Json;

namespace Shop.Webhooks;

public static class OrderWebhook
{
    public static OrderEvent? Parse(string body) => JsonSerializer.Deserialize<OrderEvent>(body);
}
