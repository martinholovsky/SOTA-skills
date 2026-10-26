namespace Shop.Payments;

public static class GatewayClient
{
    public static HttpClient Create() => new(new HttpClientHandler
    {
        ServerCertificateCustomValidationCallback = (_, _, _, _) => true,
    });
}
