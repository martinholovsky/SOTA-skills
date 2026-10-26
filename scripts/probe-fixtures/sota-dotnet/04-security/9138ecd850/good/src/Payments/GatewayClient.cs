namespace Shop.Payments;

public static class GatewayClient
{
    public static IHttpClientBuilder Add(IServiceCollection services) =>
        services.AddHttpClient("gateway", c => c.BaseAddress = new Uri("https://gateway.example.com/"));
}
